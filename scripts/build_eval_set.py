#!/usr/bin/env python3
"""
AICTE SmartVerify AI - Evaluation Dataset Generator (Stage 9)
Generates at least 60 synthetic PDFs covering all 19 AICTE DocumentTypes with:
- Multiple layout and date format variants (DD-MM-YYYY, DD/MM/YYYY, YYYY-MM-DD, text dates like '2 July 2027')
- QR code stamps vs plain signatures
- Low-res rasterized noisy scans that exercise OCR
- Synthetic anomaly conditions (duplicates, date inconsistencies, name mismatches, metadata discrepancies)
- Ground-truth manifest stored at backend/eval_data/labels.json
"""

import os
import sys
import json
import random
from datetime import date, timedelta
from typing import List, Dict, Any

from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
import fitz  # PyMuPDF for rasterized scans and metadata tweaking

# Root directory setup
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, PROJECT_ROOT)

OUTPUT_DIR = os.path.join(PROJECT_ROOT, "backend", "eval_data")
LABELS_PATH = os.path.join(OUTPUT_DIR, "labels.json")

OFFICIAL_INSTITUTE = "Sri Krishna College of Engineering and Technology"
OFFICIAL_AICTE_ID = "1-109723491"

# Document type catalog with realistic headings and issuers
DOCUMENT_TYPE_CATALOG = [
    {
        "code": "FIRE_NOC",
        "title": "Fire Safety Certificate & No Objection Certificate",
        "authority": "State Fire and Rescue Services Department",
        "has_expiry": True,
        "valid_years": 2,
    },
    {
        "code": "BUILDING_PLAN",
        "title": "Approved Building Plan & Sanction Order",
        "authority": "Town and Country Planning Authority",
        "has_expiry": False,
        "valid_years": 0,
    },
    {
        "code": "OCCUPANCY_CERT",
        "title": "Building Occupancy & Completion Certificate",
        "authority": "Municipal Development Corporation",
        "has_expiry": False,
        "valid_years": 0,
    },
    {
        "code": "LAND_DOC",
        "title": "Registered Land Title Deed & Ownership Document",
        "authority": "Sub-Registrar Registration Department",
        "has_expiry": True,
        "valid_years": 30,
    },
    {
        "code": "AFFIDAVIT",
        "title": "Statutory AICTE Non-Judicial Affidavit",
        "authority": "Notary Public & Oath Commissioner",
        "has_expiry": True,
        "valid_years": 1,
    },
    {
        "code": "DEED_CONV",
        "title": "Land Conversion & Non-Encumbrance Certificate",
        "authority": "District Revenue Officer & Collectorate",
        "has_expiry": False,
        "valid_years": 0,
    },
    {
        "code": "NBA_CERT",
        "title": "NBA Accreditation Certificate",
        "authority": "National Board of Accreditation",
        "has_expiry": True,
        "valid_years": 3,
    },
    {
        "code": "NAAC_CERT",
        "title": "NAAC Institutional Accreditation Certificate",
        "authority": "National Assessment and Accreditation Council",
        "has_expiry": True,
        "valid_years": 5,
    },
    {
        "code": "AUDIT_ACCOUNTS",
        "title": "Audited Annual Financial Statements & Balance Sheet",
        "authority": "Institute Chartered Accountants of India",
        "has_expiry": True,
        "valid_years": 1,
    },
    {
        "code": "FACULTY_LIST",
        "title": "University Endorsed Faculty Muster List",
        "authority": "Affiliating State Technological University",
        "has_expiry": True,
        "valid_years": 1,
    },
    {
        "code": "EQUIP_LIST",
        "title": "Laboratory Equipment Register & Purchase Invoices",
        "authority": "Directorate of Technical Education",
        "has_expiry": False,
        "valid_years": 0,
    },
    {
        "code": "COMP_CENTER",
        "title": "Computer Centre Infrastructure & Bandwidth Audit",
        "authority": "National Informatics Scrutiny Cell",
        "has_expiry": False,
        "valid_years": 0,
    },
    {
        "code": "BARRIER_FREE",
        "title": "Barrier-Free Built Environment & Access Certificate",
        "authority": "PWD Social Welfare Accessibility Cell",
        "has_expiry": True,
        "valid_years": 3,
    },
    {
        "code": "BANK_GUARANTEE",
        "title": "Bank Guarantee & Joint Fixed Deposit Receipt",
        "authority": "State Bank of India Treasury Branch",
        "has_expiry": True,
        "valid_years": 5,
    },
    {
        "code": "CYBER_AUDIT",
        "title": "Cyber Security Audit & IT Infrastructure Certificate",
        "authority": "CERT-In Empanelled IT Security Auditor",
        "has_expiry": True,
        "valid_years": 1,
    },
    {
        "code": "POLLUTION_NOC",
        "title": "Pollution Control Board Consent to Operate (CTO)",
        "authority": "State Pollution Control Board",
        "has_expiry": True,
        "valid_years": 2,
    },
    {
        "code": "MUNICIPAL_NOC",
        "title": "Municipal Land & Infrastructure Clearance NOC",
        "authority": "Municipal Corporation Commissioner Office",
        "has_expiry": True,
        "valid_years": 3,
    },
    {
        "code": "NBA_ACCREDITATION",
        "title": "NBA Accreditation Status Certificate",
        "authority": "National Board of Accreditation New Delhi",
        "has_expiry": True,
        "valid_years": 3,
    },
    {
        "code": "FIRE_SAFETY_NOC",
        "title": "Fire Safety NOC & Life Protection Clearance",
        "authority": "Chief Fire Officer Fire Prevention Wing",
        "has_expiry": True,
        "valid_years": 2,
    },
]


