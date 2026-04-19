"""
routers/analyze.py

Analysis & Lookup Endpoints — query the PostgreSQL reference data.

Endpoints:
  GET /analyze/icd              — search ICD-10 codes by keyword or code prefix
  GET /analyze/icd/{code}       — get a single ICD-10 code detail
  GET /analyze/procedures       — search procedure codes by keyword
  GET /analyze/tpa-list         — list all TPAs with rule counts (for frontend dropdown)
  GET /analyze/conflict-rules   — list all active conflict rules (admin view)
"""

import logging
from fastapi import APIRouter, HTTPException, Query, status
from schemas.models import ErrorResponse

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/analyze",
    tags=["Analysis & Lookup"],
)


# ─────────────────────────────────────────────
# DB Helper
# ─────────────────────────────────────────────

async def _get_pool():
    try:
        from db import get_postgres_pool
        return await get_postgres_pool()
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Database unavailable: {exc}",
        )


# ─────────────────────────────────────────────
# GET /analyze/icd  — Search ICD Codes
# ─────────────────────────────────────────────

@router.get(
    "/icd",
    status_code=status.HTTP_200_OK,
    summary="Search ICD-10 codes",
    description="""
Search ICD-10 codes by keyword (searches description) or code prefix.
Returns matching codes with severity and category.
Used to populate autocomplete fields in the frontend.
    """,
)
async def search_icd(
    q:        str = Query(default="",    description="Search keyword or ICD code prefix"),
    severity: str = Query(default=None,  description="Filter by severity: minor|moderate|serious|critical"),
    category: str = Query(default=None,  description="Filter by category: Cardiac|Oncology|etc."),
    limit:    int = Query(default=20, ge=1, le=100),
):
    pool = await _get_pool()
    try:
        conditions = ["is_active = TRUE"]
        params     = []
        idx        = 1

        if q:
            conditions.append(
                f"(LOWER(code) LIKE LOWER(${idx}) OR LOWER(description) LIKE LOWER(${idx+1}))"
            )
            params.extend([f"{q}%", f"%{q}%"])
            idx += 2

        if severity:
            conditions.append(f"severity = ${idx}")
            params.append(severity.lower())
            idx += 1

        if category:
            conditions.append(f"LOWER(category) LIKE LOWER(${idx})")
            params.append(f"%{category}%")
            idx += 1

        params.append(limit)
        where = " AND ".join(conditions)

        rows = await pool.fetch(
            f"""
            SELECT code, description, category, severity, is_active
            FROM icd_codes
            WHERE {where}
            ORDER BY code
            LIMIT ${idx}
            """,
            *params,
        )

        return {
            "total":   len(rows),
            "results": [dict(r) for r in rows],
        }

    except Exception as exc:
        logger.error("ICD search error: %s", exc)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


# ─────────────────────────────────────────────
# GET /analyze/icd/{code}  — Single ICD Detail
# ─────────────────────────────────────────────

@router.get(
    "/icd/{code}",
    status_code=status.HTTP_200_OK,
    summary="Get a single ICD-10 code detail",
    responses={
        404: {"description": "ICD code not found", "model": ErrorResponse},
    },
)
async def get_icd_detail(code: str):
    pool = await _get_pool()
    try:
        row = await pool.fetchrow(
            """
            SELECT code, description, category, severity, is_active
            FROM icd_codes
            WHERE UPPER(code) = UPPER($1)
            """,
            code,
        )
        if not row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"ICD-10 code '{code}' not found in database.",
            )

        # Also fetch mapped procedures
        procedures = await pool.fetch(
            """
            SELECT p.code, p.description, p.requires_auth, ipm.is_primary
            FROM icd_procedure_mapping ipm
            JOIN procedure_codes p ON p.code = ipm.procedure_code
            WHERE ipm.icd_code = $1 AND p.is_active = TRUE
            ORDER BY ipm.is_primary DESC
            """,
            row["code"],
        )

        return {
            **dict(row),
            "mapped_procedures": [dict(p) for p in procedures],
        }

    except HTTPException:
        raise
    except Exception as exc:
        logger.error("ICD detail error for %s: %s", code, exc)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


# ─────────────────────────────────────────────
# GET /analyze/procedures  — Search Procedures
# ─────────────────────────────────────────────

