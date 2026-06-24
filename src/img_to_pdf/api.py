"""Stateless FastAPI service for the Paperloom web client."""

from __future__ import annotations

import asyncio
import os
import shutil
import tempfile
from pathlib import Path
from typing import Annotated, Literal

from fastapi import FastAPI, File, Form, HTTPException, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response

from .converter import ConversionError, PdfOptions, SUPPORTED_EXTENSIONS, convert_images_to_pdf

MAX_FILES = 40
MAX_FILE_BYTES = 25 * 1024 * 1024
MAX_TOTAL_BYTES = 120 * 1024 * 1024
CHUNK_SIZE = 1024 * 1024


def _cors_origins() -> list[str]:
    configured = os.environ.get(
        "PAPERLOOM_CORS_ORIGINS",
        "http://localhost:3000,http://127.0.0.1:3000",
    )
    return [origin.strip() for origin in configured.split(",") if origin.strip()]


app = FastAPI(
    title="Paperloom API",
    version="1.0.0",
    description="Stateless, safe image-to-PDF conversion for the Paperloom web application.",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins(),
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)


@app.get("/health", tags=["service"])
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/convert", response_class=Response, tags=["conversion"])
async def convert(
    files: Annotated[list[UploadFile], File(description="Ordered image files")],
    page_size: Annotated[Literal["A4", "Letter", "Original"], Form()] = "A4",
    orientation: Annotated[Literal["Auto", "Portrait", "Landscape"], Form()] = "Auto",
    margin_mm: Annotated[float, Form(ge=0, le=100)] = 10,
    dpi: Annotated[int, Form(ge=72, le=600)] = 300,
    quality: Annotated[int, Form(ge=1, le=100)] = 92,
) -> Response:
    """Convert uploaded files in their multipart order and return a downloadable PDF."""
    if not files:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Upload at least one image.")
    if len(files) > MAX_FILES:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail=f"A maximum of {MAX_FILES} images is allowed per export.")

    options = PdfOptions(page_size, orientation, margin_mm, dpi, quality)
    temporary_directory = Path(tempfile.mkdtemp(prefix="paperloom-"))
    total_bytes = 0
    try:
        uploaded_paths: list[Path] = []
        for position, upload in enumerate(files, start=1):
            source_name = Path(upload.filename or "").name
            extension = Path(source_name).suffix.lower()
            if not source_name or extension not in SUPPORTED_EXTENSIONS:
                raise HTTPException(
                    status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                    detail=f"'{source_name or 'unnamed file'}' is not a supported image.",
                )
            stored_path = temporary_directory / f"{position:03d}{extension}"
            file_bytes = await _save_upload(upload, stored_path, total_bytes)
            total_bytes += file_bytes
            uploaded_paths.append(stored_path)

        output_path = temporary_directory / "paperloom.pdf"
        try:
            await asyncio.to_thread(convert_images_to_pdf, uploaded_paths, output_path, options)
        except ConversionError as exc:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc

        pdf = await asyncio.to_thread(output_path.read_bytes)
        return Response(
            content=pdf,
            media_type="application/pdf",
            headers={
                "Content-Disposition": 'attachment; filename="paperloom.pdf"',
                "Cache-Control": "no-store",
            },
        )
    finally:
        for upload in files:
            await upload.close()
        shutil.rmtree(temporary_directory, ignore_errors=True)


async def _save_upload(upload: UploadFile, destination: Path, bytes_so_far: int) -> int:
    """Stream an upload to disk, enforcing individual and total request limits."""
    written = 0
    try:
        with destination.open("wb") as handle:
            while chunk := await upload.read(CHUNK_SIZE):
                written += len(chunk)
                if written > MAX_FILE_BYTES:
                    raise HTTPException(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        detail=f"'{Path(upload.filename or 'image').name}' exceeds the 25 MB per-file limit.",
                    )
                if bytes_so_far + written > MAX_TOTAL_BYTES:
                    raise HTTPException(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        detail="The combined upload exceeds the 120 MB request limit.",
                    )
                handle.write(chunk)
    except OSError as exc:
        raise HTTPException(status_code=status.HTTP_507_INSUFFICIENT_STORAGE, detail="The server could not store the upload.") from exc
    return written


def main() -> None:
    """Launch a development-friendly ASGI server."""
    import uvicorn

    uvicorn.run("img_to_pdf.api:app", host="0.0.0.0", port=8000, reload=False)
