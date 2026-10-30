import csv
import hashlib
import io
import os
import uuid
from datetime import datetime, timezone, date
from typing import Optional, List, Dict, Any

from sqlalchemy.orm import Session
from reportlab.lib.pagesizes import letter
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
from backend.app.models.verification import VerificationResult
from backend.app.models.validation_run import ValidationRun, ValidationFinding
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
        self.setFont("Helvetica", 7.5)
        self.setFillColor(colors.HexColor("#475569"))
        page_width, _ = self._pagesize
        margin = 36

        # Thin rule line
        self.setStrokeColor(colors.HexColor("#CBD5E1"))
        self.setLineWidth(0.5)
        self.line(margin, 26, page_width - margin, 26)

        # Footer Left: Reference number & SHA-256 hash
        ref_text = f"Ref: {self.report_ref} | SHA-256: {self.sha256_hash}"
        self.drawString(margin, 16, ref_text)

        # Footer Right: Page X of Y
        page_str = f"Page {self._pageNumber} of {page_count}"
        self.drawRightString(page_width - margin, 16, page_str)
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
        date_range: str,
        application_id: Optional[str] = None,
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

        timestamp_str = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        slug = report_type.lower().replace(" ", "_")
        ext = report_format.lower()
        unique_id = uuid.uuid4().hex[:6]
        app_suffix = f"_{app.application_id}" if app and ("validation" in slug) else ""
        filename = f"{slug}{app_suffix}_{unique_id}_{timestamp_str}.{ext}"
        file_path = os.path.join(STORAGE_DIR, filename)

        ref_no = f"REP-{slug.upper()[:3]}-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{unique_id.upper()}"
        sha_seed = f"{ref_no}_{inst_name}_{app.application_id if app else 'none'}_{timestamp_str}"
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
    ):
        with open(file_path, mode="w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["AICTE SmartVerify AI - Official Report Export"])
            writer.writerow(["Institute:", inst_name])
            writer.writerow(["Report Type:", report_type])
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
                            fnd.reason,
                            fnd.suggested_action or "None",
                        ])

                writer.writerow([])
                writer.writerow(["Disclaimer:", "AI-generated decision support; final decisions rest with authorised AICTE officials"])

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
            pagesize=letter,
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
            fontSize=15,
            leading=18,
            textColor=colors.HexColor('#0B3C9D'),
            spaceAfter=3,
        )
        sub_style = ParagraphStyle(
            'ReportSub',
            parent=styles['Normal'],
            fontSize=9,
            leading=13,
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
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
            ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#F8FAFC')),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#D5DBE5')),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F1F5F9')]),
        ]))
        elements.append(t)
        elements.append(Spacer(1, 20))
        elements.append(Paragraph("<i>This is an electronically generated report from AICTE SmartVerify AI. Verified by Institute Digital Signatures.</i>", styles['Italic']))

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
    ):
        doc = SimpleDocTemplate(
            file_path,
            pagesize=letter,
            rightMargin=36,
            leftMargin=36,
            topMargin=36,
            bottomMargin=42,
        )
        styles = getSampleStyleSheet()
        elements = []

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
            lang="en",
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
            fontSize=12,
            leading=15,
            textColor=colors.HexColor('#0B3C9D'),
            fontName='Helvetica-Bold',
        )
        header_sub_style = ParagraphStyle(
            'HdrSub',
            parent=styles['Normal'],
            fontSize=7.5,
            leading=10.5,
            textColor=colors.HexColor('#475569'),
        )
        header_doc_style = ParagraphStyle(
            'HdrDoc',
            parent=styles['Normal'],
            fontSize=10.5,
            leading=13,
            textColor=colors.HexColor('#0F2A5C'),
            fontName='Helvetica-Bold',
        )

        title_cell_content = [
            Paragraph("ALL INDIA COUNCIL FOR TECHNICAL EDUCATION", header_title_style),
            Paragraph("A Statutory Body under Ministry of Education, Govt. of India", header_sub_style),
            Paragraph("AICTE SmartVerify AI — Statutory Compliance &amp; Validation Summary", header_doc_style),
        ]

        if logo_img:
            header_table = Table([[logo_img, title_cell_content]], colWidths=[52, 488])
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

        # Divider bar
        divider_table = Table([[""]], colWidths=[540], rowHeights=[2])
        divider_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#0B3C9D')),
            ('TOPPADDING', (0, 0), (-1, -1), 0),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
        ]))
        elements.append(divider_table)
        elements.append(Spacer(1, 8))

        # ---------------------------------------------------------
        # 2. Metadata Table (Institute & Application Details)
        # ---------------------------------------------------------
        meta_label_style = ParagraphStyle('MetaLbl', parent=styles['Normal'], fontSize=7.5, leading=9.5, fontName='Helvetica-Bold', textColor=colors.HexColor('#334155'))
        meta_val_style = ParagraphStyle('MetaVal', parent=styles['Normal'], fontSize=7.5, leading=9.5, textColor=colors.HexColor('#0F172A'))

        inst_code = institute.code if institute and hasattr(institute, 'code') and institute.code else "SKCET01"
        ruleset_ver = val_run.ruleset_version if val_run else "v2026.1 (APH 2026-27)"
        app_cat = app.category if app else "EOA"
        app_ay = app.academic_year if app else "2026-2027"

        meta_data = [
            [
                Paragraph("<b>Institute:</b>", meta_label_style),
                Paragraph(f"{inst_name} ({inst_code})", meta_val_style),
                Paragraph("<b>Application ID:</b>", meta_label_style),
                Paragraph(f"<b>{app_code}</b>", meta_val_style),
            ],
            [
                Paragraph("<b>Category / AY:</b>", meta_label_style),
                Paragraph(f"{app_cat} | AY {app_ay}", meta_val_style),
                Paragraph("<b>RuleSet Version:</b>", meta_label_style),
                Paragraph(ruleset_ver, meta_val_style),
            ],
            [
                Paragraph("<b>Report Scope:</b>", meta_label_style),
                Paragraph(date_range, meta_val_style),
                Paragraph("<b>Generated On:</b>", meta_label_style),
                Paragraph(f"{datetime.now(timezone.utc).strftime('%d-%m-%Y %H:%M UTC')}", meta_val_style),
            ],
        ]
        meta_table = Table(meta_data, colWidths=[80, 190, 95, 175])
        meta_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#F8FAFC')),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ]))
        elements.append(meta_table)
        elements.append(Spacer(1, 10))

        # ---------------------------------------------------------
        # 3. Overall Status and Score Executive Badge
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
            fontSize=11,
            leading=14,
            fontName='Helvetica-Bold',
            textColor=badge_fg,
            alignment=1,  # Center
        )
        badge_sub = ParagraphStyle(
            'BadgeSub',
            parent=styles['Normal'],
            fontSize=7.5,
            leading=10,
            textColor=badge_fg,
            alignment=1,
        )

        score_style = ParagraphStyle(
            'ScoreStyle',
            parent=styles['Normal'],
            fontSize=12,
            leading=14,
            fontName='Helvetica-Bold',
            textColor=colors.HexColor('#0F2A5C'),
        )
        counts_style = ParagraphStyle(
            'CountsStyle',
            parent=styles['Normal'],
            fontSize=7.5,
            leading=10.5,
            textColor=colors.HexColor('#475569'),
        )

        b_count = val_run.blocker_count if val_run else 0
        m_count = val_run.major_count if val_run else 0
        min_count = val_run.minor_count if val_run else 0
        adv_count = val_run.advisory_count if val_run else 0

        status_cell = [
            Paragraph(f"OVERALL OUTCOME: {status_val.replace('_', ' ')}", badge_style),
            Paragraph("AICTE Automated Regulatory Scrutiny", badge_sub),
        ]
        score_cell = [
            Paragraph(f"Compliance Score: <b>{score_val:.1f} / 100.0</b>", score_style),
            Paragraph(f"Deficiency Counts: <b>Blockers: {b_count}</b> | <b>Major: {m_count}</b> | Minor: {min_count} | Advisory: {adv_count}", counts_style),
        ]

        exec_table = Table([[status_cell, score_cell]], colWidths=[240, 300])
        exec_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, 0), badge_bg),
            ('BOX', (0, 0), (0, 0), 1, badge_border),
            ('BACKGROUND', (1, 0), (1, 0), colors.HexColor('#F1F5F9')),
            ('BOX', (1, 0), (1, 0), 0.5, colors.HexColor('#CBD5E1')),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('LEFTPADDING', (0, 0), (-1, -1), 10),
            ('RIGHTPADDING', (0, 0), (-1, -1), 10),
        ]))
        elements.append(exec_table)
        elements.append(Spacer(1, 10))

        # ---------------------------------------------------------
        # 4. AI Compliance Explanation (Narrative)
        # ---------------------------------------------------------
        sec_head_style = ParagraphStyle(
            'SecHead',
            parent=styles['Heading3'],
            fontSize=9.5,
            leading=12,
            textColor=colors.HexColor('#0B3C9D'),
            fontName='Helvetica-Bold',
            spaceAfter=4,
        )
        body_p_style = ParagraphStyle(
            'BodyP',
            parent=styles['Normal'],
            fontSize=7.5,
            leading=10.5,
            textColor=colors.HexColor('#1E293B'),
        )

        elements.append(Paragraph("1. AI Compliance Explanation &amp; Guidance", sec_head_style))
        headline_text = explanation.get("headline", "Validation completed successfully.")
        summary_text = explanation.get("plain_summary", "Institutional application processed according to APH norms.")

        exp_box_data = [
            [Paragraph(f"<b>Executive Summary:</b> {headline_text}", body_p_style)],
            [Paragraph(f"{summary_text}", body_p_style)],
        ]
        if explanation.get("what_officials_will_review"):
            exp_box_data.append([
                Paragraph(f"<b>AICTE Scrutiny Committee Focus:</b> {explanation['what_officials_will_review']}", body_p_style)
            ])

        exp_table = Table(exp_box_data, colWidths=[540])
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
        elements.append(Spacer(1, 10))

        # ---------------------------------------------------------
        # 5. Root Causes (Stage 3-ii Root Cause Analyzer)
        # ---------------------------------------------------------
        elements.append(Paragraph("2. Root Cause Analysis (Deterministic Cause Grouping)", sec_head_style))
        if root_causes:
            rc_rows = [["Cause Code", "Headline & Rules Affected", "Severity", "Official Review"]]
            for rc in root_causes:
                rules_str = ", ".join(rc.affected_rule_codes) if rc.affected_rule_codes else "None"
                detail_p = Paragraph(f"<b>{rc.headline}</b><br/><font color='#475569'>Affects {len(rc.affected_rule_codes)} rule(s): {rules_str}</font>", body_p_style)
                review_str = "Yes (Mandatory)" if rc.needs_official_review else "No"
                rc_rows.append([
                    rc.cause_code,
                    detail_p,
                    rc.severity,
                    review_str,
                ])
            rc_table = Table(rc_rows, colWidths=[110, 270, 75, 85])
            rc_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0F2A5C')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 7.5),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E1')),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F8FAFC')]),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('TOPPADDING', (0, 0), (-1, -1), 4),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
                ('LEFTPADDING', (0, 0), (-1, -1), 5),
                ('RIGHTPADDING', (0, 0), (-1, -1), 5),
            ]))
            elements.append(rc_table)
        else:
            no_rc_p = Paragraph("<i>No compliance root causes detected. All mandatory statutory criteria and documentation are satisfied.</i>", body_p_style)
            elements.append(no_rc_p)

        elements.append(Spacer(1, 10))

        # ---------------------------------------------------------
        # 6. Detailed Findings Table (Rule, Severity, Result, Evidence, Action)
        # ---------------------------------------------------------
        elements.append(Paragraph("3. Detailed Compliance Findings (Stage 3-i Rule Engine)", sec_head_style))
        find_cell_style = ParagraphStyle('FindCell', parent=styles['Normal'], fontSize=7, leading=8.5, textColor=colors.HexColor('#1E293B'))
        find_bold_style = ParagraphStyle('FindBld', parent=styles['Normal'], fontSize=7, leading=8.5, fontName='Helvetica-Bold', textColor=colors.HexColor('#0F2A5C'))

        findings_data = [["Rule", "Severity", "Result", "Evidence / Reason", "Suggested Action"]]

        if findings:
            for f in findings:
                res_col = colors.HexColor("#15803D") if f.status == "PASS" else (
                    colors.HexColor("#B45309") if f.status == "WARNING" else colors.HexColor("#B91C1C")
                )
                res_p = Paragraph(f"<font color='{res_col.hexval()}'><b>{f.status}</b></font>", find_bold_style)
                rule_p = Paragraph(f"<b>{f.rule_code}</b><br/>{f.rule_title[:24]}", find_cell_style)
                ev_text = f.reason or "Criteria verified against uploaded documentation."
                act_text = f.suggested_action or "No remediation required."
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
                Paragraph("Baseline validation passed.", find_cell_style),
                Paragraph("None", find_cell_style),
            ])

        findings_table = Table(findings_data, colWidths=[85, 55, 55, 205, 140])
        findings_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0B3C9D')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 7.5),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 4),
            ('TOPPADDING', (0, 0), (-1, 0), 4),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E1')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F8FAFC')]),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 4),
            ('RIGHTPADDING', (0, 0), (-1, -1), 4),
        ]))
        elements.append(findings_table)
        elements.append(Spacer(1, 10))

        # ---------------------------------------------------------
        # 7. Statutory Document Verification Scrutiny
        # ---------------------------------------------------------
        elements.append(Paragraph("4. Statutory Document Verification Scrutiny", sec_head_style))
        ver_header = [["Document Type / File", "Verification Status", "Issuing Authority Source", "Verified Timestamp"]]
        ver_rows = []

        # Find application documents
        app_docs = []
        inst_id = institute.id if institute else (app.institute_id if app else None)
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
            for doc_item in app_docs:
                latest_v = doc_item.latest_verification
                v_st = latest_v.status if latest_v else "VERIFICATION_PENDING"
                v_src = latest_v.source_name if latest_v else "Issuing Authority Register"
                v_time = (
                    latest_v.checked_at.strftime("%d-%m-%Y %H:%M UTC")
                    if latest_v and latest_v.checked_at
                    else "Pending"
                )

                st_color = (
                    colors.HexColor("#15803D")
                    if v_st == "VERIFIED"
                    else (
                        colors.HexColor("#B91C1C")
                        if v_st in ["MISMATCH_DETECTED", "EXPIRED"]
                        else colors.HexColor("#B45309")
                    )
                )

                doc_desc = f"<b>{doc_item.document_type_code or 'DOC'}</b><br/><font color='#475569'>{doc_item.original_filename[:32]}</font>"
                ver_rows.append([
                    Paragraph(doc_desc, find_cell_style),
                    Paragraph(f"<font color='{st_color.hexval()}'><b>{v_st.replace('_', ' ')}</b></font>", find_bold_style),
                    Paragraph(v_src, find_cell_style),
                    Paragraph(v_time, find_cell_style),
                ])
        else:
            ver_rows.append([
                Paragraph("<b>GENERAL</b><br/><font color='#475569'>No institutional documents attached</font>", find_cell_style),
                Paragraph("<font color='#64748B'><b>PENDING</b></font>", find_bold_style),
                Paragraph("Issuing Authority Registry", find_cell_style),
                Paragraph("—", find_cell_style),
            ])

        ver_table = Table(ver_header + ver_rows, colWidths=[165, 115, 150, 110])
        ver_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0F2A5C')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 7.5),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 4),
            ('TOPPADDING', (0, 0), (-1, 0), 4),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E1')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F8FAFC')]),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 4),
            ('RIGHTPADDING', (0, 0), (-1, -1), 4),
        ]))
        elements.append(ver_table)
        elements.append(Spacer(1, 10))

        # ---------------------------------------------------------
        # 8. Remediation Steps (How to Fix)
        # ---------------------------------------------------------
        how_to_fix = explanation.get("how_to_fix", [])
        if how_to_fix:
            elements.append(Paragraph("5. Recommended Remediation Steps", sec_head_style))
            fix_items = []
            for idx, fix in enumerate(how_to_fix, 1):
                effort_str = fix.get("effort", "Medium")
                step_text = fix.get("step", "")
                fix_items.append([
                    Paragraph(f"<b>Step {idx}:</b>", find_bold_style),
                    Paragraph(f"{step_text}", body_p_style),
                    Paragraph(f"<b>Effort: {effort_str}</b>", find_cell_style),
                ])
            fix_table = Table(fix_items, colWidths=[50, 410, 80])
            fix_table.setStyle(TableStyle([
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('TOPPADDING', (0, 0), (-1, -1), 2),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
                ('LEFTPADDING', (0, 0), (-1, -1), 2),
                ('RIGHTPADDING', (0, 0), (-1, -1), 2),
            ]))
            elements.append(fix_table)
            elements.append(Spacer(1, 10))

        # ---------------------------------------------------------
        # 8. Mandatory Statutory Disclaimer Box
        # ---------------------------------------------------------
        disclaimer_style = ParagraphStyle(
            'DiscStyle',
            parent=styles['Normal'],
            fontSize=7.5,
            leading=10,
            textColor=colors.HexColor('#334155'),
        )
        disc_content = (
            "<b>STATUTORY NOTICE &amp; DISCLAIMER:</b><br/>"
            "AI-generated decision support; final decisions rest with authorised AICTE officials.<br/>"
            "<font size='6.5' color='#64748B'>This validation summary is an automated compliance evaluation conducted pursuant to the AICTE "
            "Approval Process Handbook (APH 2026-27). This document serves as institutional pre-scrutiny advisory intelligence and does not constitute "
            "formal grant, renewal, or rejection of AICTE approval. All findings and classifications are subject to review by the AICTE Scrutiny Committee.</font>"
        )
        disc_table = Table([[Paragraph(disc_content, disclaimer_style)]], colWidths=[540])
        disc_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#F8FAFC')),
            ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#94A3B8')),
            ('LINELEFT', (0, 0), (-1, -1), 3, colors.HexColor('#F58220')),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ]))
        elements.append(KeepTogether(disc_table))

        # Build document with NumberedCanvas
        doc.build(elements, canvasmaker=make_numbered_canvas(ref_no, sha256_hash))
