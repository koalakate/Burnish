# Plan: Burnish Phase 3 — Brand Setup & Multi-Brand (Maya + Priya)

> **Goal:** Manual brand ruleset creation, org-level defaults, multi-brand switching.
>
> **Exit criteria:** Priya can create 3 brand rulesets, switch between them, upload a deck selecting "Acme Corp," and get issues checked against Acme's specific rules — not another client's.
>
> **Ref:** Product Roadmap Phase 3, MVP Plan Task 18 + new work
>
> **Depends on:** Phase 2 (upload-check-fix loop must work end-to-end)

## Validation Commands
- `ruff check services/ packages/`
- `mypy services/ packages/ --ignore-missing-imports`
- `pytest packages/ services/ tests/ -x --tb=short`
- `cd apps/web && npm run lint && npm run build`

### Task 1: Brand ruleset CRUD API
- [ ] Implement `POST /api/brands` in `services/api/routers/brand.py` — create a new brand ruleset for the current org. Accept: name, colors (list with hex + tolerance), fonts (list with family + allowed weights), size rules (per-role min/max), layout rules (margins, max elements, grid)
- [ ] Implement `GET /api/brands` — list all brand rulesets for current org
- [ ] Implement `GET /api/brands/{brand_id}` — get full brand ruleset details
- [ ] Implement `PUT /api/brands/{brand_id}` — update brand ruleset (partial update supported)
- [ ] Implement `DELETE /api/brands/{brand_id}` — soft-delete brand ruleset (prevent deletion if it's the org default)
- [ ] Implement `POST /api/brands/{brand_id}/duplicate` — clone a brand ruleset with " (Copy)" suffix (Priya: clone Acme Corp → Acme Corp v2)
- [ ] All routes scoped to org via RLS middleware
- [ ] Write API tests: full CRUD cycle, duplication, org isolation (brand from org A not visible to org B)

### Task 2: Org-level default brand ruleset
- [ ] Add `default_brand_id` column to Organization model
- [ ] Implement `PUT /api/org/settings` — set org default brand ruleset
- [ ] Implement `GET /api/org/settings` — get org settings including default brand
- [ ] When a deck is uploaded without selecting a brand, auto-assign the org default
- [ ] If no org default is set and no brand selected, return a clear error: "Please select a brand ruleset or set an org default in settings"
- [ ] Write tests: upload with explicit brand, upload with org default fallback, upload with neither (error)

### Task 3: Brand selector on upload + check flow
- [ ] Modify `POST /api/decks/upload` to accept optional `brand_id` parameter
- [ ] Modify `POST /api/decks/{deck_id}/check` to accept optional `brand_id` override (re-check against different brand)
- [ ] Store active brand_id on CheckRun record so results are traceable to which ruleset was used
- [ ] Update frontend upload dropzone: add a brand selector dropdown (compact, non-intrusive for Jake — defaults to org default, expandable for Priya)
- [ ] Show active brand indicator on check results page header: "Checked against: Acme Corp Brand"
- [ ] Write tests: check with brand A produces different results than check with brand B for the same deck

### Task 4: Brand ruleset editor UI
- [ ] Implement brand list page at `(dashboard)/brand/page.tsx` — grid of brand cards with name, color swatches preview, font list, "Set as Default" button, duplicate button
- [ ] Implement brand editor at `(dashboard)/brand/[id]/page.tsx` with sections:
- [ ] **Color section**: add/remove brand colors, color picker with hex input, per-color Delta-E tolerance slider (1-30, default 10)
- [ ] **Font section**: add/remove font families, per-font allowed weight range checkboxes (100-900)
- [ ] **Size rules section**: min/max font size per role (title, body, caption) with number inputs
- [ ] **Layout section**: margin values (top/right/bottom/left in pt), max elements per slide, alignment grid toggle
- [ ] Live preview panel: "If this color appears in a deck, it will be flagged" — show a sample slide with violations highlighted using current rules
- [ ] Auto-save on change (debounced 500ms) with save indicator
- [ ] Create `apps/web/src/components/brand-rule-editor.tsx` component

### Task 5: Brand-as-plugin architecture (swappable theme objects)
- [ ] Refactor BrandRuleset to be fully self-contained and portable: all rules, tolerances, and default templates in a single JSON-serializable object
- [ ] Implement `POST /api/brands/import` — import a brand ruleset from JSON file
- [ ] Implement `GET /api/brands/{brand_id}/export` — export brand ruleset as downloadable JSON
- [ ] Add brand ruleset version field with auto-increment on update (for audit trail)
- [ ] Write tests: export brand → import into different org → verify identical rules

### Task 6: Multi-brand integration test
- [ ] Create 3 brand rulesets with distinct rules (different color palettes, different fonts, different size minimums)
- [ ] Upload a single deck that violates all 3 brands differently
- [ ] Run check against each brand → verify each produces different issues specific to that brand's rules
- [ ] Switch default brand → upload without selecting → verify default is applied
- [ ] Duplicate a brand → modify the copy → verify original is unchanged
