# Burnish Core MVP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the core Burnish product — upload a PPTX, check it against brand rules, view per-slide issues with severity, and accept AI-generated corrections — end-to-end.

**Architecture:** Python/FastAPI backend with BullMQ workers for async processing. PPTX files are parsed into a Canonical Slide Model (CSM), evaluated by a rule engine + GPT-4o vision scorer, then corrected and re-exported. Next.js 14 frontend with Clerk auth, Konva.js slide previews, and a side-by-side correction UI.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy 2.x (async), Alembic, python-pptx, Redis + BullMQ, PostgreSQL 16 + pgvector, Cloudflare R2, Next.js 14, TypeScript, Tailwind CSS, shadcn/ui, Zustand, TanStack Query, Konva.js, Clerk, OpenAI GPT-4o, Anthropic Claude 3.5 Sonnet.

---

## File Structure

```
# The repo root IS the project root. No `burnish/` subdirectory.
# All paths below are relative to the repo root.
├── pyproject.toml                         # Python monorepo config (uv/hatch)
├── alembic.ini
├── alembic/
│   ├── env.py
│   └── versions/
├── docker-compose.yml
├── .env.example
├── .gitignore
├── packages/
│   └── csm/
│       ├── __init__.py
│       ├── models.py                      # Pydantic CSM types (shared across all services)
│       └── test_models.py
├── services/
│   ├── __init__.py
│   ├── api/
│   │   ├── __init__.py
│   │   ├── main.py                        # FastAPI app entry point
│   │   ├── deps.py                        # Dependency injection (db session, current user, current org)
│   │   ├── middleware/
│   │   │   ├── __init__.py
│   │   │   ├── auth.py                    # Clerk JWT verification
│   │   │   └── tenant.py                  # RLS org context injection
│   │   ├── routers/
│   │   │   ├── __init__.py
│   │   │   ├── decks.py                   # Upload, list, get, delete decks
│   │   │   ├── checks.py                  # Trigger check, get results, per-slide results
│   │   │   ├── corrections.py             # Accept/dismiss corrections
│   │   │   └── brand.py                   # CRUD brand rulesets (manual editor)
│   │   └── schemas/
│   │       ├── __init__.py
│   │       ├── deck_schemas.py
│   │       ├── check_schemas.py
│   │       ├── correction_schemas.py
│   │       └── brand_schemas.py
│   ├── db/
│   │   ├── __init__.py
│   │   ├── engine.py                      # Async SQLAlchemy engine + session factory
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   ├── base.py                    # Declarative base + common mixins
│   │   │   ├── org.py                     # Organization, User
│   │   │   ├── brand.py                   # BrandRuleset
│   │   │   ├── deck.py                    # Deck
│   │   │   ├── check.py                   # CheckRun, SlideCheckResult, Issue
│   │   │   └── generation.py              # (future — stub)
│   │   └── migrations/                    # Alembic-managed
│   ├── ingestion/
│   │   ├── __init__.py
│   │   ├── pptx_parser.py                 # python-pptx → CSM
│   │   ├── thumbnail.py                   # CSM slide → PNG thumbnail via Pillow
│   │   └── test_pptx_parser.py
│   ├── rules/
│   │   ├── __init__.py
│   │   ├── engine.py                      # Orchestrates all evaluators
│   │   ├── evaluators/
│   │   │   ├── __init__.py
│   │   │   ├── color.py                   # Brand palette compliance (Delta-E CIELAB)
│   │   │   ├── typography.py              # Font family, size, weight checks
│   │   │   ├── layout.py                  # Margins, alignment, element count
│   │   │   ├── accessibility.py           # WCAG AA contrast ratio
│   │   │   ├── content.py                 # Text density, bullet count, empty placeholders
│   │   │   └── image.py                   # DPI, aspect ratio distortion, alt text
│   │   ├── models.py                      # Issue, Severity, SlideIssueSet types
│   │   └── tests/
│   │       ├── test_color.py
│   │       ├── test_typography.py
│   │       ├── test_layout.py
│   │       ├── test_accessibility.py
│   │       ├── test_content.py
│   │       └── test_image.py
│   ├── vision/
│   │   ├── __init__.py
│   │   ├── scorer.py                      # GPT-4o vision scoring per slide
│   │   ├── rubric.py                      # Scoring rubric prompt + output schema
│   │   └── test_scorer.py
│   ├── correction/
│   │   ├── __init__.py
│   │   ├── engine.py                      # Orchestrates correctors
│   │   ├── correctors/
│   │   │   ├── __init__.py
│   │   │   ├── color.py                   # Swap off-brand colors → nearest brand color
│   │   │   ├── font.py                    # Swap wrong fonts → brand font
│   │   │   ├── contrast.py                # Adjust colors to meet WCAG AA
│   │   │   ├── font_size.py               # Bump font sizes to meet minimums
│   │   │   └── alignment.py               # Snap elements to grid/margins
│   │   ├── exporter.py                    # Corrected CSM → .pptx file via python-pptx
│   │   └── tests/
│   │       ├── test_color_corrector.py
│   │       ├── test_font_corrector.py
│   │       ├── test_contrast_corrector.py
│   │       └── test_exporter.py
│   ├── storage/
│   │   ├── __init__.py
│   │   └── r2.py                          # Upload/download/signed URL helpers for Cloudflare R2
│   └── workers/
│       ├── __init__.py
│       ├── main.py                        # BullMQ worker entry point
│       ├── ingestion_worker.py            # Parse PPTX → CSM → thumbnails → store
│       ├── check_worker.py                # Run rule engine + vision scorer → store results
│       └── correction_worker.py           # Generate corrections → store
├── apps/
│   └── web/
│       ├── package.json
│       ├── tsconfig.json
│       ├── tailwind.config.ts
│       ├── next.config.mjs
│       ├── src/
│       │   ├── app/
│       │   │   ├── layout.tsx             # Root layout with Clerk provider
│       │   │   ├── (auth)/
│       │   │   │   ├── sign-in/[[...sign-in]]/page.tsx
│       │   │   │   └── sign-up/[[...sign-up]]/page.tsx
│       │   │   └── (dashboard)/
│       │   │       ├── layout.tsx         # Dashboard shell — sidebar, header
│       │   │       ├── page.tsx           # Home — recent decks, org DQS
│       │   │       ├── decks/
│       │   │       │   ├── page.tsx       # Deck library
│       │   │       │   └── upload/page.tsx# Upload flow
│       │   │       ├── checks/
│       │   │       │   └── [id]/
│       │   │       │       ├── page.tsx   # Check results overview
│       │   │       │       └── slides/
│       │   │       │           └── [idx]/page.tsx  # Single slide detail + correction
│       │   │       ├── brand/
│       │   │       │   ├── page.tsx       # Brand rulesets list
│       │   │       │   └── [id]/page.tsx  # Ruleset editor
│       │   │       └── settings/
│       │   │           └── page.tsx
│       │   ├── components/
│       │   │   ├── ui/                    # shadcn/ui components
│       │   │   ├── slide-preview.tsx      # Konva.js canvas slide renderer
│       │   │   ├── issue-overlay.tsx      # Bounding box annotations on slide
│       │   │   ├── check-panel.tsx        # Issue list with severity badges
│       │   │   ├── correction-view.tsx    # Side-by-side original vs corrected
│       │   │   ├── brand-rule-editor.tsx  # Manual brand rule form
│       │   │   ├── deck-card.tsx          # Deck list item
│       │   │   ├── upload-dropzone.tsx    # File upload with drag-and-drop
│       │   │   └── dqs-badge.tsx          # Design Quality Score display
│       │   ├── lib/
│       │   │   ├── api.ts                 # Type-safe fetch wrapper
│       │   │   ├── stores/
│       │   │   │   ├── deck-store.ts      # Zustand: active deck state
│       │   │   │   └── check-store.ts     # Zustand: check results state
│       │   │   └── types.ts               # Shared TypeScript types (mirrors Python schemas)
│       │   └── middleware.ts              # Clerk auth middleware
│       └── public/
├── conftest.py                            # Root conftest — adds packages/ and services/ to sys.path
├── tests/
│   ├── __init__.py
│   ├── golden_decks/                      # underscore, not hyphen — valid Python package
│   │   ├── __init__.py
│   │   ├── generate_fixtures.py
│   │   ├── brand_violations.pptx
│   │   └── accessibility_fails.pptx
│   ├── integration/
│   │   ├── __init__.py
│   │   └── test_full_pipeline.py
│   └── e2e/
│       └── upload_check_correct.spec.ts
└── docs/
    ├── superpowers/
    │   └── plans/
    └── api/
```

---

## Task 1: Repository Scaffold + Docker Compose

**Files:**
- Create: `burnish/pyproject.toml`
- Create: `burnish/docker-compose.yml`
- Create: `burnish/.env.example`
- Create: `burnish/.gitignore`
- Create: `burnish/services/__init__.py`
- Create: `burnish/packages/__init__.py`

- [ ] **Step 1: Initialize git repo**

```bash
cd /Users/ekaterinablagireva/Documents/work/R\&D/Slides
git init
```

- [ ] **Step 2: Create pyproject.toml**

```toml
[project]
name = "burnish"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
    "fastapi>=0.111",
    "uvicorn[standard]>=0.30",
    "pydantic>=2.0",
    "sqlalchemy[asyncio]>=2.0",
    "asyncpg>=0.29",
    "alembic>=1.13",
    "python-pptx>=1.0",
    "pillow>=10.0",
    "httpx>=0.27",
    "python-multipart>=0.0.9",
    "boto3>=1.34",
    "redis>=5.0",
    "bullmq>=1.0",
    "openai>=1.30",
    "anthropic>=0.25",
    "colormath>=3.0",
    "pydantic-settings>=2.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "pytest-asyncio>=0.23",
    "pytest-cov>=5.0",
    "ruff>=0.4",
    "mypy>=1.10",
    "httpx",
]

[tool.ruff]
target-version = "py312"
line-length = 100

[tool.ruff.lint]
select = ["E", "F", "I", "N", "W", "UP"]

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["services", "packages", "tests"]

[tool.mypy]
python_version = "3.12"
strict = true
plugins = ["pydantic.mypy"]
```

- [ ] **Step 3: Create docker-compose.yml**

```yaml
services:
  postgres:
    image: pgvector/pgvector:pg16
    environment:
      POSTGRES_DB: burnish
      POSTGRES_USER: burnish
      POSTGRES_PASSWORD: burnish_dev
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U burnish"]
      interval: 5s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 5s
      retries: 5

volumes:
  pgdata:
```

- [ ] **Step 4: Create .env.example**

```bash
# Database
DATABASE_URL=postgresql+asyncpg://burnish:burnish_dev@localhost:5432/burnish

# Redis
REDIS_URL=redis://localhost:6379

# Auth
CLERK_SECRET_KEY=sk_test_...
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=pk_test_...

# AI
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...

# Storage (Cloudflare R2)
R2_ACCOUNT_ID=
R2_ACCESS_KEY_ID=
R2_SECRET_ACCESS_KEY=
R2_BUCKET_NAME=burnish-files
R2_ENDPOINT_URL=https://<account_id>.r2.cloudflarestorage.com
```

- [ ] **Step 5: Create .gitignore**

```gitignore
__pycache__/
*.py[cod]
*.egg-info/
dist/
.venv/
.env
*.db
node_modules/
.next/
.turbo/
```

- [ ] **Step 6: Create package __init__.py stubs and conftest**

Create empty `services/__init__.py` and `packages/__init__.py`.

Create root `conftest.py` so imports work without `pip install -e .`:

```python
# conftest.py
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
```

Create `tests/__init__.py` and `tests/golden_decks/__init__.py` (empty).

- [ ] **Step 7: Install Python dependencies**

```bash
pip install -e ".[dev]"
```

This installs all project dependencies (fastapi, sqlalchemy, python-pptx, etc.) in editable mode. Every subsequent task depends on this.

- [ ] **Step 8: Start Docker services and verify**

```bash
docker compose up -d
docker compose ps  # Expected: postgres and redis both healthy
```

- [ ] **Step 9: Commit**

```bash
git add pyproject.toml docker-compose.yml .env.example .gitignore conftest.py services/__init__.py packages/__init__.py tests/__init__.py tests/golden_decks/__init__.py
git commit -m "feat: repo scaffold with docker-compose (postgres + redis)"
```

---

## Task 2: CSM (Canonical Slide Model) Types

**Files:**
- Create: `packages/csm/__init__.py`
- Create: `packages/csm/models.py`
- Create: `packages/csm/test_models.py`

- [ ] **Step 1: Write the failing test**

```python
# packages/csm/test_models.py
import json
from uuid import uuid4

from packages.csm.models import (
    BoundingBox,
    CSM,
    Color,
    Font,
    ImageElement,
    Paragraph,
    ShapeElement,
    Slide,
    SlideBackground,
    TableCell,
    TableElement,
    TextElement,
    TextRun,
)


def test_color_from_hex():
    c = Color(hex="#1A2B4C", r=26, g=43, b=76)
    assert c.hex == "#1A2B4C"
    assert c.a == 1.0


def test_text_element_roundtrip():
    el = TextElement(
        id="shape_1",
        bbox=BoundingBox(x=100, y=50, width=400, height=60),
        paragraphs=[
            Paragraph(
                runs=[
                    TextRun(
                        text="Hello World",
                        font=Font(family="Inter", weight=700, size_pt=24),
                        color=Color(hex="#000000", r=0, g=0, b=0),
                    )
                ],
                alignment="left",
                line_spacing=1.15,
            )
        ],
    )
    data = el.model_dump()
    restored = TextElement(**data)
    assert restored.paragraphs[0].runs[0].text == "Hello World"
    assert restored.type == "text"


def test_csm_serialization():
    csm = CSM(
        id=uuid4(),
        deck_id=uuid4(),
        source_type="pptx",
        total_slides=1,
        slides=[
            Slide(
                index=0,
                id="slide_1",
                width_pt=720,
                height_pt=540,
                background=SlideBackground(
                    type="color", color=Color(hex="#FFFFFF", r=255, g=255, b=255)
                ),
                elements=[],
            )
        ],
        master_fonts=[],
        master_colors=[],
        metadata={"title": "Test Deck"},
        created_at="2026-03-24T00:00:00Z",
    )
    json_str = csm.model_dump_json()
    restored = CSM.model_validate_json(json_str)
    assert restored.total_slides == 1
    assert restored.slides[0].width_pt == 720


def test_slide_element_discriminator():
    """TextElement, ImageElement, ShapeElement, TableElement all serialize with 'type' field."""
    text = TextElement(
        id="t1",
        bbox=BoundingBox(x=0, y=0, width=100, height=50),
        paragraphs=[],
    )
    img = ImageElement(
        id="i1",
        bbox=BoundingBox(x=0, y=0, width=100, height=100),
        ref="images/logo.png",
        aspect_ratio=1.0,
    )
    shape = ShapeElement(
        id="s1",
        bbox=BoundingBox(x=0, y=0, width=50, height=50),
        shape_type="rectangle",
    )
    table = TableElement(
        id="tb1",
        bbox=BoundingBox(x=0, y=0, width=300, height=200),
        rows=2,
        cols=2,
        cells=[
            TableCell(
                row=0,
                col=0,
                paragraphs=[],
            )
        ],
    )
    assert text.type == "text"
    assert img.type == "image"
    assert shape.type == "shape"
    assert table.type == "table"
```

- [ ] **Step 2: Run test to verify it fails**

```bash
python -m pytest packages/csm/test_models.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'packages.csm.models'`

- [ ] **Step 3: Write the CSM models**

```python
# packages/csm/__init__.py
```

```python
# packages/csm/models.py
from __future__ import annotations

from typing import Literal, Union
from uuid import UUID

from pydantic import BaseModel, Field


class Color(BaseModel):
    hex: str
    r: int
    g: int
    b: int
    a: float = 1.0


class BoundingBox(BaseModel):
    x: float
    y: float
    width: float
    height: float


class Font(BaseModel):
    family: str
    weight: int = 400
    size_pt: float = 12.0
    italic: bool = False
    underline: bool = False
    strikethrough: bool = False


class TextRun(BaseModel):
    text: str
    font: Font
    color: Color
    link_url: str | None = None


class Paragraph(BaseModel):
    runs: list[TextRun]
    alignment: Literal["left", "center", "right", "justify"] = "left"
    line_spacing: float = 1.0
    space_before_pt: float = 0
    space_after_pt: float = 0
    indent_level: int = 0


class TextElement(BaseModel):
    type: Literal["text"] = "text"
    id: str
    bbox: BoundingBox
    paragraphs: list[Paragraph]
    text_overflow: bool = False
    is_placeholder: bool = False
    placeholder_type: str | None = None


class ImageElement(BaseModel):
    type: Literal["image"] = "image"
    id: str
    bbox: BoundingBox
    ref: str
    dpi: float | None = None
    aspect_ratio: float
    has_alt_text: bool = False
    alt_text: str | None = None
    is_stretched: bool = False


class ShapeElement(BaseModel):
    type: Literal["shape"] = "shape"
    id: str
    bbox: BoundingBox
    shape_type: str
    fill_color: Color | None = None
    stroke_color: Color | None = None
    stroke_width_pt: float = 0


class TableCell(BaseModel):
    row: int
    col: int
    row_span: int = 1
    col_span: int = 1
    paragraphs: list[Paragraph] = Field(default_factory=list)
    background_color: Color | None = None


class TableElement(BaseModel):
    type: Literal["table"] = "table"
    id: str
    bbox: BoundingBox
    rows: int
    cols: int
    cells: list[TableCell]


SlideElement = Union[TextElement, ImageElement, ShapeElement, TableElement]


class SlideBackground(BaseModel):
    type: Literal["color", "image", "gradient"]
    color: Color | None = None
    image_ref: str | None = None
    gradient: dict | None = None


class Slide(BaseModel):
    index: int
    id: str
    width_pt: float
    height_pt: float
    background: SlideBackground
    elements: list[SlideElement] = Field(default_factory=list)
    speaker_notes: str = ""
    layout_name: str | None = None
    thumbnail_ref: str | None = None


class CSM(BaseModel):
    id: UUID
    deck_id: UUID
    source_type: str
    total_slides: int
    slides: list[Slide]
    master_fonts: list[Font] = Field(default_factory=list)
    master_colors: list[Color] = Field(default_factory=list)
    metadata: dict = Field(default_factory=dict)
    created_at: str
```