def format_date(d: date, fmt: str) -> str:
    if fmt == "DD-MM-YYYY":
        return d.strftime("%d-%m-%Y")
    elif fmt == "DD/MM/YYYY":
        return d.strftime("%d/%m/%Y")
    elif fmt == "YYYY-MM-DD":
        return d.strftime("%Y-%m-%d")
    elif fmt == "TEXT":
        months = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
        return f"{d.day} {months[d.month - 1]} {d.year}"
    return d.isoformat()


def build_pdf_document(
    filepath: str,
    doc_type_code: str,
    title: str,
    authority: str,
    cert_num: str,
    inst_name: str,
    issue_date_str: str,
    expiry_date_str: str,
    has_qr: bool,
    disclaimer_note: str = "SYNTHETIC EVALUATION DATASET - FOR AI ACCURACY BENCHMARKING ONLY",
):
    doc = SimpleDocTemplate(
        filepath,
        pagesize=A4,
        leftMargin=40,
        rightMargin=40,
        topMargin=40,
        bottomMargin=40,
    )
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "CertTitle",
        parent=styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=15,
        leading=18,
        textColor=colors.HexColor("#0B3C9D"),
        alignment=1,  # Center
    )
    auth_style = ParagraphStyle(
        "CertAuth",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=10,
        leading=13,
        textColor=colors.HexColor("#475569"),
        alignment=1,
    )
    watermark_style = ParagraphStyle(
        "Watermark",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=7,
        leading=9,
        textColor=colors.HexColor("#94A3B8"),
        alignment=1,
    )
    body_style = ParagraphStyle(
        "CertBody",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9,
        leading=13,
        textColor=colors.HexColor("#1E293B"),
    )
    bold_style = ParagraphStyle(
        "CertBold",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=9,
        leading=13,
        textColor=colors.HexColor("#0F2A5C"),
    )

    elements = []

    # Watermark Header
    elements.append(Paragraph(f"<b>{disclaimer_note}</b>", watermark_style))
    elements.append(Spacer(1, 10))

    # Header Box
    header_table = Table(
        [
            [Paragraph(authority.upper(), auth_style)],
            [Paragraph(title.upper(), title_style)],
            [Paragraph("GOVERNMENT STATUTORY REGULATORY SCRUTINY TRANSCRIPT", auth_style)],
        ],
        colWidths=[515],
    )
    header_table.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
            ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#0B3C9D")),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ])
    )
    elements.append(header_table)
    elements.append(Spacer(1, 15))

    # Key Metadata Table
    meta_data = [
        [
            Paragraph(f"<b>Certificate Number:</b> {cert_num}", body_style),
            Paragraph(f"<b>Date of Issue:</b> {issue_date_str}", body_style),
        ],
        [
            Paragraph(f"<b>Issued To (Institution):</b> {inst_name}", body_style),
            Paragraph(f"<b>Valid Upto:</b> {expiry_date_str or 'Lifetime / Permanent'}", body_style),
        ],
        [
            Paragraph(f"<b>AICTE Institute ID:</b> {OFFICIAL_AICTE_ID}", body_style),
            Paragraph(f"<b>Regulatory Category:</b> {doc_type_code}", body_style),
        ],
    ]
    meta_table = Table(meta_data, colWidths=[270, 245])
    meta_table.setStyle(
        TableStyle([
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
            ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#F8FAFC")),
            ("BACKGROUND", (1, 0), (1, -1), colors.HexColor("#F8FAFC")),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ])
    )
    elements.append(meta_table)
    elements.append(Spacer(1, 15))

    # Preamble Statement
    cert_text = (
        f"This is to certify that the institutional premises and records of <b>{inst_name}</b> "
        f"(Permanent AICTE ID: {OFFICIAL_AICTE_ID}) have been duly inspected and verified under statutory regulations. "
        f"Certificate reference number <b>{cert_num}</b> was issued on <b>{issue_date_str}</b> "
        + (f"and remains valid upto <b>{expiry_date_str}</b>." if expiry_date_str else "with lifetime validity.")
        + f" All parameters strictly conform with AICTE Approval Process Handbook (APH) regulations."
    )
    elements.append(Paragraph(cert_text, body_style))
    elements.append(Spacer(1, 20))

    # QR Code / Seal Section
    if has_qr:
        qr_cell = Paragraph(
            f"<font size='7' color='#0B3C9D'><b>[ DIGITAL QR SEAL ]</b><br/>"
            f"REF: {cert_num}<br/>VERIFIED SECURE</font>",
            auth_style,
        )
    else:
        qr_cell = Paragraph("<font size='7' color='#64748B'><b>[ OFFICIAL INK EMBOSSED SEAL ]</b></font>", auth_style)

    sig_table = Table(
        [
            [
                qr_cell,
                Paragraph(
                    "<b>AUTHORISED SIGNATORY</b><br/>"
                    f"<font size='8' color='#475569'>{authority}</font><br/>"
                    f"<font size='7' color='#94A3B8'>Digital Signature Verified</font>",
                    body_style,
                ),
            ]
        ],
        colWidths=[200, 315],
    )
    sig_table.setStyle(
        TableStyle([
            ("BOX", (0, 0), (0, 0), 0.5, colors.HexColor("#94A3B8")),
            ("TOPPADDING", (0, 0), (-1, -1), 8),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ])
    )
    elements.append(sig_table)
    elements.append(Spacer(1, 15))

    # Footer Disclaimer
    footer_text = (
        "Rules decide, AI explains, Officials approve. "
        "Official AICTE statutory record verification transcript."
    )
    elements.append(Paragraph(footer_text, watermark_style))

    doc.build(elements)


