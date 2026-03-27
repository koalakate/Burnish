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
- [ ] Create `services/correction/__init__.py` and `services/correction/engine.py` with `CorrectionEngine` class that takes a list of corrector functions and applies them to CSM
- [ ] Create `services/correction/correctors/__init__.py`
- [ ] Create `services/correction/correctors/color.py` — swap off-brand colors to the nearest brand palette color (using Delta-E result from the issue's details)
- [ ] Create `services/correction/correctors/font.py` — substitute disallowed fonts with the first allowed brand font, preserving size and weight
- [ ] Create `services/correction/correctors/contrast.py` — adjust text or background color to meet WCAG AA contrast ratio (lighten/darken the less prominent color)
- [ ] Create `services/correction/correctors/font_size.py` — bump font sizes below the brand minimum to the minimum, scaling proportionally within a text box
- [ ] Create `services/correction/correctors/alignment.py` — snap elements to the nearest grid line based on brand layout rules (margin, alignment grid)
- [ ] Each corrector signature: `(csm: CSM, issues: List[Issue], brand: BrandRuleset) -> CSM` (returns modified copy, original untouched)
- [ ] Write tests for each corrector: apply to a CSM with known issues → verify the issue is resolved in the corrected CSM

### Task 2: PPTX exporter (corrected CSM → .pptx)
- [ ] Create `services/correction/exporter.py` with `export_pptx(original_pptx_path: Path, corrected_csm: CSM) -> bytes`
- [ ] Strategy: open the original PPTX with python-pptx, apply CSM corrections to matching shapes (by element ID), save as new .pptx
- [ ] Handle: color changes (text run, shape fill), font substitution, font size changes, element repositioning
- [ ] Preserve all original PPTX elements not touched by corrections (animations, transitions, notes, media)
- [ ] Write tests: export a corrected CSM → re-parse the exported PPTX → verify corrections were applied and untouched elements are preserved

### Task 3: Deck upload + check trigger API routes
- [ ] Implement `POST /api/decks/upload` in `services/api/routers/decks.py` — accept multipart PPTX upload, validate file type/size (max 50MB), store in R2 with org-prefixed key, create Deck DB record, return deck_id
- [ ] Implement `GET /api/decks` — list decks for current org (paginated)
- [ ] Implement `GET /api/decks/{deck_id}` — get deck details including status and thumbnail URLs
- [ ] Implement `DELETE /api/decks/{deck_id}` — soft-delete deck and mark R2 files for cleanup
- [ ] Implement `POST /api/decks/{deck_id}/check` in `services/api/routers/checks.py` — enqueue check job to BullMQ, return check_run_id
- [ ] Implement `GET /api/checks/{check_run_id}` — get check status, overall DQS, per-slide summary
- [ ] Implement `GET /api/checks/{check_run_id}/slides/{slide_index}` — get per-slide issues with bounding boxes
- [ ] All routes enforce org-scoped RLS via middleware
- [ ] Write API tests: upload flow, check trigger, results retrieval, 404 for wrong org

### Task 4: Correction API routes
- [ ] Implement `GET /api/checks/{check_run_id}/corrections` in `services/api/routers/corrections.py` — list all corrections grouped by slide
- [ ] Implement `POST /api/checks/{check_run_id}/corrections/{correction_id}/accept` — mark correction as accepted
- [ ] Implement `POST /api/checks/{check_run_id}/corrections/{correction_id}/dismiss` — mark correction as dismissed
- [ ] Implement `POST /api/checks/{check_run_id}/fix-all` — accept all corrections, trigger export worker
- [ ] Implement `GET /api/checks/{check_run_id}/export` — download the corrected PPTX (returns signed R2 URL)
- [ ] Write API tests: accept/dismiss flow, fix-all, export download

### Task 5: BullMQ workers — ingestion, check, correction
- [ ] Create `services/workers/__init__.py` and `services/workers/main.py` — BullMQ worker entry point that registers all job processors
- [ ] Create `services/workers/ingestion_worker.py` — on deck upload: download PPTX from R2, parse to CSM, generate slide thumbnails (PNG via Pillow), store CSM in DB (JSONB), upload thumbnails to R2, update deck status to "parsed"
- [ ] Create `services/workers/check_worker.py` — on check trigger: load CSM from DB, load brand ruleset, run rule engine + vision scorer in parallel, calculate DQS, store results (issues, scores) in DB, update check_run status to "complete"
- [ ] Create `services/workers/correction_worker.py` — after check complete: load CSM + issues, run correction engine, store corrected CSM and per-issue corrections in DB, pre-generate corrected PPTX and upload to R2
- [ ] Wire workers to listen on BullMQ queues: "ingestion", "check", "correction"
- [ ] Add worker to `docker-compose.yml` as a separate service
- [ ] Write integration test: upload PPTX → trigger check → poll until complete → verify issues exist → fix-all → download corrected PPTX

### Task 6: Frontend design direction
- [ ] Define the visual design language for Burnish UI: color palette, typography scale, spacing system, component patterns
- [ ] Design principles: speed-first for Jake (minimal chrome, immediate feedback), depth-available for Priya (expandable panels, detailed views)
- [ ] Create a design tokens file at `apps/web/src/lib/design-tokens.ts` with colors, font sizes, spacing values
- [ ] Configure Tailwind theme in `tailwind.config.ts` to use design tokens
- [ ] Document the design direction in `apps/web/DESIGN.md` for reference

### Task 7: Upload + Deck library UI
- [ ] Create `apps/web/src/components/upload-dropzone.tsx` — drag-and-drop PPTX upload with progress bar, file type validation, size limit feedback. Zero forms (Jake's mandate)
- [ ] Create `apps/web/src/components/deck-card.tsx` — deck thumbnail, name, date, DQS badge, status indicator (parsing/checking/ready)
- [ ] Implement upload page at `(dashboard)/decks/upload/page.tsx` — full-screen dropzone that auto-navigates to check results after upload
- [ ] Implement deck library page at `(dashboard)/decks/page.tsx` — grid of deck cards, sorted by recent, with upload CTA
- [ ] Wire to API using TanStack Query: upload mutation, deck list query with polling for status updates
- [ ] Create Zustand store at `src/lib/stores/deck-store.ts` for active deck state

### Task 8: Check results page + slide preview
- [ ] Create `apps/web/src/components/slide-preview.tsx` — Konva.js canvas that renders a slide thumbnail with optional issue overlay bounding boxes
- [ ] Create `apps/web/src/components/issue-overlay.tsx` — draw colored bounding boxes on slide canvas (red=error, yellow=warning, blue=info) with click-to-select
- [ ] Create `apps/web/src/components/check-panel.tsx` — issue list with severity badges, plain-English descriptions, grouped by evaluator type
- [ ] Create `apps/web/src/components/dqs-badge.tsx` — circular DQS score display (green ≥80, yellow 60-79, red <60)
- [ ] Implement check results overview at `(dashboard)/checks/[id]/page.tsx` — slide strip (horizontal scrollable row of thumbnails with severity dots), overall DQS, issue count summary
- [ ] Implement slide detail at `(dashboard)/checks/[id]/slides/[idx]/page.tsx` — large slide preview with overlays + issue panel on the right
- [ ] Wire to API: check results query, slide issues query, auto-poll while status is "checking"
- [ ] Live preview with hot-reload: CSM → Konva.js canvas updates in real-time as corrections are applied

### Task 9: Correction view UI (side-by-side)
- [ ] Create `apps/web/src/components/correction-view.tsx` — side-by-side view with original slide (left) and corrected slide (right), both rendered via Konva.js
- [ ] Highlight changed elements with a subtle glow/outline on the corrected side
- [ ] Per-issue correction card: shows what changed ("Font changed: Comic Sans → Inter"), with Accept/Dismiss buttons
- [ ] Priya's edit-in-place: clicking a correction opens an inline editor to tweak the AI's suggestion before accepting
- [ ] "Fix All" button at the top — applies all corrections, shows progress, then offers download
- [ ] Download button: fetches corrected PPTX from export API, triggers browser download
- [ ] DQS badge on download confirmation (Priya screenshots this for clients)
- [ ] Wire to API: corrections query, accept/dismiss mutations, fix-all mutation, export download

### Task 10: End-to-end integration test
- [ ] Write Playwright or Cypress E2E test at `tests/e2e/upload_check_correct.spec.ts`
- [ ] Test flow: upload a golden deck PPTX → wait for check results → verify issues are displayed → click "Fix All" → download corrected PPTX → verify file is valid
- [ ] Test Jake's mandate: entire flow completes in under 2 minutes wall-clock time
- [ ] Test Priya's edit-in-place: dismiss one correction, accept the rest, download
