import base64
import re
from pathlib import Path
import sys
import subprocess

DESKTOP = Path.home() / "Desktop"
PYINSTXTRACTOR = DESKTOP / "tractor.py"

BASE64_RE = re.compile(
    rb"[A-Za-z0-9+/=]{20,}"
)

def extract_exe(exe_path):
    subprocess.check_call(
        [sys.executable, str(PYINSTXTRACTOR), str(exe_path)],
        cwd=DESKTOP
    )

def find_source_prepared(extracted_dir):
    for f in extracted_dir.rglob("source_prepared.pyc"):
        return f
    return None

def scan_pyc(pyc_path):
    print("[+] Scanning .pyc directly (no decompile)...\n")

    data = pyc_path.read_bytes()

    for match in BASE64_RE.finditer(data):
        try:
            token = match.group().decode("ascii")
            decoded = base64.b64decode(token[::-1]).decode("utf-8")
            print("[*] Encoded :", token)
            print("[+] Decoded :", decoded)
            print("-" * 60)
        except Exception:
            pass

def main():
    if len(sys.argv) != 2:
        print("Usage: python fast_pyc_string_decoder.py <target.exe>")
        sys.exit(1)

    exe = DESKTOP / sys.argv[1]

    extract_exe(exe)

    extracted = DESKTOP / f"{exe.name}_extracted"
    pyc = find_source_prepared(extracted)

    if not pyc:
        print("[!] source_prepared.pyc not found")
        sys.exit(1)

    scan_pyc(pyc)

if __name__ == "__main__":
    main()
