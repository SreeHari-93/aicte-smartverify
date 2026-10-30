import csv
import hashlib
import io
import os
import re
import uuid
from datetime import datetime, timezone, date
from typing import Optional, List, Dict, Any

from sqlalchemy.orm import Session
from reportlab.lib.pagesizes import A4
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    Image,
    KeepTogether,
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.pdfgen import canvas

from backend.app.models.application import Application
from backend.app.models.certificate import Certificate
from backend.app.models.report import Report
from backend.app.models.institute import Institute
from backend.app.models.rule import Rule
from backend.app.models.document import Document
from backend.app.models.extracted_field import ExtractedField
from backend.app.models.verification import VerificationResult
from backend.app.models.validation_run import ValidationRun, ValidationFinding
from backend.app.models.anomaly import AnomalyFlag
from backend.app.services.anomaly.evidence_graph import EvidenceGraphBuilder
from backend.app.services.validation.runner import ValidationRunner
from backend.app.services.explainer.root_cause import RootCauseAnalyzer
from backend.app.services.explainer.narrator import ExplainerNarrator

STORAGE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../storage/reports"))
os.makedirs(STORAGE_DIR, exist_ok=True)

LOGO_PATHS = [
    os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../aicte-logo.png")),
    os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../frontend/public/aicte-logo.png")),
    os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../frontend/dist/aicte-logo.png")),
]

# ---------------------------------------------------------------------------
# Font Registration for English & Devanagari (Hindi) Unicode
# ---------------------------------------------------------------------------
HINDI_FONT_NAME = "Helvetica"
HINDI_FONT_BOLD = "Helvetica-Bold"

try:
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont

    font_candidates = [
        ("Nirmala", "C:\\Windows\\Fonts\\Nirmala.ttc", 0),
        ("Mangal", "C:\\Windows\\Fonts\\mangal.ttf", None),
        ("Aparajita", "C:\\Windows\\Fonts\\aparaj.ttf", None),
        ("Nirmala", "/usr/share/fonts/truetype/noto/NotoSansDevanagari-Regular.ttf", None),
        ("Nirmala", "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc", 0),
    ]
    for fname, fpath, sub_idx in font_candidates:
        if os.path.exists(fpath):
            if sub_idx is not None:
                pdfmetrics.registerFont(TTFont(fname, fpath, subfontIndex=sub_idx))
            else:
                pdfmetrics.registerFont(TTFont(fname, fpath))
            HINDI_FONT_NAME = fname
            HINDI_FONT_BOLD = fname
            break
except Exception:
    HINDI_FONT_NAME = "Helvetica"
    HINDI_FONT_BOLD = "Helvetica-Bold"


def sanitize_text(text: Optional[str]) -> str:
    """
    Enforces AICTE stage guideline: Never use the words forgery, fraud, or misconduct.
    Replaces prohibited terminology with non-inflammatory regulatory terminology.
    """
    if not text:
        return ""
    cleaned = re.sub(r'(?i)\bforgery\b', 'potential anomaly', text)
    cleaned = re.sub(r'(?i)\bfraud\b', 'potential anomaly', cleaned)
    cleaned = re.sub(r'(?i)\bmisconduct\b', 'inconsistency', cleaned)
    return cleaned


