"""Direct LCD5A control via USB HID - no iGameCenter needed."""
import hid
import struct
import time
import argparse
import sys
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO

VID = 0x048D
PID = 0x5711

# Protocol
HEADER_DISPLAY = 0xA9
HEADER_MASS_STORAGE = 0xD0

# Known commands (from protocol reverse engineering)
CMD_GET_DEVICE = 0xED12
CMD_GET_FILES = 0xE619  # 58905
CMD_PLAY_FILE = 0xE51A  # 58650
CMD_GET_SD = 0xEA15     # 59925

PAK_HEADER_MAGIC = b"JP"


def xor_checksum(data):
    """Compute XOR checksum over all bytes."""
    result = 0
    for b in data:
        result ^= b
    return result & 0xFF


def build_command(header, cmd_id, body=b""):
    """Build a protocol command: [Header 1B][CmdID 2B LE][BodyLen 1B][Body][XOR 1B]"""
    cmd_bytes = struct.pack("<H", cmd_id)
    body_len = len(body)
    if body_len > 255:
        raise ValueError(f"Body too long: {body_len}")
    msg = bytes([header]) + cmd_bytes + bytes([body_len]) + body
    chk = xor_checksum(msg)
    return msg + bytes([chk])


def parse_response(data):
    """Parse a protocol response. Returns (header, cmd_id, body) or None."""
    if len(data) < 5:
        return None
    header = data[0]
    cmd_id = struct.unpack("<H", data[1:3])[0]
    body_len = data[3]
    if len(data) < 5 + body_len:
        return None
    body = data[4:4 + body_len]
    return header, cmd_id, body


