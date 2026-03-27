# Plan: Burnish Phase 1 — Core Check Engine

> **Goal:** Given a PPTX and a brand ruleset, produce a per-slide list of issues with severity and DQS score.
>
> **Exit criteria:** CLI/test command takes a `.pptx` + ruleset JSON → outputs a JSON report with per-slide issues, severities, and an overall DQS. Golden deck tests all pass.
>
> **Ref:** Product Roadmap Phase 1, MVP Plan Tasks 2, 5, 6, 7, 8, 9, 10, 21
>
> **Depends on:** Phase 0 (repo scaffold, DB, storage)

## Validation Commands
- `ruff check services/ packages/`
- `mypy services/ packages/ --ignore-missing-imports`
- `pytest packages/ services/ tests/ -x --tb=short`

### Task 1: Canonical Slide Model (CSM) types
- [ ] Create `packages/csm/models.py` with Pydantic v2 models: `Color` (hex, r, g, b, a), `Font` (family, weight, size_pt, italic, underline), `BoundingBox` (x, y, width, height), `TextRun`, `Paragraph`, `TextElement`, `ImageElement`, `ShapeElement`, `TableElement`, `TableCell`, `Slide`, `SlideBackground`, `CSM`
- [ ] Use discriminated union for element types via `type` literal field (text, image, shape, table)
- [ ] All models must support JSON round-trip: `model_dump_json()` → `model_validate_json()`
- [ ] Export all types from `packages/csm/__init__.py`
- [ ] Write tests: Color construction, TextElement round-trip, CSM serialization, element type discriminator

### Task 2: PPTX parser (python-pptx → CSM)
- [ ] Create `services/ingestion/__init__.py` and `services/ingestion/pptx_parser.py`
- [ ] Implement `parse_pptx(file_path: Path) -> CSM` that reads a .pptx file and converts to CSM
- [ ] Handle all shape types: text boxes, images, auto-shapes, tables, grouped shapes
- [ ] Extract per-run font properties (family, size, weight, color) — fall back to slide master defaults when run-level properties are not set
- [ ] Extract slide backgrounds (solid color, gradient, image)
- [ ] Extract slide dimensions from presentation-level properties
- [ ] Create `services/ingestion/thumbnail.py` — generate PNG thumbnails from CSM slides using Pillow (render shapes as colored rectangles with text, for preview purposes)
- [ ] Write tests with a minimal hand-crafted PPTX fixture: parse → verify CSM has correct slide count, element types, font properties, colors

### Task 3: Brand ruleset model
- [ ] Define `BrandRuleset` Pydantic model in `packages/csm/brand.py`: `colors` (list of allowed Color with tolerance_delta_e), `fonts` (list of allowed Font families with weight ranges), `size_rules` (min/max by element role: title, body, caption), `layout_rules` (margins, max_elements_per_slide, alignment grid), `custom_tolerances` (per-evaluator overrides)
- [ ] Create a default/sample brand ruleset JSON fixture at `tests/golden_decks/sample_brand.json`
- [ ] Write tests: BrandRuleset loads from JSON, validates constraints, exports back to JSON

### Task 4: Rule engine skeleton and Issue model
- [ ] Create `services/rules/__init__.py` and `services/rules/models.py` with `Issue` (id, slide_index, element_id, evaluator, severity, message, details, bbox), `Severity` enum (error, warning, info), `SlideIssueSet`
- [ ] Create `services/rules/engine.py` with `RuleEngine` class that: accepts a list of evaluator functions, runs each against (CSM, BrandRuleset), collects and deduplicates issues, returns `List[SlideIssueSet]`
- [ ] Each evaluator has signature: `(slide: Slide, brand: BrandRuleset) -> List[Issue]`
- [ ] Engine runs evaluators per-slide, in parallel where possible
- [ ] Write test: engine with a dummy evaluator that always returns one issue → verify output structure

### Task 5: Color compliance evaluator
- [ ] Create `services/rules/evaluators/__init__.py` and `services/rules/evaluators/color.py`
- [ ] For each text run and shape fill color in the slide, compute Delta-E (CIELAB) distance to the nearest brand palette color using colormath
- [ ] If Delta-E > brand tolerance (default 10.0), emit an Issue with severity=error, message in plain English: "This blue (#1A2B4C) is off-brand. Closest match: Brand Blue (#1B3A6B)"
- [ ] Include the nearest brand color in issue details for the correction engine
- [ ] Write tests: on-brand color passes, off-brand color emits issue with correct nearest match and Delta-E value

