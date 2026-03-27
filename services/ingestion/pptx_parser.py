"""PPTX parser — reads a .pptx file and converts it to a Canonical Slide Model."""

from __future__ import annotations

import io
from pathlib import Path
from typing import Any

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE_TYPE
from pptx.shapes.base import BaseShape
from pptx.shapes.group import GroupShape
from pptx.shapes.picture import Picture
from pptx.shapes.placeholder import _InheritsDimensions
from pptx.slide import Slide as PptxSlide
from pptx.util import Emu

from packages.csm.models import (
    CSM,
    BoundingBox,
    Color,
    Font,
    ImageElement,
    Paragraph,
    ShapeElement,
    Slide,
    SlideBackground,
    SlideElement,
    TableCell,
    TableElement,
    TextElement,
    TextRun,
)


def parse_pptx(file_path: Path | str) -> CSM:
    """Parse a .pptx file and return a Canonical Slide Model."""
    prs = Presentation(str(file_path))

    width = float(prs.slide_width or Emu(9144000))  # default 10 inches
    height = float(prs.slide_height or Emu(6858000))  # default 7.5 inches
    title = _extract_title(prs)
    author = _extract_author(prs)

    slides: list[Slide] = []
    for idx, pptx_slide in enumerate(prs.slides):
        slides.append(_parse_slide(idx, pptx_slide))

    return CSM(
        slides=slides,
        width=width,
        height=height,
        title=title,
        author=author,
    )


def _extract_title(prs: Any) -> str | None:
    """Extract presentation title from core properties."""
    try:
        return prs.core_properties.title or None
    except Exception:
        return None


def _extract_author(prs: Any) -> str | None:
    """Extract author from core properties."""
    try:
        return prs.core_properties.author or None
    except Exception:
        return None


def _parse_slide(index: int, pptx_slide: PptxSlide) -> Slide:
    """Parse a single slide into a CSM Slide."""
    elements: list[SlideElement] = []
    for shape in pptx_slide.shapes:
        elements.extend(_parse_shape(shape))

    background = _parse_background(pptx_slide)
    notes = _parse_notes(pptx_slide)
    layout_name = _get_layout_name(pptx_slide)

    return Slide(
        index=index,
        elements=elements,
        background=background,
        notes=notes,
        layout_name=layout_name,
    )


def _parse_shape(shape: BaseShape) -> list[SlideElement]:
    """Parse a shape into one or more CSM elements, recursing into groups."""
    # Grouped shapes — recurse
    if shape.shape_type == MSO_SHAPE_TYPE.GROUP:
        elements: list[SlideElement] = []
        group: GroupShape = shape  # type: ignore[assignment]
        for child in group.shapes:
            elements.extend(_parse_shape(child))
        return elements

    # Table
    if shape.has_table:
        return [_parse_table(shape)]

    # Picture / image
    if shape.shape_type == MSO_SHAPE_TYPE.PICTURE or (
        shape.shape_type == MSO_SHAPE_TYPE.PLACEHOLDER and _is_picture_placeholder(shape)
    ):
        return [_parse_image(shape)]

    # Auto-shapes: shapes with an explicit geometric shape type (not freeform/text boxes)
    if shape.shape_type is not None and shape.shape_type not in (
        MSO_SHAPE_TYPE.TEXT_BOX,
        MSO_SHAPE_TYPE.PLACEHOLDER,
        MSO_SHAPE_TYPE.FREEFORM,
    ):
        return [_parse_shape_element(shape)]

    # Text frame (text boxes, placeholders)
    if shape.has_text_frame:
        return [_parse_text_element(shape)]

    # Fallback: treat as shape
    return [_parse_shape_element(shape)]


def _is_picture_placeholder(shape: BaseShape) -> bool:
    """Check if a placeholder contains a picture."""
    return isinstance(shape, Picture) or (
        isinstance(shape, _InheritsDimensions) and hasattr(shape, "image")
    )


def _bbox(shape: BaseShape) -> BoundingBox:
    """Extract bounding box from a shape."""
    return BoundingBox(
        x=float(shape.left or 0),
        y=float(shape.top or 0),
        width=float(shape.width or 0),
        height=float(shape.height or 0),
    )


def _rgb_to_color(rgb: RGBColor | None, alpha: float = 1.0) -> Color | None:
    """Convert an RGBColor to a CSM Color."""
    if rgb is None:
        return None
    r, g, b = int(rgb[0]), int(rgb[1]), int(rgb[2])
    hex_str = f"#{r:02X}{g:02X}{b:02X}"
    return Color(hex=hex_str, r=r, g=g, b=b, a=alpha)


