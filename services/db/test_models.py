from services.db.models import (
    Base,
    BrandRuleset,
    CheckRun,
    Deck,
    Issue,
    SlideCheckResult,
    User,
)
from services.db.models.check import CheckStatus, CorrectionStatus, Severity, TriggerType
from services.db.models.deck import SourceType
from services.db.models.org import OrgRole, PlanType


def test_all_models_registered_on_base():
    table_names = set(Base.metadata.tables.keys())
    expected = {
        "organizations",
        "users",
        "brand_rulesets",
        "decks",
        "check_runs",
        "slide_check_results",
        "issues",
    }
    assert expected.issubset(table_names), f"Missing tables: {expected - table_names}"


def test_org_id_on_all_tenant_models():
    """Every tenant-scoped model must have an org_id column for RLS."""
    tenant_models = [BrandRuleset, Deck, CheckRun]
    for model in tenant_models:
        columns = {c.name for c in model.__table__.columns}
        assert "org_id" in columns, f"{model.__name__} missing org_id column"


def test_user_has_org_id():
    columns = {c.name for c in User.__table__.columns}
    assert "org_id" in columns


def test_enums_defined():
    assert PlanType.free.value == "free"
    assert OrgRole.admin.value == "admin"
    assert SourceType.pptx.value == "pptx"
    assert CheckStatus.queued.value == "queued"
    assert Severity.error.value == "error"
    assert TriggerType.manual.value == "manual"
    assert CorrectionStatus.pending.value == "pending"


def test_check_run_relationships():
    """CheckRun should have slide_results relationship."""
    assert hasattr(CheckRun, "slide_results")


def test_issue_relationships():
    """Issue should have slide_result relationship."""
    assert hasattr(Issue, "slide_result")


def test_slide_check_result_relationships():
    assert hasattr(SlideCheckResult, "check_run")
    assert hasattr(SlideCheckResult, "issues")
