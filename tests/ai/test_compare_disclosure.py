"""CompareDisclosure 도구 — frame.disclosureDiff 위에 의미 분류 + chip 발급.

dartlab 의 DART 공시 시계열 parquet 자산 (tests/fixtures/dart/docs) 위에서만
성립. 005930 fixture 가 2015 ~ 2026Q1 보고서 시계열을 갖고 있음.
"""

from __future__ import annotations

from dartlab.ai.tools.compareDisclosure import compareDisclosure
from dartlab.ai.tools.registry import _SPECS, _TOOLS, CANONICAL_V2


def test_compareDisclosure_registered_as_canonical_tool() -> None:
    """등록 3 위치 (_SPECS + _TOOLS + CANONICAL_V2) 모두 노출."""
    assert "CompareDisclosure" in _SPECS
    assert "CompareDisclosure" in _TOOLS
    assert "CompareDisclosure" in CANONICAL_V2


def test_compareDisclosure_005930_yoy_returns_disclosure_ref_and_chip() -> None:
    """005930 2024.09 vs 2025.09 YoY diff — disclosureRef 발급 + chip 자동 생성."""
    result = compareDisclosure("005930", "2024.09", "2025.09")
    assert result.ok
    assert result.data is not None
    assert result.data["sectionChanged"] > 0
    assert result.data["chipText"].startswith("📋 공시 diff:")
    assert "[conf:90]" in result.data["chipText"]
    # 최소 1 ref + kind 정확
    assert result.refs and len(result.refs) == 1
    ref = result.refs[0]
    assert ref.kind == "disclosureRef"
    assert ref.payload["stockCode"] == "005930"
    assert ref.payload["periodA"] == "2024.09"
    assert ref.payload["periodB"] == "2025.09"
    assert ref.sourceType == "internal"


def test_compareDisclosure_unknown_period_returns_error_with_available_list() -> None:
    """존재하지 않는 period — error + 가용 보고서 enum 노출."""
    result = compareDisclosure("005930", "9999.99", "2025.09")
    assert not result.ok
    assert result.error == "period_not_found"
    assert "가용" in result.summary


def test_compareDisclosure_missing_stockcode_fixture_returns_error() -> None:
    """공시 본문 parquet 없는 종목 — graceful error."""
    result = compareDisclosure("999999", "2024.09", "2025.09")
    assert not result.ok
    assert result.error and result.error.startswith("docs_not_found")


def test_compareDisclosure_semantic_tags_classify_added_lines() -> None:
    """의미 분류 키워드 매칭 — sample line 안 키워드 1+ 시 tag 발급."""
    result = compareDisclosure("005930", "2024.09", "2025.09", topN=15)
    assert result.ok
    counts = result.data["semanticTagCounts"]
    # 5 카테고리 모두 키 존재 (값은 0 가능)
    for tag in ("guidanceUp", "guidanceDown", "riskAdded", "accountingChange", "businessLineShift"):
        assert tag in counts
    # 005930 fixture 의 1 년 차이 → 최소 1 카테고리 1+ 곳 분류
    assert sum(counts.values()) > 0
