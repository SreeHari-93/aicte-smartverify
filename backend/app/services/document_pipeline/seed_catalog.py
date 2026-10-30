from typing import List, Dict, Any
from sqlalchemy.orm import Session
from backend.app.models.document_type import DocumentType

DOCUMENT_TYPES_CATALOG: List[Dict[str, Any]] = [
    {
        "code": "FIRE_NOC",
        "name": "Fire Safety Certificate / NOC",
        "description": "NOC issued by State Fire & Rescue Services confirming fire safety installations.",
        "issuing_authority": "State Fire & Rescue Services Department",
        "accepted_formats": ["PDF", "JPG", "PNG"],
        "max_size_mb": 10,
        "has_expiry": True,
        "default_validity_months": 12,
        "verification_method": "QR",
        "extraction_schema": [
            {"key": "noc_number", "label": "NOC Ref Number", "type": "id", "required": True},
            {"key": "valid_upto", "label": "Valid Until Date", "type": "date", "required": True},
            {"key": "building_name", "label": "Institution / Building Name", "type": "text", "required": True},
        ],
        "keywords": [
            "fire", "safety", "noc", "rescue", "clearance", "flame", "extinguisher",
            "hydrant", "disaster", "hazard", "firefighting", "station officer"
        ],
    },
    {
        "code": "BUILDING_PLAN",
        "name": "Approved Building Plan",
        "description": "Sanctioned building plan with carpet and built-up area endorsements.",
        "issuing_authority": "Local Municipal Corporation / DTCP / CMDA",
        "accepted_formats": ["PDF"],
        "max_size_mb": 15,
        "has_expiry": False,
        "default_validity_months": 0,
        "verification_method": "MANUAL",
        "extraction_schema": [
            {"key": "approval_number", "label": "Sanction Order Number", "type": "id", "required": True},
            {"key": "built_up_area_sqm", "label": "Total Built-Up Area (sq.m)", "type": "number", "required": True},
            {"key": "survey_numbers", "label": "Survey Numbers", "type": "text", "required": True},
        ],
        "keywords": [
            "building", "plan", "dtcp", "cmda", "sanction", "architect", "blueprint",
            "built-up area", "carpet area", "survey number", "structural", "drawing"
        ],
    },
    {
        "code": "OCCUPANCY_CERT",
        "name": "Occupancy / Completion Certificate",
        "description": "Certificate from competent civic authority certifying building fitness for educational occupancy.",
        "issuing_authority": "Municipal Corporation / Town Planning Authority",
        "accepted_formats": ["PDF"],
        "max_size_mb": 10,
        "has_expiry": False,
        "default_validity_months": 0,
        "verification_method": "PORTAL",
        "extraction_schema": [
            {"key": "certificate_number", "label": "Certificate Number", "type": "id", "required": True},
            {"key": "completion_date", "label": "Date of Completion", "type": "date", "required": True},
        ],
        "keywords": [
            "occupancy", "completion", "fit", "inhabitation", "structural fitness",
            "completion certificate", "habitable", "civic body", "planning authority"
        ],
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
        "keywords": [
            "land", "title", "deed", "patta", "chitta", "lease", "sub-registrar",
            "sale deed", "acres", "society", "trust", "revenue department"
        ],
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
        "keywords": [
            "affidavit", "stamp", "notary", "oath", "undertaking", "deponent",
            "sworn", "solemnly affirm", "prescribed format", "stamp paper", "non-judicial"
        ],
    },
    {
        "code": "DEED_CONV",
        "name": "Land Conversion & Non-Encumbrance Certificate",
        "description": "Certificate proving non-agricultural land use conversion and nil encumbrance.",
        "issuing_authority": "Revenue Divisional Officer / Tehsildar",
        "accepted_formats": ["PDF"],
        "max_size_mb": 10,
        "has_expiry": False,
        "default_validity_months": 0,
        "verification_method": "PORTAL",
        "extraction_schema": [
            {"key": "order_number", "label": "Conversion Order Ref", "type": "id", "required": True},
            {"key": "encumbrance_status", "label": "Encumbrance Status", "type": "text", "required": True},
        ],
        "keywords": [
            "conversion", "encumbrance", "non-agricultural", "revenue", "tehsildar",
            "district collector", "land use", "nil encumbrance", "order ref"
        ],
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
        "keywords": [
            "nba", "accreditation", "tier-1", "tier-2", "programme", "board of accreditation",
            "accredited", "valid upto", "evaluation", "washington accord"
        ],
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
        "keywords": [
            "naac", "grade", "cgpa", "institutional", "council", "assessment",
            "cycle", "peer team", "university grants commission"
        ],
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
        "keywords": [
            "audit", "balance sheet", "ca", "udin", "financial", "expenditure",
            "income", "chartered accountant", "icai", "statutory auditor"
        ],
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
        "keywords": [
            "faculty", "muster", "phd", "endorsement", "cadre", "professors",
            "assistant professor", "associate professor", "registrar", "university endorsed"
        ],
    },
    {
        "code": "EQUIP_LIST",
        "name": "Laboratory Equipment Register & Invoices",
        "description": "Certified inventory of laboratory apparatus and equipment with valuation.",
        "issuing_authority": "Institution Principal & Purchase Committee",
        "accepted_formats": ["PDF"],
        "max_size_mb": 20,
        "has_expiry": False,
        "default_validity_months": 0,
        "verification_method": "MANUAL",
        "extraction_schema": [
            {"key": "stock_register_page", "label": "Stock Register Volume/Folio", "type": "text", "required": True},
            {"key": "total_equipment_value_inr", "label": "Total Equipment Value (INR)", "type": "number", "required": True},
        ],
        "keywords": [
            "equipment", "laboratory", "stock", "invoice", "machinery", "apparatus",
            "stock register", "lab instruments", "purchase committee", "valuation"
        ],
    },
    {
        "code": "COMP_CENTER",
        "name": "Computer Centre Infrastructure Report",
        "description": "Details of student PCs, server configuration, LAN architecture, and bandwidth speed.",
        "issuing_authority": "System Administrator / Principal",
        "accepted_formats": ["PDF"],
        "max_size_mb": 10,
        "has_expiry": False,
        "default_validity_months": 0,
        "verification_method": "MANUAL",
        "extraction_schema": [
            {"key": "total_pcs", "label": "Total Student PCs", "type": "number", "required": True},
            {"key": "bandwidth_mbps", "label": "Internet Bandwidth (Mbps)", "type": "number", "required": True},
        ],
        "keywords": [
            "computer", "terminal", "lan", "bandwidth", "network", "server",
            "pcs", "internet", "gigabit", "wi-fi", "system administrator"
        ],
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
        "keywords": [
            "barrier", "disability", "ramp", "lift", "divyangjan", "accessible",
            "pwd", "wheelchair", "barrier-free", "braille", "handicapped"
        ],
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
        "keywords": [
            "fdr", "bank guarantee", "security deposit", "joint account", "deposit",
            "fixed deposit", "lien", "maturity date", "commercial bank"
        ],
    },
    {
        "code": "CYBER_AUDIT",
        "name": "Cyber Security Audit & IT Infrastructure Certificate",
        "description": "Information security and IT network audit certificate by CERT-In empanelled auditor.",
        "issuing_authority": "CERT-In Empanelled IT Security Auditor",
        "accepted_formats": ["PDF"],
        "max_size_mb": 10,
        "has_expiry": True,
        "default_validity_months": 12,
        "verification_method": "PORTAL",
        "extraction_schema": [
            {"key": "certificate_number", "label": "Audit Report Number", "type": "id", "required": True},
            {"key": "valid_upto", "label": "Valid Until Date", "type": "date", "required": True},
        ],
        "keywords": ["cyber", "security", "audit", "it infrastructure", "cert-in", "network"],
    },
    {
        "code": "POLLUTION_NOC",
        "name": "Pollution Control Board Consent to Operate (CTO)",
        "description": "Consent to Establish / Operate issued by State Pollution Control Board.",
        "issuing_authority": "State Pollution Control Board",
        "accepted_formats": ["PDF"],
        "max_size_mb": 10,
        "has_expiry": True,
        "default_validity_months": 24,
        "verification_method": "QR",
        "extraction_schema": [
            {"key": "consent_order_number", "label": "Consent Order Number", "type": "id", "required": True},
            {"key": "valid_upto", "label": "Valid Until Date", "type": "date", "required": True},
        ],
        "keywords": ["pollution", "consent", "operate", "cto", "spcb", "effluent", "environmental"],
    },
    {
        "code": "MUNICIPAL_NOC",
        "name": "Municipal Land & Infrastructure Clearance NOC",
        "description": "Civic NOC confirming absence of unauthorised construction or encroachments.",
        "issuing_authority": "Municipal Corporation Commissioner Office",
        "accepted_formats": ["PDF"],
        "max_size_mb": 10,
        "has_expiry": True,
        "default_validity_months": 36,
        "verification_method": "PORTAL",
        "extraction_schema": [
            {"key": "noc_reference_number", "label": "NOC Reference Number", "type": "id", "required": True},
            {"key": "valid_upto", "label": "Valid Until Date", "type": "date", "required": True},
        ],
        "keywords": ["municipal", "clearance", "encroachment", "civic", "corporation", "infrastructure"],
    },
    {
        "code": "NBA_ACCREDITATION",
        "name": "NBA Accreditation Status Certificate",
        "description": "Accreditation status notification issued by National Board of Accreditation.",
        "issuing_authority": "National Board of Accreditation New Delhi",
        "accepted_formats": ["PDF"],
        "max_size_mb": 10,
        "has_expiry": True,
        "default_validity_months": 36,
        "verification_method": "PORTAL",
        "extraction_schema": [
            {"key": "accreditation_number", "label": "Accreditation Ref Number", "type": "id", "required": True},
            {"key": "valid_upto", "label": "Valid Until Date", "type": "date", "required": True},
        ],
        "keywords": ["nba", "accreditation", "tier", "outcomes", "evaluator", "accredited"],
    },
    {
        "code": "FIRE_SAFETY_NOC",
        "name": "Fire Safety NOC & Life Protection Clearance",
        "description": "Life safety certificate issued by Chief Fire Officer.",
        "issuing_authority": "Chief Fire Officer Fire Prevention Wing",
        "accepted_formats": ["PDF"],
        "max_size_mb": 10,
        "has_expiry": True,
        "default_validity_months": 24,
        "verification_method": "QR",
        "extraction_schema": [
            {"key": "noc_number", "label": "Fire NOC Number", "type": "id", "required": True},
            {"key": "valid_upto", "label": "Valid Until Date", "type": "date", "required": True},
        ],
        "keywords": ["fire", "safety", "protection", "noc", "rescue", "hazard"],
    },
]


def seed_catalog_document_types(db: Session):
    """Inserts or updates the 14 standard DocumentTypes with rich keywords and schemas"""
    for dt_dict in DOCUMENT_TYPES_CATALOG:
        dt = db.query(DocumentType).filter(DocumentType.code == dt_dict["code"]).first()
        if not dt:
            dt = DocumentType(**dt_dict)
            db.add(dt)
        else:
            for k, v in dt_dict.items():
                setattr(dt, k, v)
    db.commit()
