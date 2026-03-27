"""Canonical Slide Model (CSM) — format-agnostic representation of a presentation."""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, Field


class Color(BaseModel):
    """A color with hex and RGBA components."""

    hex: str = Field(description="Hex color string, e.g. '#FF0000'")
    r: int = Field(ge=0, le=255)
    g: int = Field(ge=0, le=255)
    b: int = Field(ge=0, le=255)
    a: float = Field(default=1.0, ge=0.0, le=1.0)


class Font(BaseModel):
    """Font specification for a text run."""

    family: str | None = None
    weight: int | None = Field(default=None, ge=100, le=900)
    size_pt: float | None = None
    italic: bool = False
    underline: bool = False


class BoundingBox(BaseModel):
    """Position and size of an element on a slide, in EMU or points."""

    x: float
    y: float
    width: float
    height: float


class TextRun(BaseModel):
    """A contiguous run of text with uniform formatting."""

    text: str
    font: Font = Field(default_factory=Font)
    color: Color | None = None
    hyperlink: str | None = None


class Paragraph(BaseModel):
    """A paragraph containing one or more text runs."""

    runs: list[TextRun] = Field(default_factory=list)
    alignment: str | None = None
    level: int = 0


class TextElement(BaseModel):
    """A text box or placeholder on a slide."""

    type: Literal["text"] = "text"
    id: str = ""
    name: str = ""
    bbox: BoundingBox
    paragraphs: list[Paragraph] = Field(default_factory=list)
    role: str | None = Field(
        default=None, description="Semantic role: title, body, caption, subtitle, etc."
    )


class ImageElement(BaseModel):
    """An image on a slide."""

    type: Literal["image"] = "image"
    id: str = ""
    name: str = ""
    bbox: BoundingBox
    image_bytes: bytes | None = Field(default=None, exclude=True)
    content_type: str | None = None
    alt_text: str | None = None
    dpi: float | None = None
    original_width: int | None = None
    original_height: int | None = None


class ShapeElement(BaseModel):
    """An auto-shape (rectangle, oval, arrow, etc.) on a slide."""

    type: Literal["shape"] = "shape"
    id: str = ""
    name: str = ""
    bbox: BoundingBox
    shape_type: str | None = None
    fill_color: Color | None = None
    line_color: Color | None = None
    line_width: float | None = None
    paragraphs: list[Paragraph] = Field(default_factory=list)


class TableCell(BaseModel):
    """A single cell in a table."""

    row: int
    col: int
    paragraphs: list[Paragraph] = Field(default_factory=list)
    fill_color: Color | None = None
    row_span: int = 1
    col_span: int = 1


class TableElement(BaseModel):
    """A table on a slide."""

    type: Literal["table"] = "table"
    id: str = ""
    name: str = ""
    bbox: BoundingBox
    rows: int = 0
    cols: int = 0
    cells: list[TableCell] = Field(default_factory=list)


SlideElement = Annotated[
    TextElement | ImageElement | ShapeElement | TableElement,
    Field(discriminator="type"),
]


class SlideBackground(BaseModel):
    """Background of a slide."""

    solid_color: Color | None = None
    gradient_colors: list[Color] | None = None
    image_bytes: bytes | None = Field(default=None, exclude=True)


class Slide(BaseModel):
    """A single slide in the presentation."""

    index: int
    elements: list[SlideElement] = Field(default_factory=list)
    background: SlideBackground | None = None
    notes: str | None = None
    layout_name: str | None = None


class CSM(BaseModel):
    """Canonical Slide Model — the top-level representation of a presentation."""

    slides: list[Slide] = Field(default_factory=list)
    width: float = 0.0
    height: float = 0.0
    title: str | None = None
    author: str | None = None
