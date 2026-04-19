"""
agents/icd_mapper.py

Responsibilities:
  Step 4  — Predict ICD-10 code from disease description + SOAP assessment (LLM)
  Step 5  — Validate predicted code against PostgreSQL icd_codes table
  Step 6  — If invalid, find closest match (prefix search + text search)
  Step 7  — Map validated ICD to a procedure from icd_procedure_mapping table
  Step 8  — Check conflict_rules table for diagnosis-procedure conflicts
"""

import os
import json
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────
# LLM Helper — Lazy Groq Initialization
# ─────────────────────────────────────────────

async def _call_llm(prompt: str, max_tokens: int = 256) -> str:
    """Lazy Groq client — created inside function, never at import time."""
    try:
        from groq import AsyncGroq
    except ImportError as e:
        raise RuntimeError("groq not installed. Run: pip install groq") from e

    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise EnvironmentError("GROQ_API_KEY is not set in environment.")

    client = AsyncGroq(api_key=api_key)
    response = await client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1,
        max_tokens=max_tokens,
        response_format={"type": "json_object"},
    )
    return response.choices[0].message.content


# ─────────────────────────────────────────────
# Step 4: Predict ICD-10 from Clinical Notes
# ─────────────────────────────────────────────

_PREDICT_PROMPT = """You are a clinical coding specialist (CCS). Based on the disease description and clinical assessment below, predict the single most accurate ICD-10-CM diagnosis code.

Disease Description: {disease_description}
Clinical Assessment: {assessment}
Patient Age: {age} | Gender: {gender}

Rules:
- Use the most specific ICD-10-CM code available (not a category-only code)
- Prioritize primary diagnosis
- confidence is a float between 0.0 and 1.0

Return ONLY this JSON (no extra text):
{{"icd10_code": "X00.0", "icd10_description": "Full description here", "confidence": 0.87}}"""


async def predict_icd_code(
    disease_description: str,
    assessment: str,
    patient_age: int,
    patient_gender: str,
) -> dict:
    """
    Step 4: Use Groq LLM to predict the most accurate ICD-10 code
    from the raw disease description and SOAP assessment.
    """
    prompt = _PREDICT_PROMPT.format(
        disease_description=disease_description,
        assessment=assessment,
        age=patient_age,
        gender=patient_gender,
    )
    try:
        raw = await _call_llm(prompt)
        data = json.loads(raw)
        return {
            "code": str(data.get("icd10_code", "R69")).strip().upper(),
            "description": str(data.get("icd10_description", "Illness, unspecified")),
            "confidence": float(data.get("confidence", 0.5)),
        }
    except Exception as e:
        logger.error("ICD prediction failed: %s", e)
        return {
            "code": "R69",
            "description": "Illness, unspecified",
            "confidence": 0.3,
        }


# ─────────────────────────────────────────────
# Step 5: Validate ICD Code in PostgreSQL
# ─────────────────────────────────────────────

async def validate_icd_in_db(code: str, pool) -> Optional[dict]:
    """
    Step 5: Check if the predicted ICD-10 code exists in the icd_codes table.
    Returns the DB record (code, description, severity) or None if not found.
    """
    try:
        row = await pool.fetchrow(
            """
            SELECT code, description, severity, category
            FROM icd_codes
            WHERE code = $1 AND is_active = TRUE
            """,
            code,
        )
        if row:
            return {
                "code": row["code"],
                "description": row["description"],
                "severity": row["severity"],
                "category": row["category"],
            }
        return None
    except Exception as e:
        logger.error("ICD DB validation error: %s", e)
        return None


# ─────────────────────────────────────────────
# Step 6: Find Closest ICD Match (Correction)
# ─────────────────────────────────────────────

