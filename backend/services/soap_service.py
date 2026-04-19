import os
import json
import logging
from typing import Optional

from schemas.soap_schema import SOAPRequest, SOAPResponse

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Prompt Builder
# ---------------------------------------------------------------------------

def _build_soap_prompt(req: SOAPRequest) -> str:
    """Construct a detailed clinical prompt for the LLM."""
    medications_line = (
        f"Current Medications: {req.medications}"
        if req.medications
        else "Current Medications: None reported"
    )

    return f"""You are a highly experienced clinical physician. Based on the information below, generate a structured SOAP note in valid JSON format.

PATIENT INFORMATION:
- Name: {req.patient_name}
- Age: {req.patient_age} years
- Gender: {req.patient_gender.value}
- {medications_line}

DOCTOR'S RAW NOTES:
{req.raw_notes}

INSTRUCTIONS:
1. Generate a professional, clean, and VERY concise SOAP note.
2. The values MUST be simple, flat text strings. Do NOT use nested JSON objects.
3. Assign the most accurate ICD-10 diagnosis code based on the assessment.
4. Do NOT add any commentary outside the JSON block.

Return ONLY a valid JSON object with this exact structure:
{{
  "subjective": "<Patient's chief complaint, history of present illness, relevant symptoms as reported>",
  "objective": "<Clinical findings, vitals (estimated if not provided), physical exam observations>",
  "assessment": "<Primary diagnosis and differential diagnoses with clinical reasoning>",
  "plan": "<Diagnostic workup, treatments, medications, referrals, and follow-up instructions>",
  "icd10_code": "<Most appropriate ICD-10 code, e.g. J18.9>"
}}"""


# ---------------------------------------------------------------------------
# LLM Caller — Lazy Initialization
# ---------------------------------------------------------------------------

async def _call_groq_llm(prompt: str) -> str:
    """
    Lazy-initialize the Groq client and call the LLM.
    The client is created inside this function (not at import time)
    so that environment variables are read at call time.
    """
    try:
        from groq import AsyncGroq  # import deferred intentionally
    except ImportError as exc:
        raise RuntimeError(
            "groq package is not installed. Run: pip install groq"
        ) from exc

    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise EnvironmentError(
            "GROQ_API_KEY is not set. Add it to your .env file."
        )

    # Lazy client — created fresh per call (lightweight, stateless)
    client = AsyncGroq(api_key=api_key)

    chat_completion = await client.chat.completions.create(
        model="llama-3.3-70b-versatile",   # Best available Groq model for structured output
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a board-certified physician assistant specialized in "
                    "clinical documentation. Always respond with valid JSON only."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        temperature=0.2,        # Low temperature for consistent clinical output
        max_tokens=1024,
        response_format={"type": "json_object"},  # Enforce JSON mode
    )

    return chat_completion.choices[0].message.content


# ---------------------------------------------------------------------------
# Response Parser
# ---------------------------------------------------------------------------

def _parse_soap_response(raw_json: str) -> SOAPResponse:
    """Parse and validate the LLM JSON output into a SOAPResponse."""
    try:
        data = json.loads(raw_json)
    except json.JSONDecodeError as exc:
        logger.error("LLM returned invalid JSON: %s", raw_json)
        raise ValueError(f"LLM returned malformed JSON: {exc}") from exc

    required_keys = {"subjective", "objective", "assessment", "plan", "icd10_code",}
    missing = required_keys - data.keys()
    if missing:
        raise ValueError(f"LLM response is missing required fields: {missing}")

    def _stringify(v):
        if isinstance(v, dict):
            return "; ".join(f"{val}" for val in v.values() if val)
        if isinstance(v, list):
            return "; ".join(f"{val}" for val in v if val)
        return str(v).strip()
        
    return SOAPResponse(**{k: _stringify(v) for k, v in data.items() if k in required_keys})


# ---------------------------------------------------------------------------
# Public Service Function
# ---------------------------------------------------------------------------

async def generate_soap_note(req: SOAPRequest) -> SOAPResponse:
    """
    Orchestrates SOAP note generation:
    1. Builds the clinical prompt
    2. Calls Groq LLM (lazy init)
    3. Parses and validates the structured response
    """
    logger.info(
        "Generating SOAP note for patient: %s, age: %d",
        req.patient_name,
        req.patient_age,
    )

    prompt = _build_soap_prompt(req)

    try:
        raw_output = await _call_groq_llm(prompt)
    except EnvironmentError:
        raise   # Re-raise config errors as-is for the router to handle
    except Exception as exc:
        logger.exception("Groq LLM call failed")
        raise RuntimeError(f"LLM request failed: {exc}") from exc

    try:
        soap_response = _parse_soap_response(raw_output)
    except ValueError as exc:
        logger.error("Failed to parse LLM response: %s", exc)
        raise RuntimeError(f"Failed to parse LLM output: {exc}") from exc

    logger.info("SOAP note generated successfully for %s", req.patient_name)
    return soap_response