- [ ] **Step 4: Run test to verify it passes**

```bash
python -m pytest packages/csm/test_models.py -v
```

Expected: 4 passed

- [ ] **Step 5: Commit**

```bash
git add packages/
git commit -m "feat: canonical slide model (CSM) pydantic types with tests"
```

---

## Task 3: Database Models + Alembic Setup

**Files:**
- Create: `services/db/__init__.py`
- Create: `services/db/engine.py`
- Create: `services/db/models/__init__.py`
- Create: `services/db/models/base.py`
- Create: `services/db/models/org.py`
- Create: `services/db/models/brand.py`
- Create: `services/db/models/deck.py`
- Create: `services/db/models/check.py`
- Create: `alembic.ini`
- Create: `alembic/env.py`

- [ ] **Step 1: Create database engine module**

```python
# services/db/__init__.py
```

```python
# services/db/engine.py
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from pydantic_settings import BaseSettings


class DBSettings(BaseSettings):
    database_url: str = "postgresql+asyncpg://burnish:burnish_dev@localhost:5432/burnish"


settings = DBSettings()
engine = create_async_engine(settings.database_url, echo=False)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_session():
    async with async_session() as session:
        yield session
```

- [ ] **Step 2: Create base model with common mixins**

```python
# services/db/models/__init__.py
from services.db.models.base import Base
from services.db.models.org import Organization, User
from services.db.models.brand import BrandRuleset
from services.db.models.deck import Deck
from services.db.models.check import CheckRun, SlideCheckResult, Issue

__all__ = [
    "Base",
    "Organization",
    "User",
    "BrandRuleset",
    "Deck",
    "CheckRun",
    "SlideCheckResult",
    "Issue",
]
```

```python
# services/db/models/base.py
import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )


class UUIDMixin:
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
```

- [ ] **Step 3: Create Organization and User models**

```python
# services/db/models/org.py
import enum
import uuid

from sqlalchemy import Enum, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from services.db.models.base import Base, TimestampMixin, UUIDMixin


class PlanType(str, enum.Enum):
    free = "free"
    pro = "pro"
    business = "business"
    enterprise = "enterprise"


class OrgRole(str, enum.Enum):
    owner = "owner"
    admin = "admin"
    editor = "editor"
    viewer = "viewer"


class Organization(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "organizations"

    name: Mapped[str] = mapped_column(String(255))
    slug: Mapped[str] = mapped_column(String(100), unique=True)
    plan: Mapped[PlanType] = mapped_column(Enum(PlanType), default=PlanType.free)
    settings: Mapped[dict] = mapped_column(JSONB, default=dict)

    users: Mapped[list["User"]] = relationship(back_populates="organization")


class User(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "users"

    org_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("organizations.id"))
    clerk_id: Mapped[str] = mapped_column(String(255), unique=True)
    email: Mapped[str] = mapped_column(String(255))
    role: Mapped[OrgRole] = mapped_column(Enum(OrgRole), default=OrgRole.editor)

    organization: Mapped["Organization"] = relationship(back_populates="users")
```

- [ ] **Step 4: Create Brand, Deck, and Check models**

```python
# services/db/models/brand.py
import uuid

from sqlalchemy import Boolean, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from services.db.models.base import Base, TimestampMixin, UUIDMixin


class BrandRuleset(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "brand_rulesets"

    org_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("organizations.id"))
    name: Mapped[str] = mapped_column(String(255))
    version: Mapped[int] = mapped_column(Integer, default=1)
    is_active: Mapped[bool] = mapped_column(Boolean, default=False)
    rules: Mapped[dict] = mapped_column(JSONB, default=dict)
```

```python
# services/db/models/deck.py
import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from services.db.models.base import Base, TimestampMixin, UUIDMixin


class SourceType(str, enum.Enum):
    pptx = "pptx"
    gslides = "gslides"
    figma = "figma"
    pdf = "pdf"
    keynote = "keynote"


class Deck(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "decks"

    org_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("organizations.id"))
    uploaded_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    name: Mapped[str] = mapped_column(String(255))
    source_type: Mapped[SourceType] = mapped_column(Enum(SourceType))
    source_ref: Mapped[str] = mapped_column(String(1024))
    slide_count: Mapped[int] = mapped_column(Integer, default=0)
    version_number: Mapped[int] = mapped_column(Integer, default=1)
    parent_deck_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("decks.id"), nullable=True
    )
    csm_ref: Mapped[str] = mapped_column(String(1024), default="")
```

```python
# services/db/models/check.py
import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, Float, ForeignKey, Integer, String, Boolean
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from services.db.models.base import Base, TimestampMixin, UUIDMixin


class CheckStatus(str, enum.Enum):
    queued = "queued"
    running = "running"
    complete = "complete"
    failed = "failed"


class TriggerType(str, enum.Enum):
    manual = "manual"
    upload = "upload"
    cicd = "cicd"
    schedule = "schedule"
    api = "api"


class Severity(str, enum.Enum):
    error = "error"
    warning = "warning"
    info = "info"


class CorrectionStatus(str, enum.Enum):
    pending = "pending"
    accepted = "accepted"
    rejected = "rejected"
    edited = "edited"


class CheckRun(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "check_runs"

    deck_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("decks.id"))
    ruleset_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("brand_rulesets.id")
    )
    org_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("organizations.id"))
    triggered_by: Mapped[TriggerType] = mapped_column(Enum(TriggerType), default=TriggerType.manual)
    status: Mapped[CheckStatus] = mapped_column(Enum(CheckStatus), default=CheckStatus.queued)
    dqs_overall: Mapped[float | None] = mapped_column(Float, nullable=True)
    issue_count_error: Mapped[int] = mapped_column(Integer, default=0)
    issue_count_warning: Mapped[int] = mapped_column(Integer, default=0)
    issue_count_info: Mapped[int] = mapped_column(Integer, default=0)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    slide_results: Mapped[list["SlideCheckResult"]] = relationship(back_populates="check_run")


class SlideCheckResult(Base, UUIDMixin):
    __tablename__ = "slide_check_results"

    check_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("check_runs.id")
    )
    slide_index: Mapped[int] = mapped_column(Integer)
    dqs_slide: Mapped[float] = mapped_column(Float, default=0.0)
    vision_scores: Mapped[dict] = mapped_column(JSONB, default=dict)
    thumbnail_ref: Mapped[str] = mapped_column(String(1024), default="")
    corrected_thumbnail_ref: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    corrected_csm_ref: Mapped[str | None] = mapped_column(String(1024), nullable=True)

    check_run: Mapped["CheckRun"] = relationship(back_populates="slide_results")
    issues: Mapped[list["Issue"]] = relationship(back_populates="slide_result")


class Issue(Base, UUIDMixin):
    __tablename__ = "issues"

    slide_result_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("slide_check_results.id")
    )
    rule_type: Mapped[str] = mapped_column(String(100))
    severity: Mapped[Severity] = mapped_column(Enum(Severity))
    message: Mapped[str] = mapped_column(String(1024))
    element_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    element_bbox: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    original_value: Mapped[str | None] = mapped_column(String(500), nullable=True)
    expected_value: Mapped[str | None] = mapped_column(String(500), nullable=True)
    correction_applied: Mapped[bool] = mapped_column(Boolean, default=False)
    correction_status: Mapped[CorrectionStatus | None] = mapped_column(
        Enum(CorrectionStatus), nullable=True
    )

    slide_result: Mapped["SlideCheckResult"] = relationship(back_populates="issues")
```

- [ ] **Step 5: Set up Alembic**

```bash
pip install alembic
alembic init alembic
```

Then edit `alembic/env.py`:

```python
# alembic/env.py
import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import create_async_engine

from services.db.engine import settings
from services.db.models import Base

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = settings.database_url
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection):
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    connectable = create_async_engine(settings.database_url, poolclass=pool.NullPool)
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
```

Update `alembic.ini` to remove the default `sqlalchemy.url` line (we use settings).

- [ ] **Step 6: Generate and run initial migration**

```bash
alembic revision --autogenerate -m "initial schema"
alembic upgrade head
```

- [ ] **Step 7: Verify tables exist**

```bash
docker compose exec postgres psql -U burnish -d burnish -c "\dt"
```

Expected: Tables `organizations`, `users`, `brand_rulesets`, `decks`, `check_runs`, `slide_check_results`, `issues`

- [ ] **Step 8: Commit**

```bash
git add services/db/ alembic/ alembic.ini
git commit -m "feat: database models and alembic migrations for all core entities"
```

---

## Task 4: Cloudflare R2 Storage Client

**Files:**
- Create: `services/storage/__init__.py`
- Create: `services/storage/r2.py`
- Test: `services/storage/test_r2.py`

- [ ] **Step 1: Write the failing test**

```python
# services/storage/test_r2.py
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from services.storage.r2 import R2Client


@pytest.fixture
def r2_client():
    with patch("services.storage.r2.boto3") as mock_boto3:
        mock_s3 = MagicMock()
        mock_boto3.client.return_value = mock_s3
        client = R2Client(
            account_id="test",
            access_key_id="test_key",
            secret_access_key="test_secret",
            bucket_name="test-bucket",
        )
        yield client, mock_s3


def test_upload_file(r2_client):
    client, mock_s3 = r2_client
    client.upload_file(b"file content", "decks/test.pptx", "application/vnd.openxmlformats-officedocument.presentationml.presentation")
    mock_s3.put_object.assert_called_once()
    call_kwargs = mock_s3.put_object.call_args.kwargs
    assert call_kwargs["Key"] == "decks/test.pptx"
    assert call_kwargs["Bucket"] == "test-bucket"


def test_download_file(r2_client):
    client, mock_s3 = r2_client
    mock_s3.get_object.return_value = {"Body": MagicMock(read=MagicMock(return_value=b"content"))}
    result = client.download_file("decks/test.pptx")
    assert result == b"content"


def test_generate_signed_url(r2_client):
    client, mock_s3 = r2_client
    mock_s3.generate_presigned_url.return_value = "https://signed.url/test"
    url = client.get_signed_url("decks/test.pptx")
    assert "signed.url" in url
```

- [ ] **Step 2: Run test to verify it fails**

```bash
python -m pytest services/storage/test_r2.py -v
```

Expected: FAIL — module not found

- [ ] **Step 3: Implement R2 client**

```python
# services/storage/__init__.py
```

```python
# services/storage/r2.py
import boto3
from pydantic_settings import BaseSettings


class R2Settings(BaseSettings):
    r2_account_id: str = ""
    r2_access_key_id: str = ""
    r2_secret_access_key: str = ""
    r2_bucket_name: str = "burnish-files"
    r2_endpoint_url: str = ""


class R2Client:
    def __init__(
        self,
        account_id: str = "",
        access_key_id: str = "",
        secret_access_key: str = "",
        bucket_name: str = "burnish-files",
    ):
        endpoint = f"https://{account_id}.r2.cloudflarestorage.com" if account_id else ""
        self.bucket_name = bucket_name
        self.s3 = boto3.client(
            "s3",
            endpoint_url=endpoint or None,
            aws_access_key_id=access_key_id,
            aws_secret_access_key=secret_access_key,
            region_name="auto",
        )

    def upload_file(self, data: bytes, key: str, content_type: str = "application/octet-stream") -> str:
        self.s3.put_object(
            Bucket=self.bucket_name,
            Key=key,
            Body=data,
            ContentType=content_type,
        )
        return key

    def download_file(self, key: str) -> bytes:
        response = self.s3.get_object(Bucket=self.bucket_name, Key=key)
        return response["Body"].read()

    def get_signed_url(self, key: str, expires_in: int = 900) -> str:
        return self.s3.generate_presigned_url(
            "get_object",
            Params={"Bucket": self.bucket_name, "Key": key},
            ExpiresIn=expires_in,
        )

    def delete_file(self, key: str) -> None:
        self.s3.delete_object(Bucket=self.bucket_name, Key=key)
```

- [ ] **Step 4: Run test to verify it passes**

```bash
python -m pytest services/storage/test_r2.py -v
```

Expected: 3 passed

- [ ] **Step 5: Commit**

```bash
git add services/storage/
git commit -m "feat: cloudflare R2 storage client with upload, download, signed URLs"
```

---

## Task 5: PPTX Parser → CSM

**Files:**
- Create: `services/ingestion/__init__.py`
- Create: `services/ingestion/pptx_parser.py`
- Create: `services/ingestion/test_pptx_parser.py`
- Create: `tests/golden_decks/` (test fixtures)

- [ ] **Step 1: Create a test fixture PPTX programmatically and write the failing test**

```python
# services/ingestion/test_pptx_parser.py
import io
from uuid import uuid4

import pytest
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor

from services.ingestion.pptx_parser import PptxParser


def _make_test_pptx() -> bytes:
    """Create a minimal PPTX with known content for testing."""
    prs = Presentation()
    slide_layout = prs.slide_layouts[0]  # Title Slide
    slide = prs.slides.add_slide(slide_layout)

    # Add a text box
    from pptx.util import Emu
    txBox = slide.shapes.add_textbox(Inches(1), Inches(1), Inches(4), Inches(1))
    tf = txBox.text_frame
    p = tf.paragraphs[0]
    run = p.add_run()
    run.text = "Hello Burnish"
    run.font.name = "Arial"
    run.font.size = Pt(24)
    run.font.bold = True
    run.font.color.rgb = RGBColor(0x1A, 0x2B, 0x4C)

    buf = io.BytesIO()
    prs.save(buf)
    return buf.getvalue()


def test_parse_pptx_returns_csm():
    parser = PptxParser()
    pptx_bytes = _make_test_pptx()
    deck_id = uuid4()
    csm = parser.parse(pptx_bytes, deck_id)

    assert csm.source_type == "pptx"
    assert csm.deck_id == deck_id
    assert csm.total_slides >= 1


def test_parse_pptx_extracts_text():
    parser = PptxParser()
    pptx_bytes = _make_test_pptx()
    csm = parser.parse(pptx_bytes, uuid4())

    # Find a text element with "Hello Burnish"
    found = False
    for slide in csm.slides:
        for el in slide.elements:
            if el.type == "text":
                for para in el.paragraphs:
                    for run in para.runs:
                        if "Hello Burnish" in run.text:
                            found = True
                            assert run.font.family == "Arial"
                            assert run.font.weight == 700  # bold
                            assert run.font.size_pt == 24.0
                            assert run.color.hex.upper() == "#1A2B4C"
    assert found, "Could not find 'Hello Burnish' text in parsed CSM"


def test_parse_pptx_slide_dimensions():
    parser = PptxParser()
    pptx_bytes = _make_test_pptx()
    csm = parser.parse(pptx_bytes, uuid4())
    slide = csm.slides[0]
    assert slide.width_pt > 0
    assert slide.height_pt > 0
```

- [ ] **Step 2: Run test to verify it fails**

```bash
python -m pytest services/ingestion/test_pptx_parser.py -v
```

Expected: FAIL — module not found

- [ ] **Step 3: Implement PptxParser**

```python
# services/ingestion/__init__.py
```

