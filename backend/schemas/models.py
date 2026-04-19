"""
schemas/models.py

General shared Pydantic models used across the entire InsureMind backend.

Sections:
  1. Enums              — shared enum types
  2. Health Check       — /health endpoint response models
  3. Error Responses    — standard error shapes for all routers
  4. Pagination         — generic paginated wrapper
  5. Audit History      — list + detail views for past agent runs
  6. Dashboard Stats    — aggregate stats for analytics panel
  7. Form Submission    — routers/form.py lightweight save
  8. Final Submit       — routers/submit.py response
  9. ICD + Procedure    — lightweight lookup response models
  10. Payer / TPA       — TPA info models
  11. Generic           — success, message responses
"""

from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Any, Dict
from datetime import datetime
from enum import Enum


# ─────────────────────────────────────────────────────────────────────────────
# 1. Enums
# ─────────────────────────────────────────────────────────────────────────────

class RecommendationEnum(str, Enum):
    approved        = "APPROVED"
    likely_approved = "LIKELY APPROVED"
    needs_review    = "NEEDS REVIEW"
    likely_denied   = "LIKELY DENIED"
    denied          = "DENIED"


class ConditionTypeEnum(str, Enum):
    minor    = "minor"
    moderate = "moderate"
    serious  = "serious"
    critical = "critical"


class GenderEnum(str, Enum):
    male   = "male"
    female = "female"
    other  = "other"


class SeverityLevelEnum(str, Enum):
    low      = "low"
    medium   = "medium"
    high     = "high"
    critical = "critical"


# ─────────────────────────────────────────────────────────────────────────────
# 2. Health Check
# ─────────────────────────────────────────────────────────────────────────────

class DBHealthStatus(BaseModel):
    """Individual database health status — used inside HealthResponse."""
    status:          str
    detail:          Optional[str]  = None
    database:        Optional[str]  = None
    version:         Optional[str]  = None
    icd_codes:       Optional[int]  = None     # PostgreSQL only
    conflict_rules:  Optional[int]  = None     # PostgreSQL only


class HealthResponse(BaseModel):
    """
    Response for GET /health.
    Shows API version, GROQ key status, and DB connectivity.
    """
    status:              str
    version:             str
    groq_key_configured: bool
    mongodb:             DBHealthStatus
    postgresql:          DBHealthStatus

    model_config = {
        "json_schema_extra": {
            "example": {
                "status":              "ok",
                "version":             "1.0.0",
                "groq_key_configured": True,
                "mongodb":    {"status": "ok",    "database": "healthcare"},
                "postgresql": {
                    "status":         "ok",
                    "version":        "PostgreSQL 16.2",
                    "icd_codes":      112,
                    "conflict_rules":  21,
                },
            }
        }
    }


# ─────────────────────────────────────────────────────────────────────────────
# 3. Error Responses
# ─────────────────────────────────────────────────────────────────────────────

class ErrorResponse(BaseModel):
    """Standard error body returned for 4xx and 5xx responses."""
    detail:     str
    error_type: Optional[str] = None
    request_id: Optional[str] = None

    model_config = {
        "json_schema_extra": {
            "example": {
                "detail":     "GROQ_API_KEY is not set. Add it to your .env file.",
                "error_type": "EnvironmentError",
                "request_id": None,
            }
        }
    }


class ValidationErrorField(BaseModel):
    """Single field-level validation error."""
    field:   str
    message: str
    value:   Optional[Any] = None


class ValidationErrorResponse(BaseModel):
    """422 Unprocessable Entity response body."""
    detail: str = "Request validation failed"
    errors: List[ValidationErrorField]

    model_config = {
        "json_schema_extra": {
            "example": {
                "detail": "Request validation failed",
                "errors": [
                    {
                        "field":   "patient_age",
                        "message": "Input should be less than or equal to 150",
                        "value":   999,
                    }
                ],
            }
        }
    }


# ─────────────────────────────────────────────────────────────────────────────
# 4. Pagination
# ─────────────────────────────────────────────────────────────────────────────

class PaginatedResponse(BaseModel):
    """Generic paginated wrapper — used for any list endpoint."""
    total:   int = Field(..., description="Total number of records in database")
    page:    int = Field(..., description="Current page number (1-indexed)")
    limit:   int = Field(..., description="Records per page")
    records: List[Any]


# ─────────────────────────────────────────────────────────────────────────────
# 5. Audit History — List + Detail
# ─────────────────────────────────────────────────────────────────────────────

