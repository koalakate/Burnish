"""Thumbnail generator — renders CSM slides as PNG preview images using Pillow."""

from __future__ import annotations

from io import BytesIO

from PIL import Image, ImageDraw, ImageFont

from packages.csm.models import (
    CSM,
    ImageElement,
    ShapeElement,
    Slide,
    TableElement,
    TextElement,
)

# Default render dimensions (pixels)
DEFAULT_WIDTH = 960
DEFAULT_HEIGHT = 540


def generate_thumbnail(
    slide: Slide,
    csm_width: float,
    csm_height: float,
    output_width: int = DEFAULT_WIDTH,
    output_height: int = DEFAULT_HEIGHT,
) -> bytes:
    """Render a single CSM slide to a PNG thumbnail.

    Shapes are drawn as colored rectangles with text overlaid for preview purposes.
    """
    img = Image.new("RGB", (output_width, output_height), color=(255, 255, 255))

    # Apply background
    if slide.background:
        bg = slide.background
        if bg.solid_color:
            c = bg.solid_color
            img = Image.new("RGB", (output_width, output_height), color=(c.r, c.g, c.b))

    draw = ImageDraw.Draw(img)

    # Scale factors from EMU/slide coords to pixel coords
    scale_x = output_width / csm_width if csm_width > 0 else 1.0
    scale_y = output_height / csm_height if csm_height > 0 else 1.0

    for element in slide.elements:
        bbox = element.bbox
        x1 = int(bbox.x * scale_x)
        y1 = int(bbox.y * scale_y)
        x2 = int((bbox.x + bbox.width) * scale_x)
        y2 = int((bbox.y + bbox.height) * scale_y)

        if isinstance(element, TextElement):
            draw.rectangle([x1, y1, x2, y2], outline=(100, 100, 100), width=1)
            text = _extract_text(element)
            if text:
                _draw_text(draw, text, x1 + 4, y1 + 2, x2 - x1 - 8)

        elif isinstance(element, ImageElement):
            draw.rectangle(
                [x1, y1, x2, y2], fill=(220, 220, 240), outline=(150, 150, 200), width=1
            )
            _draw_text(draw, "[Image]", x1 + 4, y1 + 2, x2 - x1 - 8)

        elif isinstance(element, ShapeElement):
            fill = (200, 200, 200)
            if element.fill_color:
                c = element.fill_color
                fill = (c.r, c.g, c.b)
            outline = (100, 100, 100)
            if element.line_color:
                lc = element.line_color
                outline = (lc.r, lc.g, lc.b)
            draw.rectangle([x1, y1, x2, y2], fill=fill, outline=outline, width=1)
            text = ""
            for p in element.paragraphs:
                for r in p.runs:
                    text += r.text
            if text:
                _draw_text(draw, text, x1 + 4, y1 + 2, x2 - x1 - 8)

        elif isinstance(element, TableElement):
            draw.rectangle(
                [x1, y1, x2, y2], fill=(240, 240, 240), outline=(100, 100, 100), width=1
            )
            # Draw grid lines
            if element.rows > 1 and element.cols > 1:
                cell_h = (y2 - y1) / element.rows
                cell_w = (x2 - x1) / element.cols
                for row_i in range(1, element.rows):
                    ry = int(y1 + row_i * cell_h)
                    draw.line([(x1, ry), (x2, ry)], fill=(180, 180, 180))
                for c_idx in range(1, element.cols):
                    cx = int(x1 + c_idx * cell_w)
                    draw.line([(cx, y1), (cx, y2)], fill=(180, 180, 180))

    buf = BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def generate_deck_thumbnails(
    csm: CSM,
    output_width: int = DEFAULT_WIDTH,
    output_height: int = DEFAULT_HEIGHT,
) -> list[bytes]:
    """Generate PNG thumbnails for all slides in a CSM."""
    return [
        generate_thumbnail(slide, csm.width, csm.height, output_width, output_height)
        for slide in csm.slides
    ]


def _extract_text(element: TextElement) -> str:
    """Extract plain text from a TextElement."""
    parts: list[str] = []
    for para in element.paragraphs:
        line = "".join(run.text for run in para.runs)
        if line:
            parts.append(line)
    return "\n".join(parts)


def _draw_text(
    draw: ImageDraw.ImageDraw,
    text: str,
    x: int,
    y: int,
    max_width: int,
) -> None:
    """Draw text within a bounding area, truncating if needed."""
    try:
        font = ImageFont.load_default()
    except Exception:
        font = None

    # Truncate text to fit roughly
    if max_width > 0 and len(text) > max_width // 6:
        text = text[: max_width // 6] + "..."

    # Only draw first few lines
    lines = text.split("\n")[:5]
    current_y = y
    for line in lines:
        draw.text((x, current_y), line, fill=(0, 0, 0), font=font)
        current_y += 14  # Approximate line height
