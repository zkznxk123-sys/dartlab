"""파이프라인 모니터 triage/분류 단위 테스트 — P4.

단발 transient 실패(blip)에 Issue 를 만들던 alert fatigue 를 제거한 로직 가드:
``_triage`` 가 연속 2회+ 실패만 persistent(알림) 로, 첫 실패는 transient(자동 재실행)로
판정하는지 + ``_classifyFailure`` 가 실패 원인을 시그니처로 분류하는지 검증한다.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

ROOT = Path(__file__).resolve().parents[2]


def _loadMonitor():
    path = ROOT / ".github" / "scripts" / "ops" / "monitorPipeline.py"
    spec = importlib.util.spec_from_file_location("monitorPipeline", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ─── _triage (순수 로직) ──────────────────────────────────────────────


def test_triage_no_runs():
    mod = _loadMonitor()
    assert mod._triage([])["state"] == "no_runs"


def test_triage_running_skips():
    mod = _loadMonitor()
    runs = [{"conclusion": None, "status": "in_progress", "databaseId": 1, "url": "u"}]
    assert mod._triage(runs)["state"] == "running"


def test_triage_ok():
    mod = _loadMonitor()
    runs = [{"conclusion": "success", "status": "completed", "databaseId": 1, "url": "u"}]
    assert mod._triage(runs)["state"] == "ok"


def test_triage_transient_first_failure():
    """최신 실패 + 직전 성공 = transient (자동 재실행 대상, 알림 X)."""
    mod = _loadMonitor()
    runs = [
        {"conclusion": "failure", "status": "completed", "databaseId": 2, "url": "u2"},
        {"conclusion": "success", "status": "completed", "databaseId": 1, "url": "u1"},
    ]
    t = mod._triage(runs)
    assert t["state"] == "transient"
    assert t["runId"] == 2


def test_triage_persistent_two_consecutive():
    """최신+직전 모두 실패 = persistent (Issue 알림 대상)."""
    mod = _loadMonitor()
    runs = [
        {"conclusion": "failure", "status": "completed", "databaseId": 3, "url": "u3"},
        {"conclusion": "failure", "status": "completed", "databaseId": 2, "url": "u2"},
    ]
    assert mod._triage(runs)["state"] == "persistent"


def test_triage_single_run_failure_is_transient():
    """이력 1건뿐(직전 없음)인 첫 실패는 transient (직전을 success 로 간주)."""
    mod = _loadMonitor()
    runs = [{"conclusion": "failure", "status": "completed", "databaseId": 5, "url": "u"}]
    assert mod._triage(runs)["state"] == "transient"


# ─── _classifyFailure (시그니처 매칭) ─────────────────────────────────


@pytest.mark.parametrize(
    "logText,expected",
    [
        ("The hosted runner lost communication with the server", "메모리/디스크 (runner)"),
        ("HTTP 429 Too Many Requests — retry this action in 5 minutes", "HF rate-limit (429)"),
        ("The job running on runner timed out after 120 minutes", "timeout/cancelled"),
        ("Traceback: ValueError in buildScan", "code/기타"),
        ("", "unknown"),
    ],
)
def test_classifyFailure(monkeypatch, logText, expected):
    mod = _loadMonitor()
    monkeypatch.setattr(mod, "_gh", lambda *a, **k: logText)
    assert mod._classifyFailure(123) == expected
