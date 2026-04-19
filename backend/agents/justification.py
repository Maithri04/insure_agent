"""
agents/justification.py

Pipeline Steps 9 – 13
──────────────────────
Step 9  — Combine SOAP note + evidence fields into justification context
Step 10 — Detect missing evidence items (driven by evidence_detector result)
Step 11 — If evidence missing, populate frontend checklist suggestions
Step 12 — Generate clinical justification letter via LLM (Groq)
Step 13 — Score justification (rule-based + LLM scoring)
           If score < 0.75 → rewrite with specific improvement instructions
           Max 2 iterations total (1 initial + 1 rewrite)
           Only accept rewrite if it genuinely improves the score

Design:
  • Scoring is hybrid: rule-based criteria check + LLM self-scoring
  • Rule-based scoring catches objective criteria (word count, key terms present,
    ICD mentioned, procedure mentioned, severity present, etc.)
  • LLM scoring acts as second opinion on clinical quality
  • Final score = 0.55 × rule_score + 0.45 × llm_score
  • Threshold: 0.75 — if below, one rewrite attempt is made
  • Fallback justification is always available if LLM is unreachable
"""

import os
import re
import json
import logging
from typing import List
from schemas.agent_schema import AgentRequest, EvidenceResult

logger = logging.getLogger(__name__)

# Score threshold below which a rewrite is triggered
JUSTIFICATION_THRESHOLD = 0.75
MAX_ITERATIONS = 2


# ─────────────────────────────────────────────────────────────────────────────
# LLM Helper — Lazy Groq Initialization
# ─────────────────────────────────────────────────────────────────────────────

async def _call_groq(prompt: str) -> str:
    """Lazy Groq client — never initialized at import time."""
    try:
        from groq import AsyncGroq
    except ImportError as exc:
        raise RuntimeError("groq not installed. Run: pip install groq") from exc

    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise EnvironmentError("GROQ_API_KEY is not set in environment.")

    client = AsyncGroq(api_key=api_key)
    response = await client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a senior medical reviewer and prior authorization specialist. "
                    "You write compelling clinical justification letters for insurance companies. "
                    "Always respond with valid JSON only."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        temperature=0.3,
        max_tokens=1200,
        response_format={"type": "json_object"},
    )
    return response.choices[0].message.content


# ─────────────────────────────────────────────────────────────────────────────
# Step 12: Generation Prompt
# ─────────────────────────────────────────────────────────────────────────────

def _build_generation_prompt(
    req: AgentRequest,
    soap: dict,
    icd_code: str,
    icd_description: str,
    procedure_code: str,
    procedure_description: str,
) -> str:
    return f"""Write a clinical justification letter for insurance prior authorization.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PATIENT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Name   : {req.patient_name}
Age    : {req.patient_age} years
Gender : {req.patient_gender.value}
TPA    : {req.tpa}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
DIAGNOSIS & PROCEDURE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ICD-10     : {icd_code} — {icd_description}
Procedure  : {procedure_code} — {procedure_description}
Medications: {req.medications or "None documented"}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SOAP NOTE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Subjective : {soap.get("subjective", "Not available")}
Objective  : {soap.get("objective", "Not available")}
Assessment : {soap.get("assessment", "Not available")}
Plan       : {soap.get("plan", "Not available")}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CLINICAL JUSTIFICATION EVIDENCE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Duration of symptoms  : {req.duration_of_symptoms or "Not provided"}
Prior treatment       : {req.prior_treatment or "Not documented"}
Severity              : {req.severity or "Not specified"}
Investigations / Labs : {req.investigations or "Not documented"}
Specialist referral   : {req.specialist_referral or "Not provided"}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
REQUIREMENTS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Write a clinical justification that:
1. Opens with a clear statement of medical necessity
2. References the specific diagnosis ({icd_code}) and why the procedure ({procedure_code}) is required
3. Incorporates all available evidence fields above
4. Uses professional clinical language for insurance reviewers
5. Mentions treatment history and why alternatives were insufficient (if prior treatment provided)
6. References investigations/lab results (if provided)
7. Closes with a statement of clinical urgency appropriate to the severity
8. Length: 180–260 words

Also self-score this justification from 0.0 to 1.0 based on:
  • Evidence completeness (are all fields referenced?)
  • Clinical specificity (concrete findings, measurements, ICD terminology)
  • Medical necessity language (clear statement of need)
  • Professional documentation quality

Return ONLY this JSON:
{{"justification": "Full text here...", "llm_score": 0.84}}"""