class AuditRecordSummary(BaseModel):
    """
    Lightweight audit log record for list views.
    Excludes heavy text fields (SOAP, justification text).
    Returned by GET /agent/history.
    """
    request_id:              str
    timestamp:               str
    patient_name:            str
    patient_age:             int
    patient_gender:          str
    tpa:                     str
    icd_code:                str
    icd_description:         str
    procedure_code:          str
    condition_type:          str
    approval_probability:    float
    approval_recommendation: str
    missing_evidence:        List[str]
    conflict_count:          int
    risk_flag_count:         int
    justification_score:     float
    submitted:               bool
    submitted_at:            Optional[str]   = None
    processing_duration_ms:  Optional[float] = None

    model_config = {
        "json_schema_extra": {
            "example": {
                "request_id":              "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                "timestamp":               "2025-04-19T10:30:00Z",
                "patient_name":            "Uma",
                "patient_age":             70,
                "patient_gender":          "female",
                "tpa":                     "Demo TPA",
                "icd_code":                "I21.9",
                "icd_description":         "Acute myocardial infarction, unspecified",
                "procedure_code":          "92928",
                "condition_type":          "critical",
                "approval_probability":    0.81,
                "approval_recommendation": "APPROVED",
                "missing_evidence":        ["Investigations"],
                "conflict_count":          0,
                "risk_flag_count":         2,
                "justification_score":     0.84,
                "submitted":               True,
                "submitted_at":            "2025-04-19T10:31:00Z",
                "processing_duration_ms":  3240.5,
            }
        }
    }


class AuditRecordDetail(AuditRecordSummary):
    """
    Full audit log record — includes all clinical fields, SOAP, and justification.
    Returned by GET /agent/history/{request_id}.
    """
    # Raw clinical inputs from the form
    disease_description:   str
    medications:           Optional[str] = None
    procedure_input:       Optional[str] = None

    # Clinical Justification form fields (drives Missing Evidence Checklist)
    duration_of_symptoms:  Optional[str] = None
    prior_treatment:       Optional[str] = None
    severity:              Optional[str] = None
    investigations:        Optional[str] = None
    specialist_referral:   Optional[str] = None

    # SOAP Note
    soap_subjective: str
    soap_objective:  str
    soap_assessment: str
    soap_plan:       str

    # Justification
    justification_text: str

    # Structured conflict + risk data
    conflicts:  List[Dict[str, Any]] = []
    risk_flags: List[Dict[str, Any]] = []

    # Explainability output
    reasons:     List[str] = []
    suggestions: List[str] = []


class AuditHistoryResponse(BaseModel):
    """Paginated audit history response for GET /agent/history."""
    total:   int
    page:    int
    records: List[AuditRecordSummary]


# ─────────────────────────────────────────────────────────────────────────────
# 6. Dashboard Stats
# ─────────────────────────────────────────────────────────────────────────────

class TPAVolume(BaseModel):
    """TPA name and number of claims submitted through it."""
    tpa:   str
    count: int


class DashboardStats(BaseModel):
    """
    Aggregate statistics for the analytics / dashboard panel.
    Returned by GET /agent/stats.
    """
    total:            int   = 0
    submitted_count:  int   = 0
    approved_count:   int   = 0
    denied_count:     int   = 0
    review_count:     int   = 0
    avg_probability:  Optional[float] = None
    avg_just_score:   Optional[float] = None
    top_tpas:         List[TPAVolume] = []

    model_config = {
        "json_schema_extra": {
            "example": {
                "total":           120,
                "submitted_count":  85,
                "approved_count":   60,
                "denied_count":     15,
                "review_count":     45,
                "avg_probability":  0.672,
                "avg_just_score":   0.741,
                "top_tpas": [
                    {"tpa": "Demo TPA",    "count": 45},
                    {"tpa": "Star Health", "count": 30},
                    {"tpa": "Medi Assist", "count": 25},
                ],
            }
        }
    }


# ─────────────────────────────────────────────────────────────────────────────
# 7. Form Submission (routers/form.py)
# ─────────────────────────────────────────────────────────────────────────────