```python
# services/ingestion/pptx_parser.py
from __future__ import annotations

import io
from uuid import UUID, uuid4

from pptx import Presentation
from pptx.enum.shapes import MSO_SHAPE_TYPE
from pptx.util import Emu

from packages.csm.models import (
    BoundingBox,
    CSM,
    Color,
    Font,
    ImageElement,
    Paragraph,
    ShapeElement,
    Slide,
    SlideBackground,
    TableCell,
    TableElement,
    TextElement,
    TextRun,
)


def _emu_to_pt(emu: int | Emu | None) -> float:
    """Convert EMU (English Metric Units) to points. 1 pt = 12700 EMU."""
    if emu is None:
        return 0.0
    return int(emu) / 12700


def _rgb_to_color(rgb) -> Color:
    """Convert python-pptx RGBColor to our Color model."""
    if rgb is None:
        return Color(hex="#000000", r=0, g=0, b=0)
    r, g, b = rgb[0], rgb[1], rgb[2]
    return Color(hex=f"#{r:02X}{g:02X}{b:02X}", r=r, g=g, b=b)


def _alignment_str(alignment) -> str:
    from pptx.enum.text import PP_ALIGN

    mapping = {
        PP_ALIGN.LEFT: "left",
        PP_ALIGN.CENTER: "center",
        PP_ALIGN.RIGHT: "right",
        PP_ALIGN.JUSTIFY: "justify",
    }
    return mapping.get(alignment, "left")


class PptxParser:
    def parse(self, pptx_data: bytes, deck_id: UUID) -> CSM:
        prs = Presentation(io.BytesIO(pptx_data))
        slides = []

        for idx, slide in enumerate(prs.slides):
            elements = []
            for shape in slide.shapes:
                if shape.has_text_frame:
                    elements.append(self._parse_text(shape))
                elif shape.shape_type == MSO_SHAPE_TYPE.PICTURE:
                    elements.append(self._parse_image(shape))
                elif shape.has_table:
                    elements.append(self._parse_table(shape))
                else:
                    elements.append(self._parse_shape(shape))

            slide_id = str(slide.slide_id) if hasattr(slide, 'slide_id') else str(idx)
            slides.append(
                Slide(
                    index=idx,
                    id=slide_id,
                    width_pt=_emu_to_pt(prs.slide_width),
                    height_pt=_emu_to_pt(prs.slide_height),
                    background=self._parse_background(slide),
                    elements=elements,
                    speaker_notes=self._extract_notes(slide),
                    layout_name=slide.slide_layout.name if slide.slide_layout else None,
                )
            )

        return CSM(
            id=uuid4(),
            deck_id=deck_id,
            source_type="pptx",
            total_slides=len(slides),
            slides=slides,
            master_fonts=self._extract_master_fonts(prs),
            master_colors=self._extract_theme_colors(prs),
            metadata=self._extract_metadata(prs),
            created_at="",
        )

    def _parse_text(self, shape) -> TextElement:
        paragraphs = []
        for para in shape.text_frame.paragraphs:
            runs = []
            for run in para.runs:
                font = run.font
                rgb = None
                if font.color and font.color.type is not None:
                    try:
                        rgb = font.color.rgb
                    except (AttributeError, TypeError):
                        pass
                color = _rgb_to_color(rgb)

                size_pt = font.size.pt if font.size else 12.0
                runs.append(
                    TextRun(
                        text=run.text,
                        font=Font(
                            family=font.name or "Unknown",
                            weight=700 if font.bold else 400,
                            size_pt=size_pt,
                            italic=bool(font.italic),
                            underline=bool(font.underline),
                        ),
                        color=color,
                    )
                )
            if runs:
                paragraphs.append(
                    Paragraph(
                        runs=runs,
                        alignment=_alignment_str(para.alignment),
                        line_spacing=para.line_spacing if para.line_spacing else 1.0,
                    )
                )

        return TextElement(
            id=str(shape.shape_id),
            bbox=BoundingBox(
                x=_emu_to_pt(shape.left),
                y=_emu_to_pt(shape.top),
                width=_emu_to_pt(shape.width),
                height=_emu_to_pt(shape.height),
            ),
            paragraphs=paragraphs,
            is_placeholder=shape.is_placeholder,
            placeholder_type=(
                str(shape.placeholder_format.type) if shape.is_placeholder else None
            ),
        )

    def _parse_image(self, shape) -> ImageElement:
        w = _emu_to_pt(shape.width)
        h = _emu_to_pt(shape.height)
        aspect = w / h if h > 0 else 1.0
        return ImageElement(
            id=str(shape.shape_id),
            bbox=BoundingBox(
                x=_emu_to_pt(shape.left),
                y=_emu_to_pt(shape.top),
                width=w,
                height=h,
            ),
            ref="",  # populated during ingestion worker (extract + upload to R2)
            aspect_ratio=aspect,
        )

    def _parse_table(self, shape) -> TableElement:
        table = shape.table
        cells = []
        for row_idx, row in enumerate(table.rows):
            for col_idx, cell in enumerate(row.cells):
                paras = []
                for para in cell.text_frame.paragraphs:
                    runs = []
                    for run in para.runs:
                        runs.append(
                            TextRun(
                                text=run.text,
                                font=Font(family=run.font.name or "Unknown", size_pt=12.0),
                                color=Color(hex="#000000", r=0, g=0, b=0),
                            )
                        )
                    if runs:
                        paras.append(Paragraph(runs=runs, alignment="left", line_spacing=1.0))
                cells.append(
                    TableCell(row=row_idx, col=col_idx, paragraphs=paras)
                )
        return TableElement(
            id=str(shape.shape_id),
            bbox=BoundingBox(
                x=_emu_to_pt(shape.left),
                y=_emu_to_pt(shape.top),
                width=_emu_to_pt(shape.width),
                height=_emu_to_pt(shape.height),
            ),
            rows=len(table.rows),
            cols=len(table.columns),
            cells=cells,
        )

    def _parse_shape(self, shape) -> ShapeElement:
        fill_color = None
        if hasattr(shape, "fill") and shape.fill.type is not None:
            try:
                fc = shape.fill.fore_color.rgb
                fill_color = _rgb_to_color(fc)
            except (AttributeError, TypeError):
                pass
        return ShapeElement(
            id=str(shape.shape_id),
            bbox=BoundingBox(
                x=_emu_to_pt(shape.left),
                y=_emu_to_pt(shape.top),
                width=_emu_to_pt(shape.width),
                height=_emu_to_pt(shape.height),
            ),
            shape_type=str(shape.shape_type) if shape.shape_type else "freeform",
        )

    def _parse_background(self, slide) -> SlideBackground:
        return SlideBackground(
            type="color",
            color=Color(hex="#FFFFFF", r=255, g=255, b=255),
        )

    def _extract_notes(self, slide) -> str:
        if slide.has_notes_slide:
            return slide.notes_slide.notes_text_frame.text
        return ""

    def _extract_master_fonts(self, prs) -> list:
        return []

    def _extract_theme_colors(self, prs) -> list:
        return []

    def _extract_metadata(self, prs) -> dict:
        cp = prs.core_properties
        return {
            "title": cp.title or "",
            "author": cp.author or "",
            "subject": cp.subject or "",
        }
```

- [ ] **Step 4: Run test to verify it passes**

```bash
python -m pytest services/ingestion/test_pptx_parser.py -v
```

Expected: 3 passed

- [ ] **Step 5: Commit**

```bash
git add services/ingestion/
git commit -m "feat: PPTX parser — python-pptx to Canonical Slide Model"
```

---

## Task 6: Rule Engine — Issue Models + Engine Skeleton

**Files:**
- Create: `services/rules/__init__.py`
- Create: `services/rules/models.py`
- Create: `services/rules/engine.py`
- Create: `services/rules/evaluators/__init__.py`

- [ ] **Step 1: Write the failing test**

```python
# services/rules/test_engine.py
from uuid import uuid4

from packages.csm.models import (
    BoundingBox,
    Color,
    Font,
    Paragraph,
    Slide,
    SlideBackground,
    TextElement,
    TextRun,
)
from services.rules.engine import RuleEngine
from services.rules.models import BrandRulesetConfig, ColorRuleConfig


def _make_slide_with_color(hex_color: str) -> Slide:
    r = int(hex_color[1:3], 16)
    g = int(hex_color[3:5], 16)
    b = int(hex_color[5:7], 16)
    return Slide(
        index=0,
        id="slide_0",
        width_pt=720,
        height_pt=540,
        background=SlideBackground(type="color", color=Color(hex="#FFFFFF", r=255, g=255, b=255)),
        elements=[
            TextElement(
                id="shape_1",
                bbox=BoundingBox(x=100, y=50, width=400, height=60),
                paragraphs=[
                    Paragraph(
                        runs=[
                            TextRun(
                                text="Test",
                                font=Font(family="Arial", weight=400, size_pt=16),
                                color=Color(hex=hex_color, r=r, g=g, b=b),
                            )
                        ],
                        alignment="left",
                        line_spacing=1.0,
                    )
                ],
            )
        ],
    )


def test_engine_returns_issues_for_off_brand_color():
    ruleset = BrandRulesetConfig(
        colors=[
            ColorRuleConfig(name="Primary Blue", hex="#1A2B4C", tolerance_delta_e=5.0),
        ],
        fonts=[],
        layout={},
        accessibility={},
    )
    engine = RuleEngine(ruleset)
    slide = _make_slide_with_color("#FF0000")  # clearly off-brand
    results = engine.evaluate_slide(slide)
    color_issues = [i for i in results if i.rule_type == "color.off_brand"]
    assert len(color_issues) >= 1
    assert color_issues[0].severity == "error"


def test_engine_passes_near_match():
    ruleset = BrandRulesetConfig(
        colors=[
            ColorRuleConfig(name="Primary Blue", hex="#1A2B4C", tolerance_delta_e=5.0),
        ],
        fonts=[],
        layout={},
        accessibility={},
    )
    engine = RuleEngine(ruleset)
    slide = _make_slide_with_color("#1A2B4D")  # very close
    results = engine.evaluate_slide(slide)
    color_issues = [i for i in results if i.rule_type == "color.off_brand"]
    assert len(color_issues) == 0
```

- [ ] **Step 2: Run test to verify it fails**

```bash
python -m pytest services/rules/test_engine.py -v
```

Expected: FAIL — module not found

- [ ] **Step 3: Implement rule models, engine, and color evaluator**

```python
# services/rules/__init__.py
```

```python
# services/rules/models.py
from __future__ import annotations

from pydantic import BaseModel


class ColorRuleConfig(BaseModel):
    name: str
    hex: str
    tolerance_delta_e: float = 5.0
    usage_context: str | None = None


class FontRuleConfig(BaseModel):
    family: str
    context: str | None = None  # "heading", "body", "caption"
    min_size_pt: float | None = None
    max_size_pt: float | None = None


class LayoutConfig(BaseModel):
    margin_min_pt: float = 36.0  # 0.5 inch default
    max_elements_per_slide: int = 15


class AccessibilityConfig(BaseModel):
    min_contrast_ratio: float = 4.5  # WCAG AA
    min_font_size_pt: float = 10.0
    require_alt_text: bool = True


class BrandRulesetConfig(BaseModel):
    colors: list[ColorRuleConfig] = []
    fonts: list[FontRuleConfig] = []
    layout: LayoutConfig | dict = LayoutConfig()
    accessibility: AccessibilityConfig | dict = AccessibilityConfig()


class IssueResult(BaseModel):
    rule_type: str
    severity: str  # "error", "warning", "info"
    message: str
    element_id: str | None = None
    element_bbox: dict | None = None
    original_value: str | None = None
    expected_value: str | None = None
```

```python
# services/rules/evaluators/__init__.py
```

```python
# services/rules/evaluators/color.py
from __future__ import annotations

from packages.csm.models import Color, ImageElement, Slide, TextElement
from services.rules.models import BrandRulesetConfig, IssueResult


def _srgb_to_linear(c: float) -> float:
    return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4


def _rgb_to_lab(r: int, g: int, b: int) -> tuple[float, float, float]:
    """Convert sRGB to CIELAB (approximate)."""
    # sRGB → linear RGB
    rl = _srgb_to_linear(r / 255.0)
    gl = _srgb_to_linear(g / 255.0)
    bl = _srgb_to_linear(b / 255.0)

    # Linear RGB → XYZ (D65)
    x = 0.4124564 * rl + 0.3575761 * gl + 0.1804375 * bl
    y = 0.2126729 * rl + 0.7151522 * gl + 0.0721750 * bl
    z = 0.0193339 * rl + 0.1191920 * gl + 0.9503041 * bl

    # XYZ → Lab
    xn, yn, zn = 0.95047, 1.0, 1.08883
    x, y, z = x / xn, y / yn, z / zn

    def f(t: float) -> float:
        return t ** (1 / 3) if t > 0.008856 else (7.787 * t) + (16 / 116)

    l_star = 116 * f(y) - 16
    a_star = 500 * (f(x) - f(y))
    b_star = 200 * (f(y) - f(z))
    return l_star, a_star, b_star


def delta_e_simple(r1: int, g1: int, b1: int, r2: int, g2: int, b2: int) -> float:
    """Simple CIE76 Delta-E (good enough for our tolerance checks)."""
    l1, a1, b1_lab = _rgb_to_lab(r1, g1, b1)
    l2, a2, b2_lab = _rgb_to_lab(r2, g2, b2)
    return ((l1 - l2) ** 2 + (a1 - a2) ** 2 + (b1_lab - b2_lab) ** 2) ** 0.5


def _hex_to_rgb(hex_str: str) -> tuple[int, int, int]:
    h = hex_str.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


class ColorEvaluator:
    def __init__(self, ruleset: BrandRulesetConfig):
        self.palette = ruleset.colors

    def evaluate_slide(self, slide: Slide) -> list[IssueResult]:
        if not self.palette:
            return []
        issues = []
        for el in slide.elements:
            if el.type == "text":
                for para in el.paragraphs:
                    for run in para.runs:
                        c = run.color
                        if not self._is_brand_color(c):
                            nearest = self._nearest_brand_color(c)
                            issues.append(
                                IssueResult(
                                    rule_type="color.off_brand",
                                    severity="error",
                                    message=(
                                        f"Color {c.hex} is not in the brand palette. "
                                        f"Nearest: {nearest.hex}"
                                    ),
                                    element_id=el.id,
                                    element_bbox=el.bbox.model_dump() if el.bbox else None,
                                    original_value=c.hex,
                                    expected_value=nearest.hex,
                                )
                            )
        return issues

    def _is_brand_color(self, color: Color) -> bool:
        # Also allow black and white without penalty
        if color.hex.upper() in ("#000000", "#FFFFFF"):
            return True
        for rule in self.palette:
            tr, tg, tb = _hex_to_rgb(rule.hex)
            de = delta_e_simple(color.r, color.g, color.b, tr, tg, tb)
            if de <= rule.tolerance_delta_e:
                return True
        return False

    def _nearest_brand_color(self, color: Color) -> ColorRuleConfig:
        best = self.palette[0]
        best_de = float("inf")
        for rule in self.palette:
            tr, tg, tb = _hex_to_rgb(rule.hex)
            de = delta_e_simple(color.r, color.g, color.b, tr, tg, tb)
            if de < best_de:
                best_de = de
                best = rule
        return best
```

```python
# services/rules/engine.py
from __future__ import annotations

from packages.csm.models import Slide
from services.rules.evaluators.color import ColorEvaluator
from services.rules.models import BrandRulesetConfig, IssueResult


class RuleEngine:
    def __init__(self, ruleset: BrandRulesetConfig):
        self.ruleset = ruleset
        self.evaluators = [
            ColorEvaluator(ruleset),
            # TypographyEvaluator, LayoutEvaluator, etc. added in subsequent tasks
        ]

    def evaluate_slide(self, slide: Slide) -> list[IssueResult]:
        issues = []
        for evaluator in self.evaluators:
            issues.extend(evaluator.evaluate_slide(slide))
        return issues

    def evaluate_all(self, slides: list[Slide]) -> dict[int, list[IssueResult]]:
        results = {}
        for slide in slides:
            results[slide.index] = self.evaluate_slide(slide)
        return results
```

- [ ] **Step 4: Run test to verify it passes**

```bash
python -m pytest services/rules/test_engine.py -v
```

Expected: 2 passed

- [ ] **Step 5: Commit**

```bash
git add services/rules/
git commit -m "feat: rule engine with color evaluator (Delta-E palette compliance)"
```

---

## Task 7: Typography Evaluator

**Files:**
- Create: `services/rules/evaluators/typography.py`
- Create: `services/rules/tests/test_typography.py`

- [ ] **Step 1: Write the failing test**

```python
# services/rules/tests/__init__.py
```

```python
# services/rules/tests/test_typography.py
from packages.csm.models import (
    BoundingBox, Color, Font, Paragraph, Slide, SlideBackground, TextElement, TextRun,
)
from services.rules.evaluators.typography import TypographyEvaluator
from services.rules.models import BrandRulesetConfig, FontRuleConfig


def _slide_with_font(family: str, size_pt: float) -> Slide:
    return Slide(
        index=0, id="s0", width_pt=720, height_pt=540,
        background=SlideBackground(type="color", color=Color(hex="#FFFFFF", r=255, g=255, b=255)),
        elements=[
            TextElement(
                id="el1",
                bbox=BoundingBox(x=0, y=0, width=400, height=60),
                paragraphs=[
                    Paragraph(
                        runs=[TextRun(
                            text="Test",
                            font=Font(family=family, weight=400, size_pt=size_pt),
                            color=Color(hex="#000000", r=0, g=0, b=0),
                        )],
                        alignment="left", line_spacing=1.0,
                    )
                ],
            )
        ],
    )


def test_flags_wrong_font():
    ruleset = BrandRulesetConfig(
        fonts=[FontRuleConfig(family="Inter")],
    )
    evaluator = TypographyEvaluator(ruleset)
    issues = evaluator.evaluate_slide(_slide_with_font("Comic Sans MS", 16))
    assert any(i.rule_type == "typography.wrong_font" for i in issues)


def test_passes_correct_font():
    ruleset = BrandRulesetConfig(
        fonts=[FontRuleConfig(family="Inter")],
    )
    evaluator = TypographyEvaluator(ruleset)
    issues = evaluator.evaluate_slide(_slide_with_font("Inter", 16))
    assert not any(i.rule_type == "typography.wrong_font" for i in issues)


def test_flags_font_too_small():
    ruleset = BrandRulesetConfig(
        fonts=[FontRuleConfig(family="Inter", min_size_pt=12.0)],
        accessibility={"min_font_size_pt": 10.0, "min_contrast_ratio": 4.5, "require_alt_text": True},
    )
    evaluator = TypographyEvaluator(ruleset)
    issues = evaluator.evaluate_slide(_slide_with_font("Inter", 8))
    assert any(i.rule_type == "typography.size_too_small" for i in issues)
```

- [ ] **Step 2: Run test to verify it fails**

```bash
python -m pytest services/rules/tests/test_typography.py -v
```

Expected: FAIL

- [ ] **Step 3: Implement TypographyEvaluator**

