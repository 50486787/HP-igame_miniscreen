"""LCD5A display controller via iGame API DLLs (pythonnet bridge).

Usage:
  python lcd_display.py text "Hello World"
  python lcd_display.py image cat.png
  python lcd_display.py play mypet
  python lcd_display.py switch   -- interactive switch between stored files
  python lcd_display.py list
  python lcd_display.py done     -- show success notification
  python lcd_display.py fail "Build error"  -- show failure notification
"""

import os
import sys
import argparse
import tempfile
from PIL import Image, ImageDraw
from pak_utils import (CANVAS_W, CANVAS_H, VISIBLE_X, VISIBLE_Y,
                       VISIBLE_W, VISIBLE_H, CENTER_X, CENTER_Y,
                       make_canvas, find_font, enhance_for_lcd,
                       build_pak_from_jpeg_bytes, image_to_jpeg)

# ── .NET assembly loading via pythonnet ──

IGAME_DIR = r"C:\Program Files\iGameCenter"
BIN_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bin")

def init_clr():
    """Initialize .NET CLR and load iGame API assemblies."""
    import clr

    igame_api_dir = os.path.join(IGAME_DIR, "iGameAPI")
    n15_dir = os.path.join(igame_api_dir, "N15_25")
    for d in [BIN_DIR, IGAME_DIR, igame_api_dir, n15_dir]:
        os.add_dll_directory(d)

    sep = ";" if sys.platform == "win32" else ":"
    cur_path = os.environ.get("PATH", "")
    new_path = sep.join([BIN_DIR, IGAME_DIR, igame_api_dir, n15_dir, cur_path])
    os.environ["PATH"] = new_path

    clr.AddReference(os.path.join(BIN_DIR, "iGameAPI.Contracts"))
    clr.AddReference(os.path.join(BIN_DIR, "iGameAPI.LCD.CSharp"))

    from iGameAPI.Contracts.LCD import LCD_IC_VERSION
    from iGameAPI.LCD.CSharp import LCD, LCD5A, LogCallbackFun

    return LCD, LCD5A, LCD_IC_VERSION, LogCallbackFun


class LCD5AController:
    """Controls the LCD5A device via iGame API."""

    def __init__(self):
        self.device = None
        self.LCD = None
        self.LCD5A = None
        self.VERSION = None

    def connect(self):
        """Scan for and connect to LCD5A device."""
        LCD, LCD5A, LCD_IC_VERSION, LogCallbackFun = init_clr()
        self.LCD = LCD
        self.LCD5A = LCD5A
        self.VERSION = LCD_IC_VERSION

        callback = LogCallbackFun(lambda msg: None)
        print("[Scanning] Looking for LCD5A...")
        devices = LCD.GetLCDGeneralCOM(callback)

        if not devices or len(devices) == 0:
            raise Exception("No iGame LCD device found.")

        for i, dev in enumerate(devices):
            if dev.Version == LCD_IC_VERSION.LCD5A:
                self.device = dev
                try:
                    self._invoke("SetLang", 1)
                except Exception:
                    pass
                print("[Connected] LCD5A ready")
                return True

        raise Exception("No LCD5A found in scan results.")

    def close(self):
        if self.device:
            try:
                self._invoke("Close")
            except Exception:
                pass
            self.device = None

    def _invoke(self, method_name, *args):
        """Call method via reflection to bypass interface type issues."""
        method = self.device.GetType().GetMethod(method_name)
        if method is None:
            raise AttributeError(f"Method '{method_name}' not found")
        return method.Invoke(self.device, args or None)

    def list_files(self):
        """List files stored on the device."""
        images = self._invoke("GetImages")
        if not images:
            return []
        return [(img.FileName, img.FileSize) for img in images]

    def play(self, name):
        """Play a stored file."""
        self._invoke("PlayMov", name)

    def delete(self, name):
        """Delete a stored file."""
        self._invoke("DeleteMov", name)

    def upload_and_play(self, file_path, name=None):
        """Upload a PAK/GIF file and start playing it.

        GIFs are auto-converted to PAK first (the API's native GIF handler
        produces a black screen on LCD5A hardware).
        """
        file_path = os.path.abspath(file_path)
        if name is None:
            name = os.path.splitext(os.path.basename(file_path))[0]

        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        # Auto-convert GIF to PAK to avoid black-screen bug
        ext = os.path.splitext(file_path)[1].lower()
        if ext in (".gif", ".giff"):
            from gif_to_pak import gif_to_pak
            tf = tempfile.NamedTemporaryFile(suffix=".pak", delete=False)
            tf.close()
            try:
                gif_to_pak(file_path, tf.name, quality=60)
                file_path = tf.name
            except Exception:
                os.unlink(tf.name)
                raise

        size_kb = os.path.getsize(file_path) / 1024
        print(f"[Upload] {os.path.basename(file_path)} ({size_kb:.0f}KB) as '{name}'")
        task = self._invoke("UploadImage", name, file_path)
        ok = task.GetAwaiter().GetResult()

        if ok:
            print("[OK] Uploaded, playing...")
            try:
                self._invoke("SetStartIMG", name)
            except Exception:
                pass
            self._invoke("PlayMov", name)
            return True
        print("[FAIL] Upload returned false")
        return False