class LCD5ADevice:
    def __init__(self):
        self.device = None
        self.report_size = 64

    def connect(self):
        """Find and open the LCD5A HID device."""
        print(f"[Scanning] VID=0x{VID:04X} PID=0x{PID:04X}...")
        try:
            self.device = hid.device()
            self.device.open(VID, PID)
            info = self.device.get_manufacturer_string()
            product = self.device.get_product_string()
            print(f"[Connected] Manufacturer: {info}, Product: {product}")
            self.device.set_nonblocking(False)
            return True
        except OSError as e:
            print(f"[Error] Cannot open device: {e}")
            return False

    def close(self):
        if self.device:
            self.device.close()
            self.device = None

    def send_command(self, header, cmd_id, body=b"", read_response=True, timeout=2000):
        """Send a command and optionally read response."""
        cmd = build_command(header, cmd_id, body)
        print(f"[Send] ({len(cmd)}B) {cmd.hex(' ')}")

        # Try multiple sending methods
        results = []

        # Method 1: hid_write with 0x00 report ID prefix (HID output report)
        report0 = b"\x00" + cmd
        try:
            written = self.device.write(report0)
            print(f"  write(+0x00) -> {written} bytes")
            results.append("write+0x00")
        except OSError as e:
            print(f"  write(+0x00) error: {e}")

        # Method 2: hid_write without prefix
        try:
            written = self.device.write(cmd)
            print(f"  write(raw) -> {written} bytes")
            results.append("write_raw")
        except OSError as e:
            print(f"  write(raw) error: {e}")

        # Method 3: send_feature_report with 0x00 prefix
        try:
            self.device.send_feature_report(report0)
            print(f"  send_feature_report(+0x00) OK")
            results.append("feature+0x00")
        except OSError as e:
            print(f"  send_feature_report(+0x00) error: {e}")

        if not results:
            print("  All send methods failed!")
            return None

        if not read_response:
            return None

        # Try reading response with retries
        for attempt in range(3):
            time.sleep(0.5)
            for read_size in [64, 65, 256]:
                try:
                    response = self.device.read(read_size, timeout_ms=timeout)
                    if response and len(response) > 0:
                        print(f"[Recv] ({len(response)}B) {bytes(response).hex(' ')}")
                        return bytes(response)
                except OSError as e:
                    pass
        print("  (no response after retries)")
        return None

    def get_device_info(self):
        """Get device information."""
        print("\n=== Get Device Info ===")
        resp = self.send_command(HEADER_DISPLAY, CMD_GET_DEVICE)
        if resp:
            parsed = parse_response(resp)
            if parsed:
                header, cmd_id, body = parsed
                print(f"  Header: 0x{header:02X}, CmdID: 0x{cmd_id:04X}")
                print(f"  Body: {body.hex(' ') if body else '(empty)'}")
        return resp

    def get_files(self):
        """List files on device."""
        print("\n=== Get Files ===")
        resp = self.send_command(HEADER_DISPLAY, CMD_GET_FILES)
        if resp:
            parsed = parse_response(resp)
            if parsed:
                header, cmd_id, body = parsed
                if body:
                    print(f"  Raw: {body}")
        return resp

    def play_file(self, filename):
        """Play a file stored on the device."""
        print(f"\n=== Play: {filename} ===")
        body = filename.encode("ascii", errors="replace") + b"\x00"
        # Truncate/pad to specific length?
        return self.send_command(HEADER_DISPLAY, CMD_PLAY_FILE, body)

    def probe(self):
        """Deep probe - read raw data without sending, try different protocols."""
        print("\n=== Deep Probe ===")
        # Try to read any pending data
        for i in range(3):
            try:
                data = self.device.read(256, timeout_ms=500)
                if data:
                    print(f"[RawRead] ({len(data)}B) {bytes(data).hex(' ')}")
                else:
                    print("[RawRead] (empty)")
            except OSError as e:
                print(f"[RawRead] error: {e}")

        # Try get feature report
        for report_id in [0, 1, 2]:
            try:
                data = self.device.get_feature_report(report_id, 64)
                print(f"[GetFeature id={report_id}] {bytes(data).hex(' ')}")
            except OSError as e:
                print(f"[GetFeature id={report_id}] error: {e}")

        # Try sending raw protocol commands via write
        print("\n=== Try raw protocol via write ===")
        for test_name, test_bytes in [
            ("GetDevice", build_command(HEADER_DISPLAY, CMD_GET_DEVICE)),
            ("GetDevice(D0)", build_command(HEADER_MASS_STORAGE, CMD_GET_DEVICE)),
            ("GetFiles", build_command(HEADER_DISPLAY, CMD_GET_FILES)),
        ]:
            print(f"\n--- {test_name} ---")
            # Try as HID output report
            for prefix in [b"", b"\x00", b"\x01"]:
                pkt = prefix + test_bytes
                try:
                    n = self.device.write(pkt)
                    print(f"  write prefix={prefix.hex() if prefix else 'none'} -> {n}B")
                    time.sleep(0.3)
                    # Try reading
                    try:
                        r = self.device.read(64, timeout_ms=500)
                        if r:
                            print(f"    recv: {bytes(r).hex(' ')}")
                    except:
                        pass
                except OSError as e:
                    print(f"  write prefix={prefix.hex() if prefix else 'none'} -> {e}")

    def upload_and_play(self, pak_data, name):
        """Upload PAK data and play it.

        The upload protocol needs further RE. For now we try the known
        mass-storage header 0xD0. The upload command ID is unknown,
        so this is experimental.
        """
        print(f"\n=== Upload: {name} ({len(pak_data)} bytes) ===")

        # Try: header 0xD0 with CMD 0xE61A (guess - might be upload)
        # For now, just print what we'd send and try a raw write
        cmd = bytes([HEADER_MASS_STORAGE])
        print(f"  Data preview: {pak_data[:32].hex(' ')}...")
        print("  (Upload protocol TBD - need command ID)")
        return None


# ── PAK Generation (reuse from text_display.py) ──