```python
# services/rules/evaluators/typography.py
from __future__ import annotations

from packages.csm.models import Slide, TextElement
from services.rules.models import BrandRulesetConfig, IssueResult


class TypographyEvaluator:
    def __init__(self, ruleset: BrandRulesetConfig):
        self.allowed_fonts = [f.family.lower() for f in ruleset.fonts]
        self.font_rules = ruleset.fonts

    def evaluate_slide(self, slide: Slide) -> list[IssueResult]:
        if not self.font_rules:
            return []
        issues = []
        for el in slide.elements:
            if el.type == "text":
                for para in el.paragraphs:
                    for run in para.runs:
                        # Font family check
                        if self.allowed_fonts and run.font.family.lower() not in self.allowed_fonts:
                            issues.append(IssueResult(
                                rule_type="typography.wrong_font",
                                severity="error",
                                message=f"Font '{run.font.family}' is not in the brand font list. "
                                        f"Allowed: {', '.join(f.family for f in self.font_rules)}",
                                element_id=el.id,
                                original_value=run.font.family,
                                expected_value=self.font_rules[0].family,
                            ))
                        # Size check per rule
                        for rule in self.font_rules:
                            if rule.family.lower() == run.font.family.lower() and rule.min_size_pt:
                                if run.font.size_pt < rule.min_size_pt:
                                    issues.append(IssueResult(
                                        rule_type="typography.size_too_small",
                                        severity="warning",
                                        message=f"Font size {run.font.size_pt}pt is below minimum "
                                                f"{rule.min_size_pt}pt for {rule.family}",
                                        element_id=el.id,
                                        original_value=str(run.font.size_pt),
                                        expected_value=str(rule.min_size_pt),
                                    ))
        return issues
```

- [ ] **Step 4: Run test to verify it passes**

```bash
python -m pytest services/rules/tests/test_typography.py -v
```

Expected: 3 passed

- [ ] **Step 5: Register in engine**

Update `services/rules/engine.py`:

```python
from services.rules.evaluators.color import ColorEvaluator
from services.rules.evaluators.typography import TypographyEvaluator

class RuleEngine:
    def __init__(self, ruleset: BrandRulesetConfig):
        self.ruleset = ruleset
        self.evaluators = [
            ColorEvaluator(ruleset),
            TypographyEvaluator(ruleset),
        ]
    # ... rest unchanged
```

- [ ] **Step 6: Run all rule tests**

```bash
python -m pytest services/rules/ -v
```

Expected: All pass

- [ ] **Step 7: Commit**

```bash
git add services/rules/
git commit -m "feat: typography evaluator — font family and size checks"
```

---

## Task 8: Accessibility Evaluator (WCAG Contrast)

**Files:**
- Create: `services/rules/evaluators/accessibility.py`
- Create: `services/rules/tests/test_accessibility.py`

- [ ] **Step 1: Write the failing test**

```python
# services/rules/tests/test_accessibility.py
from packages.csm.models import (
    BoundingBox, Color, Font, Paragraph, Slide, SlideBackground, TextElement, TextRun,
)
from services.rules.evaluators.accessibility import AccessibilityEvaluator
from services.rules.models import AccessibilityConfig, BrandRulesetConfig


def _slide_with_text_color(fg_hex: str, bg_hex: str = "#FFFFFF") -> Slide:
    r, g, b = int(fg_hex[1:3], 16), int(fg_hex[3:5], 16), int(fg_hex[5:7], 16)
    br, bg_val, bb = int(bg_hex[1:3], 16), int(bg_hex[3:5], 16), int(bg_hex[5:7], 16)
    return Slide(
        index=0, id="s0", width_pt=720, height_pt=540,
        background=SlideBackground(type="color", color=Color(hex=bg_hex, r=br, g=bg_val, b=bb)),
        elements=[
            TextElement(
                id="el1",
                bbox=BoundingBox(x=0, y=0, width=400, height=60),
                paragraphs=[Paragraph(
                    runs=[TextRun(
                        text="Test",
                        font=Font(family="Inter", size_pt=16),
                        color=Color(hex=fg_hex, r=r, g=g, b=b),
                    )],
                    alignment="left", line_spacing=1.0,
                )],
            )
        ],
    )


def test_fails_low_contrast():
    """Light gray on white should fail WCAG AA."""
    ruleset = BrandRulesetConfig(
        accessibility=AccessibilityConfig(min_contrast_ratio=4.5),
    )
    evaluator = AccessibilityEvaluator(ruleset)
    issues = evaluator.evaluate_slide(_slide_with_text_color("#AAAAAA", "#FFFFFF"))
    assert any(i.rule_type == "a11y.low_contrast" for i in issues)


def test_passes_good_contrast():
    """Black on white should pass."""
    ruleset = BrandRulesetConfig(
        accessibility=AccessibilityConfig(min_contrast_ratio=4.5),
    )
    evaluator = AccessibilityEvaluator(ruleset)
    issues = evaluator.evaluate_slide(_slide_with_text_color("#000000", "#FFFFFF"))
    assert not any(i.rule_type == "a11y.low_contrast" for i in issues)
```

- [ ] **Step 2: Run test to verify it fails**

```bash
python -m pytest services/rules/tests/test_accessibility.py -v
```

- [ ] **Step 3: Implement AccessibilityEvaluator**

```python
# services/rules/evaluators/accessibility.py
from __future__ import annotations

from packages.csm.models import Color, Slide, TextElement
from services.rules.models import AccessibilityConfig, BrandRulesetConfig, IssueResult


def _relative_luminance(c: Color) -> float:
    vals = [c.r / 255.0, c.g / 255.0, c.b / 255.0]
    linear = [v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4 for v in vals]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]


def contrast_ratio(fg: Color, bg: Color) -> float:
    l1 = _relative_luminance(fg)
    l2 = _relative_luminance(bg)
    lighter, darker = max(l1, l2), min(l1, l2)
    return (lighter + 0.05) / (darker + 0.05)


class AccessibilityEvaluator:
    def __init__(self, ruleset: BrandRulesetConfig):
        if isinstance(ruleset.accessibility, dict):
            self.config = AccessibilityConfig(**ruleset.accessibility)
        else:
            self.config = ruleset.accessibility

    def evaluate_slide(self, slide: Slide) -> list[IssueResult]:
        issues = []
        bg_color = slide.background.color or Color(hex="#FFFFFF", r=255, g=255, b=255)

        for el in slide.elements:
            if el.type == "text":
                for para in el.paragraphs:
                    for run in para.runs:
                        ratio = contrast_ratio(run.color, bg_color)
                        if ratio < self.config.min_contrast_ratio:
                            issues.append(IssueResult(
                                rule_type="a11y.low_contrast",
                                severity="error",
                                message=(
                                    f"Contrast ratio {ratio:.1f}:1 fails WCAG AA "
                                    f"({self.config.min_contrast_ratio}:1 minimum)"
                                ),
                                element_id=el.id,
                                original_value=f"{ratio:.1f}",
                                expected_value=f">= {self.config.min_contrast_ratio}",
                            ))
        return issues
```

- [ ] **Step 4: Run test to verify it passes**

```bash
python -m pytest services/rules/tests/test_accessibility.py -v
```

Expected: 2 passed

- [ ] **Step 5: Register in engine**

Update `services/rules/engine.py` to add `AccessibilityEvaluator`:

```python
from services.rules.evaluators.accessibility import AccessibilityEvaluator

# In __init__, add to self.evaluators:
#     AccessibilityEvaluator(ruleset),
```

- [ ] **Step 6: Commit**

```bash
git add services/rules/
git commit -m "feat: accessibility evaluator — WCAG AA contrast ratio checks"
```

---

## Task 9: Layout + Content + Image Evaluators

**Files:**
- Create: `services/rules/evaluators/layout.py`
- Create: `services/rules/evaluators/content.py`
- Create: `services/rules/evaluators/image.py`
- Create: `services/rules/tests/test_layout.py`
- Create: `services/rules/tests/test_content.py`
- Create: `services/rules/tests/test_image.py`

- [ ] **Step 1: Write failing tests for layout evaluator**

```python
# services/rules/tests/test_layout.py
from packages.csm.models import (
    BoundingBox, Color, Font, Paragraph, Slide, SlideBackground, TextElement, TextRun,
)
from services.rules.evaluators.layout import LayoutEvaluator
from services.rules.models import BrandRulesetConfig, LayoutConfig


def _slide_with_element_at(x: float, y: float) -> Slide:
    return Slide(
        index=0, id="s0", width_pt=720, height_pt=540,
        background=SlideBackground(type="color", color=Color(hex="#FFFFFF", r=255, g=255, b=255)),
        elements=[
            TextElement(
                id="el1",
                bbox=BoundingBox(x=x, y=y, width=200, height=40),
                paragraphs=[Paragraph(
                    runs=[TextRun(text="Test", font=Font(family="Inter", size_pt=16),
                                  color=Color(hex="#000000", r=0, g=0, b=0))],
                    alignment="left", line_spacing=1.0,
                )],
            )
        ],
    )


def test_flags_element_in_margin():
    ruleset = BrandRulesetConfig(layout=LayoutConfig(margin_min_pt=36.0))
    evaluator = LayoutEvaluator(ruleset)
    issues = evaluator.evaluate_slide(_slide_with_element_at(10, 10))  # inside margin
    assert any(i.rule_type == "layout.margin_violation" for i in issues)


def test_passes_element_outside_margin():
    ruleset = BrandRulesetConfig(layout=LayoutConfig(margin_min_pt=36.0))
    evaluator = LayoutEvaluator(ruleset)
    issues = evaluator.evaluate_slide(_slide_with_element_at(50, 50))
    assert not any(i.rule_type == "layout.margin_violation" for i in issues)
```

- [ ] **Step 2: Write failing test for content evaluator**

```python
# services/rules/tests/test_content.py
from packages.csm.models import (
    BoundingBox, Color, Font, Paragraph, Slide, SlideBackground, TextElement, TextRun,
)
from services.rules.evaluators.content import ContentEvaluator
from services.rules.models import BrandRulesetConfig


def _slide_with_word_count(word_count: int) -> Slide:
    text = " ".join(["word"] * word_count)
    return Slide(
        index=0, id="s0", width_pt=720, height_pt=540,
        background=SlideBackground(type="color", color=Color(hex="#FFFFFF", r=255, g=255, b=255)),
        elements=[
            TextElement(
                id="el1",
                bbox=BoundingBox(x=50, y=50, width=600, height=400),
                paragraphs=[Paragraph(
                    runs=[TextRun(text=text, font=Font(family="Inter", size_pt=14),
                                  color=Color(hex="#000000", r=0, g=0, b=0))],
                    alignment="left", line_spacing=1.0,
                )],
            )
        ],
    )


def test_flags_dense_slide():
    evaluator = ContentEvaluator(BrandRulesetConfig())
    issues = evaluator.evaluate_slide(_slide_with_word_count(200))
    assert any(i.rule_type == "content.too_dense" for i in issues)


def test_passes_normal_slide():
    evaluator = ContentEvaluator(BrandRulesetConfig())
    issues = evaluator.evaluate_slide(_slide_with_word_count(30))
    assert not any(i.rule_type == "content.too_dense" for i in issues)
```

- [ ] **Step 3: Write failing test for image evaluator**

```python
# services/rules/tests/test_image.py
from packages.csm.models import (
    BoundingBox, Color, ImageElement, Slide, SlideBackground,
)
from services.rules.evaluators.image import ImageEvaluator
from services.rules.models import BrandRulesetConfig, AccessibilityConfig


def _slide_with_image(has_alt: bool, dpi: float | None = 150) -> Slide:
    return Slide(
        index=0, id="s0", width_pt=720, height_pt=540,
        background=SlideBackground(type="color", color=Color(hex="#FFFFFF", r=255, g=255, b=255)),
        elements=[
            ImageElement(
                id="img1",
                bbox=BoundingBox(x=50, y=50, width=300, height=200),
                ref="images/photo.png",
                aspect_ratio=1.5,
                dpi=dpi,
                has_alt_text=has_alt,
                alt_text="A photo" if has_alt else None,
            )
        ],
    )


def test_flags_missing_alt_text():
    ruleset = BrandRulesetConfig(
        accessibility=AccessibilityConfig(require_alt_text=True),
    )
    evaluator = ImageEvaluator(ruleset)
    issues = evaluator.evaluate_slide(_slide_with_image(has_alt=False))
    assert any(i.rule_type == "image.no_alt_text" for i in issues)


def test_flags_low_dpi():
    evaluator = ImageEvaluator(BrandRulesetConfig())
    issues = evaluator.evaluate_slide(_slide_with_image(has_alt=True, dpi=50))
    assert any(i.rule_type == "image.low_dpi" for i in issues)
```

- [ ] **Step 4: Run all tests to verify they fail**

```bash
python -m pytest services/rules/tests/ -v
```

- [ ] **Step 5: Implement all three evaluators**

```python
# services/rules/evaluators/layout.py
from __future__ import annotations

from packages.csm.models import Slide
from services.rules.models import BrandRulesetConfig, IssueResult, LayoutConfig


class LayoutEvaluator:
    def __init__(self, ruleset: BrandRulesetConfig):
        if isinstance(ruleset.layout, dict):
            self.config = LayoutConfig(**ruleset.layout)
        else:
            self.config = ruleset.layout

    def evaluate_slide(self, slide: Slide) -> list[IssueResult]:
        issues = []
        margin = self.config.margin_min_pt

        for el in slide.elements:
            bbox = el.bbox
            if bbox.x < margin or bbox.y < margin:
                issues.append(IssueResult(
                    rule_type="layout.margin_violation",
                    severity="warning",
                    message=f"Element '{el.id}' at ({bbox.x:.0f}, {bbox.y:.0f}) "
                            f"is within the {margin}pt margin zone",
                    element_id=el.id,
                    element_bbox=bbox.model_dump(),
                ))
            if bbox.x + bbox.width > slide.width_pt - margin:
                issues.append(IssueResult(
                    rule_type="layout.margin_violation",
                    severity="warning",
                    message=f"Element '{el.id}' extends past right margin",
                    element_id=el.id,
                ))

        if len(slide.elements) > self.config.max_elements_per_slide:
            issues.append(IssueResult(
                rule_type="layout.too_many_elements",
                severity="warning",
                message=f"Slide has {len(slide.elements)} elements "
                        f"(max {self.config.max_elements_per_slide})",
            ))
        return issues
```

```python
# services/rules/evaluators/content.py
from __future__ import annotations

from packages.csm.models import Slide, TextElement
from services.rules.models import BrandRulesetConfig, IssueResult

MAX_WORDS_PER_SLIDE = 100


class ContentEvaluator:
    def __init__(self, ruleset: BrandRulesetConfig):
        self.max_words = MAX_WORDS_PER_SLIDE

    def evaluate_slide(self, slide: Slide) -> list[IssueResult]:
        issues = []
        total_words = 0
        for el in slide.elements:
            if el.type == "text":
                for para in el.paragraphs:
                    for run in para.runs:
                        total_words += len(run.text.split())

        if total_words > self.max_words:
            issues.append(IssueResult(
                rule_type="content.too_dense",
                severity="warning",
                message=f"Slide has ~{total_words} words (recommended max: {self.max_words}). "
                        "Consider splitting across multiple slides.",
                original_value=str(total_words),
                expected_value=f"<= {self.max_words}",
            ))
        return issues
```

```python
# services/rules/evaluators/image.py
from __future__ import annotations

from packages.csm.models import ImageElement, Slide
from services.rules.models import AccessibilityConfig, BrandRulesetConfig, IssueResult

MIN_DPI = 72


class ImageEvaluator:
    def __init__(self, ruleset: BrandRulesetConfig):
        if isinstance(ruleset.accessibility, dict):
            self.a11y = AccessibilityConfig(**ruleset.accessibility)
        else:
            self.a11y = ruleset.accessibility

    def evaluate_slide(self, slide: Slide) -> list[IssueResult]:
        issues = []
        for el in slide.elements:
            if el.type == "image":
                if self.a11y.require_alt_text and not el.has_alt_text:
                    issues.append(IssueResult(
                        rule_type="image.no_alt_text",
                        severity="warning",
                        message=f"Image '{el.id}' has no alt text (required for accessibility)",
                        element_id=el.id,
                    ))
                if el.dpi is not None and el.dpi < MIN_DPI:
                    issues.append(IssueResult(
                        rule_type="image.low_dpi",
                        severity="warning",
                        message=f"Image DPI ({el.dpi}) is below minimum ({MIN_DPI})",
                        element_id=el.id,
                        original_value=str(el.dpi),
                        expected_value=f">= {MIN_DPI}",
                    ))
                if el.is_stretched:
                    issues.append(IssueResult(
                        rule_type="image.stretched",
                        severity="warning",
                        message=f"Image '{el.id}' appears stretched/distorted",
                        element_id=el.id,
                    ))
        return issues
```

- [ ] **Step 6: Register all evaluators in engine**

Update `services/rules/engine.py` to include all evaluators:

```python
from services.rules.evaluators.color import ColorEvaluator
from services.rules.evaluators.typography import TypographyEvaluator
from services.rules.evaluators.layout import LayoutEvaluator
from services.rules.evaluators.accessibility import AccessibilityEvaluator
from services.rules.evaluators.content import ContentEvaluator
from services.rules.evaluators.image import ImageEvaluator

# In __init__:
self.evaluators = [
    ColorEvaluator(ruleset),
    TypographyEvaluator(ruleset),
    LayoutEvaluator(ruleset),
    AccessibilityEvaluator(ruleset),
    ContentEvaluator(ruleset),
    ImageEvaluator(ruleset),
]
```

- [ ] **Step 7: Run all tests**

```bash
python -m pytest services/rules/ -v
```

Expected: All tests pass

- [ ] **Step 8: Commit**

```bash
git add services/rules/
git commit -m "feat: layout, content, and image evaluators with full test coverage"
```

---

## Task 10: Vision Scoring Service (GPT-4o)

**Files:**
- Create: `services/vision/__init__.py`
- Create: `services/vision/rubric.py`
- Create: `services/vision/scorer.py`
- Create: `services/vision/test_scorer.py`

- [ ] **Step 1: Write the failing test (mocked OpenAI)**

