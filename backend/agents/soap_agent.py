"""
agents/soap_agent.py

Pipeline Steps 1 – 3
─────────────────────
Step 1 — Receive raw doctor input (disease_description + all form fields)
Step 2 — Use LLM to understand and structure clinical notes
Step 3 — Return structured SOAP note:
           Subjective | Objective | Assessment | Plan

Design:
  • Groq LLM (llama-3.3-70b-versatile) — lazy init, never at import time
  • Prompt engineered for clinical accuracy and ICD-ready assessment language
  • Fallback SOAP built from form fields if LLM fails — system never crashes
  • async — non-blocking for FastAPI
"""

import os
import json
import logging
from schemas.agent_schema import AgentRequest

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# LLM Client — Lazy Initialization (Step 2)
# ─────────────────────────────────────────────────────────────────────────────

async def _call_groq(prompt: str) -> str:
    """
    Lazy Groq client — instantiated inside the function at call time.
    Reads GROQ_API_KEY from environment (never at import time).
    Uses JSON mode to guarantee structured output.
    """
    try:
        from groq import AsyncGroq
    except ImportError as exc:
        raise RuntimeError(
            "groq package missing. Install with: pip install groq"
        ) from exc

    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise EnvironmentError(
            "GROQ_API_KEY is not set. Add it to your .env file."
        )

    client = AsyncGroq(api_key=api_key)

    response = await client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a board-certified clinical documentation specialist. "
                    "Your task is to convert raw doctor notes into a structured SOAP note. "
                    "Use formal, professional clinical language appropriate for insurance prior authorization. "
                    "Always respond with valid JSON only — no preamble, no markdown."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        temperature=0.15,   # Low = consistent, reproducible clinical language
        max_tokens=900,
        response_format={"type": "json_object"},
    )
    return response.choices[0].message.content


# ─────────────────────────────────────────────────────────────────────────────
# Prompt Builder (Step 2)
# ─────────────────────────────────────────────────────────────────────────────

def _build_soap_prompt(req: AgentRequest) -> str:
    """
    Construct a rich clinical prompt using all available form fields.
    The more context provided, the better the SOAP output quality.
    """
    # Build clinical justification context block
    cj_lines = []
    if req.duration_of_symptoms:
        cj_lines.append(f"  • Duration of symptoms   : {req.duration_of_symptoms}")
    if req.prior_treatment:
        cj_lines.append(f"  • Prior treatment        : {req.prior_treatment}")
    if req.severity:
        cj_lines.append(f"  • Severity               : {req.severity}")
    if req.investigations:
        cj_lines.append(f"  • Investigations/Labs    : {req.investigations}")
    if req.specialist_referral:
        cj_lines.append(f"  • Specialist referral    : {req.specialist_referral}")

    clinical_justification_block = (
        "\n".join(cj_lines) if cj_lines else "  • No additional justification fields provided"
    )

    return f"""Convert the following patient information into a structured SOAP note for insurance prior authorization.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PATIENT DEMOGRAPHICS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Name   : {req.patient_name}
  Age    : {req.patient_age} years
  Gender : {req.patient_gender.value}
  TPA    : {req.tpa}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CLINICAL NOTES (Doctor's Raw Input)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{req.disease_description}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
MEDICATIONS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  {req.medications or "None reported"}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CLINICAL JUSTIFICATION FIELDS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{clinical_justification_block}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PROCEDURE (if known)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  {req.procedure or "Not specified — will be mapped from diagnosis"}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
INSTRUCTIONS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Generate a complete, clinically accurate SOAP note with these exact 4 fields:

  subjective : Chief complaint, symptom history, patient-reported severity and duration
  objective  : Vital signs (estimate from context if not stated), physical exam findings,
               test results, observations from investigations
  assessment : Primary diagnosis with clinical reasoning, differential diagnoses if relevant.
               Use language that clearly supports ICD-10 coding.
  plan       : Specific treatment plan — medications with doses if stated, procedures,
               specialist referrals, follow-up schedule, monitoring parameters

Return ONLY this JSON structure — no extra keys, no commentary:
{{
  "subjective": "...",
  "objective":  "...",
  "assessment": "...",
  "plan":       "..."
}}"""


# ─────────────────────────────────────────────────────────────────────────────
# Fallback SOAP (used when LLM fails)
# ─────────────────────────────────────────────────────────────────────────────

