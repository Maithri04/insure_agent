"""
services/pdf_service.py

PDF Report Generation using reportlab.platypus.

Generates a professional prior authorization report PDF including:
  • Hospital header with case ID and timestamp
  • Patient demographics
  • ICD-10 + Procedure details
  • Full SOAP note (4 sections)
  • Clinical evidence summary
  • Justification text
  • Risk flags table
  • Approval probability + recommendation (color-coded)
  • Reasons + suggestions

Saved to: reports/{case_id}.pdf
"""

import os
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# PDF output directory — relative to backend root
REPORTS_DIR = Path("reports")


# ─────────────────────────────────────────────────────────────────────────────
# Color Palette
# ─────────────────────────────────────────────────────────────────────────────

def _get_recommendation_color(recommendation: str):
    """Return a reportlab Color for the approval recommendation badge."""
    from reportlab.lib import colors
    mapping = {
        "APPROVED":        colors.HexColor("#16a34a"),   # green
        "LIKELY APPROVED": colors.HexColor("#2563eb"),   # blue
        "NEEDS REVIEW":    colors.HexColor("#d97706"),   # amber
        "LIKELY DENIED":   colors.HexColor("#ea580c"),   # orange
        "DENIED":          colors.HexColor("#dc2626"),   # red
    }
    return mapping.get(recommendation, colors.HexColor("#6b7280"))


def _get_severity_color(severity: str):
    from reportlab.lib import colors
    mapping = {
        "high":     colors.HexColor("#dc2626"),
        "critical": colors.HexColor("#dc2626"),
        "medium":   colors.HexColor("#d97706"),
        "low":      colors.HexColor("#2563eb"),
    }
    return mapping.get(severity.lower(), colors.HexColor("#6b7280"))


# ─────────────────────────────────────────────────────────────────────────────
# Style Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _build_styles():
    """Build and return a StyleSheet with all custom paragraph styles."""
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT

    styles = getSampleStyleSheet()

    styles.add(ParagraphStyle(
        name="HospitalName",
        fontSize=22, fontName="Helvetica-Bold",
        textColor=colors.HexColor("#1e3a5f"),
        spaceAfter=2, alignment=TA_CENTER,
    ))
    styles.add(ParagraphStyle(
        name="HospitalSub",
        fontSize=10, fontName="Helvetica",
        textColor=colors.HexColor("#64748b"),
        spaceAfter=4, alignment=TA_CENTER,
    ))
    styles.add(ParagraphStyle(
        name="ReportTitle",
        fontSize=14, fontName="Helvetica-Bold",
        textColor=colors.HexColor("#1e3a5f"),
        spaceAfter=4, alignment=TA_CENTER,
    ))
    styles.add(ParagraphStyle(
        name="CaseID",
        fontSize=11, fontName="Helvetica-Bold",
        textColor=colors.HexColor("#2563eb"),
        spaceAfter=2, alignment=TA_CENTER,
    ))
    styles.add(ParagraphStyle(
        name="SectionHeader",
        fontSize=12, fontName="Helvetica-Bold",
        textColor=colors.white,
        spaceBefore=10, spaceAfter=4,
        leftIndent=6,
    ))
    styles.add(ParagraphStyle(
        name="FieldLabel",
        fontSize=9, fontName="Helvetica-Bold",
        textColor=colors.HexColor("#374151"),
        spaceAfter=1,
    ))
    styles.add(ParagraphStyle(
        name="FieldValue",
        fontSize=9, fontName="Helvetica",
        textColor=colors.HexColor("#111827"),
        spaceAfter=4, leftIndent=8,
    ))
    styles.add(ParagraphStyle(
        name="SOAPText",
        fontSize=9, fontName="Helvetica",
        textColor=colors.HexColor("#1f2937"),
        spaceAfter=6, leftIndent=8,
        leading=13,
    ))
    styles.add(ParagraphStyle(
        name="BulletItem",
        fontSize=9, fontName="Helvetica",
        textColor=colors.HexColor("#374151"),
        spaceAfter=3, leftIndent=12,
        bulletIndent=4,
    ))
    styles.add(ParagraphStyle(
        name="FooterText",
        fontSize=8, fontName="Helvetica",
        textColor=colors.HexColor("#9ca3af"),
        alignment=TA_CENTER,
    ))
    styles.add(ParagraphStyle(
        name="ApprovalLabel",
        fontSize=18, fontName="Helvetica-Bold",
        textColor=colors.white,
        alignment=TA_CENTER,
        spaceAfter=2,
    ))
    styles.add(ParagraphStyle(
        name="JustificationText",
        fontSize=9, fontName="Helvetica",
        textColor=colors.HexColor("#1f2937"),
        leading=14, spaceAfter=4,
    ))

    return styles


