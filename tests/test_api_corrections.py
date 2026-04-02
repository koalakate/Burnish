"""Tests for correction API routes.

Uses FastAPI TestClient with dependency overrides to mock DB and R2.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock

from fastapi.testclient import TestClient

from services.api.deps import get_current_user, get_db
from services.api.main import app
from services.api.routers.corrections import _get_r2
from services.db.models.check import (
    CheckRun,
    CheckStatus,
    CorrectionStatus,
    Issue,
    Severity,
    SlideCheckResult,
    TriggerType,
)

# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------

ORG_ID = str(uuid.uuid4())
USER_ID = str(uuid.uuid4())
OTHER_ORG_ID = str(uuid.uuid4())
NOW = datetime.now(UTC)

TENANT_RESULT = MagicMock()


def _user(org_id: str = ORG_ID) -> dict[str, Any]:
    return {"user_id": USER_ID, "org_id": org_id, "role": "owner"}


def _make_issue(
    slide_result_id: uuid.UUID,
    issue_id: uuid.UUID | None = None,
    correction_status: CorrectionStatus | None = None,
    has_correction: bool = True,
) -> Issue:
    issue = MagicMock(spec=Issue)
    issue.id = issue_id or uuid.uuid4()
    issue.slide_result_id = slide_result_id
    issue.rule_type = "color"
    issue.severity = Severity.error
    issue.message = "Off-brand color"
    issue.element_id = "txt1"
    issue.element_bbox = {"x": 0, "y": 0, "width": 100, "height": 50}
    issue.original_value = "#FF0000" if has_correction else None
    issue.expected_value = "#1B3A6B" if has_correction else None
    issue.correction_applied = has_correction
    issue.correction_status = correction_status
    return issue


def _make_slide_result(
    check_run_id: uuid.UUID,
    slide_index: int = 0,
    issues: list[Issue] | None = None,
) -> SlideCheckResult:
    sr = MagicMock(spec=SlideCheckResult)
    sr.id = uuid.uuid4()
    sr.check_run_id = check_run_id
    sr.slide_index = slide_index
    sr.dqs_slide = 68.0
    sr.thumbnail_ref = f"thumbnails/{slide_index}.png"
    sr.issues = issues or []
    return sr


def _make_check_run(
    check_id: uuid.UUID | None = None,
    org_id: str = ORG_ID,
    status: CheckStatus = CheckStatus.complete,
    slide_results: list[SlideCheckResult] | None = None,
    exported_pptx_ref: str | None = None,
) -> CheckRun:
    cr = MagicMock(spec=CheckRun)
    cr.id = check_id or uuid.uuid4()
    cr.deck_id = uuid.uuid4()
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
    cr.slide_results = slide_results or []
    cr.exported_pptx_ref = exported_pptx_ref
    return cr


class MockScalarResult:
    def __init__(self, value: Any = None) -> None:
        self._value = value

    def scalar_one_or_none(self) -> Any:
        return self._value


def make_mock_session(
    execute_side_effects: list[Any] | None = None,
) -> AsyncMock:
    session = AsyncMock()
    if execute_side_effects:
        all_effects = [TENANT_RESULT, *execute_side_effects]
        session.execute = AsyncMock(side_effect=all_effects)
    session.commit = AsyncMock()
    session.add = MagicMock()
    return session


# ---------------------------------------------------------------------------
# List corrections tests
# ---------------------------------------------------------------------------


class TestListCorrections:
    def test_list_corrections_grouped_by_slide(self) -> None:
        cr = _make_check_run()
        sr0 = _make_slide_result(cr.id, slide_index=0)
        sr1 = _make_slide_result(cr.id, slide_index=1)
        issue0 = _make_issue(sr0.id)
        issue1 = _make_issue(sr1.id)
        sr0.issues = [issue0]
        sr1.issues = [issue1]
        cr.slide_results = [sr1, sr0]  # out of order to test sorting

        session = make_mock_session(
            execute_side_effects=[MockScalarResult(value=cr)]
        )
        app.dependency_overrides[get_db] = lambda: session
        app.dependency_overrides[get_current_user] = lambda: _user()

        try:
            client = TestClient(app)
            resp = client.get(f"/api/checks/{cr.id}/corrections")
            assert resp.status_code == 200
            body = resp.json()
            assert body["check_run_id"] == str(cr.id)
            assert body["total"] == 2
            assert len(body["slides"]) == 2
            assert body["slides"][0]["slide_index"] == 0
            assert body["slides"][1]["slide_index"] == 1
            assert len(body["slides"][0]["corrections"]) == 1
        finally:
            app.dependency_overrides.clear()

    def test_list_corrections_excludes_no_correction_issues(self) -> None:
        cr = _make_check_run()
        sr = _make_slide_result(cr.id, slide_index=0)
        issue_with = _make_issue(sr.id, has_correction=True)
        issue_without = _make_issue(sr.id, has_correction=False)
        sr.issues = [issue_with, issue_without]
        cr.slide_results = [sr]

        session = make_mock_session(
            execute_side_effects=[MockScalarResult(value=cr)]
        )
        app.dependency_overrides[get_db] = lambda: session
        app.dependency_overrides[get_current_user] = lambda: _user()

        try:
            client = TestClient(app)
            resp = client.get(f"/api/checks/{cr.id}/corrections")
            assert resp.status_code == 200
            body = resp.json()
            assert body["total"] == 1
        finally:
            app.dependency_overrides.clear()

    def test_list_corrections_not_found(self) -> None:
        session = make_mock_session(
            execute_side_effects=[MockScalarResult(value=None)]
        )
        app.dependency_overrides[get_db] = lambda: session
        app.dependency_overrides[get_current_user] = lambda: _user()

        try:
            client = TestClient(app)
            resp = client.get(f"/api/checks/{uuid.uuid4()}/corrections")
            assert resp.status_code == 404
        finally:
            app.dependency_overrides.clear()

    def test_list_corrections_wrong_org(self) -> None:
        session = make_mock_session(
            execute_side_effects=[MockScalarResult(value=None)]
        )
        app.dependency_overrides[get_db] = lambda: session
        app.dependency_overrides[get_current_user] = lambda: _user(OTHER_ORG_ID)

        try:
            client = TestClient(app)
            resp = client.get(f"/api/checks/{uuid.uuid4()}/corrections")
            assert resp.status_code == 404
        finally:
            app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Accept correction tests
# ---------------------------------------------------------------------------


class TestAcceptCorrection:
    def test_accept_correction_success(self) -> None:
        cr = _make_check_run()
        sr = _make_slide_result(cr.id, slide_index=0)
        issue = _make_issue(sr.id)
        sr.issues = [issue]
        cr.slide_results = [sr]

        session = make_mock_session(
            execute_side_effects=[MockScalarResult(value=cr)]
        )
        app.dependency_overrides[get_db] = lambda: session
        app.dependency_overrides[get_current_user] = lambda: _user()

        try:
            client = TestClient(app)
            resp = client.post(
                f"/api/checks/{cr.id}/corrections/{issue.id}/accept"
            )
            assert resp.status_code == 200
            body = resp.json()
            assert body["id"] == str(issue.id)
            assert body["correction_status"] == "accepted"
            assert issue.correction_status == CorrectionStatus.accepted
        finally:
            app.dependency_overrides.clear()

    def test_accept_correction_not_found(self) -> None:
        cr = _make_check_run()
        cr.slide_results = []

        session = make_mock_session(
            execute_side_effects=[MockScalarResult(value=cr)]
        )
        app.dependency_overrides[get_db] = lambda: session
        app.dependency_overrides[get_current_user] = lambda: _user()

        try:
            client = TestClient(app)
            resp = client.post(
                f"/api/checks/{cr.id}/corrections/{uuid.uuid4()}/accept"
            )
            assert resp.status_code == 404
        finally:
            app.dependency_overrides.clear()

    def test_accept_check_run_wrong_org(self) -> None:
        session = make_mock_session(
            execute_side_effects=[MockScalarResult(value=None)]
        )
        app.dependency_overrides[get_db] = lambda: session
        app.dependency_overrides[get_current_user] = lambda: _user(OTHER_ORG_ID)

        try:
            client = TestClient(app)
            resp = client.post(
                f"/api/checks/{uuid.uuid4()}/corrections/{uuid.uuid4()}/accept"
            )
            assert resp.status_code == 404
        finally:
            app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Dismiss correction tests
# ---------------------------------------------------------------------------


class TestDismissCorrection:
    def test_dismiss_correction_success(self) -> None:
        cr = _make_check_run()
        sr = _make_slide_result(cr.id, slide_index=0)
        issue = _make_issue(sr.id)
        sr.issues = [issue]
        cr.slide_results = [sr]

        session = make_mock_session(
            execute_side_effects=[MockScalarResult(value=cr)]
        )
        app.dependency_overrides[get_db] = lambda: session
        app.dependency_overrides[get_current_user] = lambda: _user()

        try:
            client = TestClient(app)
            resp = client.post(
                f"/api/checks/{cr.id}/corrections/{issue.id}/dismiss"
            )
            assert resp.status_code == 200
            body = resp.json()
            assert body["id"] == str(issue.id)
            assert body["correction_status"] == "rejected"
            assert issue.correction_status == CorrectionStatus.rejected
        finally:
            app.dependency_overrides.clear()

    def test_dismiss_correction_not_found(self) -> None:
        cr = _make_check_run()
        cr.slide_results = []

        session = make_mock_session(
            execute_side_effects=[MockScalarResult(value=cr)]
        )
        app.dependency_overrides[get_db] = lambda: session
        app.dependency_overrides[get_current_user] = lambda: _user()

        try:
            client = TestClient(app)
            resp = client.post(
                f"/api/checks/{cr.id}/corrections/{uuid.uuid4()}/dismiss"
            )
            assert resp.status_code == 404
        finally:
            app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Fix-all tests
# ---------------------------------------------------------------------------


class TestFixAll:
    def test_fix_all_accepts_pending_corrections(self) -> None:
        cr = _make_check_run(status=CheckStatus.complete)
        sr = _make_slide_result(cr.id, slide_index=0)
        issue1 = _make_issue(sr.id, has_correction=True)
        issue2 = _make_issue(sr.id, has_correction=True)
        dismissed = _make_issue(
            sr.id,
            has_correction=True,
            correction_status=CorrectionStatus.rejected,
        )
        sr.issues = [issue1, issue2, dismissed]
        cr.slide_results = [sr]

        session = make_mock_session(
            execute_side_effects=[MockScalarResult(value=cr)]
        )
        app.dependency_overrides[get_db] = lambda: session
        app.dependency_overrides[get_current_user] = lambda: _user()

        try:
            client = TestClient(app)
            resp = client.post(f"/api/checks/{cr.id}/fix-all")
            assert resp.status_code == 200
            body = resp.json()
            assert body["accepted_count"] == 2
            assert body["status"] == "accepted"
            assert issue1.correction_status == CorrectionStatus.accepted
            assert issue2.correction_status == CorrectionStatus.accepted
            assert dismissed.correction_status == CorrectionStatus.rejected
        finally:
            app.dependency_overrides.clear()

    def test_fix_all_rejects_non_complete_check(self) -> None:
        cr = _make_check_run(status=CheckStatus.running)

        session = make_mock_session(
            execute_side_effects=[MockScalarResult(value=cr)]
        )
        app.dependency_overrides[get_db] = lambda: session
        app.dependency_overrides[get_current_user] = lambda: _user()

        try:
            client = TestClient(app)
            resp = client.post(f"/api/checks/{cr.id}/fix-all")
            assert resp.status_code == 400
            assert "not complete" in resp.json()["detail"].lower()
        finally:
            app.dependency_overrides.clear()

    def test_fix_all_not_found(self) -> None:
        session = make_mock_session(
            execute_side_effects=[MockScalarResult(value=None)]
        )
        app.dependency_overrides[get_db] = lambda: session
        app.dependency_overrides[get_current_user] = lambda: _user()

        try:
            client = TestClient(app)
            resp = client.post(f"/api/checks/{uuid.uuid4()}/fix-all")
            assert resp.status_code == 404
        finally:
            app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Export tests
# ---------------------------------------------------------------------------


class TestExport:
    def test_export_download_success(self) -> None:
        cr = _make_check_run(
            exported_pptx_ref="dev-org/exports/abc.pptx"
        )
        r2_mock = MagicMock()
        r2_mock.get_signed_url = MagicMock(
            return_value="https://r2.example.com/signed/abc.pptx"
        )

        session = make_mock_session(
            execute_side_effects=[MockScalarResult(value=cr)]
        )
        app.dependency_overrides[get_db] = lambda: session
        app.dependency_overrides[get_current_user] = lambda: _user()
        app.dependency_overrides[_get_r2] = lambda: r2_mock

        try:
            client = TestClient(app)
            resp = client.get(f"/api/checks/{cr.id}/export")
            assert resp.status_code == 200
            body = resp.json()
            assert body["download_url"] == "https://r2.example.com/signed/abc.pptx"
            r2_mock.get_signed_url.assert_called_once_with(
                "dev-org/exports/abc.pptx"
            )
        finally:
            app.dependency_overrides.clear()

    def test_export_not_ready(self) -> None:
        cr = _make_check_run(exported_pptx_ref=None)

        session = make_mock_session(
            execute_side_effects=[MockScalarResult(value=cr)]
        )
        app.dependency_overrides[get_db] = lambda: session
        app.dependency_overrides[get_current_user] = lambda: _user()
        app.dependency_overrides[_get_r2] = lambda: MagicMock()

        try:
            client = TestClient(app)
            resp = client.get(f"/api/checks/{cr.id}/export")
            assert resp.status_code == 404
            assert "not available" in resp.json()["detail"].lower()
        finally:
            app.dependency_overrides.clear()

    def test_export_check_run_not_found(self) -> None:
        session = make_mock_session(
            execute_side_effects=[MockScalarResult(value=None)]
        )
        app.dependency_overrides[get_db] = lambda: session
        app.dependency_overrides[get_current_user] = lambda: _user()
        app.dependency_overrides[_get_r2] = lambda: MagicMock()

        try:
            client = TestClient(app)
            resp = client.get(f"/api/checks/{uuid.uuid4()}/export")
            assert resp.status_code == 404
        finally:
            app.dependency_overrides.clear()

    def test_export_wrong_org(self) -> None:
        session = make_mock_session(
            execute_side_effects=[MockScalarResult(value=None)]
        )
        app.dependency_overrides[get_db] = lambda: session
        app.dependency_overrides[get_current_user] = lambda: _user(OTHER_ORG_ID)
        app.dependency_overrides[_get_r2] = lambda: MagicMock()

        try:
            client = TestClient(app)
            resp = client.get(f"/api/checks/{uuid.uuid4()}/export")
            assert resp.status_code == 404
        finally:
            app.dependency_overrides.clear()