```python
# services/vision/test_scorer.py
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from services.vision.scorer import VisionScorer, VisionScoreOutput


def test_vision_score_output_validation():
    valid = VisionScoreOutput(
        visual_hierarchy=8,
        whitespace_balance=7,
        alignment_discipline=9,
        consistency=8,
        information_density=6,
        reasoning="Well-structured slide",
    )
    assert valid.dqs == pytest.approx(76.0)  # (8+7+9+8+6)/5 * 10


def test_vision_score_output_rejects_out_of_range():
    with pytest.raises(Exception):
        VisionScoreOutput(
            visual_hierarchy=15,  # invalid
            whitespace_balance=7,
            alignment_discipline=9,
            consistency=8,
            information_density=6,
            reasoning="Test",
        )


@pytest.mark.asyncio
async def test_score_slide_parses_response():
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = json.dumps({
        "visual_hierarchy": 8,
        "whitespace_balance": 7,
        "alignment_discipline": 9,
        "consistency": 8,
        "information_density": 6,
        "reasoning": "Clean layout",
    })

    with patch("services.vision.scorer.openai") as mock_openai:
        mock_client = AsyncMock()
        mock_openai.AsyncOpenAI.return_value = mock_client
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

        scorer = VisionScorer()
        result = await scorer.score_slide_from_bytes(b"fake_png_data")

    assert result.visual_hierarchy == 8
    assert result.dqs == pytest.approx(76.0)
```

- [ ] **Step 2: Run test to verify it fails**

```bash
python -m pytest services/vision/test_scorer.py -v
```

- [ ] **Step 3: Implement vision scorer**

```python
# services/vision/__init__.py
```

```python
# services/vision/rubric.py
VISION_RUBRIC = """
You are a presentation design expert. Score this slide on 5 dimensions, each 1-10:

1. visual_hierarchy: Is the most important content the most visually prominent?
2. whitespace_balance: Is breathing room well distributed — not too dense, not too sparse?
3. alignment_discipline: Do elements feel intentionally placed, aligned to a grid?
4. consistency: Does this slide feel like it belongs in a cohesive deck visually?
5. information_density: Is the content load appropriate for a single presented slide?

Respond ONLY as valid JSON:
{"visual_hierarchy": X, "whitespace_balance": X, "alignment_discipline": X,
 "consistency": X, "information_density": X, "reasoning": "..."}
"""
```

```python
# services/vision/scorer.py
from __future__ import annotations

import base64
import json

import openai
from pydantic import BaseModel, field_validator

from services.vision.rubric import VISION_RUBRIC


class VisionScoreOutput(BaseModel):
    visual_hierarchy: float
    whitespace_balance: float
    alignment_discipline: float
    consistency: float
    information_density: float
    reasoning: str

    @field_validator(
        "visual_hierarchy", "whitespace_balance", "alignment_discipline",
        "consistency", "information_density",
    )
    @classmethod
    def score_in_range(cls, v: float) -> float:
        if not (1 <= v <= 10):
            raise ValueError(f"Score must be between 1 and 10, got {v}")
        return v

    @property
    def dqs(self) -> float:
        total = (
            self.visual_hierarchy
            + self.whitespace_balance
            + self.alignment_discipline
            + self.consistency
            + self.information_density
        )
        return total / 5 * 10


class VisionScorer:
    def __init__(self):
        self.client = openai.AsyncOpenAI()

    async def score_slide_from_bytes(self, image_data: bytes) -> VisionScoreOutput:
        image_b64 = base64.b64encode(image_data).decode("utf-8")
        response = await self.client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": VISION_RUBRIC},
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/png;base64,{image_b64}"},
                        },
                    ],
                }
            ],
            response_format={"type": "json_object"},
            max_tokens=512,
        )
        raw = response.choices[0].message.content
        return VisionScoreOutput(**json.loads(raw))
```

- [ ] **Step 4: Run test to verify it passes**

```bash
python -m pytest services/vision/test_scorer.py -v
```

Expected: 3 passed

- [ ] **Step 5: Commit**

```bash
git add services/vision/
git commit -m "feat: GPT-4o vision scorer with validated output schema"
```

---

## Task 11: Correction Engine + PPTX Exporter

**Files:**
- Create: `services/correction/__init__.py`
- Create: `services/correction/engine.py`
- Create: `services/correction/correctors/__init__.py`
- Create: `services/correction/correctors/color.py`
- Create: `services/correction/correctors/font.py`
- Create: `services/correction/correctors/contrast.py`
- Create: `services/correction/correctors/font_size.py`
- Create: `services/correction/exporter.py`
- Create: `services/correction/tests/test_color_corrector.py`
- Create: `services/correction/tests/test_exporter.py`

- [ ] **Step 1: Write failing test for color corrector**

```python
# services/correction/tests/__init__.py
```

```python
# services/correction/tests/test_color_corrector.py
from packages.csm.models import (
    BoundingBox, Color, Font, Paragraph, Slide, SlideBackground, TextElement, TextRun,
)
from services.correction.correctors.color import ColorCorrector
from services.rules.models import IssueResult


def _slide_with_color(hex_color: str) -> Slide:
    r = int(hex_color[1:3], 16)
    g = int(hex_color[3:5], 16)
    b = int(hex_color[5:7], 16)
    return Slide(
        index=0, id="s0", width_pt=720, height_pt=540,
        background=SlideBackground(type="color", color=Color(hex="#FFFFFF", r=255, g=255, b=255)),
        elements=[
            TextElement(
                id="el1",
                bbox=BoundingBox(x=50, y=50, width=400, height=60),
                paragraphs=[Paragraph(
                    runs=[TextRun(text="Test", font=Font(family="Inter", size_pt=16),
                                  color=Color(hex=hex_color, r=r, g=g, b=b))],
                    alignment="left", line_spacing=1.0,
                )],
            )
        ],
    )


def test_color_corrector_swaps_color():
    slide = _slide_with_color("#FF0000")
    issue = IssueResult(
        rule_type="color.off_brand",
        severity="error",
        message="Off brand",
        element_id="el1",
        original_value="#FF0000",
        expected_value="#1A2B4C",
    )
    corrector = ColorCorrector()
    corrected = corrector.apply(slide, issue)
    # Find the text run and verify color was changed
    el = corrected.elements[0]
    assert el.paragraphs[0].runs[0].color.hex == "#1A2B4C"
```

- [ ] **Step 2: Run test to verify it fails**

```bash
python -m pytest services/correction/tests/test_color_corrector.py -v
```

- [ ] **Step 3: Implement color corrector**

```python
# services/correction/__init__.py
```

```python
# services/correction/correctors/__init__.py
```

```python
# services/correction/correctors/color.py
from __future__ import annotations

from packages.csm.models import Color, Slide
from services.rules.models import IssueResult


class ColorCorrector:
    def apply(self, slide: Slide, issue: IssueResult) -> Slide:
        corrected = slide.model_copy(deep=True)
        if not issue.expected_value or not issue.element_id:
            return corrected

        new_hex = issue.expected_value
        nr = int(new_hex[1:3], 16)
        ng = int(new_hex[3:5], 16)
        nb = int(new_hex[5:7], 16)
        new_color = Color(hex=new_hex, r=nr, g=ng, b=nb)

        for el in corrected.elements:
            if el.id == issue.element_id and el.type == "text":
                for para in el.paragraphs:
                    for run in para.runs:
                        if run.color.hex.upper() == (issue.original_value or "").upper():
                            run.color = new_color
        return corrected
```

- [ ] **Step 4: Implement font corrector**

```python
# services/correction/correctors/font.py
from __future__ import annotations

from packages.csm.models import Slide
from services.rules.models import IssueResult


class FontCorrector:
    def apply(self, slide: Slide, issue: IssueResult) -> Slide:
        corrected = slide.model_copy(deep=True)
        if not issue.expected_value or not issue.element_id:
            return corrected

        for el in corrected.elements:
            if el.id == issue.element_id and el.type == "text":
                for para in el.paragraphs:
                    for run in para.runs:
                        if run.font.family == issue.original_value:
                            run.font.family = issue.expected_value
        return corrected
```

- [ ] **Step 5: Implement contrast corrector**

```python
# services/correction/correctors/contrast.py
from __future__ import annotations

from packages.csm.models import Color, Slide
from services.rules.models import IssueResult


class ContrastCorrector:
    def apply(self, slide: Slide, issue: IssueResult) -> Slide:
        """Darken text color to meet contrast minimum against background."""
        corrected = slide.model_copy(deep=True)
        if not issue.element_id:
            return corrected

        for el in corrected.elements:
            if el.id == issue.element_id and el.type == "text":
                for para in el.paragraphs:
                    for run in para.runs:
                        # Simple approach: darken by reducing RGB values by 30%
                        r = max(0, int(run.color.r * 0.7))
                        g = max(0, int(run.color.g * 0.7))
                        b = max(0, int(run.color.b * 0.7))
                        run.color = Color(hex=f"#{r:02X}{g:02X}{b:02X}", r=r, g=g, b=b)
        return corrected
```

- [ ] **Step 6: Implement font size corrector**

```python
# services/correction/correctors/font_size.py
from __future__ import annotations

from packages.csm.models import Slide
from services.rules.models import IssueResult


class FontSizeCorrector:
    def apply(self, slide: Slide, issue: IssueResult) -> Slide:
        corrected = slide.model_copy(deep=True)
        if not issue.expected_value or not issue.element_id:
            return corrected

        target_size = float(issue.expected_value)
        for el in corrected.elements:
            if el.id == issue.element_id and el.type == "text":
                for para in el.paragraphs:
                    for run in para.runs:
                        if run.font.size_pt < target_size:
                            run.font.size_pt = target_size
        return corrected
```

- [ ] **Step 7: Implement correction engine**

```python
# services/correction/engine.py
from __future__ import annotations

from packages.csm.models import Slide
from services.correction.correctors.color import ColorCorrector
from services.correction.correctors.contrast import ContrastCorrector
from services.correction.correctors.font import FontCorrector
from services.correction.correctors.font_size import FontSizeCorrector
from services.rules.models import IssueResult


class CorrectionEngine:
    def __init__(self):
        self.correctors = {
            "color.off_brand": ColorCorrector(),
            "typography.wrong_font": FontCorrector(),
            "a11y.low_contrast": ContrastCorrector(),
            "typography.size_too_small": FontSizeCorrector(),
        }

    def correct_slide(self, slide: Slide, issues: list[IssueResult]) -> Slide:
        corrected = slide.model_copy(deep=True)
        for issue in issues:
            corrector = self.correctors.get(issue.rule_type)
            if corrector:
                corrected = corrector.apply(corrected, issue)
        return corrected
```

- [ ] **Step 8: Implement PPTX exporter (CSM → .pptx)**

```python
# services/correction/exporter.py
from __future__ import annotations

import io

from pptx import Presentation
from pptx.util import Pt, Emu
from pptx.dml.color import RGBColor

from packages.csm.models import CSM, Slide, TextElement


def _pt_to_emu(pt: float) -> int:
    return int(pt * 12700)


class PptxExporter:
    def export(self, csm: CSM) -> bytes:
        """Export a CSM to a .pptx file. Creates a new presentation from scratch."""
        prs = Presentation()
        prs.slide_width = _pt_to_emu(csm.slides[0].width_pt) if csm.slides else Emu(9144000)
        prs.slide_height = _pt_to_emu(csm.slides[0].height_pt) if csm.slides else Emu(6858000)

        blank_layout = prs.slide_layouts[6]  # Blank layout

        for csm_slide in csm.slides:
            slide = prs.slides.add_slide(blank_layout)
            for el in csm_slide.elements:
                if el.type == "text":
                    self._add_text_element(slide, el)

        buf = io.BytesIO()
        prs.save(buf)
        return buf.getvalue()

    def _add_text_element(self, slide, el: TextElement):
        txBox = slide.shapes.add_textbox(
            _pt_to_emu(el.bbox.x),
            _pt_to_emu(el.bbox.y),
            _pt_to_emu(el.bbox.width),
            _pt_to_emu(el.bbox.height),
        )
        tf = txBox.text_frame
        tf.word_wrap = True

        for p_idx, para in enumerate(el.paragraphs):
            if p_idx == 0:
                p = tf.paragraphs[0]
            else:
                p = tf.add_paragraph()

            for run_data in para.runs:
                run = p.add_run()
                run.text = run_data.text
                run.font.name = run_data.font.family
                run.font.size = Pt(run_data.font.size_pt)
                run.font.bold = run_data.font.weight >= 700
                run.font.italic = run_data.font.italic
                run.font.color.rgb = RGBColor(
                    run_data.color.r, run_data.color.g, run_data.color.b
                )
```

- [ ] **Step 9: Write exporter test**

```python
# services/correction/tests/test_exporter.py
from uuid import uuid4

from pptx import Presentation
import io

from packages.csm.models import (
    BoundingBox, CSM, Color, Font, Paragraph, Slide, SlideBackground, TextElement, TextRun,
)
from services.correction.exporter import PptxExporter


def test_export_produces_valid_pptx():
    csm = CSM(
        id=uuid4(), deck_id=uuid4(), source_type="pptx", total_slides=1,
        slides=[
            Slide(
                index=0, id="s0", width_pt=720, height_pt=540,
                background=SlideBackground(type="color", color=Color(hex="#FFFFFF", r=255, g=255, b=255)),
                elements=[
                    TextElement(
                        id="el1",
                        bbox=BoundingBox(x=50, y=50, width=400, height=60),
                        paragraphs=[Paragraph(
                            runs=[TextRun(text="Hello Burnish", font=Font(family="Inter", size_pt=24, weight=700),
                                          color=Color(hex="#1A2B4C", r=26, g=43, b=76))],
                            alignment="left", line_spacing=1.0,
                        )],
                    )
                ],
            )
        ],
        master_fonts=[], master_colors=[], metadata={}, created_at="",
    )
    exporter = PptxExporter()
    pptx_bytes = exporter.export(csm)

    # Verify it's a valid PPTX
    prs = Presentation(io.BytesIO(pptx_bytes))
    assert len(prs.slides) == 1
    shapes = list(prs.slides[0].shapes)
    assert len(shapes) >= 1
    assert shapes[0].has_text_frame
    assert "Hello Burnish" in shapes[0].text_frame.text
```

- [ ] **Step 10: Run all correction tests**

```bash
python -m pytest services/correction/ -v
```

Expected: All passed

- [ ] **Step 11: Commit**

```bash
git add services/correction/
git commit -m "feat: correction engine with color/font/contrast/size correctors + PPTX exporter"
```

---

## Task 12: FastAPI Application Skeleton + Auth Middleware

**Files:**
- Create: `services/api/__init__.py`
- Create: `services/api/main.py`
- Create: `services/api/deps.py`
- Create: `services/api/middleware/__init__.py`
- Create: `services/api/middleware/auth.py`
- Create: `services/api/middleware/tenant.py`
- Create: `services/api/schemas/__init__.py`

- [ ] **Step 1: Write the failing test**

```python
# services/api/test_main.py
import pytest
from httpx import ASGITransport, AsyncClient

from services.api.main import app


@pytest.mark.asyncio
async def test_health_check():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
```

- [ ] **Step 2: Run test to verify it fails**

```bash
python -m pytest services/api/test_main.py -v
```

- [ ] **Step 3: Implement FastAPI app**

```python
# services/api/__init__.py
```

```python
# services/api/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Burnish API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health_check():
    return {"status": "ok"}
```

```python
# services/api/deps.py
from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, Request

from services.db.engine import async_session


async def get_db():
    async with async_session() as session:
        yield session


# Placeholder auth dep — will integrate Clerk JWT later
async def get_current_user(request: Request) -> dict:
    # In production: verify Clerk JWT from Authorization header
    return {"user_id": "dev-user", "org_id": "dev-org", "role": "owner"}
```

```python
# services/api/middleware/__init__.py
```

```python
# services/api/middleware/auth.py
from __future__ import annotations

from fastapi import HTTPException, Request


async def verify_clerk_token(request: Request) -> dict:
    """Placeholder for Clerk JWT verification. Will be replaced with real Clerk SDK."""
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing authorization token")
    # TODO: Verify with Clerk SDK
    return {"user_id": "dev-user", "org_id": "dev-org", "role": "owner"}
```

```python
# services/api/middleware/tenant.py
from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


async def set_tenant_context(session: AsyncSession, org_id: str):
    """Set PostgreSQL RLS context for multi-tenant isolation."""
    # Use parameterized query to prevent SQL injection
    await session.execute(text("SET app.current_org_id = :org_id"), {"org_id": org_id})
```

```python
# services/api/schemas/__init__.py
```

- [ ] **Step 4: Run test to verify it passes**

```bash
python -m pytest services/api/test_main.py -v
```

Expected: 1 passed

- [ ] **Step 5: Commit**

```bash
git add services/api/
git commit -m "feat: FastAPI app skeleton with health check, CORS, and auth placeholder"
```

---

## Task 13: Deck Upload + Check Trigger API Routes

**Files:**
- Create: `services/api/schemas/deck_schemas.py`
- Create: `services/api/schemas/check_schemas.py`
- Create: `services/api/schemas/brand_schemas.py`
- Create: `services/api/routers/__init__.py`
- Create: `services/api/routers/decks.py`
- Create: `services/api/routers/checks.py`
- Create: `services/api/routers/brand.py`
- Create: `services/api/routers/corrections.py`

- [ ] **Step 1: Create API schemas**

```python
# services/api/schemas/deck_schemas.py
from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel


class DeckResponse(BaseModel):
    id: UUID
    name: str
    source_type: str
    slide_count: int
    version_number: int


class DeckListResponse(BaseModel):
    decks: list[DeckResponse]
    total: int
```

```python
# services/api/schemas/check_schemas.py
from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel


class CheckTriggerRequest(BaseModel):
    deck_id: UUID
    ruleset_id: UUID


class CheckRunResponse(BaseModel):
    id: UUID
    deck_id: UUID
    status: str
    dqs_overall: float | None
    issue_count_error: int
    issue_count_warning: int
    issue_count_info: int


class IssueResponse(BaseModel):
    id: UUID
    rule_type: str
    severity: str
    message: str
    element_id: str | None
    element_bbox: dict | None
    original_value: str | None
    expected_value: str | None
    correction_applied: bool
    correction_status: str | None


class SlideResultResponse(BaseModel):
    slide_index: int
    dqs_slide: float
    vision_scores: dict
    thumbnail_url: str | None
    corrected_thumbnail_url: str | None
    issues: list[IssueResponse]
```