# ── PAK generation ──


def _text_to_pak_fast(text, font_size=60, fg=(255, 255, 255), bg=(30, 30, 30)):
    """Single-frame PAK for live text (fast upload)."""
    img = make_canvas(bg=bg)
    draw = ImageDraw.Draw(img)
    font = find_font(font_size)

    lines = text.replace("\\n", "\n").split("\n")
    n = len(lines)
    line_spacing = font_size + 12
    y_positions = [CENTER_Y + (i - (n - 1) / 2.0) * line_spacing for i in range(n)]

    for i, line in enumerate(lines):
        draw.text((CENTER_X, int(y_positions[i])), line, fill=fg, font=font, anchor="mm")

    jpeg = image_to_jpeg(img, quality=20)
    return build_pak_from_jpeg_bytes([jpeg], num_frames=1)


def make_text_pak(text, font_size=60, fg=(30, 30, 30), bg=(240, 240, 250)):
    """Generate PAK with centered text (accounts for bezel offset)."""
    img = make_canvas(bg=bg)
    draw = ImageDraw.Draw(img)
    font = find_font(font_size)

    lines = text.replace("\\n", "\n").split("\n")
    n = len(lines)
    line_spacing = font_size + 12
    y_positions = [CENTER_Y + (i - (n - 1) / 2.0) * line_spacing for i in range(n)]

    for i, line in enumerate(lines):
        draw.text((CENTER_X, int(y_positions[i])), line, fill=fg, font=font, anchor="mm")

    jpeg = image_to_jpeg(img)
    return build_pak_from_jpeg_bytes([jpeg], num_frames=3)


def make_status_pak(status, message=""):
    """Generate a status notification PAK (colored background + icon + text)."""
    colors = {
        "done": (40, 160, 40),
        "fail": (200, 40, 40),
        "warn": (200, 160, 30),
        "info": (40, 80, 200),
    }
    icons = {"done": "[OK]", "fail": "[X]", "warn": "[!]", "info": "[i]"}
    bg = colors.get(status, (120, 120, 120))
    icon = icons.get(status, "")

    text = f"{icon} {message}" if message else f"{icon} Task complete"
    return make_text_pak(text, font_size=52, fg=(255, 255, 255), bg=bg)


def make_image_pak(image_path, quality=60):
    """Generate PAK from an image file (resized to canvas)."""
    img = enhance_for_lcd(Image.open(image_path).convert("RGB"))
    img = img.resize((CANVAS_W, CANVAS_H), Image.LANCZOS)
    return build_pak_from_jpeg_bytes([image_to_jpeg(img, quality=quality)], num_frames=3)


def make_image_visible_pak(image_path, quality=60):
    """Generate PAK from an image, sized to the visible area (800x216)."""
    img = enhance_for_lcd(Image.open(image_path).convert("RGB"))
    canvas = make_canvas()
    img_resized = img.resize((VISIBLE_W, VISIBLE_H), Image.LANCZOS)
    canvas.paste(img_resized, (VISIBLE_X, VISIBLE_Y))
    return build_pak_from_jpeg_bytes([image_to_jpeg(canvas, quality=quality)], num_frames=3)


def make_image_text_pak(image_path, text, font_size=36, text_bottom=True, quality=60):
    """Generate PAK with image in visible area + text overlay."""
    img = enhance_for_lcd(Image.open(image_path).convert("RGB"))
    img = img.resize((VISIBLE_W, VISIBLE_H), Image.LANCZOS)

    draw = ImageDraw.Draw(img)
    font = find_font(font_size)

    bbox = draw.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]

    if text_bottom:
        bar_h = th + 20
        overlay = Image.new("RGBA", (VISIBLE_W, bar_h), (0, 0, 0, 160))
        img_rgba = img.convert("RGBA")
        img_rgba.paste(overlay, (0, VISIBLE_H - bar_h), overlay)
        img = img_rgba.convert("RGB")
        tx = (VISIBLE_W - tw) // 2
        ty = VISIBLE_H - bar_h + (bar_h - th) // 2
    else:
        tx = (VISIBLE_W - tw) // 2
        ty = (VISIBLE_H - th) // 2

    draw = ImageDraw.Draw(img)
    draw.text((tx, ty), text, fill=(255, 255, 255), font=font)

    canvas = make_canvas()
    canvas.paste(img, (VISIBLE_X, VISIBLE_Y))
    return build_pak_from_jpeg_bytes([image_to_jpeg(canvas, quality=quality)], num_frames=3)


# ── CLI ──

TEMP_PAK = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_temp_display.pak")


