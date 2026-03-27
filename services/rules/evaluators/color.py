"""Color compliance evaluator — checks slide colors against the brand palette."""

from __future__ import annotations

import math
import uuid

from packages.csm.brand import BrandColor, BrandRuleset
from packages.csm.models import Color, Slide
from services.rules.models import Issue, Severity

# ---------------------------------------------------------------------------
# sRGB → CIELAB conversion
# ---------------------------------------------------------------------------

def _linearize(c: float) -> float:
    """Convert an sRGB channel (0-1) to linear RGB."""
    if c <= 0.04045:
        return c / 12.92
    return float(((c + 0.055) / 1.055) ** 2.4)


def _f(t: float) -> float:
    """CIE nonlinear transform."""
    delta = 6.0 / 29.0
    if t > delta**3:
        return float(t ** (1.0 / 3.0))
    return t / (3.0 * delta**2) + 4.0 / 29.0


def rgb_to_lab(r: int, g: int, b: int) -> tuple[float, float, float]:
    """Convert sRGB (0-255) to CIELAB (L*, a*, b*) using D65 illuminant."""
    # Normalize and linearize
    rl = _linearize(r / 255.0)
    gl = _linearize(g / 255.0)
    bl = _linearize(b / 255.0)

    # sRGB → XYZ (D65)
    x = 0.4124564 * rl + 0.3575761 * gl + 0.1804375 * bl
    y = 0.2126729 * rl + 0.7151522 * gl + 0.0721750 * bl
    z = 0.0193339 * rl + 0.1191920 * gl + 0.9503041 * bl

    # D65 reference white
    xn, yn, zn = 0.95047, 1.00000, 1.08883

    fx = _f(x / xn)
    fy = _f(y / yn)
    fz = _f(z / zn)

    l_star = 116.0 * fy - 16.0
    a_star = 500.0 * (fx - fy)
    b_star = 200.0 * (fy - fz)
    return l_star, a_star, b_star


# ---------------------------------------------------------------------------
# CIEDE2000 Delta-E
# ---------------------------------------------------------------------------

def delta_e_ciede2000(
    lab1: tuple[float, float, float],
    lab2: tuple[float, float, float],
) -> float:
    """Compute CIEDE2000 color difference between two CIELAB colors."""
    l1, a1, b1 = lab1
    l2, a2, b2 = lab2

    # Step 1: Calculate C' and h'
    c1 = math.sqrt(a1**2 + b1**2)
    c2 = math.sqrt(a2**2 + b2**2)
    c_avg = (c1 + c2) / 2.0
    c_avg7 = c_avg**7
    g = 0.5 * (1.0 - math.sqrt(c_avg7 / (c_avg7 + 25.0**7)))

    a1p = a1 * (1.0 + g)
    a2p = a2 * (1.0 + g)

    c1p = math.sqrt(a1p**2 + b1**2)
    c2p = math.sqrt(a2p**2 + b2**2)

    h1p = math.degrees(math.atan2(b1, a1p)) % 360.0
    h2p = math.degrees(math.atan2(b2, a2p)) % 360.0

    # Step 2: Calculate Delta L', Delta C', Delta H'
    dl = l2 - l1
    dc = c2p - c1p

    if c1p * c2p == 0:
        dh = 0.0
    elif abs(h2p - h1p) <= 180.0:
        dh = h2p - h1p
    elif h2p - h1p > 180.0:
        dh = h2p - h1p - 360.0
    else:
        dh = h2p - h1p + 360.0

    dh_big = 2.0 * math.sqrt(c1p * c2p) * math.sin(math.radians(dh / 2.0))

    # Step 3: Weighting functions
    l_avg = (l1 + l2) / 2.0
    c_avg_p = (c1p + c2p) / 2.0

    if c1p * c2p == 0:
        h_avg = h1p + h2p
    elif abs(h1p - h2p) <= 180.0:
        h_avg = (h1p + h2p) / 2.0
    elif h1p + h2p < 360.0:
        h_avg = (h1p + h2p + 360.0) / 2.0
    else:
        h_avg = (h1p + h2p - 360.0) / 2.0

    t = (
        1.0
        - 0.17 * math.cos(math.radians(h_avg - 30.0))
        + 0.24 * math.cos(math.radians(2.0 * h_avg))
        + 0.32 * math.cos(math.radians(3.0 * h_avg + 6.0))
        - 0.20 * math.cos(math.radians(4.0 * h_avg - 63.0))
    )

    sl = 1.0 + 0.015 * (l_avg - 50.0) ** 2 / math.sqrt(20.0 + (l_avg - 50.0) ** 2)
    sc = 1.0 + 0.045 * c_avg_p
    sh = 1.0 + 0.015 * c_avg_p * t

    c_avg_p7 = c_avg_p**7
    rc = 2.0 * math.sqrt(c_avg_p7 / (c_avg_p7 + 25.0**7))
    d_theta = 30.0 * math.exp(-((h_avg - 275.0) / 25.0) ** 2)
    rt = -math.sin(math.radians(2.0 * d_theta)) * rc

    return math.sqrt(
        (dl / sl) ** 2
        + (dc / sc) ** 2
        + (dh_big / sh) ** 2
        + rt * (dc / sc) * (dh_big / sh)
    )


