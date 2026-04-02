"""PPTX exporter — applies corrected CSM back to the original .pptx file."""

from __future__ import annotations

import io
import logging
from pathlib import Path

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.shapes.base import BaseShape
from pptx.util import Emu, Pt

from packages.csm.models import (
    CSM,
    Color,
    Paragraph,
    ShapeElement,
    SlideElement,
    TableElement,
    TextElement,
)

logger = logging.getLogger(__name__)


def export_pptx(original_pptx_path: Path, corrected_csm: CSM) -> bytes:
    """Apply corrections from a CSM back to the original PPTX and return bytes.

    Opens the original PPTX, walks each slide's shapes, and patches
    properties that differ in the corrected CSM.  Elements not present in
    the CSM (or not modified) are left untouched — preserving animations,
    transitions, notes, media, and any other content python-pptx doesn't
    model.
    """
    prs = Presentation(str(original_pptx_path))

    # Build a lookup: (slide_index, element_id) -> CSM element
    elem_lookup: dict[tuple[int, str], SlideElement] = {}
    for slide in corrected_csm.slides:
        for elem in slide.elements:
            elem_lookup[(slide.index, elem.id)] = elem

    for slide_idx, pptx_slide in enumerate(prs.slides):
        for shape in pptx_slide.shapes:
            _apply_shape(shape, slide_idx, elem_lookup)

    buf = io.BytesIO()
    prs.save(buf)
    return buf.getvalue()


def _apply_shape(
    shape: BaseShape,
    slide_idx: int,
    lookup: dict[tuple[int, str], SlideElement],
) -> None:
    """Apply CSM corrections to a single shape, recursing into groups."""
    from pptx.enum.shapes import MSO_SHAPE_TYPE
    from pptx.shapes.group import GroupShape

    if shape.shape_type == MSO_SHAPE_TYPE.GROUP:
        group: GroupShape = shape  # type: ignore[assignment]
        for child in group.shapes:
            _apply_shape(child, slide_idx, lookup)
        return

    shape_id = str(shape.shape_id)
    csm_elem = lookup.get((slide_idx, shape_id))
    if csm_elem is None:
        return

    # Apply bounding box (position/size) changes
    _apply_bbox(shape, csm_elem)

    if csm_elem.type == "text":
        assert isinstance(csm_elem, TextElement)
        _apply_text_element(shape, csm_elem)
    elif csm_elem.type == "shape":
        assert isinstance(csm_elem, ShapeElement)
        _apply_shape_element(shape, csm_elem)
    elif csm_elem.type == "table":
        assert isinstance(csm_elem, TableElement)
        _apply_table_element(shape, csm_elem)
    # Images: no text/color corrections needed — bbox already handled above


def _apply_bbox(shape: BaseShape, csm_elem: SlideElement) -> None:
    """Update shape position and size from CSM bounding box."""
    bbox = csm_elem.bbox
    shape.left = Emu(int(bbox.x))
    shape.top = Emu(int(bbox.y))
    shape.width = Emu(int(bbox.width))
    shape.height = Emu(int(bbox.height))


def _apply_text_element(shape: BaseShape, csm_elem: TextElement) -> None:
    """Apply text-level corrections (font, color, size) to a text frame."""
    if not shape.has_text_frame:
        return
    tf = shape.text_frame  # type: ignore[attr-defined]
    _apply_paragraphs(tf.paragraphs, csm_elem.paragraphs)


def _apply_shape_element(shape: BaseShape, csm_elem: ShapeElement) -> None:
    """Apply corrections to an auto-shape (fill, line, text)."""
    # Fill color
    if csm_elem.fill_color is not None:
        _apply_fill_color(shape, csm_elem.fill_color)

    # Line color
    if csm_elem.line_color is not None:
        try:
            shape.line.color.rgb = _to_rgb(csm_elem.line_color)  # type: ignore[attr-defined]
        except (AttributeError, TypeError):
            pass

    # Text inside shapes
    if shape.has_text_frame and csm_elem.paragraphs:
        tf = shape.text_frame  # type: ignore[attr-defined]
        _apply_paragraphs(tf.paragraphs, csm_elem.paragraphs)


