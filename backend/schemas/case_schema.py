"""
schemas/case_schema.py

Pydantic models for Case management:
  - CaseSaveRequest  : input when saving a full agent result as a case
  - CaseResponse     : full case detail returned by GET /case/{case_id}
  - CaseListItem     : lightweight record for history list view
  - CaseListResponse : paginated list of cases
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Any
from datetime import datetime


# ─────────────────────────────────────────────
# Save Request — passed by agent_service after pipeline completes
# ─────────────────────────────────────────────

class CaseSaveRequest(BaseModel):
    """
    Full agent output passed to case_service.save_case().
    Contains everything needed to generate the PDF and store in PostgreSQL.
    """
    patient_name:            str
    patient_age:             int
    patient_gender:          str
    tpa:                     str
    disease_description:     str
    medications:             Optional[str] = None
    procedure:               Optional[str] = None

    # Clinical justification fields
    duration_of_symptoms:    Optional[str] = None
    prior_treatment:         Optional[str] = None
    severity:                Optional[str] = None
    investigations:          Optional[str] = None
    specialist_referral:     Optional[str] = None

    # SOAP
    soap_subjective:         str
    soap_objective:          str
    soap_assessment:         str
    soap_plan:               str

    # ICD + Procedure
    icd_code:                str
    icd_description:         str
    procedure_code:          str
    procedure_description:   str

    # Justification
    justification_text:      str
    justification_score:     float

    # Evidence
    missing_evidence:        List[str] = []
    evidence_score:          float

    # Risk + Conflicts
    risk_flags:              List[dict] = []
    conflicts:               List[dict] = []
    condition_type:          str

    # Approval
    approval_probability:    float
    approval_recommendation: str

    # Explainability
    reasons:                 List[str] = []
    suggestions:             List[str] = []


# ─────────────────────────────────────────────
# Case Detail Response — GET /case/{case_id}
# ─────────────────────────────────────────────

class SOAPDetail(BaseModel):
    subjective: str
    objective:  str
    assessment: str
    plan:       str


class CaseResponse(BaseModel):
    """
    Full case record returned by GET /case/{case_id}.
    Displayed in the frontend Case Detail page when doctor enters name + case_id.
    """
    # Identity
    case_id:                 str
    created_at:              str

    # Patient
    patient_name:            str
    patient_age:             int
    patient_gender:          str
    tpa:                     str

    # Clinical inputs
    disease_description:     Optional[str] = None
    medications:             Optional[str] = None
    procedure:               Optional[str] = None

    # Justification fields
    duration_of_symptoms:    Optional[str] = None
    prior_treatment:         Optional[str] = None
    severity:                Optional[str] = None
    investigations:          Optional[str] = None
    specialist_referral:     Optional[str] = None

    # SOAP
    soap:                    Optional[SOAPDetail] = None

    # ICD + Procedure
    icd_code:                Optional[str] = None
    icd_description:         Optional[str] = None
    procedure_code:          Optional[str] = None
    procedure_description:   Optional[str] = None

    # Justification
    justification_text:      Optional[str] = None
    justification_score:     Optional[float] = None

    # Evidence
    missing_evidence:        Optional[List[str]] = None
    evidence_score:          Optional[float] = None

    # Risk + Conflicts
    risk_flags:              Optional[List[dict]] = None
    conflicts:               Optional[List[dict]] = None
    condition_type:          Optional[str] = None

    # Approval
    approval_probability:    Optional[float] = None
    approval_recommendation: Optional[str] = None

    # Explainability
    reasons:                 Optional[List[str]] = None
    suggestions:             Optional[List[str]] = None

    # PDF
    pdf_path:                Optional[str] = None
    pdf_available:           bool = False

    model_config = {
        "json_schema_extra": {
            "example": {
                "case_id":                 "HOSP1",
                "created_at":              "2025-04-19T10:30:00Z",
                "patient_name":            "Uma",
                "patient_age":             70,
                "patient_gender":          "female",
                "tpa":                     "Demo TPA",
                "icd_code":                "I21.9",
                "icd_description":         "Acute myocardial infarction, unspecified",
                "approval_probability":    0.82,
                "approval_recommendation": "APPROVED",
                "pdf_available":           True,
            }
        }
    }


# ─────────────────────────────────────────────
# Case List Item — History View
# ─────────────────────────────────────────────

class CaseListItem(BaseModel):
    """Lightweight case record for the history list view."""
    case_id:                 str
    created_at:              str
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
    pdf_available:           bool


class CaseListResponse(BaseModel):
    """Paginated case history response."""
    total:   int
    page:    int
    cases:   List[CaseListItem]


# ─────────────────────────────────────────────
# Case Access Request — frontend access form
# ─────────────────────────────────────────────

class CaseAccessRequest(BaseModel):
    """
    Used by POST /case/access — doctor enters patient_name + case_id
    to retrieve their case report.
    """
    patient_name: str = Field(..., min_length=1, description="Patient name (case-insensitive match)")
    case_id:      str = Field(..., min_length=1, description="Case ID e.g. HOSP1")

    model_config = {
        "json_schema_extra": {
            "example": {
                "patient_name": "Uma",
                "case_id":      "HOSP1",
            }
        }
    }


# ─────────────────────────────────────────────
# Case Save Response
# ─────────────────────────────────────────────

class CaseSaveResponse(BaseModel):
    """Returned after successfully saving a case."""
    case_id:    str
    pdf_path:   Optional[str] = None
    message:    str

    model_config = {
        "json_schema_extra": {
            "example": {
                "case_id":  "HOSP5",
                "pdf_path": "reports/HOSP5.pdf",
                "message":  "Case HOSP5 saved and PDF generated.",
            }
        }
    }