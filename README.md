# Token Decoder (Vercel + Local)

This project extracts a PyInstaller exe inside a zip, finds `source_prepared.pyc`, and decodes the first reversed base64 token.

## Run locally

1. Make sure you have Python 3.9+ installed.
2. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

3. Start the local server:

   ```bash
   python local_server.py
   ```

4. Open `index.html` in your browser and upload the zip.

The UI will send the zip to `http://localhost:8000/api/decode`.

## Deploy to Vercel (zip upload)

1. Zip the project root (make sure `pycdas.x86_64` is included).
2. Go to https://vercel.com/new
3. Choose **Import Project** and upload the zip.
4. Deploy. Vercel will expose:
   - UI at `/`
   - API at `/api/decode`

After deploy, open the Vercel URL and upload your zip there.

## Large uploads (fix for FUNCTION_PAYLOAD_TOO_LARGE)

This project uses direct-to-blob uploads in hosted mode to avoid Vercel payload limits.

1. In Vercel, add the Environment Variable:

   - `BLOB_READ_WRITE_TOKEN` (from Vercel Blob settings)

2. Deploy again.

The UI will upload the zip to Vercel Blob, then call `/api/decode` with the blob URL.

## Notes

- `pycdas.x86_64` runs only on Linux, so the backend must run on Vercel (not Pages Functions).
- If your zip uploads exceed Vercel size limits, ask for a direct-to-blob upload flow.
