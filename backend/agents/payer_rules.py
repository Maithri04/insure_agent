"""
agents/payer_rules.py

Pipeline Step — Payer Policy Layer
────────────────────────────────────
Applies TPA/insurance-specific rules on top of the base approval probability.

What it does:
  • Queries the payer_rules PostgreSQL table for rules matching the TPA name
  • Each rule can: BOOST, REDUCE, or DENY an authorization based on
    the diagnosis category, procedure, condition type, or evidence score
  • Returns a modified approval_probability, added reasons, and added risk flags
  • If no payer rules exist for this TPA, returns the original probability unchanged

Payer rule types:
  boost         — Certain conditions/procedures always approved by this TPA
  reduce        — TPA has stricter criteria; requires additional documentation
  deny          — TPA policy explicitly excludes this procedure/diagnosis
  require_docs  — Extra documentation required (flags for review, no probability change)

Database: payer_rules table (created in seed.sql)
  TPA name matching is case-insensitive and uses partial match
  (so "Demo TPA", "demo tpa", "DEMO" all match "Demo TPA" rules)
"""

import json
import logging
from typing import List, Tuple
from schemas.agent_schema import RiskFlag, SeverityEnum

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# DB Fetch — Payer Rules
# ─────────────────────────────────────────────────────────────────────────────

async def _fetch_payer_rules(tpa_name: str, pool) -> list:
    """
    Fetch all active rules for the given TPA from the payer_rules table.
    Uses case-insensitive partial match so "demo TPA" matches "Demo TPA".
    """
    try:
        rows = await pool.fetch(
            """
            SELECT
                rule_name,
                rule_type,
                condition_category,
                procedure_code,
                condition_type,
                min_evidence_score,
                probability_modifier,
                description,
                action,
                metadata
            FROM payer_rules
            WHERE is_active = TRUE
              AND LOWER(tpa_name) LIKE LOWER($1)
            ORDER BY
                CASE rule_type
                    WHEN 'deny'         THEN 1
                    WHEN 'reduce'       THEN 2
                    WHEN 'require_docs' THEN 3
                    WHEN 'boost'        THEN 4
                END
            """,
            f"%{tpa_name.strip()}%",
        )
        return list(rows)
    except Exception as exc:
        logger.error("payer_rules DB fetch error: %s", exc)
        return []


# ─────────────────────────────────────────────────────────────────────────────
# Rule Matchers
# ─────────────────────────────────────────────────────────────────────────────

def _matches_condition_category(rule_category: str | None, icd_category: str) -> bool:
    """Check if the rule's condition_category matches the ICD category."""
    if not rule_category:
        return True   # NULL category = applies to all conditions
    return rule_category.lower().strip() in icd_category.lower().strip()


def _matches_procedure(rule_procedure: str | None, procedure_code: str) -> bool:
    """Check if the rule's procedure_code matches the requested procedure."""
    if not rule_procedure:
        return True   # NULL procedure = applies to all procedures
    return rule_procedure.strip().upper() == procedure_code.strip().upper()


def _matches_condition_type(rule_cond_type: str | None, condition_type: str) -> bool:
    """Check if the rule applies to this condition severity type."""
    if not rule_cond_type:
        return True   # NULL = applies to all condition types
    return rule_cond_type.lower().strip() == condition_type.lower().strip()


def _passes_evidence_threshold(min_score: float | None, evidence_score: float) -> bool:
    """Check if rule only fires when evidence is below a minimum threshold."""
    if min_score is None:
        return True
    return evidence_score < min_score


# ─────────────────────────────────────────────────────────────────────────────
# Rule Processor
# ─────────────────────────────────────────────────────────────────────────────

def _apply_rule(
    row: dict,
    icd_category: str,
    procedure_code: str,
    condition_type: str,
    evidence_score: float,
    current_probability: float,
) -> Tuple[float, str | None, RiskFlag | None]:
    """
    Evaluate a single payer rule row.
    Returns: (new_probability, reason_string, risk_flag_or_None)
    """
    # Check if this rule applies to the current context
    if not _matches_condition_category(row.get("condition_category"), icd_category):
        return current_probability, None, None
    if not _matches_procedure(row.get("procedure_code"), procedure_code):
        return current_probability, None, None
    if not _matches_condition_type(row.get("condition_type"), condition_type):
        return current_probability, None, None

    # Evidence threshold check (e.g. only apply reduce if evidence < 0.6)
    min_ev = row.get("min_evidence_score")
    if min_ev is not None:
        if not _passes_evidence_threshold(float(min_ev), evidence_score):
            return current_probability, None, None

    rule_type   = row.get("rule_type", "")
    modifier    = float(row.get("probability_modifier") or 0.0)
    description = row.get("description", "")
    rule_name   = row.get("rule_name", "Unknown Rule")

    new_prob    = current_probability
    reason      = None
    flag        = None

    if rule_type == "deny":
        new_prob = min(current_probability, 0.10)  # Cap at 10%
        reason   = f"Payer policy DENY: {description}"
        flag     = RiskFlag(
            flag=f"Payer Denial Rule: {rule_name}",
            severity=SeverityEnum.high,
            description=f"TPA policy explicitly excludes this claim: {description}",
        )

    elif rule_type == "reduce":
        new_prob = max(0.05, current_probability + modifier)
        reason   = f"Payer policy reduces approval probability: {description}"
        if modifier <= -0.15:
            flag = RiskFlag(
                flag=f"Payer Restriction: {rule_name}",
                severity=SeverityEnum.medium,
                description=description,
            )

    elif rule_type == "boost":
        new_prob = min(0.98, current_probability + modifier)
        reason   = f"Payer policy supports this claim: {description}"

    elif rule_type == "require_docs":
        # Probability unchanged but a review flag is added
        reason = f"Payer requires additional documentation: {description}"
        flag   = RiskFlag(
            flag=f"Additional Docs Required: {rule_name}",
            severity=SeverityEnum.low,
            description=description,
        )

    return round(new_prob, 3), reason, flag


