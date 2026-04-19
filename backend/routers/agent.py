import logging
from fastapi import APIRouter, HTTPException, status

from schemas.agent_schema import AgentRequest, AgentResponse
from schemas.models import ErrorResponse

logger = logging.getLogger(__name__)

router = APIRouter(
    tags=["Smart Agent"],
)

async def _get_db():
    try:
        from db import get_postgres_pool, get_mongo_db
        pg_pool  = await get_postgres_pool()
        mongo_db = get_mongo_db()
        return pg_pool, mongo_db
    except Exception as exc:
        logger.error("DB connection failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Database connection unavailable: {exc}",
        )

@router.post(
    "/agent-run",
    response_model=AgentResponse,
    status_code=status.HTTP_200_OK,
    summary="Run the full agent pipeline",
)
async def agent_run(payload: AgentRequest) -> AgentResponse:
    pg_pool, mongo_db = await _get_db()
    try:
        from agents.agent_service import run_agent
        return await run_agent(payload, pg_pool, mongo_db)
    except EnvironmentError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc))
    except Exception as exc:
        logger.exception("Agent /agent-run failed for: %s", payload.patient_name)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))