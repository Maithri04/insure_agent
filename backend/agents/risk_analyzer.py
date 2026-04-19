"""
agents/risk_analyzer.py

Pipeline Steps 14 – 16
────────────────────────
Step 14 — Analyze and categorize all risk flags (high / medium / low severity)
           Sources: conflicts, patient age, documentation gaps,
                    high-acuity ICD codes, missing referral for serious conditions
Step 15 — Classify condition type: minor / moderate / serious / critical
           Logic: DB severity > ICD prefix rules > user-entered severity field
Step 16 — Apply condition-based approval modifier:
           • minor    → probability reduced  (low medical necessity baseline)
           • moderate → probability unchanged
           • serious  → probability boosted  (clear medical necessity)
           • critical → probability boosted more (urgent, life-threatening)

Design:
  • Pure Python logic — no LLM calls, no DB queries
  • All rules are deterministic and auditable
  • Condition classification uses a multi-strategy approach for robustness
  • High-acuity ICD prefix list is carefully curated from clinical literature
"""

import logging
from typing import List, Tuple
from schemas.agent_schema import (
    ConflictItem, EvidenceResult, RiskFlag, SeverityEnum
)

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# ICD-10 Prefix Classification Maps (Step 15)
# ─────────────────────────────────────────────────────────────────────────────

# Critical: life-threatening, immediate intervention usually required
_CRITICAL_ICD_PREFIXES = (
    "I21",  # Acute MI
    "I22",  # Subsequent MI
    "I46",  # Cardiac arrest
    "I63",  # Cerebral infarction (ischaemic stroke)
    "I64",  # Stroke NOS
    "I26",  # Pulmonary embolism
    "J96",  # Respiratory failure
    "R09",  # Other cardiorespiratory symptoms
    "S06",  # Intracranial injury
    "T71",  # Asphyxiation
    "A41",  # Sepsis
    "K35",  # Acute appendicitis
    "P07",  # Preterm newborn
    "G06",  # Intracranial abscess
    "N17",  # Acute kidney failure
)

# Serious: significant morbidity, specialist care required
_SERIOUS_ICD_PREFIXES = (
    "I",    # All cardiac (not already critical)
    "C",    # All malignancies
    "J18",  # Pneumonia
    "J44",  # COPD exacerbation
    "J85",  # Lung abscess
    "J12",  # Viral pneumonia
    "K74",  # Cirrhosis
    "K85",  # Acute pancreatitis
    "K92",  # GI bleeding
    "N18",  # CKD (stages 3–5)
    "N04",  # Nephrotic syndrome
    "G35",  # Multiple sclerosis
    "G20",  # Parkinson disease
    "G30",  # Alzheimer disease
    "G91",  # Hydrocephalus
    "M32",  # Systemic lupus
    "M80",  # Osteoporosis with fracture
    "B18",  # Chronic viral hepatitis
    "B20",  # HIV disease
    "A15",  # Tuberculosis
    "F20",  # Schizophrenia
    "L89",  # Pressure ulcer
    "S72",  # Femoral neck fracture
    "O42",  # PROM (obstetric)
    "H35",  # Macular degeneration
    "H43",  # Vitreous haemorrhage
    "G40",  # Epilepsy
    "I71",  # Aortic aneurysm
    "I82",  # DVT
)

# Moderate: significant symptoms but not immediately life-threatening
_MODERATE_ICD_PREFIXES = (
    "M",    # Musculoskeletal
    "K",    # Gastrointestinal (non-critical)
    "N",    # Renal/urinary (non-critical)
    "G",    # Neurological (non-critical)
    "E",    # Endocrine / diabetes
    "H",    # Ophthalmology / ENT
    "J45",  # Asthma
    "J20",  # Acute bronchitis
    "F3",   # Mood disorders
    "F4",   # Anxiety / stress disorders
    "L40",  # Psoriasis
)


