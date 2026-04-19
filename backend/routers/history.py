"""
routers/history.py

History Endpoints — Download stored reports in PDF form by case ID.

Endpoints:
  GET  /history/{case_id} — download PDF for a given case ID
"""

import logging
from fastapi import APIRouter, HTTPException, status
from schemas.models import ErrorResponse

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/history",
    tags=["History"],
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
# GET /history/{case_id}  —  Download PDF
# ─────────────────────────────────────────────

from fastapi.responses import FileResponse
from pathlib import Path

@router.get(
    "/{case_id}",
    summary="Download PDF report for a case by case ID",
    description="""
Returns the PDF report for the given case_id as a file download.

If the PDF doesn't exist yet, it will be generated on-the-fly before download.
The browser will prompt the user to save the file locally.
    """,
    responses={
        200: {"description": "PDF file download"},
        404: {"description": "Case not found",           "model": ErrorResponse},
        503: {"description": "PDF generation failed",    "model": ErrorResponse},
    },
)
async def download_history_pdf(case_id: str):
    pool = await _get_pg()
    try:
        from services.case_service import get_case_by_id, update_pdf_path
        from services.pdf_service  import generate_pdf
        from db import get_mongo_db

        case = await get_case_by_id(case_id.upper(), pool)
        if not case:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Case '{case_id.upper()}' not found.",
            )

        pdf_path_str = case.get("pdf_path")

        # Generate PDF if it doesn't exist yet
        if not pdf_path_str or not Path(pdf_path_str).exists():
            logger.info("PDF not found for %s — generating now...", case_id)
            try:
                pdf_path_str = await generate_pdf(case)
                mongo_db = get_mongo_db()
                await update_pdf_path(case_id.upper(), pdf_path_str, pool, mongo_db)
            except Exception as pdf_exc:
                logger.error("PDF generation failed for %s: %s", case_id, pdf_exc)
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail=f"PDF generation failed: {pdf_exc}",
                )

        pdf_path = Path(pdf_path_str)
        if not pdf_path.exists():
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="PDF file not found on server. Please try regenerating.",
            )

        # Return as file download — browser saves to local system
        return FileResponse(
            path=str(pdf_path),
            media_type="application/pdf",
            filename=f"InsureMind_{case_id.upper()}_Report.pdf",
            headers={
                "Content-Disposition": f'attachment; filename="InsureMind_{case_id.upper()}_Report.pdf"'
            },
        )

    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("GET /history/%s failed", case_id)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))