"""
agents/agent_service.py

Master orchestrator — executes all 20 steps of the InsureMind agent pipeline.

Steps:
  1–3   SOAP generation from raw disease description
  4     Predict ICD-10 code (LLM)
  5     Validate ICD code against PostgreSQL
  6     Correct invalid ICD — find closest match
  7     Map ICD to procedure (if not provided)
  8     Check diagnosis-procedure conflicts (rule engine)
  9–11  Extract evidence from 5 frontend fields → Missing Evidence Checklist
  12–13 Generate + score justification → rewrite if score < 0.75 (max 2 iterations)
  14    Analyze risk flags (high / medium / low)
  15    Classify condition type (minor / moderate / serious / critical)
  16    Apply condition-based approval modifier
  17–18 Calculate approval probability (weighted scoring model)
  19    Generate explainable output (reasons + suggestions)
  20    Compose final response + save audit log to MongoDB
"""

import uuid
import logging
import os
import json
from datetime import datetime, timezone
from typing import List, Tuple

from schemas.agent_schema import (
    AgentRequest, AgentResponse,
    SOAPNote, ICDResult, ProcedureResult,
    ConflictItem, EvidenceResult,
    JustificationResult, RiskFlag,
    ApprovalBreakdown, SeverityEnum, PatientDetails,
)
from agents.icd_mapper import (
    predict_icd_code,
    validate_icd_in_db,
    find_closest_icd,
    map_icd_to_procedure,
    check_conflicts_in_db,
)
from agents.evidence_detector import (
    check_evidence,
    generate_and_score_justification,
)

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────
# Steps 1–3: SOAP Generation
# ─────────────────────────────────────────────

_SOAP_PROMPT = """You are a clinical physician. Convert the patient information below into a structured SOAP note.
Write clean, accurate, and VERY concise sentences. The values MUST be simple, flat text strings (do NOT use nested JSON objects or arrays).

PATIENT : {name}, {age}yo {gender}
TPA     : {tpa}
MEDS    : {meds}
NOTES   : {desc}

Return ONLY this exact JSON (no extra text):
{{
  "subjective": "Patient-reported symptoms, history, chief complaint...",
  "objective": "Vital signs, physical exam findings, clinical observations...",
  "assessment": "Primary diagnosis, differential diagnoses, clinical reasoning...",
  "plan": "Treatment plan, medications, referrals, follow-up instructions..."
}}"""


async def _generate_soap(req: AgentRequest, steps: List[str]) -> dict:
    """Steps 1–3: Generate SOAP note via Groq LLM."""
    steps.append("Step 1 ▶ Parsing raw clinical notes with LLM...")

    try:
        from groq import AsyncGroq
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise EnvironmentError("GROQ_API_KEY not set")

        client = AsyncGroq(api_key=api_key)
        prompt = _SOAP_PROMPT.format(
            name=req.patient_name,
            age=req.patient_age,
            gender=req.patient_gender.value,
            tpa=req.tpa,
            meds=req.medications or "None reported",
            desc=req.disease_description,
        )
        response = await client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            max_tokens=800,
            response_format={"type": "json_object"},
        )
        data = json.loads(response.choices[0].message.content)
        steps.append("Step 2 ✓ SOAP note structured successfully")
        
        def _ensure_str(val):
            if isinstance(val, dict):
                return "; ".join(f"{v}" for v in val.values() if v)
            if isinstance(val, list):
                return "; ".join(f"{v}" for v in val if v)
            return str(val).strip() if val else ""
            
        return {
            "subjective": _ensure_str(data.get("subjective")),
            "objective":  _ensure_str(data.get("objective")),
            "assessment": _ensure_str(data.get("assessment")),
            "plan":       _ensure_str(data.get("plan")),
        }
    except Exception as e:
        logger.error("SOAP generation error: %s", e)
        steps.append("Step 2 ⚠ SOAP generation failed — using fallback")
        return {
            "subjective": req.disease_description,
            "objective":  "Clinical examination findings pending documentation.",
            "assessment": f"Assessment based on described symptoms: {req.disease_description[:120]}",
            "plan":       "Further evaluation and treatment as clinically indicated.",
        }


# ─────────────────────────────────────────────
# Steps 14–15: Risk Flag Analysis
# ─────────────────────────────────────────────

