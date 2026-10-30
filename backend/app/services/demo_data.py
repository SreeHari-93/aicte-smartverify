import os
import hashlib
import json
from datetime import date, datetime, timedelta, timezone
from typing import Dict, Any, List

from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.graphics.shapes import Drawing
from reportlab.graphics.barcode.qr import QrCodeWidget
from sqlalchemy.orm import Session

from backend.app.models.institute import Institute
from backend.app.models.application import Application
from backend.app.models.document import Document
from backend.app.models.document_page import DocumentPage
from backend.app.models.document_classification import DocumentClassification
from backend.app.models.extracted_field import ExtractedField
from backend.app.models.validation_run import ValidationRun, ValidationFinding
from backend.app.services.validation.runner import ValidationRunner

DEMO_DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../demo_data"))
os.makedirs(DEMO_DATA_DIR, exist_ok=True)


def create_synthetic_pdf(
    filename: str,
    title: str,
    doc_type_code: str,
    fields: Dict[str, Any],
) -> str:
    """
    Generates a small synthetic PDF certificate into backend/demo_data/
    using ReportLab. Uses fake data only.
    """
    file_path = os.path.join(DEMO_DATA_DIR, filename)
    doc = SimpleDocTemplate(
        file_path,
        pagesize=letter,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36,
    )
    styles = getSampleStyleSheet()
    elements = []

    title_style = ParagraphStyle(
        "CertTitle",
        parent=styles["Heading1"],
        fontSize=14,
        leading=18,
        textColor=colors.HexColor("#0B3C9D"),
        spaceAfter=8,
    )
    meta_style = ParagraphStyle(
        "CertMeta",
        parent=styles["Normal"],
        fontSize=9,
        leading=12,
        textColor=colors.HexColor("#475569"),
    )

    elements.append(Paragraph("AICTE REGULATORY STATUTORY REPOSITORY (SYNTHETIC DEMO)", meta_style))
    elements.append(Paragraph(f"Official Document: {title}", title_style))
    elements.append(Paragraph(f"Document Type Code: <b>{doc_type_code}</b> | Classification: Verified", meta_style))
    elements.append(Spacer(1, 12))

    data = [["Attribute", "Extracted Certified Value"]]
    for k, v in fields.items():
        data.append([str(k).replace("_", " ").title(), str(v)])

    t = Table(data, colWidths=[180, 340])
    t.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0B3C9D")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 9),
            ("BOTTOMPADDING", (0, 0), (-1, 0), 5),
            ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#F8FAFC")),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
            ("FONTSIZE", (0, 1), (-1, -1), 8),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F1F5F9")]),
        ])
    )
    elements.append(t)
    elements.append(Spacer(1, 12))

    # Embed machine-readable QR code on certificate
    qr_payload_dict = {
        "certificate_number": (
            fields.get("certificate_number")
            or fields.get("noc_number")
            or fields.get("approval_number")
            or fields.get("accreditation_id")
            or fields.get("certificate_id")
            or fields.get("deed_number")
            or f"QR-{doc_type_code}"
        ),
        "institute_name": fields.get("institute_name", "Sri Krishna College of Engineering and Technology"),
        "doc_type": doc_type_code,
        "issue_date": str(fields.get("issue_date") or ""),
        "expiry_date": str(fields.get("expiry_date") or ""),
    }
    qr_json = json.dumps(qr_payload_dict)
    qr_widget = QrCodeWidget(qr_json)
    bounds = qr_widget.getBounds()
    qw = max(1.0, bounds[2] - bounds[0])
    qh = max(1.0, bounds[3] - bounds[1])
    qr_drawing = Drawing(80, 80, transform=[80 / qw, 0, 0, 80 / qh, 0, 0])
    qr_drawing.add(qr_widget)

    elements.append(Paragraph("<b>Statutory Verification QR Code (Machine Readable):</b>", meta_style))
    elements.append(Spacer(1, 4))
    elements.append(qr_drawing)
    elements.append(Spacer(1, 10))

    elements.append(
        Paragraph(
            "<i>Security Disclaimer: Synthetic test certificate generated for AICTE SmartVerify AI Stage 3 demonstration. Not for statutory governance.</i>",
            meta_style,
        )
    )

    doc.build(elements)
    return file_path


