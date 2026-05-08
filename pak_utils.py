"""Shared utilities for LCD5A PAK generation.

Constants, JPEG encoding, PAK binary format, font finding, brightness enhancement.
Import from here instead of duplicating across modules.
"""

import struct
from io import BytesIO
from PIL import Image, ImageEnhance, ImageFont

# Canvas: 1024x240. Bezel covers left ~224px.
# Visible area: x=224..1024, y=24..240 (800x216 effective)
CANVAS_W = 1024
CANVAS_H = 240
VISIBLE_X = 224
VISIBLE_Y = 24
VISIBLE_W = 800
VISIBLE_H = 216
CENTER_X = 624   # (224 + 1024) / 2
CENTER_Y = 132   # (24 + 240) / 2

PAK_MAGIC = b"JP"


def make_canvas(bg=(240, 240, 250)):
    return Image.new("RGB", (CANVAS_W, CANVAS_H), bg)


def find_font(size=60):
    for fp in [
        "C:/Windows/Fonts/msyh.ttc",
        "C:/Windows/Fonts/msyhbd.ttc",
        "C:/Windows/Fonts/simhei.ttf",
        "C:/Windows/Fonts/simsun.ttc",
        "C:/Windows/Fonts/arial.ttf",
    ]:
        try:
            return ImageFont.truetype(fp, size)
        except Exception:
            continue
    return ImageFont.load_default()


def enhance_for_lcd(img):
    """Boost brightness if image is too dark for the LCD (avg < 150 -> boost to ~180)."""
    pixels = list(img.getdata())
    n = len(pixels) * 3
    avg = sum(sum(p[:3]) for p in pixels) / max(n, 1)
    if avg < 150:
        factor = min(2.5, 180 / max(avg, 1))
        img = ImageEnhance.Brightness(img).enhance(factor)
    return img


def image_to_jpeg(img, quality=30, rotate=True):
    """Convert PIL Image to JPEG bytes. Rotates 180° by default (screen mount)."""
    if rotate:
        img = img.transpose(Image.ROTATE_180)
    buf = BytesIO()
    img.save(buf, format="JPEG", quality=quality)
    return buf.getvalue()


def build_pak(frames, quality=60, rotate=True):
    """Build PAK binary from list of PIL Image frames."""
    jpeg_bytes_list = [image_to_jpeg(f, quality=quality, rotate=rotate) for f in frames]
    return build_pak_from_jpeg_bytes(jpeg_bytes_list)


def _pack_frames(jpeg_bytes_list):
    """Low-level: pack JPEG bytes into PAK binary structure."""
    n = len(jpeg_bytes_list)
    header = PAK_MAGIC + struct.pack("<HI", n, 0x0C)
    header += b"\x00" * (n * 4)

    offset_table = b""
    frame_data = b""
    current_offset = len(header)

    for jpeg_data in jpeg_bytes_list:
        offset_table += struct.pack("<I", current_offset)
        entry = struct.pack("<I", len(jpeg_data)) + jpeg_data
        while len(entry) % 4 != 0:
            entry += b"\x00"
        frame_data += entry
        current_offset = len(header) + len(frame_data)

    return header[:8] + offset_table + frame_data


def build_pak_from_jpeg_bytes(jpeg_bytes_list, num_frames=None):
    """Build PAK from pre-compressed JPEG byte strings.

    If num_frames is specified and larger than len(jpeg_bytes_list),
    the existing frames are duplicated to reach num_frames.
    """
    if num_frames and num_frames > len(jpeg_bytes_list):
        repeat = num_frames // len(jpeg_bytes_list) + 1
        jpeg_bytes_list = (jpeg_bytes_list * repeat)[:num_frames]
    return _pack_frames(jpeg_bytes_list)