def _analyze_risk_flags(
    req: AgentRequest,
    icd_code: str,
    raw_conflicts: list,
    evidence: EvidenceResult,
    condition_type: str,
    steps: List[str],
) -> List[RiskFlag]:
    """Steps 14–15: Identify clinical and administrative risk flags."""
    steps.append("Step 8 ▶ Analyzing risk flags...")
    flags: List[RiskFlag] = []

    # ── Conflict-based flags ──────────────────
    for c in raw_conflicts:
        flags.append(RiskFlag(
            flag=f"Conflict: {c['rule_name']}",
            severity=SeverityEnum(c.get("severity", "medium")),
            description=c.get("description", "Diagnosis-procedure conflict detected"),
        ))

    # ── Patient age risk ──────────────────────
    if req.patient_age >= 65:
        flags.append(RiskFlag(
            flag="Elderly patient (≥65 years)",
            severity=SeverityEnum.medium,
            description="Elderly patients carry increased surgical/procedural risk. Enhanced documentation and specialist sign-off recommended.",
        ))
    elif req.patient_age <= 12:
        flags.append(RiskFlag(
            flag="Pediatric patient (≤12 years)",
            severity=SeverityEnum.medium,
            description="Pediatric-specific dosing, consent requirements, and clinical criteria apply.",
        ))

    # ── Documentation completeness risk ───────
    if evidence.completeness_score < 0.4:
        flags.append(RiskFlag(
            flag="Critical documentation gap",
            severity=SeverityEnum.high,
            description=f"Only {evidence.completeness_score:.0%} of required evidence fields completed. "
                        f"Missing: {', '.join(evidence.missing_labels)}. Very high denial risk.",
        ))
    elif evidence.completeness_score < 0.8:
        flags.append(RiskFlag(
            flag="Incomplete clinical evidence",
            severity=SeverityEnum.medium,
            description=f"Missing evidence: {', '.join(evidence.missing_labels)}. May negatively affect approval decision.",
        ))

    # ── High-acuity ICD code risk ─────────────
    HIGH_RISK_PREFIXES = ("I2", "I5", "I6", "C", "J96", "K92", "N17", "N18", "G35", "G20")
    if any(icd_code.startswith(p) for p in HIGH_RISK_PREFIXES):
        flags.append(RiskFlag(
            flag="High-acuity diagnosis",
            severity=SeverityEnum.high,
            description=f"ICD-10 {icd_code} indicates a serious/complex medical condition. "
                        "Comprehensive supporting documentation is critical for authorization.",
        ))

    # ── Missing specialist referral for serious/critical ──
    if condition_type in ("serious", "critical"):
        referral_item = next((i for i in evidence.items if i.label == "Referral"), None)
        if referral_item and not referral_item.is_present:
            flags.append(RiskFlag(
                flag="No specialist referral documented",
                severity=SeverityEnum.medium,
                description="Serious conditions typically require specialist involvement for insurance authorization.",
            ))

    # ── No investigations for non-minor conditions ──
    if condition_type != "minor":
        inv_item = next((i for i in evidence.items if i.label == "Investigations"), None)
        if inv_item and not inv_item.is_present:
            flags.append(RiskFlag(
                flag="No diagnostic investigations documented",
                severity=SeverityEnum.medium,
                description="Lab results, imaging, or diagnostic test data are expected for this condition type.",
            ))

    steps.append(f"Step 9 ✓ Identified {len(flags)} risk flag(s)")
    return flags


# ─────────────────────────────────────────────
# Step 15–16: Condition Classification
# ─────────────────────────────────────────────

def _classify_condition(
    icd_code: str,
    severity_input: str | None,
    icd_db_severity: str | None,
) -> str:
    """
    Step 15: Classify condition as minor / moderate / serious / critical.
    Priority order: DB severity > ICD prefix rules > user severity input.
    """
    # Use DB severity if available and valid
    db_sev = (icd_db_severity or "").lower()
    if db_sev in ("critical", "serious", "moderate", "minor"):
        return db_sev

    # ICD prefix-based classification
    CRITICAL_PREFIXES = ("I21", "I22", "I46", "J96", "R09", "S06", "T71", "I63", "I64")
    SERIOUS_PREFIXES  = ("I", "C", "J18", "J44", "J45", "N17", "N18", "K92", "G35", "G20", "G43")
    MODERATE_PREFIXES = ("M", "K2", "K3", "K4", "K5", "K6", "K7", "N", "G4", "E1", "E0", "H")

    if any(icd_code.startswith(p) for p in CRITICAL_PREFIXES):
        return "critical"
    if any(icd_code.startswith(p) for p in SERIOUS_PREFIXES):
        return "serious"
    if any(icd_code.startswith(p) for p in MODERATE_PREFIXES):
        return "moderate"

    # Last resort: use user-input severity field
    sev = (severity_input or "").lower()
    if sev in ("high", "critical", "severe"):
        return "serious"
    if sev == "moderate":
        return "moderate"

    return "minor"


