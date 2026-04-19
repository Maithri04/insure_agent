"""
agents/evidence_detector.py

Responsibilities:
  Step 9  — Extract evidence from the 5 frontend Clinical Justification fields
  Step 10 — Detect missing evidence, generate Missing Evidence Checklist
  Step 11 — Return suggestions for each missing item
  Step 12 — Generate clinical justification via LLM
  Step 13 — Score justification; if score < 0.75, rewrite (max 2 iterations)
"""

import os
import json
import logging
from typing import List

from schemas.agent_schema import (
    AgentRequest, EvidenceItem, EvidenceResult, SeverityEnum
)

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────
# Evidence Field Definitions
# Maps frontend form field → label in Missing Evidence Checklist
# ─────────────────────────────────────────────

EVIDENCE_FIELDS = [
    ("duration_of_symptoms", "Duration"),
    ("prior_treatment",      "Prior treatment"),
    ("severity",             "Severity"),
    ("investigations",       "Investigations"),
    ("specialist_referral",  "Referral"),
]

# These values are treated as "not provided"
EMPTY_VALUES = {
    "", "none", "no", "nothing", "n/a", "na",
    "not provided", "unknown", "nil", "nill", "-",
}


def _is_present(value: str | None) -> bool:
    """Return True if the field has meaningful content."""
    if not value:
        return False
    return value.strip().lower() not in EMPTY_VALUES


# ─────────────────────────────────────────────
# Step 9-11: Evidence Check
# ─────────────────────────────────────────────

def check_evidence(req: AgentRequest) -> EvidenceResult:
    """
    Steps 9–11: Check the 5 Clinical Justification fields from the frontend form.
    Returns EvidenceResult that directly drives the Missing Evidence Checklist panel.

    Checklist items: Duration, Prior treatment, Severity, Investigations, Referral
    """
    items: List[EvidenceItem] = []
    missing_labels: List[str] = []

    for field_name, label in EVIDENCE_FIELDS:
        value = getattr(req, field_name, None)
        present = _is_present(value)

        items.append(EvidenceItem(
            label=label,
            is_present=present,
            value=value.strip() if present and value else None,
        ))

        if not present:
            missing_labels.append(label)

    present_count = sum(1 for item in items if item.is_present)
    completeness_score = round(present_count / len(EVIDENCE_FIELDS), 2)

    suggestions = _build_suggestions(missing_labels)

    return EvidenceResult(
        items=items,
        missing_labels=missing_labels,
        completeness_score=completeness_score,
        suggestions=suggestions,
    )


def _build_suggestions(missing: List[str]) -> List[str]:
    """Step 11: Build actionable suggestions for each missing evidence field."""
    tip_map = {
        "Duration":        "Specify how long symptoms have been present (e.g. '3 weeks', '6 months', '1 year').",
        "Prior treatment": "Describe previous treatments tried and their outcomes (e.g. medications, physiotherapy).",
        "Severity":        "Indicate severity level (mild / moderate / high) and describe functional impact on daily activities.",
        "Investigations":  "Include lab results, imaging reports, or diagnostic test findings (e.g. ECG, X-ray, blood work).",
        "Referral":        "Specify if specialist referral was obtained, pending, or attempted, and the specialist's name/specialty.",
    }
    return [tip_map[m] for m in missing if m in tip_map]


# ─────────────────────────────────────────────
# LLM Helper — Lazy Groq Initialization
# ─────────────────────────────────────────────

async def _call_llm(prompt: str) -> str:
    """Lazy Groq client — never initialized at import time."""
    try:
        from groq import AsyncGroq
    except ImportError as e:
        raise RuntimeError("groq not installed") from e

    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise EnvironmentError("GROQ_API_KEY is not set")

    client = AsyncGroq(api_key=api_key)
    response = await client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
        max_tokens=1024,
        response_format={"type": "json_object"},
    )
    return response.choices[0].message.content


# ─────────────────────────────────────────────
# Justification Prompts
# ─────────────────────────────────────────────

_JUSTIFICATION_PROMPT = """You are a senior medical reviewer writing a clinical justification letter for insurance prior authorization.

PATIENT: {patient_name}, {patient_age}yo {patient_gender}
TPA / PAYER: {tpa}
DIAGNOSIS: {icd_code} — {icd_description}
PROCEDURE: {procedure_code} — {procedure_description}

SOAP NOTE:
  Subjective : {subjective}
  Objective  : {objective}
  Assessment : {assessment}
  Plan       : {plan}

CLINICAL JUSTIFICATION FIELDS:
  Duration of symptoms : {duration}
  Prior treatment      : {prior_treatment}
  Severity             : {severity}
  Investigations       : {investigations}
  Specialist referral  : {referral}
  Medications          : {medications}

Write a compelling, medically accurate clinical justification (150–250 words) that:
1. Establishes medical necessity clearly
2. References the clinical evidence provided
3. Uses professional clinical language appropriate for insurance reviewers
4. Explains why the requested procedure is required and appropriate

Return ONLY this JSON:
{{"justification": "Full justification text here...", "score": 0.82}}

Where score (0.0–1.0) reflects: evidence completeness, clinical urgency, specificity, and documentation quality."""


