"""
ml/approval_model.py

Pipeline Steps 17 – 18
────────────────────────
Step 17 — Evaluate all scoring inputs:
           evidence completeness, justification quality, conflict penalties,
           risk flag penalties, condition severity bonus, payer modifier
Step 18 — Calculate final approval probability using a weighted model
           and map it to a recommendation label with clinical reasoning

Scoring Formula:
  base_score = (evidence × W_EVIDENCE) + (justification × W_JUSTIFICATION)

  final_score = base_score
              + severity_bonus          (from risk_analyzer.py Step 16)
              + payer_modifier          (from payer_rules.py)
              - conflict_penalty        (Step 8: high=-0.13, medium=-0.05 each)
              - risk_penalty            (Step 14: high flags=-0.07 each)

  Clamped to [0.04, 0.98]

Recommendation Thresholds:
  ≥ 0.82 → APPROVED
  ≥ 0.67 → LIKELY APPROVED
  ≥ 0.50 → NEEDS REVIEW
  ≥ 0.35 → LIKELY DENIED
   < 0.35 → DENIED

Design:
  • Pure Python — no external ML library dependency
  • Fully deterministic and auditable
  • Weights tunable via constants
  • Detailed breakdown returned for every prediction (explainability)
  • Scoring breakdown stored in audit log and returned to frontend
"""

import logging
from typing import List, Tuple
from schemas.agent_schema import (
    ConflictItem, RiskFlag, EvidenceResult,
    ApprovalBreakdown, SeverityEnum,
)

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Model Weights (tunable)
# ─────────────────────────────────────────────────────────────────────────────

W_EVIDENCE      = 0.35   # Weight: clinical evidence completeness
W_JUSTIFICATION = 0.40   # Weight: justification quality score

# Conflict penalties (per conflict, capped)
PENALTY_CONFLICT_HIGH   = 0.13
PENALTY_CONFLICT_MEDIUM = 0.05
PENALTY_CONFLICT_LOW    = 0.02
MAX_CONFLICT_PENALTY    = 0.40   # Total conflict penalty never exceeds this

# Risk flag penalties (per high/critical flag, capped)
PENALTY_RISK_HIGH       = 0.07
MAX_RISK_PENALTY        = 0.22

# Recommendation thresholds
THRESHOLD_APPROVED       = 0.82
THRESHOLD_LIKELY_APPROVED = 0.67
THRESHOLD_NEEDS_REVIEW   = 0.50
THRESHOLD_LIKELY_DENIED  = 0.35


# ─────────────────────────────────────────────────────────────────────────────
# Step 17: Component Score Calculators
# ─────────────────────────────────────────────────────────────────────────────

def _calculate_conflict_penalty(conflicts: List[ConflictItem]) -> float:
    """
    Step 17: Sum conflict penalties by severity, capped at MAX_CONFLICT_PENALTY.
    Deny-action conflicts apply the maximum high penalty each.
    """
    total = 0.0
    for c in conflicts:
        if c.severity == SeverityEnum.high or c.action == "deny":
            total += PENALTY_CONFLICT_HIGH
        elif c.severity == SeverityEnum.medium:
            total += PENALTY_CONFLICT_MEDIUM
        else:
            total += PENALTY_CONFLICT_LOW
    return round(min(MAX_CONFLICT_PENALTY, total), 4)


def _calculate_risk_penalty(risk_flags: List[RiskFlag]) -> float:
    """
    Step 17: Sum risk penalties for high/critical flags, capped at MAX_RISK_PENALTY.
    Medium flags contribute a reduced penalty.
    """
    total = 0.0
    for flag in risk_flags:
        if flag.severity in (SeverityEnum.high, SeverityEnum.critical):
            total += PENALTY_RISK_HIGH
        elif flag.severity == SeverityEnum.medium:
            total += PENALTY_RISK_HIGH * 0.4  # 40% of high penalty
    return round(min(MAX_RISK_PENALTY, total), 4)


def _hard_deny_check(conflicts: List[ConflictItem]) -> bool:
    """
    Check if any conflict has action='deny' with high severity.
    Hard denials cap probability at a very low value regardless of other scores.
    """
    return any(
        c.action == "deny" and c.severity == SeverityEnum.high
        for c in conflicts
    )


# ─────────────────────────────────────────────────────────────────────────────
# Step 18: Recommendation Mapping
# ─────────────────────────────────────────────────────────────────────────────

def _map_to_recommendation(probability: float) -> str:
    """
    Step 18: Map probability score to a clinical recommendation label.
    These labels are displayed directly in the frontend approval panel.
    """
    if probability >= THRESHOLD_APPROVED:
        return "APPROVED"
    elif probability >= THRESHOLD_LIKELY_APPROVED:
        return "LIKELY APPROVED"
    elif probability >= THRESHOLD_NEEDS_REVIEW:
        return "NEEDS REVIEW"
    elif probability >= THRESHOLD_LIKELY_DENIED:
        return "LIKELY DENIED"
    else:
        return "DENIED"


