"""Generate PPTX golden-deck fixtures programmatically.

Each fixture targets specific evaluator scenarios so the integration test
suite can verify the full check-engine pipeline (parse → evaluate → DQS).

Run standalone:  python -m tests.golden_decks.generate_fixtures
"""

from __future__ import annotations

from pathlib import Path

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.util import Emu, Inches, Pt

_FIXTURES_DIR = Path(__file__).parent

# Standard slide dimensions: 10 × 7.5 inches
_SLIDE_W = Emu(9_144_000)
_SLIDE_H = Emu(6_858_000)

# --- Brand-approved values (must match sample_brand.json) ---
_BRAND_BLUE = RGBColor(0x1B, 0x3A, 0x6B)
_BRAND_WHITE = RGBColor(0xFF, 0xFF, 0xFF)
_BRAND_ORANGE = RGBColor(0xE8, 0x77, 0x22)
_BRAND_DARK_GRAY = RGBColor(0x33, 0x33, 0x33)
_APPROVED_FONT = "Inter"
_ALT_FONT = "Roboto"


def _new_prs() -> Presentation:
    prs = Presentation()
    prs.slide_width = _SLIDE_W
    prs.slide_height = _SLIDE_H
    return prs


def _blank_slide(prs: Presentation):
    return prs.slides.add_slide(prs.slide_layouts[6])


def _add_textbox(slide, left, top, width, height, text, font_name, font_size_pt,
                 font_color, bold=False, italic=False):
    """Helper to add a simple textbox with one run."""
    txbox = slide.shapes.add_textbox(left, top, width, height)
    tf = txbox.text_frame
    p = tf.paragraphs[0]
    run = p.add_run()
    run.text = text
    run.font.name = font_name
    run.font.size = Pt(font_size_pt)
    run.font.color.rgb = font_color
    run.font.bold = bold
    run.font.italic = italic
    return txbox


# ---------------------------------------------------------------
# 1. brand_violations.pptx
# ---------------------------------------------------------------
def generate_brand_violations(out: Path) -> None:
    """Slides with off-brand colors, wrong fonts, and undersized text."""
    prs = _new_prs()

    # Slide 0: Off-brand color (bright red — far from any brand color)
    s = _blank_slide(prs)
    _add_textbox(s, Inches(1), Inches(1), Inches(5), Inches(1),
                 "Off-brand red text", _APPROVED_FONT, 24,
                 RGBColor(0xFF, 0x00, 0x00))

    # Slide 1: Wrong font family
    s = _blank_slide(prs)
    _add_textbox(s, Inches(1), Inches(1), Inches(5), Inches(1),
                 "Comic Sans is not approved", "Comic Sans MS", 18,
                 _BRAND_DARK_GRAY)

    # Slide 2: Undersized title text (min 24pt for title, using 10pt)
    s = _blank_slide(prs)
    _add_textbox(s, Inches(1), Inches(1), Inches(5), Inches(1),
                 "Tiny title text", _APPROVED_FONT, 10, _BRAND_DARK_GRAY)
    # Mark the placeholder as a title by using slide_layouts[0] instead
    # Actually, we can't set role on a textbox — the parser infers role from
    # placeholder type.  Use a title layout instead.

    # Slide 2 alt: use a title-slide layout to get a real title placeholder
    s2 = prs.slides.add_slide(prs.slide_layouts[0])
    title_ph = s2.shapes.title
    title_ph.text = ""
    tf = title_ph.text_frame
    p = tf.paragraphs[0]
    run = p.add_run()
    run.text = "Tiny title"
    run.font.name = _APPROVED_FONT
    run.font.size = Pt(10)  # below 24pt minimum
    run.font.color.rgb = _BRAND_DARK_GRAY

    prs.save(str(out))


# ---------------------------------------------------------------
# 2. accessibility_fails.pptx
# ---------------------------------------------------------------
def generate_accessibility_fails(out: Path) -> None:
    """Slides with low-contrast text and missing alt text on images."""
    prs = _new_prs()

    # Slide 0: Low contrast — light gray text on white background
    s = _blank_slide(prs)
    bg = s.background
    fill = bg.fill
    fill.solid()
    fill.fore_color.rgb = _BRAND_WHITE
    # Light gray on white => very low contrast ratio (~1.5:1)
    _add_textbox(s, Inches(1), Inches(1), Inches(5), Inches(1),
                 "Hard to read text", _APPROVED_FONT, 14,
                 RGBColor(0xCC, 0xCC, 0xCC))

    # Slide 1: Image without alt text
    s = _blank_slide(prs)
    # Create a small 10×10 red PNG in memory for the image
    import io

    from PIL import Image as PILImage
    img = PILImage.new("RGB", (10, 10), (255, 0, 0))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    s.shapes.add_picture(buf, Inches(1), Inches(1), Inches(2), Inches(2))
    # python-pptx doesn't set alt_text by default => it will be None

    # Slide 2: Another low-contrast case — dark text on dark background
    s = _blank_slide(prs)
    bg = s.background
    fill = bg.fill
    fill.solid()
    fill.fore_color.rgb = RGBColor(0x22, 0x22, 0x22)
    _add_textbox(s, Inches(1), Inches(1), Inches(5), Inches(1),
                 "Dark on dark", _APPROVED_FONT, 14,
                 RGBColor(0x44, 0x44, 0x44))

    prs.save(str(out))


