import csv
import io
import os
import re
from datetime import datetime, timezone, date
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import desc
from reportlab.lib.pagesizes import A4
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    Image,
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.pdfgen import canvas

from backend.app.models.workflow import ApplicationWorkflow
from backend.app.models.evc import EvcRecord
from backend.app.models.undertaking import Undertaking
from backend.app.models.document_validity import DocumentValidityRecord
from backend.app.models.escalation import EscalationRecord
from backend.app.models.institute import Institute
from backend.app.models.application import Application
from backend.app.services.scheduler_service import get_effective_time

CANONICAL_REGIONS = [
    "Northern",
    "Southern",
    "Eastern",
    "Western",
    "Central",
    "South-Western",
]

def normalize_region(raw: Optional[str]) -> Optional[str]:
    """
    Normalises region names to canonical AICTE regional offices:
    Northern, Southern, Eastern, Western, Central, South-Western.
    Maps variants: South, Southern, South Region -> Southern; North, Northern -> Northern; etc.
    Returns None if raw is empty, 'ALL', or national.
    """
    if not raw:
        return None
    s = str(raw).strip().lower()
    if s in ("all", "national", "all regions", "all_regions", "none", "null", "all_scope"):
        return None
    if "south-west" in s or "south west" in s or s in ("swro", "south-western", "south western"):
        return "South-Western"
    if "south" in s or s in ("sr", "sro", "tamil nadu", "kerala", "andhra pradesh", "telangana", "puducherry"):
        return "Southern"
    if "north" in s or s in ("nr", "nro", "delhi", "punjab", "haryana", "uttar pradesh", "rajasthan", "uttarakhand", "himachal pradesh", "jammu & kashmir"):
        return "Northern"
    if "west" in s or s in ("wr", "wro", "maharashtra", "gujarat", "goa"):
        return "Western"
    if "east" in s or s in ("er", "ero", "west bengal", "odisha", "bihar", "jharkhand", "assam", "sikkim", "tripura", "manipur", "meghalaya", "mizoram", "nagaland", "arunachal pradesh"):
        return "Eastern"
    if "central" in s or s in ("cro", "madhya pradesh", "chhattisgarh"):
        return "Central"
    if s in ("karnataka",):
        return "South-Western"
    return s.title()

REPORT_TYPES = {
    "application_pendency": "Application Pendency & Stage Ageing Report",
    "evc_status": "Expert Visit Committee (EVC) Physical Inspection Report",
    "undertaking_compliance": "Statutory Undertakings Compliance & Fulfilment Register",
    "document_validity": "Monitored Document Validity & Lease Renewal Register",
    "overdue_cases": "Consolidated Overdue Cases & Statutory Escalation Log",
    "region_processing_performance": "Region-Wise Processing Performance & Throughput Audit"
}

LOGO_PATHS = [
    os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../aicte-logo.png")),
    os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../frontend/public/aicte-logo.png")),
    os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../frontend/dist/aicte-logo.png")),
]


class NumberedCanvas(canvas.Canvas):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            canvas.Canvas.showPage(self)
        canvas.Canvas.save(self)

    def draw_page_decorations(self, page_count: int):
        self.saveState()
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#64748B"))

        # Header rule
        self.setStrokeColor(colors.HexColor("#CBD5E1"))
        self.setLineWidth(0.5)
        self.line(40, 805, 555, 805)

        # Header Text
        self.drawString(40, 810, "ALL INDIA COUNCIL FOR TECHNICAL EDUCATION • CONSOLIDATED STATUTORY REPORT")

        # Footer rule
        self.line(40, 45, 555, 45)

        # Footer Text
        footer_note = "System reminders and workflow actions support the process. Decisions remain with the competent authority."
        self.drawString(40, 32, footer_note)
        self.drawRightString(555, 32, f"Page {self._pageNumber} of {page_count}")
        self.restoreState()