def _build_fallback_soap(req: AgentRequest) -> dict:
    """
    Construct a basic SOAP note purely from form fields.
    Used when the LLM call fails — ensures the pipeline always continues.
    """
    severity_str = f"Reported severity: {req.severity}." if req.severity else ""
    duration_str = (
        f"Symptoms present for {req.duration_of_symptoms}."
        if req.duration_of_symptoms else ""
    )
    prior_str = (
        f"Prior treatment: {req.prior_treatment}."
        if req.prior_treatment else "No prior treatment documented."
    )
    inv_str = (
        f"Investigations: {req.investigations}."
        if req.investigations else "No investigations documented."
    )
    referral_str = (
        f"Specialist referral: {req.specialist_referral}."
        if req.specialist_referral else ""
    )
    meds_str = (
        f"Current medications: {req.medications}."
        if req.medications else "No medications reported."
    )

    return {
        "subjective": (
            f"{req.patient_name}, a {req.patient_age}-year-old {req.patient_gender.value}, "
            f"presents with the following: {req.disease_description}. "
            f"{duration_str} {severity_str}"
        ).strip(),
        "objective": (
            f"Patient {req.patient_age}yo {req.patient_gender.value}. "
            f"{inv_str} {meds_str} "
            f"Vital signs not documented in provided notes. "
            f"Further clinical examination findings pending."
        ).strip(),
        "assessment": (
            f"Clinical assessment based on presented symptoms: {req.disease_description[:200]}. "
            f"{prior_str} "
            f"Full diagnostic workup required to confirm primary diagnosis."
        ).strip(),
        "plan": (
            f"Continue current management. {meds_str} "
            f"{referral_str} "
            f"Follow-up as clinically indicated. "
            f"{'Procedure planned: ' + req.procedure if req.procedure else 'Procedure to be determined pending diagnosis confirmation.'}"
        ).strip(),
    }


# ─────────────────────────────────────────────────────────────────────────────
# Parser & Validator (Step 3)
# ─────────────────────────────────────────────────────────────────────────────

def _parse_soap_response(raw_json: str) -> dict:
    """
    Parse LLM JSON output and validate all 4 SOAP fields are present.
    Raises ValueError if malformed — triggers fallback in caller.
    """
    try:
        data = json.loads(raw_json)
    except json.JSONDecodeError as exc:
        raise ValueError(f"LLM returned invalid JSON: {exc}") from exc

    required = {"subjective", "objective", "assessment", "plan"}
    missing = required - set(data.keys())
    if missing:
        raise ValueError(f"LLM response missing SOAP fields: {missing}")

    # Ensure all fields are non-empty strings
    result = {}
    for field in required:
        value = str(data.get(field, "")).strip()
        if not value:
            raise ValueError(f"SOAP field '{field}' is empty in LLM response")
        result[field] = value

    return result


# ─────────────────────────────────────────────────────────────────────────────
# Public Entry Point — called by agent_service.py
# ─────────────────────────────────────────────────────────────────────────────

async def generate_soap_note(req: AgentRequest, steps: list) -> dict:
    """
    Steps 1–3: Generate a structured SOAP note from raw doctor input.

    Args:
        req   : Full AgentRequest from the frontend form
        steps : Mutable list — agent thought process log (shown on frontend right panel)

    Returns:
        dict with keys: subjective, objective, assessment, plan
    """
    steps.append("Step 1 ▶ Receiving and parsing raw clinical notes...")

    prompt = _build_soap_prompt(req)
    steps.append("Step 2 ▶ Sending clinical notes to LLM for SOAP structuring...")

    try:
        raw_output = await _call_groq(prompt)
        soap_data = _parse_soap_response(raw_output)
        steps.append(
            "Step 3 ✓ SOAP note generated — "
            f"Subjective ({len(soap_data['subjective'])} chars) | "
            f"Objective ({len(soap_data['objective'])} chars) | "
            f"Assessment ({len(soap_data['assessment'])} chars) | "
            f"Plan ({len(soap_data['plan'])} chars)"
        )
        logger.info(
            "SOAP generated for %s (%dy %s)",
            req.patient_name, req.patient_age, req.patient_gender.value,
        )
        return soap_data

    except EnvironmentError:
        raise   # Config errors bubble up — don't swallow

    except Exception as exc:
        logger.error("SOAP LLM call failed, using fallback: %s", exc)
        steps.append("Step 3 ⚠ LLM unavailable — SOAP generated from form fields (fallback)")
        return _build_fallback_soap(req)
