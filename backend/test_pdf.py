import asyncio
from services.pdf_service import generate_pdf

async def main():
    try:
        case_data = {
            "case_id": "HOSP100",
            "approval_recommendation": "APPROVED",
            "approval_probability": 0.95,
            "patient_name": "Jane Doe",
            "patient_age": 45,
            "patient_gender": "female",
            "condition_type": "chronic",
            "icd_code": "E11.9",
            "soap_json": {
                "subjective": "Patient complains of fatigue.",
                "objective": "Blood pressure normal.",
                "assessment": "Diabetes type 2.",
                "plan": "Continue metformin."
            },
            "justification_text": "Patient meets all criteria for continued medication.",
            "risk_flags": [
                {"severity": "high", "flag": "Missing Labs", "description": "HbA1c not provided."}
            ]
        }
        print("Starting generate_pdf...", flush=True)
        path = await generate_pdf(case_data)
        print(f"Generated: {path}", flush=True)
    except Exception as e:
        print(f"Error: {e}", flush=True)

if __name__ == "__main__":
    asyncio.run(main())
