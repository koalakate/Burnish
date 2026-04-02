# Plan: Burnish Phase 2 — Upload-Check-Fix Loop (Jake's Journey)

> **Goal:** End-to-end flow: upload PPTX → async check → view results → "Fix All" → download corrected PPTX.
>
> **Exit criteria:** Jake's full CJM works: drag deck → wait <10s → see issues → "Fix All" → download corrected PPTX. Opens correctly in PowerPoint.
>
> **Ref:** Product Roadmap Phase 2, MVP Plan Tasks 11, 13, 14, 16, 17, 19, 20
>
> **Depends on:** Phase 0 (scaffold), Phase 1 (check engine, CSM, parsers)

## Validation Commands
- `ruff check services/ packages/`
- `mypy services/ packages/ --ignore-missing-imports`
- `pytest packages/ services/ tests/ -x --tb=short`
- `cd apps/web && npm run lint && npm run build`

### Task 1: Correction engine — correctors
- [x] Create `services/correction/__init__.py` and `services/correction/engine.py` with `CorrectionEngine` class that takes a list of corrector functions and applies them to CSM
- [x] Create `services/correction/correctors/__init__.py`
- [x] Create `services/correction/correctors/color.py` — swap off-brand colors to the nearest brand palette color (using Delta-E result from the issue's details)
- [x] Create `services/correction/correctors/font.py` — substitute disallowed fonts with the first allowed brand font, preserving size and weight
- [x] Create `services/correction/correctors/contrast.py` — adjust text or background color to meet WCAG AA contrast ratio (lighten/darken the less prominent color)
- [x] Create `services/correction/correctors/font_size.py` — bump font sizes below the brand minimum to the minimum, scaling proportionally within a text box
- [x] Create `services/correction/correctors/alignment.py` — snap elements to the nearest grid line based on brand layout rules (margin, alignment grid)
- [x] Each corrector signature: `(csm: CSM, issues: List[Issue], brand: BrandRuleset) -> CSM` (returns modified copy, original untouched)
- [x] Write tests for each corrector: apply to a CSM with known issues → verify the issue is resolved in the corrected CSM

### Task 2: PPTX exporter (corrected CSM → .pptx)
- [x] Create `services/correction/exporter.py` with `export_pptx(original_pptx_path: Path, corrected_csm: CSM) -> bytes`
- [x] Strategy: open the original PPTX with python-pptx, apply CSM corrections to matching shapes (by element ID), save as new .pptx
- [x] Handle: color changes (text run, shape fill), font substitution, font size changes, element repositioning
- [x] Preserve all original PPTX elements not touched by corrections (animations, transitions, notes, media)
- [x] Write tests: export a corrected CSM → re-parse the exported PPTX → verify corrections were applied and untouched elements are preserved

### Task 3: Deck upload + check trigger API routes
- [x] Implement `POST /api/decks/upload` in `services/api/routers/decks.py` — accept multipart PPTX upload, validate file type/size (max 50MB), store in R2 with org-prefixed key, create Deck DB record, return deck_id
- [x] Implement `GET /api/decks` — list decks for current org (paginated)
- [x] Implement `GET /api/decks/{deck_id}` — get deck details including status and thumbnail URLs
- [x] Implement `DELETE /api/decks/{deck_id}` — soft-delete deck and mark R2 files for cleanup
- [x] Implement `POST /api/decks/{deck_id}/check` in `services/api/routers/checks.py` — enqueue check job to BullMQ, return check_run_id
- [x] Implement `GET /api/checks/{check_run_id}` — get check status, overall DQS, per-slide summary
- [x] Implement `GET /api/checks/{check_run_id}/slides/{slide_index}` — get per-slide issues with bounding boxes
- [x] All routes enforce org-scoped RLS via middleware
- [x] Write API tests: upload flow, check trigger, results retrieval, 404 for wrong org

### Task 4: Correction API routes
- [x] Implement `GET /api/checks/{check_run_id}/corrections` in `services/api/routers/corrections.py` — list all corrections grouped by slide
- [x] Implement `POST /api/checks/{check_run_id}/corrections/{correction_id}/accept` — mark correction as accepted
- [x] Implement `POST /api/checks/{check_run_id}/corrections/{correction_id}/dismiss` — mark correction as dismissed
- [x] Implement `POST /api/checks/{check_run_id}/fix-all` — accept all corrections, trigger export worker
- [x] Implement `GET /api/checks/{check_run_id}/export` — download the corrected PPTX (returns signed R2 URL)
- [x] Write API tests: accept/dismiss flow, fix-all, export download

### Task 5: BullMQ workers — ingestion, check, correction
- [x] Create `services/workers/__init__.py` and `services/workers/main.py` — BullMQ worker entry point that registers all job processors
- [x] Create `services/workers/ingestion_worker.py` — on deck upload: download PPTX from R2, parse to CSM, generate slide thumbnails (PNG via Pillow), store CSM in DB (JSONB), upload thumbnails to R2, update deck status to "parsed"
- [x] Create `services/workers/check_worker.py` — on check trigger: load CSM from DB, load brand ruleset, run rule engine + vision scorer in parallel, calculate DQS, store results (issues, scores) in DB, update check_run status to "complete"
- [x] Create `services/workers/correction_worker.py` — after check complete: load CSM + issues, run correction engine, store corrected CSM and per-issue corrections in DB, pre-generate corrected PPTX and upload to R2
- [x] Wire workers to listen on BullMQ queues: "ingestion", "check", "correction"
- [x] Add worker to `docker-compose.yml` as a separate service
- [x] Write integration test: upload PPTX → trigger check → poll until complete → verify issues exist → fix-all → download corrected PPTX

### Task 6: Frontend design direction
- [x] Define the visual design language for Burnish UI: color palette, typography scale, spacing system, component patterns
- [x] Design principles: speed-first for Jake (minimal chrome, immediate feedback), depth-available for Priya (expandable panels, detailed views)
- [x] Create a design tokens file at `apps/web/src/lib/design-tokens.ts` with colors, font sizes, spacing values
- [x] Configure Tailwind theme in `tailwind.config.ts` to use design tokens
- [x] Document the design direction in `apps/web/DESIGN.md` for reference

### Task 7: Upload + Deck library UI
- [x] Create `apps/web/src/components/upload-dropzone.tsx` — drag-and-drop PPTX upload with progress bar, file type validation, size limit feedback. Zero forms (Jake's mandate)
- [x] Create `apps/web/src/components/deck-card.tsx` — deck thumbnail, name, date, DQS badge, status indicator (parsing/checking/ready)
- [x] Implement upload page at `(dashboard)/decks/upload/page.tsx` — full-screen dropzone that auto-navigates to check results after upload
- [x] Implement deck library page at `(dashboard)/decks/page.tsx` — grid of deck cards, sorted by recent, with upload CTA
- [x] Wire to API using TanStack Query: upload mutation, deck list query with polling for status updates
- [x] Create Zustand store at `src/lib/stores/deck-store.ts` for active deck state

### Task 8: Check results page + slide preview
- [x] Create `apps/web/src/components/slide-preview.tsx` — Konva.js canvas that renders a slide thumbnail with optional issue overlay bounding boxes
- [x] Create `apps/web/src/components/issue-overlay.tsx` — draw colored bounding boxes on slide canvas (red=error, yellow=warning, blue=info) with click-to-select
- [x] Create `apps/web/src/components/check-panel.tsx` — issue list with severity badges, plain-English descriptions, grouped by evaluator type
- [x] Create `apps/web/src/components/dqs-badge.tsx` — circular DQS score display (green ≥80, yellow 60-79, red <60)
- [x] Implement check results overview at `(dashboard)/checks/[id]/page.tsx` — slide strip (horizontal scrollable row of thumbnails with severity dots), overall DQS, issue count summary
- [x] Implement slide detail at `(dashboard)/checks/[id]/slides/[idx]/page.tsx` — large slide preview with overlays + issue panel on the right
- [x] Wire to API: check results query, slide issues query, auto-poll while status is "checking"
- [x] Live preview with hot-reload: CSM → Konva.js canvas updates in real-time as corrections are applied

### Task 9: Correction view UI (side-by-side)
- [x] Create `apps/web/src/components/correction-view.tsx` — side-by-side view with original slide (left) and corrected slide (right), both rendered via Konva.js
- [x] Highlight changed elements with a subtle glow/outline on the corrected side
- [x] Per-issue correction card: shows what changed ("Font changed: Comic Sans → Inter"), with Accept/Dismiss buttons
- [x] Priya's edit-in-place: clicking a correction opens an inline editor to tweak the AI's suggestion before accepting
- [x] "Fix All" button at the top — applies all corrections, shows progress, then offers download
- [x] Download button: fetches corrected PPTX from export API, triggers browser download
- [x] DQS badge on download confirmation (Priya screenshots this for clients)
- [x] Wire to API: corrections query, accept/dismiss mutations, fix-all mutation, export download

### Task 10: End-to-end integration test
- [x] Write Playwright or Cypress E2E test at `tests/e2e/upload_check_correct.spec.ts`
- [x] Test flow: upload a golden deck PPTX → wait for check results → verify issues are displayed → click "Fix All" → download corrected PPTX → verify file is valid
- [x] Test Jake's mandate: entire flow completes in under 2 minutes wall-clock time
- [x] Test Priya's edit-in-place: dismiss one correction, accept the rest, download