# ─────────────────────────────────────────────
# Steps 17–18: Approval Probability Model
# ─────────────────────────────────────────────

def _calculate_approval_probability(
    evidence: EvidenceResult,
    justification_score: float,
    raw_conflicts: list,
    risk_flags: List[RiskFlag],
    condition_type: str,
    steps: List[str],
) -> Tuple[float, ApprovalBreakdown, str]:
    """
    Steps 17–18: Weighted scoring model for approval probability.

    Formula:
      base = (evidence × 0.35) + (justification × 0.40)
            + severity_bonus − conflict_penalty − risk_penalty

    Recommendation thresholds:
      ≥ 0.80 → APPROVED
      ≥ 0.65 → LIKELY APPROVED
      ≥ 0.50 → NEEDS REVIEW
      ≥ 0.35 → LIKELY DENIED
       < 0.35 → DENIED
    """
    steps.append("Step 10 ▶ Calculating approval probability...")

    evidence_score = evidence.completeness_score      # 0.0 – 1.0
    just_score     = justification_score              # 0.0 – 1.0

    # Step 16: Severity modifier
    # Minor conditions have a lower baseline (mild fever = lower medical necessity)
    # Serious/critical conditions get a bonus (cardiac surgery = clear necessity)
    severity_bonus_map = {
        "minor":    -0.12,
        "moderate":  0.00,
        "serious":   0.08,
        "critical":  0.13,
    }
    severity_bonus = severity_bonus_map.get(condition_type, 0.0)

    # Conflict penalty
    high_conflicts = sum(1 for c in raw_conflicts if c.get("severity") == "high")
    med_conflicts  = sum(1 for c in raw_conflicts if c.get("severity") == "medium")
    conflict_penalty = min(0.35, (high_conflicts * 0.13) + (med_conflicts * 0.05))

    # Risk flag penalty
    high_risks = sum(
        1 for r in risk_flags
        if r.severity in (SeverityEnum.high, SeverityEnum.critical)
    )
    risk_penalty = min(0.20, high_risks * 0.07)

    # Final weighted score
    raw_score = (
        (evidence_score * 0.35)
        + (just_score * 0.40)
        + severity_bonus
        - conflict_penalty
        - risk_penalty
    )
    probability = round(max(0.04, min(0.98, raw_score)), 3)

    # Recommendation label
    if probability >= 0.80:
        recommendation = "APPROVED"
    elif probability >= 0.65:
        recommendation = "LIKELY APPROVED"
    elif probability >= 0.50:
        recommendation = "NEEDS REVIEW"
    elif probability >= 0.35:
        recommendation = "LIKELY DENIED"
    else:
        recommendation = "DENIED"

    breakdown = ApprovalBreakdown(
        evidence_score=round(evidence_score, 3),
        justification_score=round(just_score, 3),
        severity_bonus=round(severity_bonus, 3),
        conflict_penalty=round(conflict_penalty, 3),
        risk_penalty=round(risk_penalty, 3),
    )

    steps.append(
        f"Step 11 ✓ Approval probability: {probability:.1%} → {recommendation}"
    )
    return probability, breakdown, recommendation


# ─────────────────────────────────────────────
# Steps 19: Explainability
# ─────────────────────────────────────────────

