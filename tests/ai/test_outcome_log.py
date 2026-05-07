"""회귀 가드 — outcome_log lifecycle (pending → resolved, atomic, asymmetric, HTML separator)."""

from __future__ import annotations

import pytest


@pytest.fixture
def tmp_dartlab_home(tmp_path, monkeypatch):
    monkeypatch.setenv("DARTLAB_HOME", str(tmp_path))
    return tmp_path


@pytest.mark.unit
def test_safe_stockcode_kr_us_generic_path_traversal_blocked(tmp_dartlab_home) -> None:
    from dartlab.ai.memory.outcome_log import safe_stockcode

    assert safe_stockcode("005930") == "005930"
    assert safe_stockcode("AAPL") == "AAPL"
    assert safe_stockcode("BRK.B") == "BRK.B"
    assert safe_stockcode("foo_bar") == "foo_bar"

    for bad in ["..", "../etc", "/abs/path", "...", "a" * 17, "", "  "]:
        with pytest.raises(ValueError):
            safe_stockcode(bad)


@pytest.mark.unit
def test_store_decision_appends_pending_entry_and_idempotent(tmp_dartlab_home) -> None:
    from dartlab.ai.memory.outcome_log import get_pending_entries, store_decision

    written_first = store_decision(
        stockCode="005930",
        market="KR",
        date="2026-05-07",
        theme="Buy",
        decision_text="ROE 회복 + 메모리 업황 변곡점.",
    )
    assert written_first is True

    written_again = store_decision(
        stockCode="005930",
        market="KR",
        date="2026-05-07",
        theme="Buy",
        decision_text="중복 호출 — idempotency guard.",
    )
    assert written_again is False

    entries = get_pending_entries("005930", market="KR")
    assert len(entries) == 1
    assert entries[0].decision.startswith("ROE 회복")


@pytest.mark.unit
def test_batch_update_with_outcomes_atomic_rewrite_pending_to_resolved(tmp_dartlab_home) -> None:
    from dartlab.ai.memory.outcome_log import (
        Update,
        batch_update_with_outcomes,
        get_pending_entries,
        store_decision,
    )

    store_decision(
        stockCode="005930",
        market="KR",
        date="2026-04-01",
        theme="Buy",
        decision_text="3 개월 보유 시 + 알파 예상.",
    )
    assert len(get_pending_entries("005930")) == 1

    count = batch_update_with_outcomes(
        [
            Update(
                stockCode="005930",
                market="KR",
                date="2026-04-01",
                raw_return="+5.4%",
                alpha="+1.8%vs_KOSPI",
                holding="30d",
                reflection="Directional 정답 — 메모리 업종 회복 thesis 가 30 일 시점에서 유효.",
            )
        ]
    )
    assert count == 1
    pending = get_pending_entries("005930")
    assert len(pending) == 0


@pytest.mark.unit
def test_get_past_context_asymmetric_same_vs_cross(tmp_dartlab_home) -> None:
    from dartlab.ai.memory.outcome_log import (
        Update,
        batch_update_with_outcomes,
        get_past_context,
        store_decision,
    )

    store_decision(stockCode="005930", market="KR", date="2025-03-31", theme="Buy", decision_text="A 회사 결정.")
    batch_update_with_outcomes(
        [
            Update(
                stockCode="005930",
                market="KR",
                date="2025-03-31",
                raw_return="+3.2%",
                alpha="+1.1%vs_KOSPI",
                holding="30d",
                reflection="Same-stock reflection 본문.",
            )
        ]
    )

    store_decision(stockCode="000660", market="KR", date="2025-03-31", theme="Hold", decision_text="B 회사 결정.")
    batch_update_with_outcomes(
        [
            Update(
                stockCode="000660",
                market="KR",
                date="2025-03-31",
                raw_return="-1.0%",
                alpha="-2.5%vs_KOSPI",
                holding="30d",
                reflection="Cross-stock reflection 본문.",
            )
        ]
    )

    ctx = get_past_context("005930", market="KR", n_same=5, n_cross=3)
    assert "Same-stock reflection 본문" in ctx
    assert "DECISION: A 회사 결정" in ctx  # full format
    assert "Cross-stock reflection 본문" in ctx
    assert "DECISION: B 회사 결정" not in ctx  # cross 는 reflection 만


@pytest.mark.unit
def test_html_separator_immune_to_prose_contamination(tmp_dartlab_home) -> None:
    """`---` 같은 markdown horizontal rule 이 entry 본문 안에 있어도 split 안 깨짐."""
    from dartlab.ai.memory.outcome_log import get_pending_entries, store_decision

    store_decision(
        stockCode="005930",
        market="KR",
        date="2026-05-07",
        theme="Hold",
        decision_text="thesis 1\n---\nthesis 2 (markdown horizontal rule 포함).",
    )
    entries = get_pending_entries("005930")
    assert len(entries) == 1
    assert "thesis 1" in entries[0].decision
    assert "thesis 2" in entries[0].decision


@pytest.mark.unit
def test_atomic_write_no_dangling_tmp_file(tmp_dartlab_home) -> None:
    from dartlab.ai.memory.outcome_log import store_decision

    store_decision(
        stockCode="005930",
        market="KR",
        date="2026-05-07",
        theme="Buy",
        decision_text="atomic write 검증.",
    )
    log_dir = tmp_dartlab_home / "decisions" / "KR"
    tmp_files = [p for p in log_dir.iterdir() if p.suffix not in {".md"}]
    assert tmp_files == [], f"dangling tmp files: {tmp_files}"


@pytest.mark.unit
def test_empty_past_context_returns_empty_string(tmp_dartlab_home) -> None:
    """env 새 세션 — pending/resolved 0 건이면 빈 문자열 반환 (placeholder 부재 전제)."""
    from dartlab.ai.memory.outcome_log import get_past_context

    assert get_past_context("005930", market="KR") == ""
