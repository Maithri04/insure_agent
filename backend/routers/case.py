"""
routers/case.py

Case Endpoints:
  POST /case/access           — doctor enters patient_name + case_id → returns full case
  GET  /case/{case_id}        — fetch case by ID only (internal/admin)
  GET  /case/download/{case_id} — download PDF report to local system
"""

import logging
from fastapi import APIRouter, HTTPException, status
from schemas.case_schema import CaseResponse
from schemas.models import ErrorResponse

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/case",
    tags=["Case Management"],
)


# ─────────────────────────────────────────────
# DB Helper
# ─────────────────────────────────────────────

async def _get_pg():
    try:
        from db import get_postgres_pool
        return await get_postgres_pool()
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Database unavailable: {exc}",
        )


# ─────────────────────────────────────────────
# GET /case/{case_id}  —  Fetch by ID
# ─────────────────────────────────────────────

@router.get(
    "/{case_id}",
    response_model=CaseResponse,
    response_model_exclude_none=True,
    status_code=status.HTTP_200_OK,
    summary="Fetch full case by case ID",
    description="Returns the full case record by case_id without patient name verification. Used internally.",
    responses={
        404: {"description": "Case not found", "model": ErrorResponse},
    },
)
async def get_case_by_id(case_id: str):
    pool = await _get_pg()
    try:
        from services.case_service import get_case_by_id as fetch
        case = await fetch(case_id.upper(), pool)

        if not case:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Case '{case_id.upper()}' not found.",
            )

        # Map DB field `soap_json` to API field `soap` (required by CaseResponse model)
        if not case.get("soap") and case.get("soap_json"):
            soap_val = case.get("soap_json")
            if isinstance(soap_val, str):
                try:
                    import json as _json
                    soap_val = _json.loads(soap_val)
                except Exception:
                    soap_val = None
            if isinstance(soap_val, dict):
                case["soap"] = soap_val

        return case

    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("GET /case/%s failed", case_id)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