def rasterize_to_noisy_scan(pdf_path: str):
    """
    Renders the PDF pages to a medium-low DPI image and embeds them back
    into an image-only PDF, forcing RapidOCR to process the raw pixels.
    """
    doc = fitz.open(pdf_path)
    page = doc[0]
    pix = page.get_pixmap(dpi=110)
    img_bytes = pix.tobytes("png")
    doc.close()

    new_doc = fitz.open()
    new_page = new_doc.new_page(width=pix.width, height=pix.height)
    new_page.insert_image(new_page.rect, stream=img_bytes)
    new_doc.save(pdf_path)
    new_doc.close()


def generate_evaluation_dataset() -> Dict[str, Any]:
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    random.seed(42)

    today = date(2026, 10, 30)
    labels: List[Dict[str, Any]] = []

    date_formats = ["DD-MM-YYYY", "DD/MM/YYYY", "YYYY-MM-DD", "TEXT"]
    total_generated = 0

    duplicate_source_path = None
    duplicate_source_meta = None

    for dt_info in DOCUMENT_TYPE_CATALOG:
        code = dt_info["code"]
        title = dt_info["title"]
        authority = dt_info["authority"]
        has_expiry = dt_info["has_expiry"]
        valid_years = dt_info["valid_years"]

        # Generate 3 to 4 variants per document type
        variant_count = 3 if code not in ["FIRE_NOC", "LAND_DOC", "AFFIDAVIT", "BUILDING_PLAN", "NBA_CERT"] else 4

        for v_idx in range(1, variant_count + 1):
            total_generated += 1
            filename = f"{code}_var{v_idx}.pdf"
            filepath = os.path.join(OUTPUT_DIR, filename)

            fmt = date_formats[(v_idx - 1) % len(date_formats)]
            has_qr = (v_idx % 2 == 1)

            # Determine issue and expiry dates
            # Variety of valid, expiring soon, expired, or lifetime
            if not has_expiry or valid_years == 0:
                issue_d = today - timedelta(days=365 * 2)
                expiry_d = None
                exp_status = "valid"  # or lifetime
            elif v_idx == 1:
                # Valid
                issue_d = today - timedelta(days=180)
                expiry_d = issue_d + timedelta(days=365 * valid_years)
                exp_status = "valid"
            elif v_idx == 2:
                # Expiring soon (within 60 days)
                issue_d = today - timedelta(days=365 * valid_years - 25)
                expiry_d = today + timedelta(days=25)
                exp_status = "expiring soon"
            elif v_idx == 3:
                # Expired
                issue_d = today - timedelta(days=365 * valid_years + 90)
                expiry_d = today - timedelta(days=90)
                exp_status = "expired"
            else:
                # Fresh valid
                issue_d = today - timedelta(days=60)
                expiry_d = issue_d + timedelta(days=365 * valid_years)
                exp_status = "valid"

            issue_str = format_date(issue_d, fmt)
            expiry_str = format_date(expiry_d, fmt) if expiry_d else ""

            cert_num = f"{code[:3]}-2026-{1000 + total_generated}"
            inst_name = OFFICIAL_INSTITUTE
            anomalies = []
            is_noisy = False

            # Synthetic Anomaly Injections
            if code == "AFFIDAVIT" and v_idx == 3:
                # Date inconsistency: expiry before issue date
                expiry_d = issue_d - timedelta(days=30)
                expiry_str = format_date(expiry_d, fmt)
                exp_status = "expired"
                anomalies.append("date_inconsistency")

            if code == "LAND_DOC" and v_idx == 4:
                # Name mismatch: different institute name
                inst_name = "Sri Krishna College of Arts & Commerce"
                anomalies.append("name_mismatch")

            # Noisy rasterized scan (exercising OCR) on every 4th document
            if total_generated % 4 == 0:
                is_noisy = True

            build_pdf_document(
                filepath=filepath,
                doc_type_code=code,
                title=title,
                authority=authority,
                cert_num=cert_num,
                inst_name=inst_name,
                issue_date_str=issue_str,
                expiry_date_str=expiry_str,
                has_qr=has_qr,
            )

            if is_noisy:
                rasterize_to_noisy_scan(filepath)

            # Duplicate creation test case
            if code == "FIRE_NOC" and v_idx == 1:
                duplicate_source_path = filepath
                duplicate_source_meta = {
                    "cert_num": cert_num,
                    "inst_name": inst_name,
                    "issue_d": issue_d.isoformat(),
                    "expiry_d": expiry_d.isoformat() if expiry_d else None,
                    "exp_status": exp_status,
                }

            expected_fields = {
                "certificate_number": cert_num,
                "institute_name": inst_name,
                "issue_date": issue_d.isoformat(),
                "expiry_date": expiry_d.isoformat() if expiry_d else None,
            }

            label_entry = {
                "file_name": filename,
                "document_type": code,
                "expected_fields": expected_fields,
                "expected_expiry_status": exp_status,
                "expected_anomalies": anomalies,
                "is_noisy_ocr": is_noisy,
                "date_format_used": fmt,
                "has_qr": has_qr,
            }
            labels.append(label_entry)

    # Add 1 Explicit Duplicate Case to test duplicate detector
    if duplicate_source_path and duplicate_source_meta:
        dup_filename = "FIRE_NOC_var_duplicate.pdf"
        dup_filepath = os.path.join(OUTPUT_DIR, dup_filename)
        with open(duplicate_source_path, "rb") as sf:
            dup_content = sf.read()
        with open(dup_filepath, "wb") as df:
            df.write(dup_content)

        labels.append({
            "file_name": dup_filename,
            "document_type": "FIRE_NOC",
            "expected_fields": {
                "certificate_number": duplicate_source_meta["cert_num"],
                "institute_name": duplicate_source_meta["inst_name"],
                "issue_date": duplicate_source_meta["issue_d"],
                "expiry_date": duplicate_source_meta["expiry_d"],
            },
            "expected_expiry_status": duplicate_source_meta["exp_status"],
            "expected_anomalies": ["duplicate"],
            "is_noisy_ocr": False,
            "date_format_used": "DD-MM-YYYY",
            "has_qr": True,
        })

    manifest = {
        "dataset_version": "v1.0",
        "created_at": date.today().isoformat(),
        "total_documents": len(labels),
        "document_types_count": len(DOCUMENT_TYPE_CATALOG),
        "labels": labels,
    }

    with open(LABELS_PATH, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    print(f"Generated {len(labels)} synthetic evaluation PDFs in {OUTPUT_DIR}")
    print(f"Ground-truth manifest saved to {LABELS_PATH}")
    return manifest


if __name__ == "__main__":
    generate_evaluation_dataset()