```python
# services/api/schemas/brand_schemas.py
from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel


class ColorRuleInput(BaseModel):
    name: str
    hex: str
    tolerance_delta_e: float = 5.0
    usage_context: str | None = None


class FontRuleInput(BaseModel):
    family: str
    context: str | None = None
    min_size_pt: float | None = None


class BrandRulesetCreateRequest(BaseModel):
    name: str
    colors: list[ColorRuleInput] = []
    fonts: list[FontRuleInput] = []
    margin_min_pt: float = 36.0
    max_elements_per_slide: int = 15
    min_contrast_ratio: float = 4.5
    require_alt_text: bool = True


class BrandRulesetResponse(BaseModel):
    id: UUID
    name: str
    version: int
    is_active: bool
    rules: dict
```

```python
# services/api/schemas/correction_schemas.py
from __future__ import annotations

from pydantic import BaseModel


class CorrectionActionRequest(BaseModel):
    action: str  # "accept" or "dismiss"
```

- [ ] **Step 2: Create deck router**

```python
# services/api/routers/__init__.py
```

```python
# services/api/routers/decks.py
from __future__ import annotations

from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, UploadFile

from services.api.deps import get_current_user, get_db
from services.api.schemas.deck_schemas import DeckListResponse, DeckResponse

router = APIRouter(prefix="/decks", tags=["decks"])


@router.post("/upload", response_model=DeckResponse)
async def upload_deck(
    file: UploadFile,
    user: dict = Depends(get_current_user),
):
    """Upload a PPTX file. Returns deck metadata. Triggers async ingestion."""
    if not file.filename or not file.filename.endswith(".pptx"):
        raise HTTPException(status_code=400, detail="Only .pptx files are supported")

    content = await file.read()
    if len(content) > 100 * 1024 * 1024:  # 100MB
        raise HTTPException(status_code=400, detail="File too large (max 100MB)")

    # TODO: Store file in R2, create DB record, enqueue ingestion job
    deck_id = uuid4()
    return DeckResponse(
        id=deck_id,
        name=file.filename,
        source_type="pptx",
        slide_count=0,  # populated after ingestion
        version_number=1,
    )


@router.get("", response_model=DeckListResponse)
async def list_decks(user: dict = Depends(get_current_user)):
    """List all decks for the current org."""
    # TODO: Query DB
    return DeckListResponse(decks=[], total=0)


@router.get("/{deck_id}", response_model=DeckResponse)
async def get_deck(deck_id: UUID, user: dict = Depends(get_current_user)):
    """Get deck metadata."""
    # TODO: Query DB
    raise HTTPException(status_code=404, detail="Deck not found")
```

- [ ] **Step 3: Create checks router**

```python
# services/api/routers/checks.py
from __future__ import annotations

from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException

from services.api.deps import get_current_user
from services.api.schemas.check_schemas import (
    CheckRunResponse,
    CheckTriggerRequest,
    SlideResultResponse,
)

router = APIRouter(prefix="/checks", tags=["checks"])


@router.post("", response_model=CheckRunResponse)
async def trigger_check(
    request: CheckTriggerRequest,
    user: dict = Depends(get_current_user),
):
    """Trigger a new check run for a deck against a ruleset."""
    check_id = uuid4()
    # TODO: Enqueue check job
    return CheckRunResponse(
        id=check_id,
        deck_id=request.deck_id,
        status="queued",
        dqs_overall=None,
        issue_count_error=0,
        issue_count_warning=0,
        issue_count_info=0,
    )


@router.get("/{check_id}", response_model=CheckRunResponse)
async def get_check(check_id: UUID, user: dict = Depends(get_current_user)):
    """Get check run status and summary."""
    # TODO: Query DB
    raise HTTPException(status_code=404, detail="Check not found")


@router.get("/{check_id}/slides", response_model=list[SlideResultResponse])
async def get_check_slides(check_id: UUID, user: dict = Depends(get_current_user)):
    """Get per-slide results for a check run."""
    # TODO: Query DB
    return []
```

- [ ] **Step 4: Create brand router**

```python
# services/api/routers/brand.py
from __future__ import annotations

from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException

from services.api.deps import get_current_user
from services.api.schemas.brand_schemas import (
    BrandRulesetCreateRequest,
    BrandRulesetResponse,
)

router = APIRouter(prefix="/brand", tags=["brand"])


@router.post("/rulesets", response_model=BrandRulesetResponse)
async def create_ruleset(
    request: BrandRulesetCreateRequest,
    user: dict = Depends(get_current_user),
):
    """Create a new brand ruleset from manual input."""
    ruleset_id = uuid4()
    rules = {
        "colors": [c.model_dump() for c in request.colors],
        "fonts": [f.model_dump() for f in request.fonts],
        "layout": {
            "margin_min_pt": request.margin_min_pt,
            "max_elements_per_slide": request.max_elements_per_slide,
        },
        "accessibility": {
            "min_contrast_ratio": request.min_contrast_ratio,
            "require_alt_text": request.require_alt_text,
        },
    }
    # TODO: Store in DB
    return BrandRulesetResponse(
        id=ruleset_id,
        name=request.name,
        version=1,
        is_active=True,
        rules=rules,
    )


@router.get("/rulesets", response_model=list[BrandRulesetResponse])
async def list_rulesets(user: dict = Depends(get_current_user)):
    """List brand rulesets for the org."""
    # TODO: Query DB
    return []


@router.get("/rulesets/{ruleset_id}", response_model=BrandRulesetResponse)
async def get_ruleset(ruleset_id: UUID, user: dict = Depends(get_current_user)):
    """Get a specific ruleset."""
    # TODO: Query DB
    raise HTTPException(status_code=404, detail="Ruleset not found")
```

- [ ] **Step 5: Create corrections router**

```python
# services/api/routers/corrections.py
from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from services.api.deps import get_current_user
from services.api.schemas.correction_schemas import CorrectionActionRequest

router = APIRouter(prefix="/checks", tags=["corrections"])


@router.get("/{check_id}/slides/{slide_idx}/correction")
async def get_correction(
    check_id: UUID,
    slide_idx: int,
    user: dict = Depends(get_current_user),
):
    """Get corrected slide data + thumbnail URL."""
    # TODO: Fetch from DB/R2
    return {
        "slide_index": slide_idx,
        "corrected_thumbnail_url": None,
        "corrected_csm_ref": None,
    }


@router.post("/{check_id}/slides/{slide_idx}/correction/accept")
async def accept_correction(
    check_id: UUID,
    slide_idx: int,
    user: dict = Depends(get_current_user),
):
    """Accept the correction for a slide."""
    # TODO: Update DB, mark correction as accepted
    return {"status": "accepted"}


@router.post("/{check_id}/slides/{slide_idx}/correction/dismiss")
async def dismiss_correction(
    check_id: UUID,
    slide_idx: int,
    user: dict = Depends(get_current_user),
):
    """Dismiss the correction for a slide."""
    # TODO: Update DB
    return {"status": "dismissed"}
```

- [ ] **Step 6: Register routers in main app**

Update `services/api/main.py`:

```python
from services.api.routers import decks, checks, brand, corrections

app.include_router(decks.router, prefix="/v1")
app.include_router(checks.router, prefix="/v1")
app.include_router(brand.router, prefix="/v1")
app.include_router(corrections.router, prefix="/v1")
```

- [ ] **Step 6: Write router integration test**

```python
# services/api/test_routers.py
import pytest
from httpx import ASGITransport, AsyncClient

from services.api.main import app


@pytest.mark.asyncio
async def test_list_decks():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/v1/decks")
    assert response.status_code == 200
    assert response.json()["total"] == 0


@pytest.mark.asyncio
async def test_create_brand_ruleset():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/v1/brand/rulesets", json={
            "name": "Test Brand",
            "colors": [{"name": "Blue", "hex": "#1A2B4C"}],
            "fonts": [{"family": "Inter"}],
        })
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Test Brand"
    assert data["is_active"] is True
```

- [ ] **Step 7: Run tests**

```bash
python -m pytest services/api/ -v
```

Expected: All passed

- [ ] **Step 8: Commit**

```bash
git add services/api/
git commit -m "feat: API routes — deck upload, check trigger, brand ruleset CRUD"
```

---

## Task 14: Frontend Design Direction (MUST DO BEFORE ANY UI CODE)

**Pre-requisite:** Read `docs/personas-and-cjms.md` before proceeding.

This task establishes the design system, aesthetic direction, and component patterns for the entire frontend. No UI code should be written without completing this task first.

**Skills required:**
- `frontend-design` — for distinctive, non-generic UI direction
- `user-research-insights` — for grounding design in persona needs (install via `npx skillfish add` if not available)

- [ ] **Step 1: Read personas and CJMs**

Read `docs/personas-and-cjms.md` thoroughly. Internalize these three users:
- **Maya** (Brand Manager) — sets up rules, reviews extractions, checks analytics
- **Jake** (Sales AE) — uploads, clicks "Fix All", downloads, leaves in 90 seconds
- **Priya** (Freelance Designer) — switches brands, reviews each issue individually, edits corrections

- [ ] **Step 2: Define aesthetic direction using frontend-design skill**

Invoke the `frontend-design` skill. Follow the Mandatory Design Thinking Phase:

**Purpose:** Burnish is a professional tool for people who care about design quality. It should feel like the *result* of good design — not like a dashboard template.

**Recommended tone:** **Editorial / Magazine** with **Industrial / Utilitarian** accents.
- The slide preview area should feel like a lightbox in a gallery — clean, focused, spacious
- The issue panel should feel like a typographer's margin notes — precise, informative, understated
- The correction view should feel like a before/after in a design magazine — dramatic reveal

**Differentiation anchor:** If someone screenshots the correction view with the logo removed, they should recognize it by:
- The dramatic side-by-side with issue annotations that use thin, precise lines (not fat colored boxes)
- Typography-forward issue descriptions (not card-based generic alerts)
- The DQS score rendered as a large, confident number — not a progress bar

- [ ] **Step 3: Compute DFII score**

Evaluate the direction:
| Dimension | Score | Rationale |
|-----------|-------|-----------|
| Aesthetic Impact | 4 | Editorial + industrial is distinctive but not radical |
| Context Fit | 5 | Perfect for a design quality tool — practices what it preaches |
| Implementation Feasibility | 4 | Achievable with Tailwind + custom CSS variables |
| Performance Safety | 5 | No heavy animations, mostly typography + layout |
| Consistency Risk | 2 | Low — restrained palette, systematic spacing |

**DFII = (4+5+4+5) - 2 = 16** → Excellent. Execute fully.

- [ ] **Step 4: Define the Design System Snapshot**

Create `apps/web/src/styles/design-system.md` with:

```markdown
# Burnish Design System

## Aesthetic Direction
Editorial / Magazine + Industrial Utilitarian
"A design quality tool that looks like the output of great design."

## Fonts
- **Display/Headings:** Instrument Serif (from Google Fonts) — editorial gravitas, distinctive serifs
- **Body/UI:** Geist Sans (from Vercel) — clean, modern, excellent readability at small sizes
- **Monospace (scores/data):** Geist Mono — for DQS numbers, hex codes, measurements
- **Rationale:** Instrument Serif signals editorial authority. Geist is functional without being generic (not Inter/Roboto).

## Color System (CSS Variables)
```css
:root {
  /* Ink — dominant dark tones */
  --ink-950: #0A0A0B;
  --ink-900: #18181B;
  --ink-800: #27272A;
  --ink-700: #3F3F46;
  --ink-500: #71717A;
  --ink-300: #D4D4D8;
  --ink-100: #F4F4F5;
  --ink-50: #FAFAFA;

  /* Signal — issue severity */
  --signal-error: #DC2626;
  --signal-error-soft: #FEF2F2;
  --signal-warning: #D97706;
  --signal-warning-soft: #FFFBEB;
  --signal-success: #059669;
  --signal-success-soft: #ECFDF5;
  --signal-info: #2563EB;
  --signal-info-soft: #EFF6FF;

  /* Accent — single brand accent */
  --accent: #6366F1;         /* Indigo — used sparingly for CTAs and active states */
  --accent-soft: #EEF2FF;

  /* Surface */
  --surface-page: #FAFAFA;
  --surface-card: #FFFFFF;
  --surface-elevated: #FFFFFF;
  --surface-overlay: rgba(0, 0, 0, 0.6);
}
```

## Spacing Rhythm
Base unit: 4px. Scale: 4, 8, 12, 16, 24, 32, 48, 64, 96.
- Component padding: 16px (compact), 24px (default), 32px (spacious)
- Section gaps: 48px or 64px
- The slide preview area uses generous 64px margins — gallery-like breathing room

## Motion Philosophy
- **Entrance:** Slide corrections fade in from corrected state (0.3s ease-out)
- **Hover:** Issue annotations highlight with a subtle border glow (0.15s)
- **Transitions:** Side-by-side toggle uses a clean crossfade (0.2s)
- **No:** Bouncing, wiggling, particle effects, loading spinners (use skeleton states)

## Component Patterns
- **Issue annotations on slides:** 1px lines with small severity dot, not thick colored rectangles
- **Issue list items:** Typography-led (bold rule name, regular description), not card-based
- **DQS score:** Large Geist Mono number (48px+), color-coded, no surrounding chrome
- **Buttons:** "Fix All" is large, dark, confident. Secondary actions are ghost buttons.
- **Upload zone:** Minimal — thin dashed border, no illustration, large drop target
```

- [ ] **Step 5: Create Tailwind config with design system**

Create `apps/web/tailwind.config.ts` with custom fonts, colors, and spacing from the design system.

- [ ] **Step 6: Commit**

```bash
git add docs/personas-and-cjms.md apps/web/src/styles/
git commit -m "feat: design system, personas, and CJMs — editorial/industrial aesthetic direction"
```

---

## Task 15: Next.js Frontend Scaffold

**Pre-requisite:** Task 14 (Design Direction) must be complete. All components below must follow the design system defined there.

**Files:**
- Create: `apps/web/package.json`
- Create: `apps/web/tsconfig.json`
- Create: `apps/web/tailwind.config.ts`
- Create: `apps/web/next.config.mjs`
- Create: `apps/web/src/app/layout.tsx`
- Create: `apps/web/src/middleware.ts`
- Create: `apps/web/src/lib/api.ts`
- Create: `apps/web/src/lib/types.ts`

- [ ] **Step 1: Initialize Next.js app**

```bash
cd apps && npx create-next-app@latest web --typescript --tailwind --eslint --app --src-dir --no-import-alias
cd web
```

- [ ] **Step 2: Install dependencies**

```bash
npm install @clerk/nextjs zustand @tanstack/react-query react-konva konva
npm install -D @types/react @types/node
```

- [ ] **Step 3: Install shadcn/ui**

```bash
npx shadcn-ui@latest init
npx shadcn-ui@latest add button card badge input label select dialog tabs table
```

- [ ] **Step 4: Create API client**

```typescript
// apps/web/src/lib/api.ts
const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/v1";

async function fetchAPI<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...options?.headers,
    },
  });
  if (!response.ok) {
    throw new Error(`API error: ${response.status}`);
  }
  return response.json();
}

export const api = {
  decks: {
    list: () => fetchAPI<{ decks: Deck[]; total: number }>("/decks"),
    upload: async (file: File) => {
      const formData = new FormData();
      formData.append("file", file);
      const response = await fetch(`${API_BASE}/decks/upload`, {
        method: "POST",
        body: formData,
      });
      return response.json();
    },
  },
  checks: {
    trigger: (deckId: string, rulesetId: string) =>
      fetchAPI<CheckRun>("/checks", {
        method: "POST",
        body: JSON.stringify({ deck_id: deckId, ruleset_id: rulesetId }),
      }),
    get: (checkId: string) => fetchAPI<CheckRun>(`/checks/${checkId}`),
    slides: (checkId: string) =>
      fetchAPI<SlideResult[]>(`/checks/${checkId}/slides`),
  },
  brand: {
    createRuleset: (data: CreateRulesetRequest) =>
      fetchAPI<BrandRuleset>("/brand/rulesets", {
        method: "POST",
        body: JSON.stringify(data),
      }),
    listRulesets: () => fetchAPI<BrandRuleset[]>("/brand/rulesets"),
  },
};
```

- [ ] **Step 5: Create shared types**

```typescript
// apps/web/src/lib/types.ts
export interface Deck {
  id: string;
  name: string;
  source_type: string;
  slide_count: number;
  version_number: number;
}

export interface CheckRun {
  id: string;
  deck_id: string;
  status: "queued" | "running" | "complete" | "failed";
  dqs_overall: number | null;
  issue_count_error: number;
  issue_count_warning: number;
  issue_count_info: number;
}

export interface Issue {
  id: string;
  rule_type: string;
  severity: "error" | "warning" | "info";
  message: string;
  element_id: string | null;
  element_bbox: { x: number; y: number; width: number; height: number } | null;
  original_value: string | null;
  expected_value: string | null;
  correction_applied: boolean;
  correction_status: string | null;
}

export interface SlideResult {
  slide_index: number;
  dqs_slide: number;
  vision_scores: Record<string, number>;
  thumbnail_url: string | null;
  corrected_thumbnail_url: string | null;
  issues: Issue[];
}

export interface BrandRuleset {
  id: string;
  name: string;
  version: number;
  is_active: boolean;
  rules: Record<string, unknown>;
}

export interface CreateRulesetRequest {
  name: string;
  colors: Array<{ name: string; hex: string; tolerance_delta_e?: number }>;
  fonts: Array<{ family: string; min_size_pt?: number }>;
  margin_min_pt?: number;
  min_contrast_ratio?: number;
  require_alt_text?: boolean;
}
```

