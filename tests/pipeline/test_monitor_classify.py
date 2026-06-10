"""파이프라인 모니터 triage/분류/알림 단위 테스트.

``_triage`` 가 연속 2회+ 실패를 persistent(조치 필요), 첫 실패를 transient(자동 재실행)로
구분 판정하는지 + ``_classifyFailure`` 시그니처 분류 + ``_issueTitle`` 제목 + 모든 scheduled
파이프라인이 MONITORED_WORKFLOWS 에 등록됐는지(미등록=조용한 실패 가드) 검증한다.
정책: 단발이든 연속이든 **모든 실패를 알린다**(단발은 auto-rerun 병행, 가시성 우선).
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
    """최신 실패 + 직전 성공 = transient (자동 재실행 + 알림 — 단발도 surface)."""
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


# ─── _issueTitle (연속 vs 단발 표기) ──────────────────────────────────


def test_issue_title_persistent():
    """연속 실패 있으면 'Pipeline failure: …' (조치 필요 톤)."""
    mod = _loadMonitor()
    title = mod._issueTitle([{"name": "Original SSOT Sync"}], [])
    assert title == "Pipeline failure: Original SSOT Sync"


def test_issue_title_transient_only():
    """단발 실패뿐이면 '(자동 재실행 중)' 표기 — 알림은 하되 심각도 구분."""
    mod = _loadMonitor()
    title = mod._issueTitle([], [{"name": "Macro Data Sync (Bulk)"}])
    assert title.startswith("Pipeline failure (자동 재실행 중):")
    assert "Macro Data Sync (Bulk)" in title


def test_issue_title_truncates_when_many():
    """워크플로우가 많아 100자 초과면 개수 요약으로 축약."""
    mod = _loadMonitor()
    many = [{"name": f"Very Long Workflow Name Number {i}"} for i in range(10)]
    title = mod._issueTitle(many, [])
    assert len(title) <= 100
    assert "10개 워크플로우" in title


# ─── MONITORED_WORKFLOWS 커버리지 (미등록 = 조용한 실패 가드) ──────────


def test_monitored_covers_core_scheduled_pipelines():
    """핵심 scheduled 파이프라인이 모두 감시목록에 — 특히 Original SSOT Sync(과거 미등록=조용한 실패)."""
    mod = _loadMonitor()
    required = {
        "Original SSOT Sync",
        "Data Sync",
        "EDGAR Data Sync (Bulk)",
        "Gov Price Sync (Bulk)",
        "Gov Index Sync (Bulk)",
        "Macro Data Sync (Bulk)",
        "News Archive Sync",
        "GDELT Sync",
        "Valuation Snapshot",
        "Search Index Delta (daily)",
        "Search Index Main (monthly)",
        "Quant Audit",
        "Update KindList",
    }
    missing = required - set(mod.MONITORED_WORKFLOWS)
    assert not missing, f"감시목록 누락(조용한 실패 위험): {missing}"
