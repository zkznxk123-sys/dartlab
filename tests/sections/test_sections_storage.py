"""sectionsStorage + sectionsBuilder MVP 단위 테스트.

검증 항목:
    1. wideToLong 변환 (period 컬럼 → row, null cell drop)
    2. saveSectionsByPeriod + loadSectionsLong round-trip parity
    3. loadSectionsWide 가 원본 wide 와 schema 호환
    4. listAvailablePeriods 정렬 (newer first, annual=Q4 후)
    5. clearSectionsArtifact 디렉터리 정리

operation.sectionsRefactor 의 PR-1a 가드. MVP 단계는 *단일 content 컬럼* 유지.
다음 단계 (PR-1b) 에서 content_raw/plain/table_struct 3 분리 시 본 테스트 schema
확장 필요.
"""

from __future__ import annotations

import polars as pl
import pytest

try:
    from dartlab.providers.dart.docs.sections.sectionsBuilder import (
        clearSectionsArtifact,
        saveSectionsByPeriod,
        wideToLong,
    )
except ImportError:
    pytest.skip(
        "sections 사전빌드 파이프라인 (parked, plan snazzy-wibbling-origami §3.5 B) — "
        "sectionsBuilder 빌드/변환 함수 미완성. 완성 후 해제.",
        allow_module_level=True,
    )
from dartlab.providers.dart.docs.sections.sectionsStorage import (
    _periodSortKey,
    hasSectionsArtifact,
    listAvailablePeriods,
    loadSectionsLong,
    loadSectionsWide,
    sectionsDir,
    sectionsPath,
)

pytestmark = [pytest.mark.unit]


def _makeFixtureWide() -> pl.DataFrame:
    """5 row × 3 period wide DataFrame 픽스처. period 별 sparse cell 포함."""
    return pl.DataFrame(
        {
            "topic": ["사업의 개요", "사업의 개요", "사업의 개요", "주주 현황", "주주 현황"],
            "blockType": ["text", "table", "text", "text", "table"],
            "blockOrder": [0, 1, 2, 0, 1],
            "segmentKey": [
                "body|p:개요|occ:1",
                "table|sem:매출|occ:1",
                "body|p:연구|occ:1",
                "body|p:주주|occ:1",
                "table|sem:주식|occ:1",
            ],
            "2025Q3": ["분기 개요 본문", "| 구분 | 매출 |\n| - | - |\n| 국내 | 100 |", None, "분기 주주 본문", None],
            "2025": [
                "연간 개요 본문",
                "| 구분 | 매출 |\n| - | - |\n| 국내 | 400 |",
                "연간 연구 본문",
                "연간 주주 본문",
                "| 주주 | 지분 |\n| - | - |\n| A | 50% |",
            ],
            "2024": [
                "전년 개요 본문",
                "| 구분 | 매출 |\n| - | - |\n| 국내 | 350 |",
                "전년 연구 본문",
                "전년 주주 본문",
                "| 주주 | 지분 |\n| - | - |\n| A | 48% |",
            ],
        }
    )


def test_period_sort_key_assigns_annual_highest_rank():
    # 같은 연도 안 정렬: annual (2025-12-31 종료) 이 가장 최신 → rank 4.
    # Q1=1, Q2=2, Q3=3, annual=4. reverse=True (newer first) 시 annual 이 first.
    sortKeys = [_periodSortKey(p) for p in ["2025Q1", "2025", "2025Q3", "2024Q2", "2024"]]
    assert sortKeys == [(2025, 1), (2025, 4), (2025, 3), (2024, 2), (2024, 4)]


def test_wide_to_long_drops_null_and_empty_cells():
    wide = _makeFixtureWide()
    long = wideToLong(wide)
    # null cell (사업의 개요 / text / blockOrder=2 / 2025Q3) 는 drop
    nullDropped = long.filter(
        (pl.col("topic") == "사업의 개요") & (pl.col("blockOrder") == 2) & (pl.col("period") == "2025Q3")
    )
    assert nullDropped.height == 0
    # 정상 cell 은 보존
    valid = long.filter((pl.col("topic") == "사업의 개요") & (pl.col("blockOrder") == 0) & (pl.col("period") == "2025"))
    assert valid.height == 1
    assert valid["content"][0] == "연간 개요 본문"


