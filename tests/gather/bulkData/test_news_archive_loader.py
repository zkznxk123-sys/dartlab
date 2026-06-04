"""Phase A — newsHeadlines.loadNewsArchive 단위 테스트.

일별 sharding concat + asof PIT 필터 + dedup + 빈 결과 schema 회귀 가드.
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from pathlib import Path

import polars as pl
import pytest

from dartlab.gather.bulkData import newsHeadlines

pytestmark = pytest.mark.unit


def _writeDay(root: Path, market: str, day: str, rows: list[dict]) -> None:
    p = root / market / f"{day}.parquet"
    p.parent.mkdir(parents=True, exist_ok=True)
    df = pl.DataFrame(rows).with_columns(
        pl.col("date").cast(pl.Date),
        pl.col("captured_at").cast(pl.Datetime("us", time_zone="UTC")),
    )
    df.write_parquet(p)


@pytest.fixture
def isolatedArchive(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """LOCAL_ROOT 를 tmp 로 격리 + lru_cache 초기화."""
    monkeypatch.setattr(newsHeadlines, "_LOCAL_ROOT", tmp_path)
    monkeypatch.setattr(newsHeadlines, "_GDELT_ROOT", tmp_path)  # GDELT 백필 경로도 격리(실데이터 누수 차단)
    # 로컬 부재 시 _loadDay/_loadGdeltDay 가 HF loadData 로 실데이터 auto-download → 격리 깨짐.
    # loadData 를 None 으로 막아 로컬(tmp)만 보게 한다(완전 오프라인 단위 테스트).
    monkeypatch.setattr("dartlab.core.dataLoader.loadData", lambda *a, **k: None)
    newsHeadlines._loadDay.cache_clear()
    newsHeadlines._loadGdeltDay.cache_clear()
    return tmp_path


def test_loader_empty_returns_schema(isolatedArchive: Path) -> None:
    """archive 0 일 → 빈 DataFrame + 7 컬럼 schema 유지."""
    df = newsHeadlines.loadNewsArchive("2026-05-01", "2026-05-03", "KR")
    assert df.height == 0
    assert set(df.columns) == set(newsHeadlines._EMPTY_SCHEMA.keys())


def test_loader_concat_range(isolatedArchive: Path) -> None:
    """기간 [a..c] 3 일 parquet 각각 1 행 → 3 행 concat."""
    cap = datetime(2026, 5, 4, 0, 0, tzinfo=timezone.utc)
    for day, url in [("2026-05-01", "u1"), ("2026-05-02", "u2"), ("2026-05-03", "u3")]:
        _writeDay(
            isolatedArchive,
            "KR",
            day,
            [{"date": day, "title": "t", "source": "s", "url": url, "market": "KR", "query": "q", "captured_at": cap}],
        )

    df = newsHeadlines.loadNewsArchive("2026-05-01", "2026-05-03", "KR")
    assert df.height == 3
    assert sorted(df["url"].to_list()) == ["u1", "u2", "u3"]


def test_loader_asof_filter(isolatedArchive: Path) -> None:
    """asof=2026-05-02 → 그 이전 captured_at 만 유지."""
    cap1 = datetime(2026, 5, 1, 12, 0, tzinfo=timezone.utc)
    cap2 = datetime(2026, 5, 2, 12, 0, tzinfo=timezone.utc)
    cap3 = datetime(2026, 5, 3, 12, 0, tzinfo=timezone.utc)
    rows_by_day = [
        ("2026-05-01", "u1", cap1),
        ("2026-05-02", "u2", cap2),
        ("2026-05-03", "u3", cap3),
    ]
    for day, url, cap in rows_by_day:
        _writeDay(
            isolatedArchive,
            "KR",
            day,
            [{"date": day, "title": "t", "source": "s", "url": url, "market": "KR", "query": "q", "captured_at": cap}],
        )

    df = newsHeadlines.loadNewsArchive("2026-05-01", "2026-05-03", "KR", asof="2026-05-02")
    urls = set(df["url"].to_list())
    assert "u1" in urls
    assert "u3" not in urls  # captured_at 5-03 > asof 5-02


def test_loader_dedup_by_url(isolatedArchive: Path) -> None:
    """같은 url 이 두 일자 parquet 에 등장 → 1 행만 유지."""
    cap = datetime(2026, 5, 4, 0, 0, tzinfo=timezone.utc)
    _writeDay(
        isolatedArchive,
        "KR",
        "2026-05-01",
        [
            {
                "date": "2026-05-01",
                "title": "t1",
                "source": "s",
                "url": "shared",
                "market": "KR",
                "query": "q1",
                "captured_at": cap,
            }
        ],
    )
    _writeDay(
        isolatedArchive,
        "KR",
        "2026-05-02",
        [
            {
                "date": "2026-05-02",
                "title": "t2",
                "source": "s",
                "url": "shared",
                "market": "KR",
                "query": "q2",
                "captured_at": cap,
            }
        ],
    )

    df = newsHeadlines.loadNewsArchive("2026-05-01", "2026-05-02", "KR")
    assert df.height == 1
    assert df["url"][0] == "shared"


def test_loader_market_isolation(isolatedArchive: Path) -> None:
    """KR 과 US 디렉터리 격리 — KR fetch 시 US 안 섞임."""
    cap = datetime(2026, 5, 4, 0, 0, tzinfo=timezone.utc)
    _writeDay(
        isolatedArchive,
        "KR",
        "2026-05-01",
        [
            {
                "date": "2026-05-01",
                "title": "kr",
                "source": "s",
                "url": "u-kr",
                "market": "KR",
                "query": "q",
                "captured_at": cap,
            }
        ],
    )
    _writeDay(
        isolatedArchive,
        "US",
        "2026-05-01",
        [
            {
                "date": "2026-05-01",
                "title": "us",
                "source": "s",
                "url": "u-us",
                "market": "US",
                "query": "q",
                "captured_at": cap,
            }
        ],
    )

    df = newsHeadlines.loadNewsArchive("2026-05-01", "2026-05-01", "KR")
    assert df.height == 1
    assert df["url"][0] == "u-kr"