def classify_condition(
    icd_code: str,
    severity_input: str | None,
    icd_db_severity: str | None,
) -> str:
    """
    Step 15: Classify condition type using a multi-strategy approach.

    Priority order (highest → lowest reliability):
      1. DB severity   — explicitly set in icd_codes.severity during seeding
      2. ICD prefix    — deterministic rules based on ICD-10 chapter/category
      3. User input    — severity field from frontend Clinical Justification form

    Returns one of: "minor" | "moderate" | "serious" | "critical"
    """
    # Strategy 1: Use DB severity if valid
    db_sev = (icd_db_severity or "").lower().strip()
    if db_sev in ("critical", "serious", "moderate", "minor"):
        return db_sev

    # Strategy 2: ICD prefix-based classification
    # Check critical first (most specific)
    if any(icd_code.startswith(p) for p in _CRITICAL_ICD_PREFIXES):
        return "critical"

    if any(icd_code.startswith(p) for p in _SERIOUS_ICD_PREFIXES):
        return "serious"

    if any(icd_code.startswith(p) for p in _MODERATE_ICD_PREFIXES):
        return "moderate"

    # Strategy 3: Map user-entered severity to condition type
    sev_map = {
        "critical": "critical",
        "severe":   "serious",
        "high":     "serious",
        "moderate": "moderate",
        "medium":   "moderate",
        "low":      "minor",
        "mild":     "minor",
    }
    if severity_input:
        mapped = sev_map.get(severity_input.lower().strip())
        if mapped:
            return mapped

    # Default: minor (safest assumption — requires more evidence burden)
    return "minor"


def _get_condition_label(condition_type: str) -> str:
    """Human-readable label for the condition type (shown in frontend)."""
    labels = {
        "minor":    "Minor Condition — Standard evidence requirements",
        "moderate": "Moderate Condition — Elevated documentation expected",
        "serious":  "Serious Medical Condition — Strong medical necessity supported",
        "critical": "Critical / Life-Threatening — Urgent authorization priority",
    }
    return labels.get(condition_type, "Unknown severity classification")


# ─────────────────────────────────────────────────────────────────────────────
# Step 16: Condition-Based Probability Modifier
# ─────────────────────────────────────────────────────────────────────────────

# Maps condition_type → probability modifier applied to base score
_CONDITION_MODIFIERS = {
    "minor":    -0.12,  # Step 16: minor conditions → reduced probability
    "moderate":  0.00,  # neutral
    "serious":   0.08,  # Step 16: serious conditions → increased probability
    "critical":  0.13,  # Step 16: critical conditions → highest boost
}


def get_severity_bonus(condition_type: str) -> float:
    """Step 16: Return the probability modifier for this condition type."""
    return _CONDITION_MODIFIERS.get(condition_type, 0.0)


# ─────────────────────────────────────────────────────────────────────────────
# Step 14: High-Acuity ICD Risk Detection
# ─────────────────────────────────────────────────────────────────────────────

# ICD prefixes that always generate a high-acuity risk flag
_HIGH_ACUITY_PREFIXES = (
    "I2", "I46", "I5", "I6", "I26",
    "C",  "J96", "K85", "K35", "K92",
    "N17", "G35", "G20", "G06", "A41",
    "S06", "T71",
)

# Known surgical/high-risk procedure codes
_HIGH_RISK_PROCEDURES = {
    "33533", "33249", "61510", "92928", "33208",
    "27447", "22612", "59510", "38230", "50543",
    "32663", "27130",
}


# ─────────────────────────────────────────────────────────────────────────────
# Public Entry Point — Step 14
# ─────────────────────────────────────────────────────────────────────────────