# ─────────────────────────────────────────────────────────────────────────────
# Step 13: Scoring Prompt (for rewrite decision)
# ─────────────────────────────────────────────────────────────────────────────

def _build_rewrite_prompt(
    current_text: str,
    current_score: float,
    weaknesses: List[str],
    icd_code: str,
    procedure_code: str,
) -> str:
    weakness_block = "\n".join(f"  • {w}" for w in weaknesses)
    return f"""The clinical justification below scored {current_score:.2f}/1.0, which is BELOW the required threshold of {JUSTIFICATION_THRESHOLD}.

CURRENT JUSTIFICATION:
───────────────────────────────────────────
{current_text}
───────────────────────────────────────────

IDENTIFIED WEAKNESSES:
{weakness_block}

REWRITE INSTRUCTIONS:
Produce a significantly improved version that addresses every weakness above. Requirements:
  1. Explicitly state medical necessity for {procedure_code} given diagnosis {icd_code}
  2. Add quantitative clinical data where the original was vague
  3. Reference evidence-based clinical guidelines or standard of care
  4. Use stronger medical necessity language: "medically indicated", "clinically essential",
     "evidence-based protocol requires", "failure of conservative management demonstrated by..."
  5. Ensure all available evidence (duration, prior treatment, severity, investigations,
     referral) is explicitly referenced and connected to the authorization request
  6. Target length: 220–280 words

Self-score the rewritten justification on the same 0.0–1.0 scale.

Return ONLY this JSON:
{{"justification": "Improved text here...", "llm_score": 0.88}}"""


# ─────────────────────────────────────────────────────────────────────────────
# Step 13: Rule-Based Scoring
# ─────────────────────────────────────────────────────────────────────────────

# Clinical keywords that indicate strong justification quality
_NECESSITY_PHRASES = [
    "medically necessary", "medically indicated", "clinically indicated",
    "medical necessity", "essential", "required", "standard of care",
    "evidence-based", "failure of conservative", "prior treatment",
    "clinical guidelines", "treatment protocol",
]
_URGENCY_PHRASES = [
    "urgent", "emergent", "immediate", "acute", "critical", "risk of",
    "life-threatening", "deteriorating", "worsening", "complications",
]


def _rule_based_score(
    text: str,
    icd_code: str,
    procedure_code: str,
    evidence: EvidenceResult,
) -> tuple[float, List[str]]:
    """
    Step 13: Score the justification text against objective rule-based criteria.

    Scoring breakdown (totals to 1.0):
      Length adequacy          0.10
      Medical necessity lang   0.20
      ICD code mentioned       0.10
      Procedure mentioned      0.10
      Evidence completeness    0.25  (0.05 per evidence field)
      Clinical urgency lang    0.10
      Specificity indicators   0.15

    Returns: (score: float, weaknesses: List[str])
    """
    text_lower = text.lower()
    words = len(text.split())
    score = 0.0
    weaknesses: List[str] = []

    # ── Length ────────────────────────────────
    if words >= 180:
        score += 0.10
    elif words >= 120:
        score += 0.05
        weaknesses.append(f"Justification is too short ({words} words). Target 180–260 words.")
    else:
        weaknesses.append(f"Critically short justification ({words} words). Needs substantial expansion.")

    # ── Medical necessity language ─────────────
    necessity_hits = sum(1 for p in _NECESSITY_PHRASES if p in text_lower)
    if necessity_hits >= 3:
        score += 0.20
    elif necessity_hits >= 1:
        score += 0.10
        weaknesses.append("Add stronger medical necessity language (e.g. 'medically indicated', 'standard of care requires').")
    else:
        weaknesses.append("Missing medical necessity language entirely — must explicitly state clinical need.")

    # ── ICD code referenced ───────────────────
    if icd_code.lower() in text_lower or icd_code.replace(".", "").lower() in text_lower:
        score += 0.10
    else:
        weaknesses.append(f"ICD-10 code {icd_code} not explicitly referenced in justification.")

    # ── Procedure referenced ──────────────────
    if procedure_code.lower() in text_lower:
        score += 0.10
    else:
        # Partial credit if a procedure keyword is mentioned
        if any(kw in text_lower for kw in ["procedure", "surgery", "operation", "therapy", "treatment"]):
            score += 0.05
        else:
            weaknesses.append(f"Procedure code {procedure_code} or procedure description not referenced.")

    # ── Evidence field coverage ───────────────
    evidence_checks = [
        ("duration",       ["duration", "week", "month", "year", "day", "since"]),
        ("prior treatment",["prior treatment", "previous treatment", "conservative", "failed", "tried", "medications"]),
        ("severity",       ["severe", "high", "moderate", "critical", "significant", "serious"]),
        ("investigations", ["investigation", "lab", "test", "ecg", "mri", "ct scan", "x-ray", "biopsy", "result"]),
        ("referral",       ["referral", "specialist", "referred", "consultant", "cardiologist", "oncologist"]),
    ]
    evidence_score_per_item = 0.05
    for label, keywords in evidence_checks:
        if any(kw in text_lower for kw in keywords):
            score += evidence_score_per_item
        else:
            weaknesses.append(f"Evidence field '{label}' not adequately addressed in justification.")

    # ── Clinical urgency language ─────────────
    urgency_hits = sum(1 for p in _URGENCY_PHRASES if p in text_lower)
    if urgency_hits >= 2:
        score += 0.10
    elif urgency_hits == 1:
        score += 0.05
        weaknesses.append("Strengthen clinical urgency — reference specific risks of delaying treatment.")

    # ── Specificity (numbers, measurements) ───
    has_numbers = bool(re.search(r'\d+', text))
    has_measurements = bool(re.search(
        r'\b\d+\s*(mg|ml|mmhg|bpm|kg|years?|months?|weeks?|days?|%)\b', text_lower
    ))
    if has_numbers and has_measurements:
        score += 0.15
    elif has_numbers:
        score += 0.08
        weaknesses.append("Add specific clinical measurements (e.g. dosages, lab values, duration in numbers).")
    else:
        weaknesses.append("Lacks specific quantitative data — add measurements, lab values, or clinical metrics.")

    return round(min(1.0, score), 3), weaknesses