def test_wide_to_long_preserves_meta_columns():
    wide = _makeFixtureWide()
    long = wideToLong(wide)
    expectedMeta = {"topic", "blockType", "blockOrder", "segmentKey"}
    assert expectedMeta.issubset(set(long.columns))
    assert "period" in long.columns
    assert "content" in long.columns


def test_save_and_load_long_round_trip(tmp_path, monkeypatch):
    # _cfg.dataDir 를 tmp_path 로 격리. 5 baseline docs.parquet 무관 stand-alone test.
    monkeypatch.setattr("dartlab.config.dataDir", str(tmp_path))
    code = "TEST01"
    wide = _makeFixtureWide()

    saved = saveSectionsByPeriod(code, wide)
    assert set(saved.keys()) == {"2025Q3", "2025", "2024"}

    available = listAvailablePeriods(code)
    # newer first — 같은 연도 안에서 annual (12-31 종료) 이 Q3 (09-30 종료) 보다 최신.
    # rank: 2025 annual=(2025,4) > 2025Q3=(2025,3) > 2024 annual=(2024,4).
    assert available == ["2025", "2025Q3", "2024"]

    assert hasSectionsArtifact(code)

    loaded = loadSectionsLong(code)
    assert loaded is not None
    # 원본 long 과 row 수 일치 (null cell drop 후)
    expected = wideToLong(wide)
    assert loaded.height == expected.height


def test_load_wide_restores_original_schema(tmp_path, monkeypatch):
    monkeypatch.setattr("dartlab.config.dataDir", str(tmp_path))
    code = "TEST02"
    wide = _makeFixtureWide()
    saveSectionsByPeriod(code, wide)

    loaded = loadSectionsWide(code)
    assert loaded is not None
    # period 컬럼 모두 복원
    assert {"2025Q3", "2025", "2024"}.issubset(set(loaded.columns))
    # meta 컬럼 보존
    assert {"topic", "blockType", "blockOrder", "segmentKey"}.issubset(set(loaded.columns))


def test_load_long_columnar_projection(tmp_path, monkeypatch):
    monkeypatch.setattr("dartlab.config.dataDir", str(tmp_path))
    code = "TEST03"
    saveSectionsByPeriod(code, _makeFixtureWide())

    # meta 컬럼만 select — content 페이지 fault 0
    metaOnly = loadSectionsLong(code, columns=["topic", "blockType", "blockOrder", "period"])
    assert metaOnly is not None
    assert "content" not in metaOnly.columns
    assert {"topic", "blockType", "blockOrder", "period"} == set(metaOnly.columns)


def test_period_filter_restricts_files(tmp_path, monkeypatch):
    monkeypatch.setattr("dartlab.config.dataDir", str(tmp_path))
    code = "TEST04"
    saveSectionsByPeriod(code, _makeFixtureWide())

    only2025 = loadSectionsLong(code, periods=["2025"])
    assert only2025 is not None
    assert set(only2025["period"].unique().to_list()) == {"2025"}


def test_clear_removes_all_period_files(tmp_path, monkeypatch):
    monkeypatch.setattr("dartlab.config.dataDir", str(tmp_path))
    code = "TEST05"
    saveSectionsByPeriod(code, _makeFixtureWide())
    assert hasSectionsArtifact(code)

    removed = clearSectionsArtifact(code)
    assert removed == 3
    assert not hasSectionsArtifact(code)
    assert not sectionsDir(code).exists()


def test_empty_wide_returns_empty_dict(tmp_path, monkeypatch):
    monkeypatch.setattr("dartlab.config.dataDir", str(tmp_path))
    code = "TEST06"
    empty = pl.DataFrame({"topic": [], "blockType": [], "blockOrder": [], "segmentKey": []})
    result = saveSectionsByPeriod(code, empty)
    assert result == {}


def test_missing_artifact_returns_none(tmp_path, monkeypatch):
    monkeypatch.setattr("dartlab.config.dataDir", str(tmp_path))
    assert loadSectionsLong("NONEXIST") is None
    assert loadSectionsWide("NONEXIST") is None
    assert not hasSectionsArtifact("NONEXIST")
    assert listAvailablePeriods("NONEXIST") == []


def test_path_helpers():
    p = sectionsPath("005930", "2025Q3")
    assert p.name == "2025Q3.parquet"
    assert p.parent.name == "005930"
