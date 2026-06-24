# Paperloom

Paperloom is an image-to-PDF converter with a dramatic Next.js web interface and a Python conversion API. Choose images, arrange them, tune the paper layout, and download a clean PDF.

## What it does

- Builds multi-page PDFs from JPEG, PNG, WebP, TIFF, BMP, and GIF images.
- Corrects camera orientation from EXIF metadata and safely flattens transparent images onto white.
- Provides thumbnails, drag-and-drop, page reordering, A4/Letter/original sizing, margins, DPI, and JPEG quality controls.
- Keeps the API stateless: uploads are stored only in a request-scoped temporary directory and are removed after conversion.
- Safely flattens transparent images, fixes camera orientation, and writes output atomically.

## Run the web app

Start the Python API in one terminal:

```bash
python3 -m venv .venv
. .venv/bin/activate
python3 -m pip install -e '.[api]'
paperloom-api
```

Then start the Next.js app in another terminal:

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:3000` (or `http://127.0.0.1:3000`). The frontend expects the API on `http://localhost:8000`; set `NEXT_PUBLIC_API_URL` to use another API origin.

### Production API configuration

Set `PAPERLOOM_CORS_ORIGINS` to a comma-separated list of allowed frontend origins, for example:

```bash
PAPERLOOM_CORS_ORIGINS=https://paperloom.example.com paperloom-api
```

By default, the API protects its process from images over 120 million source pixels and exports over 180 million rendered pixels. For a trusted, high-memory server, set either value to `0` to remove that pixel limit:

```bash
PAPERLOOM_MAX_SOURCE_PIXELS=0 PAPERLOOM_MAX_OUTPUT_PIXELS=0 paperloom-api
```

The endpoint limits a request to 40 files, 25 MB per file, and 120 MB total. Adjust these deployment-level limits at a reverse proxy if needed.

## Desktop app (optional)

The original local Tk desktop app is retained. Python's Tk is included with the usual Windows and macOS installers. On Debian/Ubuntu, install `python3-tk`; distribution Pillow users may also need `python3-pil.imagetk`.

```bash
python3 -m pip install -e '.[dnd]'
paperloom
```

## Running the tests

```bash
python3 -m pytest
```

## Notes

`Original` paper size makes each PDF page match the source image proportions at the selected DPI. `A4` and `Letter` fit each image within the configured margins without cropping. The output is a standard PDF, intended for ordinary viewing and printing.

# Image-to-pdf-converter-production
