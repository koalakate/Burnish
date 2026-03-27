# Plan: Burnish Phase 6 — Integrations & Scale

> **Goal:** Meet users where they work. Scale to enterprise.
>
> **Exit criteria:** This phase is incremental — each task is independently shippable. Each integration has its own exit criteria below.
>
> **Ref:** Product Roadmap Phase 6
>
> **Depends on:** Phase 4 (core product must be complete before extending)

## Validation Commands
- `ruff check services/ packages/`
- `mypy services/ packages/ --ignore-missing-imports`
- `pytest packages/ services/ tests/ -x --tb=short`
- `cd apps/web && npm run lint && npm run build`

### Task 1: Google Slides import/export
- [ ] Create `services/integrations/__init__.py` and `services/integrations/google_slides.py`
- [ ] Implement Google OAuth2 flow: user connects their Google account, store refresh token securely (encrypted at rest)
- [ ] Implement `import_google_slides(presentation_id: str, credentials) -> CSM` — fetch Google Slides presentation via API, convert to CSM (map Google Slides elements to CSM types: text boxes, images, shapes, tables)
- [ ] Implement `export_to_google_slides(csm: CSM, credentials) -> str` — create or update a Google Slides presentation from CSM, return presentation ID
- [ ] Handle Google Slides-specific features: speaker notes, slide transitions, master slide references
- [ ] Add Google Slides as import source on upload page: "Import from Google Slides" button with presentation URL input
- [ ] Add "Export to Google Slides" option alongside PPTX download on correction/generation results
- [ ] Implement `POST /api/integrations/google/import` and `POST /api/integrations/google/export` API routes
- [ ] Write tests with mocked Google API: import → CSM conversion, CSM → export, round-trip fidelity

### Task 2: Slack integration — check decks via Slack
- [ ] Create `services/integrations/slack.py`
- [ ] Implement Slack app with slash command: `/burnish check [file_url]` — triggers a check on the attached or linked PPTX
- [ ] Implement Slack bot: when a .pptx file is shared in a channel where bot is installed, offer "Check this deck?" button
- [ ] Post check results as a threaded message: DQS badge, top 3 issues, "View full results" link to Burnish web UI
- [ ] Support Slack file upload: bot downloads the attached PPTX, runs check, posts results
- [ ] Implement `POST /api/integrations/slack/events` webhook endpoint for Slack event subscriptions
- [ ] Implement `POST /api/integrations/slack/commands` for slash command handling
- [ ] Add Slack configuration page in settings: install bot to workspace, select default brand for Slack checks
- [ ] Write tests: simulate Slack event → verify check is triggered → verify result message format

### Task 3: Figma integration
- [ ] Create `services/integrations/figma.py`
- [ ] Implement Figma OAuth2 flow for user authentication
- [ ] Implement `import_figma_frames(file_key: str, node_ids: List[str], credentials) -> CSM` — fetch Figma frames via API, convert to CSM (map Figma nodes to CSM elements: text, rectangles, images, groups)
- [ ] Implement `export_to_figma(csm: CSM, credentials) -> str` — create a new Figma file from CSM (using Figma's REST API or plugin API)
- [ ] Handle Figma-specific properties: auto-layout, constraints, component instances
- [ ] Add "Import from Figma" source on upload page with Figma file URL + frame selector
- [ ] Add "Export to Figma" option on results page
- [ ] Write tests with mocked Figma API: import frames → CSM, CSM → Figma export

### Task 4: Public API + API keys
- [ ] Create `services/api/routers/api_keys.py` — CRUD for org API keys (generate, list, revoke)
- [ ] Implement API key authentication middleware: accept `X-API-Key` header as alternative to Clerk JWT
- [ ] API keys are scoped to org and have configurable permissions (read, check, correct, generate)
- [ ] Rate limiting per API key: configurable requests/minute (default 60)
- [ ] Create API documentation page: auto-generated OpenAPI spec served at `/api/docs`
- [ ] Add API key management page in settings UI: generate key, copy key, revoke key, view usage
- [ ] Write tests: create API key → use for check flow → verify org scoping, rate limiting, permission enforcement

### Task 5: Webhooks — notify external systems
- [ ] Create `services/integrations/webhooks.py`
- [ ] Implement `POST /api/webhooks` — register a webhook URL for events: `check.complete`, `correction.complete`, `generation.complete`
- [ ] Implement webhook delivery: on event, POST JSON payload to registered URL with HMAC signature for verification
- [ ] Retry logic: 3 retries with exponential backoff (1s, 5s, 25s), log failures
- [ ] Webhook management UI in settings: add URL, select events, view delivery log, test webhook
- [ ] Write tests: register webhook → trigger event → verify payload delivered with correct signature

### Task 6: SSO/SCIM for enterprise identity management
- [ ] Configure Clerk Enterprise SSO: SAML 2.0 and OIDC support
- [ ] Implement SCIM 2.0 provisioning endpoint at `/api/scim/v2/` — user provisioning (create, update, deactivate), group provisioning
- [ ] Map SCIM groups to Burnish org roles (admin, editor, viewer)
- [ ] Auto-provision users on first SSO login: create user record, assign to org
- [ ] Handle user deprovisioning: deactivate user, preserve their check history (don't delete)
- [ ] Write tests: SCIM user provision → verify Burnish user created, SCIM deactivation → verify user deactivated but data preserved

### Task 7: Bulk operations — org-wide audit
- [ ] Implement `POST /api/decks/bulk-check` — accept list of deck_ids or "all decks in org", enqueue batch check jobs
- [ ] Implement batch progress tracking: `GET /api/bulk/{batch_id}` — overall progress (X/Y complete), per-deck status
- [ ] UI: "Audit All Decks" button on deck library page, progress modal showing completion
- [ ] Results summary page: table of all decks with DQS, sorted by worst first, bulk "Fix All" option
- [ ] Rate limit bulk operations to prevent overwhelming workers (max 50 decks per batch)
- [ ] Write tests: bulk check 5 decks → verify all complete, progress tracking accurate

### Task 8: Custom evaluator plugin system
- [ ] Create `services/rules/evaluators/custom.py` — custom evaluator runner
- [ ] Define custom evaluator format: JSON rule definition with condition (element selector + property check) and issue template (severity, message)
- [ ] Example: `{"selector": "slide[index=0] text[role=title]", "check": "contains", "value": "Legal Disclaimer", "severity": "error", "message": "Slide 1 must contain a legal disclaimer"}`
- [ ] Implement `POST /api/brands/{brand_id}/custom-rules` — CRUD for custom evaluator rules attached to a brand ruleset
- [ ] UI: custom rules editor in brand ruleset page — rule builder with condition picker and message template
- [ ] Write tests: define custom rule → run check → verify custom issue is emitted when condition is violated
