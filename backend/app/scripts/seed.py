"""
Seed script for AICTE SmartVerify AI.
Seeds Sri Krishna College of Engineering and Technology (Coimbatore)
with applications, relative-date certificates, courses,
accreditations, mock complaints, DocumentTypes, Categories,
Checklists, 21 Rules with declarative definitions, and a published RuleSet.
"""

from datetime import date, datetime, timedelta, timezone
from backend.app.database import SessionLocal, engine, Base
from backend.app.models.institute import Institute
from backend.app.models.user import User, UserRole
from backend.app.models.application import Application
from backend.app.models.certificate import Certificate
from backend.app.models.course import Course
from backend.app.models.accreditation import Accreditation
from backend.app.models.rule import Rule, RuleVersion, RuleSet
from backend.app.models.document_type import DocumentType
from backend.app.models.application_category import ApplicationCategory
from backend.app.models.checklist_item import ChecklistItem
from backend.app.models.complaint import Complaint, ComplaintEvent
from backend.app.security.password import hash_password
from backend.app.services.notification_service import check_and_create_certificate_notifications


def seed_database():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    try:
        print("[SEED] Starting AICTE SmartVerify AI comprehensive seeding...")

        # ----------------------------------------------------------------------
        # 1. Main Target Institute: Sri Krishna College of Eng & Tech
        # ----------------------------------------------------------------------
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
            print("  + Created Institute: Sri Krishna College of Engineering and Technology")

        # User for SKCET
        skcet_user = db.query(User).filter(User.email == "skcet@aicte.edu.in").first()
        if not skcet_user:
            skcet_user = User(
                email="skcet@aicte.edu.in",
                password_hash=hash_password("Institute@123"),
                role=UserRole.INSTITUTE,
                institute_id=skcet.id,
                is_active=True,
            )
            db.add(skcet_user)
            db.commit()
            print("  + Created Institute User: skcet@aicte.edu.in (Pass: Institute@123)")

        # ----------------------------------------------------------------------
        # 2. Accreditation for SKCET
        # ----------------------------------------------------------------------
        accred = db.query(Accreditation).filter(Accreditation.institute_id == skcet.id).first()
        if not accred:
            accred = Accreditation(
                institute_id=skcet.id,
                nirf_rank=73,
                naac_grade="A++ (CGPA 3.62)",
                nba_accredited_courses=9,
                college_code="C-26922 / TNEA 2718",
                location_address="Sugunapuram, Kuniamuthur, Coimbatore, Tamil Nadu - 641008",
                phone="+91 422 2678001 / 02",
            )
            db.add(accred)
            db.commit()
            print("  + Added Accreditation profile for SKCET (NIRF Rank 73, NAAC A++)")

        # ----------------------------------------------------------------------
        # 3. 11 Courses for SKCET
        # ----------------------------------------------------------------------
        existing_courses = db.query(Course).filter(Course.institute_id == skcet.id).count()
        if existing_courses == 0:
            courses_list = [
                ("B.E - Computer Science & Engineering", "UG", 180),
                ("B.Tech - Artificial Intelligence & Data Science", "UG", 120),
                ("B.E - Electronics & Communication Engineering", "UG", 180),
                ("B.E - Mechanical Engineering", "UG", 120),
                ("B.Tech - Information Technology", "UG", 120),
                ("B.E - Civil Engineering", "UG", 60),
                ("B.E - Electrical & Electronics Engineering", "UG", 60),
                ("B.E - Mechatronics Engineering", "UG", 60),
                ("B.Tech - Computer Science & Business Systems", "UG", 60),
                ("M.E - Computer Science & Engineering", "PG", 24),
                ("Master of Business Administration (MBA)", "PG", 60),
            ]
            for c_name, level, intake in courses_list:
                c = Course(institute_id=skcet.id, name=c_name, level=level, intake=intake)
                db.add(c)
            db.commit()
            print("  + Seeded 11 Courses for SKCET")

        # ----------------------------------------------------------------------
        # 3b. Courses for Delhi Institute of Advanced Technology (DEL0101)
        # ----------------------------------------------------------------------
        delhi_inst = db.query(Institute).filter(Institute.aicte_institute_id == "DEL0101").first()
        if delhi_inst and db.query(Course).filter(Course.institute_id == delhi_inst.id).count() == 0:
            delhi_courses = [
                ("B.Tech Computer Science and Engineering", "UG", 120),
                ("B.Tech Artificial Intelligence and Data Science", "UG", 60),
                ("B.Tech Electronics and Communication Engineering", "UG", 90),
                ("B.Tech Mechanical Engineering", "UG", 60),
                ("B.Tech Information Technology", "UG", 60),
                ("MBA", "PG", 60),
            ]
            for c_name, level, intake in delhi_courses:
                c = Course(institute_id=delhi_inst.id, name=c_name, level=level, intake=intake)
                db.add(c)
            db.commit()
            print("  + Seeded 6 Courses for Delhi Institute of Advanced Technology (DEL0101)")

        # ----------------------------------------------------------------------
        # 3c. Accreditation & Courses for BITS Pilani (1-BITS0102)
        # ----------------------------------------------------------------------
        bits_insts = db.query(Institute).filter(Institute.aicte_institute_id.in_(["1-BITS0102", "INST-BITS"])).all()
        for b_inst in bits_insts:
            if not db.query(Accreditation).filter(Accreditation.institute_id == b_inst.id).first():
                db.add(Accreditation(
                    institute_id=b_inst.id,
                    nirf_rank=20,
                    naac_grade="A++ (CGPA 3.68)",
                    nba_accredited_courses=8,
                    college_code="C-30102 / BITS-PIL01",
                    location_address="Vidya Vihar, Pilani, Rajasthan - 333031",
                    phone="+91 1596 245073 / 74",
                ))
            if db.query(Course).filter(Course.institute_id == b_inst.id).count() == 0:
                b_courses = [
                    ("B.E. Computer Science", "UG", 180),
                    ("B.E. Electronics & Instrumentation", "UG", 120),
                    ("B.E. Electrical & Electronics", "UG", 120),
                    ("B.E. Mechanical Engineering", "UG", 120),
                    ("M.E. Microelectronics", "PG", 60),
                ]
                for c_name, level, intake in b_courses:
                    db.add(Course(institute_id=b_inst.id, name=c_name, level=level, intake=intake))
        db.commit()

        # ----------------------------------------------------------------------
        # 3d. Accreditation & Courses for NIT Trichy (1-NITT0103)
        # ----------------------------------------------------------------------
        nitt_insts = db.query(Institute).filter(Institute.aicte_institute_id.in_(["1-NITT0103", "INST-NITT"])).all()
        for n_inst in nitt_insts:
            if not db.query(Accreditation).filter(Accreditation.institute_id == n_inst.id).first():
                db.add(Accreditation(
                    institute_id=n_inst.id,
                    nirf_rank=9,
                    naac_grade="A++ (CGPA 3.78)",
                    nba_accredited_courses=10,
                    college_code="C-40103 / NITT-0103",
                    location_address="Tanjore Main Road, NH67, Tiruchirappalli, Tamil Nadu - 620015",
                    phone="+91 431 2503000 / 01",
                ))
            if db.query(Course).filter(Course.institute_id == n_inst.id).count() == 0:
                n_courses = [
                    ("B.Tech. Computer Science & Engineering", "UG", 120),
                    ("B.Tech. Electronics & Communication Engineering", "UG", 120),
                    ("B.Tech. Electrical & Electronics Engineering", "UG", 120),
                    ("B.Tech. Mechanical Engineering", "UG", 120),
                    ("M.Tech. VLSI System", "PG", 60),
                ]
                for c_name, level, intake in n_courses:
                    db.add(Course(institute_id=n_inst.id, name=c_name, level=level, intake=intake))
        db.commit()

        # ----------------------------------------------------------------------
        # 4. Applications (108 applications for SKCET)
        # ----------------------------------------------------------------------
        existing_apps = db.query(Application).filter(Application.institute_id == skcet.id).count()
        if existing_apps == 0:
            now = datetime.now(timezone.utc)
            # Create primary application
            app1 = Application(
                institute_id=skcet.id,
                application_no="APP-2026-8401",
                academic_year="2026-27",
                category="Extension of Approval (EoA)",
                status="UNDER_REVIEW",
                submitted_at=now - timedelta(days=5),
            )
            db.add(app1)
            # Remaining applications
            cats = [
                "Extension of Approval (EoA)",
                "Increase in Intake / New Course",
                "Closure of Course",
                "Change of Site / Name",
            ]
            statuses = ["APPROVED", "REJECTED", "SUBMITTED", "UNDER_REVIEW", "DRAFT"]
            for i in range(2, 109):
                app_no = f"APP-2026-{8400 + i}"
                cat = cats[i % len(cats)]
                st = statuses[i % len(statuses)]
                sub_at = (now - timedelta(days=i * 3)) if st != "DRAFT" else None
                a = Application(
                    institute_id=skcet.id,
                    application_no=app_no,
                    academic_year="2026-27" if i < 30 else ("2025-26" if i < 70 else "2024-25"),
                    category=cat,
                    status=st,
                    submitted_at=sub_at,
                )
                db.add(a)
            db.commit()
            print("  + Seeded 108 Applications for SKCET")

        # ----------------------------------------------------------------------
        # 5. Certificates (24 certificates)
        # ----------------------------------------------------------------------
        existing_certs = db.query(Certificate).filter(Certificate.institute_id == skcet.id).count()
        today = date.today()
        if existing_certs == 0:
            expiring_soon_defs = [
                ("Fire and Life Safety Certificate", 8, "APP-2025-1061", "CERT-FIRE-2025"),
                ("Pollution Control Board Consent (Air/Water)", 14, "APP-2025-1062", "CERT-PCB-8912"),
                ("Building Structural Stability Certificate", 22, "APP-2025-1063", "CERT-PWD-7741"),
                ("Sanitary Conditions & Water Potability", 29, "APP-2025-1064", "CERT-SAN-1102"),
                ("High Tension Substation Electrical Safety", 45, "APP-2025-1065", "CERT-ELE-9014"),
                ("Occupancy and Completion Certificate", 55, "APP-2025-1066", "CERT-OCC-3321"),
            ]
            expired_defs = [
                ("Campus Environmental Safety Clearance", -12, "APP-2025-1067", "CERT-ENV-4491"),
                ("Hostel Occupancy & Food Safety (FSSAI)", -45, "APP-2025-1069", "CERT-FSSAI-0021"),
                ("Drinking Water Quality Clearance", -80, "APP-2025-1068", "CERT-WTR-5580"),
            ]
            valid_defs = [
                ("AICTE Extension of Approval (EoA) 2026-27", 340, "APP-2025-1070", "CERT-EOA-2026"),
                ("Anna University Affiliation Order", 280, "APP-2025-1071", "CERT-AFF-2026"),
                ("NBA Accreditation Certificate", 310, "APP-2025-1072", "CERT-NBA-5501"),
                ("NAAC Institutional Accreditation", 365, "APP-2025-1073", "CERT-NAAC-9902"),
                ("ISO 9001:2015 Quality Management Certificate", 210, "APP-2025-1074", "CERT-ISO-7711"),
                ("PWD Building Safety Certificate", 180, "APP-2025-1075", "CERT-PWD-4422"),
                ("Electrical Safety & Substation Clearance", 195, "APP-2025-1076", "CERT-ELE-3388"),
                ("Barrier-Free Ramp & Disability Access Audit", 230, "APP-2025-1077", "CERT-ACC-1199"),
                ("Campus Sewage Treatment Plant (STP) Consent", 270, "APP-2025-1078", "CERT-STP-8833"),
                ("Hazardous Waste Disposal Authorization", 290, "APP-2025-1079", "CERT-HAZ-2277"),
                ("Disaster Management Plan Approval", 160, "APP-2025-1080", "CERT-DIS-9911"),
                ("Anti-Ragging Committee Constitution Compliance", 330, "APP-2025-1081", "CERT-ARG-4466"),
                ("Internal Complaints Committee (ICC) Compliance", 350, "APP-2025-1082", "CERT-ICC-7755"),
                ("Hostel Safety & Food Hygiene FSSAI License", 240, "APP-2025-1083", "CERT-FSS-1144"),
                ("Library Digital Resources AICTE Consortium Order", 300, "APP-2025-1084", "CERT-LIB-8800"),
            ]
            all_cert_defs = expiring_soon_defs + expired_defs + valid_defs
            for c_name, offset, app_ref, c_id in all_cert_defs:
                exp_date = today + timedelta(days=offset)
                iss_date = exp_date - timedelta(days=365)
                cert = Certificate(
                    institute_id=skcet.id,
                    application_id=app_ref,
                    name=c_name,
                    certificate_id=c_id,
                    issue_date=iss_date,
                    expiry_date=exp_date,
                    document_id=None,
                )
                db.add(cert)
            db.commit()
            print("  + Seeded 24 Certificates for SKCET")

        # ----------------------------------------------------------------------
        # 6. Document Types (14 Standard Types)
        # ----------------------------------------------------------------------
        doc_type_definitions = [
            {
                "code": "FIRE_NOC",
                "name": "Fire Safety Certificate / NOC",
                "description": "NOC issued by State Fire & Rescue Services confirming fire safety installations.",
                "issuing_authority": "State Fire & Rescue Services Department",
                "accepted_formats": ["PDF"],
                "max_size_mb": 10,
                "has_expiry": True,
                "default_validity_months": 12,
                "verification_method": "QR",
                "extraction_schema": [
                    {"key": "noc_number", "label": "NOC Ref Number", "type": "id", "required": True},
                    {"key": "valid_upto", "label": "Valid Until Date", "type": "date", "required": True},
                    {"key": "building_name", "label": "Institution / Building Name", "type": "text", "required": True},
                ],
                "keywords": ["fire", "safety", "noc", "rescue", "clearance", "flame"],
            },
            {
                "code": "BUILDING_PLAN",
                "name": "Approved Building Plan",
                "description": "Sanctioned building plan with carpet and built-up area endorsements.",
                "issuing_authority": "Local Municipal Corporation / DTCP / CMDA",
                "accepted_formats": ["PDF"],
                "max_size_mb": 15,
                "has_expiry": False,
                "default_validity_months": None,
                "verification_method": "MANUAL",
                "extraction_schema": [
                    {"key": "approval_number", "label": "Sanction Order Number", "type": "id", "required": True},
                    {"key": "built_up_area_sqm", "label": "Total Built-Up Area (sq.m)", "type": "number", "required": True},
                    {"key": "survey_numbers", "label": "Survey Numbers", "type": "text", "required": True},
                ],
                "keywords": ["building", "plan", "dtcp", "cmda", "sanction", "architect", "blueprint"],
            },
            {
                "code": "OCCUPANCY_CERT",
                "name": "Occupancy / Completion Certificate",
                "description": "Certificate from competent civic authority certifying building fitness for educational occupancy.",
                "issuing_authority": "Municipal Corporation / Town Planning Authority",
                "accepted_formats": ["PDF"],
                "max_size_mb": 10,
                "has_expiry": False,
                "default_validity_months": None,
                "verification_method": "PORTAL",
                "extraction_schema": [
                    {"key": "certificate_number", "label": "Certificate Number", "type": "id", "required": True},
                    {"key": "completion_date", "label": "Date of Completion", "type": "date", "required": True},
                ],
                "keywords": ["occupancy", "completion", "fit", "inhabitation", "structural fitness"],
            },
            {
                "code": "LAND_DOC",
                "name": "Land Title Deed / Registered Lease",
                "description": "Registered sale deed or certified 30+ year lease deed in name of the Society/Trust.",
                "issuing_authority": "Sub-Registrar Office (Registration Dept)",
                "accepted_formats": ["PDF"],
                "max_size_mb": 15,
                "has_expiry": True,
                "default_validity_months": 360,
                "verification_method": "PORTAL",
                "extraction_schema": [
                    {"key": "deed_number", "label": "Registered Document Number", "type": "id", "required": True},
                    {"key": "land_area_acres", "label": "Total Land Area (Acres)", "type": "number", "required": True},
                    {"key": "owner_name", "label": "Registered Owner / Trust Name", "type": "text", "required": True},
                ],
                "keywords": ["land", "title", "deed", "patta", "chitta", "lease", "sub-registrar"],
            },
            {
                "code": "AFFIDAVIT",
                "name": "AICTE Comprehensive Affidavit",
                "description": "Notarized affidavit on Rs. 100 non-judicial stamp paper in prescribed AICTE format.",
                "issuing_authority": "Notary Public / Oath Commissioner",
                "accepted_formats": ["PDF"],
                "max_size_mb": 10,
                "has_expiry": True,
                "default_validity_months": 12,
                "verification_method": "MANUAL",
                "extraction_schema": [
                    {"key": "notary_registration_no", "label": "Notary Registration No", "type": "id", "required": True},
                    {"key": "execution_date", "label": "Execution Date", "type": "date", "required": True},
                    {"key": "deponent_name", "label": "Deponent Name", "type": "text", "required": True},
                ],
                "keywords": ["affidavit", "stamp", "notary", "oath", "undertaking", "deponent"],
            },
            {
                "code": "DEED_CONV",
                "name": "Land Conversion & Non-Encumbrance Certificate",
                "description": "Certificate proving non-agricultural land use conversion and nil encumbrance.",
                "issuing_authority": "Revenue Divisional Officer / Tehsildar",
                "accepted_formats": ["PDF"],
                "max_size_mb": 10,
                "has_expiry": False,
                "default_validity_months": None,
                "verification_method": "PORTAL",
                "extraction_schema": [
                    {"key": "order_number", "label": "Conversion Order Ref", "type": "id", "required": True},
                    {"key": "encumbrance_status", "label": "Encumbrance Status", "type": "text", "required": True},
                ],
                "keywords": ["conversion", "encumbrance", "non-agricultural", "revenue", "tehsildar"],
            },
            {
                "code": "NBA_CERT",
                "name": "NBA Accreditation Certificate",
                "description": "National Board of Accreditation certificate for engineering/technical programmes.",
                "issuing_authority": "National Board of Accreditation (NBA)",
                "accepted_formats": ["PDF"],
                "max_size_mb": 10,
                "has_expiry": True,
                "default_validity_months": 36,
                "verification_method": "API",
                "extraction_schema": [
                    {"key": "accreditation_number", "label": "NBA File No", "type": "id", "required": True},
                    {"key": "programme_name", "label": "Accredited Programme", "type": "text", "required": True},
                    {"key": "valid_upto", "label": "Valid Upto Date", "type": "date", "required": True},
                ],
                "keywords": ["nba", "accreditation", "tier-1", "programme", "board of accreditation"],
            },
            {
                "code": "NAAC_CERT",
                "name": "NAAC Institutional Accreditation",
                "description": "National Assessment and Accreditation Council certificate with CGPA and cycle details.",
                "issuing_authority": "National Assessment and Accreditation Council (NAAC)",
                "accepted_formats": ["PDF"],
                "max_size_mb": 10,
                "has_expiry": True,
                "default_validity_months": 60,
                "verification_method": "API",
                "extraction_schema": [
                    {"key": "grade", "label": "NAAC Grade", "type": "text", "required": True},
                    {"key": "cgpa", "label": "Cumulative GPA", "type": "number", "required": True},
                    {"key": "valid_upto", "label": "Valid Upto Date", "type": "date", "required": True},
                ],
                "keywords": ["naac", "grade", "cgpa", "institutional", "council"],
            },
            {
                "code": "AUDIT_ACCOUNTS",
                "name": "Audited Annual Financial Statements",
                "description": "Balance Sheet, Income & Expenditure account with CA audit report and UDIN.",
                "issuing_authority": "Chartered Accountant (ICAI Member)",
                "accepted_formats": ["PDF"],
                "max_size_mb": 20,
                "has_expiry": True,
                "default_validity_months": 12,
                "verification_method": "DIGITAL_SIGNATURE",
                "extraction_schema": [
                    {"key": "ca_udin", "label": "CA UDIN", "type": "id", "required": True},
                    {"key": "financial_year", "label": "Financial Year", "type": "text", "required": True},
                    {"key": "ca_membership_no", "label": "CA Membership Number", "type": "id", "required": True},
                ],
                "keywords": ["audit", "balance sheet", "ca", "udin", "financial", "expenditure"],
            },
            {
                "code": "FACULTY_LIST",
                "name": "University Endorsed Faculty Muster List",
                "description": "Certified list of approved teaching faculty with cadre, qualifications, and pay scales.",
                "issuing_authority": "Affiliating University (Registrar)",
                "accepted_formats": ["PDF"],
                "max_size_mb": 10,
                "has_expiry": True,
                "default_validity_months": 12,
                "verification_method": "PORTAL",
                "extraction_schema": [
                    {"key": "endorsement_ref", "label": "University Endorsement Ref", "type": "id", "required": True},
                    {"key": "total_faculty_count", "label": "Total Faculty Count", "type": "number", "required": True},
                    {"key": "phd_faculty_count", "label": "PhD Faculty Count", "type": "number", "required": True},
                ],
                "keywords": ["faculty", "muster", "phd", "endorsement", "cadre", "professors"],
            },
            {
                "code": "EQUIP_LIST",
                "name": "Laboratory Equipment Register & Invoices",
                "description": "Certified inventory of laboratory apparatus and equipment with valuation.",
                "issuing_authority": "Institution Principal & Purchase Committee",
                "accepted_formats": ["PDF"],
                "max_size_mb": 20,
                "has_expiry": False,
                "default_validity_months": None,
                "verification_method": "MANUAL",
                "extraction_schema": [
                    {"key": "stock_register_page", "label": "Stock Register Volume/Folio", "type": "text", "required": True},
                    {"key": "total_equipment_value_inr", "label": "Total Equipment Value (INR)", "type": "number", "required": True},
                ],
                "keywords": ["equipment", "laboratory", "stock", "invoice", "machinery", "apparatus"],
            },
            {
                "code": "COMP_CENTER",
                "name": "Computer Centre Infrastructure Report",
                "description": "Details of student PCs, server configuration, LAN architecture, and bandwidth speed.",
                "issuing_authority": "System Administrator / Principal",
                "accepted_formats": ["PDF"],
                "max_size_mb": 10,
                "has_expiry": False,
                "default_validity_months": None,
                "verification_method": "MANUAL",
                "extraction_schema": [
                    {"key": "total_pcs", "label": "Total Student PCs", "type": "number", "required": True},
                    {"key": "bandwidth_mbps", "label": "Internet Bandwidth (Mbps)", "type": "number", "required": True},
                ],
                "keywords": ["computer", "terminal", "lan", "bandwidth", "network", "server"],
            },
            {
                "code": "BARRIER_FREE",
                "name": "Barrier-Free Environment & Disability Access Audit",
                "description": "Audit certificate verifying ramps, lifts, and Divyangjan-friendly accessible amenities.",
                "issuing_authority": "Chartered Engineer / Government Architect",
                "accepted_formats": ["PDF"],
                "max_size_mb": 10,
                "has_expiry": True,
                "default_validity_months": 36,
                "verification_method": "MANUAL",
                "extraction_schema": [
                    {"key": "lift_available", "label": "Dedicated Disability Lift Available", "type": "text", "required": True},
                    {"key": "ramp_slope_ratio", "label": "Ramp Slope Ratio", "type": "text", "required": True},
                ],
                "keywords": ["barrier", "disability", "ramp", "lift", "divyangjan", "accessible", "pwd"],
            },
            {
                "code": "BANK_GUARANTEE",
                "name": "Fixed Deposit Receipt (FDR) / Joint Guarantee",
                "description": "Joint FDR in favour of Principal Secretary / AICTE toward institutional security fund.",
                "issuing_authority": "Scheduled Commercial Bank",
                "accepted_formats": ["PDF"],
                "max_size_mb": 10,
                "has_expiry": True,
                "default_validity_months": 96,
                "verification_method": "API",
                "extraction_schema": [
                    {"key": "fdr_account_number", "label": "FDR / BG Account Number", "type": "id", "required": True},
                    {"key": "fdr_amount_inr", "label": "Deposit Amount (INR)", "type": "number", "required": True},
                    {"key": "maturity_date", "label": "Maturity Date", "type": "date", "required": True},
                ],
                "keywords": ["fdr", "bank guarantee", "security deposit", "joint account", "deposit"],
            },
        ]

        doc_type_map = {}
        for dt_dict in doc_type_definitions:
            clean_dt = dict(dt_dict)
            if clean_dt.get("default_validity_months") is None:
                clean_dt["default_validity_months"] = 0
            dt = db.query(DocumentType).filter(DocumentType.code == clean_dt["code"]).first()
            if not dt:
                dt = DocumentType(**clean_dt)
                db.add(dt)
                db.commit()
                db.refresh(dt)
            else:
                for k, v in clean_dt.items():
                    setattr(dt, k, v)
                db.commit()
                db.refresh(dt)
            doc_type_map[dt.code] = dt
        print("  + Seeded 14 Document Types")

        # ----------------------------------------------------------------------
        # 7. Application Categories (4 Categories)
        # ----------------------------------------------------------------------
        categories_data = [
            ("EOA", "Extension of Approval (EoA)", "Annual routine approval extension for established technical institutes."),
            ("CHANGE_OF_NAME", "Change of Name / Site of Institute", "Statutory processing for renaming or campus location alteration."),
            ("INTAKE_CHANGE", "Increase in Intake / Additional Course", "Approval for enhancing seating intake or adding new programmes."),
            ("CLOSURE_MERGER", "Closure / Merger of Institute", "Progressive or complete closure, or institutional amalgamation."),
        ]
        cat_map = {}
        for c_code, c_name, c_desc in categories_data:
            cat = db.query(ApplicationCategory).filter(ApplicationCategory.code == c_code).first()
            if not cat:
                cat = ApplicationCategory(code=c_code, name=c_name, description=c_desc, is_active=True)
                db.add(cat)
                db.commit()
                db.refresh(cat)
            cat_map[c_code] = cat
        print("  + Seeded 4 Application Categories")

        # ----------------------------------------------------------------------
        # 8. Checklists for Categories
        # ----------------------------------------------------------------------
        db.query(ChecklistItem).delete()
        db.commit()

        # EOA Checklist (12 documents)
        eoa_docs = [
            ("FIRE_NOC", True, 30, "Fire NOC must remain valid for at least 30 days beyond filing date."),
            ("BUILDING_PLAN", True, None, "Approved master plan showing instructional and administrative carpet areas."),
            ("OCCUPANCY_CERT", True, None, "Local civic body occupancy completion certificate."),
            ("LAND_DOC", True, 90, "Land title documents or registered 30+ year lease agreement."),
            ("AFFIDAVIT", True, 30, "AICTE format notarized affidavit on Rs. 100 non-judicial stamp paper."),
            ("NBA_CERT", False, 0, "NBA accreditation certificate for eligible technical streams."),
            ("NAAC_CERT", False, 0, "NAAC institutional cycle accreditation certificate."),
            ("AUDIT_ACCOUNTS", True, 30, "Audited annual accounts with CA UDIN and balance sheet."),
            ("FACULTY_LIST", True, 30, "University ratified faculty muster with qualifications and cadre."),
            ("COMP_CENTER", True, None, "Computer centre specifications and internet bandwidth certificate."),
            ("BARRIER_FREE", True, 30, "Disability accessibility compliance and ramp audit certificate."),
            ("BANK_GUARANTEE", True, 60, "Active Joint Fixed Deposit Receipt / Bank Guarantee."),
        ]

        for order, (doc_code, mandatory, min_days, help_txt) in enumerate(eoa_docs, start=1):
            dt_obj = doc_type_map.get(doc_code)
            if dt_obj:
                ci = ChecklistItem(
                    category_id=cat_map["EOA"].id,
                    document_type_id=dt_obj.id,
                    is_mandatory=mandatory,
                    min_validity_days_remaining=min_days,
                    display_order=order,
                    help_text=help_txt,
                    is_active=True,
                )
                db.add(ci)

        # CHANGE_OF_NAME Checklist
        name_change_docs = [
            ("AFFIDAVIT", True, 30, "Affidavit detailing reason for name / site alteration."),
            ("LAND_DOC", True, 90, "Land title registered under updated identity."),
            ("DEED_CONV", True, None, "Land conversion clearance order."),
            ("BUILDING_PLAN", True, None, "Sanctioned master building layout."),
            ("FIRE_NOC", True, 30, "Fire safety clearance for the designated site."),
            ("BANK_GUARANTEE", True, 60, "Amended joint bank guarantee reflecting updated name."),
        ]
        for order, (doc_code, mandatory, min_days, help_txt) in enumerate(name_change_docs, start=1):
            dt_obj = doc_type_map.get(doc_code)
            if dt_obj:
                ci = ChecklistItem(
                    category_id=cat_map["CHANGE_OF_NAME"].id,
                    document_type_id=dt_obj.id,
                    is_mandatory=mandatory,
                    min_validity_days_remaining=min_days,
                    display_order=order,
                    help_text=help_txt,
                    is_active=True,
                )
                db.add(ci)

        # INTAKE_CHANGE Checklist
        intake_docs = [
            ("NBA_CERT", True, 30, "NBA Accreditation mandatory for intake expansion."),
            ("FACULTY_LIST", True, 30, "Ratified faculty list reflecting required 1:15 or 1:20 ratio."),
            ("EQUIP_LIST", True, None, "Machinery and laboratory equipment register."),
            ("COMP_CENTER", True, None, "Student terminal calculation meeting enhanced intake."),
            ("BUILDING_PLAN", True, None, "Instructional carpet area adequacy plan."),
            ("AUDIT_ACCOUNTS", True, 30, "Audited accounts showing capital reserve sufficiency."),
        ]
        for order, (doc_code, mandatory, min_days, help_txt) in enumerate(intake_docs, start=1):
            dt_obj = doc_type_map.get(doc_code)
            if dt_obj:
                ci = ChecklistItem(
                    category_id=cat_map["INTAKE_CHANGE"].id,
                    document_type_id=dt_obj.id,
                    is_mandatory=mandatory,
                    min_validity_days_remaining=min_days,
                    display_order=order,
                    help_text=help_txt,
                    is_active=True,
                )
                db.add(ci)

        # CLOSURE_MERGER Checklist
        closure_docs = [
            ("AFFIDAVIT", True, 30, "Affidavit undertaking student transfer and faculty settlement."),
            ("AUDIT_ACCOUNTS", True, 30, "Financial statement showing no outstanding dues."),
            ("BANK_GUARANTEE", True, 60, "FDR release verification submission."),
            ("LAND_DOC", True, None, "Original land documents verification."),
        ]
        for order, (doc_code, mandatory, min_days, help_txt) in enumerate(closure_docs, start=1):
            dt_obj = doc_type_map.get(doc_code)
            if dt_obj:
                ci = ChecklistItem(
                    category_id=cat_map["CLOSURE_MERGER"].id,
                    document_type_id=dt_obj.id,
                    is_mandatory=mandatory,
                    min_validity_days_remaining=min_days,
                    display_order=order,
                    help_text=help_txt,
                    is_active=True,
                )
                db.add(ci)

        db.commit()
        print("  + Seeded Category Checklists")

        # ----------------------------------------------------------------------
        # 9. Regulatory Rules (21 Rules with Declarative Definitions)
        # ----------------------------------------------------------------------
        db.query(RuleVersion).delete()
        db.query(Rule).delete()
        db.commit()

        rules_catalog = [
            # 1. DOCUMENT_REQUIRED
            {
                "rule_code": "APH-2026-CH2-R01",
                "category": "Extension of Approval (EoA)",
                "title": "Continuous EoA Validity",
                "description": "The Institution shall maintain valid, unbroken Approval for all academic sessions without unaddressed show-cause notices or pending statutory defaults.",
                "handbook_reference": "Section 2.4.1",
                "version": "v2026.1",
                "is_mandatory": True,
                "rule_type": "MANDATORY",
                "severity": "BLOCKER",
                "applies_to_categories": ["EOA"],
                "definition": {
                    "type": "DOCUMENT_REQUIRED",
                    "document": "AFFIDAVIT",
                    "min_validity_days": 30,
                },
                "ai_checks": [
                    "Extract and verify validity timeline from historical AICTE approval orders",
                    "Cross-reference show-cause notice registry for unaddressed compliance items",
                    "Confirm active council status for all previously approved divisions",
                ],
                "evidence_required": ["AFFIDAVIT", "Previous Year EoA Letter"],
                "suggested_action": "Upload signed and notarized AICTE format affidavit executed within recent 30 days.",
            },
            # 2. VALIDITY_PERIOD
            {
                "rule_code": "APH-2026-CH2-R02",
                "category": "Extension of Approval (EoA)",
                "title": "Fire and Life Safety Certificate",
                "description": "Valid Fire and Life Safety Certificate from the Competent Authority of the State/UT must be maintained across all campus premises at all times.",
                "handbook_reference": "Section 2.4.2",
                "version": "v2026.1",
                "is_mandatory": True,
                "rule_type": "MANDATORY",
                "severity": "BLOCKER",
                "applies_to_categories": ["EOA", "CHANGE_OF_NAME"],
                "definition": {
                    "type": "VALIDITY_PERIOD",
                    "document": "FIRE_NOC",
                    "must_be_valid_on": "today",
                    "buffer_days": 30,
                },
                "ai_checks": [
                    "Extract issue and expiry dates via high-accuracy OCR with date normalization",
                    "Verify digital signature or official seal from State Fire and Rescue Services",
                    "Check building names, survey numbers and blocks covered in NOC schedule",
                ],
                "evidence_required": ["FIRE_NOC"],
                "suggested_action": "Renew Fire NOC with the State Fire and Rescue Services immediately to avoid statutory withholding.",
            },
            # 3. DOCUMENT_REQUIRED
            {
                "rule_code": "APH-2026-CH2-R03",
                "category": "Extension of Approval (EoA)",
                "title": "Building Occupancy Compliance",
                "description": "Occupancy / Completion Certificate from the Competent Civic Authority must cover every operational academic block on campus.",
                "handbook_reference": "Section 2.4.3",
                "version": "v2026.1",
                "is_mandatory": True,
                "rule_type": "MANDATORY",
                "severity": "BLOCKER",
                "applies_to_categories": ["EOA", "CHANGE_OF_NAME"],
                "definition": {
                    "type": "DOCUMENT_REQUIRED",
                    "document": "OCCUPANCY_CERT",
                },
                "ai_checks": [
                    "Verify issuing municipality, urban planning body or DTCP authorization",
                    "Check total built-up plinth area matches architect master layout plan",
                ],
                "evidence_required": ["OCCUPANCY_CERT"],
                "suggested_action": "Submit civic completion/occupancy certificate from local development authority.",
            },
            # 4. DOCUMENT_REQUIRED
            {
                "rule_code": "APH-2026-CH2-R04",
                "category": "Extension of Approval (EoA)",
                "title": "Land Title and Ownership",
                "description": "Clear and undisputed land title in the name of the Applicant Society/Trust or 30+ year government lease.",
                "handbook_reference": "Section 2.4.4",
                "version": "v2026.1",
                "is_mandatory": True,
                "rule_type": "MANDATORY",
                "severity": "BLOCKER",
                "applies_to_categories": ["EOA", "CHANGE_OF_NAME"],
                "definition": {
                    "type": "DOCUMENT_REQUIRED",
                    "document": "LAND_DOC",
                },
                "ai_checks": [
                    "Cross-check title deed registration number and encumbrance register",
                    "Validate land area matches rural (7.5 acres) or mega-city (2.5 acres) minimum norms",
                ],
                "evidence_required": ["LAND_DOC"],
                "suggested_action": "Upload certified land ownership title deed registered with the Sub-Registrar.",
            },
            # 5. DOCUMENT_REQUIRED
            {
                "rule_code": "APH-2026-CH2-R05",
                "category": "Extension of Approval (EoA)",
                "title": "Barrier-Free Environment Compliance",
                "description": "Mandatory provision of barrier-free environment, ramps, Braille lift controls, and disabled-friendly rest facilities.",
                "handbook_reference": "Section 2.4.5",
                "version": "v2026.1",
                "is_mandatory": True,
                "rule_type": "MANDATORY",
                "severity": "MAJOR",
                "applies_to_categories": ["EOA"],
                "definition": {
                    "type": "DOCUMENT_REQUIRED",
                    "document": "BARRIER_FREE",
                },
                "ai_checks": [
                    "Confirm ramp gradient ratio (1:12 maximum slope) from certified architectural drawings",
                    "Verify operational passenger elevator with Braille and auditory notification",
                ],
                "evidence_required": ["BARRIER_FREE"],
                "suggested_action": "Upload Chartered Engineer barrier-free accessibility audit certificate.",
            },
            # 6. DOCUMENT_REQUIRED
            {
                "rule_code": "APH-2026-CH2-R06",
                "category": "Extension of Approval (EoA)",
                "title": "Financial Viability & Audited Accounts",
                "description": "Annual audited financial statement certified by a Chartered Accountant bearing active ICAI UDIN.",
                "handbook_reference": "Section 2.4.6",
                "version": "v2026.1",
                "is_mandatory": True,
                "rule_type": "MANDATORY",
                "severity": "MAJOR",
                "applies_to_categories": ["EOA", "INTAKE_CHANGE"],
                "definition": {
                    "type": "DOCUMENT_REQUIRED",
                    "document": "AUDIT_ACCOUNTS",
                },
                "ai_checks": [
                    "Validate CA UDIN against ICAI verification portal",
                    "Extract operational surplus, capital reserves and salary expenditure ratios",
                ],
                "evidence_required": ["AUDIT_ACCOUNTS"],
                "suggested_action": "Provide audited balance sheet and income statement with valid CA UDIN.",
            },
            # 7. NUMERIC_THRESHOLD
            {
                "rule_code": "APH-2026-CH2-R07",
                "category": "Faculty & Staffing",
                "title": "Cadre Ratio and Faculty Count",
                "description": "Maintain mandatory Cadre Ratio (1:2:6 for Professor : Associate Prof : Assistant Prof) and 1:15/1:20 teacher-to-student ratio.",
                "handbook_reference": "Section 3.1.1",
                "version": "v2026.1",
                "is_mandatory": True,
                "rule_type": "MANDATORY",
                "severity": "BLOCKER",
                "applies_to_categories": ["EOA", "INTAKE_CHANGE"],
                "definition": {
                    "type": "NUMERIC_THRESHOLD",
                    "field": "courses.total_intake",
                    "operator": ">",
                    "value": 0,
                },
                "ai_checks": [
                    "Calculate sanctioned intake across all active programmes and compute required faculty count",
                    "Verify cadre ratio proportions conform to AICTE Pay and Cadre Regulations",
                ],
                "evidence_required": ["FACULTY_LIST"],
                "suggested_action": "Reconcile approved student intake and upload endorsed faculty roster.",
            },
            # 8. COUNT_AT_LEAST
            {
                "rule_code": "APH-2026-CH2-R08",
                "category": "Faculty & Staffing",
                "title": "Minimum Faculty with Ph.D. Qualifications",
                "description": "Engineering departments must maintain minimum Ph.D. qualified faculty in accordance with statutory cadre requirements.",
                "handbook_reference": "Section 3.1.2",
                "version": "v2026.1",
                "is_mandatory": True,
                "rule_type": "MANDATORY",
                "severity": "MAJOR",
                "applies_to_categories": ["EOA", "INTAKE_CHANGE"],
                "definition": {
                    "type": "COUNT_AT_LEAST",
                    "collection": "courses",
                    "field": "intake",
                    "min_count": 1,
                    "condition": {"operator": ">=", "value": 60},
                },
                "ai_checks": [
                    "Extract Ph.D. degree awarding university and year from faculty credential registry",
                    "Verify doctoral research alignment with taught undergraduate/postgraduate discipline",
                ],
                "evidence_required": ["FACULTY_LIST"],
                "suggested_action": "Ensure high-intake courses have Ph.D. qualified faculty and upload degree certificates.",
            },
            # 9. FIELD_REQUIRED
            {
                "rule_code": "APH-2026-CH2-R09",
                "category": "Faculty & Staffing",
                "title": "Faculty Pay Scales & EPF Compliance",
                "description": "Payment of salaries through digital bank disbursement under AICTE 7th CPC salary grades.",
                "handbook_reference": "Section 3.2.1",
                "version": "v2026.1",
                "is_mandatory": True,
                "rule_type": "MANDATORY",
                "severity": "MAJOR",
                "applies_to_categories": ["EOA"],
                "definition": {
                    "type": "FIELD_REQUIRED",
                    "field": "institute.aicte_institute_id",
                },
                "ai_checks": [
                    "Cross-check electronic challan receipts with EPFO establishment code",
                    "Analyze bank disbursement scroll ensuring gross salary matches pay scale norms",
                ],
                "evidence_required": ["FACULTY_LIST", "AUDIT_ACCOUNTS"],
                "suggested_action": "Confirm valid institute ID and upload faculty salary disbursement certificates.",
            },
            # 10. INFRASTRUCTURE
            {
                "rule_code": "APH-2026-CH2-R10",
                "category": "Infrastructure & Laboratories",
                "title": "Total Instructional Built-Up Area",
                "description": "The institution must provide minimum instructional built-up carpet area for classrooms, tutorial rooms, drawing halls, and laboratories.",
                "handbook_reference": "Section 4.1.1",
                "version": "v2026.1",
                "is_mandatory": True,
                "rule_type": "MANDATORY",
                "severity": "BLOCKER",
                "applies_to_categories": ["EOA", "INTAKE_CHANGE"],
                "definition": {
                    "type": "INFRASTRUCTURE",
                    "check_type": "INSTRUCTIONAL_AREA",
                    "min_carpet_area_sqm": 400.0,
                },
                "ai_checks": [
                    "Aggregate carpet area across room dimensions extracted from architectural blue prints",
                    "Compare aggregate carpet area with APH Appendix 4 prescriptive space norms",
                ],
                "evidence_required": ["BUILDING_PLAN"],
                "suggested_action": "Ensure instructional carpet area meets minimum threshold of 400 sq.m.",
            },
            # 11. DOCUMENT_REQUIRED
            {
                "rule_code": "APH-2026-CH2-R11",
                "category": "Infrastructure & Laboratories",
                "title": "Laboratory Equipment Compliance",
                "description": "Adequate laboratory equipment, experimental setups, and consumables for each curriculum division.",
                "handbook_reference": "Section 4.2.1",
                "version": "v2026.1",
                "is_mandatory": True,
                "rule_type": "MANDATORY",
                "severity": "MAJOR",
                "applies_to_categories": ["EOA", "INTAKE_CHANGE"],
                "definition": {
                    "type": "DOCUMENT_REQUIRED",
                    "document": "EQUIP_LIST",
                },
                "ai_checks": [
                    "Parse equipment inventories and match against required syllabus experiments",
                    "Extract invoice dates and vendor GST numbers to confirm authentic procurement",
                ],
                "evidence_required": ["EQUIP_LIST"],
                "suggested_action": "Upload signed stock register extracts showing lab equipment adequacy.",
            },
            # 12. INFRASTRUCTURE
            {
                "rule_code": "APH-2026-CH2-R12",
                "category": "Infrastructure & Laboratories",
                "title": "Computing Facilities and Internet Bandwidth",
                "description": "Student-to-PC ratio of 1:4 and dedicated high-speed optical fiber connectivity of minimum 100 Mbps.",
                "handbook_reference": "Section 4.3.1",
                "version": "v2026.1",
                "is_mandatory": True,
                "rule_type": "MANDATORY",
                "severity": "MAJOR",
                "applies_to_categories": ["EOA", "INTAKE_CHANGE"],
                "definition": {
                    "type": "INFRASTRUCTURE",
                    "check_type": "COMPUTER_RATIO",
                    "min_bandwidth_mbps": 100.0,
                },
                "ai_checks": [
                    "Verify total PC inventory matches student-to-computer ratio based on total enrolled intake",
                    "Check internet leased line bill with active SLA and minimum 100 Mbps bandwidth",
                ],
                "evidence_required": ["COMP_CENTER"],
                "suggested_action": "Maintain optical fiber connection of at least 100 Mbps and update computer center specs.",
            },
            # 13. NUMERIC_THRESHOLD
            {
                "rule_code": "APH-2026-CH2-R13",
                "category": "Infrastructure & Laboratories",
                "title": "Library Books & AICTE Consortium E-Journals",
                "description": "Prescribed collection of print volumes, national journals, and active subscription to AICTE Consortium e-resources.",
                "handbook_reference": "Section 4.4.1",
                "version": "v2026.1",
                "is_mandatory": False,
                "rule_type": "ADVISORY",
                "severity": "MINOR",
                "applies_to_categories": ["EOA"],
                "definition": {
                    "type": "NUMERIC_THRESHOLD",
                    "field": "institute.nirf_rank",
                    "operator": "<=",
                    "value": 200,
                },
                "ai_checks": [
                    "Verify annual budget expenditure on print books and online e-journal consortiums",
                    "Ensure institutional NIRF ranking data is consistently recorded",
                ],
                "evidence_required": ["AUDIT_ACCOUNTS"],
                "suggested_action": "Enhance library collections and digital consortium subscriptions.",
            },
            # 14. VALIDITY_PERIOD
            {
                "rule_code": "APH-2026-CH2-R14",
                "category": "Accreditation & Approvals",
                "title": "Valid NBA Accreditation for Programme Intake",
                "description": "Institutions seeking additional intake or new divisions must hold valid Tier-I / Tier-II NBA Accreditation.",
                "handbook_reference": "Section 5.1.1",
                "version": "v2026.1",
                "is_mandatory": True,
                "rule_type": "MANDATORY",
                "severity": "BLOCKER",
                "applies_to_categories": ["INTAKE_CHANGE"],
                "definition": {
                    "type": "VALIDITY_PERIOD",
                    "document": "NBA_CERT",
                    "must_be_valid_on": "today",
                    "buffer_days": 0,
                },
                "ai_checks": [
                    "Query NBA official accreditation database using programme code",
                    "Check NBA validity date extends through the forthcoming academic session",
                ],
                "evidence_required": ["NBA_CERT"],
                "suggested_action": "Submit unexpired NBA accreditation certificate for the qualifying programme.",
            },
            # 15. EXTERNAL_VERIFICATION
            {
                "rule_code": "APH-2026-CH2-R15",
                "category": "Accreditation & Approvals",
                "title": "Institutional NAAC Accreditation Tier",
                "description": "Institutions with autonomous status or seeking university status must possess institutional NAAC accreditation.",
                "handbook_reference": "Section 5.2.1",
                "version": "v2026.1",
                "is_mandatory": False,
                "rule_type": "ADVISORY",
                "severity": "MAJOR",
                "applies_to_categories": ["EOA", "INTAKE_CHANGE"],
                "definition": {
                    "type": "EXTERNAL_VERIFICATION",
                    "document": "NAAC_CERT",
                    "verification_service": "NAAC_PORTAL_API",
                },
                "ai_checks": [
                    "Query NAAC institutional register for valid Grade and CGPA",
                    "Ensure accreditation certificate cycle is currently operational",
                ],
                "evidence_required": ["NAAC_CERT"],
                "suggested_action": "Verify institutional NAAC accreditation grade on the official NAAC portal.",
            },
            # 16. DOCUMENT_REQUIRED
            {
                "rule_code": "APH-2026-CH2-R16",
                "category": "Institutional Governance",
                "title": "Non-Encumbrance & Land Conversion Order",
                "description": "Submission of recent Non-Encumbrance Certificate from Sub-Registrar and revenue land conversion order.",
                "handbook_reference": "Section 6.1.1",
                "version": "v2026.1",
                "is_mandatory": True,
                "rule_type": "MANDATORY",
                "severity": "BLOCKER",
                "applies_to_categories": ["CHANGE_OF_NAME"],
                "definition": {
                    "type": "DOCUMENT_REQUIRED",
                    "document": "DEED_CONV",
                },
                "ai_checks": [
                    "Inspect Sub-Registrar seal and Nil encumbrance statement",
                    "Confirm Tahsildar / District Collector non-agricultural conversion order",
                ],
                "evidence_required": ["DEED_CONV"],
                "suggested_action": "Upload certified Non-Encumbrance and land conversion orders.",
            },
            # 17. CROSS_FIELD_MATCH
            {
                "rule_code": "APH-2026-CH2-R17",
                "category": "Institutional Governance",
                "title": "Name Change Verification Affidavit",
                "description": "Resolution of the Trust and governing affidavit must match the official institute name.",
                "handbook_reference": "Section 6.2.1",
                "version": "v2026.1",
                "is_mandatory": True,
                "rule_type": "MANDATORY",
                "severity": "BLOCKER",
                "applies_to_categories": ["CHANGE_OF_NAME"],
                "definition": {
                    "type": "CROSS_FIELD_MATCH",
                    "left": "institute.name",
                    "right": "doc.AFFIDAVIT.deponent_name",
                    "fuzzy": True,
                    "threshold": 0.6,
                },
                "ai_checks": [
                    "Cross-reference trust resolution with AICTE portal institute name",
                    "Validate legal gazette publication order for change of name",
                ],
                "evidence_required": ["AFFIDAVIT"],
                "suggested_action": "Ensure name on legal affidavit matches the registered institute name.",
            },
            # 18. VALIDITY_PERIOD
            {
                "rule_code": "APH-2026-CH2-R18",
                "category": "Institutional Governance",
                "title": "Joint Security Deposit (FDR) Maintenance",
                "description": "The institution shall maintain irrevocable joint Fixed Deposit with AICTE for prescribed statutory period.",
                "handbook_reference": "Section 6.3.1",
                "version": "v2026.1",
                "is_mandatory": True,
                "rule_type": "MANDATORY",
                "severity": "BLOCKER",
                "applies_to_categories": ["EOA", "CHANGE_OF_NAME", "CLOSURE_MERGER"],
                "definition": {
                    "type": "VALIDITY_PERIOD",
                    "document": "BANK_GUARANTEE",
                    "must_be_valid_on": "today",
                    "buffer_days": 60,
                },
                "ai_checks": [
                    "Verify joint account holder names including designated Regional AICTE Officer",
                    "Confirm deposit tenure and maturity date exceed current session by 60 days",
                ],
                "evidence_required": ["BANK_GUARANTEE"],
                "suggested_action": "Renew Joint Bank Guarantee or FDR with the designated scheduled commercial bank.",
            },
            # 19. COUNT_AT_LEAST
            {
                "rule_code": "APH-2026-CH2-R19",
                "category": "Institutional Governance",
                "title": "Anti-Ragging and Grievance Committee Notification",
                "description": "Constitution of Anti-Ragging Committee, Anti-Ragging Squad, and Internal Complaints Committee.",
                "handbook_reference": "Section 6.4.1",
                "version": "v2026.1",
                "is_mandatory": False,
                "rule_type": "ADVISORY",
                "severity": "ADVISORY",
                "applies_to_categories": ["EOA"],
                "definition": {
                    "type": "COUNT_AT_LEAST",
                    "collection": "complaints",
                    "field": "id",
                    "min_count": 0,
                },
                "ai_checks": [
                    "Verify annual composition of mandatory statutory committees",
                    "Check online grievance redressal portal integration and ticket resolution log",
                ],
                "evidence_required": ["AFFIDAVIT"],
                "suggested_action": "Maintain active grievance records and publish committee members online.",
            },
            # 20. COMPOSITE (all)
            {
                "rule_code": "APH-2026-CH2-R20",
                "category": "Extension of Approval (EoA)",
                "title": "Comprehensive Campus Safety Composite",
                "description": "Dual verification of structural life safety: requires both valid Fire NOC and Barrier-Free disability accessibility audit.",
                "handbook_reference": "Section 2.5.1",
                "version": "v2026.1",
                "is_mandatory": True,
                "rule_type": "MANDATORY",
                "severity": "BLOCKER",
                "applies_to_categories": ["EOA"],
                "definition": {
                    "type": "COMPOSITE",
                    "operator": "all",
                    "conditions": [
                        {
                            "type": "VALIDITY_PERIOD",
                            "document": "FIRE_NOC",
                            "must_be_valid_on": "today",
                            "buffer_days": 0,
                        },
                        {
                            "type": "DOCUMENT_REQUIRED",
                            "document": "BARRIER_FREE",
                        },
                    ],
                },
                "ai_checks": [
                    "Simultaneously verify Fire NOC validity and Barrier-Free certificate presence",
                ],
                "evidence_required": ["FIRE_NOC", "BARRIER_FREE"],
                "suggested_action": "Submit both valid Fire NOC and Barrier-Free accessibility certificates.",
            },
            # 21. COMPOSITE (all)
            {
                "rule_code": "APH-2026-CH2-R21",
                "category": "Institutional Governance",
                "title": "Mandatory Application Completeness Composite",
                "description": "Validation check requiring both academic year and application number to be populated.",
                "handbook_reference": "Section 1.1.2",
                "version": "v2026.1",
                "is_mandatory": True,
                "rule_type": "MANDATORY",
                "severity": "BLOCKER",
                "applies_to_categories": ["EOA", "CHANGE_OF_NAME", "INTAKE_CHANGE", "CLOSURE_MERGER"],
                "definition": {
                    "type": "COMPOSITE",
                    "operator": "all",
                    "conditions": [
                        {"type": "FIELD_REQUIRED", "field": "application.academic_year"},
                        {"type": "FIELD_REQUIRED", "field": "application.application_no"},
                    ],
                },
                "ai_checks": [
                    "Verify academic year is explicitly formatted as YYYY-YY",
                    "Verify unique application number exists",
                ],
                "evidence_required": ["AFFIDAVIT"],
                "suggested_action": "Complete all mandatory application identifier fields before final submission.",
            },
        ]

        seeded_rules = []
        for r_dict in rules_catalog:
            rule_obj = Rule(
                code=r_dict["rule_code"],
                rule_code=r_dict["rule_code"],
                category=r_dict["category"],
                title=r_dict["title"],
                description=r_dict["description"],
                handbook_reference=r_dict["handbook_reference"],
                handbook_ref=r_dict["handbook_reference"],
                version=r_dict["version"],
                is_mandatory=r_dict["is_mandatory"],
                rule_type=r_dict["rule_type"],
                severity=r_dict.get("severity", "MAJOR"),
                mandatory=r_dict["is_mandatory"],
                applies_to_categories=r_dict.get("applies_to_categories", ["EOA"]),
                definition=r_dict.get("definition"),
                ai_checks=r_dict.get("ai_checks", []),
                evidence_required=r_dict.get("evidence_required", []),
                suggested_action=r_dict.get("suggested_action"),
                status="PUBLISHED",
                current_version=1,
                is_active=True,
            )
            db.add(rule_obj)
            seeded_rules.append(rule_obj)

        db.commit()
        print(f"  + Seeded {len(seeded_rules)} Rules with Declarative Definitions")

        # ----------------------------------------------------------------------
        # 10. Publish Initial RuleSet: "APH 2026-27 v1"
        # ----------------------------------------------------------------------
        db.query(RuleSet).delete()
        db.commit()

        # Build snapshot
        snapshot_rules = []
        for r in seeded_rules:
            snapshot_rules.append({
                "code": r.code,
                "title": r.title,
                "description": r.description,
                "handbook_ref": r.handbook_ref,
                "rule_type": r.rule_type,
                "severity": r.severity,
                "mandatory": r.mandatory,
                "applies_to_categories": r.applies_to_categories,
                "definition": r.definition,
                "ai_checks": r.ai_checks,
                "evidence_required": r.evidence_required,
                "suggested_action": r.suggested_action,
                "status": r.status,
                "current_version": r.current_version,
                "is_active": r.is_active,
            })

        ruleset_snapshot = {
            "published_at": datetime.utcnow().isoformat() + "Z",
            "published_by": "admin@aicte-india.org",
            "rules": snapshot_rules,
            "document_types": [{"code": dt.code, "name": dt.name} for dt in doc_type_map.values()],
            "categories": [{"code": c.code, "name": c.name} for c in cat_map.values()],
        }

        initial_ruleset = RuleSet(
            name="APH 2026-27",
            version_label="v1.0",
            status="ACTIVE",
            snapshot=ruleset_snapshot,
            published_at=datetime.utcnow(),
            published_by=None,
        )
        db.add(initial_ruleset)
        db.commit()
        print(f"  + Published Initial RuleSet: '{initial_ruleset.name}' ({initial_ruleset.version_label}) with {len(snapshot_rules)} rules")

        # ----------------------------------------------------------------------
        # 11. Mock Complaints with Events
        # ----------------------------------------------------------------------
        if db.query(Complaint).filter(Complaint.institute_id == skcet.id).count() == 0:
            complaint1 = Complaint(
                ticket_id="TCK-2026-9041",
                institute_id=skcet.id,
                category="Application Processing Delay",
                subject="Discrepancy in online intake verification for B.Tech AI & DS",
                description="The approved intake of 120 seats in B.Tech AIDS is reflecting as 60 in the draft portal verification table.",
                status="In Progress",
            )
            db.add(complaint1)
            db.commit()
            db.refresh(complaint1)

            e1 = ComplaintEvent(complaint_id=complaint1.id, action="Ticket Created", notes="Complaint filed by Sri Krishna College of Eng & Tech.", created_by="Institute Officer")
            e2 = ComplaintEvent(complaint_id=complaint1.id, action="Assigned to Regional Officer", notes="Assigned to Southern Regional Office (SRO-Chennai) Scrutiny Officer.", created_by="AICTE Helpdesk")
            db.add_all([e1, e2])

            complaint2 = Complaint(
                ticket_id="TCK-2026-7812",
                institute_id=skcet.id,
                category="Payment Reconciliation",
                subject="Scrutiny fee double debit reconciliation request",
                description="Transaction ref TXN-89412 debited twice for application APP-2026-8404 during net banking gateway redirect.",
                status="Resolved",
            )
            db.add(complaint2)
            db.commit()
            db.refresh(complaint2)

            e3 = ComplaintEvent(complaint_id=complaint2.id, action="Ticket Created", notes="Payment duplicate debit query logged.", created_by="Institute Officer")
            e4 = ComplaintEvent(complaint_id=complaint2.id, action="Payment Verified", notes="Accounts branch verified duplicate debit. Refund of Rs. 50,000 initiated.", created_by="Accounts Officer")
            e5 = ComplaintEvent(complaint_id=complaint2.id, action="Resolved", notes="Refund processed to source account ref UTR-9988112.", created_by="Accounts Officer")
            db.add_all([e3, e4, e5])

            db.commit()
            print("  + Seeded 2 Complaints with full event history")

        # ----------------------------------------------------------------------
        # 12. Generate Notifications for Certificates
        # ----------------------------------------------------------------------
        notif_count = check_and_create_certificate_notifications(db)
        print(f"  + Generated {notif_count} Notifications based on seeded certificates")

        # ----------------------------------------------------------------------
        # 13. Ensure System Test Accounts Exist
        # ----------------------------------------------------------------------
        del_inst = db.query(Institute).filter(Institute.aicte_institute_id == "DEL0101").first()
        if not del_inst:
            del_inst = Institute(aicte_institute_id="DEL0101", name="Sri Krishna College of Engineering and Technology", state="Tamil Nadu", status="ACTIVE")
            db.add(del_inst)
            db.commit()
            db.refresh(del_inst)
        elif del_inst.name != "Sri Krishna College of Engineering and Technology":
            del_inst.name = "Sri Krishna College of Engineering and Technology"
            del_inst.state = "Tamil Nadu"
            db.commit()

        del_user = db.query(User).filter(User.email == "del0101@aicte.edu.in").first()
        if not del_user:
            del_user = User(email="del0101@aicte.edu.in", password_hash=hash_password("Institute@123"), role=UserRole.INSTITUTE, institute_id=del_inst.id, is_active=True)
            db.add(del_user)

        admin = db.query(User).filter(User.email == "admin@aicte-india.org").first()
        if not admin:
            admin = User(email="admin@aicte-india.org", password_hash=hash_password("Admin@2026!"), role=UserRole.ADMIN, is_active=True)
            db.add(admin)

        reviewer = db.query(User).filter(User.email == "reviewer@aicte-india.org").first()
        if not reviewer:
            reviewer = User(email="reviewer@aicte-india.org", password_hash=hash_password("Reviewer@2026!"), role=UserRole.REVIEWER, is_active=True)
            db.add(reviewer)

        db.commit()
        print("[SEED] Database seeding completed successfully.")

    except Exception as e:
        db.rollback()
        print(f"[ERROR] Seeding failed: {e}")
        raise e
    finally:
        db.close()


if __name__ == "__main__":
    seed_database()