### Task 6: Typography evaluator
- [ ] Create `services/rules/evaluators/typography.py`
- [ ] Check font family: if not in brand's allowed font list → issue (severity=error)
- [ ] Check font size: if below minimum for element role (title/body/caption) → issue (severity=warning)
- [ ] Check font weight: if not in brand's allowed weight range for the font → issue (severity=info)
- [ ] Message format: "Font 'Comic Sans' is not approved. Use 'Inter' or 'Roboto' instead."
- [ ] Write tests: approved font passes, wrong font/size/weight each emit correct issue

### Task 7: Accessibility evaluator (WCAG AA contrast)
- [ ] Create `services/rules/evaluators/accessibility.py`
- [ ] For each text element, compute contrast ratio between text color and background color (slide background or shape fill)
- [ ] WCAG AA thresholds: 4.5:1 for normal text, 3:1 for large text (≥18pt or ≥14pt bold)
- [ ] Emit issue with severity=error if below threshold, include current ratio and minimum needed
- [ ] Message format: "Low contrast (2.1:1) — text on this background needs at least 4.5:1 for readability."
- [ ] Write tests: high-contrast passes, low-contrast normal text fails, low-contrast large text uses relaxed threshold

### Task 8: Layout, Content, and Image evaluators
- [ ] Create `services/rules/evaluators/layout.py` — check margins (elements too close to slide edge), element count per slide (too crowded), alignment consistency (elements off-grid)
- [ ] Create `services/rules/evaluators/content.py` — check text density (too many words per slide), bullet count (more than 7 bullets), empty text placeholders
- [ ] Create `services/rules/evaluators/image.py` — check image DPI (below 150 for print), aspect ratio distortion (stretched/squished beyond 5% tolerance), missing alt text
- [ ] Each evaluator returns issues with plain-English messages
- [ ] Write tests for each evaluator: passing and failing cases

### Task 9: GPT-4o vision scoring service
- [ ] Create `services/vision/__init__.py`, `services/vision/scorer.py`, and `services/vision/rubric.py`
- [ ] Define scoring rubric in `rubric.py`: prompt template that asks GPT-4o to rate a slide thumbnail on visual quality (1-10), layout balance (1-10), readability (1-10), overall impression (1-10)
- [ ] Implement `score_slide(thumbnail_png: bytes, rubric: str) -> VisionScore` that sends thumbnail to GPT-4o vision API, parses structured JSON response
- [ ] Implement `score_deck(thumbnails: List[bytes]) -> List[VisionScore]` that scores slides in parallel with rate limiting (max 5 concurrent)
- [ ] Add caching: hash thumbnail bytes → cache VisionScore in Redis (TTL 24h) to avoid re-scoring unchanged slides
- [ ] Write test with mocked OpenAI client: verify prompt construction, response parsing, caching behavior

### Task 10: DQS (Design Quality Score) calculation
- [ ] Create `services/rules/dqs.py` with `calculate_dqs(rule_issues: List[SlideIssueSet], vision_scores: List[VisionScore], accessibility_issues: List[Issue]) -> DQSReport`
- [ ] Formula: `DQS = 0.4 × rule_score + 0.3 × vision_score + 0.3 × accessibility_score` where each component is 0-100
- [ ] `rule_score`: 100 minus weighted penalty per issue (error=-10, warning=-3, info=-1), clamped to 0
- [ ] `vision_score`: average of GPT-4o scores normalized to 0-100
- [ ] `accessibility_score`: 100 minus 15 per WCAG AA violation, clamped to 0
- [ ] Return per-slide DQS and overall deck DQS
- [ ] Write tests: perfect deck → DQS 100, deck with known issues → expected score, all-failing deck → DQS 0 (clamped)

### Task 11: Golden deck test suite
- [ ] Create `tests/golden_decks/generate_fixtures.py` script that generates PPTX fixtures programmatically using python-pptx
- [ ] Generate `brand_violations.pptx`: slides with known off-brand colors, wrong fonts, undersized text
- [ ] Generate `accessibility_fails.pptx`: slides with low-contrast text, missing alt text
- [ ] Generate `layout_issues.pptx`: overcrowded slides, elements off-margin, excessive bullets
- [ ] Generate `clean_deck.pptx`: a fully compliant deck that should pass all checks
- [ ] Write integration test: parse each fixture → run full rule engine + DQS → assert expected issues are found and clean deck scores DQS ≥ 95
- [ ] This test suite is the regression gate for all future changes to the check engine
