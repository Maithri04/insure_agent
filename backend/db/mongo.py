"""
db/mongo.py

MongoDB connection using Motor (async driver for FastAPI).

Features:
  • Lazy initialization — client created on first use, not at import time
  • Single client instance reused across all requests (connection pooling)
  • Health check function used at startup
  • Collections:
      audit_logs       — every agent request/response stored here
      submitted_claims — claims marked as submitted via POST /agent/submit
  • Indexes created automatically on first connect
"""

import os
import logging
from typing import Optional
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

logger = logging.getLogger(__name__)

# Module-level singletons — initialized lazily
_client: Optional[AsyncIOMotorClient] = None
_db:     Optional[AsyncIOMotorDatabase] = None


# ─────────────────────────────────────────────────────────────────────────────
# Connection
# ─────────────────────────────────────────────────────────────────────────────

def _get_client() -> AsyncIOMotorClient:
    """
    Return the Motor client, creating it if it doesn't exist yet.
    Reads MONGO_URL from environment at call time (never at import time).
    """
    global _client
    if _client is None:
        mongo_url = os.getenv("MONGO_URL")
        if not mongo_url:
            raise EnvironmentError(
                "MONGO_URL is not set. Add it to your .env file.\n"
                "Example: MONGO_URL=mongodb://admin:secret@mongo:27017/healthcare?authSource=admin"
            )
        _client = AsyncIOMotorClient(
            mongo_url,
            serverSelectionTimeoutMS=5000,   # 5s timeout for connection attempts
            connectTimeoutMS=5000,
            socketTimeoutMS=10000,
            maxPoolSize=20,                  # Max concurrent connections
            minPoolSize=2,                   # Keep minimum connections warm
        )
        logger.info("MongoDB client created (pool: 2–20 connections)")
    return _client


def get_mongo_db() -> AsyncIOMotorDatabase:
    """
    Return the Motor database instance.
    Database name is read from MONGO_DB env var (default: 'healthcare').

    Usage in agent_service.py:
        from db.mongo import get_mongo_db
        mongo_db = get_mongo_db()
        await mongo_db["audit_logs"].insert_one({...})
    """
    global _db
    if _db is None:
        db_name = os.getenv("MONGO_DB", "healthcare")
        _db = _get_client()[db_name]
        logger.info("MongoDB database handle acquired: '%s'", db_name)
    return _db


# ─────────────────────────────────────────────────────────────────────────────
# Index Setup — called once at startup
# ─────────────────────────────────────────────────────────────────────────────

async def create_mongo_indexes() -> None:
    """
    Create indexes on MongoDB collections for fast querying.
    Called during application startup (lifespan in main.py).
    Safe to call multiple times — MongoDB ignores existing indexes.
    """
    try:
        db = get_mongo_db()

        # audit_logs indexes
        await db["audit_logs"].create_index("request_id",   unique=True)
        await db["audit_logs"].create_index("timestamp")
        await db["audit_logs"].create_index("patient_name")
        await db["audit_logs"].create_index("tpa")
        await db["audit_logs"].create_index("icd_code")
        await db["audit_logs"].create_index("approval_recommendation")
        await db["audit_logs"].create_index("submitted")
        await db["audit_logs"].create_index(
            [("timestamp", -1)],   # descending for "most recent first" queries
        )

        # submitted_claims indexes
        await db["submitted_claims"].create_index("request_id",  unique=True)
        await db["submitted_claims"].create_index("submitted_at")
        await db["submitted_claims"].create_index("tpa")

        logger.info("MongoDB indexes created/verified on audit_logs + submitted_claims")

    except Exception as exc:
        # Non-fatal — app can still run without indexes (just slower queries)
        logger.warning("MongoDB index creation failed (non-fatal): %s", exc)


# ─────────────────────────────────────────────────────────────────────────────
# Health Check
# ─────────────────────────────────────────────────────────────────────────────

async def check_mongo_health() -> dict:
    """
    Ping MongoDB and return a health status dict.
    Called from GET /health endpoint in main.py.
    """
    try:
        db = get_mongo_db()
        await db.command("ping")
        return {"status": "ok", "database": db.name}
    except Exception as exc:
        logger.error("MongoDB health check failed: %s", exc)
        return {"status": "error", "detail": str(exc)}


# ─────────────────────────────────────────────────────────────────────────────
# Graceful Shutdown
# ─────────────────────────────────────────────────────────────────────────────

async def close_mongo_connection() -> None:
    """
    Close the Motor client connection pool.
    Called during application shutdown (lifespan in main.py).
    """
    global _client, _db
    if _client is not None:
        _client.close()
        _client = None
        _db     = None
        logger.info("MongoDB connection closed")