"""LCD5A Status Hook — dual path: iGame API (COM) + HID direct fallback.
Usage: python hook.py <working|done|fail|off>
"""
import os, sys, subprocess, struct, time

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
LCD = os.path.join(SCRIPT_DIR, "lcd_display.py")
STATUS = {"working": "_working", "done": "_done", "fail": "_fail", "off": "_idle", "idle": "_idle"}

VID, PID = 0x048D, 0x5711
CMD_PLAY = 0xE51A
HEADER = 0xA9

def _xor(data):
    r = 0
    for b in data: r ^= b
    return r & 0xFF

def play_via_api(name):
    """Use iGame API (requires COM port — works on host USB)."""
    r = subprocess.run([sys.executable, LCD, "play", name],
                       cwd=SCRIPT_DIR, capture_output=True, text=True, timeout=10)
    return r.returncode == 0 and "Connected" in r.stdout

def play_via_hid(name):
    """Direct HID feature report via vendor control interface (works without service)."""
    try:
        import hid
        for d in hid.enumerate(VID, PID):
            if d.get('interface_number') == 1 and d.get('usage') == 0x0010:
                dev = hid.device()
                dev.open_path(d['path'])
                dev.set_nonblocking(True)
                body = name.encode() + b'\x00'
                msg = bytes([HEADER]) + struct.pack('<H', CMD_PLAY) + bytes([len(body)]) + body
                msg += bytes([_xor(msg)])
                dev.send_feature_report(b'\x00' + msg.ljust(64, b'\x00'))
                dev.close()
                return True
    except Exception:
        pass
    return False

def main():
    if len(sys.argv) < 2 or sys.argv[1] not in STATUS:
        print("Usage: python hook.py <working|done|fail|off>")
        sys.exit(1)

    name = STATUS[sys.argv[1]]

    if play_via_api(name):
        print(f"[Hook] {name} (API)")
        sys.exit(0)

    if play_via_hid(name):
        print(f"[Hook] {name} (HID)")
        sys.exit(0)

    print(f"[Hook] {name} FAILED")
    sys.exit(1)

if __name__ == "__main__":
    main()
