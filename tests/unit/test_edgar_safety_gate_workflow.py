"""edgarSafetyGate.yml workflow 정적 가드 — PR-E7c plan delegated-prancing-tower.

본 PR-E7c 단독 검증:
- ``.github/workflows/edgarSafetyGate.yml`` 존재 + 핵심 step 5 종 박혀 있음
- weekly cron schedule (월요일 UTC 06:00 — edgarSync weekly 후 3 시간)
- workflow_dispatch 의 strict / tickers 입력
- sectionsParityEdgar.py CLI 호출 step
- 결과 artifact 30 일 보존 (4 주 카운터 추적)
"""

from __future__ import annotations

from pathlib import Path


def _workflowText() -> str:
    candidates = [
        Path("c:/Users/MSI/OneDrive/Desktop/sideProject/dartlab/.github/workflows/edgarSafetyGate.yml"),
        Path(".github/workflows/edgarSafetyGate.yml"),
    ]
    for p in candidates:
        if p.exists():
            return p.read_text(encoding="utf-8")
    raise AssertionError("edgarSafetyGate.yml 부재")


def test_workflow_file_exists() -> None:
    text = _workflowText()
    assert "EDGAR Safety Gate" in text


def test_workflow_has_weekly_cron() -> None:
    """월요일 06:00 UTC 측정 schedule (edgarSync weekly 후 3 시간)."""
    text = _workflowText()
    assert "0 6 * * 1" in text


def test_workflow_calls_parity_audit() -> None:
    """sectionsParityEdgar.py CLI 호출 step."""
    text = _workflowText()
    assert "tests/audit/sectionsParityEdgar.py" in text


def test_workflow_strict_input() -> None:
    """workflow_dispatch 의 strict / tickers 입력 + default strict=true."""
    text = _workflowText()
    assert "strict:" in text
    assert "tickers:" in text


def test_workflow_artifact_retention() -> None:
    """parity 결과 artifact 30 일 보존 (4 주 카운터 추적 용)."""
    text = _workflowText()
    assert "retention-days: 30" in text


def test_workflow_publishes_step_summary() -> None:
    """GitHub step summary 에 게이트 상태 게시 — 운영자가 결정 신호 보는 surface."""
    text = _workflowText()
    assert "GITHUB_STEP_SUMMARY" in text
    assert "PR-E7" in text  # 컨텍스트 명시


def test_workflow_downloads_baseline_artifacts() -> None:
    """5 baseline ticker (AAPL/MSFT/GOOGL/AMZN/NVDA) HF download step."""
    text = _workflowText()
    for ticker in ("AAPL", "MSFT", "GOOGL", "AMZN", "NVDA"):
        assert ticker in text
