"""
services/audit_service.py

Audit Log Service — MongoDB CRUD for all agent pipeline records.

Responsibilities:
  • save_audit_log()    — write every agent request + result to MongoDB
  • mark_submitted()    — update a record as submitted after POST /agent/submit
  • get_history()       — paginated list of past requests (for frontend history view)
  • get_by_request_id() — fetch a single complete audit record by request_id
  • get_stats()         — aggregate stats (total, approved, denied, avg probability)

Collection: audit_logs
  One document per agent run (verify or submit).
  Documents are immutable after creation except for the 'submitted' flag.

All user-entered data is stored so the doctor can:
  • Review past submissions from the frontend
  • Track approval history per TPA
  • Retrieve justification text for resubmission
"""

import logging
from datetime import datetime, timezone
from typing import Optional
from motor.motor_asyncio import AsyncIOMotorDatabase

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Document Schema (what gets written to MongoDB)
# ─────────────────────────────────────────────────────────────────────────────

def _build_audit_document(
    request_id: str,
    req,                   # AgentRequest
    soap: dict,
    icd_code: str,
    icd_description: str,
    procedure_code: str,
    approval_probability: float,
    approval_recommendation: str,
    missing_evidence: list,
    risk_flag_count: int,
    conflict_count: int,
    justification_score: float,
    justification_text: str,
    condition_type: str,
    risk_flags: list,
    conflicts: list,
    reasons: list,
    suggestions: list,
    processing_duration_ms: float,
    submitted: bool = False,
) -> dict:
    """
    Build a complete MongoDB audit document from agent pipeline outputs.
    Stores all inputs + outputs for full traceability.
    """
    return {
        # Identity
        "request_id":             request_id,
        "timestamp":              datetime.now(timezone.utc),
        "submitted":              submitted,
        "submitted_at":           None,

        # Patient info (from frontend form)
        "patient_name":           req.patient_name,
        "patient_age":            req.patient_age,
        "patient_gender":         req.patient_gender.value,
        "tpa":                    req.tpa,

        # Raw clinical inputs
        "disease_description":    req.disease_description,
        "medications":            req.medications,
        "procedure_input":        req.procedure,

        # Clinical justification fields (drives Missing Evidence Checklist)
        "duration_of_symptoms":   req.duration_of_symptoms,
        "prior_treatment":        req.prior_treatment,
        "severity":               req.severity,
        "investigations":         req.investigations,
        "specialist_referral":    req.specialist_referral,

        # SOAP Note
        "soap_subjective":        soap.get("subjective", ""),
        "soap_objective":         soap.get("objective", ""),
        "soap_assessment":        soap.get("assessment", ""),
        "soap_plan":              soap.get("plan", ""),

        # ICD + Procedure
        "icd_code":               icd_code,
        "icd_description":        icd_description,
        "procedure_code":         procedure_code,

        # Justification
        "justification_text":     justification_text,
        "justification_score":    justification_score,

        # Evidence checklist
        "missing_evidence":       missing_evidence,

        # Conflicts + risk
        "conflict_count":         conflict_count,
        "conflicts":              [
            {"rule": c.rule_name, "severity": c.severity.value, "action": c.action}
            for c in conflicts
        ],
        "risk_flag_count":        risk_flag_count,
        "risk_flags":             [
            {"flag": r.flag, "severity": r.severity.value}
            for r in risk_flags
        ],
        "condition_type":         condition_type,

        # Approval
        "approval_probability":   approval_probability,
        "approval_recommendation": approval_recommendation,

        # Explainability
        "reasons":                reasons,
        "suggestions":            suggestions,

        # Performance
        "processing_duration_ms": round(processing_duration_ms, 2),
    }


# ─────────────────────────────────────────────────────────────────────────────
# Write Operations
# ─────────────────────────────────────────────────────────────────────────────

