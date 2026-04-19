"""
services/case_service.py

Case Storage Service — saves full agent pipeline output to PostgreSQL.

Responsibilities:
  • Generate unique sequential case_id: HOSP1, HOSP2, HOSP3...
  • Save complete agent result to cases table
  • Update pdf_path after PDF is generated
  • Fetch case by case_id (with patient_name validation)
  • Fetch paginated history list
  • Log every action to MongoDB audit_logs

Cases table (defined in seed.sql):
  id               SERIAL PRIMARY KEY
  case_id          TEXT UNIQUE          — e.g. HOSP1, HOSP2
  patient_name     TEXT
  patient_age      INTEGER
  patient_gender   TEXT
  tpa              TEXT
  disease_description TEXT
  medications      TEXT
  procedure        TEXT
  duration_of_symptoms TEXT
  prior_treatment  TEXT
  severity         TEXT
  investigations   TEXT
  specialist_referral TEXT
  soap_json        JSONB
  icd_code         TEXT
  icd_description  TEXT
  procedure_code   TEXT
  procedure_description TEXT
  justification_text TEXT
  justification_score NUMERIC
  evidence_score   NUMERIC
  missing_evidence JSONB
  risk_flags       JSONB
  conflicts        JSONB
  condition_type   TEXT
  approval_probability NUMERIC
  approval_recommendation TEXT
  reasons          JSONB
  suggestions      JSONB
  pdf_path         TEXT
  created_at       TIMESTAMP DEFAULT NOW()
"""

import json
import logging
from typing import Optional
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Ensure cases table exists
# ─────────────────────────────────────────────────────────────────────────────

async def ensure_cases_table(pool) -> None:
    """
    Create the cases table if it doesn't exist.
    Called once at application startup.
    """
    sql = """
    CREATE TABLE IF NOT EXISTS cases (
        id                      SERIAL PRIMARY KEY,
        case_id                 TEXT UNIQUE NOT NULL,
        patient_name            TEXT NOT NULL,
        patient_age             INTEGER NOT NULL,
        patient_gender          TEXT NOT NULL,
        tpa                     TEXT NOT NULL,
        disease_description     TEXT,
        medications             TEXT,
        procedure               TEXT,
        duration_of_symptoms    TEXT,
        prior_treatment         TEXT,
        severity                TEXT,
        investigations          TEXT,
        specialist_referral     TEXT,
        soap_json               JSONB,
        icd_code                TEXT,
        icd_description         TEXT,
        procedure_code          TEXT,
        procedure_description   TEXT,
        justification_text      TEXT,
        justification_score     NUMERIC(5,3),
        evidence_score          NUMERIC(5,3),
        missing_evidence        JSONB,
        risk_flags              JSONB,
        conflicts               JSONB,
        condition_type          TEXT,
        approval_probability    NUMERIC(5,3),
        approval_recommendation TEXT,
        reasons                 JSONB,
        suggestions             JSONB,
        pdf_path                TEXT,
        created_at              TIMESTAMP DEFAULT NOW()
    );

    CREATE INDEX IF NOT EXISTS idx_cases_case_id      ON cases (case_id);
    CREATE INDEX IF NOT EXISTS idx_cases_patient_name ON cases (LOWER(patient_name));
    CREATE INDEX IF NOT EXISTS idx_cases_created_at   ON cases (created_at DESC);
    """
    try:
        async with pool.acquire() as conn:
            await conn.execute(sql)
        logger.info("cases table ensured")
    except Exception as exc:
        logger.warning("cases table setup failed (non-fatal): %s", exc)


# ─────────────────────────────────────────────────────────────────────────────
# Generate Case ID
# ─────────────────────────────────────────────────────────────────────────────

async def _generate_case_id(conn) -> str:
    """
    Generate next sequential case_id: HOSP1, HOSP2, HOSP3...
    Uses PostgreSQL sequence via SERIAL id — guaranteed unique and non-repeating.
    Inserts a placeholder row to reserve the id, then returns the case_id.
    """
    # Get next value from the cases_id_seq sequence
    next_id = await conn.fetchval("SELECT nextval('cases_id_seq')")
    return f"HOSP{next_id}"


# ─────────────────────────────────────────────────────────────────────────────
# Save Case
# ─────────────────────────────────────────────────────────────────────────────

