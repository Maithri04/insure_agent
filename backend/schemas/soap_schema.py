from pydantic import BaseModel, Field, field_validator
from typing import Optional
from enum import Enum


class GenderEnum(str, Enum):
    male = "male"
    female = "female"
    other = "other"


class SOAPRequest(BaseModel):
    patient_name: str = Field(..., min_length=1, max_length=100, description="Full name of the patient")
    patient_age: int = Field(..., ge=0, le=150, description="Age of the patient in years")
    patient_gender: GenderEnum = Field(..., description="Gender of the patient")
    raw_notes: str = Field(..., min_length=10, description="Doctor's raw clinical notes or description")
    medications: Optional[str] = Field(None, description="Current medications (optional)")

    @field_validator("raw_notes")
    @classmethod
    def raw_notes_not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("raw_notes cannot be blank or whitespace only")
        return v.strip()

    @field_validator("patient_name")
    @classmethod
    def patient_name_not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("patient_name cannot be blank or whitespace only")
        return v.strip()

    model_config = {
        "json_schema_extra": {
            "example": {
                "patient_name": "John Doe",
                "patient_age": 45,
                "patient_gender": "male",
                "raw_notes": "Patient complains of persistent chest pain for 3 days, shortness of breath, mild fever. No prior cardiac history.",
                "medications": "Aspirin 81mg daily",
            }
        }
    }


class SOAPResponse(BaseModel):
    case_id: str = Field(default="", description="Unique case ID sequence")
    subjective: str = Field(..., description="Patient's reported symptoms and history")
    objective: str = Field(..., description="Clinical observations and examination findings")
    assessment: str = Field(..., description="Diagnosis and clinical assessment")
    plan: str = Field(..., description="Treatment plan and next steps")
    icd10_code: str = Field(..., description="ICD-10 diagnosis code")

    model_config = {
        "json_schema_extra": {
            "example": {
                "subjective": "Patient reports persistent chest pain for 3 days with associated shortness of breath and mild fever.",
                "objective": "Vital signs stable. Mild tachycardia noted. Chest auscultation reveals decreased breath sounds at base.",
                "assessment": "Acute pleuritis, likely viral in etiology. Rule out pulmonary embolism.",
                "plan": "Order ECG, CXR, D-dimer. Prescribe NSAIDs for pain relief. Follow-up in 48 hours.",
                "icd10_code": "R07.1"
            }
        }
    }


class ErrorResponse(BaseModel):
    detail: str
    error_type: str