def _generate_explainability(
    probability: float,
    recommendation: str,
    raw_conflicts: list,
    evidence: EvidenceResult,
    risk_flags: List[RiskFlag],
    condition_type: str,
    justification_score: float,
) -> Tuple[List[str], List[str]]:
    """Step 19: Generate human-readable reasons and improvement suggestions."""
    reasons: List[str] = []
    suggestions: List[str] = []

    # Evidence reasons
    if evidence.completeness_score >= 0.8:
        reasons.append(f"Strong clinical evidence provided ({evidence.completeness_score:.0%} complete).")
    elif evidence.completeness_score >= 0.6:
        reasons.append(f"Partial clinical evidence ({evidence.completeness_score:.0%} complete) — some fields missing.")
    else:
        reasons.append(f"Insufficient clinical evidence ({evidence.completeness_score:.0%} complete) — most fields missing.")

    # Justification reasons
    if justification_score >= 0.75:
        reasons.append("Clinical justification meets documentation quality standards.")
    else:
        reasons.append(f"Clinical justification quality is below threshold (score: {justification_score:.2f}/1.00).")

    # Conflict reasons
    if raw_conflicts:
        deny_conflicts = [c for c in raw_conflicts if c.get("action") == "deny"]
        if deny_conflicts:
            reasons.append(f"{len(deny_conflicts)} conflict(s) marked for DENIAL: {deny_conflicts[0]['rule_name']}.")
        else:
            reasons.append(f"{len(raw_conflicts)} diagnosis-procedure conflict(s) flagged for review.")

    # Condition severity reason
    severity_reasons = {
        "critical": "Critical condition — strong medical necessity supports authorization.",
        "serious":  "Serious medical condition documented — supports approval decision.",
        "moderate": "Moderate condition — standard authorization review applies.",
        "minor":    "Minor condition — higher evidence burden required for approval.",
    }
    reasons.append(severity_reasons.get(condition_type, "Condition severity could not be determined."))

    # High-severity risk flag reasons
    high_flags = [r.flag for r in risk_flags if r.severity in (SeverityEnum.high, SeverityEnum.critical)]
    if high_flags:
        reasons.append(f"High-severity risk flags detected: {'; '.join(high_flags[:2])}.")

    # Suggestions from evidence
    suggestions.extend(evidence.suggestions)

    if justification_score < 0.75:
        suggestions.append("Improve clinical justification with specific lab values, measurements, and test results.")
    if raw_conflicts:
        suggestions.append("Review and resolve diagnosis-procedure conflicts before resubmission.")
    if probability < 0.50:
        suggestions.append("Consider specialist consultation and additional diagnostic workup to strengthen the case.")
    if evidence.completeness_score < 0.6:
        suggestions.append("Complete all Clinical Justification fields for significantly better approval odds.")

    return [r for r in reasons if r], suggestions


# ─────────────────────────────────────────────
# Main Pipeline — All 20 Steps
# ─────────────────────────────────────────────

