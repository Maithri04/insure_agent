from pydantic import BaseModel, Field, field_validator
from typing import Optional, List
from enum import Enum
from datetime import datetime


# ─────────────────────────────────────────────
# Enums
# ─────────────────────────────────────────────

class GenderEnum(str, Enum):
    male = "male"
    female = "female"
    other = "other"


class SeverityEnum(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"


# ─────────────────────────────────────────────
# REQUEST — matches frontend form exactly
# ─────────────────────────────────────────────

class AgentRequest(BaseModel):
    # Section: Patient Demographics
    patient_name: str = Field(..., min_length=1, max_length=100)
    patient_age: int = Field(..., ge=0, le=150)
    patient_gender: GenderEnum

    # Section: Insurance Details
    tpa: str = Field(..., description="Third Party Administrator / Insurance payer name")

    # Section: Clinical Details
    disease_description: str = Field(..., min_length=10, description="Doctor's raw clinical notes")
    medications: Optional[str] = None
    procedure: Optional[str] = Field(None, description="Procedure name or CPT code if known")

    # Section: Clinical Justification (drives Missing Evidence Checklist on right panel)
    duration_of_symptoms: Optional[str] = None
    prior_treatment: Optional[str] = None
    severity: Optional[str] = None
    investigations: Optional[str] = None
    specialist_referral: Optional[str] = None

    @field_validator("disease_description")
    @classmethod
    def desc_not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("disease_description cannot be blank")
        return v.strip()

    model_config = {
        "json_schema_extra": {
            "example": {
                "patient_name": "Uma",
                "patient_age": 70,
                "patient_gender": "female",
                "tpa": "Demo TPA",
                "disease_description": "Patient presents with severe chest pain, hypertension, and shortness of breath for 3 days.",
                "medications": "Aspirin 81mg, Lisinopril 10mg",
                "procedure": "surgery",
                "duration_of_symptoms": "1 year",
                "prior_treatment": "yes",
                "severity": "high",
                "investigations": "ECG done, shows ST elevation",
                "specialist_referral": "referred to cardiologist"
            }
        }
    }


# ─────────────────────────────────────────────
# SUB-MODELS
# ─────────────────────────────────────────────

class PatientDetails(BaseModel):
    name: str
    age: int
    gender: str


class SOAPNote(BaseModel):
    subjective: str
    objective: str
    assessment: str
    plan: str


class ICDResult(BaseModel):
    code: str
    description: str
    is_validated: bool
    was_corrected: bool
    original_predicted_code: Optional[str] = None
    confidence: float = Field(ge=0.0, le=1.0)


class ProcedureResult(BaseModel):
    code: str
    description: str
    source: str   # "provided" | "mapped_from_icd" | "default"


class EvidenceItem(BaseModel):
    label: str             # "Duration" | "Prior treatment" | "Severity" | "Investigations" | "Referral"
    is_present: bool
    value: Optional[str] = None


class EvidenceResult(BaseModel):
    items: List[EvidenceItem]      # 5 items matching the frontend checklist
    missing_labels: List[str]      # e.g. ["Duration", "Referral"] — drives the red X checklist
    completeness_score: float      # 0.0 – 1.0
    suggestions: List[str]


class ConflictItem(BaseModel):
    rule_name: str
    severity: SeverityEnum
    description: str
    action: str            # "deny" | "flag" | "review"


class JustificationResult(BaseModel):
    text: str
    score: float           # 0.0 – 1.0
    iterations: int        # how many LLM rewrites (0–2)
    is_sufficient: bool    # score >= 0.75


class RiskFlag(BaseModel):
    flag: str
    severity: SeverityEnum
    description: str


class ApprovalBreakdown(BaseModel):
    evidence_score: float
    justification_score: float
    severity_bonus: float
    conflict_penalty: float
    risk_penalty: float


# ─────────────────────────────────────────────
# MAIN RESPONSE
# ─────────────────────────────────────────────

class AgentResponse(BaseModel):
    # Report Fields Requested by User
    hospital_name: str
    hospital_details: str
    patient_details: PatientDetails
    soap_note: SOAPNote
    insurance_approval_rate: str

    # Original Fields
    request_id: str
    timestamp: str
    tpa: str

    # Agent pipeline outputs
    icd: ICDResult
    procedure: ProcedureResult
    conflicts: List[ConflictItem]

    # Evidence — directly drives the "Missing Evidence Checklist" panel
    evidence: EvidenceResult

    justification: JustificationResult
    risk_flags: List[RiskFlag]
    condition_type: str            # "minor" | "moderate" | "serious" | "critical"

    # Approval
    approval_probability: float    # 0.0 – 1.0
    approval_breakdown: ApprovalBreakdown
    approval_recommendation: str   # "APPROVED" | "LIKELY APPROVED" | "NEEDS REVIEW" | "LIKELY DENIED" | "DENIED"

    # Explainability — shown in agent thought process panel (right side)
    reasons: List[str]
    suggestions: List[str]
    processing_steps: List[str]    # step-by-step agent log for the right panel


# ─────────────────────────────────────────────
# AUDIT LOG (stored in MongoDB)
# ─────────────────────────────────────────────

class AuditLogEntry(BaseModel):
    request_id: str
    timestamp: datetime
    patient_name: str
    patient_age: int
    patient_gender: str
    tpa: str
    disease_description: str
    icd_code: str
    icd_description: str
    procedure_code: str
    approval_probability: float
    approval_recommendation: str
    missing_evidence: List[str]
    risk_flag_count: int
    conflict_count: int
    justification_score: float
    processing_duration_ms: Optional[float] = None
    submitted: bool = False