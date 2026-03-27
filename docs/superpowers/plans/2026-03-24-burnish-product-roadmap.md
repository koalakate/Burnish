# Burnish — Product Development Roadmap

> **Helicopter view.** This document describes the strategic phases of Burnish product development — from foundation through growth. For the granular implementation plan of Phase 1, see `2026-03-24-burnish-core-mvp.md`.

**Vision:** Every presentation that leaves an organization meets brand standards — automatically, instantly, without a human gatekeeper.

**Product:** AI-powered slide quality checker that ingests brand guidelines, evaluates presentations against them, and auto-corrects violations.

**Personas:** Maya (Brand Manager), Jake (Sales AE), Priya (Freelance Designer) — see `docs/personas-and-cjms.md`

---

## Phase Overview

```
Phase 0  ░░░░░░  Foundation & Scaffold          (~1 week)
Phase 1  ████░░  Core Check Engine               (~3 weeks)
Phase 2  ██████  Upload-Check-Fix Loop           (~2 weeks)
Phase 3  ░░████  Brand Setup & Multi-Brand       (~2 weeks)
Phase 4  ░░░░██  AI Brand Extraction             (~2 weeks)
Phase 5  ░░░░░█  Generation Engine               (~3 weeks)
Phase 6  ░░░░░░  Integrations & Scale            (~ongoing)
Phase 7  ░░░░░░  Analytics & Org Intelligence    (~2 weeks)
```

---

## Phase 0: Foundation & Scaffold

**Goal:** Runnable project skeleton — CI passes, Docker spins up, DB migrates, frontend renders a shell.

**Delivers:**
- Git repo with monorepo structure (Python backend + Next.js frontend)
- Docker Compose: PostgreSQL, Redis, API, worker, web
- SQLAlchemy async engine + Alembic migration harness
- Clerk auth wired into Next.js + FastAPI middleware
- Cloudflare R2 storage client with signed URLs
- CI pipeline: lint + type-check + test (empty suite passes)

**Exit criteria:** `docker compose up` boots the full stack. Authenticated user sees an empty dashboard shell.

**Risk:** Clerk + FastAPI JWT integration is underdocumented — allocate time for debugging.

**Ref:** MVP Plan Tasks 1, 3, 4, 12, 15

---

## Phase 1: Core Check Engine

**Goal:** Given a PPTX and a brand ruleset, produce a per-slide list of issues with severity and DQS score.

**Delivers:**
- Canonical Slide Model (CSM) — Pydantic types representing slides, shapes, text runs, images
- PPTX parser: `python-pptx` → CSM conversion
- Rule engine with evaluators:
  - Color compliance (Delta-E CIELAB against brand palette)
  - Typography (font family, size, weight)
  - Layout (margins, alignment, element count)
  - Accessibility (WCAG AA contrast ratio)
  - Content (text density, bullet count, empty placeholders)
  - Image (DPI, aspect ratio distortion)
- GPT-4o vision scorer for subjective quality
- DQS (Design Quality Score) calculation: weighted aggregate of rule + vision scores
- Golden deck test suite with known-violation fixtures

**Exit criteria:** CLI/test command takes a `.pptx` + ruleset JSON → outputs a JSON report with per-slide issues, severities, and an overall DQS. Golden deck tests all pass.

**Key decisions:**
- DQS formula: `0.4 × rule_score + 0.3 × vision_score + 0.3 × accessibility_score` (tunable)
- Vision scoring is expensive — run in parallel, cache aggressively
- Evaluators are stateless pure functions: `(CSM, BrandRuleset) → List[Issue]`

**Ref:** MVP Plan Tasks 2, 5, 6, 7, 8, 9, 10, 21

---

## Phase 2: Upload-Check-Fix Loop (Jake's Journey)

**Goal:** End-to-end flow: upload PPTX → async check → view results → "Fix All" → download corrected PPTX.

**Delivers:**
- **Backend:**
  - Deck upload API (multipart → R2 + DB record)
  - Async ingestion worker: parse PPTX → CSM → generate thumbnails → store
  - Async check worker: run rule engine + vision → store results
  - Async correction worker: generate corrections → store
  - Correction engine: color swap, font swap, contrast fix, font size bump, alignment snap
  - PPTX exporter: corrected CSM → new `.pptx` via python-pptx
  - Check results + correction API routes