async def save_audit_log(
    mongo_db: AsyncIOMotorDatabase,
    request_id: str,
    req,
    soap: dict,
    icd_code: str,
    icd_description: str,
    procedure_code: str,
    approval_probability: float,
    approval_recommendation: str,
    missing_evidence: list,
    risk_flag_count: int,
    conflict_count: int,
    justification_score: float,
    justification_text: str,
    condition_type: str,
    risk_flags: list,
    conflicts: list,
    reasons: list,
    suggestions: list,
    processing_duration_ms: float,
    submitted: bool = False,
) -> bool:
    """
    Save a complete agent pipeline result to MongoDB audit_logs.
    Returns True on success, False on failure (non-fatal — pipeline continues).
    """
    try:
        document = _build_audit_document(
            request_id=request_id,
            req=req,
            soap=soap,
            icd_code=icd_code,
            icd_description=icd_description,
            procedure_code=procedure_code,
            approval_probability=approval_probability,
            approval_recommendation=approval_recommendation,
            missing_evidence=missing_evidence,
            risk_flag_count=risk_flag_count,
            conflict_count=conflict_count,
            justification_score=justification_score,
            justification_text=justification_text,
            condition_type=condition_type,
            risk_flags=risk_flags,
            conflicts=conflicts,
            reasons=reasons,
            suggestions=suggestions,
            processing_duration_ms=processing_duration_ms,
            submitted=submitted,
        )
        await mongo_db["audit_logs"].insert_one(document)
        logger.info("Audit log saved — request_id: %s", request_id)
        return True

    except Exception as exc:
        logger.error("Audit log save failed for request_id %s: %s", request_id, exc)
        return False


async def mark_submitted(
    mongo_db: AsyncIOMotorDatabase,
    request_id: str,
) -> bool:
    """
    Mark an existing audit log entry as submitted.
    Called after POST /agent/submit to flag the record for the doctor's history.
    Returns True if the record was found and updated, False otherwise.
    """
    try:
        result = await mongo_db["audit_logs"].update_one(
            {"request_id": request_id},
            {
                "$set": {
                    "submitted":    True,
                    "submitted_at": datetime.now(timezone.utc),
                    "status":       "submitted",
                }
            },
        )
        if result.matched_count == 0:
            logger.warning("mark_submitted: request_id %s not found", request_id)
            return False

        logger.info("Audit log marked as submitted — request_id: %s", request_id)
        return True

    except Exception as exc:
        logger.error("mark_submitted failed for request_id %s: %s", request_id, exc)
        return False


# ─────────────────────────────────────────────────────────────────────────────
# Read Operations
# ─────────────────────────────────────────────────────────────────────────────

# Fields returned in list views (excludes large text fields for performance)
_LIST_PROJECTION = {
    "_id":                    0,
    "request_id":             1,
    "timestamp":              1,
    "patient_name":           1,
    "patient_age":            1,
    "patient_gender":         1,
    "tpa":                    1,
    "icd_code":               1,
    "icd_description":        1,
    "procedure_code":         1,
    "condition_type":         1,
    "approval_probability":   1,
    "approval_recommendation": 1,
    "missing_evidence":       1,
    "conflict_count":         1,
    "risk_flag_count":        1,
    "justification_score":    1,
    "submitted":              1,
    "submitted_at":           1,
    "processing_duration_ms": 1,
}

# Full projection — all fields (for detail view and resubmission)
_DETAIL_PROJECTION = {"_id": 0}