_REWRITE_PROMPT = """The clinical justification below scored {score:.2f}/1.0, which is below the required threshold of 0.75.

ORIGINAL JUSTIFICATION:
{current_text}

IDENTIFIED WEAKNESSES:
{weaknesses}

Rewrite it to be significantly stronger. Improvements needed:
- Add clinical specificity and quantitative findings where possible
- Strengthen medical necessity language
- Reference evidence-based guidelines or standard of care
- Address the identified weaknesses
Target length: 200–280 words.

Return ONLY this JSON:
{{"justification": "Improved justification here...", "score": 0.88}}"""


# ─────────────────────────────────────────────
# Step 12-13: Justification Generation + Scoring + Rewrite
# ─────────────────────────────────────────────

def _identify_weaknesses(score: float, evidence: EvidenceResult, missing: List[str]) -> str:
    """Build a weakness description for the rewrite prompt."""
    issues = []
    if missing:
        issues.append(f"Missing clinical evidence fields: {', '.join(missing)}")
    if score < 0.60:
        issues.append("Lacks specific clinical findings, measurements, and test results")
        issues.append("Insufficient medical necessity language and urgency")
    elif score < 0.75:
        issues.append("Needs stronger evidence-based justification with concrete data points")
    if evidence.completeness_score < 0.6:
        issues.append("Evidence is too sparse to support strong authorization")
    return " | ".join(issues) if issues else "General improvement needed for clarity and specificity"


async def generate_and_score_justification(
    req: AgentRequest,
    soap: dict,
    icd_code: str,
    icd_description: str,
    procedure_code: str,
    procedure_description: str,
    evidence: EvidenceResult,
) -> dict:
    """
    Steps 12–13: Generate clinical justification via LLM.
    Score it. If score < 0.75, rewrite once (max 2 total iterations).
    """
    SCORE_THRESHOLD = 0.75

    prompt = _JUSTIFICATION_PROMPT.format(
        patient_name=req.patient_name,
        patient_age=req.patient_age,
        patient_gender=req.patient_gender.value,
        tpa=req.tpa,
        icd_code=icd_code,
        icd_description=icd_description,
        procedure_code=procedure_code,
        procedure_description=procedure_description,
        subjective=soap.get("subjective", "Not available"),
        objective=soap.get("objective", "Not available"),
        assessment=soap.get("assessment", "Not available"),
        plan=soap.get("plan", "Not available"),
        duration=req.duration_of_symptoms or "Not provided",
        prior_treatment=req.prior_treatment or "Not provided",
        severity=req.severity or "Not provided",
        investigations=req.investigations or "Not provided",
        referral=req.specialist_referral or "Not provided",
        medications=req.medications or "None",
    )

    text = ""
    score = 0.0
    iterations = 0

    try:
        # Iteration 1: Initial generation
        raw = await _call_llm(prompt)
        data = json.loads(raw)
        text = str(data.get("justification", "")).strip()
        score = float(data.get("score", 0.5))
        iterations = 1

        # Iteration 2: Rewrite if below threshold
        if score < SCORE_THRESHOLD and text:
            weaknesses = _identify_weaknesses(score, evidence, evidence.missing_labels)
            rewrite_prompt = _REWRITE_PROMPT.format(
                score=score,
                current_text=text,
                weaknesses=weaknesses,
            )
            raw2 = await _call_llm(rewrite_prompt)
            data2 = json.loads(raw2)
            new_text = str(data2.get("justification", text)).strip()
            new_score = float(data2.get("score", score))

            # Only accept the rewrite if it actually improved
            if new_score > score and new_text:
                text = new_text
                score = new_score
            iterations = 2

    except Exception as e:
        logger.error("Justification generation failed: %s", e)
        # Fallback justification
        text = (
            f"Clinical justification for patient {req.patient_name}, {req.patient_age}yo {req.patient_gender.value}. "
            f"Diagnosis: {icd_description} ({icd_code}). "
            f"Procedure requested: {procedure_description} ({procedure_code}). "
            f"Symptoms present for {req.duration_of_symptoms or 'unspecified duration'}. "
            f"Prior treatment: {req.prior_treatment or 'not documented'}. "
            f"Severity: {req.severity or 'not specified'}. "
            "Medical necessity is established based on clinical findings. "
            "Further documentation available upon request."
        )
        score = 0.45
        iterations = 1

    return {
        "text": text,
        "score": round(min(1.0, max(0.0, score)), 3),
        "iterations": iterations,
        "is_sufficient": score >= SCORE_THRESHOLD,
    }