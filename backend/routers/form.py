"""
routers/form.py

Form Endpoints — lightweight save without running the agent pipeline.

Endpoints:
  POST /form/save      — save raw form data to MongoDB as a draft
  GET  /form/drafts    — list unsaved drafts for the current session
  DELETE /form/{id}    — delete a draft record
"""

import uuid
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, status
from schemas.models import FormSubmitRequest, FormSubmitResponse, ErrorResponse

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/form",
    tags=["Form"],
)


# ─────────────────────────────────────────────
# DB Helper
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
# POST /form/save  —  Save Draft
# ─────────────────────────────────────────────

@router.post(
    "/save",
    response_model=FormSubmitResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Save form data as a draft",
    description="""
Saves the raw Smart Agent Form data to MongoDB without running
the agent pipeline. Useful for auto-save or draft functionality.

The doctor can retrieve this later and click Verify to run the full pipeline.
    """,
    responses={
        201: {"description": "Draft saved",          "model": FormSubmitResponse},
        503: {"description": "Database unavailable", "model": ErrorResponse},
        500: {"description": "Save failed",          "model": ErrorResponse},
    },
)
async def save_form(payload: FormSubmitRequest) -> FormSubmitResponse:
    mongo_db = await _get_mongo()
    try:
        request_id = str(uuid.uuid4())

        document = {
            "request_id":           request_id,
            "timestamp":            datetime.now(timezone.utc),
            "type":                 "draft",
            "submitted":            False,

            # Patient
            "patient_name":         payload.patient_name,
            "patient_age":          payload.patient_age,
            "patient_gender":       payload.patient_gender.value,
            "tpa":                  payload.tpa,

            # Clinical
            "disease_description":  payload.disease_description,
            "medications":          payload.medications,
            "procedure":            payload.procedure,

            # Justification fields
            "duration_of_symptoms": payload.duration_of_symptoms,
            "prior_treatment":      payload.prior_treatment,
            "severity":             payload.severity,
            "investigations":       payload.investigations,
            "specialist_referral":  payload.specialist_referral,
        }

        await mongo_db["form_drafts"].insert_one(document)

        logger.info("Form draft saved — request_id: %s | patient: %s", request_id, payload.patient_name)

        return FormSubmitResponse(
            status="saved",
            message=(
                f"Form data saved for {payload.patient_name}. "
                "Click Verify to run the full agent pipeline."
            ),
            request_id=request_id,
        )

    except Exception as exc:
        logger.error("Form save failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save form data: {exc}",
        )


# ─────────────────────────────────────────────
# GET /form/drafts  —  List Drafts
# ─────────────────────────────────────────────

@router.get(
    "/drafts",
    status_code=status.HTTP_200_OK,
    summary="List saved form drafts",
    description="Returns all unsaved/draft form submissions stored in MongoDB.",
)
async def get_drafts(limit: int = 20, skip: int = 0):
    mongo_db = await _get_mongo()
    try:
        total = await mongo_db["form_drafts"].count_documents({"submitted": False})

        cursor = (
            mongo_db["form_drafts"]
            .find(
                {"submitted": False},
                {
                    "_id":          0,
                    "request_id":   1,
                    "timestamp":    1,
                    "patient_name": 1,
                    "patient_age":  1,
                    "tpa":          1,
                    "submitted":    1,
                },
            )
            .sort("timestamp", -1)
            .skip(skip)
            .limit(limit)
        )
        records = await cursor.to_list(length=limit)

        for r in records:
            if "timestamp" in r and hasattr(r["timestamp"], "isoformat"):
                r["timestamp"] = r["timestamp"].isoformat()

        return {"total": total, "records": records}

    except Exception as exc:
        logger.error("Drafts fetch failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        )


# ─────────────────────────────────────────────
# DELETE /form/{request_id}  —  Delete Draft
# ─────────────────────────────────────────────

@router.delete(
    "/{request_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete a form draft",
    responses={
        404: {"description": "Draft not found", "model": ErrorResponse},
    },
)
async def delete_draft(request_id: str):
    mongo_db = await _get_mongo()
    try:
        result = await mongo_db["form_drafts"].delete_one({"request_id": request_id})

        if result.deleted_count == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No draft found for request_id: {request_id}",
            )

        return {"status": "deleted", "request_id": request_id}

    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Draft delete failed for %s: %s", request_id, exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        )