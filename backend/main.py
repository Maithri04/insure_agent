"""
main.py

InsureMind AI — FastAPI Application Entry Point

Registers:
  • All routers   : soap, agent, analyze, form, submit
  • Middleware     : CORS
  • Lifespan       : DB connections, indexes, schema validation, shutdown cleanup
  • Health check   : GET /health
  • Docs           : GET /docs (Swagger), GET /redoc
"""

import os
import logging
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# Load .env before anything else
load_dotenv()

# ─────────────────────────────────────────────
# Logging
# ─────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s — %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────
# Lifespan — Startup & Shutdown
# ─────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Startup:
      1. Validate environment variables
      2. Create MongoDB indexes
      3. Validate PostgreSQL schema (checks seed.sql was run)
      4. Ensure payer_rules table exists (with Demo TPA seed data)

    Shutdown:
      1. Close MongoDB client
      2. Close PostgreSQL pool
    """
    logger.info("🚀 InsureMind AI starting up...")

    # ── Validate critical env vars ──────────────
    if not os.getenv("GROQ_API_KEY"):
        logger.warning(
            "⚠  GROQ_API_KEY not set — POST /agent/verify and POST /soap "
            "will return 503 until configured."
        )
    else:
        logger.info("✅ GROQ_API_KEY detected")

    # ── MongoDB setup ───────────────────────────
    try:
        from db import create_mongo_indexes
        await create_mongo_indexes()
        logger.info("✅ MongoDB indexes ready")
    except Exception as exc:
        logger.warning("⚠  MongoDB setup failed (non-fatal): %s", exc)

    # ── PostgreSQL setup ────────────────────────
    try:
        from db import validate_schema, ensure_payer_rules_table
        schema_status = await validate_schema()
        if schema_status.get("status") == "ok":
            logger.info(
                "✅ PostgreSQL schema validated — %d ICD codes | %d conflict rules",
                schema_status.get("icd_codes", 0),
                schema_status.get("conflict_rules", 0),
            )
        else:
            logger.warning(
                "⚠  PostgreSQL schema incomplete — missing tables: %s. "
                "Run db/seed.sql to initialize.",
                schema_status.get("missing_tables", []),
            )
        await ensure_payer_rules_table()
        logger.info("✅ payer_rules table ready")
    except Exception as exc:
        logger.warning("⚠  PostgreSQL setup failed (non-fatal): %s", exc)

    logger.info("✅ InsureMind AI is ready — visit /docs for API documentation")

    yield  # ── Application running ──────────────

    # ── Shutdown ────────────────────────────────
    logger.info("🛑 InsureMind AI shutting down...")
    try:
        from db import close_mongo_connection, close_postgres_pool
        await close_mongo_connection()
        await close_postgres_pool()
        logger.info("✅ Database connections closed")
    except Exception as exc:
        logger.warning("⚠  Shutdown cleanup error: %s", exc)


# ─────────────────────────────────────────────
# FastAPI App
# ─────────────────────────────────────────────

app = FastAPI(
    title="InsureMind AI — Prior Authorization API",
    description="""
## InsureMind AI Backend

A production-ready agentic AI system for insurance prior authorization in healthcare.

### Agent Pipeline (20 Steps)
1. **SOAP Generation** — Converts raw doctor notes to structured SOAP format
2. **ICD-10 Prediction** — LLM predicts the most accurate diagnosis code
3. **ICD Validation** — Validates against PostgreSQL database, corrects if invalid
4. **Procedure Mapping** — Maps ICD code to appropriate procedure
5. **Conflict Check** — Rule engine detects diagnosis-procedure conflicts
6. **Evidence Detection** — Checks 5 clinical justification fields
7. **Justification** — Generates, scores, and rewrites clinical justification
8. **Risk Analysis** — Flags high/medium/low severity issues
9. **Approval Scoring** — Weighted model calculates approval probability
10. **Explainability** — Human-readable reasons and suggestions

### Key Endpoints
- `POST /agent/verify` — Run full pipeline (Verify button)
- `POST /agent/submit` — Submit authorization request (Submit button)
- `GET  /agent/history` — Retrieve past submissions
- `POST /soap` — Generate SOAP note only
- `GET  /health` — System health check
    """,
    version="1.0.0",
    contact={
        "name":  "InsureMind AI Team",
        "email": "dev@insuremind.ai",
    },
    license_info={"name": "MIT"},
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)


# ─────────────────────────────────────────────
# CORS Middleware
# ─────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv(
        "ALLOWED_ORIGINS",
        "http://localhost:5173,http://localhost:3000"
    ).split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─────────────────────────────────────────────
# Routers
# ─────────────────────────────────────────────

from routers.agent import router as agent_router
from routers.soap  import router as soap_router

app.include_router(agent_router)
app.include_router(soap_router)


# ─────────────────────────────────────────────
# Health Check
# ─────────────────────────────────────────────

@app.get(
    "/health",
    tags=["System"],
    summary="System health check",
)
async def health_check():
    """Returns health status for API, MongoDB, and PostgreSQL."""
    from db import check_mongo_health, check_postgres_health

    mongo_health    = await check_mongo_health()
    postgres_health = await check_postgres_health()

    overall = (
        "ok"
        if mongo_health.get("status") == "ok"
        and postgres_health.get("status") == "ok"
        else "degraded"
    )

    return JSONResponse(
        status_code=200,
        content={
            "status":              overall,
            "version":             app.version,
            "groq_key_configured": bool(os.getenv("GROQ_API_KEY")),
            "mongodb":             mongo_health,
            "postgresql":          postgres_health,
        },
    )


# ─────────────────────────────────────────────
# Root
# ─────────────────────────────────────────────

@app.get("/", tags=["System"], summary="Root endpoint")
async def root():
    return {
        "message": "InsureMind AI API is running.",
        "docs":    "/docs",
        "health":  "/health",
        "version": app.version,
    }