import os
import shutil
import math
from PIL import Image, ImageDraw
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib import colors

ANOMALY_DEMO_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "../../../demo_data/anomaly")
)


def ensure_demo_dir():
    os.makedirs(ANOMALY_DEMO_DIR, exist_ok=True)


def generate_clean_sample() -> str:
    """
    Clean authentic NBA Accreditation Certificate.
    Distinct Theme: Double border frame with deep navy header block.
    """
    ensure_demo_dir()
    path = os.path.join(ANOMALY_DEMO_DIR, "clean_sample.pdf")
    c = canvas.Canvas(path, pagesize=letter)
    c.setTitle("Certificate of Accreditation")
    c.setAuthor("National Board of Accreditation")
    c.setCreator("National Board of Accreditation Portal System")
    c.setProducer("ReportLab PDF Library")

    # Double decorative border
    c.setStrokeColor(colors.HexColor("#0f2942"))
    c.setLineWidth(2)
    c.rect(30, 30, 552, 732, stroke=1, fill=0)
    c.setLineWidth(1)
    c.rect(36, 36, 540, 720, stroke=1, fill=0)

    # Deep Navy Header Banner
    c.setFillColor(colors.HexColor("#0f2942"))
    c.rect(36, 680, 540, 60, fill=1, stroke=0)

    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 15)
    c.drawCentredString(306, 715, "NATIONAL BOARD OF ACCREDITATION")
    c.setFont("Helvetica", 11)
    c.drawCentredString(306, 695, "Certificate of Statutory Accreditation")

    # Body Content
    c.setFillColor(colors.black)
    c.setFont("Helvetica-Bold", 11)
    c.drawString(60, 640, "Institution Profile:")
    c.setFont("Helvetica", 10)
    c.drawString(60, 620, "Sri Krishna College of Engineering and Technology")
    c.drawString(60, 600, "AICTE Permanent ID: SKCET01 | State: Tamil Nadu")
    c.drawString(60, 580, "Accredited Programme: Computer Science and Engineering (UG)")
    c.drawString(60, 560, "Certificate Identifier: NBA-2024-SKCET-001")
    c.drawString(60, 540, "Date of Issuance: 2026-10-28")
    c.drawString(60, 520, "Statutory Expiry Date: 2029-10-27")

    c.setFont("Helvetica-Oblique", 9)
    c.drawString(60, 470, "This statutory credential confirms compliance with apex engineering council criteria.")

    # Authentic Council Seal Outline (Lower Right)
    c.setStrokeColor(colors.HexColor("#d97706"))
    c.setLineWidth(2)
    c.circle(480, 550, 36, stroke=1, fill=0)
    c.circle(480, 550, 30, stroke=1, fill=0)
    c.setFont("Helvetica-Bold", 7)
    c.setFillColor(colors.HexColor("#d97706"))
    c.drawCentredString(480, 553, "NBA STATUTORY")
    c.drawCentredString(480, 543, "VERIFIED SEAL")

    c.showPage()
    c.save()
    return path


def generate_edited_date_sample() -> str:
    """
    Fire Department NOC with anomalous dates.
    Distinct Theme: Full-width crimson top band, vertical left safety stripe, and badge.
    """
    ensure_demo_dir()
    path = os.path.join(ANOMALY_DEMO_DIR, "edited_date_sample.pdf")
    c = canvas.Canvas(path, pagesize=letter)
    c.setTitle("Fire Safety No Objection Certificate")
    c.setAuthor("State Fire and Rescue Services")
    c.setCreator("Fire Department Portal")
    c.setProducer("ReportLab PDF Library")

    # Crimson Top Band
    c.setFillColor(colors.HexColor("#991b1b"))
    c.rect(0, 715, 612, 77, fill=1, stroke=0)

    # Left Safety Stripe
    c.setFillColor(colors.HexColor("#dc2626"))
    c.rect(0, 0, 24, 715, fill=1, stroke=0)

    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 14)
    c.drawCentredString(318, 755, "DEPARTMENT OF FIRE AND RESCUE SERVICES")
    c.setFont("Helvetica", 10)
    c.drawCentredString(318, 735, "Government Statutory Fire Compliance Certification")

    # Gold Status Badge
    c.setFillColor(colors.HexColor("#fef3c7"))
    c.setStrokeColor(colors.HexColor("#d97706"))
    c.roundRect(60, 655, 180, 30, 4, fill=1, stroke=1)
    c.setFillColor(colors.HexColor("#92400e"))
    c.setFont("Helvetica-Bold", 9)
    c.drawCentredString(150, 666, "STATUTORY CLEARANCE")

    # Details
    c.setFillColor(colors.black)
    c.setFont("Helvetica", 10)
    c.drawString(60, 620, "Facility: Sri Krishna College of Engineering and Technology")
    c.drawString(60, 600, "AICTE ID: SKCET01 | Campus Block: Main Instructional Complex")
    c.drawString(60, 580, "NOC Reference No: FIRE-NOC-2026-99")
    # Date Anomaly: Issue date after expiry & future date
    c.drawString(60, 550, "Date of Issuance: 2027-01-10")
    c.drawString(60, 530, "Statutory Expiry Date: 2025-06-30")
    c.drawString(60, 490, "Inspection notes: All hydrants and emergency stairwells reviewed.")

    c.showPage()
    c.save()
    return path


