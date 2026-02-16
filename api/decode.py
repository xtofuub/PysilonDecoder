import base64
import io
import json
import os
import re
import stat
import subprocess
import tempfile
import zipfile
from email.parser import BytesParser
from email.policy import default
from pathlib import Path
from typing import Optional

import sys
from http.server import BaseHTTPRequestHandler

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import tractor

try:
    import pyzipper
except Exception:
    pyzipper = None

BASE64_RE = re.compile(rb"[A-Za-z0-9+/=]{20,}")
BASE64_TEXT_RE = re.compile(r"[A-Za-z0-9+/=]{20,}")
PYCDAS_PATH = ROOT_DIR / "pycdas.x86_64"
PYCDAS_TIMEOUT = 30


def _safe_extract(zip_file, dest_dir: Path, password: Optional[str] = None) -> None:
    for member in zip_file.infolist():
        member_path = dest_dir / member.filename
        if not str(member_path.resolve()).startswith(str(dest_dir.resolve())):
            raise ValueError("Invalid zip path.")
    pwd = password.encode("utf-8") if password else None
    if pwd:
        zip_file.setpassword(pwd)
    zip_file.extractall(dest_dir, pwd=pwd)


def _is_aes_zip(zip_file: zipfile.ZipFile) -> bool:
    return any(info.compress_type == 99 for info in zip_file.infolist())


def _find_exe(root_dir: Path) -> Optional[Path]:
    for exe in root_dir.rglob("*.exe"):
        return exe
    return None


def _extract_pyinstaller(exe_path: Path, work_dir: Path) -> Path:
    archive = tractor.PyInstArchive(str(exe_path))
    if not archive.open():
        raise RuntimeError("Failed to open executable.")
    try:
        if not archive.checkFile():
            raise RuntimeError("Not a supported PyInstaller executable.")
        if not archive.getCArchiveInfo():
            raise RuntimeError("Failed to read archive info.")
        archive.parseTOC()
        current_dir = os.getcwd()
        os.chdir(str(work_dir))
        try:
            archive.extractFiles()
        finally:
            os.chdir(current_dir)
    finally:
        archive.close()

    extracted_dir = work_dir / f"{exe_path.name}_extracted"
    if not extracted_dir.exists():
        raise RuntimeError("Extraction failed.")
    return extracted_dir


def _find_source_prepared(extracted_dir: Path) -> Optional[Path]:
    for pyc in extracted_dir.rglob("source_prepared.pyc"):
        return pyc
    return None


