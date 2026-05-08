"""Generate a pixel-art cat animation for the LCD5A mini screen.

The cat walks, sits, blinks, and wags its tail across ~30 frames.
Output can be GIF (for preview) or PAK (for direct upload).
"""

import argparse
import os
import math
import struct
from io import BytesIO
from PIL import Image, ImageDraw

VISIBLE_W = 800
VISIBLE_H = 216
BG = (40, 42, 54)       # dark background
CAT_BODY = (255, 180, 100)
CAT_DARK = (200, 130, 60)
CAT_WHITE = (255, 255, 255)
CAT_EYE = (40, 40, 40)
CAT_NOSE = (255, 120, 120)
GROUND_Y = 180
GROUND_COLOR = (60, 62, 74)


def draw_cat(draw, cx, cy, leg_phase, tail_phase, blink=0):
    """Draw a cat centered at (cx, cy). leg_phase: 0.0-1.0 walk cycle."""
    # ── body ──
    body_w, body_h = 60, 32
    bx, by = cx - body_w // 2, cy - 8
    draw.rounded_rectangle([bx, by, bx + body_w, by + body_h], radius=14,
                           fill=CAT_BODY)

    # ── head ──
    head_r = 22
    hx, hy = cx + 18, cy - 22
    draw.ellipse([hx - head_r, hy - head_r, hx + head_r, hy + head_r],
                 fill=CAT_BODY)

    # ── ears ──
    ear_h = 16
    draw.polygon([(hx - 14, hy - 10), (hx - 18, hy - ear_h), (hx - 2, hy - 12)],
                 fill=CAT_BODY)
    draw.polygon([(hx + 2, hy - 12), (hx + 18, hy - ear_h), (hx + 14, hy - 10)],
                 fill=CAT_BODY)
    # Inner ears
    draw.polygon([(hx - 11, hy - 11), (hx - 14, hy - ear_h + 4), (hx - 4, hy - 12)],
                 fill=CAT_DARK)
    draw.polygon([(hx + 4, hy - 12), (hx + 14, hy - ear_h + 4), (hx + 11, hy - 11)],
                 fill=CAT_DARK)

    # ── eyes ──
    eye_y = hy - 4
    if blink < 0.8:
        draw.ellipse([hx - 9, eye_y - 5, hx - 1, eye_y + 5], fill=CAT_WHITE)
        draw.ellipse([hx + 1, eye_y - 5, hx + 9, eye_y + 5], fill=CAT_WHITE)
        pupil_r = 3
        draw.ellipse([hx - 6, eye_y - 2, hx - 3, eye_y + 3], fill=CAT_EYE)
        draw.ellipse([hx + 3, eye_y - 2, hx + 6, eye_y + 3], fill=CAT_EYE)
    else:
        # blinking
        for dx in [-7, 3]:
            draw.line([(hx + dx - 3, eye_y), (hx + dx + 3, eye_y)],
                      fill=CAT_EYE, width=2)

    # ── nose & mouth ──
    draw.ellipse([hx - 3, hy + 4, hx + 3, hy + 9], fill=CAT_NOSE)
    draw.line([(hx, hy + 9), (hx, hy + 14)], fill=CAT_DARK, width=1)
    draw.arc([hx - 8, hy + 8, hx, hy + 18], start=0, end=180,
             fill=CAT_DARK, width=1)
    draw.arc([hx, hy + 8, hx + 8, hy + 18], start=0, end=180,
             fill=CAT_DARK, width=1)

    # ── whiskers ──
    for side, sx in [(-1, hx - 10), (1, hx + 10)]:
        for wy in [hy + 6, hy + 10]:
            draw.line([(sx, wy), (sx + side * 16, wy - 4)], fill=CAT_WHITE, width=1)
            draw.line([(sx, wy + 2), (sx + side * 16, wy + 2)], fill=CAT_WHITE, width=1)

    # ── legs ──
    leg_w, leg_h = 10, 18
    cycle = leg_phase * 2 * math.pi
    front_angle = math.sin(cycle) * 12
    back_angle = math.sin(cycle + math.pi) * 10

    # Front legs
    for lx, la in [(bx + 14, front_angle), (bx + 28, -front_angle)]:
        l_top = by + body_h - 2
        l_bottom_x = lx + int(la * 0.5)
        l_bottom_y = GROUND_Y
        draw.rounded_rectangle(
            [lx - leg_w // 2, l_top, lx + leg_w // 2, l_bottom_y],
            radius=5, fill=CAT_BODY)
        draw.ellipse([l_bottom_x - 6, l_bottom_y - 4, l_bottom_x + 6,
                      l_bottom_y + 4], fill=CAT_BODY)

    # Back legs
    for lx, la in [(bx + body_w - 14, back_angle), (bx + body_w - 28, -back_angle)]:
        l_top = by + body_h - 2
        l_bottom_x = lx + int(la * 0.5)
        l_bottom_y = GROUND_Y
        draw.rounded_rectangle(
            [lx - leg_w // 2, l_top, lx + leg_w // 2, l_bottom_y],
            radius=5, fill=CAT_DARK)
        draw.ellipse([l_bottom_x - 6, l_bottom_y - 4, l_bottom_x + 6,
                      l_bottom_y + 4], fill=CAT_DARK)

    # ── tail ──
    tail_base_x = bx - 4
    tail_base_y = by + 6
    tail_wag = math.sin(tail_phase * 2 * math.pi) * 30
    tail_points = [
        (tail_base_x, tail_base_y),
        (tail_base_x - 16, tail_base_y - 14 + tail_wag * 0.3),
        (tail_base_x - 28, tail_base_y - 22 + tail_wag * 0.6),
        (tail_base_x - 24, tail_base_y - 36 + tail_wag),
    ]
    draw.line(tail_points, fill=CAT_BODY, width=6, joint="curve")


def draw_ground(draw):
    """Draw ground line and shadows."""
    draw.line([(0, GROUND_Y + 6), (VISIBLE_W, GROUND_Y + 6)],
              fill=GROUND_COLOR, width=2)
    for sx in range(0, VISIBLE_W, 80):
        draw.ellipse([sx + 20, GROUND_Y + 2, sx + 60, GROUND_Y + 8],
                     fill=GROUND_COLOR)


def generate_frames(num_frames=30):
    """Generate the cat animation frames."""
    frames = []
    # phase 0.0→1.0 over num_frames
    for i in range(num_frames):
        img = Image.new("RGB", (VISIBLE_W, VISIBLE_H), BG)
        draw = ImageDraw.Draw(img)
        draw_ground(draw)

        t = i / num_frames  # 0.0 → 1.0

        # Cat walks from left (x=120) to center-right (x=500), then sits
        if t < 0.6:
            # walking phase
            walk_t = t / 0.6
            cx = 120 + walk_t * 420
            cy = GROUND_Y - 30
            leg_phase = walk_t * 4  # 4 walk cycles
            tail_phase = walk_t * 3
            blink = 0
        else:
            # sitting phase (t>=0.6)
            sit_t = (t - 0.6) / 0.4
            cx = 540
            cy = GROUND_Y - 26
            leg_phase = 0.25  # sitting pose
            tail_phase = sit_t * 2
            # blink a few times
            blink = 1.0 if (sit_t * 10) % 1.0 > 0.9 else 0

        draw_cat(draw, cx, cy, leg_phase, tail_phase, blink)
        frames.append(img)

    return frames


def frames_to_pak(frames, quality=60, rotate=True):
    """Convert PIL Image frames to PAK binary (JPEG compression)."""
    pak_frames = []
    for img in frames:
        canvas = Image.new("RGB", (1024, 240), (0, 0, 0))
        canvas.paste(img, (224, 24))
        if rotate:
            canvas = canvas.transpose(Image.ROTATE_180)
        buf = BytesIO()
        canvas.save(buf, format="JPEG", quality=quality)
        pak_frames.append(buf.getvalue())

    n = len(pak_frames)
    header = b"JP" + struct.pack("<HI", n, 0x0C)
    header += b"\x00" * (n * 4)

    offset_table = b""
    frame_data = b""
    current_offset = len(header)
    for jpeg_data in pak_frames:
        offset_table += struct.pack("<I", current_offset)
        entry = struct.pack("<I", len(jpeg_data)) + jpeg_data
        while len(entry) % 4 != 0:
            entry += b"\x00"
        frame_data += entry
        current_offset = len(header) + len(frame_data)

    return header[:8] + offset_table + frame_data


def main():
    parser = argparse.ArgumentParser(
        description="Generate pixel-art cat animation for LCD5A")
    parser.add_argument("--output", "-o", default="output/pet.pak",
                        help="Output file (default: output/pet.pak)")
    parser.add_argument("--frames", "-n", type=int, default=30,
                        help="Number of frames (default: 30)")
    parser.add_argument("--duration", "-d", type=int, default=80,
                        help="Frame duration in ms for GIF (default: 80)")
    parser.add_argument("--quality", "-q", type=int, default=60,
                        help="JPEG quality for PAK (default: 60)")
    parser.add_argument("--gif", action="store_true",
                        help="Output GIF instead of PAK")
    parser.add_argument("--no-rotate", action="store_true",
                        help="Skip 180-degree rotation")
    args = parser.parse_args()

    os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)

    print(f"Generating {args.frames} frames...")
    frames = generate_frames(args.frames)

    if args.gif:
        print(f"Saving GIF to {args.output}...")
        frames[0].save(
            args.output, save_all=True, append_images=frames[1:],
            duration=args.duration, loop=0,
        )
    else:
        print(f"Building PAK to {args.output}...")
        pak_data = frames_to_pak(frames, quality=args.quality,
                                 rotate=not args.no_rotate)
        with open(args.output, "wb") as f:
            f.write(pak_data)

    size_kb = os.path.getsize(args.output) / 1024
    total_frames = len(frames)
    print(f"Done: {args.output} ({size_kb:.0f} KB, {total_frames} frames)")


if __name__ == "__main__":
    main()