def generate_duplicate_sample(source_clean_path: str) -> str:
    """
    Intended duplicate copy matching clean_sample.pdf byte-for-byte.
    """
    ensure_demo_dir()
    path = os.path.join(ANOMALY_DEMO_DIR, "duplicate_sample.pdf")
    shutil.copyfile(source_clean_path, path)
    return path


def generate_tampered_stamp_sample() -> str:
    """
    DTCP Building Plan with visual copy-move cloned seals.
    Distinct Theme: Landscape blueprint layout with dark blue sidebar and light grid.
    """
    ensure_demo_dir()
    path = os.path.join(ANOMALY_DEMO_DIR, "tampered_stamp_sample.pdf")

    # 792 x 612 Landscape Image
    width, height = 792, 612
    img = Image.new("RGB", (width, height), (248, 250, 252))
    draw = ImageDraw.Draw(img)

    # Dark blue left architectural panel
    draw.rectangle([0, 0, 160, height], fill=(30, 58, 138))
    draw.text((20, 40), "DTCP\nAPPROVALS", fill=(255, 255, 255))
    draw.text((20, 120), "ARCHITECTURAL\nSERVICES WING", fill=(191, 219, 254))

    # Grid lines on blueprint workspace
    for gx in range(180, width, 40):
        draw.line([gx, 0, gx, height], fill=(226, 232, 240), width=1)
    for gy in range(0, height, 40):
        draw.line([160, gy, width, gy], fill=(226, 232, 240), width=1)

    # Header Box
    draw.rectangle([180, 30, 760, 90], fill=(255, 255, 255), outline=(15, 23, 42), width=1)
    draw.text((200, 45), "DIRECTORATE OF TOWN AND COUNTRY PLANNING", fill=(15, 23, 42))
    draw.text((200, 65), "Institutional Infrastructure Sanction: DTCP-BLDG-2024-554", fill=(71, 85, 105))

    # Details Box
    draw.rectangle([180, 110, 760, 200], fill=(255, 255, 255), outline=(148, 163, 184), width=1)
    draw.text((200, 125), "Applicant: Sri Krishna College of Engineering and Technology (AICTE SKCET01)", fill=(15, 23, 42))
    draw.text((200, 145), "Issue Date: 2024-03-20 | Expiry Date: 2029-03-19", fill=(15, 23, 42))
    draw.text((200, 165), "Instructional Built-Up Carpet Area: 42,500 Sq. Meters", fill=(15, 23, 42))

    # Generate a rich circular seal with distinctive features for ORB detection
    seal_size = 140
    seal = Image.new("RGBA", (seal_size, seal_size), (255, 255, 255, 0))
    s_draw = ImageDraw.Draw(seal)

    # Concentric circles
    s_draw.ellipse([6, 6, seal_size - 6, seal_size - 6], outline=(180, 83, 9, 255), width=3)
    s_draw.ellipse([14, 14, seal_size - 14, seal_size - 14], outline=(180, 83, 9, 255), width=1)
    s_draw.ellipse([26, 26, seal_size - 26, seal_size - 26], outline=(180, 83, 9, 255), width=2)

    cx, cy = seal_size // 2, seal_size // 2
    for angle in range(0, 360, 30):
        rad = math.radians(angle)
        x1 = cx + int(34 * math.cos(rad))
        y1 = cy + int(34 * math.sin(rad))
        x2 = cx + int(46 * math.cos(rad))
        y2 = cy + int(46 * math.sin(rad))
        s_draw.line([x1, y1, x2, y2], fill=(180, 83, 9, 255), width=2)

    s_draw.text((cx - 24, cy - 8), "* SANCTION *", fill=(180, 83, 9, 255))
    s_draw.text((cx - 22, cy + 6), "GOVT OF TN", fill=(180, 83, 9, 255))

    # Paste stamp at Position A
    img.paste(seal, (220, 200), seal)
    # Copy-Move: Paste the identical stamp at Position B (spatially separated diagonally)
    img.paste(seal, (520, 380), seal)

    # Save as PDF
    img.save(path, "PDF", resolution=100.0)
    return path


