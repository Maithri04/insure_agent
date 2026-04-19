"""
agents/conflict_checker.py

Pipeline Step 8
────────────────
Step 8 — Check for conflicts between the validated diagnosis (ICD-10)
          and the mapped/provided procedure using the PostgreSQL rule engine.

Conflict types handled:
  • contraindication    — procedure is clinically unsafe/inappropriate for this diagnosis
  • age_restriction     — patient age falls in a restricted range for this procedure
  • gender_restriction  — procedure not applicable for patient's gender
  • missing_criteria    — required clinical criteria not met (e.g. no angiography before PTCA)
  • duplicate_billing   — potential duplicate claim within time window
  • experimental        — procedure is investigational for this diagnosis

Each rule has:
  • severity   → high | medium | low
  • action     → deny | flag | review
  • metadata   → JSONB with age ranges, allowed genders, etc.

Design:
  • All rules stored in PostgreSQL conflict_rules table (seeded via seed.sql)
  • Global rules (icd_code IS NULL) apply to all diagnoses for a procedure
  • Specific rules target exact ICD + procedure code pairs
  • Age and gender rules evaluated from JSONB metadata in Python
  • Returns structured list consumed directly by AgentResponse.conflicts
"""

import json
import logging
from typing import List
from schemas.agent_schema import ConflictItem, SeverityEnum

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# DB Query — fetch applicable rules
# ─────────────────────────────────────────────────────────────────────────────

async def _fetch_rules(icd_code: str, procedure_code: str, pool) -> list:
    """
    Fetch all active conflict rules that apply to this ICD + procedure pair.
    Includes:
      1. Exact match rules  (icd_code = X  AND procedure_code = Y)
      2. Global proc rules  (icd_code IS NULL AND procedure_code = Y)
      3. Global ICD rules   (icd_code = X  AND procedure_code IS NULL)
    """
    try:
        rows = await pool.fetch(
            """
            SELECT
                rule_name,
                icd_code,
                procedure_code,
                conflict_type,
                severity,
                description,
                action,
                metadata
            FROM conflict_rules
            WHERE is_active = TRUE
              AND (
                    (icd_code = $1 AND procedure_code = $2)
                 OR (icd_code IS NULL AND procedure_code = $2)
                 OR (icd_code = $1 AND procedure_code IS NULL)
              )
            ORDER BY
                CASE severity
                    WHEN 'high'   THEN 1
                    WHEN 'medium' THEN 2
                    WHEN 'low'    THEN 3
                END
            """,
            icd_code,
            procedure_code,
        )
        return list(rows)
    except Exception as exc:
        logger.error("conflict_rules DB fetch error: %s", exc)
        return []


# ─────────────────────────────────────────────────────────────────────────────
# Rule Evaluators
# ─────────────────────────────────────────────────────────────────────────────

def _evaluate_age_restriction(metadata_json: str | None, patient_age: int) -> bool:
    """
    Returns True (conflict applies) when patient age falls in the restricted range.
    metadata format: {"min_age": 0, "max_age": 17}
    """
    try:
        meta = json.loads(metadata_json or "{}")
        min_age = int(meta.get("min_age", 0))
        max_age = int(meta.get("max_age", 200))
        return min_age <= patient_age <= max_age
    except Exception as exc:
        logger.warning("Age restriction metadata parse error: %s", exc)
        return False


def _evaluate_gender_restriction(metadata_json: str | None, patient_gender: str) -> bool:
    """
    Returns True (conflict applies) when patient gender is NOT in allowed list.
    metadata format: {"allowed_genders": ["female"]}
    """
    try:
        meta = json.loads(metadata_json or "{}")
        allowed = [g.lower().strip() for g in meta.get("allowed_genders", [])]
        if not allowed:
            return False    # No gender filter defined — rule does not apply
        return patient_gender.lower().strip() not in allowed
    except Exception as exc:
        logger.warning("Gender restriction metadata parse error: %s", exc)
        return False


def _evaluate_contraindication(_metadata: str | None, _age: int, _gender: str) -> bool:
    """Contraindications always apply — no metadata check needed."""
    return True


def _evaluate_missing_criteria(_metadata: str | None, _age: int, _gender: str) -> bool:
    """
    Missing criteria rules always fire — the clinical completeness check
    is handled by evidence_detector.py, so here we always flag.
    """
    return True


def _evaluate_duplicate_billing(_metadata: str | None, _age: int, _gender: str) -> bool:
    """Duplicate billing rules always fire for review."""
    return True


def _evaluate_experimental(_metadata: str | None, _age: int, _gender: str) -> bool:
    """Experimental/investigational rules always fire for review."""
    return True


