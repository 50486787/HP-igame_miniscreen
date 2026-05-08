"""Convert multi-frame GIF to LCD5A PAK format.

Each GIF frame is extracted, rotated 180° (screen is mounted upside-down),
brightness-enhanced for the LCD panel, JPEG-compressed, and packed into
the native PAK container format.
"""

import struct
import argparse
import sys
import os
from io import BytesIO
from PIL import Image, ImageEnhance

CANVAS_W = 1024
CANVAS_H = 240
VISIBLE_X = 224
VISIBLE_Y = 24
VISIBLE_W = 800
VISIBLE_H = 216


def _enhance_for_lcd(img):
    """Boost brightness if image is too dark for the LCD panel."""
    pixels = list(img.getdata())
    n = len(pixels) * 3
    avg = sum(sum(p[:3]) for p in pixels) / max(n, 1)
    if avg < 150:
        factor = min(2.5, 180 / max(avg, 1))
        img = ImageEnhance.Brightness(img).enhance(factor)
    return img


def gif_to_frames(gif_path, canvas_w=CANVAS_W, canvas_h=CANVAS_H,
                  visible_w=VISIBLE_W, visible_h=VISIBLE_H,
                  visible_x=VISIBLE_X, visible_y=VISIBLE_Y,
                  quality=60, enhance=True, rotate=True):
    """Extract frames from GIF, return list of (jpeg_bytes, frame_count)."""
    gif = Image.open(gif_path)
    frames = []

    for i in range(gif.n_frames):
        gif.seek(i)
        # Convert palette/transparent frames to RGB
        frame = gif.convert("RGB")

        # Resize to fit visible area, then paste onto full canvas
        resized = frame.resize((visible_w, visible_h), Image.LANCZOS)
        canvas = Image.new("RGB", (canvas_w, canvas_h), (0, 0, 0))
        canvas.paste(resized, (visible_x, visible_y))

        if enhance:
            canvas = _enhance_for_lcd(canvas)
        if rotate:
            canvas = canvas.transpose(Image.ROTATE_180)

        buf = BytesIO()
        canvas.save(buf, format="JPEG", quality=quality)
        frames.append(buf.getvalue())

    return frames


def frames_to_pak(frames):
    """Build PAK binary from a list of JPEG frame byte strings."""
    n = len(frames)
    # Header: magic(2) + frame_count(2) + unknown(4) + offset_table(n*4)
    header = b"JP" + struct.pack("<HI", n, 0x0C)
    header += b"\x00" * (n * 4)

    offset_table = b""
    frame_data = b""
    current_offset = len(header)

    for jpeg_data in frames:
        offset_table += struct.pack("<I", current_offset)
        entry = struct.pack("<I", len(jpeg_data)) + jpeg_data
        while len(entry) % 4 != 0:
            entry += b"\x00"
        frame_data += entry
        current_offset = len(header) + len(frame_data)

    return header[:8] + offset_table + frame_data


def gif_to_pak(gif_path, pak_path, quality=60, enhance=True, rotate=True,
               canvas_w=CANVAS_W, canvas_h=CANVAS_H,
               visible_w=VISIBLE_W, visible_h=VISIBLE_H,
               visible_x=VISIBLE_X, visible_y=VISIBLE_Y):
    """Convert a GIF file to PAK format and save it."""
    frames = gif_to_frames(
        gif_path, canvas_w=canvas_w, canvas_h=canvas_h,
        visible_w=visible_w, visible_h=visible_h,
        visible_x=visible_x, visible_y=visible_y,
        quality=quality, enhance=enhance, rotate=rotate,
    )

    pak_data = frames_to_pak(frames)

    with open(pak_path, "wb") as f:
        f.write(pak_data)

    total_kb = sum(len(f) for f in frames) / 1024
    print(f"PAK: {pak_path}")
    print(f"  Frames: {len(frames)}")
    print(f"  JPEG data: {total_kb:.0f} KB")
    print(f"  PAK total: {len(pak_data) / 1024:.0f} KB")
    return pak_path


def main():
    parser = argparse.ArgumentParser(
        description="Convert GIF animation to LCD5A PAK format")
    parser.add_argument("gif", help="Input GIF file")
    parser.add_argument("pak", nargs="?", help="Output PAK file (default: <gif>.pak)")
    parser.add_argument("--quality", type=int, default=60,
                        help="JPEG quality (1-100, default: 60)")
    parser.add_argument("--no-enhance", action="store_true",
                        help="Skip brightness enhancement")
    parser.add_argument("--no-rotate", action="store_true",
                        help="Skip 180-degree rotation")
    parser.add_argument("--full-canvas", action="store_true",
                        help="Stretch to full 1024x240 instead of visible area")
    args = parser.parse_args()

    if not os.path.exists(args.gif):
        print(f"ERROR: File not found: {args.gif}")
        sys.exit(1)

    pak_path = args.pak or os.path.splitext(args.gif)[0] + ".pak"

    if args.full_canvas:
        gif_to_pak(args.gif, pak_path, quality=args.quality,
                   enhance=not args.no_enhance, rotate=not args.no_rotate,
                   visible_w=CANVAS_W, visible_h=CANVAS_H, visible_x=0, visible_y=0)
    else:
        gif_to_pak(args.gif, pak_path, quality=args.quality,
                   enhance=not args.no_enhance, rotate=not args.no_rotate)


if __name__ == "__main__":
    main()