def main():
    parser = argparse.ArgumentParser(description="LCD5A Display Controller")
    sub = parser.add_subparsers(dest="cmd")

    sub.add_parser("list", help="List files on device")

    p_play = sub.add_parser("play", help="Play a stored file")
    p_play.add_argument("name")

    p_del = sub.add_parser("delete", help="Delete a stored file")
    p_del.add_argument("name")

    p_text = sub.add_parser("text", help="Display text on screen")
    p_text.add_argument("text", nargs="+")
    p_text.add_argument("--size", type=int, default=60)

    p_img = sub.add_parser("image", help="Display an image (stretched to canvas)")
    p_img.add_argument("path")

    p_imgv = sub.add_parser("imagev", help="Display an image (visible area only)")
    p_imgv.add_argument("path")

    p_imgtxt = sub.add_parser("imagetext", help="Display image with text overlay")
    p_imgtxt.add_argument("path")
    p_imgtxt.add_argument("text", nargs="+")
    p_imgtxt.add_argument("--bottom", action="store_true", default=True)
    p_imgtxt.add_argument("--size", type=int, default=36)

    p_upload = sub.add_parser("upload", help="Upload a PAK/GIF file")
    p_upload.add_argument("path")
    p_upload.add_argument("name", nargs="?")

    p_live = sub.add_parser("live", help="Interactive live text display")
    p_live.add_argument("--size", type=int, default=60, help="Font size")

    p_switch = sub.add_parser("switch", help="Interactive switch between stored files")

    sub.add_parser("done", help="Show success notification")
    p_fail = sub.add_parser("fail", help="Show failure notification")
    p_fail.add_argument("message", nargs="*")
    sub.add_parser("warn", help="Show warning notification")
    sub.add_parser("info", help="Show info notification")

    args = parser.parse_args()
    if not args.cmd:
        parser.print_help()
        return

    lcd = LCD5AController()

    try:
        lcd.connect()

        if args.cmd == "list":
            files = lcd.list_files()
            if not files:
                print("(no files stored)")
            for name, size in files:
                print(f"  {name} ({size} bytes)")

        elif args.cmd == "play":
            lcd.play(args.name)

        elif args.cmd == "delete":
            lcd.delete(args.name)

        elif args.cmd == "text":
            text = " ".join(args.text)
            pak = make_text_pak(text, font_size=args.size)
            with open(TEMP_PAK, "wb") as f:
                f.write(pak)
            lcd.upload_and_play(TEMP_PAK, "_text")

        elif args.cmd == "image":
            pak = make_image_pak(args.path)
            with open(TEMP_PAK, "wb") as f:
                f.write(pak)
            lcd.upload_and_play(TEMP_PAK, "_image")

        elif args.cmd == "imagev":
            pak = make_image_visible_pak(args.path)
            with open(TEMP_PAK, "wb") as f:
                f.write(pak)
            lcd.upload_and_play(TEMP_PAK, "_imagev")

        elif args.cmd == "imagetext":
            text = " ".join(args.text)
            pak = make_image_text_pak(args.path, text, font_size=args.size, text_bottom=args.bottom)
            with open(TEMP_PAK, "wb") as f:
                f.write(pak)
            lcd.upload_and_play(TEMP_PAK, "_imgtxt")

        elif args.cmd == "live":
            print("=== Live Text Mode ===")
            print("Type text and press Enter to display on screen.")
            print("Empty line or Ctrl+C to exit.")
            print()
            font_size = getattr(args, 'size', 60)
            toggle = 0
            while True:
                try:
                    text = input("> ").strip()
                except (EOFError, KeyboardInterrupt):
                    print("\nBye.")
                    break
                if not text:
                    break
                # Double-buffer: upload to alternate slot so current
                # text stays during upload, then flip via PlayMov.
                slot = f"_lv{toggle}"
                toggle ^= 1
                pak = _text_to_pak_fast(text, font_size=font_size)
                with open(TEMP_PAK, "wb") as f:
                    f.write(pak)
                lcd.upload_and_play(TEMP_PAK, slot)
                try:
                    lcd.delete(f"_lv{toggle}")
                except Exception:
                    pass
                print("  -> displayed")

        elif args.cmd == "switch":
            files = lcd.list_files()
            if not files:
                print("(no files stored)")
                return
            files.sort(key=lambda x: x[0].lower())
            print("=== Stored Files ===")
            for i, (name, size) in enumerate(files):
                print(f"  [{i}] {name} ({size // 1024}KB)")
            print()
            while True:
                try:
                    choice = input("Switch to (number/name, Enter to exit): ").strip()
                except (EOFError, KeyboardInterrupt):
                    print("\nBye.")
                    break
                if not choice:
                    break
                # Try number first, then name
                name = None
                if choice.isdigit():
                    idx = int(choice)
                    if 0 <= idx < len(files):
                        name = files[idx][0]
                else:
                    name = choice
                if name:
                    print(f"  -> {name}")
                    lcd.play(name)
                else:
                    print("  Invalid choice")

        elif args.cmd == "upload":
            lcd.upload_and_play(args.path, args.name)

        elif args.cmd in ("done", "fail", "warn", "info"):
            msg = " ".join(args.message) if hasattr(args, 'message') and args.message else ""
            pak = make_status_pak(args.cmd, msg)
            with open(TEMP_PAK, "wb") as f:
                f.write(pak)
            lcd.upload_and_play(TEMP_PAK, f"_{args.cmd}")

    finally:
        lcd.close()


if __name__ == "__main__":
    main()
