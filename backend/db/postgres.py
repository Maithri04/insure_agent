"""
db/postgres.py

PostgreSQL connection using asyncpg (high-performance async driver).

Features:
  • Lazy pool initialization — pool created on first request, not at import time
  • Shared connection pool across all FastAPI requests (10–20 connections)
  • Pool is reused across requests via module-level singleton
  • Health check function used at startup
  • Schema validation — checks that all required tables exist on startup
  • Graceful shutdown — pool closed cleanly when app stops

Tables expected (from seed.sql):
  icd_codes              — 110+ validated ICD-10 codes with severity
  procedure_codes        — 50+ CPT/procedure codes
  icd_procedure_mapping  — ICD → procedure relationships
  conflict_rules         — Diagnosis-procedure conflict rules
  payer_rules            — TPA-specific approval rules
"""

import os
import logging
from typing import Optional
import asyncpg

logger = logging.getLogger(__name__)

# Module-level singleton — lazy initialized
_pool: Optional[asyncpg.Pool] = None

# Tables that must exist (created + seeded by seed.sql)
_REQUIRED_TABLES = [
    "icd_codes",
    "procedure_codes",
    "icd_procedure_mapping",
    "conflict_rules",
]


# ─────────────────────────────────────────────────────────────────────────────
# Pool Creation
# ─────────────────────────────────────────────────────────────────────────────

async def get_postgres_pool() -> asyncpg.Pool:
    """
    Return the asyncpg connection pool, creating it on first call.
    Reads POSTGRES_URL from environment at call time (never at import time).

    Usage in agent_service.py:
        from db.postgres import get_postgres_pool
        pool = await get_postgres_pool()
        row  = await pool.fetchrow("SELECT * FROM icd_codes WHERE code = $1", code)
    """
    global _pool
    if _pool is None:
        postgres_url = os.getenv("POSTGRES_URL")
        if not postgres_url:
            raise EnvironmentError(
                "POSTGRES_URL is not set. Add it to your .env file.\n"
                "Example: POSTGRES_URL=postgresql://admin:secret@postgres:5432/healthcare"
            )

        try:
            _pool = await asyncpg.create_pool(
                dsn=postgres_url,
                min_size=2,          # Keep 2 connections warm at all times
                max_size=20,         # Max concurrent connections
                command_timeout=30,  # Kill queries running > 30s
                max_inactive_connection_lifetime=300,  # Recycle idle connections every 5min
            )
            logger.info("PostgreSQL connection pool created (size: 2–20)")
        except Exception as exc:
            logger.error("Failed to create PostgreSQL pool: %s", exc)
            raise RuntimeError(f"PostgreSQL connection failed: {exc}") from exc

    return _pool


# ─────────────────────────────────────────────────────────────────────────────
# Schema Validation — called at startup
# ─────────────────────────────────────────────────────────────────────────────

async def validate_schema() -> dict:
    """
    Check that all required tables exist in the database.
    Called once at application startup (lifespan in main.py).

    Returns a status dict with any missing tables identified.
    """
    try:
        pool = await get_postgres_pool()
        async with pool.acquire() as conn:
            existing = await conn.fetch(
                """
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                  AND table_type   = 'BASE TABLE'
                """
            )
        existing_names = {row["table_name"] for row in existing}
        missing = [t for t in _REQUIRED_TABLES if t not in existing_names]

        if missing:
            logger.warning(
                "Missing PostgreSQL tables: %s — run seed.sql to initialize",
                missing,
            )
            return {"status": "incomplete", "missing_tables": missing}

        # Quick row count check
        pool = await get_postgres_pool()
        async with pool.acquire() as conn:
            icd_count  = await conn.fetchval("SELECT COUNT(*) FROM icd_codes WHERE is_active = TRUE")
            rule_count = await conn.fetchval("SELECT COUNT(*) FROM conflict_rules WHERE is_active = TRUE")

        logger.info(
            "PostgreSQL schema validated — %d ICD codes | %d conflict rules",
            icd_count, rule_count,
        )
        return {
            "status":        "ok",
            "icd_codes":     icd_count,
            "conflict_rules": rule_count,
        }

    except Exception as exc:
        logger.error("Schema validation error: %s", exc)
        return {"status": "error", "detail": str(exc)}


