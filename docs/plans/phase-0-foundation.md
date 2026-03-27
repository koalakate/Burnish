# Plan: Burnish Phase 0 — Foundation & Scaffold

> **Goal:** Runnable project skeleton — CI passes, Docker spins up, DB migrates, frontend renders a shell.
>
> **Exit criteria:** `docker compose up` boots the full stack. Authenticated user sees an empty dashboard shell.
>
> **Ref:** Product Roadmap Phase 0, MVP Plan Tasks 1, 3, 4, 12, 15
>
> **Depends on:** Nothing (this is the starting point)

## Validation Commands
- `cd apps/web && npm run lint && npm run build`
- `ruff check services/ packages/`
- `mypy services/ packages/ --ignore-missing-imports`
- `pytest packages/ services/ tests/ -x --tb=short`
- `docker compose config -q`

### Task 1: Initialize git repo and monorepo scaffold
- [ ] Initialize git repository
- [ ] Create `pyproject.toml` with all Python dependencies (fastapi, sqlalchemy, python-pptx, openai, anthropic, colormath, etc.) and dev tools (pytest, ruff, mypy)
- [ ] Create `docker-compose.yml` with PostgreSQL 16 (pgvector image) and Redis 7
- [ ] Create `.env.example` with all required env vars (DATABASE_URL, REDIS_URL, CLERK keys, AI keys, R2 storage)
- [ ] Create `.gitignore` for Python and Node artifacts
- [ ] Create root `conftest.py` that adds `packages/` and `services/` to sys.path
- [ ] Create empty `__init__.py` stubs: `services/__init__.py`, `packages/__init__.py`, `packages/csm/__init__.py`, `tests/__init__.py`, `tests/golden_decks/__init__.py`
- [ ] Verify: `docker compose up -d` starts postgres and redis healthy

### Task 2: SQLAlchemy async engine + Alembic migration harness
- [ ] Create `services/db/__init__.py`
- [ ] Create `services/db/engine.py` with async SQLAlchemy engine and session factory using `DATABASE_URL` from env
- [ ] Create `services/db/models/__init__.py` and `services/db/models/base.py` with declarative base, common mixins (id UUID, created_at, updated_at, org_id for RLS)
- [ ] Create `alembic.ini` pointing to `services/db/migrations/`
- [ ] Create `alembic/env.py` configured for async SQLAlchemy
- [ ] Create initial DB models: `services/db/models/org.py` (Organization, User), `services/db/models/deck.py` (Deck), `services/db/models/brand.py` (BrandRuleset), `services/db/models/check.py` (CheckRun, SlideCheckResult, Issue)
- [ ] Generate and run initial Alembic migration
- [ ] Write test: verify session creation and basic model CRUD against test database
- [ ] Verify: all models have `org_id` column for row-level security scoping

### Task 3: Cloudflare R2 storage client
- [ ] Create `services/storage/__init__.py` and `services/storage/r2.py`
- [ ] Implement R2Client class with methods: `upload_file(key, data, content_type)`, `download_file(key)`, `generate_signed_url(key, expires_in)`, `delete_file(key)`
- [ ] All keys are prefixed with `org_id/` to enforce per-org isolation
- [ ] Use boto3 with S3-compatible endpoint configuration
- [ ] Write tests with mocked boto3 client: upload, download, signed URL generation, org-prefix enforcement
- [ ] Add `R2_ACCOUNT_ID`, `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY`, `R2_BUCKET_NAME`, `R2_ENDPOINT_URL` to pydantic-settings config

### Task 4: FastAPI application skeleton + Clerk auth middleware
- [ ] Create `services/api/__init__.py` and `services/api/main.py` with FastAPI app, CORS middleware, health check endpoint
- [ ] Create `services/api/deps.py` with dependency injection: `get_db_session`, `get_current_user`, `get_current_org`
- [ ] Create `services/api/middleware/__init__.py` and `services/api/middleware/auth.py` — Clerk JWT verification middleware (decode JWT, extract user_id and org_id)
- [ ] Create `services/api/middleware/tenant.py` — inject org_id into SQLAlchemy session for RLS scoping
- [ ] Create empty router files: `services/api/routers/decks.py`, `services/api/routers/checks.py`, `services/api/routers/corrections.py`, `services/api/routers/brand.py`
- [ ] Create schema stubs: `services/api/schemas/deck_schemas.py`, `services/api/schemas/check_schemas.py`, `services/api/schemas/correction_schemas.py`, `services/api/schemas/brand_schemas.py`
- [ ] Write test: health check returns 200, unauthenticated request returns 401
- [ ] Verify: `uvicorn services.api.main:app` starts without errors

### Task 5: Next.js 14 frontend scaffold with Clerk auth
- [ ] Initialize Next.js 14 app in `apps/web/` with TypeScript, Tailwind CSS, App Router
- [ ] Install and configure shadcn/ui
- [ ] Install and configure Clerk: `@clerk/nextjs` with sign-in/sign-up pages at `(auth)/sign-in/[[...sign-in]]/page.tsx` and `(auth)/sign-up/[[...sign-up]]/page.tsx`
- [ ] Create `src/middleware.ts` with Clerk auth middleware protecting `(dashboard)` routes
- [ ] Create dashboard layout shell at `(dashboard)/layout.tsx` — sidebar navigation + header with user button
- [ ] Create placeholder pages: `(dashboard)/page.tsx` (home), `(dashboard)/decks/page.tsx` (deck library), `(dashboard)/brand/page.tsx` (brand rulesets), `(dashboard)/settings/page.tsx`
- [ ] Create `src/lib/api.ts` — type-safe fetch wrapper pointing to FastAPI backend
- [ ] Create `src/lib/types.ts` — shared TypeScript types mirroring Python schemas (Deck, CheckRun, Issue, BrandRuleset)
- [ ] Verify: `npm run dev` serves the app, sign-in page renders, authenticated user sees empty dashboard shell

### Task 6: CI pipeline setup
- [ ] Create `.github/workflows/ci.yml` with jobs: lint (ruff + mypy), test (pytest), frontend (npm lint + build)
- [ ] Configure pytest to run with `--tb=short -q` in CI
- [ ] Add Docker Compose service startup in CI for integration tests (postgres + redis)
- [ ] Verify: CI pipeline passes with empty test suite
