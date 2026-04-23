"""autoEnrich YoY 주입 단위 테스트 — Phase 2 축 B-1."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.unit


def test_injectYoy_computesAllNumericFields():
    from dartlab.ai.context.aiview import _injectYoy

    hist = [
        {"period": "2025", "revenue": 6.1818e12, "operating_income": 4.8244e11, "net_income": 2.829e11},
        {"period": "2024", "revenue": 4.7373e12, "operating_income": 5.1093e11, "net_income": 2.1003e11},
    ]
    yoy = _injectYoy(hist)
    assert set(yoy.keys()) == {"revenue", "operating_income", "net_income"}
    # 매출: (6.18 - 4.74) / 4.74 ≈ +30.5%
    assert yoy["revenue"].startswith("+")
    assert "%" in yoy["revenue"]
    # 영업이익: (4.82 - 5.11) / 5.11 ≈ -5.6%
    assert yoy["operating_income"].startswith("-")


def test_injectYoy_skipsNonNumericAndPeriod():
    from dartlab.ai.context.aiview import _injectYoy

    hist = [
        {"period": "2025", "revenue": 100.0, "note": "Q4", "flag": True},
        {"period": "2024", "revenue": 90.0, "note": "prev", "flag": False},
    ]
    yoy = _injectYoy(hist)
    assert "revenue" in yoy
    assert "period" not in yoy
    assert "note" not in yoy
    assert "flag" not in yoy  # bool 제외


def test_injectYoy_signChangeReturnsNoneSkipped():
    """흑자→적자 (또는 반대) 부호 전환 시 yoy_pct 가 None → 필드 생략."""
    from dartlab.ai.context.aiview import _injectYoy

    hist = [
        {"period": "2025", "net_income": -100.0},
        {"period": "2024", "net_income": 200.0},  # 흑자 → 적자
    ]
    yoy = _injectYoy(hist)
    assert "net_income" not in yoy  # None 은 skip


def test_injectYoy_singleRowReturnsEmpty():
    from dartlab.ai.context.aiview import _injectYoy

    assert _injectYoy([{"period": "2025", "revenue": 100}]) == {}
    assert _injectYoy([]) == {}


def test_autoEnrich_historyList_includesYoyKey():
    """list[dict] 를 autoEnrich 하면 결과에 _yoy 키가 존재."""
    from dartlab.ai.context.aiview import autoEnrich

    hist = [
        {"period": "2025", "revenue": 6.2e12, "operating_income": 4.8e11},
        {"period": "2024", "revenue": 4.7e12, "operating_income": 5.1e11},
    ]
    enriched = autoEnrich(hist)
    assert isinstance(enriched, dict)
    assert "_yoy" in enriched
    assert "revenue" in enriched["_yoy"]
    # history 는 원본 유지
    assert enriched["history"] == hist


def test_autoEnrich_dictWithHistory_includesYoy():
    """{history: [...]} 형태도 _yoy 주입."""
    from dartlab.ai.context.aiview import autoEnrich

    data = {
        "history": [
            {"period": "2025", "revenue": 6.2e12},
            {"period": "2024", "revenue": 4.7e12},
        ],
    }
    enriched = autoEnrich(data)
    assert isinstance(enriched, dict)
    assert "_yoy" in enriched
    assert "revenue" in enriched["_yoy"]
