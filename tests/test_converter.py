from pathlib import Path

from PIL import Image

from img_to_pdf.converter import PdfOptions, convert_images_to_pdf, image_info


def test_image_info_obeys_exif_orientation(tmp_path: Path) -> None:
    source = tmp_path / "rotated.jpg"
    image = Image.new("RGB", (80, 40), "red")
    exif = image.getexif()
    exif[274] = 6
    image.save(source, exif=exif)
    image.close()

    assert image_info(source) == (40, 80)


def test_convert_multiple_images_to_a4_pdf(tmp_path: Path) -> None:
    first = tmp_path / "one.png"
    second = tmp_path / "two.png"
    Image.new("RGBA", (160, 80), (255, 0, 0, 128)).save(first)
    Image.new("RGB", (80, 160), "blue").save(second)
    output = tmp_path / "combined.pdf"

    result = convert_images_to_pdf(
        [first, second],
        output,
        PdfOptions(paper_size="A4", margin_mm=8, dpi=150, quality=90),
    )

    assert result == output
    assert output.exists()
    assert output.read_bytes().startswith(b"%PDF")