class FormSubmitRequest(BaseModel):
    """
    Lightweight form save — stores raw input in MongoDB without
    running the full agent pipeline.
    Used by routers/form.py for draft/save functionality.
    """
    # Patient Demographics
    patient_name:   str = Field(..., min_length=1, max_length=100)
    patient_age:    int = Field(..., ge=0, le=150)
    patient_gender: GenderEnum

    # Insurance
    tpa: str = Field(..., min_length=1, description="Third Party Administrator name")

    # Clinical Details
    disease_description: str = Field(..., min_length=5)
    medications:         Optional[str] = None
    procedure:           Optional[str] = None

    # Clinical Justification (optional at save time)
    duration_of_symptoms: Optional[str] = None
    prior_treatment:      Optional[str] = None
    severity:             Optional[str] = None
    investigations:       Optional[str] = None
    specialist_referral:  Optional[str] = None

    @field_validator("disease_description")
    @classmethod
    def desc_not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("disease_description cannot be blank")
        return v.strip()

    model_config = {
        "json_schema_extra": {
            "example": {
                "patient_name":        "Uma",
                "patient_age":         70,
                "patient_gender":      "female",
                "tpa":                 "Demo TPA",
                "disease_description": "Severe chest pain radiating to left arm for 2 hours.",
                "medications":         "Aspirin 81mg",
                "procedure":           "surgery",
                "duration_of_symptoms": "1 year",
                "prior_treatment":     "yes",
                "severity":            "high",
                "investigations":      "ECG done",
                "specialist_referral": "referred to cardiologist",
            }
        }
    }


class FormSubmitResponse(BaseModel):
    """Response after saving a draft form submission."""
    status:     str = "saved"
    message:    str
    request_id: Optional[str] = None

    model_config = {
        "json_schema_extra": {
            "example": {
                "status":     "saved",
                "message":    "Form data saved. Click Verify to run the agent pipeline.",
                "request_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
            }
        }
    }


# ─────────────────────────────────────────────────────────────────────────────
# 8. Final Submit Response (routers/submit.py)
# ─────────────────────────────────────────────────────────────────────────────

class SubmitResponse(BaseModel):
    """
    Response returned after POST /agent/submit.
    Confirms the authorization request has been recorded as submitted.
    """
    status:                  str   = "submitted"
    request_id:              str
    approval_recommendation: str
    approval_probability:    float
    message:                 str

    model_config = {
        "json_schema_extra": {
            "example": {
                "status":                  "submitted",
                "request_id":              "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                "approval_recommendation": "LIKELY APPROVED",
                "approval_probability":    0.74,
                "message":                 "Authorization request submitted to Demo TPA.",
            }
        }
    }


# ─────────────────────────────────────────────────────────────────────────────
# 9. ICD + Procedure Lookup Response Models
# ─────────────────────────────────────────────────────────────────────────────

class ICDLookupItem(BaseModel):
    """Single ICD-10 code record from PostgreSQL icd_codes table."""
    code:        str
    description: str
    category:    str
    severity:    str
    is_active:   bool


class ProcedureLookupItem(BaseModel):
    """Single procedure code record from PostgreSQL procedure_codes table."""
    code:          str
    description:   str
    category:      str
    requires_auth: bool
    is_active:     bool


class ICDLookupResponse(BaseModel):
    """Response for ICD code search/lookup endpoints."""
    total:   int
    results: List[ICDLookupItem]


class ProcedureLookupResponse(BaseModel):
    """Response for procedure code search/lookup endpoints."""
    total:   int
    results: List[ProcedureLookupItem]


# ─────────────────────────────────────────────────────────────────────────────
# 10. Payer / TPA Models
# ─────────────────────────────────────────────────────────────────────────────

class PayerRuleItem(BaseModel):
    """Single payer rule record from PostgreSQL payer_rules table."""
    rule_name:            str
    rule_type:            str   # boost | reduce | deny | require_docs
    condition_category:   Optional[str]   = None
    procedure_code:       Optional[str]   = None
    condition_type:       Optional[str]   = None
    min_evidence_score:   Optional[float] = None
    probability_modifier: Optional[float] = None
    description:          str
    action:               str


class TPAListItem(BaseModel):
    """TPA name for dropdown population in the frontend Insurance Details field."""
    tpa_name: str
    rule_count: int


class TPAListResponse(BaseModel):
    """List of available TPAs — used to populate the TPA dropdown."""
    total: int
    tpas:  List[TPAListItem]


# ─────────────────────────────────────────────────────────────────────────────
# 11. Generic Responses
# ─────────────────────────────────────────────────────────────────────────────

class SuccessResponse(BaseModel):
    """Generic success wrapper for simple acknowledgement responses."""
    status:  str = "ok"
    message: str
    data:    Optional[Any] = None


class MessageResponse(BaseModel):
    """Minimal message response for status endpoints."""
    message: str