async def ensure_payer_rules_table() -> None:
    """
    Create the payer_rules table if it doesn't exist yet.
    This table may not be in the initial seed.sql but is needed by payer_rules.py.
    """
    create_sql = """
    CREATE TABLE IF NOT EXISTS payer_rules (
        id                   SERIAL PRIMARY KEY,
        tpa_name             VARCHAR(200) NOT NULL,
        rule_name            VARCHAR(200) NOT NULL,
        rule_type            VARCHAR(20)  NOT NULL CHECK (
                                 rule_type IN ('boost','reduce','deny','require_docs')
                             ),
        condition_category   VARCHAR(100),
        procedure_code       VARCHAR(20),
        condition_type       VARCHAR(20)  CHECK (
                                 condition_type IN ('minor','moderate','serious','critical')
                             ),
        min_evidence_score   NUMERIC(4,3),
        probability_modifier NUMERIC(5,3),
        description          TEXT         NOT NULL,
        action               VARCHAR(20)  NOT NULL,
        metadata             JSONB,
        is_active            BOOLEAN      DEFAULT TRUE,
        created_at           TIMESTAMP    DEFAULT NOW()
    );

    CREATE INDEX IF NOT EXISTS idx_payer_rules_tpa
        ON payer_rules (LOWER(tpa_name));

    -- Seed a few example payer rules for Demo TPA
    INSERT INTO payer_rules
        (tpa_name, rule_name, rule_type, condition_category, condition_type,
         min_evidence_score, probability_modifier, description, action)
    VALUES
        ('Demo TPA',
         'Demo TPA — Cardiac Fast Track',
         'boost', 'Cardiac', 'critical', NULL, 0.10,
         'Demo TPA fast-tracks all critical cardiac cases with complete documentation.', 'approve'),

        ('Demo TPA',
         'Demo TPA — Minor Condition Reduction',
         'reduce', NULL, 'minor', NULL, -0.08,
         'Demo TPA applies stricter scrutiny to minor conditions.', 'review'),

        ('Demo TPA',
         'Demo TPA — Oncology Documentation Requirement',
         'require_docs', 'Oncology', NULL, NULL, 0.0,
         'Demo TPA requires tumor board approval letter for all oncology claims.', 'review'),

        ('Demo TPA',
         'Demo TPA — Incomplete Evidence Penalty',
         'reduce', NULL, NULL, 0.6, -0.12,
         'Demo TPA reduces approval probability for claims with less than 60% evidence completeness.', 'review')
    ON CONFLICT DO NOTHING;
    """
    try:
        pool = await get_postgres_pool()
        async with pool.acquire() as conn:
            await conn.execute(create_sql)
        logger.info("payer_rules table ensured (created or already exists)")
    except Exception as exc:
        logger.warning("payer_rules table setup failed (non-fatal): %s", exc)


# ─────────────────────────────────────────────────────────────────────────────
# Health Check
# ─────────────────────────────────────────────────────────────────────────────

async def check_postgres_health() -> dict:
    """
    Run a lightweight health check against PostgreSQL.
    Called from GET /health endpoint in main.py.
    """
    try:
        pool = await get_postgres_pool()
        async with pool.acquire() as conn:
            version = await conn.fetchval("SELECT version()")
        return {
            "status":  "ok",
            "version": version.split(",")[0] if version else "unknown",
        }
    except Exception as exc:
        logger.error("PostgreSQL health check failed: %s", exc)
        return {"status": "error", "detail": str(exc)}


# ─────────────────────────────────────────────────────────────────────────────
# Graceful Shutdown
# ─────────────────────────────────────────────────────────────────────────────

async def close_postgres_pool() -> None:
    """
    Close the asyncpg connection pool gracefully.
    Called during application shutdown (lifespan in main.py).
    """
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None
        logger.info("PostgreSQL connection pool closed")