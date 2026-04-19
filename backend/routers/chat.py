"""
routers/chat.py

Chatbot Endpoint — InsureMind AI Medical Assistant.

Endpoint:
  POST /chat — send a message, receive a friendly LLM reply

Features:
  • Multi-turn conversation via history array
  • Optional case_id for case-aware context
  • MongoDB audit logging per interaction
"""

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, status
from schemas.chat_schema import ChatRequest, ChatResponse
from schemas.models import ErrorResponse

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/chat",
    tags=["Chatbot"],
)


# ─────────────────────────────────────────────
# POST /chat
# ─────────────────────────────────────────────

@router.post(
    "",
    response_model=ChatResponse,
    status_code=status.HTTP_200_OK,
    summary="Send a message to the InsureMind medical assistant",
    description="""
Chat with the InsureMind AI medical assistant.

The assistant can help with:
- ICD-10 and CPT codes
- Insurance prior authorization guidance
- Clinical documentation questions
- Drug information and interactions
- General medical knowledge
- Any real-world question

Pass `history` array for multi-turn conversations.
Pass `case_id` to give the assistant context about a specific case.
    """,
    responses={
        200: {"description": "Chat response",            "model": ChatResponse},
        503: {"description": "LLM unavailable",          "model": ErrorResponse},
        500: {"description": "Chat service error",       "model": ErrorResponse},
    },
)
async def chat(payload: ChatRequest) -> ChatResponse:
    try:
        from db import get_mongo_db
        mongo_db = get_mongo_db()
    except Exception as exc:
        logger.warning("MongoDB unavailable for chat logging: %s", exc)
        mongo_db = None

    try:
        from services.chat_service import get_chat_response
        reply = await get_chat_response(
            message=payload.message,
            history=payload.history,
            case_id=payload.case_id,
            mongo_db=mongo_db,
        )

        return ChatResponse(
            reply=reply,
            model="llama-3.3-70b-versatile",
            case_id=payload.case_id,
        )

    except EnvironmentError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc))
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc))
    except Exception as exc:
        logger.exception("POST /chat failed")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))