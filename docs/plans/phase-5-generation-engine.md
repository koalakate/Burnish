# Plan: Burnish Phase 5 — Generation Engine

> **Goal:** Generate brand-compliant starter decks from a brief or outline.
>
> **Exit criteria:** User describes a 10-slide pitch deck in 2 sentences → Burnish generates it → it scores ≥ 90 DQS on self-check → opens correctly in PowerPoint.
>
> **Ref:** Product Roadmap Phase 5
>
> **Depends on:** Phase 4 (CSM + brand rulesets must be stable)
>
> **Design decision:** Output is always editable native format (PPTX, Google Slides, Figma) — never screenshot-based export. Templates are declarative CSM patterns (inspired by Slidev's component layout approach, but using CSM not HTML).

## Validation Commands
- `ruff check services/ packages/`
- `mypy services/ packages/ --ignore-missing-imports`
- `pytest packages/ services/ tests/ -x --tb=short`
- `cd apps/web && npm run lint && npm run build`

### Task 1: CSM template system — declarative named layouts
- [ ] Create `packages/csm/templates.py` with `SlideTemplate` model: name (e.g. "title-slide", "two-column", "image-left", "data-chart", "quote", "section-divider"), layout definition (list of placeholder slots with bounding boxes, roles, and constraints)
- [ ] Each template slot has: `slot_id`, `role` (title, subtitle, body, image, chart, footer), `bbox` (position and size), `style_hints` (font size range, alignment, max lines)
- [ ] Create `packages/csm/template_library.py` — built-in library of 10+ common slide templates: title slide, section divider, text-only, two-column text, image-left, image-right, image-full-bleed, data/chart, quote/testimonial, bullet list, comparison, closing/CTA
- [ ] Templates are CSM fragments, not PPTX files — pure data, format-agnostic
- [ ] Implement `apply_template(template: SlideTemplate, content: Dict[str, str], brand: BrandRuleset) -> Slide` — populate a template with content, applying brand fonts, colors, and sizes
- [ ] Write tests: apply content to each template → verify resulting Slide has correct element positions, fonts, and colors from brand

### Task 2: Deck structure planner (AI)
- [ ] Create `services/generation/__init__.py` and `services/generation/planner.py`
- [ ] Implement `plan_deck(brief: str, template_library: List[SlideTemplate], brand: BrandRuleset) -> DeckPlan` — send the user's text brief to Claude to produce a structured deck outline
- [ ] `DeckPlan` model: title, total_slides, per-slide plan (template_name, content_outline per slot, speaker_notes_outline)
- [ ] Prompt engineering: instruct the AI to select appropriate templates from the library for each slide, distribute content logically, follow presentation best practices (one idea per slide, progressive disclosure, visual variety)
- [ ] Support brief styles: one-liner ("Q3 sales review"), outline (bullet list of topics), detailed brief (paragraph with requirements)
- [ ] Write tests with mocked AI client: verify plan structure for different brief styles, template selection variety

### Task 3: Content generator (AI)
- [ ] Create `services/generation/content_generator.py`
- [ ] Implement `generate_content(plan: DeckPlan, brand: BrandRuleset) -> List[SlideContent]` — for each slide in the plan, generate the actual text content for each slot
- [ ] `SlideContent` model: slide_index, per-slot content (title text, body text, bullet points, image description, chart data description)
- [ ] Enforce brand voice and tone (if specified in brand ruleset metadata)
- [ ] Content quality gates: max characters per slot (derived from template constraints), no lorem ipsum, actionable titles
- [ ] Generate speaker notes for each slide
- [ ] Write tests: generate content for a known plan → verify all slots are populated, character limits respected

### Task 4: CSM assembly — plan + content + templates → CSM
- [ ] Create `services/generation/assembler.py`
- [ ] Implement `assemble_deck(plan: DeckPlan, content: List[SlideContent], brand: BrandRuleset) -> CSM` — combine template layouts, generated content, and brand styling into a complete CSM
- [ ] For each slide: select template from plan → populate slots with generated content → apply brand fonts, colors, sizes → add to CSM
- [ ] Set slide dimensions from brand defaults (16:9 default, configurable)
- [ ] Generate consistent slide numbering and footer elements if brand requires
- [ ] Write tests: assemble a 5-slide deck → verify CSM has correct slide count, all elements positioned, brand fonts/colors applied

### Task 5: Self-check loop — generate + check + auto-correct
- [ ] Create `services/generation/quality_loop.py`
- [ ] Implement `generate_with_quality(brief: str, brand: BrandRuleset) -> CSM` — the full generation pipeline with quality assurance:
  1. Plan the deck structure
  2. Generate content
  3. Assemble CSM
  4. Run the check engine against the brand ruleset
  5. If DQS < 90, auto-apply corrections
  6. Re-check — if still < 90, regenerate problem slides (max 2 retries)
- [ ] Log each iteration's DQS for debugging
- [ ] Return the final CSM with guaranteed DQS ≥ 90 (or best-effort with warning if retries exhausted)
- [ ] Write tests: generate a deck with a strict brand → verify DQS ≥ 90 after quality loop

### Task 6: Generation API routes + worker
- [ ] Implement `POST /api/generate` — accept brief text + brand_id, optional template preferences, enqueue generation job
- [ ] Create `services/workers/generation_worker.py` — process generation job: plan → generate → assemble → quality loop → export PPTX → store in R2
- [ ] Implement `GET /api/generate/{job_id}` — get generation status (planning/generating/checking/exporting/complete), progress percentage
- [ ] Implement `GET /api/generate/{job_id}/preview` — get preview thumbnails of generated slides (available after assembly, before full export)
- [ ] Implement `GET /api/generate/{job_id}/download` — download generated PPTX
- [ ] Add generation queue to BullMQ worker setup
- [ ] Write API tests: submit brief → poll status → download PPTX → verify file is valid

### Task 7: Generation UI
- [ ] Create generation page at `(dashboard)/generate/page.tsx` — text area for brief input, brand selector, optional "Deck Type" selector (pitch deck, quarterly review, project proposal, custom)
- [ ] Create `apps/web/src/components/generation-preview.tsx` — while generating, show progressive slide thumbnails as they're assembled (polling preview endpoint)
- [ ] Show generation status steps: "Planning structure..." → "Generating content..." → "Applying brand..." → "Quality check..." → "Ready!"
- [ ] After generation complete: show the full deck in the same check results view (reuse Phase 2 components), with DQS badge
- [ ] "Download" button for the generated PPTX
- [ ] "Edit & Re-check" button: opens the generated deck in the correction view to make manual tweaks before downloading

### Task 8: Slide iteration — per-slide regeneration
- [ ] Implement `POST /api/generate/{job_id}/slides/{slide_index}/regenerate` — accept instruction text ("make slide 3 more visual", "add more data points"), regenerate just that slide
- [ ] In the generation preview UI, add per-slide action menu: "Regenerate", "Change template", "Edit content"
- [ ] "Change template" shows a template picker overlay — select a different layout and re-assemble the slide with existing content
- [ ] "Regenerate" opens a text input for instructions, sends to API, replaces the slide in-place
- [ ] After any per-slide change, re-run quality check and update DQS
- [ ] Write tests: generate deck → regenerate one slide → verify only that slide changed, DQS recalculated

### Task 9: Template library management
- [ ] Implement `GET /api/templates` — list all available templates (built-in + org custom)
- [ ] Implement `POST /api/templates` — create a custom org template (define slots and layout via JSON)
- [ ] Create template browser UI at `(dashboard)/generate/templates/page.tsx` — visual grid of template previews, filter by category (title, content, data, image)
- [ ] Each template preview shows a sample rendering with placeholder content
- [ ] Templates are stored as CSM patterns in the database, org-scoped
- [ ] Write tests: create custom template → use in generation → verify it appears in output