def _resolve_font(run: Any, slide_master_font: Font | None = None) -> Font:
    """Extract font properties from a text run, falling back to slide master defaults."""
    pptx_font = run.font

    family = pptx_font.name
    size_pt: float | None = None
    if pptx_font.size is not None:
        size_pt = float(pptx_font.size) / 12700.0  # EMU to points

    weight: int | None = None
    if pptx_font.bold is True:
        weight = 700
    elif pptx_font.bold is False:
        weight = 400

    italic = pptx_font.italic or False
    underline = pptx_font.underline or False

    # Fall back to slide master defaults for unset properties
    if slide_master_font:
        if family is None:
            family = slide_master_font.family
        if size_pt is None:
            size_pt = slide_master_font.size_pt
        if weight is None:
            weight = slide_master_font.weight
        if not italic and slide_master_font.italic:
            italic = slide_master_font.italic

    return Font(
        family=family,
        weight=weight,
        size_pt=size_pt,
        italic=italic,
        underline=bool(underline),
    )


def _get_run_color(run: Any) -> Color | None:
    """Extract color from a text run, returning None if theme/inherited."""
    try:
        font = run.font
        if font.color and font.color.rgb is not None:
            return _rgb_to_color(font.color.rgb)
    except (AttributeError, TypeError):
        pass
    return None


def _get_slide_master_font(pptx_slide: PptxSlide) -> Font | None:
    """Extract default font from the slide layout/master for fallback."""
    try:
        layout = pptx_slide.slide_layout
        master = layout.slide_master
        body_style = master.element.findall(
            ".//{http://schemas.openxmlformats.org/drawingml/2006/main}defRPr"
        )
        if body_style:
            ns = {"a": "http://schemas.openxmlformats.org/drawingml/2006/main"}
            def_rpr = body_style[0]
            family = None
            size_pt = None

            latin = def_rpr.findall("a:latin", ns)
            if latin:
                family = latin[0].get("typeface")

            sz = def_rpr.get("sz")
            if sz:
                size_pt = int(sz) / 100.0

            if family or size_pt:
                return Font(family=family, size_pt=size_pt)
    except Exception:
        pass
    return None


def _parse_paragraph(para: Any, master_font: Font | None = None) -> Paragraph:
    """Parse a python-pptx paragraph to a CSM Paragraph."""
    alignment = None
    if para.alignment is not None:
        alignment = str(para.alignment).split("(")[0].strip() if para.alignment else None

    level = para.level or 0

    runs: list[TextRun] = []
    for run in para.runs:
        font = _resolve_font(run, master_font)
        color = _get_run_color(run)
        hyperlink_url = None
        try:
            if run.hyperlink and run.hyperlink.address:
                hyperlink_url = run.hyperlink.address
        except Exception:
            pass

        runs.append(
            TextRun(
                text=run.text,
                font=font,
                color=color,
                hyperlink=hyperlink_url,
            )
        )

    return Paragraph(runs=runs, alignment=alignment, level=level)


def _parse_text_element(shape: BaseShape) -> TextElement:
    """Parse a shape with a text frame into a CSM TextElement."""
    tf = shape.text_frame  # type: ignore[attr-defined]
    role = _get_placeholder_role(shape)
    paragraphs = [_parse_paragraph(p) for p in tf.paragraphs]

    return TextElement(
        id=str(shape.shape_id),
        name=shape.name or "",
        bbox=_bbox(shape),
        paragraphs=paragraphs,
        role=role,
    )


def _get_placeholder_role(shape: BaseShape) -> str | None:
    """Map placeholder type to semantic role."""
    if not shape.is_placeholder:
        return None
    try:
        ph_idx = shape.placeholder_format.idx
        ph_type = shape.placeholder_format.type
        type_val = int(ph_type) if ph_type is not None else None
        role_map: dict[int, str] = {
            0: "title",
            1: "body",
            2: "title",
            3: "subtitle",
            12: "title",
            13: "body",
            14: "body",
            15: "caption",
        }
        if type_val is not None:
            return role_map.get(type_val)
        if ph_idx == 0:
            return "title"
        if ph_idx == 1:
            return "body"
    except Exception:
        pass
    return None


def _parse_image(shape: BaseShape) -> ImageElement:
    """Parse a picture shape into a CSM ImageElement."""
    image_bytes: bytes | None = None
    content_type: str | None = None
    dpi: float | None = None
    original_width: int | None = None
    original_height: int | None = None
    alt_text: str | None = None

    try:
        pic: Picture = shape  # type: ignore[assignment]
        image = pic.image
        image_bytes = image.blob
        content_type = image.content_type

        try:
            from PIL import Image as PILImage

            img = PILImage.open(io.BytesIO(image_bytes))
            original_width, original_height = img.size
            img_dpi = img.info.get("dpi")
            if img_dpi:
                dpi = float(img_dpi[0])
        except Exception:
            pass
    except (AttributeError, TypeError):
        pass

    try:
        alt_text = shape._element.attrib.get("descr") or None
        if alt_text is None:
            nv_sp_pr = shape._element.find(
                ".//{http://schemas.openxmlformats.org/drawingml/2006/spreadsheetml}cNvPr"
            )
            if nv_sp_pr is not None:
                alt_text = nv_sp_pr.get("descr")
    except Exception:
        pass

    return ImageElement(
        id=str(shape.shape_id),
        name=shape.name or "",
        bbox=_bbox(shape),
        image_bytes=image_bytes,
        content_type=content_type,
        alt_text=alt_text,
        dpi=dpi,
        original_width=original_width,
        original_height=original_height,
    )


