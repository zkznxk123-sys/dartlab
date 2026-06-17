"""buildNaverCompanyNews.buildCompanyIndex 순수 변환 테스트 (HF 무의존).

naver 트랙(query→코드 매핑)·gdelt 트랙(__code)·track 태그·top-N·url dedup·date desc 를 검증한다.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import polars as pl
import pytest

pytestmark = pytest.mark.unit

_SCRIPT = Path(__file__).resolve().parents[2] / ".github" / "scripts" / "sync" / "buildNaverCompanyNews.py"


def _loadModule():
    spec = importlib.util.spec_from_file_location("buildNaverCompanyNews", _SCRIPT)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _naverDf(rows: list[dict]) -> pl.DataFrame:
    return pl.DataFrame(
        rows,
        schema={
            "query": pl.Utf8,
            "date": pl.Utf8,
            "title": pl.Utf8,
            "source": pl.Utf8,
            "url": pl.Utf8,
            "description": pl.Utf8,
        },
    )


def _gdeltDf(rows: list[dict]) -> pl.DataFrame:
    return pl.DataFrame(
        rows,
        schema={
            "__code": pl.Utf8,
            "date": pl.Utf8,
            "title": pl.Utf8,
            "source": pl.Utf8,
            "url": pl.Utf8,
            "description": pl.Utf8,
        },
    )


def test_naver_track_maps_seed_rows_and_tags_track() -> None:
    mod = _loadModule()
    df = _naverDf(
        [
            {
                "query": "삼성전자",
                "date": "2026-06-15",
                "title": "A",
                "source": "한경",
                "url": "u1",
                "description": "d1",
            },
            {
                "query": "삼성전자",
                "date": "2026-06-14",
                "title": "B",
                "source": "매경",
                "url": "u2",
                "description": "d2",
            },
            {"query": "금리", "date": "2026-06-15", "title": "매크로", "source": "x", "url": "u3", "description": ""},
            {"query": "카카오", "date": "2026-06-13", "title": "C", "source": "연합", "url": "u4", "description": "d4"},
        ]
    )
    out = mod.buildCompanyIndex(df, {"삼성전자": "005930", "카카오": "035720"}, perCompany=40)

    assert set(out.keys()) == {"005930", "035720"}  # 매크로(query=금리)는 코드 없어 제외
    assert [it["url"] for it in out["005930"]] == ["u1", "u2"]  # date desc
    assert out["005930"][0] == {
        "date": "2026-06-15",
        "title": "A",
        "source": "한경",
        "url": "u1",
        "description": "d1",
        "track": "naver",
    }


def test_gdelt_track_merges_with_naver() -> None:
    mod = _loadModule()
    naver = _naverDf(
        [
            {
                "query": "삼성전자",
                "date": "2026-06-15",
                "title": "최근",
                "source": "한경",
                "url": "n1",
                "description": "스니펫",
            }
        ]
    )
    gdelt = _gdeltDf(
        [
            {
                "__code": "005930",
                "date": "2021-03-02",
                "title": "과거1",
                "source": "reuters.com",
                "url": "g1",
                "description": "",
            },
            {
                "__code": "005930",
                "date": "2019-11-10",
                "title": "과거2",
                "source": "bloomberg.com",
                "url": "g2",
                "description": "",
            },
        ]
    )
    out = mod.buildCompanyIndex(naver, {"삼성전자": "005930"}, gdeltDf=gdelt, perCompany=40)

    tracks = {it["track"] for it in out["005930"]}
    assert tracks == {"naver", "gdelt"}  # 두 트랙 합쳐짐
    gd = [it for it in out["005930"] if it["track"] == "gdelt"]
    assert [it["url"] for it in gd] == ["g1", "g2"]  # date desc, description 빈값
    assert all(it["description"] == "" for it in gd)


def test_dedup_url_and_top_n_per_track() -> None:
    mod = _loadModule()
    rows = [
        {
            "query": "삼성전자",
            "date": f"2026-06-{10 + i:02d}",
            "title": f"T{i}",
            "source": "s",
            "url": f"u{i}",
            "description": "",
        }
        for i in range(5)
    ]
    rows.append(
        {"query": "삼성전자", "date": "2026-06-10", "title": "dup", "source": "s", "url": "u0", "description": ""}
    )
    out = mod.buildCompanyIndex(_naverDf(rows), {"삼성전자": "005930"}, perCompany=3)

    urls = [it["url"] for it in out["005930"]]
    assert urls == ["u4", "u3", "u2"]  # top-3 최신순, url dedup
    assert len(set(urls)) == 3


def test_shared_url_preserved_across_companies() -> None:
    """한 기사(url)가 여러 종목을 동시 언급하면 각 종목에 모두 보존 (형제 종목 커버리지 탈취 방지)."""
    mod = _loadModule()
    df = _naverDf(
        [
            {
                "query": "에코프로",
                "date": "2026-06-17",
                "title": "공유",
                "source": "s",
                "url": "shared",
                "description": "",
            },
            {
                "query": "에코프로비엠",
                "date": "2026-06-17",
                "title": "공유",
                "source": "s",
                "url": "shared",
                "description": "",
            },
            {
                "query": "에코프로비엠",
                "date": "2026-06-16",
                "title": "단독",
                "source": "s",
                "url": "own",
                "description": "",
            },
        ]
    )
    out = mod.buildCompanyIndex(df, {"에코프로": "086520", "에코프로비엠": "247540"}, perCompany=40)

    assert [it["url"] for it in out["086520"]] == ["shared"]  # 에코프로도 공유기사 보유
    assert {it["url"] for it in out["247540"]} == {"shared", "own"}  # 에코프로비엠은 공유+단독 둘 다


def test_empty_inputs() -> None:
    mod = _loadModule()
    assert mod.buildCompanyIndex(_naverDf([]), {"삼성전자": "005930"}) == {}
    df = _naverDf(
        [{"query": "삼성전자", "date": "2026-06-15", "title": "A", "source": "s", "url": "u1", "description": ""}]
    )
    assert mod.buildCompanyIndex(df, {}) == {}  # 매핑 0 → naver 트랙 비고 gdelt 없음 → {}
