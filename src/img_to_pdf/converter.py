"""Reliable, UI-independent image-to-PDF conversion utilities."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable, Literal
import os
import tempfile

from PIL import Image, ImageOps, UnidentifiedImageError

SUPPORTED_EXTENSIONS = frozenset({".jpg", ".jpeg", ".png", ".webp", ".tif", ".tiff", ".bmp", ".gif"})
ProgressCallback = Callable[[int, int, Path], None]

_PAPER_POINTS = {
    "A4": (595.276, 841.890),
    "Letter": (612.0, 792.0),
}
DEFAULT_MAX_SOURCE_PIXELS = 120_000_000
DEFAULT_MAX_TOTAL_OUTPUT_PIXELS = 180_000_000
_LANCZOS = getattr(getattr(Image, "Resampling", Image), "LANCZOS")


class ConversionError(RuntimeError):
    """Raised when one or more selected images cannot be converted safely."""


@dataclass(frozen=True)
class PdfOptions:
    """Layout and compression options for a PDF export."""

    paper_size: Literal["A4", "Letter", "Original"] = "A4"
    orientation: Literal["Auto", "Portrait", "Landscape"] = "Auto"
    margin_mm: float = 10.0
    dpi: int = 300
    quality: int = 92

    def validate(self) -> None:
        if self.paper_size not in {*_PAPER_POINTS, "Original"}:
            raise ValueError("Paper size must be A4, Letter, or Original.")
        if self.orientation not in {"Auto", "Portrait", "Landscape"}:
            raise ValueError("Orientation must be Auto, Portrait, or Landscape.")
        if not 0 <= self.margin_mm <= 100:
            raise ValueError("Margin must be between 0 and 100 mm.")
        if not 72 <= self.dpi <= 600:
            raise ValueError("DPI must be between 72 and 600.")
        if not 1 <= self.quality <= 100:
            raise ValueError("Quality must be between 1 and 100.")


def is_supported_image(path: str | Path) -> bool:
    return Path(path).suffix.lower() in SUPPORTED_EXTENSIONS


def image_info(
    path: str | Path,
    max_source_pixels: int | None = DEFAULT_MAX_SOURCE_PIXELS,
) -> tuple[int, int]:
    """Return display-corrected image dimensions without retaining the image in memory."""
    source = Path(path)
    try:
        with Image.open(source) as image:
            _check_source_pixel_limit(source, image.size, max_source_pixels)
            corrected = ImageOps.exif_transpose(image)
            return corrected.size
    except (OSError, UnidentifiedImageError) as exc:
        raise ConversionError(f"Could not read '{source.name}' as an image.") from exc


def convert_images_to_pdf(
    image_paths: Iterable[str | Path],
    output_path: str | Path,
    options: PdfOptions | None = None,
    progress: ProgressCallback | None = None,
    max_source_pixels: int | None = DEFAULT_MAX_SOURCE_PIXELS,
    max_total_output_pixels: int | None = DEFAULT_MAX_TOTAL_OUTPUT_PIXELS,
) -> Path:
    """Convert ordered image paths to one PDF, atomically replacing the final file.

    The returned path is the finished PDF. Any failed conversion leaves an existing
    destination untouched and cleans up the temporary output.
    """
    settings = options or PdfOptions()
    settings.validate()
    paths = [Path(item).expanduser() for item in image_paths]
    if not paths:
        raise ConversionError("Add at least one image before converting.")

    destination = Path(output_path).expanduser()
    if destination.suffix.lower() != ".pdf":
        destination = destination.with_suffix(".pdf")
    try:
        destination.parent.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise ConversionError(f"Could not create output folder '{destination.parent}'.") from exc

    _check_output_memory_budget(paths, settings, max_source_pixels, max_total_output_pixels)

    pages: list[Image.Image] = []
    temp_name: str | None = None
    try:
        for index, source in enumerate(paths, start=1):
            if not source.is_file():
                raise ConversionError(f"Image not found: {source}")
            if not is_supported_image(source):
                raise ConversionError(f"Unsupported image type: {source.name}")
            page = _prepare_page(source, settings, max_source_pixels)
            pages.append(page)
            if progress:
                progress(index, len(paths), source)

        with tempfile.NamedTemporaryFile(
            prefix=f".{destination.stem}-", suffix=".pdf", dir=destination.parent, delete=False
        ) as temp_file:
            temp_name = temp_file.name

        pages[0].save(
            temp_name,
            format="PDF",
            save_all=True,
            append_images=pages[1:],
            resolution=settings.dpi,
            quality=settings.quality,
            title=destination.stem,
        )
        os.replace(temp_name, destination)
        temp_name = None
        return destination
    except (OSError, UnidentifiedImageError, ValueError) as exc:
        if isinstance(exc, ConversionError):
            raise
        raise ConversionError(f"PDF conversion failed: {exc}") from exc
    finally:
        for page in pages:
            page.close()
        if temp_name:
            try:
                Path(temp_name).unlink(missing_ok=True)
            except OSError:
                pass


def _prepare_page(source: Path, options: PdfOptions, max_source_pixels: int | None) -> Image.Image:
    with Image.open(source) as opened:
        _check_source_pixel_limit(source, opened.size, max_source_pixels)
        normalized = ImageOps.exif_transpose(opened)
        normalized.load()
        image = _flatten_to_rgb(normalized)

    if options.paper_size == "Original":
        return image

    width_pt, height_pt = _paper_dimensions(options, image.size)
    page_width = round(width_pt / 72 * options.dpi)
    page_height = round(height_pt / 72 * options.dpi)
    margin = round(options.margin_mm / 25.4 * options.dpi)
    available_width = page_width - margin * 2
    available_height = page_height - margin * 2
    if available_width <= 0 or available_height <= 0:
        image.close()
        raise ConversionError("Margin leaves no printable area on the selected page size.")

    image.thumbnail((available_width, available_height), _LANCZOS)
    page = Image.new("RGB", (page_width, page_height), "white")
    offset = ((page_width - image.width) // 2, (page_height - image.height) // 2)
    page.paste(image, offset)
    image.close()
    return page


def _check_source_pixel_limit(source: Path, size: tuple[int, int], max_source_pixels: int | None) -> None:
    if max_source_pixels is not None and size[0] * size[1] > max_source_pixels:
        raise ConversionError(f"{source.name} exceeds the configured {max_source_pixels:,} source-pixel limit.")


def _check_output_memory_budget(
    paths: list[Path],
    options: PdfOptions,
    max_source_pixels: int | None,
    max_total_output_pixels: int | None,
) -> None:
    """Reject exports that would make Pillow retain an unsafe number of pixels in RAM."""
    if options.paper_size == "Original":
        estimated_pixels = sum(
            width * height for width, height in (image_info(path, max_source_pixels) for path in paths)
        )
    else:
        width_pt, height_pt = _PAPER_POINTS[options.paper_size]
        page_pixels = round(width_pt / 72 * options.dpi) * round(height_pt / 72 * options.dpi)
        estimated_pixels = page_pixels * len(paths)
    if max_total_output_pixels is not None and estimated_pixels > max_total_output_pixels:
        raise ConversionError(
            "This export exceeds the configured output-pixel limit. "
            "Ask the server administrator to raise PAPERLOOM_MAX_OUTPUT_PIXELS."
        )


def _flatten_to_rgb(image: Image.Image) -> Image.Image:
    """Create an RGB image, compositing alpha channels over a white page."""
    if image.mode in {"RGBA", "LA"} or (image.mode == "P" and "transparency" in image.info):
        rgba = image.convert("RGBA")
        background = Image.new("RGBA", rgba.size, "white")
        background.alpha_composite(rgba)
        rgb = background.convert("RGB")
        rgba.close()
        background.close()
        return rgb
    return image.convert("RGB")


def _paper_dimensions(options: PdfOptions, image_size: tuple[int, int]) -> tuple[float, float]:
    width, height = _PAPER_POINTS[options.paper_size]
    source_landscape = image_size[0] > image_size[1]
    landscape = (
        options.orientation == "Landscape"
        or (options.orientation == "Auto" and source_landscape)
    )
    return (height, width) if landscape else (width, height)
