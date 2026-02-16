# PyInstaller Token Decoder

A web-based tool to safely extract and decode tokens from PyInstaller-packed executables without running them.

## Features

- 🔒 **No execution**: Files are only extracted and parsed; the `.exe` is never run
- 🔐 **AES zip support**: Handles encrypted zips with password protection
- 🌐 **Web GUI**: Clean browser interface for easy uploads
- 📦 **Automatic cleanup**: Temporary files are deleted after processing

## Setup

### Prerequisites

- Python 3.7+
- pip

### Installation

1. Clone or download this project
2. Install dependencies:

```bash
pip install pyzipper
```

If `tractor.py` or other modules are missing, ensure they're in the root directory.

## Usage

### Start the Server

```bash
python local_server.py
```

The server will start at `http://localhost:8000`.

### Using the GUI

1. Open your browser and navigate to `http://localhost:8000`
2. Drop a `.zip` file containing a single PyInstaller `.exe`
3. Click **Decode token**
4. The decoded token will appear below

### Encrypted Zips

If your zip is password-protected, the default password is `infected`. This is hardcoded in [api/decode.py](api/decode.py) and can be changed if needed.

## How It Works

When you upload a zip:

1. **Extract**: The zip is extracted (supports AES encryption via `pyzipper`)
2. **Find .exe**: Locates the PyInstaller executable
3. **Parse archive**: Extracts the bundled files from the PyInstaller archive
4. **Hunt token**: Scans `source_prepared.pyc` for base64-encoded tokens
5. **Decode**: Reverses and decodes the first valid token found
6. **Return result**: Displays the decoded token in the browser
7. **Clean up**: Temporary files are deleted

**No code is executed at any stage.**

## File Structure

```
.
├── index.html          # Web UI
├── app.js              # Frontend logic
├── styles.css          # UI styling
├── local_server.py     # Local HTTP server
├── api/
│   └── decode.py       # Decode handler (core logic)
├── tractor.py          # PyInstaller archive parser
├── yo.py               # (utility, optional)
└── README.md           # This file
```

## API

### POST /api/decode

Upload a zip file to extract and decode tokens.

**Request:**
- `Content-Type`: `multipart/form-data`
- Field name: `file` (required, must be a `.zip`)

**Response:**
```json
{
  "decoded_token": "your-decoded-token-here"
}
```

**Error responses:**
```json
{
  "error": "No .exe found in zip."
}
```

### GET /

Serves the web interface.

- `GET /` → index.html
- `GET /app.js` → JavaScript
- `GET /styles.css` → CSS

## Customization

### Change the Default Zip Password

Edit [api/decode.py](api/decode.py), line ~188:

```python
_safe_extract(zip_file, tmp_dir, password="your-password")
```

### Change the Server Port

Edit [local_server.py](local_server.py) and change `8000` to your desired port:

```python
server = HTTPServer(("localhost", 5000), DecodeHandler)
```

## Troubleshooting

### "AES zip detected. Install pyzipper to extract it."

Run `pip install pyzipper`.

### "No .exe found in zip"

Ensure your zip contains at least one `.exe` file.

### "source_prepared.pyc not found"

The PyInstaller exe may not be compatible or the extraction failed. Try re-packing the exe.

### "No token found"

The token pattern may not match. Check if the binary structure is different.

## Safety Notes

- ✅ Executables are **never run**
- ✅ Files are stored in **temporary directories** and deleted after processing
- ✅ The server runs **locally** by default
- ⚠️ Only share the server with trusted users if deployed remotely

## License

Use at your own discretion. This tool is for security research and analysis only.
