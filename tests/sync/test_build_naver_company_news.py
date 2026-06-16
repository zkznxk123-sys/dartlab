"""buildNaverCompanyNews.buildCompanyIndex 순수 변환 테스트 (HF 무의존).

종목 시드 행만 채택·코드 그룹핑·top-N·url dedup·date desc·item 스키마를 검증한다.
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


def _df(rows: list[dict]) -> pl.DataFrame:
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


def test_maps_company_seed_rows_and_groups_by_code() -> None:
    mod = _loadModule()
    df = _df(
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
            {
                "query": "금리",
                "date": "2026-06-15",
                "title": "매크로",
                "source": "x",
                "url": "u3",
                "description": "",
            },  # 매크로 키워드 → 제외
            {"query": "카카오", "date": "2026-06-13", "title": "C", "source": "연합", "url": "u4", "description": "d4"},
        ]
    )
    nameToCode = {"삼성전자": "005930", "카카오": "035720"}
    out = mod.buildCompanyIndex(df, nameToCode, perCompany=40)

    assert set(out.keys()) == {"005930", "035720"}  # 매크로(query=금리) 행은 코드 없어 제외
    assert [it["url"] for it in out["005930"]] == ["u1", "u2"]  # date desc
    assert out["005930"][0] == {"date": "2026-06-15", "title": "A", "source": "한경", "url": "u1", "description": "d1"}
    assert [it["url"] for it in out["035720"]] == ["u4"]


def test_dedup_url_and_top_n() -> None:
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
    )  # url 중복
    out = mod.buildCompanyIndex(_df(rows), {"삼성전자": "005930"}, perCompany=3)

    items = out["005930"]
    assert len(items) == 3  # top-3 (최신순)
    urls = [it["url"] for it in items]
    assert urls == ["u4", "u3", "u2"]  # date desc, dedup 으로 u0 1회만 존재(상위 3 밖)
    assert len(set(urls)) == 3


def test_empty_inputs() -> None:
    mod = _loadModule()
    assert mod.buildCompanyIndex(_df([]), {"삼성전자": "005930"}) == {}
    df = _df([{"query": "삼성전자", "date": "2026-06-15", "title": "A", "source": "s", "url": "u1", "description": ""}])
    assert mod.buildCompanyIndex(df, {}) == {}  # 매핑 0 → {}
