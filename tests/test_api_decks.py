"""Tests for deck and check API routes.

Uses FastAPI TestClient with dependency overrides to mock DB and R2.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from io import BytesIO
from typing import Any
from unittest.mock import AsyncMock, MagicMock

from fastapi.testclient import TestClient

from services.api.deps import get_current_user, get_db
from services.api.main import app
from services.api.routers.checks import _get_r2 as _get_r2_checks
from services.api.routers.decks import _get_r2
from services.db.models.check import (
    CheckRun,
    CheckStatus,
    Issue,
    Severity,
    SlideCheckResult,
    TriggerType,
)
from services.db.models.deck import Deck, DeckStatus, SourceType

# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------

ORG_ID = str(uuid.uuid4())
USER_ID = str(uuid.uuid4())
OTHER_ORG_ID = str(uuid.uuid4())
NOW = datetime.now(UTC)


def _user(org_id: str = ORG_ID) -> dict[str, Any]:
    return {"user_id": USER_ID, "org_id": org_id, "role": "owner"}


def _make_deck(
    deck_id: uuid.UUID | None = None,
    org_id: str = ORG_ID,
    status: DeckStatus = DeckStatus.uploaded,
    deleted: bool = False,
) -> Deck:
    deck = MagicMock(spec=Deck)
    deck.id = deck_id or uuid.uuid4()
    deck.org_id = uuid.UUID(org_id)
    deck.uploaded_by = uuid.UUID(USER_ID)
    deck.name = "test.pptx"
    deck.source_type = SourceType.pptx
    deck.source_ref = f"{org_id}/decks/{deck.id}/test.pptx"
    deck.status = status
    deck.slide_count = 5
    deck.version_number = 1
    deck.csm_ref = ""
    deck.created_at = NOW
    deck.updated_at = NOW
    deck.deleted_at = NOW if deleted else None
    return deck


def _make_check_run(
    check_id: uuid.UUID | None = None,
    deck_id: uuid.UUID | None = None,
    org_id: str = ORG_ID,
    status: CheckStatus = CheckStatus.complete,
) -> CheckRun:
    cr = MagicMock(spec=CheckRun)
    cr.id = check_id or uuid.uuid4()
    cr.deck_id = deck_id or uuid.uuid4()
    cr.org_id = uuid.UUID(org_id)
    cr.ruleset_id = uuid.uuid4()
    cr.triggered_by = TriggerType.manual
    cr.status = status
    cr.dqs_overall = 72.5
    cr.issue_count_error = 3
    cr.issue_count_warning = 5
    cr.issue_count_info = 2
    cr.started_at = NOW
    cr.completed_at = NOW
    cr.created_at = NOW
    cr.slide_results = []
    return cr


def _make_slide_result(
    check_run_id: uuid.UUID,
    slide_index: int = 0,
) -> SlideCheckResult:
    sr = MagicMock(spec=SlideCheckResult)
    sr.id = uuid.uuid4()
    sr.check_run_id = check_run_id
    sr.slide_index = slide_index
    sr.dqs_slide = 68.0
    sr.thumbnail_ref = f"thumbnails/{slide_index}.png"
    sr.issues = []
    return sr


def _make_issue(slide_result_id: uuid.UUID) -> Issue:
    issue = MagicMock(spec=Issue)
    issue.id = uuid.uuid4()
    issue.slide_result_id = slide_result_id
    issue.rule_type = "color"
    issue.severity = Severity.error
    issue.message = "Off-brand color"
    issue.element_id = "txt1"
    issue.element_bbox = {"x": 0, "y": 0, "width": 100, "height": 50}
    issue.original_value = "#FF0000"
    issue.expected_value = "#1B3A6B"
    issue.correction_status = None
    return issue


def _pptx_bytes() -> bytes:
    """Minimal valid-looking bytes (real validation is in parser, not the route)."""
    return b"PK\x03\x04" + b"\x00" * 100


# ---------------------------------------------------------------------------
# Mock DB session builder
# ---------------------------------------------------------------------------


class MockScalarResult:
    """Mimics the result of session.execute() for select queries."""

    def __init__(self, value: Any = None, values: list[Any] | None = None):
        self._value = value
        self._values = values or []

    def scalar_one_or_none(self) -> Any:
        return self._value

    def scalar_one(self) -> Any:
        return self._value

    def scalars(self) -> MockScalarResult:
        return self

    def all(self) -> list[Any]:
        return self._values


TENANT_RESULT = MagicMock()  # placeholder result for set_tenant_context call


def make_mock_session(
    execute_side_effects: list[Any] | None = None,
) -> AsyncMock:
    session = AsyncMock()
    if execute_side_effects:
        # Prepend tenant context result since every route calls set_tenant_context
        all_effects = [TENANT_RESULT, *execute_side_effects]
        session.execute = AsyncMock(side_effect=all_effects)
    session.commit = AsyncMock()
    session.add = MagicMock()
    return session


# ---------------------------------------------------------------------------
# Upload tests
# ---------------------------------------------------------------------------


class TestUploadDeck:
    def test_upload_pptx_success(self) -> None:
        deck_store: list[Any] = []
        r2_mock = MagicMock()
        r2_mock.org_key = MagicMock(return_value="dev-org/decks/x/test.pptx")
        r2_mock.upload_file = MagicMock()

        session = make_mock_session()

        def capture_add(obj: Any) -> None:
            deck_store.append(obj)

        session.add = capture_add

        app.dependency_overrides[get_db] = lambda: session
        app.dependency_overrides[get_current_user] = lambda: _user()
        app.dependency_overrides[_get_r2] = lambda: r2_mock

        try:
            client = TestClient(app)
            resp = client.post(
                "/api/decks/upload",
                files={"file": ("test.pptx", BytesIO(_pptx_bytes()), "application/octet-stream")},
            )
            assert resp.status_code == 201
            body = resp.json()
            assert "deck_id" in body
            r2_mock.upload_file.assert_called_once()
        finally:
            app.dependency_overrides.clear()

    def test_upload_rejects_non_pptx(self) -> None:
        session = make_mock_session()
        app.dependency_overrides[get_db] = lambda: session
        app.dependency_overrides[get_current_user] = lambda: _user()
        app.dependency_overrides[_get_r2] = lambda: MagicMock()

        try:
            client = TestClient(app)
            resp = client.post(
                "/api/decks/upload",
                files={"file": ("doc.pdf", BytesIO(b"pdf data"), "application/pdf")},
            )
            assert resp.status_code == 400
            assert "pptx" in resp.json()["detail"].lower()
        finally:
            app.dependency_overrides.clear()

    def test_upload_rejects_empty_file(self) -> None:
        session = make_mock_session()
        app.dependency_overrides[get_db] = lambda: session
        app.dependency_overrides[get_current_user] = lambda: _user()
        app.dependency_overrides[_get_r2] = lambda: MagicMock()

        try:
            client = TestClient(app)
            resp = client.post(
                "/api/decks/upload",
                files={"file": ("test.pptx", BytesIO(b""), "application/octet-stream")},
            )
            assert resp.status_code == 400
            assert "empty" in resp.json()["detail"].lower()
        finally:
            app.dependency_overrides.clear()

    def test_upload_rejects_oversized_file(self) -> None:
        session = make_mock_session()
        app.dependency_overrides[get_db] = lambda: session
        app.dependency_overrides[get_current_user] = lambda: _user()
        app.dependency_overrides[_get_r2] = lambda: MagicMock()

        try:
            client = TestClient(app)
            # 51 MB
            big_data = b"\x00" * (51 * 1024 * 1024)
            resp = client.post(
                "/api/decks/upload",
                files={"file": ("test.pptx", BytesIO(big_data), "application/octet-stream")},
            )
            assert resp.status_code == 400
            assert "50mb" in resp.json()["detail"].lower()
        finally:
            app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# List decks tests
# ---------------------------------------------------------------------------


class TestListDecks:
    def test_list_decks_empty(self) -> None:
        session = make_mock_session(
            execute_side_effects=[
                MockScalarResult(value=0),  # count query
                MockScalarResult(values=[]),  # select query
            ]
        )
        app.dependency_overrides[get_db] = lambda: session
        app.dependency_overrides[get_current_user] = lambda: _user()

        try:
            client = TestClient(app)
            resp = client.get("/api/decks")
            assert resp.status_code == 200
            body = resp.json()
            assert body["total"] == 0
            assert body["items"] == []
        finally:
            app.dependency_overrides.clear()

    def test_list_decks_returns_items(self) -> None:
        decks = [_make_deck(), _make_deck()]
        session = make_mock_session(
            execute_side_effects=[
                MockScalarResult(value=2),
                MockScalarResult(values=decks),
            ]
        )
        app.dependency_overrides[get_db] = lambda: session
        app.dependency_overrides[get_current_user] = lambda: _user()

        try:
            client = TestClient(app)
            resp = client.get("/api/decks?page=1&page_size=10")
            assert resp.status_code == 200
            body = resp.json()
            assert body["total"] == 2
            assert len(body["items"]) == 2
        finally:
            app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Get deck tests
# ---------------------------------------------------------------------------


class TestGetDeck:
    def test_get_deck_found(self) -> None:
        deck = _make_deck()
        session = make_mock_session(
            execute_side_effects=[MockScalarResult(value=deck)]
        )
        app.dependency_overrides[get_db] = lambda: session
        app.dependency_overrides[get_current_user] = lambda: _user()

        try:
            client = TestClient(app)
            resp = client.get(f"/api/decks/{deck.id}")
            assert resp.status_code == 200
            body = resp.json()
            assert body["id"] == str(deck.id)
            assert body["name"] == "test.pptx"
        finally:
            app.dependency_overrides.clear()

    def test_get_deck_not_found(self) -> None:
        session = make_mock_session(
            execute_side_effects=[MockScalarResult(value=None)]
        )
        app.dependency_overrides[get_db] = lambda: session
        app.dependency_overrides[get_current_user] = lambda: _user()

        try:
            client = TestClient(app)
            resp = client.get(f"/api/decks/{uuid.uuid4()}")
            assert resp.status_code == 404
        finally:
            app.dependency_overrides.clear()

    def test_get_deck_wrong_org_returns_404(self) -> None:
        session = make_mock_session(
            execute_side_effects=[MockScalarResult(value=None)]
        )
        app.dependency_overrides[get_db] = lambda: session
        app.dependency_overrides[get_current_user] = lambda: _user(OTHER_ORG_ID)

        try:
            client = TestClient(app)
            resp = client.get(f"/api/decks/{uuid.uuid4()}")
            assert resp.status_code == 404
        finally:
            app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Delete deck tests
# ---------------------------------------------------------------------------


class TestDeleteDeck:
    def test_delete_deck_success(self) -> None:
        deck = _make_deck()
        session = make_mock_session(
            execute_side_effects=[MockScalarResult(value=deck)]
        )
        app.dependency_overrides[get_db] = lambda: session
        app.dependency_overrides[get_current_user] = lambda: _user()

        try:
            client = TestClient(app)
            resp = client.delete(f"/api/decks/{deck.id}")
            assert resp.status_code == 204
        finally:
            app.dependency_overrides.clear()

    def test_delete_deck_not_found(self) -> None:
        session = make_mock_session(
            execute_side_effects=[MockScalarResult(value=None)]
        )
        app.dependency_overrides[get_db] = lambda: session
        app.dependency_overrides[get_current_user] = lambda: _user()

        try:
            client = TestClient(app)
            resp = client.delete(f"/api/decks/{uuid.uuid4()}")
            assert resp.status_code == 404
        finally:
            app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Check trigger tests
# ---------------------------------------------------------------------------


class TestTriggerCheck:
    def test_trigger_check_success(self) -> None:
        deck = _make_deck()
        ruleset = MagicMock()
        ruleset.id = uuid.uuid4()
        ruleset.is_active = True

        session = make_mock_session(
            execute_side_effects=[
                MockScalarResult(value=deck),    # deck lookup
                MockScalarResult(value=ruleset),  # ruleset lookup
            ]
        )
        app.dependency_overrides[get_db] = lambda: session
        app.dependency_overrides[get_current_user] = lambda: _user()

        try:
            client = TestClient(app)
            resp = client.post(f"/api/decks/{deck.id}/check")
            assert resp.status_code == 201
            body = resp.json()
            assert "check_run_id" in body
            assert body["status"] == "queued"
        finally:
            app.dependency_overrides.clear()

    def test_trigger_check_deck_not_found(self) -> None:
        session = make_mock_session(
            execute_side_effects=[MockScalarResult(value=None)]
        )
        app.dependency_overrides[get_db] = lambda: session
        app.dependency_overrides[get_current_user] = lambda: _user()

        try:
            client = TestClient(app)
            resp = client.post(f"/api/decks/{uuid.uuid4()}/check")
            assert resp.status_code == 404
        finally:
            app.dependency_overrides.clear()

    def test_trigger_check_no_ruleset(self) -> None:
        deck = _make_deck()
        session = make_mock_session(
            execute_side_effects=[
                MockScalarResult(value=deck),
                MockScalarResult(value=None),  # no active ruleset
            ]
        )
        app.dependency_overrides[get_db] = lambda: session
        app.dependency_overrides[get_current_user] = lambda: _user()

        try:
            client = TestClient(app)
            resp = client.post(f"/api/decks/{deck.id}/check")
            assert resp.status_code == 400
            assert "ruleset" in resp.json()["detail"].lower()
        finally:
            app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Get check run tests
# ---------------------------------------------------------------------------


class TestGetCheckRun:
    def test_get_check_run_with_slides(self) -> None:
        cr = _make_check_run()
        sr0 = _make_slide_result(cr.id, slide_index=0)
        sr1 = _make_slide_result(cr.id, slide_index=1)
        cr.slide_results = [sr1, sr0]  # out of order to test sorting

        r2_mock = MagicMock()
        r2_mock.get_signed_url = MagicMock(side_effect=lambda key: f"https://signed/{key}")

        session = make_mock_session(
            execute_side_effects=[MockScalarResult(value=cr)]
        )
        app.dependency_overrides[get_db] = lambda: session
        app.dependency_overrides[get_current_user] = lambda: _user()
        app.dependency_overrides[_get_r2_checks] = lambda: r2_mock

        try:
            client = TestClient(app)
            resp = client.get(f"/api/checks/{cr.id}")
            assert resp.status_code == 200
            body = resp.json()
            assert body["dqs_overall"] == 72.5
            assert body["issue_count_error"] == 3
            assert len(body["slides"]) == 2
            assert body["slides"][0]["slide_index"] == 0
            assert body["slides"][1]["slide_index"] == 1
            assert body["slides"][0]["thumbnail_url"].startswith("https://signed/")
        finally:
            app.dependency_overrides.clear()

    def test_get_check_run_not_found(self) -> None:
        session = make_mock_session(
            execute_side_effects=[MockScalarResult(value=None)]
        )
        app.dependency_overrides[get_db] = lambda: session
        app.dependency_overrides[get_current_user] = lambda: _user()

        try:
            client = TestClient(app)
            resp = client.get(f"/api/checks/{uuid.uuid4()}")
            assert resp.status_code == 404
        finally:
            app.dependency_overrides.clear()

    def test_get_check_run_wrong_org(self) -> None:
        session = make_mock_session(
            execute_side_effects=[MockScalarResult(value=None)]
        )
        app.dependency_overrides[get_db] = lambda: session
        app.dependency_overrides[get_current_user] = lambda: _user(OTHER_ORG_ID)

        try:
            client = TestClient(app)
            resp = client.get(f"/api/checks/{uuid.uuid4()}")
            assert resp.status_code == 404
        finally:
            app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Get slide issues tests
# ---------------------------------------------------------------------------


class TestGetSlideIssues:
    def test_get_slide_with_issues(self) -> None:
        cr = _make_check_run()
        sr = _make_slide_result(cr.id, slide_index=0)
        issue = _make_issue(sr.id)
        sr.issues = [issue]

        r2_mock = MagicMock()
        r2_mock.get_signed_url = MagicMock(side_effect=lambda key: f"https://signed/{key}")

        session = make_mock_session(
            execute_side_effects=[
                MockScalarResult(value=cr),   # check_run lookup
                MockScalarResult(value=sr),   # slide_result lookup
            ]
        )
        app.dependency_overrides[get_db] = lambda: session
        app.dependency_overrides[get_current_user] = lambda: _user()
        app.dependency_overrides[_get_r2_checks] = lambda: r2_mock

        try:
            client = TestClient(app)
            resp = client.get(f"/api/checks/{cr.id}/slides/0")
            assert resp.status_code == 200
            body = resp.json()
            assert body["slide_index"] == 0
            assert body["dqs_slide"] == 68.0
            assert body["thumbnail_url"].startswith("https://signed/")
            assert len(body["issues"]) == 1
            assert body["issues"][0]["rule_type"] == "color"
            assert body["issues"][0]["severity"] == "error"
            assert body["issues"][0]["element_bbox"] is not None
        finally:
            app.dependency_overrides.clear()

    def test_get_slide_not_found(self) -> None:
        cr = _make_check_run()
        session = make_mock_session(
            execute_side_effects=[
                MockScalarResult(value=cr),
                MockScalarResult(value=None),
            ]
        )
        app.dependency_overrides[get_db] = lambda: session
        app.dependency_overrides[get_current_user] = lambda: _user()

        try:
            client = TestClient(app)
            resp = client.get(f"/api/checks/{cr.id}/slides/99")
            assert resp.status_code == 404
        finally:
            app.dependency_overrides.clear()

    def test_get_slide_check_run_wrong_org(self) -> None:
        session = make_mock_session(
            execute_side_effects=[MockScalarResult(value=None)]
        )
        app.dependency_overrides[get_db] = lambda: session
        app.dependency_overrides[get_current_user] = lambda: _user(OTHER_ORG_ID)

        try:
            client = TestClient(app)
            resp = client.get(f"/api/checks/{uuid.uuid4()}/slides/0")
            assert resp.status_code == 404
        finally:
            app.dependency_overrides.clear()