# ---------------------------------------------------------------
# 3. layout_issues.pptx
# ---------------------------------------------------------------
def generate_layout_issues(out: Path) -> None:
    """Overcrowded slides, elements at the edge, excessive bullets."""
    prs = _new_prs()

    # Slide 0: Too many elements (>10)
    s = _blank_slide(prs)
    for i in range(12):
        row = i // 4
        col = i % 4
        _add_textbox(
            s,
            Inches(0.8 + col * 2.2),
            Inches(0.8 + row * 2.0),
            Inches(2), Inches(1),
            f"Box {i + 1}",
            _APPROVED_FONT, 14, _BRAND_DARK_GRAY,
        )

    # Slide 1: Element at the very edge (margin violation)
    s = _blank_slide(prs)
    _add_textbox(s, Inches(0.1), Inches(0.1), Inches(3), Inches(1),
                 "Too close to edge", _APPROVED_FONT, 14, _BRAND_DARK_GRAY)

    # Slide 2: Excessive bullets (>7) and too many words
    s = _blank_slide(prs)
    txbox = s.shapes.add_textbox(Inches(1), Inches(0.5), Inches(7), Inches(6))
    tf = txbox.text_frame
    # First paragraph (level 0) is the "heading"
    p = tf.paragraphs[0]
    run = p.add_run()
    run.text = "Key points to remember in this very long presentation:"
    run.font.name = _APPROVED_FONT
    run.font.size = Pt(14)
    run.font.color.rgb = _BRAND_DARK_GRAY
    # Add 9 bullet paragraphs (level 1) — exceeds 7-bullet limit
    for i in range(9):
        p = tf.add_paragraph()
        p.level = 1
        run = p.add_run()
        run.text = (
            f"Bullet point {i + 1} with quite a lot of extra words "
            "to push the total word count over the limit"
        )
        run.font.name = _APPROVED_FONT
        run.font.size = Pt(12)
        run.font.color.rgb = _BRAND_DARK_GRAY

    prs.save(str(out))


# ---------------------------------------------------------------
# 4. clean_deck.pptx
# ---------------------------------------------------------------
def generate_clean_deck(out: Path) -> None:
    """A fully brand-compliant deck — should pass all checks, DQS >= 95."""
    prs = _new_prs()

    # Slide 0: Title slide (using title layout)
    s = prs.slides.add_slide(prs.slide_layouts[0])
    bg = s.background
    fill = bg.fill
    fill.solid()
    fill.fore_color.rgb = _BRAND_WHITE
    title_ph = s.shapes.title
    title_ph.text = ""
    tf = title_ph.text_frame
    p = tf.paragraphs[0]
    run = p.add_run()
    run.text = "Acme Corp Quarterly Review"
    run.font.name = _APPROVED_FONT
    run.font.size = Pt(36)
    run.font.color.rgb = _BRAND_BLUE
    # Subtitle
    sub = s.placeholders[1]
    sub.text = ""
    tf = sub.text_frame
    p = tf.paragraphs[0]
    run = p.add_run()
    run.text = "Q1 2026 Results"
    run.font.name = _APPROVED_FONT
    run.font.size = Pt(20)
    run.font.color.rgb = _BRAND_DARK_GRAY

    # Slide 1: Simple content slide (blank layout, few elements, brand colors)
    s = _blank_slide(prs)
    bg = s.background
    fill = bg.fill
    fill.solid()
    fill.fore_color.rgb = _BRAND_WHITE
    _add_textbox(s, Inches(1), Inches(0.8), Inches(8), Inches(1),
                 "Revenue Growth", _APPROVED_FONT, 28, _BRAND_BLUE, bold=True)
    _add_textbox(s, Inches(1), Inches(2), Inches(7), Inches(3),
                 "Our revenue grew by 25% this quarter.", _APPROVED_FONT, 16,
                 _BRAND_DARK_GRAY)

    # Slide 2: Slide with a branded shape
    s = _blank_slide(prs)
    bg = s.background
    fill = bg.fill
    fill.solid()
    fill.fore_color.rgb = _BRAND_WHITE
    _add_textbox(s, Inches(1), Inches(0.8), Inches(8), Inches(1),
                 "Key Highlights", _APPROVED_FONT, 28, _BRAND_BLUE, bold=True)
    shape = s.shapes.add_shape(
        MSO_SHAPE.ROUNDED_RECTANGLE,
        Inches(1), Inches(2.2), Inches(3), Inches(1.5),
    )
    shape_fill = shape.fill
    shape_fill.solid()
    shape_fill.fore_color.rgb = _BRAND_BLUE
    # Add text inside the shape
    tf = shape.text_frame
    p = tf.paragraphs[0]
    run = p.add_run()
    run.text = "25% growth"
    run.font.name = _APPROVED_FONT
    run.font.size = Pt(18)
    run.font.color.rgb = _BRAND_WHITE

    prs.save(str(out))


# ---------------------------------------------------------------
# Main — regenerate all fixtures
# ---------------------------------------------------------------
def generate_all() -> None:
    """Generate all golden-deck PPTX fixtures."""
    generate_brand_violations(_FIXTURES_DIR / "brand_violations.pptx")
    generate_accessibility_fails(_FIXTURES_DIR / "accessibility_fails.pptx")
    generate_layout_issues(_FIXTURES_DIR / "layout_issues.pptx")
    generate_clean_deck(_FIXTURES_DIR / "clean_deck.pptx")


if __name__ == "__main__":
    generate_all()
    print("Golden deck fixtures generated successfully.")