@router.get(
    "/procedures",
    status_code=status.HTTP_200_OK,
    summary="Search procedure codes",
    description="Search CPT/procedure codes by keyword or code. Used to validate procedure input.",
)
async def search_procedures(
    q:             str  = Query(default="",    description="Search keyword or procedure code prefix"),
    requires_auth: bool = Query(default=None,  description="Filter by requires_auth flag"),
    category:      str  = Query(default=None,  description="Filter by category"),
    limit:         int  = Query(default=20, ge=1, le=100),
):
    pool = await _get_pool()
    try:
        conditions = ["is_active = TRUE"]
        params     = []
        idx        = 1

        if q:
            conditions.append(
                f"(LOWER(code) LIKE LOWER(${idx}) OR LOWER(description) LIKE LOWER(${idx+1}))"
            )
            params.extend([f"{q}%", f"%{q}%"])
            idx += 2

        if requires_auth is not None:
            conditions.append(f"requires_auth = ${idx}")
            params.append(requires_auth)
            idx += 1

        if category:
            conditions.append(f"LOWER(category) LIKE LOWER(${idx})")
            params.append(f"%{category}%")
            idx += 1

        params.append(limit)
        where = " AND ".join(conditions)

        rows = await pool.fetch(
            f"""
            SELECT code, description, category, requires_auth, is_active
            FROM procedure_codes
            WHERE {where}
            ORDER BY code
            LIMIT ${idx}
            """,
            *params,
        )

        return {
            "total":   len(rows),
            "results": [dict(r) for r in rows],
        }

    except Exception as exc:
        logger.error("Procedure search error: %s", exc)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


# ─────────────────────────────────────────────
# GET /analyze/tpa-list  — TPA Dropdown Data
# ─────────────────────────────────────────────

@router.get(
    "/tpa-list",
    status_code=status.HTTP_200_OK,
    summary="List all TPAs for frontend dropdown",
    description="""
Returns all unique TPA names from the payer_rules table along with
their rule counts. Used to populate the TPA dropdown in Insurance Details.
    """,
)
async def get_tpa_list():
    pool = await _get_pool()
    try:
        rows = await pool.fetch(
            """
            SELECT tpa_name, COUNT(*) AS rule_count
            FROM payer_rules
            WHERE is_active = TRUE
            GROUP BY tpa_name
            ORDER BY tpa_name
            """
        )
        return {
            "total": len(rows),
            "tpas": [{"tpa_name": r["tpa_name"], "rule_count": r["rule_count"]} for r in rows],
        }
    except Exception as exc:
        logger.error("TPA list error: %s", exc)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


# ─────────────────────────────────────────────
# GET /analyze/conflict-rules  — Admin View
# ─────────────────────────────────────────────

@router.get(
    "/conflict-rules",
    status_code=status.HTTP_200_OK,
    summary="List all active conflict rules",
    description="Returns all active conflict rules from PostgreSQL. Useful for admin/debug views.",
)
async def get_conflict_rules(
    severity:      str = Query(default=None, description="Filter by severity: low|medium|high"),
    conflict_type: str = Query(default=None, description="Filter by type: contraindication|age_restriction|etc."),
    limit:         int = Query(default=50, ge=1, le=200),
):
    pool = await _get_pool()
    try:
        conditions = ["is_active = TRUE"]
        params     = []
        idx        = 1

        if severity:
            conditions.append(f"severity = ${idx}")
            params.append(severity.lower())
            idx += 1

        if conflict_type:
            conditions.append(f"conflict_type = ${idx}")
            params.append(conflict_type.lower())
            idx += 1

        params.append(limit)
        where = " AND ".join(conditions)

        rows = await pool.fetch(
            f"""
            SELECT
                rule_name, icd_code, procedure_code,
                conflict_type, severity, description, action
            FROM conflict_rules
            WHERE {where}
            ORDER BY
                CASE severity WHEN 'high' THEN 1 WHEN 'medium' THEN 2 ELSE 3 END,
                rule_name
            LIMIT ${idx}
            """,
            *params,
        )

        return {
            "total":   len(rows),
            "results": [dict(r) for r in rows],
        }

    except Exception as exc:
        logger.error("Conflict rules fetch error: %s", exc)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))