# Dispatcher — maps conflict_type → evaluator function
_EVALUATORS = {
    "contraindication":    _evaluate_contraindication,
    "age_restriction":     _evaluate_age_restriction,
    "gender_restriction":  _evaluate_gender_restriction,
    "missing_criteria":    _evaluate_missing_criteria,
    "duplicate_billing":   _evaluate_duplicate_billing,
    "experimental":        _evaluate_experimental,
}


# ─────────────────────────────────────────────────────────────────────────────
# Conflict Rule Processor
# ─────────────────────────────────────────────────────────────────────────────

def _process_rule(row: dict, patient_age: int, patient_gender: str) -> ConflictItem | None:
    """
    Evaluate a single conflict rule row from the DB.
    Returns a ConflictItem if the rule fires, None if it does not apply.
    """
    conflict_type = row["conflict_type"]
    metadata_raw  = row["metadata"]

    # Convert asyncpg Record metadata to string if it came as dict/JSON
    if isinstance(metadata_raw, dict):
        metadata_str = json.dumps(metadata_raw)
    else:
        metadata_str = str(metadata_raw) if metadata_raw else None

    evaluator = _EVALUATORS.get(conflict_type)
    if not evaluator:
        logger.warning("Unknown conflict type '%s' in rule '%s'", conflict_type, row["rule_name"])
        return None

    # Call the appropriate evaluator with age and gender context
    if conflict_type == "age_restriction":
        fires = evaluator(metadata_str, patient_age)
    elif conflict_type == "gender_restriction":
        fires = evaluator(metadata_str, patient_gender)
    else:
        fires = evaluator(metadata_str, patient_age, patient_gender)

    if not fires:
        return None

    return ConflictItem(
        rule_name=row["rule_name"],
        severity=SeverityEnum(row["severity"]),
        description=row["description"],
        action=row["action"],
    )


# ─────────────────────────────────────────────────────────────────────────────
# Summary Stats
# ─────────────────────────────────────────────────────────────────────────────

def _build_conflict_summary(conflicts: List[ConflictItem]) -> str:
    """
    Build a one-line summary for the agent steps log / thought process panel.
    """
    if not conflicts:
        return "Step 8 ✓ No conflicts found — diagnosis and procedure are compatible"

    deny_count   = sum(1 for c in conflicts if c.action == "deny")
    flag_count   = sum(1 for c in conflicts if c.action == "flag")
    review_count = sum(1 for c in conflicts if c.action == "review")
    high_count   = sum(1 for c in conflicts if c.severity == SeverityEnum.high)

    parts = []
    if deny_count:
        parts.append(f"{deny_count} DENY")
    if flag_count:
        parts.append(f"{flag_count} FLAG")
    if review_count:
        parts.append(f"{review_count} REVIEW")

    return (
        f"Step 8 ✓ {len(conflicts)} conflict(s) detected "
        f"[{' | '.join(parts)}] — {high_count} high severity"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Public Entry Point — called by agent_service.py
# ─────────────────────────────────────────────────────────────────────────────

async def run_conflict_checks(
    icd_code: str,
    procedure_code: str,
    patient_age: int,
    patient_gender: str,
    pool,
    steps: list,
) -> List[ConflictItem]:
    """
    Step 8: Full conflict check against the PostgreSQL rule engine.

    Checks:
      1. Exact ICD + procedure conflicts
      2. Global procedure-level rules (any diagnosis)
      3. Global ICD-level rules (any procedure)
      4. Age restriction evaluation (from JSONB metadata)
      5. Gender restriction evaluation (from JSONB metadata)

    Args:
        icd_code       : Validated ICD-10 code
        procedure_code : Mapped or provided procedure code
        patient_age    : Patient age from frontend form
        patient_gender : Patient gender from frontend form
        pool           : asyncpg connection pool
        steps          : Agent thought process log list

    Returns:
        List[ConflictItem] — empty list means no conflicts found
    """
    steps.append(
        f"Step 8 ▶ Running conflict rule engine for ICD {icd_code} + "
        f"Procedure {procedure_code} | Age {patient_age} | Gender {patient_gender}..."
    )

    raw_rows = await _fetch_rules(icd_code, procedure_code, pool)

    if not raw_rows:
        steps.append("Step 8 ✓ No conflict rules matched — diagnosis and procedure are compatible")
        return []

    conflicts: List[ConflictItem] = []
    for row in raw_rows:
        item = _process_rule(dict(row), patient_age, patient_gender)
        if item:
            conflicts.append(item)
            logger.info(
                "Conflict fired: [%s] %s — action: %s",
                item.severity.value.upper(), item.rule_name, item.action,
            )

    steps.append(_build_conflict_summary(conflicts))
    return conflicts