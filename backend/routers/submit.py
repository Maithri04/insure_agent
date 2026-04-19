"""
routers/submit.py

Final Submission Endpoints — dedicated submit flow separate from the agent router.

Endpoints:
  POST /submit/authorization   — submit an existing verified agent result by request_id
  GET  /submit/status/{id}     — check submission status of a prior authorization
  GET  /submit/all             — list all submitted claims
"""

import logging
from fastapi import APIRouter, HTTPException, Query, status
from schemas.models import ErrorResponse

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/submit",
    tags=["Submission"],
)


# ─────────────────────────────────────────────
# DB Helpers
# ─────────────────────────────────────────────

async def _get_mongo():
    try:
        from db import get_mongo_db
        return get_mongo_db()
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Database unavailable: {exc}",
        )


# ─────────────────────────────────────────────
# POST /submit/authorization  —  Submit by request_id
# ─────────────────────────────────────────────

@router.post(
    "/authorization",
    status_code=status.HTTP_200_OK,
    summary="Submit a verified authorization request by request_id",
    description="""
Marks an existing verified agent run as officially submitted to the TPA.

Use this when:
  1. The doctor first clicked **Verify** (`POST /agent/verify`)
  2. Reviewed the results
  3. Now clicks **Submit** to finalize

Alternatively, `POST /agent/submit` does both steps in one call.
This endpoint is for the two-step verify-then-submit flow.
    """,
    responses={
        200: {"description": "Submitted successfully"},
        404: {"description": "Request not found", "model": ErrorResponse},
        409: {"description": "Already submitted",  "model": ErrorResponse},
        503: {"description": "DB unavailable",     "model": ErrorResponse},
    },
)
async def submit_authorization(request_id: str = Query(..., description="request_id from /agent/verify response")):
    mongo_db = await _get_mongo()
    try:
        # Fetch the existing audit record
        record = await mongo_db["audit_logs"].find_one(
            {"request_id": request_id},
            {"_id": 0, "submitted": 1, "patient_name": 1, "tpa": 1,
             "approval_recommendation": 1, "approval_probability": 1},
        )

        if not record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No agent run found for request_id: {request_id}. Run /agent/verify first.",
            )

        if record.get("submitted"):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Request {request_id} has already been submitted.",
            )

        # Mark as submitted
        from services import mark_submitted
        await mark_submitted(mongo_db, request_id)

        logger.info(
            "Authorization submitted — request_id: %s | patient: %s | TPA: %s",
            request_id, record.get("patient_name"), record.get("tpa"),
        )

        return {
            "status":                  "submitted",
            "request_id":              request_id,
            "patient_name":            record.get("patient_name"),
            "tpa":                     record.get("tpa"),
            "approval_recommendation": record.get("approval_recommendation"),
            "approval_probability":    record.get("approval_probability"),
            "message": (
                f"Authorization request for {record.get('patient_name')} submitted to "
                f"{record.get('tpa')}. Recommendation: {record.get('approval_recommendation')}."
            ),
        }

    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Submit authorization failed for %s: %s", request_id, exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        )


# ─────────────────────────────────────────────
# GET /submit/status/{request_id}  —  Check Status
# ─────────────────────────────────────────────

@router.get(
    "/status/{request_id}",
    status_code=status.HTTP_200_OK,
    summary="Check the submission status of a prior authorization",
    description="Returns the current submission status and recommendation for a given request_id.",
    responses={
        404: {"description": "Request not found", "model": ErrorResponse},
    },
)
async def get_submission_status(request_id: str):
    mongo_db = await _get_mongo()
    try:
        record = await mongo_db["audit_logs"].find_one(
            {"request_id": request_id},
            {
                "_id":                    0,
                "request_id":             1,
                "timestamp":              1,
                "submitted":              1,
                "submitted_at":           1,
                "patient_name":           1,
                "tpa":                    1,
                "icd_code":               1,
                "icd_description":        1,
                "procedure_code":         1,
                "approval_probability":   1,
                "approval_recommendation": 1,
                "condition_type":         1,
                "justification_score":    1,
                "missing_evidence":       1,
                "conflict_count":         1,
                "risk_flag_count":        1,
            },
        )

        if not record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No record found for request_id: {request_id}",
            )

        # Serialize datetimes
        for key in ("timestamp", "submitted_at"):
            if key in record and record[key] and hasattr(record[key], "isoformat"):
                record[key] = record[key].isoformat()

        return record

    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Status check failed for %s: %s", request_id, exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        )


# ─────────────────────────────────────────────
# GET /submit/all  —  All Submitted Claims
# ─────────────────────────────────────────────

@router.get(
    "/all",
    status_code=status.HTTP_200_OK,
    summary="List all submitted prior authorization claims",
    description="""
Returns a paginated list of all claims that have been officially submitted.
Filters to `submitted: true` records only.
    """,
)
async def get_all_submitted(
    limit: int = Query(default=20, ge=1, le=100),
    skip:  int = Query(default=0,  ge=0),
    tpa:   str = Query(default=None, description="Filter by TPA name"),
):
    mongo_db = await _get_mongo()
    try:
        query: dict = {"submitted": True}
        if tpa:
            query["tpa"] = {"$regex": tpa, "$options": "i"}

        total = await mongo_db["audit_logs"].count_documents(query)

        cursor = (
            mongo_db["audit_logs"]
            .find(
                query,
                {
                    "_id":                     0,
                    "request_id":              1,
                    "timestamp":               1,
                    "submitted_at":            1,
                    "patient_name":            1,
                    "patient_age":             1,
                    "tpa":                     1,
                    "icd_code":                1,
                    "icd_description":         1,
                    "procedure_code":          1,
                    "approval_probability":    1,
                    "approval_recommendation": 1,
                    "condition_type":          1,
                    "justification_score":     1,
                },
            )
            .sort("submitted_at", -1)
            .skip(skip)
            .limit(limit)
        )

        records = await cursor.to_list(length=limit)

        for r in records:
            for key in ("timestamp", "submitted_at"):
                if key in r and r[key] and hasattr(r[key], "isoformat"):
                    r[key] = r[key].isoformat()

        return {"total": total, "page": skip // limit + 1, "records": records}

    except Exception as exc:
        logger.error("GET /submit/all failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        )