async def save_case(
    req,          # CaseSaveRequest
    pool,
    mongo_db,
) -> dict:
    """
    Save the full agent pipeline output to PostgreSQL cases table.

    Steps:
      1. Generate sequential case_id (HOSP1, HOSP2...)
      2. Insert all fields into cases table
      3. Log action to MongoDB audit_logs
      4. Return case_id and created_at

    Returns: {"case_id": "HOSP5", "created_at": "..."}
    """
    try:
        async with pool.acquire() as conn:
            # Step 1: Generate unique case_id using transaction
            async with conn.transaction():
                # Reserve sequence value — atomic and safe under concurrent requests
                next_id = await conn.fetchval(
                    "INSERT INTO cases (case_id, patient_name, patient_age, patient_gender, "
                    "tpa, disease_description, medications, procedure, "
                    "duration_of_symptoms, prior_treatment, severity, investigations, specialist_referral, "
                    "soap_json, icd_code, icd_description, procedure_code, procedure_description, "
                    "justification_text, justification_score, evidence_score, missing_evidence, "
                    "risk_flags, conflicts, condition_type, approval_probability, approval_recommendation, "
                    "reasons, suggestions) "
                    "VALUES ("
                    "   'PLACEHOLDER'::text, $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, "
                    "   $13::jsonb, $14, $15, $16, $17, $18, $19, $20, $21::jsonb, "
                    "   $22::jsonb, $23::jsonb, $24, $25, $26, $27::jsonb, $28::jsonb"
                    ") RETURNING id",
                    # Patient
                    req.patient_name,
                    req.patient_age,
                    req.patient_gender,
                    req.tpa,
                    req.disease_description,
                    req.medications,
                    req.procedure,
                    # Justification fields
                    req.duration_of_symptoms,
                    req.prior_treatment,
                    req.severity,
                    req.investigations,
                    req.specialist_referral,
                    # SOAP as JSON
                    json.dumps({
                        "subjective": req.soap_subjective,
                        "objective":  req.soap_objective,
                        "assessment": req.soap_assessment,
                        "plan":       req.soap_plan,
                    }),
                    # ICD + Procedure
                    req.icd_code,
                    req.icd_description,
                    req.procedure_code,
                    req.procedure_description,
                    # Justification
                    req.justification_text,
                    req.justification_score,
                    req.evidence_score,
                    json.dumps(req.missing_evidence),
                    # Risk
                    json.dumps(req.risk_flags),
                    json.dumps(req.conflicts),
                    req.condition_type,
                    # Approval
                    req.approval_probability,
                    req.approval_recommendation,
                    # Explainability
                    json.dumps(req.reasons),
                    json.dumps(req.suggestions),
                )

                # Step 2: Set the real case_id now that we have the auto-incremented id
                case_id = f"HOSP{next_id}"
                await conn.execute(
                    "UPDATE cases SET case_id = $1 WHERE id = $2",
                    case_id,
                    next_id,
                )

        # Step 3: Log to MongoDB
        try:
            await mongo_db["audit_logs"].insert_one({
                "action":      "case_saved",
                "case_id":     case_id,
                "patient_name": req.patient_name,
                "tpa":          req.tpa,
                "icd_code":     req.icd_code,
                "approval_recommendation": req.approval_recommendation,
                "timestamp":    datetime.now(timezone.utc),
            })
        except Exception as mongo_exc:
            logger.warning("MongoDB audit log failed for case_saved: %s", mongo_exc)

        logger.info("Case saved — case_id: %s | patient: %s", case_id, req.patient_name)
        return {"case_id": case_id, "created_at": datetime.now(timezone.utc).isoformat()}

    except Exception as exc:
        logger.error("save_case failed: %s", exc)
        raise


# ─────────────────────────────────────────────────────────────────────────────
# Update PDF Path
# ─────────────────────────────────────────────────────────────────────────────

async def update_pdf_path(case_id: str, pdf_path: str, pool, mongo_db) -> None:
    """
    Update the pdf_path column after PDF has been generated.
    Called by pdf_service after successfully writing the PDF file.
    """
    try:
        async with pool.acquire() as conn:
            await conn.execute(
                "UPDATE cases SET pdf_path = $1 WHERE case_id = $2",
                pdf_path,
                case_id,
            )

        # Log to MongoDB
        try:
            await mongo_db["audit_logs"].insert_one({
                "action":    "pdf_generated",
                "case_id":   case_id,
                "pdf_path":  pdf_path,
                "timestamp": datetime.now(timezone.utc),
            })
        except Exception:
            pass

        logger.info("PDF path updated — case_id: %s | path: %s", case_id, pdf_path)

    except Exception as exc:
        logger.error("update_pdf_path failed for %s: %s", case_id, exc)
        raise


# ─────────────────────────────────────────────────────────────────────────────
# Fetch Case by ID + Patient Name
# ─────────────────────────────────────────────────────────────────────────────