class ConsolidatedReportService:
    @classmethod
    def list_report_types(cls) -> List[Dict[str, str]]:
        return [{"id": k, "name": v} for k, v in REPORT_TYPES.items()]

    @classmethod
    def _get_record_region(cls, db: Session, model_name: str, item: Any) -> Optional[str]:
        """Derive normalized canonical region for any record."""
        if model_name == "workflow":
            return normalize_region(item.region)
        elif model_name == "evc":
            wf = db.query(ApplicationWorkflow).filter(ApplicationWorkflow.application_id == item.application_id).first()
            return normalize_region(wf.region) if wf else None
        elif model_name == "undertaking":
            wf = db.query(ApplicationWorkflow).filter(ApplicationWorkflow.application_id == item.application_id).first()
            return normalize_region(wf.region) if wf else None
        elif model_name == "validity":
            if item.application_id:
                wf = db.query(ApplicationWorkflow).filter(ApplicationWorkflow.application_id == item.application_id).first()
                if wf and wf.region:
                    return normalize_region(wf.region)
            if item.institute_id:
                inst = db.query(Institute).filter(Institute.id == item.institute_id).first()
                if inst and inst.state:
                    return normalize_region(inst.state)
            return None
        elif model_name == "escalation":
            cid = str(item.case_id or "")
            ctype = str(item.case_type or "").lower()
            if "app-" in cid.lower() or ctype in ("workflow", "application"):
                app = db.query(Application).filter(Application.application_id == cid).first()
                if app:
                    wf = db.query(ApplicationWorkflow).filter(ApplicationWorkflow.application_id == app.id).first()
                    if wf:
                        return normalize_region(wf.region)
                if "-s" in cid.lower(): return "Southern"
                if "-n" in cid.lower(): return "Northern"
                if "-w" in cid.lower(): return "Western"
                if "-e" in cid.lower(): return "Eastern"
                if "-c" in cid.lower(): return "Central"
            elif "ut-" in cid.lower() or ctype == "undertaking":
                m = re.search(r"\d+", cid)
                if m:
                    ut = db.query(Undertaking).filter(Undertaking.id == int(m.group(0))).first()
                    if ut:
                        wf = db.query(ApplicationWorkflow).filter(ApplicationWorkflow.application_id == ut.application_id).first()
                        if wf:
                            return normalize_region(wf.region)
            elif "doc-" in cid.lower() or ctype == "validity":
                m = re.search(r"\d+", cid)
                if m:
                    doc = db.query(DocumentValidityRecord).filter(DocumentValidityRecord.id == int(m.group(0))).first()
                    if doc:
                        return cls._get_record_region(db, "validity", doc)
            return None
        return None

    @classmethod
    def generate_csv(
        cls,
        db: Session,
        report_type: str,
        region: Optional[str] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> str:
        output = io.StringIO()
        writer = csv.writer(output)

        now = get_effective_time(db)
        canonical_region = normalize_region(region)
        region_label = canonical_region if canonical_region else "All Regions (National)"
        if start_date and end_date:
            date_label = f"{start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}"
        elif start_date:
            date_label = f"From {start_date.strftime('%Y-%m-%d')}"
        elif end_date:
            date_label = f"Up to {end_date.strftime('%Y-%m-%d')}"
        else:
            date_label = "All Dates"

        report_name = REPORT_TYPES.get(report_type, "AICTE Consolidated Statutory Report")

        # Standard CSV Metadata Header
        writer.writerow([f"# Report: {report_name}"])
        writer.writerow([f"# Regional Scope: {region_label} | Date Range: {date_label} | Generated: {now.strftime('%Y-%m-%d %H:%M UTC')}"])
        writer.writerow([])

        rows_written = 0

        if report_type == "application_pendency":
            writer.writerow(["Application ID", "Institute Name", "Region", "Category", "Template", "Current Stage", "Assigned Officer", "Stage Due Date", "SLA Status", "Status"])
            workflows = db.query(ApplicationWorkflow).order_by(desc(ApplicationWorkflow.id)).all()
            for wf in workflows:
                reg = cls._get_record_region(db, "workflow", wf)
                if canonical_region and reg != canonical_region:
                    continue
                if start_date and wf.created_at and wf.created_at.date() < start_date:
                    continue
                if end_date and wf.created_at and wf.created_at.date() > end_date:
                    continue

                due_str = wf.due_date.strftime("%Y-%m-%d") if wf.due_date else "N/A"
                sla_badge = "ON TRACK"
                if wf.due_date:
                    due = wf.due_date.replace(tzinfo=timezone.utc) if wf.due_date.tzinfo is None else wf.due_date
                    diff = (due - now).total_seconds()
                    if diff < 0:
                        sla_badge = "OVERDUE"
                    elif diff <= 7 * 86400:
                        sla_badge = "DUE SOON"

                app_code = wf.application.application_id if wf.application else str(wf.application_id)
                inst_n = wf.application.institute.name if (wf.application and wf.application.institute) else "N/A"
                cat = wf.application.category if wf.application else "N/A"
                tmpl_c = wf.template.code if wf.template else "N/A"

                writer.writerow([
                    app_code,
                    inst_n,
                    reg or "N/A",
                    cat,
                    tmpl_c,
                    wf.current_stage_name,
                    wf.assigned_officer.email if wf.assigned_officer else "Unassigned",
                    due_str,
                    sla_badge,
                    wf.status
                ])
                rows_written += 1

        elif report_type == "evc_status":
            writer.writerow(["Case ID", "Institute Name", "Region", "Proposed Date", "Confirmed Date", "Status", "Report Uploaded", "Committee Members", "Scheduling Deadline"])
            records = db.query(EvcRecord).order_by(desc(EvcRecord.id)).all()
            for evc in records:
                reg = cls._get_record_region(db, "evc", evc)
                if canonical_region and reg != canonical_region:
                    continue
                if start_date and evc.created_at and evc.created_at.date() < start_date:
                    continue
                if end_date and evc.created_at and evc.created_at.date() > end_date:
                    continue

                writer.writerow([
                    evc.case_id,
                    evc.institute_name,
                    reg or "N/A",
                    evc.proposed_date.strftime("%Y-%m-%d") if evc.proposed_date else "N/A",
                    evc.confirmed_date.strftime("%Y-%m-%d") if evc.confirmed_date else "N/A",
                    evc.status,
                    "YES" if evc.report_file_path else "NO",
                    ", ".join([m.get("name", "") for m in (evc.committee_members or [])]),
                    evc.scheduling_deadline.strftime("%Y-%m-%d") if evc.scheduling_deadline else "N/A"
                ])
                rows_written += 1

        elif report_type == "undertaking_compliance":
            writer.writerow(["Undertaking ID", "Application ID", "Institute Name", "Region", "Category", "Condition", "Due Date", "Status", "Evidence Uploaded", "Verification Reason"])
            records = db.query(Undertaking).order_by(desc(Undertaking.id)).all()
            for ut in records:
                reg = cls._get_record_region(db, "undertaking", ut)
                if canonical_region and reg != canonical_region:
                    continue
                if start_date and ut.created_at and ut.created_at.date() < start_date:
                    continue
                if end_date and ut.created_at and ut.created_at.date() > end_date:
                    continue

                writer.writerow([
                    f"UT-{ut.id}",
                    ut.application_id,
                    ut.institute.name if ut.institute else "N/A",
                    reg or "N/A",
                    ut.category,
                    ut.condition_title or ut.condition_description,
                    ut.due_date.strftime("%Y-%m-%d") if ut.due_date else "N/A",
                    ut.status,
                    "YES" if ut.evidence_file_path else "NO",
                    ut.verification_reason or "N/A"
                ])
                rows_written += 1

        elif report_type == "document_validity":
            writer.writerow(["Validity ID", "Institute Name", "Region", "Doc Type", "Expiry Date", "Days Left", "Status", "Renewal Status", "Lessor", "Lessee"])
            records = db.query(DocumentValidityRecord).order_by(desc(DocumentValidityRecord.id)).all()
            for doc in records:
                reg = cls._get_record_region(db, "validity", doc)
                if canonical_region and reg != canonical_region:
                    continue
                if start_date and doc.created_at and doc.created_at.date() < start_date:
                    continue
                if end_date and doc.created_at and doc.created_at.date() > end_date:
                    continue

                writer.writerow([
                    f"DOC-{doc.id}",
                    doc.institute.name if doc.institute else "N/A",
                    reg or "N/A",
                    doc.document_type_code,
                    doc.expiry_date.strftime("%Y-%m-%d") if doc.expiry_date else "N/A",
                    doc.days_left,
                    doc.status,
                    doc.renewal_status or "N/A",
                    doc.lease_lessor or "N/A",
                    doc.lease_lessee or "N/A"
                ])
                rows_written += 1

        elif report_type == "overdue_cases":
            writer.writerow(["Case ID", "Case Type", "Region", "Event Type", "Escalation Level", "Notified Role", "Days Overdue", "Status", "Logged At"])
            records = db.query(EscalationRecord).order_by(desc(EscalationRecord.id)).all()
            for esc in records:
                reg = cls._get_record_region(db, "escalation", esc)
                if canonical_region and reg != canonical_region:
                    continue
                if start_date and esc.created_at and esc.created_at.date() < start_date:
                    continue
                if end_date and esc.created_at and esc.created_at.date() > end_date:
                    continue

                writer.writerow([
                    esc.case_id,
                    esc.case_type,
                    reg or "N/A",
                    esc.event_type,
                    esc.level,
                    esc.notified_role,
                    esc.days_overdue,
                    esc.status,
                    esc.created_at.strftime("%Y-%m-%d %H:%M UTC") if esc.created_at else "N/A"
                ])
                rows_written += 1

        elif report_type == "region_processing_performance":
            writer.writerow(["Region Jurisdiction", "Total Applications", "In Progress", "Completed", "Overdue Stages", "EVC Pending", "Undertakings Active", "Compliance Rate"])
            target_regions = [canonical_region] if canonical_region else CANONICAL_REGIONS

            all_wfs = db.query(ApplicationWorkflow).all()
            all_evcs = db.query(EvcRecord).all()
            all_uts = db.query(Undertaking).all()

            for r_name in target_regions:
                # Group by canonical region
                wfs_in_reg = [w for w in all_wfs if normalize_region(w.region) == r_name]
                if start_date:
                    wfs_in_reg = [w for w in wfs_in_reg if w.created_at and w.created_at.date() >= start_date]
                if end_date:
                    wfs_in_reg = [w for w in wfs_in_reg if w.created_at and w.created_at.date() <= end_date]

                tot = len(wfs_in_reg)
                inp = sum(1 for w in wfs_in_reg if w.status == "IN_PROGRESS")
                comp = sum(1 for w in wfs_in_reg if w.status == "COMPLETED")

                # Overdue stages
                overdue = 0
                for w in wfs_in_reg:
                    if w.due_date:
                        due = w.due_date.replace(tzinfo=timezone.utc) if w.due_date.tzinfo is None else w.due_date
                        if (due - now).total_seconds() < 0:
                            overdue += 1

                # EVC pending in region
                evc_pending = sum(
                    1 for e in all_evcs
                    if e.status == "PENDING_SCHEDULING" and cls._get_record_region(db, "evc", e) == r_name
                )

                # Undertakings active in region
                ut_active = sum(
                    1 for u in all_uts
                    if u.status in ("ACTIVE", "SUBMITTED", "PENDING") and cls._get_record_region(db, "undertaking", u) == r_name
                )

                rate = f"{(comp / max(1, tot)) * 100:.1f}%" if tot > 0 else "N/A"
                writer.writerow([
                    f"{r_name} Regional Office",
                    tot,
                    inp,
                    comp,
                    overdue,
                    evc_pending,
                    ut_active,
                    rate
                ])
                rows_written += 1

        if rows_written == 0:
            writer.writerow(["No records for the selected filters"])

        return output.getvalue()

    @classmethod
    def generate_pdf(
        cls,
        db: Session,
        report_type: str,
        region: Optional[str] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> bytes:
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            leftMargin=36,
            rightMargin=36,
            topMargin=46,
            bottomMargin=46
        )

        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            "ReportTitle",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=15,
            leading=18,
            textColor=colors.HexColor("#0F2A5C"),
        )
        subtitle_style = ParagraphStyle(
            "ReportSubtitle",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=8,
            leading=11,
            textColor=colors.HexColor("#334155"),
        )
        cell_style = ParagraphStyle(
            "ReportCell",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=8,
            leading=10,
            textColor=colors.HexColor("#1E293B"),
        )
        header_cell_style = ParagraphStyle(
            "ReportHeaderCell",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=8,
            leading=10,
            textColor=colors.white,
        )

        story = []

        # Logo and Header
        logo_path = None
        for p in LOGO_PATHS:
            if os.path.exists(p):
                logo_path = p
                break

        now = get_effective_time(db)
        canonical_region = normalize_region(region)
        region_label = canonical_region if canonical_region else "All Regions (National)"
        if start_date and end_date:
            date_label = f"{start_date.strftime('%d-%b-%Y')} to {end_date.strftime('%d-%b-%Y')}"
        elif start_date:
            date_label = f"From {start_date.strftime('%d-%b-%Y')}"
        elif end_date:
            date_label = f"Up to {end_date.strftime('%d-%b-%Y')}"
        else:
            date_label = "All Dates"

        report_name = REPORT_TYPES.get(report_type, "AICTE Consolidated Statutory Report")

        header_data = []
        if logo_path:
            logo_img = Image(logo_path, width=48, height=48)
            header_data.append([
                logo_img,
                Paragraph(
                    f"<b>ALL INDIA COUNCIL FOR TECHNICAL EDUCATION</b><br/>"
                    f"<font size=8 color='#F58220'><b>अखिल भारतीय तकनीकी शिक्षा परिषद</b></font><br/>"
                    f"<font size=11 color='#0F2A5C'><b>{report_name.upper()}</b></font>",
                    title_style
                )
            ])
            header_table = Table(header_data, colWidths=[55, 465])
            header_table.setStyle(TableStyle([
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ]))
            story.append(header_table)
        else:
            story.append(Paragraph(report_name, title_style))

        story.append(Spacer(1, 10))

        # Metadata pill box with Jurisdiction and Date Range
        meta_text = (
            f"<b>Generated At:</b> {now.strftime('%d-%b-%Y %H:%M UTC')} &nbsp;&nbsp;|&nbsp;&nbsp; "
            f"<b>Scope / Jurisdiction:</b> {region_label} &nbsp;&nbsp;|&nbsp;&nbsp; "
            f"<b>Date Range:</b> {date_label} &nbsp;&nbsp;|&nbsp;&nbsp; "
            f"<b>Regulatory Authority:</b> AICTE Approvals Bureau"
        )
        meta_table = Table([[Paragraph(meta_text, subtitle_style)]], colWidths=[520])
        meta_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
            ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
            ("PADDING", (0, 0), (-1, -1), 6),
        ]))
        story.append(meta_table)
        story.append(Spacer(1, 14))

        # Dynamic Content
        table_rows = []
        col_widths = []

        if report_type == "application_pendency":
            headers = ["Application ID", "Institution", "Region", "Stage", "Officer", "SLA Status"]
            table_rows.append([Paragraph(h, header_cell_style) for h in headers])
            col_widths = [85, 140, 65, 90, 80, 60]

            workflows = db.query(ApplicationWorkflow).order_by(desc(ApplicationWorkflow.id)).all()
            for wf in workflows:
                reg = cls._get_record_region(db, "workflow", wf)
                if canonical_region and reg != canonical_region:
                    continue
                if start_date and wf.created_at and wf.created_at.date() < start_date:
                    continue
                if end_date and wf.created_at and wf.created_at.date() > end_date:
                    continue

                badge = "ON TRACK"
                if wf.due_date:
                    due = wf.due_date.replace(tzinfo=timezone.utc) if wf.due_date.tzinfo is None else wf.due_date
                    diff = (due - now).total_seconds()
                    if diff < 0:
                        badge = "OVERDUE"
                    elif diff <= 7 * 86400:
                        badge = "DUE SOON"

                app_code = wf.application.application_id if wf.application else str(wf.application_id)
                inst_n = wf.application.institute.name if (wf.application and wf.application.institute) else "N/A"

                table_rows.append([
                    Paragraph(f"<b>{app_code}</b>", cell_style),
                    Paragraph(inst_n[:28], cell_style),
                    Paragraph(reg or "N/A", cell_style),
                    Paragraph(wf.current_stage_name[:20], cell_style),
                    Paragraph((wf.assigned_officer.email.split('@')[0] if wf.assigned_officer else 'Unassigned')[:14], cell_style),
                    Paragraph(f"<b>{badge}</b>", cell_style),
                ])

        elif report_type == "evc_status":
            headers = ["Case ID", "Institution", "Region", "Status", "Proposed Date", "Confirmed Date", "Report"]
            table_rows.append([Paragraph(h, header_cell_style) for h in headers])
            col_widths = [80, 130, 65, 75, 60, 60, 50]

            records = db.query(EvcRecord).order_by(desc(EvcRecord.id)).all()
            for evc in records:
                reg = cls._get_record_region(db, "evc", evc)
                if canonical_region and reg != canonical_region:
                    continue
                if start_date and evc.created_at and evc.created_at.date() < start_date:
                    continue
                if end_date and evc.created_at and evc.created_at.date() > end_date:
                    continue

                table_rows.append([
                    Paragraph(f"<b>{evc.case_id}</b>", cell_style),
                    Paragraph(evc.institute_name[:25], cell_style),
                    Paragraph(reg or "N/A", cell_style),
                    Paragraph(evc.status, cell_style),
                    Paragraph(evc.proposed_date.strftime("%d-%b-%Y") if evc.proposed_date else "-", cell_style),
                    Paragraph(evc.confirmed_date.strftime("%d-%b-%Y") if evc.confirmed_date else "-", cell_style),
                    Paragraph("SUBMITTED" if evc.report_file_path else "PENDING", cell_style),
                ])

        elif report_type == "undertaking_compliance":
            headers = ["Ref ID", "Institution", "Region", "Condition Title", "Due Date", "Status"]
            table_rows.append([Paragraph(h, header_cell_style) for h in headers])
            col_widths = [75, 135, 65, 145, 55, 45]

            records = db.query(Undertaking).order_by(desc(Undertaking.id)).all()
            for ut in records:
                reg = cls._get_record_region(db, "undertaking", ut)
                if canonical_region and reg != canonical_region:
                    continue
                if start_date and ut.created_at and ut.created_at.date() < start_date:
                    continue
                if end_date and ut.created_at and ut.created_at.date() > end_date:
                    continue

                table_rows.append([
                    Paragraph(f"<b>UT-{ut.id}</b>", cell_style),
                    Paragraph((ut.institute.name if ut.institute else "N/A")[:24], cell_style),
                    Paragraph(reg or "N/A", cell_style),
                    Paragraph((ut.condition_title or ut.condition_description)[:32], cell_style),
                    Paragraph(ut.due_date.strftime("%d-%b-%Y") if ut.due_date else "-", cell_style),
                    Paragraph(f"<b>{ut.status}</b>", cell_style),
                ])

        elif report_type == "document_validity":
            headers = ["Doc ID", "Institution", "Region", "Type", "Expiry Date", "Days Left", "Status"]
            table_rows.append([Paragraph(h, header_cell_style) for h in headers])
            col_widths = [65, 145, 65, 75, 65, 50, 55]

            records = db.query(DocumentValidityRecord).order_by(desc(DocumentValidityRecord.id)).all()
            for doc_rec in records:
                reg = cls._get_record_region(db, "validity", doc_rec)
                if canonical_region and reg != canonical_region:
                    continue
                if start_date and doc_rec.created_at and doc_rec.created_at.date() < start_date:
                    continue
                if end_date and doc_rec.created_at and doc_rec.created_at.date() > end_date:
                    continue

                table_rows.append([
                    Paragraph(f"<b>DOC-{doc_rec.id}</b>", cell_style),
                    Paragraph((doc_rec.institute.name if doc_rec.institute else "N/A")[:26], cell_style),
                    Paragraph(reg or "N/A", cell_style),
                    Paragraph(doc_rec.document_type_code, cell_style),
                    Paragraph(doc_rec.expiry_date.strftime("%d-%b-%Y") if doc_rec.expiry_date else "-", cell_style),
                    Paragraph(str(doc_rec.days_left), cell_style),
                    Paragraph(f"<b>{doc_rec.status}</b>", cell_style),
                ])

        elif report_type == "overdue_cases":
            headers = ["Case ID", "Case Type", "Region", "Level", "Role Notified", "Days Overdue", "Status"]
            table_rows.append([Paragraph(h, header_cell_style) for h in headers])
            col_widths = [95, 70, 65, 50, 90, 75, 75]

            records = db.query(EscalationRecord).order_by(desc(EscalationRecord.id)).all()
            for esc in records:
                reg = cls._get_record_region(db, "escalation", esc)
                if canonical_region and reg != canonical_region:
                    continue
                if start_date and esc.created_at and esc.created_at.date() < start_date:
                    continue
                if end_date and esc.created_at and esc.created_at.date() > end_date:
                    continue

                table_rows.append([
                    Paragraph(f"<b>{esc.case_id}</b>", cell_style),
                    Paragraph(esc.case_type.upper(), cell_style),
                    Paragraph(reg or "N/A", cell_style),
                    Paragraph(f"Lvl {esc.level}", cell_style),
                    Paragraph(esc.notified_role, cell_style),
                    Paragraph(str(esc.days_overdue), cell_style),
                    Paragraph(f"<b>{esc.status}</b>", cell_style),
                ])

        else:  # region_processing_performance
            headers = ["Region Jurisdiction", "Total Apps", "In Progress", "Completed", "Overdue Stages", "Compliance Rate"]
            table_rows.append([Paragraph(h, header_cell_style) for h in headers])
            col_widths = [150, 75, 75, 75, 75, 70]

            target_regions = [canonical_region] if canonical_region else CANONICAL_REGIONS
            all_wfs = db.query(ApplicationWorkflow).all()

            for r_name in target_regions:
                wfs_in_reg = [w for w in all_wfs if normalize_region(w.region) == r_name]
                if start_date:
                    wfs_in_reg = [w for w in wfs_in_reg if w.created_at and w.created_at.date() >= start_date]
                if end_date:
                    wfs_in_reg = [w for w in wfs_in_reg if w.created_at and w.created_at.date() <= end_date]

                tot = len(wfs_in_reg)
                inp = sum(1 for w in wfs_in_reg if w.status == "IN_PROGRESS")
                comp = sum(1 for w in wfs_in_reg if w.status == "COMPLETED")
                overdue = 0
                for w in wfs_in_reg:
                    if w.due_date:
                        due = w.due_date.replace(tzinfo=timezone.utc) if w.due_date.tzinfo is None else w.due_date
                        if (due - now).total_seconds() < 0:
                            overdue += 1
                rate = f"{(comp / max(1, tot)) * 100:.1f}%" if tot > 0 else "N/A"

                table_rows.append([
                    Paragraph(f"<b>{r_name} Regional Office</b>", cell_style),
                    Paragraph(str(tot), cell_style),
                    Paragraph(str(inp), cell_style),
                    Paragraph(str(comp), cell_style),
                    Paragraph(str(overdue), cell_style),
                    Paragraph(f"<b>{rate}</b>", cell_style),
                ])

        # If no records match the filter, show a clear notification row
        if len(table_rows) == 1:
            empty_row = [Paragraph("<b>No records for the selected filters</b>", cell_style)] + [Paragraph("", cell_style) for _ in range(len(col_widths) - 1)]
            table_rows.append(empty_row)

        data_table = Table(table_rows, colWidths=col_widths, repeatRows=1)
        data_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0B3C9D")),
            ("ALIGN", (0, 0), (-1, -1), "LEFT"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8FAFC")]),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
        ]))
        story.append(data_table)

        doc.build(story, canvasmaker=NumberedCanvas)
        return buffer.getvalue()