async def run_agent(req: AgentRequest, pg_pool, mongo_db) -> AgentResponse:
    """
    Entry point for the full 20-step InsureMind agent pipeline.
    Called by POST /agent/verify and POST /agent/submit.
    """
    request_id  = str(uuid.uuid4())
    timestamp   = datetime.now(timezone.utc).isoformat()
    start_time  = datetime.now(timezone.utc)
    steps: List[str] = []

    steps.append(f"🤖 InsureMind Agent initialized | Request: {request_id[:8]}...")

    # ── Steps 1–3: SOAP ────────────────────────────────────────────────────
    soap_data = await _generate_soap(req, steps)
    soap_note = SOAPNote(**soap_data)

    # ── Step 4: Predict ICD-10 ─────────────────────────────────────────────
    steps.append("Step 3 ▶ Predicting ICD-10 code via LLM...")
    predicted = await predict_icd_code(
        disease_description=req.disease_description,
        assessment=soap_data.get("assessment", ""),
        patient_age=req.patient_age,
        patient_gender=req.patient_gender.value,
    )

    # ── Step 5: Validate ICD in PostgreSQL ────────────────────────────────
    steps.append(f"Step 4 ▶ Validating ICD {predicted['code']} in database...")
    db_icd = await validate_icd_in_db(predicted["code"], pg_pool)

    was_corrected   = False
    original_code   = None
    icd_db_severity = None

    if db_icd:
        final_code  = db_icd["code"]
        final_desc  = db_icd["description"]
        icd_db_severity = db_icd.get("severity")
        is_validated = True
        steps.append(f"Step 5 ✓ ICD {final_code} validated in database")
    else:
        # ── Step 6: Find closest match ────────────────────────────────────
        steps.append(f"Step 5 ▶ ICD {predicted['code']} not found — searching for closest match...")
        original_code = predicted["code"]
        closest = await find_closest_icd(predicted["code"], predicted["description"], pg_pool)
        if closest:
            final_code  = closest["code"]
            final_desc  = closest["description"]
            icd_db_severity = closest.get("severity")
            was_corrected = True
            is_validated  = True
            steps.append(f"Step 6 ✓ Corrected to closest match: {final_code} — {final_desc}")
        else:
            final_code   = predicted["code"]
            final_desc   = predicted["description"]
            is_validated = False
            steps.append(f"Step 6 ⚠ No DB match found — using LLM prediction: {final_code}")

    icd_result = ICDResult(
        code=final_code,
        description=final_desc,
        is_validated=is_validated,
        was_corrected=was_corrected,
        original_predicted_code=original_code,
        confidence=predicted["confidence"],
    )

    # ── Step 7: Map ICD to Procedure ───────────────────────────────────────
    steps.append("Step 7 ▶ Mapping diagnosis to procedure code...")
    if req.procedure and req.procedure.strip():
        proc_code   = req.procedure.strip()
        proc_desc   = req.procedure.strip()
        proc_source = "provided"
        steps.append(f"Step 7 ✓ Using provided procedure: {proc_code}")
    else:
        mapped = await map_icd_to_procedure(final_code, pg_pool)
        if mapped:
            proc_code   = mapped["code"]
            proc_desc   = mapped["description"]
            proc_source = "mapped_from_icd"
            steps.append(f"Step 7 ✓ Mapped procedure from ICD: {proc_code} — {proc_desc}")
        else:
            proc_code   = "99213"
            proc_desc   = "Office or outpatient visit, established patient"
            proc_source = "default"
            steps.append("Step 7 ⚠ No procedure mapping found — using default evaluation code")

    procedure_result = ProcedureResult(
        code=proc_code,
        description=proc_desc,
        source=proc_source,
    )

    # ── Step 8: Conflict Check ─────────────────────────────────────────────
    steps.append("Step 8 ▶ Checking diagnosis-procedure conflicts (rule engine)...")
    raw_conflicts = await check_conflicts_in_db(
        icd_code=final_code,
        procedure_code=proc_code,
        patient_age=req.patient_age,
        patient_gender=req.patient_gender.value,
        pool=pg_pool,
    )
    conflicts = [
        ConflictItem(
            rule_name=c["rule_name"],
            severity=SeverityEnum(c.get("severity", "medium")),
            description=c["description"],
            action=c.get("action", "flag"),
        )
        for c in raw_conflicts
    ]
    steps.append(f"Step 8 ✓ Conflict check complete — {len(conflicts)} conflict(s) found")

    # ── Steps 9–11: Evidence Detection ────────────────────────────────────
    steps.append("Step 9 ▶ Checking evidence from Clinical Justification fields...")
    evidence = check_evidence(req)
    if evidence.missing_labels:
        steps.append(
            f"Step 10 ✓ Evidence {evidence.completeness_score:.0%} complete | "
            f"Missing: {', '.join(evidence.missing_labels)}"
        )
    else:
        steps.append("Step 10 ✓ All evidence fields complete (100%)")

    # ── Steps 12–13: Justification ────────────────────────────────────────
    steps.append("Step 11 ▶ Generating clinical justification via LLM...")
    just_data = await generate_and_score_justification(
        req=req,
        soap=soap_data,
        icd_code=final_code,
        icd_description=final_desc,
        procedure_code=proc_code,
        procedure_description=proc_desc,
        evidence=evidence,
    )
    justification = JustificationResult(**just_data)
    rewrite_note = f" (rewritten in {justification.iterations} iterations)" if justification.iterations == 2 else ""
    steps.append(
        f"Step 12 ✓ Justification score: {justification.score:.2f} — "
        f"{'Sufficient' if justification.is_sufficient else 'Below threshold'}{rewrite_note}"
    )

    # ── Step 15: Condition Classification ─────────────────────────────────
    condition_type = _classify_condition(final_code, req.severity, icd_db_severity)
    steps.append(f"Step 13 ✓ Condition classified as: '{condition_type}'")

    # ── Steps 14: Risk Analysis ────────────────────────────────────────────
    risk_flags = _analyze_risk_flags(req, final_code, raw_conflicts, evidence, condition_type, steps)

    # ── Steps 17–18: Approval Probability ─────────────────────────────────
    approval_prob, breakdown, recommendation = _calculate_approval_probability(
        evidence=evidence,
        justification_score=justification.score,
        raw_conflicts=raw_conflicts,
        risk_flags=risk_flags,
        condition_type=condition_type,
        steps=steps,
    )

    # ── Step 19: Explainability ────────────────────────────────────────────
    reasons, suggestions = _generate_explainability(
        probability=approval_prob,
        recommendation=recommendation,
        raw_conflicts=raw_conflicts,
        evidence=evidence,
        risk_flags=risk_flags,
        condition_type=condition_type,
        justification_score=justification.score,
    )
    steps.append("Step 12 ✓ Explainable output generated")

    # ── Step 20: Audit Log → MongoDB ──────────────────────────────────────
    duration_ms = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
    try:
        await mongo_db["audit_logs"].insert_one({
            "request_id":             request_id,
            "timestamp":              datetime.now(timezone.utc),
            "patient_name":           req.patient_name,
            "patient_age":            req.patient_age,
            "patient_gender":         req.patient_gender.value,
            "tpa":                    req.tpa,
            "disease_description":    req.disease_description,
            "icd_code":               final_code,
            "icd_description":        final_desc,
            "procedure_code":         proc_code,
            "approval_probability":   approval_prob,
            "approval_recommendation": recommendation,
            "missing_evidence":       evidence.missing_labels,
            "risk_flag_count":        len(risk_flags),
            "conflict_count":         len(conflicts),
            "justification_score":    justification.score,
            "processing_duration_ms": round(duration_ms, 2),
            "submitted":              False,
        })
        steps.append("📁 Audit log saved to MongoDB ✓")
    except Exception as e:
        logger.error("Audit log write failed: %s", e)
        steps.append("⚠ Audit log write failed (non-critical)")

    steps.append(f"✅ Agent complete — {recommendation} ({approval_prob:.1%}) | {round(duration_ms)}ms")

    # ── Step 20: Compose Final Response & Save Case ───────────────────────
    from schemas.case_schema import CaseSaveRequest
    from services.case_service import save_case
    
    # Save the case to Postgres to generate a strictly sequential Case ID
    case_req = CaseSaveRequest(
        patient_name=req.patient_name,
        patient_age=req.patient_age,
        patient_gender=req.patient_gender.value,
        tpa=req.tpa,
        disease_description=req.disease_description,
        medications=req.medications,
        procedure=req.procedure,
        duration_of_symptoms=req.duration_of_symptoms,
        prior_treatment=req.prior_treatment,
        severity=req.severity,
        investigations=req.investigations,
        specialist_referral=req.specialist_referral,
        soap_subjective=soap_note.subjective,
        soap_objective=soap_note.objective,
        soap_assessment=soap_note.assessment,
        soap_plan=soap_note.plan,
        icd_code=icd_result.code,
        icd_description=icd_result.description,
        procedure_code=procedure_result.code,
        procedure_description=procedure_result.description,
        justification_text=justification.text,
        justification_score=justification.score,
        missing_evidence=evidence.missing_labels,
        evidence_score=evidence.completeness_score,
        risk_flags=[f.model_dump() for f in risk_flags],
        conflicts=[c.model_dump() for c in conflicts],
        condition_type=condition_type,
        approval_probability=approval_prob,
        approval_recommendation=recommendation,
        reasons=reasons,
        suggestions=suggestions,
    )
    
    try:
        saved_case = await save_case(case_req, pg_pool, mongo_db)
        case_id = saved_case["case_id"]
        steps.append(f"📁 Case saved to DB with ID: {case_id} ✓")
    except Exception as e:
        logger.error("Failed to save case to DB: %s", e)
        import time
        case_id = f"HOSP-ERR-{int(time.time()*1000)}"
        steps.append("⚠ Failed to save case to database")

    return AgentResponse(
        hospital_name="InsureMind General Hospital",
        hospital_details="123 Health Ave, Medical City. Phone: (555) 123-4567",
        patient_details=PatientDetails(
            name=req.patient_name,
            age=req.patient_age,
            gender=req.patient_gender.value,
        ),
        soap_note=soap_note,
        insurance_approval_rate=f"{approval_prob:.0%}",
        case_id=case_id,
        
        request_id=request_id,
        timestamp=timestamp,
        tpa=req.tpa,
        icd=icd_result,
        procedure=procedure_result,
        conflicts=conflicts,
        evidence=evidence,
        justification=justification,
        risk_flags=risk_flags,
        condition_type=condition_type,
        approval_probability=approval_prob,
        approval_breakdown=breakdown,
        approval_recommendation=recommendation,
        reasons=reasons,
        suggestions=suggestions,
        processing_steps=steps,
    )