- **Frontend:**
  - Upload dropzone (drag & drop, zero forms — Jake's mandate)
  - Deck library page
  - Check results page with slide strip + severity dots (red/yellow/green)
  - Slide detail page with issue list + bounding box overlays
  - Side-by-side correction view (original vs corrected via Konva.js)
  - "Fix All" button + per-issue accept/dismiss
  - Corrected PPTX download (one click)

**Exit criteria:** Jake's full CJM works: drag deck → wait <10s → see issues → "Fix All" → download corrected PPTX. Opens correctly in PowerPoint.

**UX mandates (from personas):**
- Issue descriptions in **plain English** — "This blue is wrong. Should be this blue." Not "Delta-E 12.3 exceeds tolerance."
- Edit-in-place for corrections — Priya can tweak the AI's suggestion, not just accept/dismiss
- Download offers "Save as new version" vs "Replace original" (Priya's version awareness)
- DQS badge visible on export/download confirmation (Priya screenshots this for clients)

**Key decisions:**
- Correction is non-destructive: original PPTX is preserved, corrections create a new version
- Corrections are pre-computed during the check run, not on-demand
- "Fix All" applies accepted corrections and triggers the exporter
- Live preview with hot-reload: CSM → Konva.js canvas updates in real-time as corrections are applied (pattern borrowed from Slidev's instant-feedback architecture)

**Ref:** MVP Plan Tasks 11, 13, 14, 16, 17, 19, 20

---

## Phase 3: Brand Setup & Multi-Brand (Maya + Priya)

**Goal:** Manual brand ruleset creation, org-level defaults, multi-brand switching.

**Delivers:**
- Brand ruleset CRUD (colors, fonts, size rules, custom tolerances)
- Brand ruleset editor UI with live preview ("if this color appears, it'll be flagged")
- Org-level default ruleset (auto-applied when Jake uploads without selecting)
- Multi-brand support: brand switcher in dashboard header (Priya's mandate)
- Active brand indicator during upload + check (Priya: "I need to know which rules are active")
- Brand ruleset duplication (for Priya: "clone Acme Corp → Acme Corp v2")

**Exit criteria:** Priya can create 3 brand rulesets, switch between them, upload a deck selecting "Acme Corp," and get issues checked against Acme's specific rules — not another client's.

**Key decisions:**
- Brand-as-plugin architecture: brand rulesets are self-contained, swappable theme objects (palette, fonts, layout constraints, default templates) — portable across orgs and exportable (pattern borrowed from Slidev's theme/addon plugin system)

**Ref:** MVP Plan Task 18 + new work

---

## Phase 4: AI Brand Extraction (Maya's Onboarding)

**Goal:** Upload a brand guidelines PDF → AI extracts colors, fonts, size rules, and layout preferences automatically.

**Delivers:**
- PDF/Notion page ingestion pipeline
- AI extraction: brand colors, font families, size hierarchies, logo usage rules, spacing preferences
- Confidence scores per extracted rule (Maya's trust requirement)
- Source snippets: link each extracted rule back to the specific PDF page/section it came from
- Rule review UI: table of extracted rules with confidence, source, accept/edit/reject per rule
- Bulk actions: "Accept all high-confidence rules" (confidence > 0.85)

**Exit criteria:** Maya uploads her 47-page brand PDF. Burnish extracts 12 colors, 4 font families, 6 size rules, and margin preferences — with 75%+ accuracy on first pass. She reviews in the table, accepts 9/12 colors immediately (high confidence), corrects 3. Total time: <10 minutes vs hours of manual entry.

**Key decisions:**
- Use Claude 3.5 Sonnet for PDF understanding (better at structured extraction than GPT-4o)
- Extraction is a one-shot pipeline, not iterative — but rules are editable after
- Confidence threshold for "auto-accept" suggestion is configurable per org

---

## Phase 5: Generation Engine

**Goal:** Generate brand-compliant starter decks from a brief or outline.

**Delivers:**
- Deck generation from text brief: "Q3 sales review for enterprise prospects"
- Template library: common deck structures (pitch deck, quarterly review, project proposal)
- Layout intelligence: auto-layout based on content volume per slide
- Brand-native generation: all generated slides pass the check engine with DQS ≥ 90
- Iteration: "make slide 3 more visual" / "add a data slide after slide 5"

**Exit criteria:** User describes a 10-slide pitch deck in 2 sentences → Burnish generates it → it scores ≥ 90 DQS on self-check → opens correctly in PowerPoint.

**Key decisions:**
- Generation uses the CSM as intermediate representation (same as correction)
- Templates are stored as CSM patterns, not PPTX files — declarative named layouts (`title-slide`, `two-column`, `image-left`) that the AI populates with content (pattern borrowed from Slidev's Vue component layouts)
- Output is always editable native format (PPTX, Google Slides, Figma) — never screenshot-based export
- Priya's use case: "generate a compliant starter deck for new projects"

**Design decision — Slidev evaluation (2026-03-27):**
Evaluated [Slidev](https://sli.dev) (MIT, Vue 3 + Vite + Markdown → web slides) for potential reuse. **Conclusion: borrow patterns, not code.** Slidev's core is incompatible — its data model is Markdown (not shape-level CSM), and its PPTX export produces image-only slides (no editable text/shapes). Three patterns adopted: (1) declarative CSM templates, (2) live preview hot-reload, (3) brand-as-plugin. See Phases 2, 3, 5.

---

## Phase 6: Integrations & Scale (Ongoing)

**Goal:** Meet users where they work. Scale to enterprise.

**Delivers (incremental):**
- **Google Slides support** — import/export via Google Slides API
- **Slack integration** — "check this deck" via Slack bot, results posted in thread
- **Figma integration** — check slide designs directly in Figma
- **SSO/SCIM** — enterprise identity management
- **API access** — public API for CI/CD integration ("fail the build if DQS < 80")
- **Webhooks** — notify external systems on check complete
- **Bulk operations** — check 50 decks at once (org-wide audit)
- **Custom evaluators** — plugin system for org-specific rules ("slide 1 must have the legal disclaimer")
- **Localization** — multi-language issue descriptions
- **On-premise deployment** — air-gapped enterprise option

**Exit criteria:** This phase never ends — it's the growth engine. Each sub-item is its own mini-project with separate planning.

---

## Phase 7: Analytics & Org Intelligence (Maya's Dashboard)

**Goal:** Maya checks the analytics dashboard on Monday to see how the org is doing.

**Delivers:**
- Org-wide DQS trend over time (line chart, weekly aggregation)
- Per-team DQS breakdown (Maya: "which teams consistently produce off-brand work")
- Most common violations leaderboard (top 10 recurring issues)
- Per-user check history (anonymized or named, org setting)
- Check volume metrics (decks checked/week, corrections accepted vs dismissed)
- Weekly email digest (optional): org DQS, top violations, trend direction

**Exit criteria:** Maya logs in Monday, sees a dashboard with DQS trend, top violations, and per-team breakdown. She can identify that "Sales West" averages 62 DQS and needs training.

**Key decisions:**
- Analytics are read-derived: materialized from check_run data, not a separate event system
- Per-person stats require org admin permission
- No real-time streaming — batch refresh on page load + manual refresh button

---

## Cross-Cutting Concerns (All Phases)

### Security & Multi-Tenancy
- Row-Level Security (RLS) from Phase 0 — every query scoped to org
- PPTX files stored in per-org R2 prefixes
- Brand rulesets are org-private (Priya's clients never see each other's rules)
- Clerk handles auth, org membership, and role-based access

### Performance Targets
- PPTX upload → check results: **< 15 seconds** for a 20-slide deck
- Correction generation: **< 5 seconds** after check completes
- PPTX export: **< 3 seconds**
- Dashboard page load: **< 1 second** (cached aggregates)

### Quality Gates
- Every phase ships with tests (unit + integration)
- Golden deck suite grows with each new evaluator
- DQS formula is validated against human-rated decks before launch
- Correction quality: corrected PPTX must render identically in PowerPoint, Google Slides, and Keynote (layout fidelity test)

### Monetization Checkpoints
- **Phase 2 complete → Free tier viable** (upload + check + fix, 5 decks/month)
- **Phase 3 complete → Pro tier viable** (multi-brand, unlimited decks)
- **Phase 4 complete → Enterprise pilot viable** (AI extraction, SSO)
- **Phase 5 complete → Premium add-on** (generation engine)
- **Phase 7 complete → Team/Enterprise tier enrichment** (analytics, org management)

---

## Dependencies & Sequencing

```
Phase 0 ──→ Phase 1 ──→ Phase 2 ──→ Phase 3 ──→ Phase 4
                │                                    │
                │                                    ├──→ Phase 5 (needs brand rulesets for brand-native gen)
                │                                    │
                │                                    └──→ Phase 6 (integrations can start after Phase 4)
                │
                └──→ Phase 7 (can start any time after sufficient check data accumulates)
```

- **Phase 0 → 1:** Scaffold must exist before engine work begins
- **Phase 1 → 2:** Check engine must work before the UI can show results
- **Phase 2 → 3:** Upload flow must exist before brand switching makes sense in UI
- **Phase 3 → 4:** Manual brand entry must work before AI extraction replaces it (fallback path)
- **Phase 4 → 5:** CSM + brand rulesets must be stable for generation to produce brand-native decks
- **Phase 4 → 6:** Core product must be complete before integrations extend it
- **Phase 7:** Analytics needs accumulated check data to be meaningful — can be built independently once enough usage exists

---

## What This Plan Intentionally Omits

- **Pricing page & billing integration** — product-market fit first, then optimize revenue
- **Mobile app** — responsive web first, native later if demand proves it
- **Real-time collaboration** — single-user check loop is the MVP; multiplayer comes in Phase 7
- **Versioning/diff between deck versions** — useful but not core to the check→fix loop
- **White-labeling** — enterprise Phase 7 item, not a priority until first 10 paying customers
