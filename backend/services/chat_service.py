"""
services/chat_service.py

LLM-powered Medical Assistant Chatbot Service.

System Prompt:
  "You are a medical assistant helping doctors with ICD codes, insurance approvals,
   and clinical documentation — much like a normal chatbot that can answer anything
   in the real world."

Features:
  • Multi-turn conversation support (pass history array)
  • Optional case context (pass case_id to get case-aware responses)
  • Friendly, professional tone
  • Lazy Groq initialization
  • MongoDB audit logging for every chat interaction
"""

import os
import logging
from datetime import datetime, timezone
from typing import List, Optional

from schemas.chat_schema import ChatMessage

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────
# System Prompt
# ─────────────────────────────────────────────

SYSTEM_PROMPT = """You are InsureMind AI — a friendly and knowledgeable medical assistant helping doctors with:
- ICD-10 and CPT diagnosis/procedure codes
- Insurance prior authorization decisions and appeals
- Clinical documentation and SOAP notes
- Evidence-based treatment guidelines
- Drug interactions and medication information
- General medical knowledge and real-world questions

Tone: Be warm, professional, and conversational.
Format: Your answers MUST be VERY specific and extremely concise. Do NOT provide long, verbose explanations unless explicitly asked. Give only the exact information requested. Get straight to the point.
Accuracy: If you're uncertain about a specific medical fact, say so clearly and suggest consulting official sources.
You can answer questions about any real-world topic, not just medicine."""


# ─────────────────────────────────────────────
# Lazy LLM Client
# ─────────────────────────────────────────────

async def _call_groq(messages: list) -> str:
    """Lazy Groq client — never initialized at import time."""
    try:
        from groq import AsyncGroq
    except ImportError as exc:
        raise RuntimeError("groq not installed. Run: pip install groq") from exc

    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise EnvironmentError("GROQ_API_KEY is not set in environment.")

    client = AsyncGroq(api_key=api_key)
    response = await client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=messages,
        temperature=0.6,    # Slightly higher for conversational warmth
        max_tokens=1024,
    )
    return response.choices[0].message.content.strip()


# ─────────────────────────────────────────────
# Public Entry Point
# ─────────────────────────────────────────────

async def get_chat_response(
    message:  str,
    history:  List[ChatMessage],
    case_id:  Optional[str],
    mongo_db,
) -> str:
    """
    Generate a chatbot reply using Groq LLM.

    Args:
        message  : User's latest message
        history  : Previous conversation turns (for multi-turn context)
        case_id  : Optional case context — if provided, adds a note to the system prompt
        mongo_db : MongoDB db instance for audit logging

    Returns:
        str — LLM reply text
    """
    # Build system prompt — optionally add case context
    system_content = SYSTEM_PROMPT
    if case_id:
        system_content += (
            f"\n\nCurrent Case Context: The doctor is asking about case {case_id}. "
            "Reference this case when relevant to the conversation."
        )

    # Build messages array for Groq
    messages = [{"role": "system", "content": system_content}]

    # Add conversation history (last 10 turns max to stay within token budget)
    for turn in history[-10:]:
        messages.append({"role": turn.role, "content": turn.content})

    # Add current user message
    messages.append({"role": "user", "content": message})

    try:
        reply = await _call_groq(messages)
    except EnvironmentError:
        raise
    except Exception as exc:
        logger.error("Chatbot LLM call failed: %s", exc)
        raise RuntimeError(f"Chat service unavailable: {exc}") from exc

    # Log to MongoDB
    try:
        await mongo_db["audit_logs"].insert_one({
            "action":    "chatbot_used",
            "case_id":   case_id,
            "message":   message[:200],   # Truncate for audit log
            "timestamp": datetime.now(timezone.utc),
        })
    except Exception as mongo_exc:
        logger.warning("Chatbot audit log failed (non-fatal): %s", mongo_exc)

    logger.info("Chatbot response generated — case_id: %s | msg_len: %d", case_id, len(message))
    return reply