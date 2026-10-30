import os
import shutil
import math
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

ANOMALY_DEMO_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "../../../demo_data/anomaly")
)


def ensure_demo_dir():
    os.makedirs(ANOMALY_DEMO_DIR, exist_ok=True)


def generate_clean_sample() -> str:
    ensure_demo_dir()
    path = os.path.join(ANOMALY_DEMO_DIR, "clean_sample.pdf")
    c = canvas.Canvas(path, pagesize=letter)
    c.setTitle("Certificate of Accreditation")
    c.setAuthor("National Board of Accreditation")
    c.setCreator("National Board of Accreditation Portal System")
    c.setProducer("ReportLab PDF Library")

    c.setFont("Helvetica-Bold", 16)
    c.drawCentredString(300, 720, "NATIONAL BOARD OF ACCREDITATION")
    c.setFont("Helvetica", 12)
    c.drawCentredString(300, 695, "Certificate of Statutory Accreditation")

    c.setFont("Helvetica", 10)
    c.drawString(72, 640, "Institution: Sri Krishna College of Engineering and Technology")
    c.drawString(72, 620, "AICTE Permanent ID: SKCET01")
    c.drawString(72, 600, "Programme: Computer Science and Engineering (UG)")
    c.drawString(72, 580, "Certificate Number: NBA-2024-SKCET-001")
    c.drawString(72, 560, "Date of Issue: 2026-10-28")
    c.drawString(72, 540, "Valid Upto: 2029-10-27")
    c.drawString(72, 500, "This is to certify that the specified technical education program meets")
    c.drawString(72, 485, "all quality benchmarks as established by the statutory council.")

    # Single authentic seal outline
    c.circle(480, 560, 40)
    c.setFont("Helvetica", 8)
    c.drawCentredString(480, 560, "NBA OFFICIAL")
    c.drawCentredString(480, 548, "COUNCIL SEAL")

    c.showPage()
    c.save()
    return path


def generate_edited_date_sample() -> str:
    ensure_demo_dir()
    path = os.path.join(ANOMALY_DEMO_DIR, "edited_date_sample.pdf")
    c = canvas.Canvas(path, pagesize=letter)
    c.setTitle("Fire Safety No Objection Certificate")
    c.setAuthor("State Fire and Rescue Services")
    c.setCreator("Fire Department Portal")
    c.setProducer("ReportLab PDF Library")

    c.setFont("Helvetica-Bold", 16)
    c.drawCentredString(300, 720, "DEPARTMENT OF FIRE AND RESCUE SERVICES")
    c.setFont("Helvetica", 12)
    c.drawCentredString(300, 695, "Statutory Fire Safety Compliance Certificate")

    c.setFont("Helvetica", 10)
    c.drawString(72, 640, "Institution: Sri Krishna College of Engineering and Technology")
    c.drawString(72, 620, "AICTE Permanent ID: SKCET01")
    c.drawString(72, 600, "Certificate Number: FIRE-NOC-2026-99")
    # Date anomaly: Issue date after expiry date & future date
    c.drawString(72, 580, "Date of Issue: 2027-01-10")
    c.drawString(72, 560, "Valid Upto: 2025-06-30")
    c.drawString(72, 520, "Premises inspected and cleared for institutional instructional occupancy.")

    c.showPage()
    c.save()
    return path


def generate_duplicate_sample(source_clean_path: str) -> str:
    ensure_demo_dir()
    path = os.path.join(ANOMALY_DEMO_DIR, "duplicate_sample.pdf")
    shutil.copyfile(source_clean_path, path)
    return path