def make_text_pak(text, width=1024, height=240, font_size=60,
                  fg=(255, 255, 255), bg=(30, 30, 30), quality=30):
    """Generate a single-frame PAK with centered text."""
    img = Image.new("RGB", (width, height), bg)
    draw = ImageDraw.Draw(img)

    font = None
    for fp in [
        "C:/Windows/Fonts/msyh.ttc",
        "C:/Windows/Fonts/msyhbd.ttc",
        "C:/Windows/Fonts/simhei.ttf",
        "C:/Windows/Fonts/simsun.ttc",
        "C:/Windows/Fonts/arial.ttf",
    ]:
        try:
            font = ImageFont.truetype(fp, font_size)
            break
        except Exception:
            continue
    if font is None:
        font = ImageFont.load_default()

    lines = text.replace("\\n", "\n").split("\n")
    if not lines:
        lines = [""]

    line_spacing = font_size + 12
    total_h = len(lines) * line_spacing
    start_y = (height - total_h) // 2

    for i, line in enumerate(lines):
        bbox = draw.textbbox((0, 0), line, font=font)
        tw = bbox[2] - bbox[0]
        x = (width - tw) // 2
        y = start_y + i * line_spacing
        draw.text((x, y), line, fill=fg, font=font)

    img = img.transpose(Image.ROTATE_180)

    buf = BytesIO()
    img.save(buf, format="JPEG", quality=quality)
    jpeg_data = buf.getvalue()

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

    return header[:8] + offset_table + frame_data


def make_image_pak(image_path, width=1024, height=240, quality=60):
    """Generate PAK from an image file."""
    img = Image.open(image_path).convert("RGB")
    img = img.resize((width, height), Image.LANCZOS)
    img = img.transpose(Image.ROTATE_180)

    buf = BytesIO()
    img.save(buf, format="JPEG", quality=quality)
    jpeg_data = buf.getvalue()

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

    return header[:8] + offset_table + frame_data


# ── CLI ──

def main():
    parser = argparse.ArgumentParser(description="LCD5A Direct Control (no iGameCenter)")
    sub = parser.add_subparsers(dest="cmd")

    sub.add_parser("detect", help="Find and connect to device")
    sub.add_parser("info", help="Get device info")
    sub.add_parser("files", help="List stored files")
    sub.add_parser("probe", help="Deep probe - test all communication methods")
    p_play = sub.add_parser("play", help="Play a stored file")
    p_play.add_argument("name", help="Filename on device")
    p_text = sub.add_parser("text", help="Display text")
    p_text.add_argument("text", help="Text to display (\\n for newline)")
    p_text.add_argument("--size", type=int, default=60, help="Font size")
    p_img = sub.add_parser("image", help="Display an image")
    p_img.add_argument("path", help="Image file path")

    args = parser.parse_args()
    if not args.cmd:
        parser.print_help()
        return

    lcd = LCD5ADevice()

    if args.cmd == "probe":
        if not lcd.connect():
            return
        lcd.probe()
        lcd.close()

    elif args.cmd == "detect":
        if lcd.connect():
            print("\n[OK] Device found and connected!")
            lcd.close()
        else:
            print("\n[FAIL] Device not found. Is the LCD5A connected via USB?")

    elif args.cmd == "info":
        if not lcd.connect():
            return
        lcd.get_device_info()
        lcd.close()

    elif args.cmd == "files":
        if not lcd.connect():
            return
        lcd.get_files()
        lcd.close()

    elif args.cmd == "play":
        if not lcd.connect():
            return
        lcd.play_file(args.name)
        lcd.close()

    elif args.cmd == "text":
        pak = make_text_pak(args.text, font_size=args.size)
        print(f"[PAK] {len(pak)} bytes")
        # For now, just save to file for testing
        out = "test_output.pak"
        with open(out, "wb") as f:
            f.write(pak)
        print(f"[SAVED] {out}")
        # TODO: upload via raw HID

    elif args.cmd == "image":
        pak = make_image_pak(args.path)
        out = "test_image.pak"
        with open(out, "wb") as f:
            f.write(pak)
        print(f"[SAVED] {out} ({len(pak)} bytes)")
        # TODO: upload via raw HID


if __name__ == "__main__":
    main()
