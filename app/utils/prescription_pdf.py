from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)


def generate_prescription_pdf(patient, doctor, record, prescription):
    """
    Generate a prescription PDF in memory.

    Returns:
        bytes: PDF file content
    """

    buffer = BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=18 * mm,
        leftMargin=18 * mm,
        topMargin=18 * mm,
        bottomMargin=18 * mm,
    )

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "PrescriptionTitle",
        parent=styles["Title"],
        alignment=TA_CENTER,
        fontSize=20,
        spaceAfter=6,
    )

    normal_style = ParagraphStyle(
        "NormalText",
        parent=styles["Normal"],
        fontSize=10,
        leading=14,
    )

    heading_style = ParagraphStyle(
        "SectionHeading",
        parent=styles["Heading2"],
        fontSize=13,
        spaceBefore=10,
        spaceAfter=6,
    )

    story = []

    # Header
    story.append(Paragraph("SMARTCARE", title_style))
    story.append(
        Paragraph(
            "Hospital Management System - Prescription",
            ParagraphStyle(
                "Subtitle",
                parent=normal_style,
                alignment=TA_CENTER,
                fontSize=10,
            ),
        )
    )

    story.append(Spacer(1, 10))

    # Patient and doctor information
    patient_data = [
        ["Patient Name", patient.full_name],
        ["Patient Code", patient.patient_code],
        ["Doctor", f"Dr. {doctor.full_name}"],
    ]

    if getattr(doctor, "specialization", None):
        patient_data.append(
            ["Specialization", doctor.specialization]
        )

    if getattr(patient, "age", None) is not None:
        patient_data.append(["Age", str(patient.age)])

    if getattr(patient, "gender", None):
        patient_data.append(["Gender", patient.gender])

    patient_table = Table(
        patient_data,
        colWidths=[42 * mm, 125 * mm],
    )

    patient_table.setStyle(
        TableStyle(
            [
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("BACKGROUND", (0, 0), (0, -1), colors.lightgrey),
                ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                ("FONTNAME", (1, 0), (1, -1), "Helvetica"),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )

    story.append(patient_table)

    # Diagnosis
    story.append(Paragraph("Diagnosis", heading_style))
    story.append(
        Paragraph(
            record.diagnosis or "-",
            normal_style,
        )
    )

    # Clinical notes
    if record.clinical_notes:
        story.append(Paragraph("Clinical Notes", heading_style))
        story.append(
            Paragraph(
                record.clinical_notes,
                normal_style,
            )
        )

    # Medicines
    story.append(Paragraph("Prescribed Medicines", heading_style))

    medicine_data = [
        [
            "Medicine",
            "Dosage",
            "Frequency",
            "Duration",
            "Instructions",
        ]
    ]

    for item in prescription.items:
        medicine_data.append(
            [
                item.medicine_name or "-",
                item.dosage or "-",
                item.frequency or "-",
                item.duration or "-",
                item.instructions or "-",
            ]
        )

    medicine_table = Table(
        medicine_data,
        colWidths=[
            35 * mm,
            27 * mm,
            27 * mm,
            25 * mm,
            53 * mm,
        ],
        repeatRows=1,
    )

    medicine_table.setStyle(
        TableStyle(
            [
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )

    story.append(medicine_table)

    # Advice
    if prescription.advice:
        story.append(Paragraph("Doctor's Advice", heading_style))
        story.append(
            Paragraph(
                prescription.advice,
                normal_style,
            )
        )

    # Follow-up
    if record.follow_up_date:
        story.append(Paragraph("Follow-up Date", heading_style))
        story.append(
            Paragraph(
                record.follow_up_date.strftime("%d %B %Y"),
                normal_style,
            )
        )

    story.append(Spacer(1, 20))

    story.append(
        Paragraph(
            "This prescription was generated electronically by SmartCare.",
            ParagraphStyle(
                "Footer",
                parent=normal_style,
                alignment=TA_CENTER,
                fontSize=8,
            ),
        )
    )

    doc.build(story)

    pdf_bytes = buffer.getvalue()
    buffer.close()

    return pdf_bytes