def generate_tampered_stamp_sample() -> str:
    ensure_demo_dir()
    path = os.path.join(ANOMALY_DEMO_DIR, "tampered_stamp_sample.pdf")

    # Create base white document image
    img = Image.new("RGB", (612, 792), (255, 255, 255))
    draw = ImageDraw.Draw(img)

    # Draw document header and text
    draw.text((72, 60), "TOWN AND COUNTRY PLANNING AUTHORITY", fill=(0, 0, 0))
    draw.text((72, 85), "Approved Institutional Building Plan & Layout", fill=(60, 60, 60))
    draw.text((72, 130), "Institution: Sri Krishna College of Engineering and Technology", fill=(0, 0, 0))
    draw.text((72, 155), "AICTE Permanent ID: SKCET01", fill=(0, 0, 0))
    draw.text((72, 180), "Approval No: DTCP-BLDG-2024-554", fill=(0, 0, 0))
    draw.text((72, 205), "Date of Issue: 2024-03-20", fill=(0, 0, 0))
    draw.text((72, 230), "Valid Upto: 2029-03-19", fill=(0, 0, 0))

    # Generate a rich circular seal with distinctive features for ORB detection
    seal_size = 140
    seal = Image.new("RGBA", (seal_size, seal_size), (255, 255, 255, 0))
    s_draw = ImageDraw.Draw(seal)

    # Concentric circles
    s_draw.ellipse([6, 6, seal_size - 6, seal_size - 6], outline=(30, 64, 175, 255), width=3)
    s_draw.ellipse([14, 14, seal_size - 14, seal_size - 14], outline=(30, 64, 175, 255), width=1)
    s_draw.ellipse([26, 26, seal_size - 26, seal_size - 26], outline=(30, 64, 175, 255), width=2)

    # Cross pattern and stars
    cx, cy = seal_size // 2, seal_size // 2
    for angle in range(0, 360, 30):
        rad = math.radians(angle)
        x1 = cx + int(36 * math.cos(rad))
        y1 = cy + int(36 * math.sin(rad))
        x2 = cx + int(48 * math.cos(rad))
        y2 = cy + int(48 * math.sin(rad))
        s_draw.line([x1, y1, x2, y2], fill=(30, 64, 175, 255), width=2)

    s_draw.text((cx - 24, cy - 8), "* APPROVED *", fill=(30, 64, 175, 255))
    s_draw.text((cx - 22, cy + 6), "GOVT OF TN", fill=(30, 64, 175, 255))

    # Paste stamp at Position A
    img.paste(seal, (80, 340), seal)
    # Copy-Move: Paste the identical stamp at Position B (spatially separated)
    img.paste(seal, (380, 520), seal)

    # Save as PDF
    img.save(path, "PDF", resolution=100.0)
    return path


def generate_suspicious_metadata_sample() -> str:
    ensure_demo_dir()
    path = os.path.join(ANOMALY_DEMO_DIR, "suspicious_metadata_sample.pdf")
    c = canvas.Canvas(path, pagesize=letter)
    c.setTitle("Revenue Department Land Title Certificate")
    c.setAuthor("Freelance Graphics Designer")
    c.setCreator("Adobe Photoshop CC 2023 (Windows)")
    c.setProducer("Canva Web PDF Export Engine")

    c.setFont("Helvetica-Bold", 16)
    c.drawCentredString(300, 720, "REVENUE ADMINISTRATION DEPARTMENT")
    c.setFont("Helvetica", 12)
    c.drawCentredString(300, 695, "Certificate of Land Title and Possession")

    c.setFont("Helvetica", 10)
    c.drawString(72, 640, "Institution: Sri Krishna College of Engineering and Technology")
    c.drawString(72, 620, "AICTE Permanent ID: SKCET01")
    c.drawString(72, 600, "Certificate Number: LAND-REG-2021-008")
    # Date issued 5 years ago, but PDF generated recently
    c.drawString(72, 580, "Date of Issue: 2021-03-01")
    c.drawString(72, 560, "Valid Upto: 2099-12-31")
    c.drawString(72, 520, "Land Survey Numbers: 42/1A, 42/1B, 43/2, total area 15.25 Acres.")

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

    return {
        "clean": clean_p,
        "edited_date": date_p,
        "duplicate": dup_p,
        "tampered_stamp": tamper_p,
        "suspicious_metadata": meta_p,
    }