def _apply_table_element(shape: BaseShape, csm_elem: TableElement) -> None:
    """Apply corrections to table cells."""
    if not shape.has_table:
        return
    table = shape.table  # type: ignore[attr-defined]

    # Build cell lookup by (row, col)
    csm_cells = {(c.row, c.col): c for c in csm_elem.cells}

    for row_idx, row in enumerate(table.rows):
        for col_idx, cell in enumerate(row.cells):
            csm_cell = csm_cells.get((row_idx, col_idx))
            if csm_cell is None:
                continue

            # Cell fill color
            if csm_cell.fill_color is not None:
                _apply_cell_fill(cell, csm_cell.fill_color)

            # Cell text
            _apply_paragraphs(
                cell.text_frame.paragraphs,
                csm_cell.paragraphs,
            )


def _apply_paragraphs(
    pptx_paras: list,  # type: ignore[type-arg]
    csm_paras: list[Paragraph],
) -> None:
    """Sync font/color changes from CSM paragraphs to python-pptx paragraphs."""
    for p_idx, csm_para in enumerate(csm_paras):
        if p_idx >= len(pptx_paras):
            break
        pptx_para = pptx_paras[p_idx]
        pptx_runs = list(pptx_para.runs)
        for r_idx, csm_run in enumerate(csm_para.runs):
            if r_idx >= len(pptx_runs):
                break
            pptx_run = pptx_runs[r_idx]

            # Font family
            if csm_run.font.family is not None:
                pptx_run.font.name = csm_run.font.family

            # Font size
            if csm_run.font.size_pt is not None:
                pptx_run.font.size = Pt(csm_run.font.size_pt)

            # Bold / weight
            if csm_run.font.weight is not None:
                pptx_run.font.bold = csm_run.font.weight >= 700

            # Italic — only set if explicitly specified to avoid overriding theme inheritance
            if csm_run.font.italic is not None:
                pptx_run.font.italic = csm_run.font.italic

            # Underline — only set if explicitly specified
            if csm_run.font.underline is not None:
                pptx_run.font.underline = csm_run.font.underline

            # Text color
            if csm_run.color is not None:
                pptx_run.font.color.rgb = _to_rgb(csm_run.color)


def _apply_fill_color(shape: BaseShape, color: Color) -> None:
    """Set solid fill color on a shape."""
    try:
        shape.fill.solid()  # type: ignore[attr-defined]
        shape.fill.fore_color.rgb = _to_rgb(color)  # type: ignore[attr-defined]
    except (AttributeError, TypeError):
        logger.warning("Could not apply fill color to shape %s", shape.shape_id)


def _apply_cell_fill(cell: object, color: Color) -> None:  # noqa: ANN001
    """Set solid fill color on a table cell via XML manipulation."""
    try:
        from lxml import etree

        ns = "http://schemas.openxmlformats.org/drawingml/2006/main"
        tc = cell._tc  # type: ignore[attr-defined]
        tc_pr = tc.find(f"{{{ns}}}tcPr")
        if tc_pr is None:
            tc_pr = etree.SubElement(tc, f"{{{ns}}}tcPr")

        # Remove existing fills
        for old_fill in tc_pr.findall(f"{{{ns}}}solidFill"):
            tc_pr.remove(old_fill)

        solid_fill = etree.SubElement(tc_pr, f"{{{ns}}}solidFill")
        srgb = etree.SubElement(solid_fill, f"{{{ns}}}srgbClr")
        srgb.set("val", color.hex.lstrip("#"))
    except Exception:
        logger.warning("Could not apply cell fill color")


def _to_rgb(color: Color) -> RGBColor:
    """Convert a CSM Color to a python-pptx RGBColor."""
    return RGBColor(color.r, color.g, color.b)  # type: ignore[no-untyped-call]
