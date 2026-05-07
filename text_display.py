"""Display text/numbers on LCD5A screen - generates PAK and uploads."""
from PIL import Image, ImageDraw, ImageFont
import struct
import sys
import os
from io import BytesIO


def text_to_pak(text, pak_path, width=1024, height=240, font_size=60,
                color=(255, 255, 255), bg=(30, 30, 30), quality=30):
    """Create a single-frame PAK from text. Device LCD is physically rotated 180,
    so we draw normally then rotate before encoding."""
    img = Image.new("RGB", (width, height), bg)
    draw = ImageDraw.Draw(img)

    # Try fonts: prefer Chinese-capable
    font = None
    for font_path in [
        "C:/Windows/Fonts/msyh.ttc",
        "C:/Windows/Fonts/msyhbd.ttc",
        "C:/Windows/Fonts/simhei.ttf",
        "C:/Windows/Fonts/simsun.ttc",
        "C:/Windows/Fonts/arial.ttf",
        "C:/Windows/Fonts/consola.ttf",
    ]:
        try:
            font = ImageFont.truetype(font_path, font_size)
            break
        except Exception:
            continue
    if font is None:
        font = ImageFont.load_default()

    # Handle \n line breaks
    lines = text.replace("\\n", "\n").split("\n")
    if not lines:
        lines = [""]

    # Measure each line
    line_heights = []
    max_line_w = 0
    max_width = width - 40
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        lw = bbox[2] - bbox[0]
        lh = bbox[3] - bbox[1]
        line_heights.append(lh)
        if lw > max_line_w:
            max_line_w = lw

    line_spacing = font_size + 12
    total_text_h = len(lines) * line_spacing - (line_spacing - line_heights[0] if lines else 0)
    start_y = (height - total_text_h) // 2

    # Visual center (bezel covers ~240px on left side)
    center_x = 620

    for i, line in enumerate(lines):
        bbox = draw.textbbox((0, 0), line, font=font)
        tw = bbox[2] - bbox[0]
        x = center_x - tw // 2
        y = start_y + i * line_spacing
        draw.text((x, y), line, fill=color, font=font)

    # Device LCD is mounted 180-degree rotated, so flip both axes
    img = img.transpose(Image.ROTATE_180)

    # Encode as JPEG
    buf = BytesIO()
    img.save(buf, format="JPEG", quality=quality)
    jpeg_data = buf.getvalue()

    # Build PAK with a few duplicate frames
    num_frames = 3
    header = b"JP" + struct.pack("<HI", num_frames, 0x0C)
    header += b"\x00" * (num_frames * 4)

    offset_table = b""
    frame_data = b""
    current_offset = len(header)

    for _ in range(num_frames):
        offset_table += struct.pack("<I", current_offset)
        entry = struct.pack("<I", len(jpeg_data)) + jpeg_data
        while len(entry) % 4 != 0:
            entry += b"\x00"
        frame_data += entry
        current_offset = len(header) + len(frame_data)

    pak_data = header[:8] + offset_table + frame_data

    with open(pak_path, "wb") as f:
        f.write(pak_data)

    print(f"PAK: {pak_path} ({len(pak_data)} bytes, \"{text[:50]}{'...' if len(text)>50 else ''}\")")
    return True


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: text_display.py <text> [output.pak] [--size N] [--color R,G,B]")
        print("  Use \\n for line breaks")
        sys.exit(1)

    text = sys.argv[1]
    pak_path = sys.argv[2] if len(sys.argv) > 2 else "text_display.pak"
    font_size = 60
    fg = (255, 255, 255)
    bg = (30, 30, 30)

    args = sys.argv[3:]
    for j, a in enumerate(args):
        if a == "--size" and j + 1 < len(args):
            font_size = int(args[j + 1])
        elif a == "--color" and j + 1 < len(args):
            parts = args[j + 1].split(",")
            if len(parts) == 3:
                fg = tuple(int(p) for p in parts)
        elif a == "--bg" and j + 1 < len(args):
            parts = args[j + 1].split(",")
            if len(parts) == 3:
                bg = tuple(int(p) for p in parts)

    text_to_pak(text, pak_path, font_size=font_size, color=fg, bg=bg)
