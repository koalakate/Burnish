"""Tests for Canonical Slide Model (CSM) types."""

import json

from packages.csm import (
    CSM,
    BoundingBox,
    Color,
    Font,
    ImageElement,
    Paragraph,
    ShapeElement,
    Slide,
    SlideBackground,
    TableCell,
    TableElement,
    TextElement,
    TextRun,
)


class TestColor:
    def test_color_construction(self) -> None:
        c = Color(hex="#FF0000", r=255, g=0, b=0)
        assert c.hex == "#FF0000"
        assert c.r == 255
        assert c.g == 0
        assert c.b == 0
        assert c.a == 1.0

    def test_color_with_alpha(self) -> None:
        c = Color(hex="#FF000080", r=255, g=0, b=0, a=0.5)
        assert c.a == 0.5

    def test_color_round_trip(self) -> None:
        c = Color(hex="#00FF00", r=0, g=255, b=0, a=0.8)
        json_str = c.model_dump_json()
        c2 = Color.model_validate_json(json_str)
        assert c == c2


class TestFont:
    def test_font_defaults(self) -> None:
        f = Font()
        assert f.family is None
        assert f.weight is None
        assert f.size_pt is None
        assert f.italic is False
        assert f.underline is False

    def test_font_full(self) -> None:
        f = Font(family="Inter", weight=700, size_pt=24.0, italic=True, underline=True)
        assert f.family == "Inter"
        assert f.weight == 700


class TestTextElement:
    def test_text_element_round_trip(self) -> None:
        elem = TextElement(
            id="txt1",
            name="Title",
            bbox=BoundingBox(x=0, y=0, width=100, height=50),
            paragraphs=[
                Paragraph(
                    runs=[
                        TextRun(
                            text="Hello World",
                            font=Font(family="Inter", size_pt=24.0),
                            color=Color(hex="#000000", r=0, g=0, b=0),
                        )
                    ],
                    alignment="center",
                )
            ],
            role="title",
        )
        json_str = elem.model_dump_json()
        elem2 = TextElement.model_validate_json(json_str)
        assert elem == elem2
        assert elem2.type == "text"
        assert elem2.paragraphs[0].runs[0].text == "Hello World"


class TestElementDiscriminator:
    def test_discriminator_text(self) -> None:
        slide = Slide(
            index=0,
            elements=[
                TextElement(
                    id="t1",
                    bbox=BoundingBox(x=0, y=0, width=100, height=50),
                    paragraphs=[],
                )
            ],
        )
        data = json.loads(slide.model_dump_json())
        assert data["elements"][0]["type"] == "text"
        slide2 = Slide.model_validate_json(slide.model_dump_json())
        assert isinstance(slide2.elements[0], TextElement)

    def test_discriminator_image(self) -> None:
        slide = Slide(
            index=0,
            elements=[
                ImageElement(
                    id="img1",
                    bbox=BoundingBox(x=0, y=0, width=200, height=150),
                    alt_text="A photo",
                )
            ],
        )
        slide2 = Slide.model_validate_json(slide.model_dump_json())
        assert isinstance(slide2.elements[0], ImageElement)
        assert slide2.elements[0].alt_text == "A photo"

    def test_discriminator_shape(self) -> None:
        slide = Slide(
            index=0,
            elements=[
                ShapeElement(
                    id="s1",
                    bbox=BoundingBox(x=10, y=10, width=80, height=40),
                    fill_color=Color(hex="#0000FF", r=0, g=0, b=255),
                )
            ],
        )
        slide2 = Slide.model_validate_json(slide.model_dump_json())
        assert isinstance(slide2.elements[0], ShapeElement)

    def test_discriminator_table(self) -> None:
        slide = Slide(
            index=0,
            elements=[
                TableElement(
                    id="tbl1",
                    bbox=BoundingBox(x=0, y=0, width=300, height=200),
                    rows=2,
                    cols=2,
                    cells=[
                        TableCell(row=0, col=0, paragraphs=[Paragraph(runs=[TextRun(text="A")])]),
                        TableCell(row=0, col=1, paragraphs=[Paragraph(runs=[TextRun(text="B")])]),
                    ],
                )
            ],
        )
        slide2 = Slide.model_validate_json(slide.model_dump_json())
        assert isinstance(slide2.elements[0], TableElement)
        assert slide2.elements[0].rows == 2

    def test_mixed_elements(self) -> None:
        slide = Slide(
            index=0,
            elements=[
                TextElement(id="t1", bbox=BoundingBox(x=0, y=0, width=100, height=50)),
                ImageElement(id="i1", bbox=BoundingBox(x=0, y=50, width=100, height=100)),
                ShapeElement(id="s1", bbox=BoundingBox(x=100, y=0, width=50, height=50)),
                TableElement(
                    id="tbl1", bbox=BoundingBox(x=100, y=50, width=100, height=100), rows=1, cols=1
                ),
            ],
        )
        slide2 = Slide.model_validate_json(slide.model_dump_json())
        assert len(slide2.elements) == 4
        types = [e.type for e in slide2.elements]
        assert types == ["text", "image", "shape", "table"]


class TestCSMSerialization:
    def test_csm_round_trip(self) -> None:
        csm = CSM(
            title="Test Deck",
            author="Test Author",
            width=9144000,
            height=6858000,
            slides=[
                Slide(
                    index=0,
                    background=SlideBackground(
                        solid_color=Color(hex="#FFFFFF", r=255, g=255, b=255)
                    ),
                    elements=[
                        TextElement(
                            id="title",
                            name="Title",
                            bbox=BoundingBox(x=0, y=0, width=9144000, height=1000000),
                            paragraphs=[
                                Paragraph(
                                    runs=[
                                        TextRun(
                                            text="Slide 1",
                                            font=Font(family="Inter", size_pt=36.0, weight=700),
                                        )
                                    ]
                                )
                            ],
                            role="title",
                        ),
                        ImageElement(
                            id="img1",
                            bbox=BoundingBox(x=100, y=1000000, width=4000000, height=3000000),
                            alt_text="Logo",
                            dpi=300.0,
                        ),
                    ],
                    layout_name="Title Slide",
                ),
                Slide(
                    index=1,
                    elements=[
                        TextElement(
                            id="body",
                            bbox=BoundingBox(x=500000, y=500000, width=8000000, height=5000000),
                            paragraphs=[
                                Paragraph(
                                    runs=[TextRun(text="Bullet 1")],
                                    level=0,
                                ),
                                Paragraph(
                                    runs=[TextRun(text="Bullet 2")],
                                    level=0,
                                ),
                            ],
                            role="body",
                        )
                    ],
                ),
            ],
        )
        json_str = csm.model_dump_json()
        csm2 = CSM.model_validate_json(json_str)
        assert csm2.title == "Test Deck"
        assert len(csm2.slides) == 2
        assert csm2.slides[0].elements[0].type == "text"
        assert csm2.slides[0].elements[1].type == "image"
        assert csm2.width == 9144000

    def test_empty_csm(self) -> None:
        csm = CSM()
        json_str = csm.model_dump_json()
        csm2 = CSM.model_validate_json(json_str)
        assert csm2.slides == []
        assert csm2.title is None