def _recommendation_reason(
    recommendation: str,
    probability: float,
    evidence: EvidenceResult,
    justification_score: float,
    condition_type: str,
    conflict_count: int,
    high_risk_flag_count: int,
) -> str:
    """
    Generate a one-sentence primary reason for the recommendation.
    Shown in the frontend's explainability panel.
    """
    if recommendation == "APPROVED":
        return (
            f"Strong clinical documentation ({evidence.completeness_score:.0%} complete), "
            f"high justification quality ({justification_score:.2f}), and a "
            f"'{condition_type}' condition with no disqualifying conflicts support approval."
        )
    elif recommendation == "LIKELY APPROVED":
        return (
            f"Good evidence quality ({evidence.completeness_score:.0%}) and justification "
            f"score ({justification_score:.2f}) support approval with minor reservations."
        )
    elif recommendation == "NEEDS REVIEW":
        issues = []
        if evidence.completeness_score < 0.7:
            issues.append(f"incomplete evidence ({evidence.completeness_score:.0%})")
        if justification_score < 0.7:
            issues.append(f"low justification score ({justification_score:.2f})")
        if conflict_count > 0:
            issues.append(f"{conflict_count} unresolved conflict(s)")
        return (
            f"Manual review required due to: {'; '.join(issues) if issues else 'insufficient overall scoring'}."
        )
    elif recommendation == "LIKELY DENIED":
        return (
            f"High denial risk — evidence is {evidence.completeness_score:.0%} complete, "
            f"justification score is {justification_score:.2f}, and "
            f"{conflict_count} conflict(s) detected with {high_risk_flag_count} high-risk flag(s)."
        )
    else:  # DENIED
        return (
            "Claim denied — critical conflicts detected (deny action), "
            "insufficient clinical evidence, or policy exclusion applied. "
            "Address conflicts and resubmit with complete documentation."
        )


# ─────────────────────────────────────────────────────────────────────────────
# Public Entry Point — called by agent_service.py (Steps 17–18)
# ─────────────────────────────────────────────────────────────────────────────

def calculate_approval_probability(
    evidence: EvidenceResult,
    justification_score: float,
    conflicts: List[ConflictItem],
    risk_flags: List[RiskFlag],
    condition_type: str,
    severity_bonus: float,
    payer_modifier: float,
    steps: list,
) -> Tuple[float, ApprovalBreakdown, str, str]:
    """
    Steps 17–18: Calculate the final approval probability and recommendation.

    Args:
        evidence           : EvidenceResult with completeness_score
        justification_score: Hybrid score from justification.py (0.0–1.0)
        conflicts          : List of ConflictItem from conflict_checker.py
        risk_flags         : List of RiskFlag from risk_analyzer.py
        condition_type     : "minor" | "moderate" | "serious" | "critical"
        severity_bonus     : Float modifier from risk_analyzer.get_severity_bonus()
        payer_modifier     : Net modifier from payer_rules.apply_payer_rules()
        steps              : Agent thought process log list

    Returns:
        Tuple of:
          probability       : float  (0.04–0.98)
          breakdown         : ApprovalBreakdown
          recommendation    : str    (e.g. "APPROVED")
          primary_reason    : str    (one-sentence explanation)
    """
    steps.append("Step 17 ▶ Computing weighted approval probability...")

    evidence_score = evidence.completeness_score
    conflict_penalty = _calculate_conflict_penalty(conflicts)
    risk_penalty     = _calculate_risk_penalty(risk_flags)

    # Base weighted score (evidence + justification)
    base_score = (evidence_score * W_EVIDENCE) + (justification_score * W_JUSTIFICATION)

    # Apply all modifiers
    raw_score = (
        base_score
        + severity_bonus
        + payer_modifier
        - conflict_penalty
        - risk_penalty
    )

    # Hard deny check — any high-severity deny conflict floors the score
    if _hard_deny_check(conflicts):
        raw_score = min(raw_score, 0.12)
        steps.append("Step 17 ⚠ Hard deny rule triggered — probability floored at ≤12%")

    # Clamp to valid range
    probability = round(max(0.04, min(0.98, raw_score)), 3)

    # Map to recommendation
    recommendation = _map_to_recommendation(probability)

    # Count high-risk flags for reason generation
    high_flag_count = sum(
        1 for f in risk_flags
        if f.severity in (SeverityEnum.high, SeverityEnum.critical)
    )

    primary_reason = _recommendation_reason(
        recommendation=recommendation,
        probability=probability,
        evidence=evidence,
        justification_score=justification_score,
        condition_type=condition_type,
        conflict_count=len(conflicts),
        high_risk_flag_count=high_flag_count,
    )

    breakdown = ApprovalBreakdown(
        evidence_score=round(evidence_score, 3),
        justification_score=round(justification_score, 3),
        severity_bonus=round(severity_bonus, 3),
        conflict_penalty=round(conflict_penalty, 3),
        risk_penalty=round(risk_penalty, 3),
    )

    steps.append(
        f"Step 17 ✓ Score breakdown — "
        f"Evidence: {evidence_score:.2f}×{W_EVIDENCE} | "
        f"Justification: {justification_score:.2f}×{W_JUSTIFICATION} | "
        f"Severity: {severity_bonus:+.3f} | "
        f"Payer: {payer_modifier:+.3f} | "
        f"Conflict: -{conflict_penalty:.3f} | "
        f"Risk: -{risk_penalty:.3f}"
    )
    steps.append(
        f"Step 18 ✓ Final probability: {probability:.1%} → "
        f"Recommendation: {recommendation}"
    )

    logger.info(
        "Approval calculated — probability: %.3f | recommendation: %s | "
        "condition: %s | conflicts: %d | risk_flags: %d",
        probability, recommendation, condition_type, len(conflicts), len(risk_flags),
    )

    return probability, breakdown, recommendation, primary_reason