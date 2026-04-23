"""serialize.py 단위 테스트 — 표 깨짐·한국어 단위 포맷 SSOT 검증.

Phase 2 축 A: `_dfToMarkdown` 수동 GFM 빌드 + `_formatNum` 재사용.
"""

from __future__ import annotations

import polars as pl
import pytest

pytestmark = pytest.mark.unit


def test_dfToMarkdown_smallTable_producesValidGfm():
    from dartlab.ai.tools.serialize import _dfToMarkdown

    df = pl.DataFrame(
        {
            "snakeId": ["sales", "operating_profit", "net_profit"],
            "항목": ["매출액", "영업이익", "당기순이익"],
            "2024": [4.7373e12, 5.1093e11, 2.1003e11],
            "2025": [6.1818e12, 4.8244e11, 2.829e11],
        }
    )
    out = _dfToMarkdown(df, maxRows=100)
    # shape 헤더
    assert "shape: (3, 4)" in out
    # GFM 구조: 정확히 5 줄 (header + divider + 3 data rows)
    tableLines = [l for l in out.split("\n") if l.startswith("|")]
    assert len(tableLines) == 5, f"expected 5 table lines, got {len(tableLines)}: {tableLines}"
    # divider
    assert "| --- | --- | --- | --- |" in out
    # 한국어 단위 포맷 (지수 표기 아님)
    assert "4.7조" in out or "4조" in out, f"unit format missing in {out}"
    assert "e12" not in out, "exponent notation should not appear"


def test_dfToMarkdown_largeDf_truncates():
    from dartlab.ai.tools.serialize import _dfToMarkdown

    df = pl.DataFrame({"n": list(range(50))})
    out = _dfToMarkdown(df, maxRows=10)
    assert "상위 10개" in out
    assert "전체 50개" in out
    tableLines = [l for l in out.split("\n") if l.startswith("|")]
    # header + divider + 10 rows
    assert len(tableLines) == 12


def test_dfToMarkdown_manyColumns_doesNotWrapRows():
    """컬럼 16개 이상일 때도 한 행이 한 줄을 유지해야 함 (Polars 줄바꿈 버그 방지)."""
    from dartlab.ai.tools.serialize import _dfToMarkdown

    # 16 개 컬럼
    cols = {f"col_{i}": [1.0, 2.0, 3.0] for i in range(16)}
    df = pl.DataFrame(cols)
    out = _dfToMarkdown(df, maxRows=100)
    tableLines = [l for l in out.split("\n") if l.startswith("|")]
    # header + divider + 3 rows = 5 lines
    assert len(tableLines) == 5
    # 각 행에 pipe 개수 일관
    pipeCount = tableLines[0].count("|")
    for line in tableLines:
        assert line.count("|") == pipeCount, f"pipe count mismatch: {line}"


def test_dfToMarkdown_pipeInStringEscaped():
    from dartlab.ai.tools.serialize import _dfToMarkdown

    df = pl.DataFrame({"note": ["has | pipe", "normal"]})
    out = _dfToMarkdown(df, maxRows=10)
    assert "has \\| pipe" in out


def test_dfToMarkdown_noneValuesRenderedAsDash():
    from dartlab.ai.tools.serialize import _dfToMarkdown

    df = pl.DataFrame({"a": [1.0, None, 3.0], "b": [None, 2.0, None]})
    out = _dfToMarkdown(df, maxRows=10)
    # 2행에 " - " 셀 등장
    assert "| - |" in out


def test_formatCell_usesFormatNumForNumbers():
    """숫자 경로가 aiview._formatNum 재사용 — SSOT 확인."""
    from dartlab.ai.tools.serialize import _formatCell

    # 금액 컬럼명 힌트 → 조/억 포맷
    out = _formatCell(4.7373e12, "revenue")
    assert "조" in out or "4." in out
    assert "e" not in out.lower()

    # 비율 필드
    out2 = _formatCell(12.5, "margin")
    # _isRatioField 가 margin 계열 인식하면 "12.5%" 형태
    assert "%" in out2 or "12.5" in out2


def test_formatCell_booleanAndNone():
    from dartlab.ai.tools.serialize import _formatCell

    assert _formatCell(None) == "-"
    assert _formatCell(True) == "true"
    assert _formatCell(False) == "false"


def test_tabularListToMarkdown_usesFormatNum():
    from dartlab.ai.tools.serialize import _tabularListToMarkdown

    rows = [
        {"period": "2024", "revenue": 4.7e12, "operating_income": 5.1e11},
        {"period": "2025", "revenue": 6.2e12, "operating_income": 4.8e11},
    ]
    out = _tabularListToMarkdown(rows)
    # 한국어 단위 포맷 적용
    assert "e12" not in out
    assert "조" in out or "억" in out
    # 구조 OK
    tableLines = [l for l in out.split("\n") if l.startswith("|")]
    assert len(tableLines) == 4  # header + divider + 2 rows