def _ensure_executable(path: Path) -> None:
    try:
        mode = path.stat().st_mode
        path.chmod(mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    except Exception:
        pass


def _decode_token_candidates(candidates) -> Optional[str]:
    for token in candidates:
        token = token.strip()
        if not token:
            continue
        try:
            decoded = base64.b64decode(token[::-1]).decode("utf-8")
            return decoded
        except Exception:
            continue
    return None


def _decode_from_pyc_bytes(pyc_path: Path) -> Optional[str]:
    data = pyc_path.read_bytes()
    tokens = (match.group().decode("ascii", errors="ignore") for match in BASE64_RE.finditer(data))
    return _decode_token_candidates(tokens)


def _decode_from_pycdas(pyc_path: Path) -> Optional[str]:
    if not PYCDAS_PATH.exists():
        return None
    _ensure_executable(PYCDAS_PATH)
    try:
        result = subprocess.run(
            [str(PYCDAS_PATH), str(pyc_path)],
            capture_output=True,
            text=True,
            timeout=PYCDAS_TIMEOUT,
        )
    except Exception:
        return None

    output = "\n".join(filter(None, [result.stdout, result.stderr]))
    if not output:
        return None
    tokens = BASE64_TEXT_RE.findall(output)
    return _decode_token_candidates(tokens)


def _decode_first_token(pyc_path: Path) -> Optional[str]:
    decoded = _decode_from_pycdas(pyc_path)
    if decoded:
        return decoded
    return _decode_from_pyc_bytes(pyc_path)


def _parse_multipart_upload(content_type: str, body: bytes) -> Optional[tuple[str, bytes]]:
    if not content_type.lower().startswith("multipart/form-data"):
        return None
    match = re.search(r"boundary=([^;]+)", content_type, flags=re.IGNORECASE)
    if not match:
        return None
    boundary = match.group(1).strip().strip('"')
    if not boundary:
        return None

    message = BytesParser(policy=default).parsebytes(
        b"Content-Type: " + content_type.encode("utf-8") + b"\r\n\r\n" + body
    )
    for part in message.iter_parts():
        if part.get_content_disposition() != "form-data":
            continue
        field_name = part.get_param("name", header="content-disposition")
        if field_name != "file":
            continue
        filename = part.get_filename() or ""
        payload = part.get_payload(decode=True) or b""
        return filename, payload
    return None


def _json_response(handler, status: int, payload: dict) -> None:
    body = json.dumps(payload).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Access-Control-Allow-Origin", "*")
    handler.send_header("Content-Type", "application/json")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


class handler(BaseHTTPRequestHandler):  # Vercel Python entrypoint
    def do_GET(self):
        path = self.path.split("?", 1)[0]
        if path in ("/", "/index.html"):
            file_path = ROOT_DIR / "index.html"
            content_type = "text/html; charset=utf-8"
        elif path == "/app.js":
            file_path = ROOT_DIR / "app.js"
            content_type = "application/javascript; charset=utf-8"
        elif path == "/styles.css":
            file_path = ROOT_DIR / "styles.css"
            content_type = "text/css; charset=utf-8"
        else:
            body = b"Not found. Use POST /api/decode with a zip upload."
            self.send_response(404)
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        if not file_path.exists():
            body = b"UI file missing. Check index.html, app.js, styles.css."
            self.send_response(404)
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        body = file_path.read_bytes()
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_POST(self):
        content_type = self.headers.get("Content-Type", "")
        content_length = self.headers.get("Content-Length", "0")
        try:
            length = int(content_length)
        except ValueError:
            length = 0
        body = self.rfile.read(length) if length > 0 else b""
        parsed = _parse_multipart_upload(content_type, body)
        if not parsed:
            _json_response(self, 400, {"error": "Missing file field."})
            return
        filename, raw = parsed
        if not filename.lower().endswith(".zip"):
            _json_response(self, 400, {"error": "Upload must be a .zip file."})
            return
        if not raw:
            _json_response(self, 400, {"error": "Empty upload."})
            return

        try:
            with tempfile.TemporaryDirectory() as tmp:
                tmp_dir = Path(tmp)
                with zipfile.ZipFile(io.BytesIO(raw)) as probe:
                    aes_zip = _is_aes_zip(probe)

                if aes_zip:
                    if not pyzipper:
                        raise RuntimeError("AES zip detected. Install pyzipper to extract it.")
                    with pyzipper.AESZipFile(io.BytesIO(raw)) as zip_file:
                        _safe_extract(zip_file, tmp_dir, password="infected")
                else:
                    with zipfile.ZipFile(io.BytesIO(raw)) as zip_file:
                        _safe_extract(zip_file, tmp_dir, password="infected")

                exe_path = _find_exe(tmp_dir)
                if not exe_path:
                    _json_response(self, 400, {"error": "No .exe found in zip."})
                    return

                extracted_dir = _extract_pyinstaller(exe_path, tmp_dir)
                pyc_path = _find_source_prepared(extracted_dir)
                if not pyc_path:
                    _json_response(self, 400, {"error": "source_prepared.pyc not found."})
                    return

                decoded = _decode_first_token(pyc_path)
                if not decoded:
                    _json_response(self, 404, {"error": "No token found."})
                    return

                _json_response(self, 200, {"decoded_token": decoded})
        except zipfile.BadZipFile:
            _json_response(self, 400, {"error": "Invalid zip archive."})
        except Exception as exc:
            _json_response(self, 500, {"error": str(exc)})