async def get_history(
    mongo_db: AsyncIOMotorDatabase,
    limit: int = 20,
    skip: int = 0,
    submitted_only: bool = False,
    tpa_filter: Optional[str] = None,
) -> dict:
    """
    Fetch paginated history of audit log entries.
    Used by GET /agent/history to populate the doctor's submission history.

    Args:
        limit          : Max records to return (default 20)
        skip           : Pagination offset
        submitted_only : If True, only return submitted claims
        tpa_filter     : Filter by TPA name (partial, case-insensitive)

    Returns:
        {"total": int, "records": List[dict]}
    """
    try:
        query: dict = {}
        if submitted_only:
            query["submitted"] = True
        if tpa_filter:
            query["tpa"] = {"$regex": tpa_filter, "$options": "i"}

        total = await mongo_db["audit_logs"].count_documents(query)

        cursor = (
            mongo_db["audit_logs"]
            .find(query, _LIST_PROJECTION)
            .sort("timestamp", -1)
            .skip(skip)
            .limit(limit)
        )
        records = await cursor.to_list(length=limit)

        # Convert datetime objects to ISO strings for JSON serialization
        for rec in records:
            if "timestamp" in rec and hasattr(rec["timestamp"], "isoformat"):
                rec["timestamp"] = rec["timestamp"].isoformat()
            if "submitted_at" in rec and rec["submitted_at"] and hasattr(rec["submitted_at"], "isoformat"):
                rec["submitted_at"] = rec["submitted_at"].isoformat()

        return {"total": total, "page": skip // limit + 1, "records": records}

    except Exception as exc:
        logger.error("get_history failed: %s", exc)
        return {"total": 0, "page": 1, "records": [], "error": str(exc)}


async def get_by_request_id(
    mongo_db: AsyncIOMotorDatabase,
    request_id: str,
) -> Optional[dict]:
    """
    Fetch a single complete audit record by request_id.
    Returns None if not found.
    Used when doctor clicks on a past submission to view full details.
    """
    try:
        record = await mongo_db["audit_logs"].find_one(
            {"request_id": request_id},
            _DETAIL_PROJECTION,
        )
        if record and "timestamp" in record and hasattr(record["timestamp"], "isoformat"):
            record["timestamp"] = record["timestamp"].isoformat()
        return record

    except Exception as exc:
        logger.error("get_by_request_id failed for %s: %s", request_id, exc)
        return None


# ─────────────────────────────────────────────────────────────────────────────
# Aggregate Stats
# ─────────────────────────────────────────────────────────────────────────────

async def get_stats(mongo_db: AsyncIOMotorDatabase) -> dict:
    """
    Compute aggregate statistics across all audit log entries.
    Used by a dashboard summary endpoint or admin panel.

    Returns:
        total, submitted, approved, denied, needs_review,
        avg_probability, avg_justification_score, top_tpas
    """
    try:
        pipeline = [
            {
                "$group": {
                    "_id":                   None,
                    "total":                 {"$sum": 1},
                    "submitted_count":       {"$sum": {"$cond": ["$submitted", 1, 0]}},
                    "approved_count":        {
                        "$sum": {
                            "$cond": [
                                {"$in": ["$approval_recommendation", ["APPROVED", "LIKELY APPROVED"]]},
                                1, 0,
                            ]
                        }
                    },
                    "denied_count":          {
                        "$sum": {
                            "$cond": [
                                {"$in": ["$approval_recommendation", ["DENIED", "LIKELY DENIED"]]},
                                1, 0,
                            ]
                        }
                    },
                    "review_count":          {
                        "$sum": {
                            "$cond": [
                                {"$eq": ["$approval_recommendation", "NEEDS REVIEW"]},
                                1, 0,
                            ]
                        }
                    },
                    "avg_probability":       {"$avg": "$approval_probability"},
                    "avg_just_score":        {"$avg": "$justification_score"},
                }
            }
        ]

        results = await mongo_db["audit_logs"].aggregate(pipeline).to_list(length=1)
        stats = results[0] if results else {}
        stats.pop("_id", None)

        # Round float fields
        for key in ("avg_probability", "avg_just_score"):
            if key in stats and stats[key] is not None:
                stats[key] = round(float(stats[key]), 3)

        # Top TPAs by volume
        tpa_pipeline = [
            {"$group": {"_id": "$tpa", "count": {"$sum": 1}}},
            {"$sort":  {"count": -1}},
            {"$limit": 5},
            {"$project": {"tpa": "$_id", "count": 1, "_id": 0}},
        ]
        top_tpas = await mongo_db["audit_logs"].aggregate(tpa_pipeline).to_list(length=5)
        stats["top_tpas"] = top_tpas

        return stats

    except Exception as exc:
        logger.error("get_stats failed: %s", exc)
        return {"error": str(exc)}