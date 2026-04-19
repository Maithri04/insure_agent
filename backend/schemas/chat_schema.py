"""
schemas/chat_schema.py

Pydantic models for the InsureMind AI Chatbot.
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class ChatMessage(BaseModel):
    """Single message in a conversation."""
    role:    str   # "user" | "assistant"
    content: str


class ChatRequest(BaseModel):
    """
    Input for POST /chat.
    Optionally pass conversation history for multi-turn context.
    """
    message:  str = Field(..., min_length=1, description="User's message to the medical assistant")
    history:  List[ChatMessage] = Field(default=[], description="Previous conversation turns (optional)")
    case_id:  Optional[str] = Field(None, description="Optional case_id for case-aware context")

    model_config = {
        "json_schema_extra": {
            "example": {
                "message": "What ICD code is used for acute myocardial infarction?",
                "history": [],
                "case_id": None,
            }
        }
    }


class ChatResponse(BaseModel):
    """Response from POST /chat."""
    reply:      str
    model:      str = "llama-3.3-70b-versatile"
    case_id:    Optional[str] = None

    model_config = {
        "json_schema_extra": {
            "example": {
                "reply":     "I21.9",
                "model":     "llama-3.3-70b-versatile",
                "case_id":   None,
            }
        }
    }