# ---------------------------------------------------------------------------
# Color collection helpers
# ---------------------------------------------------------------------------

def _collect_colors(slide: Slide) -> list[tuple[str, str, Color]]:
    """Extract all colors from a slide as (element_id, description, Color) tuples."""
    colors: list[tuple[str, str, Color]] = []
    for elem in slide.elements:
        if elem.type == "text":
            for para in elem.paragraphs:
                for run in para.runs:
                    if run.color is not None:
                        colors.append((elem.id, f"text color in '{run.text[:30]}'", run.color))
        elif elem.type == "shape":
            if elem.fill_color is not None:
                colors.append((elem.id, "shape fill color", elem.fill_color))
            if elem.line_color is not None:
                colors.append((elem.id, "shape line color", elem.line_color))
            for para in elem.paragraphs:
                for run in para.runs:
                    if run.color is not None:
                        desc = f"text color in shape '{run.text[:30]}'"
                        colors.append((elem.id, desc, run.color))
        elif elem.type == "table":
            for cell in elem.cells:
                if cell.fill_color is not None:
                    desc = f"table cell ({cell.row},{cell.col}) fill"
                    colors.append((elem.id, desc, cell.fill_color))
                for para in cell.paragraphs:
                    for run in para.runs:
                        if run.color is not None:
                            colors.append((
                                elem.id,
                                f"text in table cell ({cell.row},{cell.col})",
                                run.color,
                            ))
    return colors


def _find_nearest_brand_color(
    color: Color, brand_colors: list[BrandColor],
) -> tuple[BrandColor, float]:
    """Find the nearest brand color and its Delta-E distance."""
    lab = rgb_to_lab(color.r, color.g, color.b)
    best_color = brand_colors[0]
    best_de = float("inf")
    for bc in brand_colors:
        bc_lab = rgb_to_lab(bc.r, bc.g, bc.b)
        de = delta_e_ciede2000(lab, bc_lab)
        if de < best_de:
            best_de = de
            best_color = bc
    return best_color, best_de


# ---------------------------------------------------------------------------
# Public evaluator
# ---------------------------------------------------------------------------

def evaluate_colors(slide: Slide, brand: BrandRuleset) -> list[Issue]:
    """Check all colors in a slide against the brand palette.

    For each text run color and shape fill color, compute Delta-E (CIEDE2000)
    distance to the nearest brand color. If the distance exceeds the brand
    tolerance, emit an error issue.
    """
    if not brand.colors:
        return []

    global_tolerance = brand.custom_tolerances.color_delta_e
    colors = _collect_colors(slide)
    issues: list[Issue] = []

    for element_id, description, color in colors:
        nearest, de = _find_nearest_brand_color(color, brand.colors)
        tolerance = global_tolerance if global_tolerance is not None else nearest.tolerance_delta_e
        if de > tolerance:
            issues.append(Issue(
                id=f"color-{slide.index}-{element_id}-{uuid.uuid4().hex[:8]}",
                slide_index=slide.index,
                element_id=element_id,
                evaluator="color",
                severity=Severity.error,
                message=(
                    f"This color ({color.hex}) is off-brand. "
                    f"Closest match: {nearest.name} ({nearest.hex}), "
                    f"Delta-E: {de:.1f}"
                ),
                details={
                    "actual_hex": color.hex,
                    "actual_rgb": [color.r, color.g, color.b],
                    "nearest_brand_color": nearest.name,
                    "nearest_brand_hex": nearest.hex,
                    "nearest_brand_rgb": [nearest.r, nearest.g, nearest.b],
                    "delta_e": round(de, 2),
                    "tolerance": tolerance,
                    "description": description,
                },
            ))

    return issues