async def find_closest_icd(predicted_code: str, description: str, pool) -> Optional[dict]:
    """
    Step 6: When predicted ICD is invalid, find the closest match using:
    1. 3-character prefix match (e.g. "I21" matches "I21.9")
    2. Full-text description search fallback
    """
    try:
        # Strategy 1: 3-character prefix match
        prefix = predicted_code[:3]
        rows = await pool.fetch(
            """
            SELECT code, description, severity, category
            FROM icd_codes
            WHERE code LIKE $1 AND is_active = TRUE
            ORDER BY code
            LIMIT 1
            """,
            f"{prefix}%",
        )
        if rows:
            row = rows[0]
            return {
                "code": row["code"],
                "description": row["description"],
                "severity": row["severity"],
                "category": row["category"],
            }

        # Strategy 2: Text search on description keywords
        keywords = description.lower().split()[:3]
        for keyword in keywords:
            if len(keyword) < 4:
                continue
            rows = await pool.fetch(
                """
                SELECT code, description, severity, category
                FROM icd_codes
                WHERE LOWER(description) LIKE $1 AND is_active = TRUE
                ORDER BY code
                LIMIT 1
                """,
                f"%{keyword}%",
            )
            if rows:
                row = rows[0]
                return {
                    "code": row["code"],
                    "description": row["description"],
                    "severity": row["severity"],
                    "category": row["category"],
                }

        return None

    except Exception as e:
        logger.error("Closest ICD search error: %s", e)
        return None


# ─────────────────────────────────────────────
# Step 7: Map ICD Code to Procedure
# ─────────────────────────────────────────────

async def map_icd_to_procedure(icd_code: str, pool) -> Optional[dict]:
    """
    Step 7: Look up icd_procedure_mapping to find the recommended
    procedure for the validated ICD-10 code.
    Returns procedure code, description, and requires_auth flag.
    """
    try:
        row = await pool.fetchrow(
            """
            SELECT p.code, p.description, p.requires_auth, p.category
            FROM icd_procedure_mapping ipm
            JOIN procedure_codes p ON p.code = ipm.procedure_code
            WHERE ipm.icd_code = $1
              AND ipm.is_primary = TRUE
              AND p.is_active = TRUE
            LIMIT 1
            """,
            icd_code,
        )
        if row:
            return {
                "code": row["code"],
                "description": row["description"],
                "requires_auth": row["requires_auth"],
                "category": row["category"],
            }
        return None
    except Exception as e:
        logger.error("Procedure mapping error: %s", e)
        return None


# ─────────────────────────────────────────────
# Step 8: Check Conflict Rules
# ─────────────────────────────────────────────

async def check_conflicts_in_db(
    icd_code: str,
    procedure_code: str,
    patient_age: int,
    patient_gender: str,
    pool,
) -> list:
    """
    Step 8: Query conflict_rules table for any conflicts between
    the diagnosis code and procedure code.
    Also applies age and gender restriction rules.
    """
    conflicts = []
    try:
        rows = await pool.fetch(
            """
            SELECT rule_name, conflict_type, severity, description, action, metadata
            FROM conflict_rules
            WHERE is_active = TRUE
              AND (icd_code = $1 OR icd_code IS NULL)
              AND (procedure_code = $2 OR procedure_code IS NULL)
            """,
            icd_code,
            procedure_code,
        )

        for row in rows:
            conflict_type = row["conflict_type"]
            include = True

            # Evaluate age restriction rules
            if conflict_type == "age_restriction":
                try:
                    meta = json.loads(row["metadata"] or "{}")
                    min_age = meta.get("min_age", 0)
                    max_age = meta.get("max_age", 200)
                    include = not (min_age <= patient_age <= max_age)
                except Exception:
                    include = False

            # Evaluate gender restriction rules
            elif conflict_type == "gender_restriction":
                try:
                    meta = json.loads(row["metadata"] or "{}")
                    allowed = [g.lower() for g in meta.get("allowed_genders", [])]
                    include = bool(allowed) and patient_gender.lower() not in allowed
                except Exception:
                    include = False

            if include:
                conflicts.append({
                    "rule_name": row["rule_name"],
                    "conflict_type": conflict_type,
                    "severity": row["severity"],
                    "description": row["description"],
                    "action": row["action"],
                })

    except Exception as e:
        logger.error("Conflict check DB error: %s", e)

    return conflicts