# ─────────────────────────────────────────────────────────────────────────────
# Section Builder Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _section_header(title: str, styles):
    """Return a colored section header bar."""
    from reportlab.platypus import Paragraph, Table, TableStyle
    from reportlab.lib import colors

    header_para = Paragraph(f"  {title}", styles["SectionHeader"])
    table = Table([[header_para]], colWidths=["100%"])
    table.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), colors.HexColor("#1e3a5f")),
        ("TOPPADDING",    (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING",   (0, 0), (-1, -1), 8),
    ]))
    return table


def _field_row(label: str, value: str, styles):
    """Return a label + value pair as a 2-column table row."""
    from reportlab.platypus import Paragraph, Table, TableStyle
    from reportlab.lib import colors

    row = Table(
        [[Paragraph(label, styles["FieldLabel"]), Paragraph(str(value or "—"), styles["FieldValue"])]],
        colWidths=["35%", "65%"],
    )
    row.setStyle(TableStyle([
        ("VALIGN",       (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING",   (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 2),
    ]))
    return row


# ─────────────────────────────────────────────────────────────────────────────
# Main PDF Generator
# ─────────────────────────────────────────────────────────────────────────────

async def generate_pdf(case_data: dict) -> str:
    """
    Generate a professional PDF report for a case using reportlab.platypus.

    Args:
        case_data : dict from case_service.get_case_by_id() or CaseSaveRequest fields

    Returns:
        str — relative path to the generated PDF file (e.g. "reports/HOSP5.pdf")

    Raises:
        RuntimeError if reportlab is not installed or PDF write fails
    """
    try:
        from reportlab.platypus import (
            SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
            HRFlowable, KeepTogether,
        )
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.units import mm
        from reportlab.lib import colors
        from reportlab.lib.styles import ParagraphStyle
    except ImportError as exc:
        raise RuntimeError(
            "reportlab not installed. Add it to requirements.txt: reportlab>=4.0"
        ) from exc

    # Ensure output directory exists
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    case_id  = case_data.get("case_id", "UNKNOWN")
    pdf_path = REPORTS_DIR / f"{case_id}.pdf"

    styles = _build_styles()
    story  = []

    # ── 1. Hospital Header ────────────────────────────────────────────────
    story.append(Paragraph("InsureMind AI Medical Center", styles["HospitalName"]))
    story.append(Paragraph("Prior Authorization Report  |  Powered by InsureMind AI", styles["HospitalSub"]))
    story.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor("#1e3a5f")))
    story.append(Spacer(1, 4))
    story.append(Paragraph("PRIOR AUTHORIZATION REPORT", styles["ReportTitle"]))
    story.append(Paragraph(f"Case ID: {case_id}", styles["CaseID"]))
    story.append(Paragraph(
        f"Generated: {datetime.now(timezone.utc).strftime('%B %d, %Y  %H:%M UTC')}",
        styles["HospitalSub"],
    ))
    story.append(Spacer(1, 8))

    # ── 2. Approval Badge ────────────────────────────────────────────────
    recommendation  = case_data.get("approval_recommendation", "NEEDS REVIEW")
    probability     = case_data.get("approval_probability", 0.0)
    badge_color     = _get_recommendation_color(recommendation)

    badge_para = Paragraph(
        f"{recommendation}  —  {probability:.1%}",
        styles["ApprovalLabel"],
    )
    badge_table = Table([[badge_para]], colWidths=["100%"])
    badge_table.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), badge_color),
        ("TOPPADDING",    (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
        ("ROUNDEDCORNERS", (0, 0), (-1, -1), 8),
    ]))
    story.append(badge_table)
    story.append(Spacer(1, 10))

    # ── 3. Patient Details & Clinical Profile ─────────────────────────────
    story.append(_section_header("PATIENT DETAILS & CLINICAL PROFILE", styles))
    story.append(Spacer(1, 4))
    demographics = [
        ("Patient Name",  case_data.get("patient_name", "—")),
        ("Age",           str(case_data.get("patient_age", "—")) + " years"),
        ("Gender",        case_data.get("patient_gender", "—").capitalize()),
        ("TPA / Insurer", case_data.get("tpa", "—")),
        ("Disease Desc.", case_data.get("disease_description", "—")),
        ("Raw Procedure", case_data.get("procedure", "—")),
    ]
    for label, value in demographics:
        story.append(_field_row(label, value, styles))
    story.append(Spacer(1, 8))

    # ── 4. Diagnosis & Procedure ──────────────────────────────────────────
    story.append(_section_header("DIAGNOSIS & PROCEDURE", styles))
    story.append(Spacer(1, 4))

    # Get ICD and procedure from either flat fields or soap_json structure
    soap = case_data.get("soap_json") or {}
    if isinstance(soap, str):
        import json as _json
        try:
            soap = _json.loads(soap)
        except Exception:
            soap = {}

    dx_data = [
        ("ICD-10 Code",          case_data.get("icd_code", "—")),
        ("ICD-10 Description",   case_data.get("icd_description", "—")),
        ("Procedure Code",       case_data.get("procedure_code", "—")),
        ("Procedure Description", case_data.get("procedure_description", "—")),
        ("Condition Type",       case_data.get("condition_type", "—").capitalize()),
        ("Medications",          case_data.get("medications") or "None documented"),
    ]
    for label, value in dx_data:
        story.append(_field_row(label, value, styles))
    story.append(Spacer(1, 8))

    # ── 5. SOAP Note ─────────────────────────────────────────────────────
    story.append(_section_header("SOAP NOTE", styles))
    story.append(Spacer(1, 4))

    soap_sections = [
        ("S — Subjective",  soap.get("subjective", case_data.get("soap_subjective", "—"))),
        ("O — Objective",   soap.get("objective",  case_data.get("soap_objective",  "—"))),
        ("A — Assessment",  soap.get("assessment", case_data.get("soap_assessment", "—"))),
        ("P — Plan",        soap.get("plan",       case_data.get("soap_plan",       "—"))),
    ]
    for soap_label, soap_text in soap_sections:
        story.append(Paragraph(soap_label, styles["FieldLabel"]))
        story.append(Paragraph(str(soap_text), styles["SOAPText"]))
    story.append(Spacer(1, 8))

    # ── 6. Clinical Evidence ──────────────────────────────────────────────
    story.append(_section_header("CLINICAL EVIDENCE", styles))
    story.append(Spacer(1, 4))

    evidence_score   = case_data.get("evidence_score", 0.0)
    missing_evidence = case_data.get("missing_evidence") or []
    if isinstance(missing_evidence, str):
        import json as _json
        try:
            missing_evidence = _json.loads(missing_evidence)
        except Exception:
            missing_evidence = []

    story.append(_field_row(
        "Evidence Completeness",
        f"{float(evidence_score):.0%} complete",
        styles,
    ))

    evidence_fields = [
        ("Duration of Symptoms",  case_data.get("duration_of_symptoms")),
        ("Prior Treatment",       case_data.get("prior_treatment")),
        ("Severity",              case_data.get("severity")),
        ("Investigations",        case_data.get("investigations")),
        ("Specialist Referral",   case_data.get("specialist_referral")),
    ]
    for label, value in evidence_fields:
        status_mark = "✓" if value and value.strip().lower() not in ("none", "no", "nothing", "n/a") else "✗ Missing"
        display_val = value if status_mark == "✓" else "Not provided"
        story.append(_field_row(f"{status_mark}  {label}", display_val, styles))

    if missing_evidence:
        story.append(Paragraph(
            f"Missing Evidence: {', '.join(missing_evidence)}",
            styles["BulletItem"],
        ))
    story.append(Spacer(1, 8))

    # ── 7. Clinical Justification ─────────────────────────────────────────
    story.append(_section_header("CLINICAL JUSTIFICATION", styles))
    story.append(Spacer(1, 4))

    just_score = case_data.get("justification_score", 0.0)
    story.append(_field_row("Justification Score", f"{float(just_score):.2f} / 1.00", styles))

    just_text = case_data.get("justification_text", "")
    if just_text:
        story.append(Paragraph(just_text, styles["JustificationText"]))
    story.append(Spacer(1, 8))

    # ── 8. Risk Flags ────────────────────────────────────────────────────
    risk_flags = case_data.get("risk_flags") or []
    if isinstance(risk_flags, str):
        import json as _json
        try:
            risk_flags = _json.loads(risk_flags)
        except Exception:
            risk_flags = []

    if risk_flags:
        story.append(_section_header("RISK FLAGS", styles))
        story.append(Spacer(1, 4))

        flag_data = [["Severity", "Flag", "Description"]]
        for flag in risk_flags:
            severity    = flag.get("severity", "low")
            flag_color  = _get_severity_color(severity)
            flag_data.append([
                Paragraph(f'<font color="{flag_color.hexval() if hasattr(flag_color, "hexval") else "#dc2626"}">'
                          f'<b>{severity.upper()}</b></font>', styles["FieldValue"]),
                Paragraph(flag.get("flag", ""), styles["FieldValue"]),
                Paragraph(flag.get("description", ""), styles["SOAPText"]),
            ])

        flag_table = Table(flag_data, colWidths=["15%", "30%", "55%"])
        flag_table.setStyle(TableStyle([
            ("BACKGROUND",    (0, 0), (-1, 0),  colors.HexColor("#e2e8f0")),
            ("FONTNAME",      (0, 0), (-1, 0),  "Helvetica-Bold"),
            ("FONTSIZE",      (0, 0), (-1, -1), 8),
            ("GRID",          (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
            ("VALIGN",        (0, 0), (-1, -1), "TOP"),
            ("TOPPADDING",    (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        story.append(flag_table)
        story.append(Spacer(1, 8))

    # ── 9. Reasons & Suggestions ──────────────────────────────────────────
    reasons     = case_data.get("reasons") or []
    suggestions = case_data.get("suggestions") or []

    if isinstance(reasons, str):
        import json as _json
        try:
            reasons = _json.loads(reasons)
        except Exception:
            reasons = []
    if isinstance(suggestions, str):
        import json as _json
        try:
            suggestions = _json.loads(suggestions)
        except Exception:
            suggestions = []

    if reasons or suggestions:
        story.append(_section_header("DECISION REASONING & RECOMMENDATIONS", styles))
        story.append(Spacer(1, 4))

        if reasons:
            story.append(Paragraph("<b>Approval Decision Reasons:</b>", styles["FieldLabel"]))
            for reason in reasons:
                story.append(Paragraph(f"• {reason}", styles["BulletItem"]))
            story.append(Spacer(1, 4))

        if suggestions:
            story.append(Paragraph("<b>Recommendations for Improvement:</b>", styles["FieldLabel"]))
            for suggestion in suggestions:
                story.append(Paragraph(f"→ {suggestion}", styles["BulletItem"]))
        story.append(Spacer(1, 8))

    # ── 10. Footer ────────────────────────────────────────────────────────
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#e2e8f0")))
    story.append(Spacer(1, 4))
    story.append(Paragraph(
        f"InsureMind AI  |  Case ID: {case_id}  |  "
        f"This report is generated by AI and must be reviewed by a licensed medical professional.",
        styles["FooterText"],
    ))

    # ── Build PDF ─────────────────────────────────────────────────────────
    doc = SimpleDocTemplate(
        str(pdf_path),
        pagesize=A4,
        rightMargin=20 * mm,
        leftMargin=20 * mm,
        topMargin=15 * mm,
        bottomMargin=15 * mm,
        title=f"InsureMind Prior Authorization Report — {case_id}",
        author="InsureMind AI",
    )
    doc.build(story)

    relative_path = str(pdf_path)
    logger.info("PDF generated — case_id: %s | path: %s", case_id, relative_path)
    return relative_path