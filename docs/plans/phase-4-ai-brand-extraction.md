# Plan: Burnish Phase 4 — AI Brand Extraction (Maya's Onboarding)

> **Goal:** Upload a brand guidelines PDF → AI extracts colors, fonts, size rules, and layout preferences automatically.
>
> **Exit criteria:** Maya uploads her 47-page brand PDF. Burnish extracts 12 colors, 4 font families, 6 size rules, and margin preferences — with 75%+ accuracy on first pass. She reviews in the table, accepts 9/12 colors immediately (high confidence), corrects 3. Total time: <10 minutes.
>
> **Ref:** Product Roadmap Phase 4
>
> **Depends on:** Phase 3 (manual brand entry must work as fallback)

## Validation Commands
- `ruff check services/ packages/`
- `mypy services/ packages/ --ignore-missing-imports`
- `pytest packages/ services/ tests/ -x --tb=short`
- `cd apps/web && npm run lint && npm run build`

### Task 1: PDF ingestion pipeline
- [ ] Create `services/extraction/__init__.py` and `services/extraction/pdf_parser.py`
- [ ] Implement `extract_pages(pdf_path: Path) -> List[PageContent]` — extract text, images, and layout from each PDF page using a PDF parsing library (PyMuPDF/fitz or pdfplumber)
- [ ] Extract embedded images (logos, color swatches, example layouts) as separate PNG buffers
- [ ] Extract text with page number and bounding box position for source linking
- [ ] Handle multi-column layouts and tables in brand guideline PDFs
- [ ] Write tests: parse a sample brand PDF fixture → verify page count, text extraction, image extraction

### Task 2: Notion page ingestion
- [ ] Create `services/extraction/notion_parser.py`
- [ ] Implement `extract_notion_page(page_url: str, api_key: str) -> List[PageContent]` — fetch Notion page content via Notion API
- [ ] Extract rich text blocks, images, tables, and nested pages
- [ ] Convert Notion content to the same `PageContent` format as PDF extraction
- [ ] Write tests with mocked Notion API: verify text extraction, image extraction, nested page handling

### Task 3: AI brand rule extraction (Claude 3.5 Sonnet)
- [ ] Create `services/extraction/ai_extractor.py`
- [ ] Implement `extract_brand_rules(pages: List[PageContent]) -> ExtractionResult` that sends page content + images to Claude 3.5 Sonnet
- [ ] Prompt engineering: instruct the model to extract structured JSON with: primary colors (hex), secondary colors (hex), accent colors (hex), font families, font size hierarchy (heading/body/caption), spacing/margin preferences, logo usage rules
- [ ] Each extracted rule includes: `value`, `confidence` (0.0-1.0), `source_page` (page number), `source_snippet` (the text/image that informed the extraction)
- [ ] Handle multi-page context: chunk pages into groups of 5-10, extract from each chunk, then merge and deduplicate results
- [ ] Write tests with mocked Anthropic client: verify prompt construction, structured output parsing, confidence scores

### Task 4: Extraction result → BrandRuleset conversion
- [ ] Create `services/extraction/converter.py`
- [ ] Implement `to_brand_ruleset(extraction: ExtractionResult) -> BrandRuleset` — convert AI extraction output to the BrandRuleset model
- [ ] Map extracted colors to Color objects with default tolerance (Delta-E 10)
- [ ] Map extracted fonts to font family rules with inferred weight ranges
- [ ] Map extracted size hierarchy to size rules per role
- [ ] Preserve confidence scores and source references as metadata on each rule
- [ ] Flag low-confidence rules (< 0.5) for manual review
- [ ] Write tests: convert a known extraction result → verify BrandRuleset has correct colors, fonts, and size rules

### Task 5: Extraction review UI
- [ ] Create extraction upload page at `(dashboard)/brand/extract/page.tsx` — upload PDF or paste Notion URL, show extraction progress
- [ ] Create `apps/web/src/components/extraction-review-table.tsx` — table of extracted rules with columns: Rule Type, Value (color swatch / font name / size), Confidence (progress bar), Source (page number link), Action (Accept / Edit / Reject)
- [ ] Color rows: show hex swatch + color name if detected, confidence bar, link to source PDF page
- [ ] Font rows: show font family name + sample text rendered in that font, weight range, confidence
- [ ] Size rows: show role (title/body/caption) + extracted min/max, confidence
- [ ] Bulk actions toolbar: "Accept All High-Confidence" (confidence > 0.85), "Reject All Low-Confidence" (confidence < 0.3)
- [ ] Edit action: inline editor to modify the extracted value before accepting
- [ ] Source snippet preview: clicking source link shows the relevant PDF page region or Notion block
- [ ] "Save as Brand Ruleset" button: converts accepted rules into a BrandRuleset, redirects to brand editor for final tweaks

### Task 6: Extraction worker + API routes
- [ ] Implement `POST /api/brands/extract` — accept PDF upload or Notion URL, enqueue extraction job
- [ ] Create `services/workers/extraction_worker.py` — process extraction job: parse PDF/Notion → AI extraction → store ExtractionResult in DB
- [ ] Implement `GET /api/extractions/{extraction_id}` — get extraction status and results
- [ ] Implement `POST /api/extractions/{extraction_id}/accept` — accept selected rules and create BrandRuleset
- [ ] Add extraction queue to BullMQ worker setup
- [ ] Write integration test: upload PDF → extraction completes → review results → accept → verify BrandRuleset is created and usable for checking

### Task 7: Configurable confidence thresholds
- [ ] Add `auto_accept_threshold` (default 0.85) and `auto_reject_threshold` (default 0.3) to org settings
- [ ] In the extraction review UI, pre-check "Accept" for rules above auto-accept threshold
- [ ] Show warning banner for rules between thresholds: "These rules need your review"
- [ ] Maya can adjust thresholds in org settings
- [ ] Write tests: extraction with various confidence scores → verify correct pre-selection based on thresholds