- [ ] **Step 6: Set up root layout with Clerk**

```tsx
// apps/web/src/app/layout.tsx
import type { Metadata } from "next";
import { ClerkProvider } from "@clerk/nextjs";
import { Inter } from "next/font/google";
import "./globals.css";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "Burnish — Design Quality for Presentations",
  description: "AI-powered brand compliance checking for slide decks",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <ClerkProvider>
      <html lang="en">
        <body className={inter.className}>{children}</body>
      </html>
    </ClerkProvider>
  );
}
```

- [ ] **Step 7: Verify frontend builds**

```bash
cd apps/web && npm run build
```

Expected: Build succeeds

- [ ] **Step 8: Commit**

```bash
git add apps/web/
git commit -m "feat: Next.js frontend scaffold with Clerk, Tailwind, shadcn, API client"
```

---

## Task 16: Upload + Deck List UI

**Persona focus:** Jake (Sales AE). He drops a file and expects instant response. Zero forms, zero config. See CJM 2 in `docs/personas-and-cjms.md`.

**Files:**
- Create: `apps/web/src/components/upload-dropzone.tsx`
- Create: `apps/web/src/components/deck-card.tsx`
- Create: `apps/web/src/app/(dashboard)/layout.tsx`
- Create: `apps/web/src/app/(dashboard)/page.tsx`
- Create: `apps/web/src/app/(dashboard)/decks/page.tsx`
- Create: `apps/web/src/app/(dashboard)/decks/upload/page.tsx`

- [ ] **Step 1: Create upload dropzone component**

```tsx
// apps/web/src/components/upload-dropzone.tsx
"use client";

import { useCallback, useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";

export function UploadDropzone() {
  const [isDragging, setIsDragging] = useState(false);
  const [uploading, setUploading] = useState(false);
  const router = useRouter();

  const handleDrop = useCallback(async (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    const file = e.dataTransfer.files[0];
    if (file && file.name.endsWith(".pptx")) {
      setUploading(true);
      try {
        const deck = await api.decks.upload(file);
        router.push(`/decks`);
      } finally {
        setUploading(false);
      }
    }
  }, [router]);

  const handleFileInput = useCallback(async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      setUploading(true);
      try {
        await api.decks.upload(file);
        router.push(`/decks`);
      } finally {
        setUploading(false);
      }
    }
  }, [router]);

  return (
    <div
      className={`border-2 border-dashed rounded-lg p-12 text-center transition-colors ${
        isDragging ? "border-blue-500 bg-blue-50" : "border-gray-300"
      }`}
      onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
      onDragLeave={() => setIsDragging(false)}
      onDrop={handleDrop}
    >
      {uploading ? (
        <p className="text-gray-500">Uploading...</p>
      ) : (
        <>
          <p className="text-lg font-medium">Drop your .pptx file here</p>
          <p className="text-sm text-gray-500 mt-2">or click to browse</p>
          <input
            type="file"
            accept=".pptx"
            onChange={handleFileInput}
            className="hidden"
            id="file-upload"
          />
          <label
            htmlFor="file-upload"
            className="mt-4 inline-block cursor-pointer px-4 py-2 bg-black text-white rounded-md text-sm"
          >
            Choose File
          </label>
        </>
      )}
    </div>
  );
}
```

- [ ] **Step 2: Create dashboard layout and pages**

```tsx
// apps/web/src/app/(dashboard)/layout.tsx
import Link from "next/link";
import { UserButton } from "@clerk/nextjs";

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen bg-gray-50">
      <nav className="border-b bg-white px-6 py-3 flex items-center justify-between">
        <div className="flex items-center gap-6">
          <Link href="/" className="text-xl font-bold">Burnish</Link>
          <Link href="/decks" className="text-sm text-gray-600 hover:text-black">Decks</Link>
          <Link href="/brand" className="text-sm text-gray-600 hover:text-black">Brand</Link>
        </div>
        <UserButton />
      </nav>
      <main className="max-w-6xl mx-auto px-6 py-8">{children}</main>
    </div>
  );
}
```

```tsx
// apps/web/src/app/(dashboard)/page.tsx
import Link from "next/link";

export default function DashboardHome() {
  return (
    <div>
      <h1 className="text-2xl font-bold">Welcome to Burnish</h1>
      <p className="text-gray-600 mt-2">Upload a deck to get started.</p>
      <Link
        href="/decks/upload"
        className="mt-4 inline-block px-4 py-2 bg-black text-white rounded-md text-sm"
      >
        Upload Deck
      </Link>
    </div>
  );
}
```

```tsx
// apps/web/src/app/(dashboard)/decks/upload/page.tsx
import { UploadDropzone } from "@/components/upload-dropzone";

export default function UploadPage() {
  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">Upload Deck</h1>
      <UploadDropzone />
    </div>
  );
}
```

- [ ] **Step 3: Verify it renders**

```bash
cd apps/web && npm run dev
# Visit http://localhost:3000/decks/upload
```

- [ ] **Step 4: Commit**

```bash
git add apps/web/
git commit -m "feat: dashboard layout, deck upload dropzone, navigation"
```

---

## Task 17: Check Results Page + Slide Preview

**Persona focus:** Jake sees red/yellow dots, clicks the worst slide. Priya reviews each one. Issues must be in **plain English** with technical details on hover. See design principles in `docs/personas-and-cjms.md`.

**Files:**
- Create: `apps/web/src/components/dqs-badge.tsx`
- Create: `apps/web/src/components/check-panel.tsx`
- Create: `apps/web/src/components/slide-preview.tsx`
- Create: `apps/web/src/components/issue-overlay.tsx`
- Create: `apps/web/src/app/(dashboard)/checks/[id]/page.tsx`
- Create: `apps/web/src/app/(dashboard)/checks/[id]/slides/[idx]/page.tsx`

- [ ] **Step 1: Create DQS badge component**

```tsx
// apps/web/src/components/dqs-badge.tsx
interface DQSBadgeProps {
  score: number | null;
  size?: "sm" | "md" | "lg";
}

export function DQSBadge({ score, size = "md" }: DQSBadgeProps) {
  if (score === null) return <span className="text-gray-400">—</span>;

  const color =
    score >= 80 ? "bg-green-100 text-green-800" :
    score >= 60 ? "bg-yellow-100 text-yellow-800" :
    "bg-red-100 text-red-800";

  const sizeClass = {
    sm: "text-xs px-1.5 py-0.5",
    md: "text-sm px-2 py-1",
    lg: "text-lg px-3 py-1.5 font-bold",
  }[size];

  return (
    <span className={`inline-block rounded-full ${color} ${sizeClass}`}>
      {score.toFixed(0)}
    </span>
  );
}
```

- [ ] **Step 2: Create check panel (issue list)**

```tsx
// apps/web/src/components/check-panel.tsx
import type { Issue } from "@/lib/types";

interface CheckPanelProps {
  issues: Issue[];
  onIssueClick?: (issue: Issue) => void;
}

const severityStyles = {
  error: "bg-red-100 text-red-800 border-red-200",
  warning: "bg-yellow-100 text-yellow-800 border-yellow-200",
  info: "bg-blue-100 text-blue-800 border-blue-200",
};

export function CheckPanel({ issues, onIssueClick }: CheckPanelProps) {
  return (
    <div className="space-y-2">
      {issues.length === 0 && (
        <p className="text-sm text-gray-500">No issues found.</p>
      )}
      {issues.map((issue) => (
        <button
          key={issue.id}
          onClick={() => onIssueClick?.(issue)}
          className={`w-full text-left p-3 rounded-md border text-sm ${severityStyles[issue.severity]}`}
        >
          <div className="font-medium">{issue.rule_type}</div>
          <div className="mt-1 opacity-80">{issue.message}</div>
          {issue.original_value && issue.expected_value && (
            <div className="mt-1 text-xs">
              <span className="line-through">{issue.original_value}</span>
              {" → "}
              <span className="font-medium">{issue.expected_value}</span>
            </div>
          )}
        </button>
      ))}
    </div>
  );
}
```

- [ ] **Step 3: Create slide preview with issue overlays (placeholder — Konva integration comes next)**

```tsx
// apps/web/src/components/slide-preview.tsx
"use client";

import type { Issue } from "@/lib/types";

interface SlidePreviewProps {
  thumbnailUrl: string | null;
  issues: Issue[];
  width?: number;
  height?: number;
}

export function SlidePreview({ thumbnailUrl, issues, width = 720, height = 540 }: SlidePreviewProps) {
  const scale = 640 / width;  // fit to container

  return (
    <div
      className="relative bg-white border rounded-lg overflow-hidden"
      style={{ width: width * scale, height: height * scale }}
    >
      {thumbnailUrl ? (
        <img src={thumbnailUrl} alt="Slide" className="w-full h-full object-contain" />
      ) : (
        <div className="w-full h-full flex items-center justify-center text-gray-400">
          No preview available
        </div>
      )}
      {/* Issue annotation overlays */}
      {issues
        .filter((i) => i.element_bbox)
        .map((issue) => {
          const bbox = issue.element_bbox!;
          const borderColor =
            issue.severity === "error" ? "border-red-500" :
            issue.severity === "warning" ? "border-yellow-500" :
            "border-blue-500";
          return (
            <div
              key={issue.id}
              className={`absolute border-2 ${borderColor} rounded pointer-events-none`}
              style={{
                left: bbox.x * scale,
                top: bbox.y * scale,
                width: bbox.width * scale,
                height: bbox.height * scale,
              }}
            />
          );
        })}
    </div>
  );
}
```

- [ ] **Step 4: Create check results page**

```tsx
// apps/web/src/app/(dashboard)/checks/[id]/page.tsx
"use client";

import { useParams } from "next/navigation";
import { DQSBadge } from "@/components/dqs-badge";
import Link from "next/link";

// Placeholder — will use TanStack Query to fetch real data
export default function CheckResultsPage() {
  const { id } = useParams<{ id: string }>();

  return (
    <div>
      <div className="flex items-center gap-4 mb-6">
        <h1 className="text-2xl font-bold">Check Results</h1>
        <DQSBadge score={72} size="lg" />
      </div>
      <p className="text-gray-500 text-sm mb-4">Check ID: {id}</p>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {/* Slide cards — populated from API */}
        <div className="border rounded-lg p-4 bg-white">
          <p className="text-sm text-gray-500">Slide thumbnails will appear here after a check run.</p>
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 5: Create single slide detail page with correction view**

```tsx
// apps/web/src/app/(dashboard)/checks/[id]/slides/[idx]/page.tsx
"use client";

import { useParams } from "next/navigation";
import { SlidePreview } from "@/components/slide-preview";
import { CheckPanel } from "@/components/check-panel";
import { DQSBadge } from "@/components/dqs-badge";

