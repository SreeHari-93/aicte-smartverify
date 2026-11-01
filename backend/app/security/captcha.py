import base64
import hashlib
import io
import random
from datetime import datetime, timezone
from PIL import Image, ImageDraw, ImageFont


def hash_captcha_text(text: str) -> str:
    """Hash normalized (uppercase, stripped, no whitespace) captcha text with SHA-256"""
    clean_text = text.strip().replace(" ", "").upper()
    return hashlib.sha256(clean_text.encode("utf-8")).hexdigest()


def generate_captcha_image(text_length: int = 5) -> tuple[str, str]:
    """
    Generate clean, high-contrast, crystal-clear captcha image using Pillow.
    Uses unambiguous characters and bold font for 100% human legibility.
    Returns: (text, base64_image_data_uri)
    """
    # Clean, unambiguous characters (avoid 0/O/Q/D, 1/I/L, 8/B, S/5, Z/2, G/6)
    chars = "2345679ACEFHKMNPRTWXY"
    text = "".join(random.choices(chars, k=text_length))

    width = 220
    height = 54
    # Clean light background (slate-50)
    img = Image.new("RGB", (width, height), color=(248, 250, 252))
    draw = ImageDraw.Draw(img)

    # 1. Subtle, clean reference guide lines (light slate)
    for y_pos in [14, 27, 40]:
        draw.line([(0, y_pos), (width, y_pos)], fill=(226, 232, 240), width=1)
    for x_pos in [44, 88, 132, 176]:
        draw.line([(x_pos, 0), (x_pos, height)], fill=(238, 242, 246), width=1)

    # 2. Try loading bold TrueType fonts with fallbacks
    font = None
    for fn in ["arialbd.ttf", "arial.ttf", "calibrib.ttf", "calibri.ttf", "DejaVuSans-Bold.ttf", "DejaVuSans.ttf"]:
        try:
            font = ImageFont.truetype(fn, 32)
            break
        except Exception:
            continue
    if font is None:
        try:
            font = ImageFont.load_default(size=28)
        except TypeError:
            font = ImageFont.load_default()

    # 3. Draw each character clearly with even spacing and high contrast
    char_spacing = (width - 40) // text_length
    for i, char in enumerate(text):
        x = 22 + i * char_spacing + random.randint(-1, 1)
        y = 10 + random.randint(-2, 2)

        # High-contrast official navy tones (clearly readable against slate-50)
        char_color = (
            random.randint(11, 25),
            random.randint(50, 75),
            random.randint(145, 175),
        )
        draw.text((x, y), char, font=font, fill=char_color)

    # 4. Convert to base64 PNG data URI
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    b64_str = base64.b64encode(buffer.getvalue()).decode("utf-8")
    data_uri = f"data:image/png;base64,{b64_str}"

    return text, data_uri

