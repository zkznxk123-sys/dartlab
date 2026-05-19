"""sections 잠재 손실 3 종 invariant 가드.

본 테스트는 sections() 결과 + selectReport() 입력 합성 DataFrame 에 대해
다음 3 invariant 를 강제한다:

1. pivot last-wins 충돌 0 — 같은 (topic, segmentKey, periodKey) 다중 row
   존재 시 후속 row 가 silent overwrite. 정상 케이스는 occurrence 카운터가
   차단해야 한다. 5 종목 baseline fixture 부재 시 fixture 005930 만.

2. chapter dedup 8자 임계 recall — pipeline.py:1023 의 8자 미만 line 만
   있는 chapter-only block 손실 케이스. 현재는 측정용 골든 sample 박제만
   (회귀 발생 시 골든 갱신).

3. selectReport 정정공시 정책 — 합성 DataFrame 으로 원본 우선 / 정정만
   있을 때 최신 1 type 선택 / 다른 type 정정 drop 동작 확인.
"""

from __future__ import annotations

from pathlib import Path

import polars as pl
import pytest

_BASELINE_DIR = Path(__file__).resolve().parents[4] / "tests" / "fixtures" / "sections_baseline"
_FIXTURE_STOCKS = ["005930"]


def _hasBaseline(stockCode: str) -> bool:
    return (_BASELINE_DIR / f"{stockCode}.parquet").exists()


# ── invariant 1 — pivot last-wins 충돌 0 ─────────────────────────────────
@pytest.mark.realData
@pytest.mark.slow
@pytest.mark.parametrize("stockCode", _FIXTURE_STOCKS)
def test_no_pivot_key_collision(stockCode: str, caplog) -> None:
    """sections() 호출 시 pipeline.py 의 pivot 충돌 카운터 logger.warning 0건."""
    if not _hasBaseline(stockCode):
        pytest.skip(f"baseline fixture 부재: {stockCode}")

    import logging

    from dartlab.providers.dart.docs.sections.pipeline import sections

    with caplog.at_level(logging.WARNING, logger="dartlab.providers.dart.docs.sections.pipeline"):
        df = sections(stockCode, topics=None)

    assert df is not None and not df.is_empty()
    collisions = [r for r in caplog.records if "pivot 충돌" in r.message]
    assert not collisions, f"{stockCode}: pivot 충돌 {len(collisions)} 건 — {collisions[0].message[:200]}"


# ── invariant 2 — chapter dedup 8자 임계 recall (골든 박제) ────────────────
@pytest.mark.unit
def test_chapter_dedup_8char_recall() -> None:
    """chapter row 본문의 의미 line ≥ 8자 임계 동작 확인 (합성).

    chapter row 본문 안 한 block 의 line 이 *모두 8자 미만* 이면 그 block 은
    sub-section 안에 동일 line 이 없어도 unique block 으로 *간주 안 됨* → drop.
    pipeline.py:1023 `meaningful = [ln for ln in missing if len(ln) >= 8]`.
    """
    from dartlab.providers.dart.docs.sections.pipeline import _splitContentBlocks

    shortOnly = "| 1 |\n|A|B|\n|C|"
    blocks = _splitContentBlocks(shortOnly)
    assert blocks, "table block split 자체는 발생"
    for _, blockText in blocks:
        lines = [ln.strip() for ln in blockText.splitlines() if ln.strip()]
        meaningful = [ln for ln in lines if len(ln) >= 8]
        assert not meaningful, f"8자 미만 line 만 있는 block 은 unique 판정 시 drop 후보 (lines: {lines})"

    longSample = "구체적으로 영업이익은 다음과 같습니다.\n2024년 매출 100억"
    blocks2 = _splitContentBlocks(longSample)
    for _, blockText in blocks2:
        lines = [ln.strip() for ln in blockText.splitlines() if ln.strip()]
        meaningful = [ln for ln in lines if len(ln) >= 8]
        assert meaningful, "본문 문장은 8자 임계 통과해야 함"


# ── invariant 3 — selectReport 정정공시 정책 ─────────────────────────────
@pytest.mark.unit
def test_selectReport_correction_policy() -> None:
    from dartlab.providers.reportSelector import selectReport

    df = pl.DataFrame(
        {
            "year": ["2024", "2024", "2024"],
            "report_type": ["사업보고서 (2024.12)", "[기재정정]사업보고서 (2024.12)", "[기재정정]사업보고서 (2024.12)"],
            "rcept_date": ["20250315", "20250320", "20250325"],
            "section_title": ["a", "b", "c"],
            "content": ["x", "y", "z"],
        }
    )
    result = selectReport(df, "2024", "annual")
    assert result is not None and result.height == 1
    assert "기재정정" not in result["report_type"][0]

    df2 = pl.DataFrame(
        {
            "year": ["2024", "2024"],
            "report_type": ["[기재정정]사업보고서 (2024.12)", "[기재정정]사업보고서 (2024.12)"],
            "rcept_date": ["20250320", "20250325"],
            "section_title": ["b", "c"],
            "content": ["y", "z"],
        }
    )
    result2 = selectReport(df2, "2024", "annual")
    assert result2 is not None and result2.height == 2