class DemoDataSeeder:
    """
    Idempotent synthetic demo data seeder for Sri Krishna College of Eng & Tech (SKCET).
    Creates 4 clearly defined applications covering:
    - DEMO-READY: outcome READY_FOR_REVIEW
    - DEMO-ATTENTION: outcome NEEDS_ATTENTION
    - DEMO-LIKELY-FAIL: outcome LIKELY_TO_FAIL
    - DEMO-BLOCKED: outcome BLOCKED
    """

    @classmethod
    def seed_all_demo_applications(cls, db: Session) -> Dict[str, Application]:
        # 0. Ensure Published Rules, RuleSet, AuthoritySources, and MockRegisters exist
        from backend.app.services.demo_rules import seed_published_rules_if_needed
        seed_published_rules_if_needed(db)
        cls.seed_authority_sources_and_mock_registers(db)

        # 1. Resolve or create SKCET institute
        skcet = db.query(Institute).filter(Institute.aicte_institute_id == "SKCET01").first()
        if not skcet:
            skcet = Institute(
                aicte_institute_id="SKCET01",
                name="Sri Krishna College of Engineering and Technology",
                state="Tamil Nadu",
                status="ACTIVE",
            )
            db.add(skcet)
            db.commit()
            db.refresh(skcet)

        # Ensure Courses & Accreditation exist for SKCET
        from backend.app.models.course import Course
        from backend.app.models.accreditation import Accreditation

        if db.query(Course).filter(Course.institute_id == skcet.id).count() == 0:
            courses_list = [
                ("B.E - Computer Science & Engineering", "UG", 180),
                ("B.Tech - Information Technology", "UG", 120),
                ("B.E - Mechanical Engineering", "UG", 120),
                ("B.E - Electronics & Communication Engineering", "UG", 180),
            ]
            for c_name, level, intake in courses_list:
                db.add(Course(institute_id=skcet.id, name=c_name, level=level, intake=intake))
            db.commit()

        if db.query(Accreditation).filter(Accreditation.institute_id == skcet.id).count() == 0:
            db.add(
                Accreditation(
                    institute_id=skcet.id,
                    nirf_rank=73,
                    naac_grade="A++ (CGPA 3.62)",
                    nba_accredited_courses=9,
                    college_code="SKCET01",
                    location_address="Sugunapuram, Kuniamuthur, Coimbatore, Tamil Nadu - 641008",
                    phone="+91 422 2678001",
                )
            )
            db.commit()

        today = date.today()
        valid_exp = (today + timedelta(days=365)).isoformat()
        exp_soon = (today + timedelta(days=20)).isoformat()  # within 30 days
        past_exp = (today - timedelta(days=45)).isoformat()   # expired 45 days ago
        issue_valid = (today - timedelta(days=60)).isoformat()

        def make_docs_for_app(app_id: str, custom_overrides: Dict[str, Dict[str, Any]], omit_types: List[str] = None):
            omit_types = omit_types or []
            base_specs = [
                ("FIRE_NOC", "Fire & Life Safety Certificate", {"certificate_number": f"FSNOC-{app_id}", "expiry_date": valid_exp, "institute_name": skcet.name, "issue_date": issue_valid}),
                ("BUILDING_PLAN", "Approved Building Plan", {"approval_number": f"BPA-{app_id}", "total_built_up_area": 42500, "instructional_area": 42500, "institute_name": skcet.name, "issue_date": (today - timedelta(days=200)).isoformat()}),
                ("OCCUPANCY_CERT", "Occupancy Certificate", {"certificate_id": f"OCC-{app_id}", "institute_name": skcet.name, "issue_date": (today - timedelta(days=150)).isoformat()}),
                ("LAND_DOC", "Land Title Deed", {"deed_number": f"LND-{app_id}", "land_area_acres": 22.5, "institute_name": skcet.name}),
                ("AFFIDAVIT", "AICTE Comprehensive Statutory Affidavit", {"deponent_name": "Dr. K. Sundararajan", "institute_name": skcet.name, "expiry_date": valid_exp, "issue_date": issue_valid}),
                ("NBA_CERT", "NBA Programme Accreditation Certificate", {"accreditation_id": f"NBA-{app_id}", "expiry_date": valid_exp, "institute_name": skcet.name}),
                ("BARRIER_FREE", "Barrier-Free Access Audit Certificate", {"audit_id": f"BFA-{app_id}", "expiry_date": valid_exp, "institute_name": skcet.name}),
                ("AUDIT_ACCOUNTS", "Audited Financial Statements", {"ca_membership_no": "CA-88219", "institute_name": skcet.name}),
                ("EQUIP_LIST", "Laboratory Equipment Muster", {"status": "VERIFIED", "institute_name": skcet.name}),
                ("BANK_GUARANTEE", "Joint FDR Bank Guarantee", {"guarantee_no": f"FDR-{app_id}", "expiry_date": valid_exp, "institute_name": skcet.name}),
                ("CYBER_AUDIT", "Campus Cyber Security Audit", {"cert_id": f"CYB-{app_id}", "expiry_date": valid_exp, "institute_name": skcet.name}),
                ("NAAC_CERT", "NAAC Institutional Accreditation", {"grade": "A++", "expiry_date": valid_exp, "institute_name": skcet.name}),
            ]

            doc_specs = []
            for doc_type_code, title, fields in base_specs:
                if doc_type_code in omit_types:
                    continue
                # Apply custom overrides
                if doc_type_code in custom_overrides:
                    fields = {**fields, **custom_overrides[doc_type_code]}
                # Include app_id in fields to guarantee distinct SHA-256 hash per app
                fields["demo_app_ref"] = app_id
                pdf_path = create_synthetic_pdf(
                    f"{app_id}_{doc_type_code.lower()}.pdf",
                    f"{title} ({app_id})",
                    doc_type_code,
                    fields,
                )
                doc_specs.append((doc_type_code, title, pdf_path, fields))
            return doc_specs

        seeded_apps = {}

        # ----------------------------------------------------------------------
        # 1. DEMO-READY: outcome READY_FOR_REVIEW
        # All mandatory documents present and valid
        # ----------------------------------------------------------------------
        app_ready = cls._upsert_application(
            db=db,
            institute_id=skcet.id,
            app_id="DEMO-READY",
            category="EOA",
            academic_year="2026-27",
            status="SUBMITTED",
        )
        cls._attach_documents(
            db=db,
            app=app_ready,
            doc_specs=make_docs_for_app("DEMO-READY", {}),
        )
        seeded_apps["DEMO-READY"] = app_ready

        # ----------------------------------------------------------------------
        # 2. DEMO-ATTENTION: outcome NEEDS_ATTENTION
        # One certificate expiring within 30 days
        # ----------------------------------------------------------------------
        app_attention = cls._upsert_application(
            db=db,
            institute_id=skcet.id,
            app_id="DEMO-ATTENTION",
            category="EOA",
            academic_year="2026-27",
            status="SUBMITTED",
        )
        cls._attach_documents(
            db=db,
            app=app_attention,
            doc_specs=make_docs_for_app(
                "DEMO-ATTENTION",
                # Occupancy Certificate expires in 20 days (< 30 days) -> triggers WARNING DOC_EXP_SOON
                {"OCCUPANCY_CERT": {"expiry_date": exp_soon, "status": "EXPIRING_SOON"}},
            ),
        )
        seeded_apps["DEMO-ATTENTION"] = app_attention

        # ----------------------------------------------------------------------
        # 3. DEMO-LIKELY-FAIL: outcome LIKELY_TO_FAIL
        # NBA certificate expired AND affidavit institute name mismatch
        # ----------------------------------------------------------------------
        app_likely_fail = cls._upsert_application(
            db=db,
            institute_id=skcet.id,
            app_id="DEMO-LIKELY-FAIL",
            category="EOA",
            academic_year="2026-27",
            status="SUBMITTED",
        )
        cls._attach_documents(
            db=db,
            app=app_likely_fail,
            doc_specs=make_docs_for_app(
                "DEMO-LIKELY-FAIL",
                {
                    # 1. NBA certificate expired -> MAJOR FAIL
                    "NBA_CERT": {"expiry_date": past_exp},
                    # 2. Affidavit institute name differs from official record -> MAJOR FAIL
                    "AFFIDAVIT": {"institute_name": "Sri Krishna Institute of Advanced Technology"},
                },
            ),
        )
        seeded_apps["DEMO-LIKELY-FAIL"] = app_likely_fail

        # ----------------------------------------------------------------------
        # 4. DEMO-BLOCKED: outcome BLOCKED
        # Mandatory Fire NOC missing
        # ----------------------------------------------------------------------
        app_blocked = cls._upsert_application(
            db=db,
            institute_id=skcet.id,
            app_id="DEMO-BLOCKED",
            category="EOA",
            academic_year="2026-27",
            status="SUBMITTED",
        )
        cls._attach_documents(
            db=db,
            app=app_blocked,
            doc_specs=make_docs_for_app(
                "DEMO-BLOCKED",
                {},
                omit_types=["FIRE_NOC"],  # Missing mandatory Fire NOC!
            ),
        )
        seeded_apps["DEMO-BLOCKED"] = app_blocked

        return seeded_apps

        return seeded_apps

    @classmethod
    def _upsert_application(
        cls,
        db: Session,
        institute_id: int,
        app_id: str,
        category: str,
        academic_year: str,
        status: str,
    ) -> Application:
        app = db.query(Application).filter(Application.application_id == app_id).first()
        if not app:
            app = Application(
                institute_id=institute_id,
                application_id=app_id,
                category=category,
                academic_year=academic_year,
                programme="Engineering",
                status=status,
                created_at=datetime.now(timezone.utc),
            )
            db.add(app)
            db.commit()
            db.refresh(app)
        else:
            app.status = status
            app.category = category
            db.commit()
            db.refresh(app)
        return app

    @classmethod
    def _attach_documents(
        cls,
        db: Session,
        app: Application,
        doc_specs: List[tuple],
    ):
        """
        Idempotently attaches synthetic documents with classification & extracted fields.
        """
        # Clean existing documents for this demo application to ensure clean state
        existing_docs = db.query(Document).filter(Document.application_id == app.id).all()
        for d in existing_docs:
            db.delete(d)
        db.commit()

        for doc_type_code, title, file_path, fields in doc_specs:
            file_size = os.path.getsize(file_path) if os.path.exists(file_path) else 1024
            with open(file_path, "rb") as f:
                sha256 = hashlib.sha256(f.read()).hexdigest()

            doc_record = Document(
                institute_id=app.institute_id,
                application_id=app.id,
                document_type_code=doc_type_code,
                original_filename=os.path.basename(file_path),
                stored_filename=f"{app.application_id}_{doc_type_code}_{os.path.basename(file_path)}",
                file_path=file_path,
                file_size=file_size,
                mime_type="application/pdf",
                sha256_hash=sha256,
                status=fields.get("doc_status", "VERIFIED"),
                ocr_status="COMPLETED",
                ocr_confidence=0.98,
                extracted_data=fields,
                created_at=datetime.now(timezone.utc),
            )
            db.add(doc_record)
            db.commit()
            db.refresh(doc_record)

            # 1. Document Page
            page = DocumentPage(
                document_id=doc_record.id,
                page_no=1,
                text=f"AICTE DEMO SYNTHETIC CERTIFICATE {title}\n" + "\n".join(f"{k}: {v}" for k, v in fields.items()),
                width=612.0,
                height=792.0,
            )
            db.add(page)

            # 2. Classification
            classification = DocumentClassification(
                document_id=doc_record.id,
                predicted_type=doc_type_code,
                score=0.98,
                mismatch_flag=False,
                created_at=datetime.now(timezone.utc),
            )
            db.add(classification)

            # 3. Extracted Fields
            for k, v in fields.items():
                ef = ExtractedField(
                    document_id=doc_record.id,
                    key=str(k),
                    value=str(v),
                    normalized_value=str(v),
                    confidence=0.98,
                    page_no=1,
                    source="rule",
                    created_at=datetime.now(timezone.utc),
                )
                db.add(ef)

        db.commit()

    @classmethod
    def seed_authority_sources_and_mock_registers(cls, db: Session):
        from backend.app.models.verification import AuthoritySource, MockRegisterEntry
        today = date.today()
        valid_exp = (today + timedelta(days=365)).isoformat()
        past_exp = (today - timedelta(days=90)).isoformat()
        issue_valid = (today - timedelta(days=60)).isoformat()

        # 1. Authority Sources
        sources_catalog = [
            {"name": "NBA", "base_url": "/mock-authorities/NBA/verify", "auth_type": "API_KEY", "env_secret_key": "NBA_API_KEY"},
            {"name": "NAAC", "base_url": "/mock-authorities/NAAC/verify", "auth_type": "BEARER", "env_secret_key": "NAAC_API_KEY"},
            {"name": "FIRE_DEPT", "base_url": "/mock-authorities/FIRE_DEPT/verify", "auth_type": "NONE", "env_secret_key": "FIRE_API_KEY"},
            {"name": "POLLUTION_BOARD", "base_url": "/mock-authorities/POLLUTION_BOARD/verify", "auth_type": "API_KEY", "env_secret_key": "POLLUTION_API_KEY"},
            {"name": "MUNICIPAL_CORP", "base_url": "/mock-authorities/MUNICIPAL_CORP/verify", "auth_type": "NONE", "env_secret_key": "MUNICIPAL_API_KEY"},
        ]
        for src_data in sources_catalog:
            src = db.query(AuthoritySource).filter(AuthoritySource.name == src_data["name"]).first()
            if not src:
                src = AuthoritySource(
                    name=src_data["name"],
                    base_url=src_data["base_url"],
                    auth_type=src_data["auth_type"],
                    enabled=True,
                    env_secret_key=src_data.get("env_secret_key"),
                )
                db.add(src)
            else:
                src.base_url = src_data["base_url"]
                src.auth_type = src_data["auth_type"]
                src.enabled = True
        db.commit()

        # 2. Mock Register Entries
        registers_catalog = [
            # A. VALID: demo certificates
            {
                "authority": "NBA",
                "certificate_number": "NBA-DEMO-READY",
                "institute_name": "Sri Krishna College of Engineering and Technology",
                "issue_date": issue_valid,
                "expiry_date": valid_exp,
                "status": "VALID",
                "data_json": {"tier": "Tier-1", "programme": "Computer Science & Engineering", "score": 750},
            },
            {
                "authority": "FIRE_DEPT",
                "certificate_number": "FSNOC-DEMO-READY",
                "institute_name": "Sri Krishna College of Engineering and Technology",
                "issue_date": issue_valid,
                "expiry_date": valid_exp,
                "status": "VALID",
                "data_json": {"hydrant_points": 12, "fire_officer": "R. Ramanathan"},
            },
            {
                "authority": "MUNICIPAL_CORP",
                "certificate_number": "OCC-DEMO-READY",
                "institute_name": "Sri Krishna College of Engineering and Technology",
                "issue_date": (today - timedelta(days=150)).isoformat(),
                "expiry_date": None,
                "status": "VALID",
                "data_json": {"built_up_sqm": 42500, "zone": "Educational Institutional Zone"},
            },
            # B. MISMATCHING: one mismatching (institute name mismatch)
            {
                "authority": "NBA",
                "certificate_number": "NBA-DEMO-LIKELY-FAIL",
                "institute_name": "Apex Global Institute of Engineering",
                "issue_date": issue_valid,
                "expiry_date": valid_exp,
                "status": "VALID",
                "data_json": {"disclaimer": "Simulated registered holder mismatch"},
            },
            # C. EXPIRED: one expired
            {
                "authority": "NBA",
                "certificate_number": "NBA-DEMO-EXPIRED",
                "institute_name": "Sri Krishna College of Engineering and Technology",
                "issue_date": (today - timedelta(days=400)).isoformat(),
                "expiry_date": past_exp,
                "status": "EXPIRED",
                "data_json": {"expired": True, "notice": "Statutory renewal overdue"},
            },
            {
                "authority": "MUNICIPAL_CORP",
                "certificate_number": "OCC-DEMO-BLOCKED",
                "institute_name": "Sri Krishna College of Engineering and Technology",
                "issue_date": "2020-01-01",
                "expiry_date": past_exp,
                "status": "EXPIRED",
                "data_json": {"fitness_revoked": True},
            },
        ]
        for reg_data in registers_catalog:
            clean_c = reg_data["certificate_number"].upper().strip()
            existing = (
                db.query(MockRegisterEntry)
                .filter(MockRegisterEntry.certificate_number == clean_c)
                .first()
            )
            if not existing:
                entry = MockRegisterEntry(**reg_data)
                db.add(entry)
            else:
                for k, v in reg_data.items():
                    setattr(existing, k, v)
        db.commit()
