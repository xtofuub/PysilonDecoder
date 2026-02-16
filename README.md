# Token Decoder (Vercel)

Upload a zip that contains a single PyInstaller `.exe`. The server extracts it, finds `source_prepared.pyc`, and returns the first decoded token it can recover.

## How it works

1. The browser uploads the zip to Vercel Blob.
2. The app calls `/api/decode` with the blob URL.
3. The server downloads the zip, extracts it, and scans for the token.
4. The blob is deleted after a successful decode.

## Deploy to Vercel

1. Zip the project root (include `pycdas.x86_64`).
2. Go to https://vercel.com/new
3. Choose **Import Project** and upload the zip.
4. Deploy.

Vercel will expose:
- UI at `/`
- API at `/api/decode`

## Environment variables

Add this in your Vercel project settings (Storage tab):

- `BLOB_READ_WRITE_TOKEN`

This enables direct uploads to Vercel Blob and cleanup after decoding.

## Limits and notes

- Max zip size is 150 MB.
- The backend runs on Linux; `pycdas.x86_64` is required.
- Blob files are deleted only after a successful decode.