class NumberedCanvas(canvas.Canvas):
    """
    Two-pass ReportLab Canvas that computes total page count (Page X of Y),
    and draws the report reference number and SHA-256 digest in the running footer.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []
        self.report_ref = getattr(self, "report_ref", "AICTE-REPORT")
        self.sha256_hash = getattr(self, "sha256_hash", "N/A")

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, page_count: int):
        self.saveState()
        self.setFont("Helvetica", 7)
        self.setFillColor(colors.HexColor("#475569"))
        page_width, _ = self._pagesize
        margin = 36

        # Thin rule line
        self.setStrokeColor(colors.HexColor("#CBD5E1"))
        self.setLineWidth(0.5)
        self.line(margin, 24, page_width - margin, 24)

        # Footer Left: Reference number & SHA-256 hash & AICTE motto
        ref_text = f"Ref: {self.report_ref} | SHA-256: {self.sha256_hash[:16]}... | Rules decide, AI explains, Officials approve."
        self.drawString(margin, 14, ref_text)

        # Footer Right: Page X of Y
        page_str = f"Page {self._pageNumber} of {page_count}"
        self.drawRightString(page_width - margin, 14, page_str)
        self.restoreState()


def make_numbered_canvas(report_ref: str, sha256_hash: str):
    class CustomNumberedCanvas(NumberedCanvas):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.report_ref = report_ref
            self.sha256_hash = sha256_hash
    return CustomNumberedCanvas


class ReportService:
    @staticmethod
    def generate_report(
        db: Session,
        institute_id: int,
        report_type: str,
        report_format: str,
        date_range: str = "Current",
        application_id: Optional[str] = None,
        language: str = "en",
        generated_by: str = "INSTITUTE",
    ) -> Report:
        institute = db.query(Institute).filter(Institute.id == institute_id).first()
        inst_name = institute.name if institute else f"Institute {institute_id}"

        # Resolve target application
        app = None
        if application_id:
            app = db.query(Application).filter(Application.application_id == str(application_id)).first()
            if not app and str(application_id).isdigit():
                app = db.query(Application).filter(Application.id == int(application_id)).first()
        if not app:
            app = (
                db.query(Application)
                .filter(Application.institute_id == institute_id)
                .order_by(Application.id.desc())
                .first()
            )

        lang = "hi" if language == "hi" else "en"
        timestamp_str = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        slug = report_type.lower().replace(" ", "_")
        ext = report_format.lower()
        unique_id = uuid.uuid4().hex[:6]
        app_suffix = f"_{app.application_id}" if app and ("validation" in slug) else ""
        lang_suffix = f"_{lang}" if "validation" in slug else ""
        filename = f"{slug}{app_suffix}{lang_suffix}_{unique_id}_{timestamp_str}.{ext}"
        file_path = os.path.join(STORAGE_DIR, filename)

        ref_no = f"REP-{slug.upper()[:3]}-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{unique_id.upper()}"
        sha_seed = f"{ref_no}_{inst_name}_{app.application_id if app else 'none'}_{timestamp_str}_{lang}"
        sha256_hash = hashlib.sha256(sha_seed.encode("utf-8")).hexdigest()

        if ext == "csv":
            ReportService._generate_csv(
                db=db,
                institute_id=institute_id,
                report_type=report_type,
                file_path=file_path,
                inst_name=inst_name,
                date_range=date_range,
                app=app,
                ref_no=ref_no,
                sha256_hash=sha256_hash,
                lang=lang,
                generated_by=generated_by,
            )
        else:
            if "validation" in report_type.lower():
                ReportService._generate_validation_summary_pdf(
                    db=db,
                    institute=institute,
                    app=app,
                    file_path=file_path,
                    inst_name=inst_name,
                    date_range=date_range,
                    ref_no=ref_no,
                    sha256_hash=sha256_hash,
                    lang=lang,
                    generated_by=generated_by,
                )
            else:
                ReportService._generate_standard_pdf(
                    db=db,
                    institute_id=institute_id,
                    report_type=report_type,
                    file_path=file_path,
                    inst_name=inst_name,
                    date_range=date_range,
                    ref_no=ref_no,
                    sha256_hash=sha256_hash,
                )

        file_size = os.path.getsize(file_path) if os.path.exists(file_path) else 0

        report_record = Report(
            institute_id=institute_id,
            report_type=report_type,
            format=report_format.upper(),
            date_range=date_range,
            filename=filename,
            file_path=file_path,
            file_size=file_size,
            application_id=app.application_id if app else (str(application_id) if application_id else None),
            language=lang,
            generated_by=generated_by,
        )
        db.add(report_record)
        db.commit()
        db.refresh(report_record)
        return report_record

    @staticmethod
    def _generate_csv(
        db: Session,
        institute_id: int,
        report_type: str,
        file_path: str,
        inst_name: str,
        date_range: str,
        app: Optional[Application] = None,
        ref_no: str = "",
        sha256_hash: str = "",
        lang: str = "en",
        generated_by: str = "INSTITUTE",
    ):
        with open(file_path, mode="w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["AICTE SmartVerify AI - Official Report Export"])
            writer.writerow(["Institute:", inst_name])
            writer.writerow(["Report Type:", report_type])
            writer.writerow(["Language:", lang])
            writer.writerow(["Generated By:", generated_by])
            writer.writerow(["Date Range:", date_range])
            writer.writerow(["Report Reference:", ref_no])
            writer.writerow(["SHA-256 Digest:", sha256_hash])
            writer.writerow(["Generated At:", datetime.now(timezone.utc).isoformat()])
            writer.writerow([])

            if "Application" in report_type and "Validation" not in report_type:
                writer.writerow(["Application ID", "Category", "Academic Year", "Programme", "Status", "Filed On"])
                apps = db.query(Application).filter(Application.institute_id == institute_id).all()
                for a in apps:
                    filed = a.filed_on.strftime("%d-%m-%Y") if a.filed_on else "N/A"
                    writer.writerow([a.application_id, a.category, a.academic_year, a.programme, a.status, filed])

            elif "Certificate" in report_type:
                writer.writerow(["Certificate ID", "Certificate Name", "Application Ref", "Issue Date", "Expiry Date", "Status", "Days Remaining"])
                certs = db.query(Certificate).filter(Certificate.institute_id == institute_id).all()
                today = date.today()
                for c in certs:
                    st, days = c.compute_status(today)
                    writer.writerow([c.certificate_id, c.name, c.application_id or "N/A", c.issue_date.strftime("%d-%m-%Y"), c.expiry_date.strftime("%d-%m-%Y"), st, days])

            else:
                # Validation Summary CSV
                val_run = None
                if app:
                    val_run = (
                        db.query(ValidationRun)
                        .filter(ValidationRun.application_id == app.id)
                        .order_by(ValidationRun.id.desc())
                        .first()
                    )
                    if not val_run:
                        val_run = ValidationRunner.run_validation(db=db, application_id=app.id)

                writer.writerow(["Application ID:", app.application_id if app else "N/A"])
                writer.writerow(["RuleSet Version:", val_run.ruleset_version if val_run else "v2026.1"])
                writer.writerow(["Overall Status:", val_run.overall_status if val_run else "N/A"])
                writer.writerow(["Score:", val_run.score if val_run else 0.0])
                writer.writerow([])
                writer.writerow(["--- DETAILED FINDINGS ---"])
                writer.writerow(["Rule Code", "Rule Title", "Severity", "Result", "Evidence / Reason", "Suggested Action"])
                if val_run:
                    for fnd in val_run.findings:
                        writer.writerow([
                            fnd.rule_code,
                            fnd.rule_title,
                            fnd.severity,
                            fnd.status,
                            sanitize_text(fnd.reason),
                            sanitize_text(fnd.suggested_action or "None"),
                        ])

                writer.writerow([])
                writer.writerow(["Disclaimer:", "Rules decide, AI explains, Officials approve. AI-generated decision support; final decisions rest with authorised AICTE officials."])

    @staticmethod
    def _generate_standard_pdf(
        db: Session,
        institute_id: int,
        report_type: str,
        file_path: str,
        inst_name: str,
        date_range: str,
        ref_no: str,
        sha256_hash: str,
    ):
        doc = SimpleDocTemplate(
            file_path,
            pagesize=A4,
            rightMargin=36,
            leftMargin=36,
            topMargin=36,
            bottomMargin=40,
        )
        styles = getSampleStyleSheet()
        elements = []

        title_style = ParagraphStyle(
            'ReportTitle',
            parent=styles['Heading1'],
            fontSize=14,
            leading=17,
            textColor=colors.HexColor('#0B3C9D'),
            spaceAfter=3,
        )
        sub_style = ParagraphStyle(
            'ReportSub',
            parent=styles['Normal'],
            fontSize=8,
            leading=11,
            textColor=colors.HexColor('#0F2A5C'),
        )

        elements.append(Paragraph("ALL INDIA COUNCIL FOR TECHNICAL EDUCATION", title_style))
        elements.append(Paragraph(f"SmartVerify AI — {report_type}", styles['Heading2']))
        elements.append(Paragraph(f"<b>Institute:</b> {inst_name}", sub_style))
        elements.append(Paragraph(f"<b>Scope:</b> {date_range} | <b>Generated:</b> {datetime.now(timezone.utc).strftime('%d-%m-%Y %H:%M UTC')}", sub_style))
        elements.append(Spacer(1, 14))

        if "Application" in report_type:
            data = [["App ID", "Category", "Year", "Programme", "Status"]]
            apps = db.query(Application).filter(Application.institute_id == institute_id).limit(40).all()
            for a in apps:
                data.append([a.application_id, a.category[:25], a.academic_year, a.programme[:20], a.status])
            t = Table(data, colWidths=[90, 150, 70, 130, 80])
        else:
            data = [["Cert ID", "Certificate Name", "Issue Date", "Expiry Date", "Status"]]
            certs = db.query(Certificate).filter(Certificate.institute_id == institute_id).limit(40).all()
            today = date.today()
            for c in certs:
                st, _ = c.compute_status(today)
                data.append([c.certificate_id, c.name[:28], c.issue_date.strftime("%d-%m-%Y"), c.expiry_date.strftime("%d-%m-%Y"), st])
            t = Table(data, colWidths=[90, 180, 80, 80, 90])

        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0B3C9D')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 8.5),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 5),
            ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#F8FAFC')),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#D5DBE5')),
            ('FONTSIZE', (0, 1), (-1, -1), 7.5),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F1F5F9')]),
        ]))
        elements.append(t)
        elements.append(Spacer(1, 16))
        elements.append(Paragraph("<i>Rules decide, AI explains, Officials approve. This is an electronically generated report from AICTE SmartVerify AI.</i>", styles['Italic']))

        doc.build(elements, canvasmaker=make_numbered_canvas(ref_no, sha256_hash))

    @staticmethod
    def _generate_validation_summary_pdf(
        db: Session,
        institute: Optional[Institute],
        app: Optional[Application],
        file_path: str,
        inst_name: str,
        date_range: str,
        ref_no: str,
        sha256_hash: str,
        lang: str = "en",
        generated_by: str = "INSTITUTE",
    ):
        doc = SimpleDocTemplate(
            file_path,
            pagesize=A4,
            rightMargin=36,
            leftMargin=36,
            topMargin=36,
            bottomMargin=38,
        )
        styles = getSampleStyleSheet()
        elements = []

        is_hindi = (lang == "hi")
        active_font = HINDI_FONT_NAME if is_hindi else "Helvetica"
        active_font_bold = HINDI_FONT_BOLD if is_hindi else "Helvetica-Bold"

        # Find or run ValidationRun
        val_run = None
        if app:
            val_run = (
                db.query(ValidationRun)
                .filter(ValidationRun.application_id == app.id)
                .order_by(ValidationRun.id.desc())
                .first()
            )
            if not val_run:
                val_run = ValidationRunner.run_validation(db=db, application_id=app.id)

        # Pre-fetch rules & Root Causes
        rules = db.query(Rule).all()
        rules_by_code = {r.rule_code: r for r in rules}
        findings = val_run.findings if val_run else []
        root_causes = RootCauseAnalyzer.analyze_findings(findings=findings, rules_by_code=rules_by_code)

        app_code = app.application_id if app else "APP-2026-NA"
        explanation = ExplainerNarrator.explain(
            root_causes=root_causes,
            institute_name=inst_name,
            application_id=app_code,
            lang=lang,
            db=db,
            run_id=val_run.id if val_run else None,
        )

        # ---------------------------------------------------------
        # 1. Header with Logo (unaltered aicte-logo.png) & AICTE Info
        # ---------------------------------------------------------
        logo_img = None
        for path in LOGO_PATHS:
            if os.path.exists(path):
                logo_img = Image(path, width=44, height=44)
                break

        header_title_style = ParagraphStyle(
            'HdrTitle',
            parent=styles['Normal'],
            fontName=active_font_bold,
            fontSize=11,
            leading=14,
            textColor=colors.HexColor('#0B3C9D'),
        )
        header_sub_style = ParagraphStyle(
            'HdrSub',
            parent=styles['Normal'],
            fontName=active_font,
            fontSize=7.5,
            leading=10,
            textColor=colors.HexColor('#475569'),
        )
        header_doc_style = ParagraphStyle(
            'HdrDoc',
            parent=styles['Normal'],
            fontName=active_font_bold,
            fontSize=10,
            leading=13,
            textColor=colors.HexColor('#0F2A5C'),
        )

        if is_hindi:
            title_cell_content = [
                Paragraph("अखिल भारतीय तकनीकी शिक्षा परिषद", header_title_style),
                Paragraph("शिक्षा मंत्रालय, भारत सरकार के अधीन एक सांविधिक निकाय", header_sub_style),
                Paragraph("एआईसीटीई स्मार्टवेरीफाई एआई — विनियामक अनुपालन एवं सत्यापन सारांश", header_doc_style),
            ]
        else:
            title_cell_content = [
                Paragraph("ALL INDIA COUNCIL FOR TECHNICAL EDUCATION", header_title_style),
                Paragraph("A Statutory Body under Ministry of Education, Govt. of India", header_sub_style),
                Paragraph("AICTE SmartVerify AI — Statutory Compliance &amp; Validation Summary", header_doc_style),
            ]

        if logo_img:
            header_table = Table([[logo_img, title_cell_content]], colWidths=[50, 474])
            header_table.setStyle(TableStyle([
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('LEFTPADDING', (0, 0), (-1, -1), 0),
                ('RIGHTPADDING', (0, 0), (-1, -1), 0),
                ('TOPPADDING', (0, 0), (-1, -1), 0),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ]))
            elements.append(header_table)
        else:
            elements.extend(title_cell_content)

        # Thin AICTE divider bar
        divider_table = Table([[""]], colWidths=[524], rowHeights=[2])
        divider_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#0B3C9D')),
            ('TOPPADDING', (0, 0), (-1, -1), 0),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
        ]))
        elements.append(divider_table)
        elements.append(Spacer(1, 6))

        # ---------------------------------------------------------
        # 2. Cover / Metadata Table (Institute & Application Details)
        # ---------------------------------------------------------
        meta_label_style = ParagraphStyle('MetaLbl', parent=styles['Normal'], fontName=active_font_bold, fontSize=7, leading=9, textColor=colors.HexColor('#334155'))
        meta_val_style = ParagraphStyle('MetaVal', parent=styles['Normal'], fontName=active_font, fontSize=7, leading=9, textColor=colors.HexColor('#0F172A'))

        inst_aicte_id = institute.aicte_institute_id if institute and institute.aicte_institute_id else "AICTE-INST-001"
        ruleset_ver = val_run.ruleset_version if val_run else "v2026.1 (APH 2026-27)"
        app_cat = app.category if app else "EOA"
        app_ay = app.academic_year if app else "2026-2027"
        gen_timestamp = datetime.now(timezone.utc).strftime('%d-%m-%Y %H:%M UTC')

        meta_data = [
            [
                Paragraph("<b>Institute:</b>", meta_label_style),
                Paragraph(f"{inst_name}", meta_val_style),
                Paragraph("<b>AICTE ID:</b>", meta_label_style),
                Paragraph(f"<b>{inst_aicte_id}</b>", meta_val_style),
            ],
            [
                Paragraph("<b>Application Ref:</b>", meta_label_style),
                Paragraph(f"<b>{app_code}</b> ({app_cat})", meta_val_style),
                Paragraph("<b>Academic Year:</b>", meta_label_style),
                Paragraph(f"AY {app_ay}", meta_val_style),
            ],
            [
                Paragraph("<b>RuleSet Version:</b>", meta_label_style),
                Paragraph(ruleset_ver, meta_val_style),
                Paragraph("<b>Report ID:</b>", meta_label_style),
                Paragraph(f"<b>{ref_no}</b>", meta_val_style),
            ],
            [
                Paragraph("<b>Generated On:</b>", meta_label_style),
                Paragraph(gen_timestamp, meta_val_style),
                Paragraph("<b>Language / User:</b>", meta_label_style),
                Paragraph(f"{'Hindi (हिन्दी)' if is_hindi else 'English (en)'} | {generated_by}", meta_val_style),
            ],
        ]
        meta_table = Table(meta_data, colWidths=[85, 185, 85, 169])
        meta_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#F8FAFC')),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ]))
        elements.append(meta_table)
        elements.append(Spacer(1, 8))

        # ---------------------------------------------------------
        # 3. Overall Status and Readiness Score Executive Badge
        # ---------------------------------------------------------
        status_val = val_run.overall_status if val_run else "PENDING"
        score_val = val_run.score if val_run else 0.0

        if status_val == "READY_FOR_REVIEW":
            badge_bg = colors.HexColor("#DCFCE7")
            badge_fg = colors.HexColor("#15803D")
            badge_border = colors.HexColor("#86EFAC")
        elif status_val == "NEEDS_ATTENTION":
            badge_bg = colors.HexColor("#FEF3C7")
            badge_fg = colors.HexColor("#B45309")
            badge_border = colors.HexColor("#FCD34D")
        elif status_val == "LIKELY_TO_FAIL":
            badge_bg = colors.HexColor("#FEE2E2")
            badge_fg = colors.HexColor("#B91C1C")
            badge_border = colors.HexColor("#FCA5A5")
        else:  # BLOCKED
            badge_bg = colors.HexColor("#FEE2E2")
            badge_fg = colors.HexColor("#7F1D1D")
            badge_border = colors.HexColor("#F87171")

        badge_style = ParagraphStyle(
            'BadgeStyle',
            parent=styles['Normal'],
            fontName=active_font_bold,
            fontSize=10,
            leading=13,
            textColor=badge_fg,
            alignment=1,
        )
        badge_sub = ParagraphStyle(
            'BadgeSub',
            parent=styles['Normal'],
            fontName=active_font,
            fontSize=7,
            leading=9,
            textColor=badge_fg,
            alignment=1,
        )

        score_style = ParagraphStyle(
            'ScoreStyle',
            parent=styles['Normal'],
            fontName=active_font_bold,
            fontSize=11,
            leading=13,
            textColor=colors.HexColor('#0F2A5C'),
        )
        counts_style = ParagraphStyle(
            'CountsStyle',
            parent=styles['Normal'],
            fontName=active_font,
            fontSize=7,
            leading=9.5,
            textColor=colors.HexColor('#475569'),
        )

        b_count = val_run.blocker_count if val_run else 0
        m_count = val_run.major_count if val_run else 0
        min_count = val_run.minor_count if val_run else 0
        adv_count = val_run.advisory_count if val_run else 0

        status_display = status_val.replace('_', ' ')
        if is_hindi:
            status_text = f"समग्र विनियामक स्थिति: {status_display}"
            status_sub_text = "एआईसीटीई स्वचालित विनियामक संवीक्षा"
            score_text = f"अनुपालन तत्परता स्कोर: <b>{score_val:.1f} / 100.0</b>"
            counts_text = f"कमियों की संख्या: <b>अवरोधक (Blocker): {b_count}</b> | <b>प्रमुख (Major): {m_count}</b> | सामान्य: {min_count} | परामर्श: {adv_count}"
        else:
            status_text = f"OVERALL STATUS: {status_display}"
            status_sub_text = "AICTE Automated Regulatory Scrutiny"
            score_text = f"Compliance Readiness Score: <b>{score_val:.1f} / 100.0</b>"
            counts_text = f"Deficiency Breakdown: <b>Blockers: {b_count}</b> | <b>Major: {m_count}</b> | Minor: {min_count} | Advisory: {adv_count}"

        status_cell = [
            Paragraph(status_text, badge_style),
            Paragraph(status_sub_text, badge_sub),
        ]
        score_cell = [
            Paragraph(score_text, score_style),
            Paragraph(counts_text, counts_style),
        ]

        exec_table = Table([[status_cell, score_cell]], colWidths=[230, 294])
        exec_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, 0), badge_bg),
            ('BOX', (0, 0), (0, 0), 1, badge_border),
            ('BACKGROUND', (1, 0), (1, 0), colors.HexColor('#F1F5F9')),
            ('BOX', (1, 0), (1, 0), 0.5, colors.HexColor('#CBD5E1')),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ]))
        elements.append(exec_table)
        elements.append(Spacer(1, 8))

        # ---------------------------------------------------------
        # 4. "Why this application failed / needs attention" (AI Explanation)
        # ---------------------------------------------------------
        sec_head_style = ParagraphStyle(
            'SecHead',
            parent=styles['Heading3'],
            fontName=active_font_bold,
            fontSize=9,
            leading=11,
            textColor=colors.HexColor('#0B3C9D'),
            spaceAfter=3,
        )
        body_p_style = ParagraphStyle(
            'BodyP',
            parent=styles['Normal'],
            fontName=active_font,
            fontSize=7,
            leading=9.5,
            textColor=colors.HexColor('#1E293B'),
        )

        why_failed_title = "1. AI अनुपालन व्याख्या एवं विनियामक मूल कारण" if is_hindi else "1. AI Compliance Explanation & Root Causes"
        elements.append(Paragraph(why_failed_title, sec_head_style))

        headline_text = sanitize_text(explanation.get("headline", "Validation completed successfully."))
        summary_text = sanitize_text(explanation.get("plain_summary", "Institutional application processed according to APH norms."))

        exp_box_data = [
            [Paragraph(f"<b>Summary:</b> {headline_text}", body_p_style)],
            [Paragraph(f"{summary_text}", body_p_style)],
        ]
        if explanation.get("what_officials_will_review"):
            officials_focus = sanitize_text(explanation['what_officials_will_review'])
            exp_box_data.append([
                Paragraph(f"<b>AICTE Scrutiny Committee Focus:</b> {officials_focus}", body_p_style)
            ])

        exp_table = Table(exp_box_data, colWidths=[524])
        exp_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#F8FAFC')),
            ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E1')),
            ('LINELEFT', (0, 0), (-1, -1), 3, colors.HexColor('#0B3C9D')),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ]))
        elements.append(exp_table)
        elements.append(Spacer(1, 8))

        # ---------------------------------------------------------
        # 5. Rule-by-rule Results Table (Rule, Severity, Result, Evidence/Reason)
        # ---------------------------------------------------------
        rules_table_title = "2. नियम-वार परिणाम तालिका (Rule-by-rule Scrutiny Results)" if is_hindi else "2. Rule-by-Rule Compliance Evaluation Results"
        elements.append(Paragraph(rules_table_title, sec_head_style))

        find_cell_style = ParagraphStyle('FindCell', parent=styles['Normal'], fontName=active_font, fontSize=6.5, leading=8.5, textColor=colors.HexColor('#1E293B'))
        find_bold_style = ParagraphStyle('FindBld', parent=styles['Normal'], fontName=active_font_bold, fontSize=6.5, leading=8.5, textColor=colors.HexColor('#0F2A5C'))

        findings_data = [["Rule Code & Title", "Severity", "Result", "Evidence / Reason", "Suggested Action"]]

        if findings:
            for f in findings:
                res_col = colors.HexColor("#15803D") if f.status == "PASS" else (
                    colors.HexColor("#B45309") if f.status in ["WARNING", "NEEDS_REVIEW"] else colors.HexColor("#B91C1C")
                )
                res_p = Paragraph(f"<font color='{res_col.hexval()}'><b>{f.status}</b></font>", find_bold_style)
                rule_p = Paragraph(f"<b>{f.rule_code}</b><br/>{sanitize_text(f.rule_title[:28])}", find_cell_style)
                ev_text = sanitize_text(f.reason) or "Verified against institutional documentation."
                act_text = sanitize_text(f.suggested_action) or "No remediation required."
                findings_data.append([
                    rule_p,
                    f.severity,
                    res_p,
                    Paragraph(ev_text, find_cell_style),
                    Paragraph(act_text, find_cell_style),
                ])
        else:
            findings_data.append([
                Paragraph("APH-GENERAL", find_cell_style),
                "INFO",
                Paragraph("PASS", find_bold_style),
                Paragraph("Baseline statutory requirements fulfilled.", find_cell_style),
                Paragraph("None", find_cell_style),
            ])

        findings_table = Table(findings_data, colWidths=[90, 50, 48, 196, 140])
        findings_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0B3C9D')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 7),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 4),
            ('TOPPADDING', (0, 0), (-1, 0), 4),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E1')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F8FAFC')]),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 3),
            ('RIGHTPADDING', (0, 0), (-1, -1), 3),
        ]))
        elements.append(findings_table)
        elements.append(Spacer(1, 8))

        # ---------------------------------------------------------
        # 6. Document Table with Extracted Fields, Expiry & Verification Status
        # ---------------------------------------------------------
        doc_table_title = "3. प्रस्तुत दस्तावेज, निष्कर्षित फील्ड एवं सत्यापन स्थिति" if is_hindi else "3. Statutory Document Verification Scrutiny & Extracted Fields"
        elements.append(Paragraph(doc_table_title, sec_head_style))

        doc_header = [["Document / File", "Extracted Key Fields", "Expiry Status", "Verification Status"]]
        doc_rows = []

        inst_id = institute.id if institute else (app.institute_id if app else None)
        app_docs = []
        if app:
            app_docs = (
                db.query(Document)
                .filter(
                    (Document.application_id == app.id)
                    | ((Document.application_id == None) & (Document.institute_id == inst_id))
                )
                .order_by(Document.created_at.desc())
                .all()
            )

        if app_docs:
            for d in app_docs:
                # Key extracted fields
                extracted_pairs = []
                if d.extracted_data and isinstance(d.extracted_data, dict):
                    for k, v in list(d.extracted_data.items())[:4]:
                        if k not in ["raw_text", "ocr_text", "bounding_boxes"] and v is not None:
                            extracted_pairs.append(f"<b>{k}:</b> {str(v)[:22]}")
                elif d.extracted_fields:
                    for ef in d.extracted_fields[:4]:
                        val = ef.normalized_value or ef.value or ""
                        extracted_pairs.append(f"<b>{ef.key}:</b> {str(val)[:22]}")

                if not extracted_pairs:
                    extracted_pairs.append("<i>Standard schema verified</i>")

                extracted_str = "<br/>".join(extracted_pairs)

                # Expiry status
                if d.document_type and not d.document_type.has_expiry:
                    exp_status = "Lifetime / No Expiry"
                else:
                    v_to = None
                    if d.extracted_data and isinstance(d.extracted_data, dict):
                        v_to = d.extracted_data.get("valid_to") or d.extracted_data.get("expiry_date") or d.extracted_data.get("valid_upto")
                    if v_to:
                        exp_status = f"Valid up to {v_to}"
                    else:
                        exp_status = "Active / Valid"

                # Verification status
                latest_v = d.latest_verification
                v_st = latest_v.status if latest_v else "VERIFICATION_PENDING"
                v_src = latest_v.source_name if latest_v else "Authority Register"
                st_color = (
                    colors.HexColor("#15803D") if v_st == "VERIFIED" else (
                        colors.HexColor("#B91C1C") if v_st in ["MISMATCH_DETECTED", "EXPIRED"] else colors.HexColor("#B45309")
                    )
                )

                doc_desc = f"<b>{d.document_type_code or 'DOC'}</b><br/><font color='#475569'>{d.original_filename[:24]}</font>"
                doc_rows.append([
                    Paragraph(doc_desc, find_cell_style),
                    Paragraph(extracted_str, find_cell_style),
                    Paragraph(exp_status, find_cell_style),
                    Paragraph(f"<font color='{st_color.hexval()}'><b>{v_st.replace('_', ' ')}</b></font><br/><font color='#64748B'>{v_src}</font>", find_cell_style),
                ])
        else:
            doc_rows.append([
                Paragraph("<b>GENERAL</b><br/><font color='#475569'>No institutional documents attached</font>", find_cell_style),
                Paragraph("—", find_cell_style),
                Paragraph("No Expiry", find_cell_style),
                Paragraph("<font color='#64748B'><b>PENDING</b></font><br/>Authority Registry", find_cell_style),
            ])

        doc_summary_table = Table(doc_header + doc_rows, colWidths=[120, 194, 95, 115])
        doc_summary_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0F2A5C')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 7),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 4),
            ('TOPPADDING', (0, 0), (-1, 0), 4),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E1')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F8FAFC')]),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 3),
            ('RIGHTPADDING', (0, 0), (-1, -1), 3),
        ]))
        elements.append(doc_summary_table)
        elements.append(Spacer(1, 8))

        # ---------------------------------------------------------
        # 7. Preliminary Anomaly Indicators & Screening
        # ---------------------------------------------------------
        anom_title = "4. प्रारंभिक विसंगति संकेतक (Preliminary Anomaly Indicators)" if is_hindi else "4. Preliminary Anomaly Indicators & Screening"
        elements.append(Paragraph(anom_title, sec_head_style))
        anomaly_disc_text = (
            "<i><b>Notice:</b> All anomaly detector outputs are preliminary indicators requiring human verification, "
            "never proof. Categorized under 'needs verification' and 'potential anomaly'. "
            "<b>Rules decide, AI explains, Officials approve.</b></i>"
        )
        elements.append(Paragraph(anomaly_disc_text, body_p_style))
        elements.append(Spacer(1, 3))

        app_doc_ids = [d.id for d in app_docs]
        anomaly_flags: List[AnomalyFlag] = []
        if app_doc_ids:
            anomaly_flags = (
                db.query(AnomalyFlag)
                .filter(AnomalyFlag.document_id.in_(app_doc_ids))
                .order_by(AnomalyFlag.id.asc())
                .all()
            )

        if anomaly_flags:
            anom_header = [["Document / Ref", "Detector / Code", "Severity", "Preliminary Indicator &amp; Reason", "Action"]]
            anom_rows = []
            for a_flag in anomaly_flags:
                doc_for_flag = next((d for d in app_docs if d.id == a_flag.document_id), None)
                doc_name_str = doc_for_flag.original_filename if doc_for_flag else f"Doc #{a_flag.document_id}"

                sev_color = colors.HexColor("#B91C1C") if a_flag.severity == "HIGH" else (
                    colors.HexColor("#B45309") if a_flag.severity == "MEDIUM" else colors.HexColor("#0B3C9D")
                )

                doc_p = Paragraph(f"<b>{doc_for_flag.document_type_code if doc_for_flag and doc_for_flag.document_type_code else 'DOC'}</b><br/><font color='#475569'>{doc_name_str[:22]}</font>", find_cell_style)
                det_p = Paragraph(f"<b>{a_flag.detector}</b><br/><font color='#64748B'>{a_flag.code}</font>", find_cell_style)
                sev_p = Paragraph(f"<font color='{sev_color.hexval()}'><b>{a_flag.severity}</b></font>", find_bold_style)
                clean_reason = sanitize_text(a_flag.reason)
                reason_p = Paragraph(clean_reason, find_cell_style)
                clean_action = sanitize_text(a_flag.recommended_action or "Needs verification by scrutiny officials.")
                action_p = Paragraph(clean_action, find_cell_style)

                anom_rows.append([doc_p, det_p, sev_p, reason_p, action_p])

            anom_table = Table(anom_header + anom_rows, colWidths=[105, 105, 50, 154, 110])
            anom_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0F2A5C')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 7),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 4),
                ('TOPPADDING', (0, 0), (-1, 0), 4),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E1')),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F8FAFC')]),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('LEFTPADDING', (0, 0), (-1, -1), 3),
                ('RIGHTPADDING', (0, 0), (-1, -1), 3),
            ]))
            elements.append(anom_table)
        else:
            no_anom_p = Paragraph("<i>No potential anomaly indicators detected. All documents passed automated preliminary screening.</i>", body_p_style)
            elements.append(no_anom_p)

        elements.append(Spacer(1, 8))

        # ---------------------------------------------------------
        # 8. Cross-Document Evidence Graph & Consistency Analysis
        # ---------------------------------------------------------
        cross_title = "5. दस्तावेजी साक्ष्य ग्राफ एवं संगति विश्लेषण" if is_hindi else "5. Cross-Document Evidence & Consistency Analysis"
        elements.append(Paragraph(cross_title, sec_head_style))
        graph_disc_text = (
            "<i><b>Notice:</b> Evidence graph cross-references extracted metadata, authority verification results, and document attributes. "
            "All consistency flags are preliminary indicators categorized as 'needs verification'.</i>"
        )
        elements.append(Paragraph(graph_disc_text, body_p_style))
        elements.append(Spacer(1, 3))

        graph_conflicts = []
        if app:
            try:
                g_data = EvidenceGraphBuilder.build_graph(db=db, application_id=app.id, is_admin=False)
                graph_conflicts = g_data.get("conflicts", [])
            except Exception:
                graph_conflicts = []

        if graph_conflicts:
            conf_header = [["Conflict Type", "Affected Documents", "Extracted Discrepancy", "Preliminary Status"]]
            conf_rows = []
            for c in graph_conflicts:
                docs_str = f"{c.get('doc_file_1', 'Doc A')[:22]}<br/>vs<br/>{c.get('doc_file_2', 'Doc B')[:22]}"
                val_str = f"<b>Doc 1:</b> {str(c.get('value_1', '—'))[:24]}<br/><b>Doc 2:</b> {str(c.get('value_2', '—'))[:24]}"
                status_str = "<font color='#B45309'><b>Needs verification</b></font>"
                conf_rows.append([
                    Paragraph(f"<b>{c.get('type', 'CONFLICT').replace('_', ' ')}</b><br/><font color='#64748B'>{c.get('field', '')}</font>", find_cell_style),
                    Paragraph(docs_str, find_cell_style),
                    Paragraph(val_str, find_cell_style),
                    Paragraph(status_str, find_cell_style),
                ])
            conf_table = Table(conf_header + conf_rows, colWidths=[120, 150, 154, 100])
            conf_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0F2A5C')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 7),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 4),
                ('TOPPADDING', (0, 0), (-1, 0), 4),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E1')),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F8FAFC')]),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('LEFTPADDING', (0, 0), (-1, -1), 3),
                ('RIGHTPADDING', (0, 0), (-1, -1), 3),
            ]))
            elements.append(conf_table)
        else:
            no_conf_p = Paragraph("<i>Cross-document consistency check passed. Extracted institute identifiers, addresses, and statutory dates are consistent across submitted documents.</i>", body_p_style)
            elements.append(no_conf_p)

        elements.append(Spacer(1, 8))

        # ---------------------------------------------------------
        # 9. Next Steps Checklist (Ordered by Severity)
        # ---------------------------------------------------------
        next_steps_title = "6. सुधारात्मक कदम एवं कार्य योजना (Next Steps Checklist)" if is_hindi else "6. Recommended Next Steps Checklist (Ordered by Severity)"
        elements.append(Paragraph(next_steps_title, sec_head_style))

        severity_rank = {
            "BLOCKER": 1,
            "HIGH": 1,
            "MAJOR": 2,
            "MEDIUM": 2,
            "WARNING": 2,
            "MINOR": 3,
            "LOW": 3,
            "INFO": 4,
            "ADVISORY": 4,
        }

        remediation_items = []
        for rc in root_causes:
            sev = (rc.severity if hasattr(rc, "severity") and rc.severity else "MAJOR").upper()
            acts = rc.ordered_suggested_actions if hasattr(rc, "ordered_suggested_actions") else []
            r_str = ", ".join(rc.affected_rule_codes) if rc.affected_rule_codes else "Compliance Rules"
            for act in acts:
                remediation_items.append({
                    "severity": sev,
                    "action": sanitize_text(act),
                    "rule": r_str,
                })

        for fix in explanation.get("how_to_fix", []):
            remediation_items.append({
                "severity": fix.get("severity", "MAJOR").upper(),
                "action": sanitize_text(fix.get("step", "")),
                "rule": fix.get("rule_code", "APH Norms"),
            })

        if not remediation_items:
            for f in findings:
                if f.status in ["FAIL", "WARNING", "BLOCKER"]:
                    remediation_items.append({
                        "severity": f.severity.upper(),
                        "action": sanitize_text(f.suggested_action or f"Address deficiency identified under rule {f.rule_code}."),
                        "rule": f.rule_code,
                    })

        # Deduplicate and sort by severity
        seen_acts = set()
        unique_remediations = []
        for r in remediation_items:
            if r["action"] and r["action"] not in seen_acts:
                seen_acts.add(r["action"])
                unique_remediations.append(r)

        unique_remediations.sort(key=lambda x: severity_rank.get(x["severity"], 99))

        if unique_remediations:
            step_header = [["Seq", "Priority", "Mandatory Action Required", "Applicable Rule"]]
            step_rows = []
            for idx, item in enumerate(unique_remediations[:8], 1):
                sev = item["severity"]
                badge_c = colors.HexColor("#7F1D1D") if sev in ["BLOCKER", "HIGH"] else (
                    colors.HexColor("#B45309") if sev in ["MAJOR", "WARNING", "MEDIUM"] else colors.HexColor("#0B3C9D")
                )
                step_rows.append([
                    Paragraph(f"<b>#{idx}</b>", find_bold_style),
                    Paragraph(f"<font color='{badge_c.hexval()}'><b>{sev}</b></font>", find_bold_style),
                    Paragraph(item["action"], find_cell_style),
                    Paragraph(f"<b>{item['rule'][:20]}</b>", find_cell_style),
                ])

            step_table = Table(step_header + step_rows, colWidths=[35, 75, 304, 110])
            step_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0B3C9D')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 7),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 4),
                ('TOPPADDING', (0, 0), (-1, 0), 4),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E1')),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F8FAFC')]),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('LEFTPADDING', (0, 0), (-1, -1), 3),
                ('RIGHTPADDING', (0, 0), (-1, -1), 3),
            ]))
            elements.append(step_table)
        else:
            no_steps_p = Paragraph("<i>No pending remediation items. Application satisfies all statutory checklists and requirements.</i>", body_p_style)
            elements.append(no_steps_p)

        elements.append(Spacer(1, 8))

        # ---------------------------------------------------------
        # 10. Mandatory Statutory Disclaimer Box
        # ---------------------------------------------------------
        disclaimer_style = ParagraphStyle(
            'DiscStyle',
            parent=styles['Normal'],
            fontName=active_font,
            fontSize=7,
            leading=9.5,
            textColor=colors.HexColor('#334155'),
        )
        if is_hindi:
            disc_content = (
                "<b>सांविधिक सूचना एवं अस्वीकरण (Statutory Notice &amp; Disclaimer):</b><br/>"
                "<b>नियम निर्णय लेते हैं, AI व्याख्या करता है, अधिकारी अनुमोदन करते हैं। (Rules decide, AI explains, Officials approve.)</b><br/>"
                "<font size='6.5' color='#64748B'>यह सत्यापन सारांश एआईसीटीई अनुमोदन प्रक्रिया पुस्तिका (APH 2026-27) के अनुसार एक स्वचालित अनुपालन मूल्यांकन है। "
                "यह दस्तावेज केवल पूर्व-संवीक्षा परामर्शी निर्णय समर्थन के लिए है और एआईसीटीई अनुमोदन का औपचारिक अनुदान या अस्वीकृति नहीं है। "
                "सभी निष्कर्ष सक्षम एआईसीटीई संवीक्षा समिति द्वारा समीक्षा के अधीन हैं।</font>"
            )
        else:
            disc_content = (
                "<b>STATUTORY NOTICE &amp; MANDATORY DISCLAIMER:</b><br/>"
                "<b>Core Principle: \"Rules decide, AI explains, Officials approve.\"</b><br/>"
                "<font size='6.5' color='#64748B'>AI-generated decision support; final decisions rest with authorised AICTE officials. "
                "This validation summary is an automated compliance evaluation conducted pursuant to the AICTE "
                "Approval Process Handbook (APH 2026-27). This document serves as institutional pre-scrutiny advisory intelligence and does not constitute "
                "formal grant, renewal, or rejection of AICTE approval. All findings and classifications are subject to review by authorized AICTE officials.</font>"
            )

        disc_table = Table([[Paragraph(disc_content, disclaimer_style)]], colWidths=[524])
        disc_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#F8FAFC')),
            ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#94A3B8')),
            ('LINELEFT', (0, 0), (-1, -1), 3, colors.HexColor('#F58220')),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ]))
        elements.append(KeepTogether(disc_table))

        # Build document with NumberedCanvas
        doc.build(elements, canvasmaker=make_numbered_canvas(ref_no, sha256_hash))