def _parse_shape_element(shape: BaseShape) -> ShapeElement:
    """Parse an auto-shape into a CSM ShapeElement."""
    fill_color: Color | None = None
    line_color: Color | None = None
    line_width: float | None = None
    shape_type_name: str | None = None

    try:
        if shape.shape_type is not None:
            shape_type_name = str(shape.shape_type)
    except Exception:
        pass

    try:
        fill = shape.fill  # type: ignore[attr-defined]
        if fill.type is not None:
            try:
                fore_color = fill.fore_color
                if fore_color.rgb is not None:
                    fill_color = _rgb_to_color(fore_color.rgb)
            except (AttributeError, TypeError):
                pass
    except Exception:
        pass

    try:
        ln = shape.line  # type: ignore[attr-defined]
        if ln.fill.type is not None:
            try:
                if ln.color.rgb is not None:
                    line_color = _rgb_to_color(ln.color.rgb)
            except (AttributeError, TypeError):
                pass
        if ln.width is not None:
            line_width = float(ln.width) / 12700.0  # EMU to points
    except Exception:
        pass

    paragraphs: list[Paragraph] = []
    if shape.has_text_frame:
        for p in shape.text_frame.paragraphs:  # type: ignore[attr-defined]
            paragraphs.append(_parse_paragraph(p))

    return ShapeElement(
        id=str(shape.shape_id),
        name=shape.name or "",
        bbox=_bbox(shape),
        shape_type=shape_type_name,
        fill_color=fill_color,
        line_color=line_color,
        line_width=line_width,
        paragraphs=paragraphs,
    )


def _parse_table(shape: BaseShape) -> TableElement:
    """Parse a table shape into a CSM TableElement."""
    table = shape.table  # type: ignore[attr-defined]
    rows = len(table.rows)
    cols = len(table.columns)

    cells: list[TableCell] = []
    for row_idx, row in enumerate(table.rows):
        for col_idx, cell in enumerate(row.cells):
            paragraphs = [_parse_paragraph(p) for p in cell.text_frame.paragraphs]
            fill_color: Color | None = None
            try:
                tc_pr = cell._tc.tcPr
                if tc_pr is not None:
                    solid_fill = tc_pr.find(
                        "{http://schemas.openxmlformats.org/drawingml/2006/main}solidFill"
                    )
                    if solid_fill is not None:
                        srgb_clr = solid_fill.find(
                            "{http://schemas.openxmlformats.org/drawingml/2006/main}srgbClr"
                        )
                        if srgb_clr is not None:
                            hex_val = srgb_clr.get("val", "")
                            if hex_val:
                                r = int(hex_val[0:2], 16)
                                g = int(hex_val[2:4], 16)
                                b = int(hex_val[4:6], 16)
                                fill_color = Color(
                                    hex=f"#{hex_val}", r=r, g=g, b=b
                                )
            except Exception:
                pass

            row_span = cell.span_height if hasattr(cell, "span_height") else 1
            col_span = cell.span_width if hasattr(cell, "span_width") else 1

            cells.append(
                TableCell(
                    row=row_idx,
                    col=col_idx,
                    paragraphs=paragraphs,
                    fill_color=fill_color,
                    row_span=row_span,
                    col_span=col_span,
                )
            )

    return TableElement(
        id=str(shape.shape_id),
        name=shape.name or "",
        bbox=_bbox(shape),
        rows=rows,
        cols=cols,
        cells=cells,
    )


def _parse_background(pptx_slide: PptxSlide) -> SlideBackground | None:
    """Extract the slide background."""
    try:
        bg = pptx_slide.background
        fill = bg.fill

        if fill.type is not None:
            from pptx.enum.dml import MSO_FILL

            if fill.type == MSO_FILL.SOLID:
                try:
                    rgb = fill.fore_color.rgb
                    if rgb:
                        return SlideBackground(solid_color=_rgb_to_color(rgb))
                except (AttributeError, TypeError):
                    pass

            elif fill.type == MSO_FILL.GRADIENT:
                colors: list[Color] = []
                try:
                    for stop in fill.gradient_stops:
                        rgb = stop.color.rgb
                        if rgb:
                            c = _rgb_to_color(rgb)
                            if c:
                                colors.append(c)
                except (AttributeError, TypeError):
                    pass
                if colors:
                    return SlideBackground(gradient_colors=colors)
    except Exception:
        pass
    return None


def _parse_notes(pptx_slide: PptxSlide) -> str | None:
    """Extract speaker notes from a slide."""
    try:
        if pptx_slide.has_notes_slide:
            notes_slide = pptx_slide.notes_slide
            text = notes_slide.notes_text_frame.text  # type: ignore[union-attr]
            return text if text.strip() else None
    except Exception:
        return None
    return None


def _get_layout_name(pptx_slide: PptxSlide) -> str | None:
    """Get the slide layout name."""
    try:
        return pptx_slide.slide_layout.name or None
    except Exception:
        return None