# ─────────────────────────────────────────────────────────────────────────────
# In-Memory Fallback Rules (when no payer_rules table exists yet)
# ─────────────────────────────────────────────────────────────────────────────

_FALLBACK_RULES = [
    # Generic rules applied when no TPA-specific rules are found
    {
        "rule_name":            "Generic — Incomplete Evidence Reduction",
        "rule_type":            "reduce",
        "condition_category":   None,
        "procedure_code":       None,
        "condition_type":       None,
        "min_evidence_score":   0.5,
        "probability_modifier": -0.10,
        "description":          "Claims with less than 50% evidence completeness receive a standard reduction.",
        "action":               "review",
        "metadata":             None,
    },
    {
        "rule_name":            "Generic — Critical Condition Fast Track",
        "rule_type":            "boost",
        "condition_category":   None,
        "procedure_code":       None,
        "condition_type":       "critical",
        "min_evidence_score":   None,
        "probability_modifier": 0.08,
        "description":          "Critical conditions receive fast-track consideration with higher base approval.",
        "action":               "approve",
        "metadata":             None,
    },
    {
        "rule_name":            "Generic — Minor Condition Documentation Requirement",
        "rule_type":            "require_docs",
        "condition_category":   None,
        "procedure_code":       None,
        "condition_type":       "minor",
        "min_evidence_score":   None,
        "probability_modifier": 0.0,
        "description":          "Minor conditions require detailed justification of medical necessity before approval.",
        "action":               "review",
        "metadata":             None,
    },
]


# ─────────────────────────────────────────────────────────────────────────────
# Public Entry Point — called by agent_service.py
# ─────────────────────────────────────────────────────────────────────────────

async def apply_payer_rules(
    tpa_name: str,
    icd_category: str,
    procedure_code: str,
    condition_type: str,
    evidence_score: float,
    current_probability: float,
    pool,
    steps: list,
) -> Tuple[float, List[str], List[RiskFlag]]:
    """
    Apply TPA/payer-specific rules to adjust the approval probability.

    Args:
        tpa_name           : TPA name from the frontend Insurance Details form
        icd_category       : Diagnostic category (e.g. "Cardiac", "Oncology")
        procedure_code     : The mapped or provided procedure code
        condition_type     : "minor" | "moderate" | "serious" | "critical"
        evidence_score     : Completeness score from evidence_detector (0.0–1.0)
        current_probability: Approval probability before payer rules
        pool               : asyncpg connection pool
        steps              : Agent thought process log

    Returns:
        Tuple of:
          adjusted_probability : float
          payer_reasons        : List[str] — added to AgentResponse.reasons
          payer_risk_flags     : List[RiskFlag] — added to AgentResponse.risk_flags
    """
    steps.append(f"Payer Rules ▶ Applying TPA policy rules for '{tpa_name}'...")

    # Try DB first, fall back to in-memory rules if table is empty/missing
    raw_rows = await _fetch_payer_rules(tpa_name, pool)
    using_fallback = False

    if not raw_rows:
        logger.info("No payer rules found for TPA '%s' — using fallback rules", tpa_name)
        raw_rows = _FALLBACK_RULES
        using_fallback = True

    adjusted_probability = current_probability
    payer_reasons: List[str] = []
    payer_risk_flags: List[RiskFlag] = []

    for row in raw_rows:
        new_prob, reason, flag = _apply_rule(
            row=dict(row),
            icd_category=icd_category,
            procedure_code=procedure_code,
            condition_type=condition_type,
            evidence_score=evidence_score,
            current_probability=adjusted_probability,
        )
        if new_prob != adjusted_probability:
            adjusted_probability = new_prob
        if reason:
            payer_reasons.append(reason)
        if flag:
            payer_risk_flags.append(flag)

    delta = round(adjusted_probability - current_probability, 3)
    direction = f"+{delta:.3f}" if delta >= 0 else f"{delta:.3f}"
    source = "fallback rules" if using_fallback else f"{len(raw_rows)} TPA rule(s)"

    steps.append(
        f"Payer Rules ✓ {source} applied | "
        f"Probability: {current_probability:.3f} → {adjusted_probability:.3f} ({direction})"
    )

    return adjusted_probability, payer_reasons, payer_risk_flags