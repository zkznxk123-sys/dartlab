"""sections() polars-only 등가 회귀.

기존 main loop (line 847~ 의 7 dict + 4 set 누적) 을 polars expression
(group_by + agg + pivot + sort) 로 치환. caller API 0 변경, 결과 DataFrame
schema/dtypes/값 동일 보장.

baseline: ``tests/fixtures/sections_baseline/{code}.parquet`` — gitignored
(40MB realData). 부재 시 skip.

마커: ``realData + slow``. parity 통과 시 본체 치환.
"""

from __future__ import annotations

from pathlib import Path

import polars as pl
import pytest

pytestmark = [pytest.mark.realData, pytest.mark.slow]

_BASELINE_DIR = Path(__file__).resolve().parents[4] / "tests" / "fixtures" / "sections_baseline"
_CANDIDATES = ["005380", "005930", "000660", "035420", "068270"]


def _hasBaseline(stockCode: str) -> bool:
    return (_BASELINE_DIR / f"{stockCode}.parquet").exists()


@pytest.mark.parametrize("stockCode", _CANDIDATES)
def test_polars_only_shape_and_schema(stockCode: str) -> None:
    """Polars-only 함수 결과의 shape + dtypes + columns 가 baseline 과 일치."""
    if not _hasBaseline(stockCode):
        pytest.skip(f"baseline fixture 부재: {stockCode}")

    from dartlab.providers.dart.docs.sections.pipeline import _sectionsPolarsOnly

    baseline = pl.read_parquet(_BASELINE_DIR / f"{stockCode}.parquet")
    result = _sectionsPolarsOnly(stockCode, None)
    assert result is not None, f"{stockCode}: polars-only 결과 None"

    # shape
    assert result.shape == baseline.shape, (
        f"{stockCode}: shape mismatch — baseline {baseline.shape} vs result {result.shape}"
    )
    # columns
    assert result.columns == baseline.columns, (
        f"{stockCode}: columns mismatch — baseline {baseline.columns[:5]}... vs result {result.columns[:5]}..."
    )
    # dtypes
    for col in baseline.columns:
        assert result.schema[col] == baseline.schema[col], (
            f"{stockCode}: dtype mismatch col={col} — baseline {baseline.schema[col]} vs result {result.schema[col]}"
        )


@pytest.mark.parametrize("stockCode", _CANDIDATES)
def test_polars_only_values_parity(stockCode: str) -> None:
    """Polars-only 함수 결과의 값이 baseline 과 완전 일치 (categorical → str 비교)."""
    if not _hasBaseline(stockCode):
        pytest.skip(f"baseline fixture 부재: {stockCode}")

    from dartlab.providers.dart.docs.sections.pipeline import _sectionsPolarsOnly

    baseline = pl.read_parquet(_BASELINE_DIR / f"{stockCode}.parquet")
    result = _sectionsPolarsOnly(stockCode, None)
    assert result is not None

    # categorical 비교는 .equals 가 까다로움 — str cast 후 비교 (값만 보면 됨)
    def _toComparable(df: pl.DataFrame) -> pl.DataFrame:
        casts = []
        for col in df.columns:
            dt = df.schema[col]
            if dt == pl.Categorical:
                casts.append(pl.col(col).cast(pl.Utf8).alias(col))
            else:
                casts.append(pl.col(col))
        return df.select(casts)

    assert _toComparable(result).equals(_toComparable(baseline)), (
        f"{stockCode}: values mismatch (categorical → str 비교 후에도)"
    )


def test_polars_only_topic_filter() -> None:
    """topics 인자 적용 시 baseline 의 해당 topic subset 과 동일."""
    stockCode = "005930"
    if not _hasBaseline(stockCode):
        pytest.skip(f"baseline fixture 부재: {stockCode}")

    from dartlab.providers.dart.docs.sections.pipeline import _sectionsPolarsOnly

    baseline = pl.read_parquet(_BASELINE_DIR / f"{stockCode}.parquet")
    topics = {"businessOverview"}
    expected = baseline.filter(pl.col("topic").cast(pl.Utf8).is_in(list(topics)))
    result = _sectionsPolarsOnly(stockCode, topics)
    assert result is not None
    assert result.shape == expected.shape, (
        f"topic filter shape mismatch — expected {expected.shape} vs result {result.shape}"
    )
