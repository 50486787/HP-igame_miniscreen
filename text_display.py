"""Display text/numbers on LCD5A screen - generates PAK and uploads."""
from PIL import Image, ImageDraw, ImageFont
import sys
from pak_utils import (CANVAS_W, CANVAS_H, VISIBLE_X, CENTER_X, CENTER_Y,
                       find_font, build_pak_from_jpeg_bytes, image_to_jpeg)


def text_to_pak(text, pak_path, font_size=60, color=(255, 255, 255),
                bg=(30, 30, 30), quality=30):
    """Create a single-frame PAK from text, centered for LCD5A display."""
    img = Image.new("RGB", (CANVAS_W, CANVAS_H), bg)
    draw = ImageDraw.Draw(img)
    font = find_font(font_size)

    lines = text.replace("\\n", "\n").split("\n")
    if not lines:
        lines = [""]

    line_spacing = font_size + 12

    for i, line in enumerate(lines):
        y = CENTER_Y + (i - (len(lines) - 1) / 2.0) * line_spacing
        draw.text((CENTER_X, int(y)), line, fill=color, font=font, anchor="mm")

    jpeg = image_to_jpeg(img, quality=quality)
    pak_data = build_pak_from_jpeg_bytes([jpeg], num_frames=3)

    with open(pak_path, "wb") as f:
        f.write(pak_data)

    print(f"PAK: {pak_path} ({len(pak_data)} bytes, "
          f"\"{text[:50]}{'...' if len(text) > 50 else ''}\")")
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
    bg_color = (30, 30, 30)

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
                bg_color = tuple(int(p) for p in parts)

    text_to_pak(text, pak_path, font_size=font_size, color=fg, bg=bg_color)
