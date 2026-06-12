"""newsSchema 단위 — canonical 17컬럼 SSOT + coerceToCanonical 계약.

스키마 구성(base 8 + enrichment 9)·컬럼 순서·null 채움·dtype 강제·빈 입력 회귀 가드.
"""

from __future__ import annotations

import polars as pl
import pytest

from dartlab.gather.sources.newsSchema import NEWS_ARCHIVE_SCHEMA, NEWS_BASE_COLS, coerceToCanonical

pytestmark = pytest.mark.unit


def test_schema_is_17_columns_base_prefix() -> None:
    """17컬럼 superset + base 8 이 스키마 선두 순서와 일치 (출력 계약)."""
    cols = list(NEWS_ARCHIVE_SCHEMA.keys())
    assert len(cols) == 17
    assert tuple(cols[:8]) == NEWS_BASE_COLS
    assert NEWS_ARCHIVE_SCHEMA["captured_at"] == pl.Datetime("us", time_zone="UTC")
    assert NEWS_ARCHIVE_SCHEMA["themes"] == pl.List(pl.Utf8)


def test_coerce_none_and_empty_return_empty_canonical() -> None:
    """None/빈 DataFrame → canonical 17컬럼 빈 DataFrame."""
    for src in (None, pl.DataFrame()):
        out = coerceToCanonical(src)
        assert out.height == 0
        assert list(out.columns) == list(NEWS_ARCHIVE_SCHEMA.keys())
        assert dict(out.schema) == NEWS_ARCHIVE_SCHEMA


def test_coerce_fills_nulls_and_orders() -> None:
    """누락 컬럼 null 채움 + 컬럼 순서/존재값 보존 (List(Utf8) 포함)."""
    out = coerceToCanonical(pl.DataFrame({"url": ["u"], "title": ["t"]}))
    assert list(out.columns) == list(NEWS_ARCHIVE_SCHEMA.keys())
    assert out["url"][0] == "u"
    assert out["title"][0] == "t"
    assert out["description"][0] is None
    assert out["sentiment_score"][0] is None
    assert out["themes"][0] is None  # List(Utf8) null 안전


def test_coerce_casts_and_drops_extra_columns() -> None:
    """스키마 외 컬럼 drop + dtype 강제 (str date → pl.Date, strict=False)."""
    out = coerceToCanonical(pl.DataFrame({"date": ["2026-06-08"], "url": ["u"], "extra_col": [1]}))
    assert "extra_col" not in out.columns
    assert out.schema["date"] == pl.Date
    assert out["date"][0].isoformat() == "2026-06-08"
