import base64
import cgi
import io
import json
import os
import re
import tempfile
import zipfile
from pathlib import Path
from typing import Optional

import sys
from http.server import BaseHTTPRequestHandler

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import tractor

BASE64_RE = re.compile(rb"[A-Za-z0-9+/=]{20,}")


def _safe_extract(zip_file: zipfile.ZipFile, dest_dir: Path) -> None:
    for member in zip_file.infolist():
        member_path = dest_dir / member.filename
        if not str(member_path.resolve()).startswith(str(dest_dir.resolve())):
            raise ValueError("Invalid zip path.")
    zip_file.extractall(dest_dir)


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


def _decode_first_token(pyc_path: Path) -> Optional[str]:
    data = pyc_path.read_bytes()
    for match in BASE64_RE.finditer(data):
        token = match.group().decode("ascii", errors="ignore")
        if not token:
            continue
        try:
            decoded = base64.b64decode(token[::-1]).decode("utf-8")
            return decoded
        except Exception:
            continue
    return None


def _json_response(handler, status: int, payload: dict) -> None:
    body = json.dumps(payload).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


class handler(BaseHTTPRequestHandler):  # Vercel Python entrypoint
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_POST(self):
        content_type = self.headers.get("Content-Type", "")
        content_length = self.headers.get("Content-Length", "0")
        environ = {
            "REQUEST_METHOD": "POST",
            "CONTENT_TYPE": content_type,
            "CONTENT_LENGTH": content_length,
        }
        form = cgi.FieldStorage(
            fp=self.rfile,
            headers=self.headers,
            environ=environ,
        )
        if "file" not in form:
            _json_response(self, 400, {"error": "Missing file field."})
            return
        file_item = form["file"]
        if not getattr(file_item, "file", None):
            _json_response(self, 400, {"error": "Invalid upload."})
            return

        filename = getattr(file_item, "filename", "") or ""
        if not filename.lower().endswith(".zip"):
            _json_response(self, 400, {"error": "Upload must be a .zip file."})
            return

        raw = file_item.file.read()
        if not raw:
            _json_response(self, 400, {"error": "Empty upload."})
            return

        try:
            with tempfile.TemporaryDirectory() as tmp:
                tmp_dir = Path(tmp)
                with zipfile.ZipFile(io.BytesIO(raw)) as zip_file:
                    _safe_extract(zip_file, tmp_dir)

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
