"""Tests for the BrandRuleset model."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from packages.csm.brand import (
    BrandColor,
    BrandFont,
    BrandRuleset,
    CustomTolerances,
    LayoutRules,
    SizeRule,
)

SAMPLE_BRAND_PATH = Path(__file__).parent / "golden_decks" / "sample_brand.json"


class TestBrandColor:
    def test_construction(self) -> None:
        c = BrandColor(name="Blue", hex="#0000FF", r=0, g=0, b=255)
        assert c.name == "Blue"
        assert c.tolerance_delta_e == 10.0

    def test_custom_tolerance(self) -> None:
        c = BrandColor(name="Red", hex="#FF0000", r=255, g=0, b=0, tolerance_delta_e=5.0)
        assert c.tolerance_delta_e == 5.0

    def test_invalid_rgb_rejected(self) -> None:
        with pytest.raises(ValidationError):
            BrandColor(name="Bad", hex="#000000", r=300, g=0, b=0)


class TestBrandFont:
    def test_construction(self) -> None:
        f = BrandFont(family="Inter", weight_min=300, weight_max=700)
        assert f.family == "Inter"
        assert f.weight_min == 300

    def test_defaults(self) -> None:
        f = BrandFont(family="Arial")
        assert f.weight_min == 100
        assert f.weight_max == 900

    def test_invalid_weight(self) -> None:
        with pytest.raises(ValidationError):
            BrandFont(family="Bad", weight_min=50)


class TestSizeRule:
    def test_construction(self) -> None:
        s = SizeRule(role="title", min_pt=24.0, max_pt=44.0)
        assert s.role == "title"
        assert s.min_pt == 24.0

    def test_defaults(self) -> None:
        s = SizeRule(role="body")
        assert s.min_pt == 0.0
        assert s.max_pt == 200.0


class TestLayoutRules:
    def test_defaults(self) -> None:
        lr = LayoutRules()
        assert lr.margin_left == 0.5
        assert lr.max_elements_per_slide == 12
        assert lr.alignment_grid_pt == 0.0

    def test_custom(self) -> None:
        lr = LayoutRules(margin_left=1.0, max_elements_per_slide=8)
        assert lr.margin_left == 1.0
        assert lr.max_elements_per_slide == 8


class TestCustomTolerances:
    def test_all_none_by_default(self) -> None:
        ct = CustomTolerances()
        assert ct.color_delta_e is None
        assert ct.max_words_per_slide is None

    def test_set_overrides(self) -> None:
        ct = CustomTolerances(color_delta_e=5.0, max_bullets_per_slide=5)
        assert ct.color_delta_e == 5.0
        assert ct.max_bullets_per_slide == 5


class TestBrandRuleset:
    def test_empty_construction(self) -> None:
        br = BrandRuleset()
        assert br.name == "Untitled Brand"
        assert br.colors == []
        assert br.fonts == []

    def test_load_from_sample_json(self) -> None:
        raw = SAMPLE_BRAND_PATH.read_text()
        br = BrandRuleset.model_validate_json(raw)
        assert br.name == "Acme Corp"
        assert len(br.colors) == 4
        assert len(br.fonts) == 2
        assert len(br.size_rules) == 4
        assert br.layout_rules.margin_left == 0.75
        assert br.custom_tolerances.max_words_per_slide == 75

    def test_json_roundtrip(self) -> None:
        raw = SAMPLE_BRAND_PATH.read_text()
        br = BrandRuleset.model_validate_json(raw)
        exported = br.model_dump_json()
        br2 = BrandRuleset.model_validate_json(exported)
        assert br == br2

    def test_export_matches_structure(self) -> None:
        raw = SAMPLE_BRAND_PATH.read_text()
        br = BrandRuleset.model_validate_json(raw)
        dumped = json.loads(br.model_dump_json())
        assert "name" in dumped
        assert "colors" in dumped
        assert "fonts" in dumped
        assert "size_rules" in dumped
        assert "layout_rules" in dumped
        assert "custom_tolerances" in dumped

    def test_validates_constraints(self) -> None:
        """Nested validation: invalid color RGB is caught even inside BrandRuleset."""
        with pytest.raises(ValidationError):
            BrandRuleset(
                name="Bad",
                colors=[BrandColor(name="X", hex="#000", r=999, g=0, b=0)],
            )

    def test_color_names(self) -> None:
        raw = SAMPLE_BRAND_PATH.read_text()
        br = BrandRuleset.model_validate_json(raw)
        names = [c.name for c in br.colors]
        assert "Brand Blue" in names
        assert "Accent Orange" in names

    def test_font_families(self) -> None:
        raw = SAMPLE_BRAND_PATH.read_text()
        br = BrandRuleset.model_validate_json(raw)
        families = [f.family for f in br.fonts]
        assert "Inter" in families
        assert "Roboto" in families

    def test_size_rules_roles(self) -> None:
        raw = SAMPLE_BRAND_PATH.read_text()
        br = BrandRuleset.model_validate_json(raw)
        roles = [s.role for s in br.size_rules]
        assert "title" in roles
        assert "body" in roles
        assert "caption" in roles
