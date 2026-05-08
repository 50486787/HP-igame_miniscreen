"""Convert multi-frame GIF to LCD5A PAK format.

Each GIF frame is extracted, rotated 180° (screen is mounted upside-down),
brightness-enhanced for the LCD panel, JPEG-compressed, and packed into
the native PAK container format.
"""

import argparse
import sys
import os
from PIL import Image
from pak_utils import (CANVAS_W, CANVAS_H, VISIBLE_X, VISIBLE_Y,
                       VISIBLE_W, VISIBLE_H, enhance_for_lcd,
                       build_pak)


def gif_to_frames(gif_path, canvas_w=CANVAS_W, canvas_h=CANVAS_H,
                  visible_w=VISIBLE_W, visible_h=VISIBLE_H,
                  visible_x=VISIBLE_X, visible_y=VISIBLE_Y,
                  quality=60, enhance=True, rotate=True):
    """Extract frames from GIF, return list of PIL Image frames."""
    gif = Image.open(gif_path)
    frames = []

    for i in range(gif.n_frames):
        gif.seek(i)
        frame = gif.convert("RGB")

        resized = frame.resize((visible_w, visible_h), Image.LANCZOS)
        canvas = Image.new("RGB", (canvas_w, canvas_h), (0, 0, 0))
        canvas.paste(resized, (visible_x, visible_y))

        if enhance:
            canvas = enhance_for_lcd(canvas)
        frames.append(canvas)

    return frames


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

    pak_data = build_pak(frames, quality=quality, rotate=rotate)

    with open(pak_path, "wb") as f:
        f.write(pak_data)

    print(f"PAK: {pak_path}")
    print(f"  Frames: {len(frames)}")
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