def generate_suspicious_metadata_sample() -> str:
    """
    Land Title Deed created via Adobe Photoshop / Canva with post-dated creation.
    Distinct Theme: Forest green header ribbon, double inner boxes, and land table.
    """
    ensure_demo_dir()
    path = os.path.join(ANOMALY_DEMO_DIR, "suspicious_metadata_sample.pdf")
    c = canvas.Canvas(path, pagesize=letter)
    c.setTitle("Revenue Administration Land Title Certificate")
    c.setAuthor("Freelance Graphics Designer")
    c.setCreator("Adobe Photoshop CC 2023 (Windows)")
    c.setProducer("Canva Web PDF Export Engine")

    # Green Header Ribbon
    c.setFillColor(colors.HexColor("#14532d"))
    c.rect(40, 700, 532, 55, fill=1, stroke=0)

    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 14)
    c.drawCentredString(306, 735, "REVENUE ADMINISTRATION DEPARTMENT")
    c.setFont("Helvetica", 10)
    c.drawCentredString(306, 715, "Official Institutional Land Title & Possession Certificate")

    # Two distinct gray info cards
    c.setFillColor(colors.HexColor("#f0fdf4"))
    c.setStrokeColor(colors.HexColor("#16a34a"))
    c.roundRect(40, 520, 532, 160, 6, fill=1, stroke=1)

    c.setFillColor(colors.HexColor("#166534"))
    c.setFont("Helvetica-Bold", 11)
    c.drawString(60, 650, "Statutory Land Parcel Record:")

    c.setFillColor(colors.black)
    c.setFont("Helvetica", 10)
    c.drawString(60, 625, "Registered Holder: Sri Krishna College of Engineering and Technology")
    c.drawString(60, 605, "AICTE Permanent ID: SKCET01 | District: Coimbatore")
    c.drawString(60, 585, "Title Reference Number: LAND-REG-2021-008")
    # Date issued in 2021, but PDF created in 2026
    c.drawString(60, 560, "Date of Statutory Issue: 2021-03-01")
    c.drawString(60, 540, "Perpetual Title Validity: 2099-12-31")

    # Lower Parcel Table
    c.setFillColor(colors.HexColor("#f8fafc"))
    c.setStrokeColor(colors.HexColor("#cbd5e1"))
    c.rect(40, 420, 532, 80, fill=1, stroke=1)
    c.setFillColor(colors.black)
    c.setFont("Helvetica-Bold", 9)
    c.drawString(60, 480, "Survey Nos: 42/1A, 42/1B, 43/2")
    c.setFont("Helvetica", 9)
    c.drawString(60, 460, "Contiguous Land Area: 15.25 Acres (Single Contiguous Parcel)")
    c.drawString(60, 440, "Zoning Classification: Educational / Instructional Public Utility")

    c.showPage()
    c.save()
    return path


def generate_conflict_sample() -> str:
    """
    Statutory credential for simulated external authority conflict (MISMATCH_DETECTED).
    Distinct Theme: Purple header banner, amber warning frame, unique cert identifier.
    """
    ensure_demo_dir()
    path = os.path.join(ANOMALY_DEMO_DIR, "conflict_sample.pdf")
    c = canvas.Canvas(path, pagesize=letter)
    c.setTitle("Statutory Council Compliance Filing")
    c.setAuthor("National Board of Accreditation")
    c.setCreator("NBA Registry System")
    c.setProducer("ReportLab PDF Library")

    # Purple Header Banner
    c.setFillColor(colors.HexColor("#581c87"))
    c.rect(30, 690, 552, 60, fill=1, stroke=0)

    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 14)
    c.drawCentredString(306, 725, "NATIONAL STATUTORY ACCREDITATION COUNCIL")
    c.setFont("Helvetica", 10)
    c.drawCentredString(306, 705, "Special Verification Registry Docket")

    # Amber Framed Card
    c.setFillColor(colors.HexColor("#fffbeb"))
    c.setStrokeColor(colors.HexColor("#b45309"))
    c.rect(40, 500, 532, 160, fill=1, stroke=1)

    c.setFillColor(colors.HexColor("#78350f"))
    c.setFont("Helvetica-Bold", 11)
    c.drawString(60, 630, "Compliance Docket Credentials:")

    c.setFillColor(colors.black)
    c.setFont("Helvetica", 10)
    c.drawString(60, 605, "Institution: Sri Krishna College of Engineering and Technology")
    c.drawString(60, 585, "Filing Reference Number: NBA-CONF-999")
    c.drawString(60, 565, "Date of Issuance: 2026-10-28")
    c.drawString(60, 545, "Statutory Expiry: 2029-10-27")
    c.drawString(60, 520, "Status: Under Active Scrutiny Verification")

    c.showPage()
    c.save()
    return path


def generate_all_samples() -> dict:
    ensure_demo_dir()
    clean_p = generate_clean_sample()
    date_p = generate_edited_date_sample()
    dup_p = generate_duplicate_sample(clean_p)
    tamper_p = generate_tampered_stamp_sample()
    meta_p = generate_suspicious_metadata_sample()
    conflict_p = generate_conflict_sample()

    return {
        "clean": clean_p,
        "edited_date": date_p,
        "duplicate": dup_p,
        "tampered_stamp": tamper_p,
        "suspicious_metadata": meta_p,
        "conflict": conflict_p,
    }