async def get_case(case_id: str, patient_name: str, pool) -> Optional[dict]:
    """
    Fetch a full case record by case_id + patient_name (case-insensitive match).
    Used by POST /case/access — doctor enters both to retrieve their report.
    Returns None if not found or name doesn't match.
    """
    try:
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT *
                FROM cases
                WHERE case_id = $1
                  AND LOWER(patient_name) = LOWER($2)
                """,
                case_id.upper(),
                patient_name.strip(),
            )
        if not row:
            return None
        return _serialize_case_row(dict(row))
    except Exception as exc:
        logger.error("get_case failed for %s: %s", case_id, exc)
        raise


async def get_case_by_id(case_id: str, pool) -> Optional[dict]:
    """
    Fetch a case by case_id only (no patient name check).
    Used internally by PDF download endpoint.
    """
    try:
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM cases WHERE case_id = $1",
                case_id.upper(),
            )
        if not row:
            return None
        return _serialize_case_row(dict(row))
    except Exception as exc:
        logger.error("get_case_by_id failed for %s: %s", case_id, exc)
        raise


# ─────────────────────────────────────────────────────────────────────────────
# Fetch History (Paginated)
# ─────────────────────────────────────────────────────────────────────────────

async def get_case_history(
    pool,
    limit:  int = 20,
    skip:   int = 0,
    search: Optional[str] = None,
) -> dict:
    """
    Fetch paginated list of all cases for the history view.
    Optionally search by patient name.
    Returns lightweight records (no SOAP/justification text).
    """
    try:
        conditions = ["1=1"]
        params     = []
        idx        = 1

        if search:
            conditions.append(f"LOWER(patient_name) LIKE LOWER(${idx})")
            params.append(f"%{search}%")
            idx += 1

        where = " AND ".join(conditions)

        async with pool.acquire() as conn:
            total = await conn.fetchval(
                f"SELECT COUNT(*) FROM cases WHERE {where}",
                *params,
            )

            params_with_limit = params + [limit, skip]
            rows = await conn.fetch(
                f"""
                SELECT
                    case_id, patient_name, patient_age, patient_gender, tpa,
                    icd_code, icd_description, procedure_code, condition_type,
                    approval_probability, approval_recommendation,
                    pdf_path, created_at
                FROM cases
                WHERE {where}
                ORDER BY created_at DESC
                LIMIT ${idx} OFFSET ${idx + 1}
                """,
                *params_with_limit,
            )

        cases = []
        for row in rows:
            r = dict(row)
            r["created_at"]    = r["created_at"].isoformat() if r.get("created_at") else None
            r["pdf_available"] = bool(r.get("pdf_path"))
            cases.append(r)

        return {
            "total": total,
            "page":  skip // limit + 1,
            "cases": cases,
        }

    except Exception as exc:
        logger.error("get_case_history failed: %s", exc)
        raise


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _serialize_case_row(row: dict) -> dict:
    """
    Convert a raw PostgreSQL row dict into a clean serializable dict.
    Parses JSONB columns and converts datetime to ISO string.
    """
    # Parse JSONB fields
    for jsonb_field in ("soap_json", "missing_evidence", "risk_flags", "conflicts", "reasons", "suggestions"):
        val = row.get(jsonb_field)
        if isinstance(val, str):
            try:
                row[jsonb_field] = json.loads(val)
            except Exception:
                pass
        # asyncpg returns JSONB as dict/list already — no-op if already parsed

    # Serialize datetime
    if "created_at" in row and row["created_at"]:
        row["created_at"] = row["created_at"].isoformat()

    # Add convenience field
    row["pdf_available"] = bool(row.get("pdf_path"))

    return row

# ─────────────────────────────────────────────────────────────────────────────
# Save SOAP Only Case
# ─────────────────────────────────────────────────────────────────────────────

async def save_soap_case(req, soap_res, pool, mongo_db) -> dict:
    """
    Saves a partial case when only the /soap endpoint is called.
    """
    try:
        async with pool.acquire() as conn:
            async with conn.transaction():
                next_id = await conn.fetchval(
                    "INSERT INTO cases (case_id, patient_name, patient_age, patient_gender, "
                    "tpa, disease_description, medications, soap_json, icd_code, condition_type, approval_recommendation) "
                    "VALUES ('PLACEHOLDER', $1, $2, $3, 'Unknown', $4, $5, $6::jsonb, $7, 'Unknown', 'PENDING') RETURNING id",
                    req.patient_name, req.patient_age, req.patient_gender.value, req.raw_notes, req.medications,
                    json.dumps({
                        "subjective": soap_res.subjective,
                        "objective": soap_res.objective,
                        "assessment": soap_res.assessment,
                        "plan": soap_res.plan,
                    }),
                    soap_res.icd10_code,
                )
                case_id = f"HOSP{next_id}"
                await conn.execute("UPDATE cases SET case_id = $1 WHERE id = $2", case_id, next_id)
        
        try:
            await mongo_db["audit_logs"].insert_one({
                "action": "soap_case_saved",
                "case_id": case_id,
                "patient_name": req.patient_name,
                "timestamp": datetime.now(timezone.utc),
            })
        except Exception:
            pass

        return {"case_id": case_id, "created_at": datetime.now(timezone.utc).isoformat()}
    except Exception as exc:
        logger.error("save_soap_case failed: %s", exc)
        raise