# schemas/__init__.py
# InsureMind AI — Schemas Module Exports

# ── Agent schemas (pipeline request/response) ──
from schemas.agent_schema import (
    # Enums
    GenderEnum,
    SeverityEnum,
    # Request
    AgentRequest,
    # Sub-models
    SOAPNote,
    ICDResult,
    ProcedureResult,
    EvidenceItem,
    EvidenceResult,
    ConflictItem,
    JustificationResult,
    RiskFlag,
    ApprovalBreakdown,
    # Main response
    AgentResponse,
    # Audit
    AuditLogEntry,
)

# ── General shared models ──
from schemas.models import (
    # Enums
    RecommendationEnum,
    ConditionTypeEnum,
    # Health
    DBHealthStatus,
    HealthResponse,
    # Errors
    ErrorResponse,
    ValidationErrorField,
    ValidationErrorResponse,
    # Pagination
    PaginatedResponse,
    # Audit history
    AuditRecordSummary,
    AuditRecordDetail,
    AuditHistoryResponse,
    # Stats
    TPAVolume,
    DashboardStats,
    # Form
    FormSubmitRequest,
    FormSubmitResponse,
    # Submit
    SubmitResponse,
    # Generic
    SuccessResponse,
)

# ── SOAP schemas ──
from schemas.soap_schema import (
    SOAPRequest,
    SOAPResponse,
)

__all__ = [
    # ── Agent ──
    "GenderEnum",
    "SeverityEnum",
    "AgentRequest",
    "SOAPNote",
    "ICDResult",
    "ProcedureResult",
    "EvidenceItem",
    "EvidenceResult",
    "ConflictItem",
    "JustificationResult",
    "RiskFlag",
    "ApprovalBreakdown",
    "AgentResponse",
    "AuditLogEntry",
    # ── General ──
    "RecommendationEnum",
    "ConditionTypeEnum",
    "DBHealthStatus",
    "HealthResponse",
    "ErrorResponse",
    "ValidationErrorField",
    "ValidationErrorResponse",
    "PaginatedResponse",
    "AuditRecordSummary",
    "AuditRecordDetail",
    "AuditHistoryResponse",
    "TPAVolume",
    "DashboardStats",
    "FormSubmitRequest",
    "FormSubmitResponse",
    "SubmitResponse",
    "SuccessResponse",
    # ── SOAP ──
    "SOAPRequest",
    "SOAPResponse",
]