# ─────────────────────────────────────────────────────────────────────────────
# Fallback Justification
# ─────────────────────────────────────────────────────────────────────────────

def _build_fallback_justification(
    req: AgentRequest,
    icd_code: str,
    icd_description: str,
    procedure_code: str,
    procedure_description: str,
) -> str:
    """
    Constructs a basic clinical justification from form fields alone.
    Used when the LLM is unavailable. Score will be approximately 0.40–0.55.
    """
    parts = [
        f"This letter is to request prior authorization for {req.patient_name}, "
        f"a {req.patient_age}-year-old {req.patient_gender.value} patient "
        f"presenting under TPA {req.tpa}.",
        "",
        f"The patient has been diagnosed with {icd_description} (ICD-10: {icd_code}), "
        f"for which {procedure_description} (Procedure: {procedure_code}) has been deemed medically necessary.",
        "",
    ]

    if req.duration_of_symptoms:
        parts.append(
            f"The patient has been experiencing symptoms for {req.duration_of_symptoms}, "
            "establishing a chronic or persistent clinical course requiring intervention."
        )
    if req.severity:
        parts.append(
            f"Symptom severity has been assessed as {req.severity}, "
            "significantly impacting the patient's quality of life and functional capacity."
        )
    if req.prior_treatment:
        parts.append(
            f"Prior treatment has been attempted ({req.prior_treatment}); "
            "however, the patient's condition has not responded adequately to conservative management, "
            "necessitating escalation of care."
        )
    if req.investigations:
        parts.append(
            f"Clinical investigations have been conducted: {req.investigations}. "
            "Findings support the medical necessity of the requested procedure."
        )
    if req.specialist_referral:
        parts.append(
            f"Specialist evaluation has been obtained ({req.specialist_referral}), "
            "corroborating the clinical decision for the requested intervention."
        )
    if req.medications:
        parts.append(
            f"Current medication regimen includes: {req.medications}. "
            "Pharmacological management alone has proven insufficient."
        )

    parts.append(
        "\nBased on the above clinical evidence, we respectfully request authorization "
        f"for {procedure_description}. We believe this intervention is medically indicated, "
        "clinically appropriate, and consistent with the standard of care for this diagnosis. "
        "All supporting documentation is available upon request."
    )

    return "\n".join(parts)


# ─────────────────────────────────────────────────────────────────────────────
# Public Entry Point — called by agent_service.py
# ─────────────────────────────────────────────────────────────────────────────

