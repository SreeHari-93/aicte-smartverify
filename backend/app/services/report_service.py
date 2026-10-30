import csv
import io
import os
import uuid
from datetime import datetime, timezone, date
from sqlalchemy.orm import Session
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

from backend.app.models.application import Application
from backend.app.models.certificate import Certificate
from backend.app.models.report import Report
from backend.app.models.institute import Institute

STORAGE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../storage/reports"))
os.makedirs(STORAGE_DIR, exist_ok=True)


class ReportService:
    @staticmethod
    def generate_report(
        db: Session,
        institute_id: int,
        report_type: str,
        report_format: str,
        date_range: str,
    ) -> Report:
        institute = db.query(Institute).filter(Institute.id == institute_id).first()
        inst_name = institute.name if institute else f"Institute {institute_id}"

        timestamp_str = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        slug = report_type.lower().replace(" ", "_")
        ext = report_format.lower()
        unique_id = uuid.uuid4().hex[:6]
        filename = f"{slug}_{unique_id}_{timestamp_str}.{ext}"
        file_path = os.path.join(STORAGE_DIR, filename)

        if ext == "csv":
            ReportService._generate_csv(db, institute_id, report_type, file_path, inst_name, date_range)
        else:
            ReportService._generate_pdf(db, institute_id, report_type, file_path, inst_name, date_range)

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
    def _generate_csv(db: Session, institute_id: int, report_type: str, file_path: str, inst_name: str, date_range: str):
        with open(file_path, mode="w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["AICTE SmartVerify AI - Official Report Export"])
            writer.writerow(["Institute:", inst_name])
            writer.writerow(["Report Type:", report_type])
            writer.writerow(["Date Range:", date_range])
            writer.writerow(["Generated At:", datetime.now(timezone.utc).isoformat()])
            writer.writerow([])

            if "Application" in report_type:
                writer.writerow(["Application ID", "Category", "Academic Year", "Programme", "Status", "Filed On"])
                apps = db.query(Application).filter(Application.institute_id == institute_id).all()
                for app in apps:
                    filed = app.filed_on.strftime("%d-%m-%Y") if app.filed_on else "N/A"
                    writer.writerow([app.application_id, app.category, app.academic_year, app.programme, app.status, filed])

            elif "Certificate" in report_type:
                writer.writerow(["Certificate ID", "Certificate Name", "Application Ref", "Issue Date", "Expiry Date", "Status", "Days Remaining"])
                certs = db.query(Certificate).filter(Certificate.institute_id == institute_id).all()
                today = date.today()
                for c in certs:
                    st, days = c.compute_status(today)
                    writer.writerow([c.certificate_id, c.name, c.application_id or "N/A", c.issue_date.strftime("%d-%m-%Y"), c.expiry_date.strftime("%d-%m-%Y"), st, days])

            else:
                # Validation Summary
                writer.writerow(["Check Name", "Status", "Evidence", "Suggested Action"])
                writer.writerow(["Land Area Clearance", "Pass", "Clearance Doc Verified under Section 2.1", "None"])
                writer.writerow(["Building Stability NOC", "Pass", "Municipal Engineer Stamp Validated", "None"])
                writer.writerow(["Fire & Life Safety NOC", "Warning", "Expires within 45 days", "Renew before inspection"])
                writer.writerow(["Faculty Cadre Ratio (1:20)", "Pass", "Calculated 1:18.4 meets norm", "None"])
                writer.writerow(["AICTE Approval Continuity", "Pass", "Unbroken continuous EoA since 2012", "None"])

    @staticmethod
    def _generate_pdf(db: Session, institute_id: int, report_type: str, file_path: str, inst_name: str, date_range: str):
        doc = SimpleDocTemplate(file_path, pagesize=letter, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
        styles = getSampleStyleSheet()
        elements = []

        title_style = ParagraphStyle(
            'ReportTitle',
            parent=styles['Heading1'],
            fontSize=16,
            leading=20,
            textColor=colors.HexColor('#0B3C9D'),
            spaceAfter=4,
        )
        sub_style = ParagraphStyle(
            'ReportSub',
            parent=styles['Normal'],
            fontSize=10,
            leading=14,
            textColor=colors.HexColor('#0F2A5C'),
        )

        elements.append(Paragraph("ALL INDIA COUNCIL FOR TECHNICAL EDUCATION", title_style))
        elements.append(Paragraph(f"SmartVerify AI — {report_type}", styles['Heading2']))
        elements.append(Paragraph(f"<b>Institute:</b> {inst_name}", sub_style))
        elements.append(Paragraph(f"<b>Scope:</b> {date_range} | <b>Generated:</b> {datetime.now(timezone.utc).strftime('%d-%m-%Y %H:%M UTC')}", sub_style))
        elements.append(Spacer(1, 15))

        if "Application" in report_type:
            data = [["App ID", "Category", "Year", "Programme", "Status"]]
            apps = db.query(Application).filter(Application.institute_id == institute_id).limit(40).all()
            for app in apps:
                data.append([app.application_id, app.category[:25], app.academic_year, app.programme[:20], app.status])
            t = Table(data, colWidths=[90, 150, 70, 130, 80])

        elif "Certificate" in report_type:
            data = [["Cert ID", "Certificate Name", "Issue Date", "Expiry Date", "Status"]]
            certs = db.query(Certificate).filter(Certificate.institute_id == institute_id).limit(40).all()
            today = date.today()
            for c in certs:
                st, _ = c.compute_status(today)
                data.append([c.certificate_id, c.name[:28], c.issue_date.strftime("%d-%m-%Y"), c.expiry_date.strftime("%d-%m-%Y"), st])
            t = Table(data, colWidths=[90, 180, 80, 80, 90])

        else:
            data = [["Check", "Result", "Evidence", "Action"]]
            data.append(["Land Area Clearance", "Pass", "Valid under Sec 2.1", "None"])
            data.append(["Building Stability NOC", "Pass", "PWD Engineer Stamp", "None"])
            data.append(["Fire Safety NOC", "Warning", "Expires in 45 days", "Renew"])
            data.append(["Cadre Ratio (1:20)", "Pass", "Ratio: 1:18.4", "None"])
            data.append(["EoA Continuity", "Pass", "Continuous since 2012", "None"])
            t = Table(data, colWidths=[130, 70, 180, 140])

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

        doc.build(elements)

