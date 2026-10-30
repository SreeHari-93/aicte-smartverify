import base64
import hashlib
import io
import random
import string
from datetime import datetime, timedelta, timezone
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from backend.app.config import settings


def hash_captcha_text(text: str) -> str:
    """Hash normalized (uppercase, stripped) captcha text with SHA-256"""
    clean_text = text.strip().upper()
    return hashlib.sha256(clean_text.encode("utf-8")).hexdigest()


def generate_captcha_image(text_length: int = 5) -> tuple[str, str]:
    """
    Generate distorted captcha image using Pillow.
    Returns: (text, base64_image_data_uri)
    """
    # Exclude ambiguous characters like 0, O, I, 1
    chars = "23456789ABCDEFGHJKLMNPQRSTUVWXYZ"
    text = "".join(random.choices(chars, k=text_length))

    width = 170
    height = 54
    # Light-grey noisy background
    bg_color = (random.randint(230, 245), random.randint(235, 248), random.randint(240, 252))
    img = Image.new("RGB", (width, height), color=bg_color)
    draw = ImageDraw.Draw(img)

    # 1. Background noise dots
    for _ in range(400):
        xy = (random.randint(0, width - 1), random.randint(0, height - 1))
        dot_color = (random.randint(180, 220), random.randint(180, 220), random.randint(180, 220))
        draw.point(xy, fill=dot_color)

    # 2. Random interference lines
    for _ in range(6):
        start = (random.randint(0, width), random.randint(0, height))
        end = (random.randint(0, width), random.randint(0, height))
        line_color = (random.randint(140, 200), random.randint(140, 200), random.randint(150, 210))
        draw.line([start, end], fill=line_color, width=random.randint(1, 2))

    # Load default font
    try:
        font = ImageFont.load_default(size=26)
    except TypeError:
        # For older Pillow versions that don't support size in load_default
        font = ImageFont.load_default()

    # Draw individual characters with slight rotation & positioning jitter
    char_spacing = (width - 30) // text_length
    for i, char in enumerate(text):
        x = 16 + i * char_spacing + random.randint(-3, 3)
        y = 12 + random.randint(-4, 4)

        char_img = Image.new("RGBA", (34, 38), (0, 0, 0, 0))
        char_draw = ImageDraw.Draw(char_img)
        # Deep navy / royal blue tones for high contrast & clarity
        char_color = (
            random.randint(11, 40),
            random.randint(40, 80),
            random.randint(120, 180),
            255,
        )
        char_draw.text((4, 2), char, font=font, fill=char_color)

        # Rotate character slightly (-15 to 15 degrees)
        angle = random.randint(-18, 18)
        rotated_char = char_img.rotate(angle, expand=True, resample=Image.BICUBIC)

        img.paste(rotated_char, (x, y), rotated_char)

    # 3. Add foreground wavy lines
    for _ in range(2):
        points = [
            (0, random.randint(10, height - 10)),
            (width // 3, random.randint(10, height - 10)),
            (2 * width // 3, random.randint(10, height - 10)),
            (width, random.randint(10, height - 10)),
        ]
        draw.line(points, fill=(245, 130, 32, 180), width=1)

    # Subtle smooth filter to blend noise
    img = img.filter(ImageFilter.SMOOTH_MORE)

    # Convert to base64
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    b64_str = base64.b64encode(buffer.getvalue()).decode("utf-8")
    data_uri = f"data:image/png;base64,{b64_str}"

    return text, data_uri