async def generate_and_score_justification(
    req: AgentRequest,
    soap: dict,
    icd_code: str,
    icd_description: str,
    procedure_code: str,
    procedure_description: str,
    evidence: EvidenceResult,
    steps: list,
) -> dict:
    """
    Steps 12–13: Generate clinical justification, score it (hybrid),
    and rewrite if score < 0.75 (max 2 iterations total).

    Scoring method:
      final_score = 0.55 × rule_score + 0.45 × llm_score

    Returns dict with:
      text         : Final justification text
      score        : Final hybrid score (0.0–1.0)
      iterations   : Number of LLM calls (1 or 2)
      is_sufficient: True if score >= 0.75
    """
    steps.append("Step 12 ▶ Generating clinical justification via LLM...")

    text       = ""
    rule_score = 0.0
    llm_score  = 0.0
    final_score = 0.0
    iterations  = 0

    try:
        # ── Iteration 1: Initial Generation ────────────────────────────────
        gen_prompt = _build_generation_prompt(
            req, soap, icd_code, icd_description, procedure_code, procedure_description
        )
        raw = await _call_groq(gen_prompt)
        data = json.loads(raw)

        text      = str(data.get("justification", "")).strip()
        llm_score = float(data.get("llm_score", 0.5))
        iterations = 1

        rule_score, weaknesses = _rule_based_score(text, icd_code, procedure_code, evidence)
        final_score = round((0.55 * rule_score) + (0.45 * llm_score), 3)

        steps.append(
            f"Step 12 ✓ Initial justification — "
            f"Rule score: {rule_score:.2f} | LLM score: {llm_score:.2f} | "
            f"Final: {final_score:.2f} | Words: {len(text.split())}"
        )

        # ── Iteration 2: Rewrite if below threshold ──────────────────────
        if final_score < JUSTIFICATION_THRESHOLD and text:
            steps.append(
                f"Step 13 ▶ Score {final_score:.2f} below threshold {JUSTIFICATION_THRESHOLD} "
                f"— rewriting justification ({len(weaknesses)} weaknesses identified)..."
            )

            rewrite_prompt = _build_rewrite_prompt(
                current_text=text,
                current_score=final_score,
                weaknesses=weaknesses,
                icd_code=icd_code,
                procedure_code=procedure_code,
            )
            raw2 = await _call_groq(rewrite_prompt)
            data2 = json.loads(raw2)

            new_text      = str(data2.get("justification", text)).strip()
            new_llm_score = float(data2.get("llm_score", llm_score))

            new_rule_score, _ = _rule_based_score(new_text, icd_code, procedure_code, evidence)
            new_final_score   = round((0.55 * new_rule_score) + (0.45 * new_llm_score), 3)

            # Only accept rewrite if it genuinely improved the score
            if new_final_score > final_score and new_text:
                text        = new_text
                rule_score  = new_rule_score
                llm_score   = new_llm_score
                final_score = new_final_score
                steps.append(
                    f"Step 13 ✓ Rewrite improved score: {final_score:.2f} "
                    f"(Rule: {rule_score:.2f} | LLM: {llm_score:.2f}) | Words: {len(text.split())}"
                )
            else:
                steps.append(
                    f"Step 13 ⚠ Rewrite did not improve score "
                    f"({new_final_score:.2f} ≤ {final_score:.2f}) — keeping original"
                )

            iterations = 2
        else:
            steps.append(
                f"Step 13 ✓ Score {final_score:.2f} meets threshold — no rewrite needed"
            )

    except EnvironmentError:
        raise   # Config errors bubble up

    except Exception as exc:
        logger.error("Justification LLM error: %s — using fallback", exc)
        steps.append("Step 12 ⚠ LLM unavailable — building justification from form fields (fallback)")

        text = _build_fallback_justification(
            req, icd_code, icd_description, procedure_code, procedure_description
        )
        rule_score, _ = _rule_based_score(text, icd_code, procedure_code, evidence)
        llm_score   = 0.40   # Conservative fallback assumption
        final_score = round((0.55 * rule_score) + (0.45 * llm_score), 3)
        iterations  = 1

        steps.append(
            f"Step 13 ✓ Fallback justification scored: {final_score:.2f}"
        )

    return {
        "text":         text,
        "score":        round(min(1.0, max(0.0, final_score)), 3),
        "iterations":   iterations,
        "is_sufficient": final_score >= JUSTIFICATION_THRESHOLD,
    }