def analyze_risk_flags(
    req,                              # AgentRequest
    icd_code: str,
    procedure_code: str,
    conflicts: List[ConflictItem],
    evidence: EvidenceResult,
    condition_type: str,
    steps: list,
) -> List[RiskFlag]:
    """
    Step 14: Systematically identify all clinical and administrative risk flags.

    Risk flag sources:
      1. Conflict-derived flags    — from Step 8 conflict checker
      2. Patient age flags         — elderly (≥65) and pediatric (≤12)
      3. Documentation gap flags   — evidence completeness thresholds
      4. High-acuity diagnosis     — critical ICD prefix detected
      5. Surgical procedure risk   — high-risk procedure without serious/critical condition
      6. Missing referral          — serious/critical condition without specialist referral
      7. Missing investigations    — non-minor condition without diagnostic tests
      8. No prior treatment        — serious condition with no treatment history documented

    Returns:
        List[RiskFlag] — sorted by severity (high → medium → low)
    """
    steps.append("Step 14 ▶ Analyzing risk flags...")
    flags: List[RiskFlag] = []

    # ── 1. Conflict-derived risk flags ────────────────────────────────────
    for conflict in conflicts:
        if conflict.severity in (SeverityEnum.high, SeverityEnum.medium):
            flags.append(RiskFlag(
                flag=f"Conflict: {conflict.rule_name}",
                severity=conflict.severity,
                description=conflict.description,
            ))

    # ── 2. Patient age risks ───────────────────────────────────────────────
    age = req.patient_age

    if age >= 75:
        flags.append(RiskFlag(
            flag="Very elderly patient (≥75 years)",
            severity=SeverityEnum.high,
            description=(
                f"Patient is {age} years old. Very elderly patients carry substantially "
                "increased procedural risk, polypharmacy concerns, and often require "
                "geriatric assessment before authorization. Comprehensive documentation required."
            ),
        ))
    elif age >= 65:
        flags.append(RiskFlag(
            flag="Elderly patient (≥65 years)",
            severity=SeverityEnum.medium,
            description=(
                f"Patient is {age} years old. Elderly patients carry increased surgical "
                "risk. Enhanced documentation, anaesthesia assessment, and specialist "
                "sign-off may be required by the TPA."
            ),
        ))
    elif age <= 12:
        flags.append(RiskFlag(
            flag="Pediatric patient (≤12 years)",
            severity=SeverityEnum.medium,
            description=(
                f"Patient is {age} years old. Pediatric-specific dosing protocols, "
                "parental consent documentation, and pediatric specialist involvement "
                "are required for insurance authorization."
            ),
        ))

    # ── 3. Evidence completeness risk ─────────────────────────────────────
    ev_score = evidence.completeness_score

    if ev_score < 0.20:
        flags.append(RiskFlag(
            flag="Critical documentation failure",
            severity=SeverityEnum.high,
            description=(
                f"Only {ev_score:.0%} of required Clinical Justification fields are completed. "
                f"Missing: {', '.join(evidence.missing_labels)}. "
                "Extremely high risk of denial. Complete all fields before submission."
            ),
        ))
    elif ev_score < 0.40:
        flags.append(RiskFlag(
            flag="Severely incomplete documentation",
            severity=SeverityEnum.high,
            description=(
                f"Clinical evidence is {ev_score:.0%} complete. "
                f"Missing: {', '.join(evidence.missing_labels)}. "
                "High denial risk — complete all justification fields."
            ),
        ))
    elif ev_score < 0.80:
        flags.append(RiskFlag(
            flag="Incomplete clinical evidence",
            severity=SeverityEnum.medium,
            description=(
                f"Clinical evidence is {ev_score:.0%} complete. "
                f"Missing: {', '.join(evidence.missing_labels)}. "
                "Completing all fields significantly improves approval odds."
            ),
        ))

    # ── 4. High-acuity ICD diagnosis ──────────────────────────────────────
    if any(icd_code.startswith(p) for p in _HIGH_ACUITY_PREFIXES):
        flags.append(RiskFlag(
            flag=f"High-acuity diagnosis: {icd_code}",
            severity=SeverityEnum.high,
            description=(
                f"ICD-10 {icd_code} indicates a serious or life-threatening condition. "
                "Comprehensive clinical documentation, specialist reports, and diagnostic "
                "evidence are critical for authorization approval."
            ),
        ))

    # ── 5. High-risk surgical procedure ───────────────────────────────────
    if procedure_code in _HIGH_RISK_PROCEDURES and condition_type in ("minor", "moderate"):
        flags.append(RiskFlag(
            flag=f"High-risk procedure for {condition_type} condition",
            severity=SeverityEnum.medium,
            description=(
                f"Procedure {procedure_code} is classified as high-risk/surgical, "
                f"but the condition is classified as '{condition_type}'. "
                "Insurers typically require stronger clinical justification for high-risk "
                "interventions when the diagnosis severity does not align."
            ),
        ))

    # ── 6. No specialist referral for serious/critical ────────────────────
    if condition_type in ("serious", "critical"):
        referral_item = next((i for i in evidence.items if i.label == "Referral"), None)
        if referral_item and not referral_item.is_present:
            flags.append(RiskFlag(
                flag="No specialist referral documented",
                severity=SeverityEnum.medium,
                description=(
                    f"Condition is classified as '{condition_type}' but no specialist "
                    "referral has been documented. Most TPAs require specialist involvement "
                    "for serious and critical condition authorizations."
                ),
            ))

    # ── 7. No investigations for non-minor conditions ─────────────────────
    if condition_type != "minor":
        inv_item = next((i for i in evidence.items if i.label == "Investigations"), None)
        if inv_item and not inv_item.is_present:
            flags.append(RiskFlag(
                flag="No diagnostic investigations documented",
                severity=SeverityEnum.medium,
                description=(
                    "Lab results, imaging reports, or diagnostic test data are expected "
                    f"for a '{condition_type}' condition. Providing investigation results "
                    "substantially strengthens the authorization request."
                ),
            ))

    # ── 8. No prior treatment for serious conditions ──────────────────────
    if condition_type in ("serious", "critical"):
        prior_item = next((i for i in evidence.items if i.label == "Prior treatment"), None)
        if prior_item and not prior_item.is_present:
            flags.append(RiskFlag(
                flag="No prior treatment history documented",
                severity=SeverityEnum.low,
                description=(
                    f"No prior treatment documented for this '{condition_type}' condition. "
                    "Documenting failed conservative management significantly strengthens "
                    "the medical necessity argument for the requested procedure."
                ),
            ))

    # ── Sort: high → medium → low ─────────────────────────────────────────
    severity_order = {
        SeverityEnum.critical: 0,
        SeverityEnum.high:     1,
        SeverityEnum.medium:   2,
        SeverityEnum.low:      3,
    }
    flags.sort(key=lambda f: severity_order.get(f.severity, 4))

    high_count   = sum(1 for f in flags if f.severity in (SeverityEnum.high, SeverityEnum.critical))
    medium_count = sum(1 for f in flags if f.severity == SeverityEnum.medium)
    low_count    = sum(1 for f in flags if f.severity == SeverityEnum.low)

    steps.append(
        f"Step 14 ✓ {len(flags)} risk flag(s) identified — "
        f"High: {high_count} | Medium: {medium_count} | Low: {low_count}"
    )
    steps.append(
        f"Step 15 ✓ Condition classified as '{condition_type}' — "
        f"{_get_condition_label(condition_type)}"
    )

    bonus = get_severity_bonus(condition_type)
    if bonus > 0:
        steps.append(
            f"Step 16 ✓ Serious/critical condition — "
            f"approval probability boosted by +{bonus:.0%}"
        )
    elif bonus < 0:
        steps.append(
            f"Step 16 ✓ Minor condition — "
            f"approval probability reduced by {bonus:.0%} (higher evidence burden applies)"
        )
    else:
        steps.append("Step 16 ✓ Moderate condition — no severity modifier applied")

    return flags