export default function SlideDetailPage() {
  const { id, idx } = useParams<{ id: string; idx: string }>();

  // Placeholder data — will be fetched from API
  return (
    <div>
      <h1 className="text-xl font-bold mb-4">
        Slide {idx} <DQSBadge score={68} />
      </h1>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Original slide */}
        <div className="lg:col-span-2">
          <h2 className="text-sm font-medium text-gray-500 mb-2">Original</h2>
          <SlidePreview thumbnailUrl={null} issues={[]} />
        </div>

        {/* Issue panel */}
        <div>
          <h2 className="text-sm font-medium text-gray-500 mb-2">Issues</h2>
          <CheckPanel issues={[]} />
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 6: Verify build**

```bash
cd apps/web && npm run build
```

- [ ] **Step 7: Commit**

```bash
git add apps/web/
git commit -m "feat: check results UI — DQS badge, slide preview, issue panel, correction view"
```

---

## Task 18: Brand Ruleset Editor UI

**Persona focus:** Maya sets up brand rules. Priya manages multiple rulesets. Brand switcher must be fast and always visible. See CJMs 1 & 3 in `docs/personas-and-cjms.md`.

**Files:**
- Create: `apps/web/src/components/brand-rule-editor.tsx`
- Create: `apps/web/src/app/(dashboard)/brand/page.tsx`
- Create: `apps/web/src/app/(dashboard)/brand/[id]/page.tsx`

- [ ] **Step 1: Create brand rule editor component**

```tsx
// apps/web/src/components/brand-rule-editor.tsx
"use client";

import { useState } from "react";
import type { CreateRulesetRequest } from "@/lib/types";

interface BrandRuleEditorProps {
  onSave: (data: CreateRulesetRequest) => void;
}

export function BrandRuleEditor({ onSave }: BrandRuleEditorProps) {
  const [name, setName] = useState("");
  const [colors, setColors] = useState<Array<{ name: string; hex: string }>>([]);
  const [fonts, setFonts] = useState<Array<{ family: string; min_size_pt?: number }>>([]);
  const [newColorName, setNewColorName] = useState("");
  const [newColorHex, setNewColorHex] = useState("#000000");
  const [newFont, setNewFont] = useState("");

  const addColor = () => {
    if (newColorName && newColorHex) {
      setColors([...colors, { name: newColorName, hex: newColorHex }]);
      setNewColorName("");
      setNewColorHex("#000000");
    }
  };

  const addFont = () => {
    if (newFont) {
      setFonts([...fonts, { family: newFont }]);
      setNewFont("");
    }
  };

  return (
    <div className="space-y-6 max-w-xl">
      <div>
        <label className="block text-sm font-medium mb-1">Ruleset Name</label>
        <input
          type="text"
          value={name}
          onChange={(e) => setName(e.target.value)}
          className="w-full border rounded-md px-3 py-2 text-sm"
          placeholder="e.g. Acme Brand Guidelines"
        />
      </div>

      {/* Colors */}
      <div>
        <label className="block text-sm font-medium mb-2">Brand Colors</label>
        <div className="space-y-2 mb-2">
          {colors.map((c, i) => (
            <div key={i} className="flex items-center gap-2">
              <div className="w-6 h-6 rounded border" style={{ backgroundColor: c.hex }} />
              <span className="text-sm">{c.name}</span>
              <span className="text-xs text-gray-400">{c.hex}</span>
              <button onClick={() => setColors(colors.filter((_, j) => j !== i))} className="text-red-500 text-xs ml-auto">Remove</button>
            </div>
          ))}
        </div>
        <div className="flex gap-2">
          <input type="text" value={newColorName} onChange={(e) => setNewColorName(e.target.value)} placeholder="Color name" className="border rounded px-2 py-1 text-sm flex-1" />
          <input type="color" value={newColorHex} onChange={(e) => setNewColorHex(e.target.value)} className="w-10 h-8 border rounded" />
          <button onClick={addColor} className="px-3 py-1 bg-gray-100 rounded text-sm">Add</button>
        </div>
      </div>

      {/* Fonts */}
      <div>
        <label className="block text-sm font-medium mb-2">Brand Fonts</label>
        <div className="space-y-1 mb-2">
          {fonts.map((f, i) => (
            <div key={i} className="flex items-center gap-2">
              <span className="text-sm">{f.family}</span>
              <button onClick={() => setFonts(fonts.filter((_, j) => j !== i))} className="text-red-500 text-xs ml-auto">Remove</button>
            </div>
          ))}
        </div>
        <div className="flex gap-2">
          <input type="text" value={newFont} onChange={(e) => setNewFont(e.target.value)} placeholder="Font family (e.g. Inter)" className="border rounded px-2 py-1 text-sm flex-1" />
          <button onClick={addFont} className="px-3 py-1 bg-gray-100 rounded text-sm">Add</button>
        </div>
      </div>

      <button
        onClick={() => onSave({ name, colors, fonts })}
        disabled={!name}
        className="px-4 py-2 bg-black text-white rounded-md text-sm disabled:opacity-50"
      >
        Save Ruleset
      </button>
    </div>
  );
}
```

- [ ] **Step 2: Create brand pages**

```tsx
// apps/web/src/app/(dashboard)/brand/page.tsx
"use client";

import Link from "next/link";
import { BrandRuleEditor } from "@/components/brand-rule-editor";
import { api } from "@/lib/api";
import { useRouter } from "next/navigation";

export default function BrandPage() {
  const router = useRouter();

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">Brand Rules</h1>
      <BrandRuleEditor
        onSave={async (data) => {
          const ruleset = await api.brand.createRuleset(data);
          router.push(`/brand/${ruleset.id}`);
        }}
      />
    </div>
  );
}
```

- [ ] **Step 3: Verify build**

```bash
cd apps/web && npm run build
```

- [ ] **Step 4: Commit**

```bash
git add apps/web/
git commit -m "feat: brand ruleset editor UI — color picker, font input, save flow"
```

---

## Task 19: Correction View UI (Side-by-Side)

**Persona focus:** This is THE magic moment. Jake clicks "Fix All" — one button, hero CTA. Priya reviews each issue — accept/edit/dismiss per issue. Side-by-side must feel like a design magazine before/after. See all three CJMs.

**Files:**
- Create: `apps/web/src/components/correction-view.tsx`

- [ ] **Step 1: Implement correction view**

```tsx
// apps/web/src/components/correction-view.tsx
"use client";

import { useState } from "react";
import { SlidePreview } from "@/components/slide-preview";
import { CheckPanel } from "@/components/check-panel";
import type { Issue } from "@/lib/types";

interface CorrectionViewProps {
  originalThumbnail: string | null;
  correctedThumbnail: string | null;
  issues: Issue[];
  onAcceptAll: () => void;
  onDismissAll: () => void;
  onAcceptIssue: (issueId: string) => void;
  onDismissIssue: (issueId: string) => void;
}

export function CorrectionView({
  originalThumbnail,
  correctedThumbnail,
  issues,
  onAcceptAll,
  onDismissAll,
  onAcceptIssue,
  onDismissIssue,
}: CorrectionViewProps) {
  const [view, setView] = useState<"split" | "original" | "corrected">("split");

  return (
    <div>
      {/* View toggle */}
      <div className="flex gap-2 mb-4">
        {(["split", "original", "corrected"] as const).map((v) => (
          <button
            key={v}
            onClick={() => setView(v)}
            className={`px-3 py-1 text-sm rounded-md ${
              view === v ? "bg-black text-white" : "bg-gray-100"
            }`}
          >
            {v.charAt(0).toUpperCase() + v.slice(1)}
          </button>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Original */}
        {(view === "split" || view === "original") && (
          <div>
            <h3 className="text-sm font-medium text-red-600 mb-2">Original</h3>
            <SlidePreview thumbnailUrl={originalThumbnail} issues={issues} />
          </div>
        )}

        {/* Corrected */}
        {(view === "split" || view === "corrected") && (
          <div>
            <h3 className="text-sm font-medium text-green-600 mb-2">Corrected</h3>
            <SlidePreview thumbnailUrl={correctedThumbnail} issues={[]} />
          </div>
        )}
      </div>

      {/* Actions */}
      <div className="mt-4 flex gap-3">
        <button
          onClick={onAcceptAll}
          className="px-4 py-2 bg-green-600 text-white rounded-md text-sm"
        >
          Accept All Corrections
        </button>
        <button
          onClick={onDismissAll}
          className="px-4 py-2 bg-gray-200 text-gray-700 rounded-md text-sm"
        >
          Keep Original
        </button>
      </div>

      {/* Per-issue actions */}
      <div className="mt-6">
        <h3 className="text-sm font-medium mb-2">Issues</h3>
        <CheckPanel issues={issues} />
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Verify build**

```bash
cd apps/web && npm run build
```

- [ ] **Step 3: Commit**

```bash
git add apps/web/
git commit -m "feat: side-by-side correction view with accept/dismiss actions"
```

---

## Task 20: Wire Backend End-to-End — Ingestion + Check + Correction Workers

**Files:**
- Create: `services/workers/__init__.py`
- Create: `services/workers/ingestion_worker.py`
- Create: `services/workers/check_worker.py`
- Create: `services/workers/correction_worker.py`

This task connects the pieces: upload → parse CSM → store → check → correct → store results.

**Note:** Workers are implemented as plain async Python classes for the MVP. BullMQ queue integration (Redis job listener, serialization, retry logic) is a follow-up task. For now, these workers can be called directly from API routes or a simple `main.py` runner.

- [ ] **Step 1: Implement ingestion worker**

```python
# services/workers/__init__.py
```

```python
# services/workers/ingestion_worker.py
"""
Ingestion worker: receives uploaded file path, parses to CSM, generates thumbnails, stores results.
"""
from __future__ import annotations

import json
from uuid import UUID

from services.ingestion.pptx_parser import PptxParser
from services.storage.r2 import R2Client


class IngestionWorker:
    def __init__(self, r2: R2Client):
        self.parser = PptxParser()
        self.r2 = r2

    async def process(self, deck_id: UUID, file_key: str) -> dict:
        # 1. Download file from R2
        pptx_bytes = self.r2.download_file(file_key)

        # 2. Parse to CSM
        csm = self.parser.parse(pptx_bytes, deck_id)

        # 3. Store CSM as JSON in R2
        csm_key = f"csm/{deck_id}.json"
        self.r2.upload_file(
            csm.model_dump_json().encode(),
            csm_key,
            "application/json",
        )

        return {
            "deck_id": str(deck_id),
            "csm_key": csm_key,
            "slide_count": csm.total_slides,
        }
```

- [ ] **Step 2: Implement check worker**

```python
# services/workers/check_worker.py
"""
Check worker: loads CSM, runs rule engine + vision scorer, stores results.
"""
from __future__ import annotations

import json
import logging
from uuid import UUID

from packages.csm.models import CSM
from services.rules.engine import RuleEngine
from services.rules.models import BrandRulesetConfig
from services.storage.r2 import R2Client
from services.vision.scorer import VisionScorer

logger = logging.getLogger(__name__)


class CheckWorker:
    def __init__(self, r2: R2Client, enable_vision: bool = True):
        self.r2 = r2
        self.enable_vision = enable_vision
        self.vision_scorer = VisionScorer() if enable_vision else None

    async def process(
        self,
        check_run_id: UUID,
        csm_key: str,
        ruleset_config: dict,
    ) -> dict:
        # 1. Load CSM from R2
        csm_json = self.r2.download_file(csm_key)
        csm = CSM.model_validate_json(csm_json)

        # 2. Build ruleset config
        ruleset = BrandRulesetConfig(**ruleset_config)
        engine = RuleEngine(ruleset)

        # 3. Evaluate all slides (rule-based)
        all_issues = engine.evaluate_all(csm.slides)

        # 4. Vision scoring (if enabled and thumbnails available)
        vision_scores_by_slide: dict[int, dict] = {}
        dqs_scores: list[float] = []
        if self.vision_scorer:
            for slide in csm.slides:
                if slide.thumbnail_ref:
                    try:
                        thumb_bytes = self.r2.download_file(slide.thumbnail_ref)
                        result = await self.vision_scorer.score_slide_from_bytes(thumb_bytes)
                        vision_scores_by_slide[slide.index] = {
                            "visual_hierarchy": result.visual_hierarchy,
                            "whitespace_balance": result.whitespace_balance,
                            "alignment_discipline": result.alignment_discipline,
                            "consistency": result.consistency,
                            "information_density": result.information_density,
                        }
                        dqs_scores.append(result.dqs)
                    except Exception as e:
                        logger.warning(f"Vision scoring failed for slide {slide.index}: {e}")

        # 5. Compute summary
        total_errors = sum(
            1 for issues in all_issues.values() for i in issues if i.severity == "error"
        )
        total_warnings = sum(
            1 for issues in all_issues.values() for i in issues if i.severity == "warning"
        )
        total_info = sum(
            1 for issues in all_issues.values() for i in issues if i.severity == "info"
        )
        dqs_overall = sum(dqs_scores) / len(dqs_scores) if dqs_scores else None

        # 6. Store results
        results_key = f"results/{check_run_id}.json"
        results_data = {
            "issues": {
                str(slide_idx): [issue.model_dump() for issue in issues]
                for slide_idx, issues in all_issues.items()
            },
            "vision_scores": {str(k): v for k, v in vision_scores_by_slide.items()},
            "dqs_overall": dqs_overall,
        }
        self.r2.upload_file(
            json.dumps(results_data).encode(),
            results_key,
            "application/json",
        )

        return {
            "check_run_id": str(check_run_id),
            "results_key": results_key,
            "dqs_overall": dqs_overall,
            "issue_count_error": total_errors,
            "issue_count_warning": total_warnings,
            "issue_count_info": total_info,
        }
```

- [ ] **Step 3: Implement correction worker**

```python
# services/workers/correction_worker.py
"""
Correction worker: loads CSM + issues, applies corrections, exports corrected PPTX.
"""
from __future__ import annotations

import json
from uuid import UUID

from packages.csm.models import CSM
from services.correction.engine import CorrectionEngine
from services.correction.exporter import PptxExporter
from services.rules.models import IssueResult
from services.storage.r2 import R2Client


class CorrectionWorker:
    def __init__(self, r2: R2Client):
        self.r2 = r2
        self.correction_engine = CorrectionEngine()
        self.exporter = PptxExporter()

    async def process(
        self,
        check_run_id: UUID,
        csm_key: str,
        results_key: str,
    ) -> dict:
        # 1. Load CSM and results
        csm_json = self.r2.download_file(csm_key)
        csm = CSM.model_validate_json(csm_json)

        results_json = self.r2.download_file(results_key)
        results_data = json.loads(results_json)
        issues_data = results_data.get("issues", results_data)  # support both formats

        # 2. Apply corrections to each slide
        corrected_slides = []
        for slide in csm.slides:
            slide_issues_raw = issues_data.get(str(slide.index), [])
            issues = [IssueResult(**i) for i in slide_issues_raw]
            corrected = self.correction_engine.correct_slide(slide, issues)
            corrected_slides.append(corrected)

        # 3. Build corrected CSM
        corrected_csm = csm.model_copy(deep=True)
        corrected_csm.slides = corrected_slides

        # 4. Export corrected PPTX
        pptx_bytes = self.exporter.export(corrected_csm)
        corrected_key = f"corrected/{check_run_id}.pptx"
        self.r2.upload_file(
            pptx_bytes,
            corrected_key,
            "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        )

        # 5. Store corrected CSM
        corrected_csm_key = f"corrected/{check_run_id}_csm.json"
        self.r2.upload_file(
            corrected_csm.model_dump_json().encode(),
            corrected_csm_key,
            "application/json",
        )

        return {
            "corrected_pptx_key": corrected_key,
            "corrected_csm_key": corrected_csm_key,
        }
```

- [ ] **Step 4: Write integration test**

```python
# tests/integration/test_full_pipeline.py
import io
from uuid import uuid4

import pytest
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor

from services.ingestion.pptx_parser import PptxParser
from services.rules.engine import RuleEngine
from services.rules.models import BrandRulesetConfig, ColorRuleConfig, FontRuleConfig
from services.correction.engine import CorrectionEngine
from services.correction.exporter import PptxExporter


def _make_violation_pptx() -> bytes:
    """PPTX with known brand violations."""
    prs = Presentation()
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    txBox = slide.shapes.add_textbox(Inches(1), Inches(1), Inches(5), Inches(1))
    tf = txBox.text_frame
    run = tf.paragraphs[0].add_run()
    run.text = "Off-brand text"
    run.font.name = "Comic Sans MS"  # wrong font
    run.font.size = Pt(16)
    run.font.color.rgb = RGBColor(0xFF, 0x00, 0x00)  # wrong color
    buf = io.BytesIO()
    prs.save(buf)
    return buf.getvalue()


def test_full_pipeline_parse_check_correct():
    """End-to-end: parse PPTX → check → correct → export."""
    pptx_bytes = _make_violation_pptx()

    # 1. Parse
    parser = PptxParser()
    csm = parser.parse(pptx_bytes, uuid4())
    assert csm.total_slides == 1

    # 2. Check
    ruleset = BrandRulesetConfig(
        colors=[ColorRuleConfig(name="Brand Blue", hex="#1A2B4C")],
        fonts=[FontRuleConfig(family="Inter")],
    )
    engine = RuleEngine(ruleset)
    issues_by_slide = engine.evaluate_all(csm.slides)
    slide_0_issues = issues_by_slide[0]

    # Should find color and font violations
    assert any(i.rule_type == "color.off_brand" for i in slide_0_issues)
    assert any(i.rule_type == "typography.wrong_font" for i in slide_0_issues)

    # 3. Correct
    correction = CorrectionEngine()
    corrected_slide = correction.correct_slide(csm.slides[0], slide_0_issues)

    # Verify corrections applied
    text_el = [e for e in corrected_slide.elements if e.type == "text"][0]
    run = text_el.paragraphs[0].runs[0]
    assert run.color.hex == "#1A2B4C"  # color corrected
    assert run.font.family == "Inter"  # font corrected

    # 4. Export
    corrected_csm = csm.model_copy(deep=True)
    corrected_csm.slides = [corrected_slide]
    exporter = PptxExporter()
    output = exporter.export(corrected_csm)
    assert len(output) > 0

    # Verify exported PPTX has corrected content
    from pptx import Presentation as Prs
    prs = Prs(io.BytesIO(output))
    assert len(prs.slides) == 1
```

- [ ] **Step 5: Run integration test**

```bash
python -m pytest tests/integration/test_full_pipeline.py -v
```

Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add services/workers/ tests/integration/
git commit -m "feat: workers for ingestion, check, and correction + full pipeline integration test"
```

---

## Task 21: Golden Deck Test Suite

**Files:**
- Create golden deck .pptx files programmatically
- Create: `tests/golden_decks/generate_fixtures.py`
- Create: `tests/test_golden_decks.py`

- [ ] **Step 1: Write fixture generator**

```python
# tests/golden_decks/generate_fixtures.py
"""Generate test PPTX fixtures with known properties."""
import io
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor


def make_brand_violations() -> bytes:
    prs = Presentation()
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    # Wrong font
    tx = slide.shapes.add_textbox(Inches(1), Inches(1), Inches(5), Inches(0.5))
    run = tx.text_frame.paragraphs[0].add_run()
    run.text = "Wrong font here"
    run.font.name = "Comic Sans MS"
    run.font.size = Pt(20)
    run.font.color.rgb = RGBColor(0xFF, 0x00, 0x00)  # off-brand red
    # Too small font
    tx2 = slide.shapes.add_textbox(Inches(1), Inches(2), Inches(5), Inches(0.5))
    run2 = tx2.text_frame.paragraphs[0].add_run()
    run2.text = "Tiny text"
    run2.font.name = "Arial"
    run2.font.size = Pt(6)
    run2.font.color.rgb = RGBColor(0, 0, 0)
    buf = io.BytesIO()
    prs.save(buf)
    return buf.getvalue()


def make_accessibility_fails() -> bytes:
    prs = Presentation()
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    # Low contrast: light gray on white
    tx = slide.shapes.add_textbox(Inches(1), Inches(1), Inches(5), Inches(0.5))
    run = tx.text_frame.paragraphs[0].add_run()
    run.text = "Hard to read"
    run.font.name = "Arial"
    run.font.size = Pt(16)
    run.font.color.rgb = RGBColor(0xBB, 0xBB, 0xBB)
    buf = io.BytesIO()
    prs.save(buf)
    return buf.getvalue()


if __name__ == "__main__":
    with open("tests/golden_decks/brand_violations.pptx", "wb") as f:
        f.write(make_brand_violations())
    with open("tests/golden_decks/accessibility_fails.pptx", "wb") as f:
        f.write(make_accessibility_fails())
    print("Golden decks generated.")
```

- [ ] **Step 2: Write golden deck regression tests**

```python
# tests/test_golden_decks.py
from uuid import uuid4

import pytest

from services.ingestion.pptx_parser import PptxParser
from services.rules.engine import RuleEngine
from services.rules.models import BrandRulesetConfig, ColorRuleConfig, FontRuleConfig
from tests.golden_decks.generate_fixtures import make_brand_violations, make_accessibility_fails

STANDARD_RULESET = BrandRulesetConfig(
    colors=[ColorRuleConfig(name="Brand Blue", hex="#1A2B4C")],
    fonts=[FontRuleConfig(family="Inter", min_size_pt=10)],
)


def test_brand_violations_deck():
    pptx_bytes = make_brand_violations()
    csm = PptxParser().parse(pptx_bytes, uuid4())
    engine = RuleEngine(STANDARD_RULESET)
    issues = engine.evaluate_all(csm.slides)

    all_issues = [i for slide_issues in issues.values() for i in slide_issues]
    error_issues = [i for i in all_issues if i.severity == "error"]
    assert len(error_issues) >= 2  # at least color + font violations


def test_accessibility_fails_deck():
    pptx_bytes = make_accessibility_fails()
    csm = PptxParser().parse(pptx_bytes, uuid4())
    engine = RuleEngine(STANDARD_RULESET)
    issues = engine.evaluate_all(csm.slides)

    all_issues = [i for slide_issues in issues.values() for i in slide_issues]
    contrast_issues = [i for i in all_issues if i.rule_type == "a11y.low_contrast"]
    assert len(contrast_issues) >= 1
```

- [ ] **Step 3: Run golden deck tests**

```bash
python -m pytest tests/test_golden_decks.py -v
```

Expected: All pass

- [ ] **Step 4: Commit**

```bash
git add tests/
git commit -m "feat: golden deck test suite for regression testing"
```

---

## Summary

This plan delivers the **Burnish Core MVP** in 21 tasks:

| # | What | Outcome |
|---|------|---------|
| 1 | Repo scaffold + Docker | Postgres, Redis running locally |
| 2 | CSM types | Canonical Slide Model — the core data structure |
| 3 | DB models + Alembic | All tables with migrations |
| 4 | R2 storage client | File upload/download/signed URLs |
| 5 | PPTX parser | python-pptx → CSM |
| 6 | Rule engine + color evaluator | Palette compliance with Delta-E |
| 7 | Typography evaluator | Font family + size checks |
| 8 | Accessibility evaluator | WCAG AA contrast |
| 9 | Layout + content + image evaluators | Margins, density, DPI, alt text |
| 10 | Vision scorer | GPT-4o per-slide DQS |
| 11 | Correction engine + exporter | Fix issues + export corrected PPTX |
| 12 | FastAPI skeleton + auth | App entry point with Clerk placeholder |
| 13 | API routes | Decks, checks, brand, corrections endpoints |
| **14** | **Design direction + design system** | **Personas, CJMs, editorial aesthetic, DFII scored** |
| 15 | Next.js scaffold | Frontend with Clerk, Tailwind, design system |
| 16 | Upload + deck list UI | Jake's 90-second flow |
| 17 | Check results UI | DQS badges, slide previews, plain-English issues |
| 18 | Brand ruleset editor | Maya's setup flow, Priya's multi-brand switching |
| 19 | Correction view | The magic moment — side-by-side accept/fix |
| 20 | Workers (end-to-end) | Ingestion → check → correction pipeline |
| 21 | Golden deck tests | Regression suite with known fixtures |

**Reference documents:**
- `docs/personas-and-cjms.md` — 3 personas (Maya, Jake, Priya) + 3 Customer Journey Maps
- `apps/web/src/styles/design-system.md` — Fonts, colors, spacing, motion philosophy

**Not included (future plans):** Google Slides, Figma, PDF, generation engine, rephrase, version diff, CI/CD gates, browser extension, Slack/Teams bot, analytics, brand intelligence (LLM extraction).
