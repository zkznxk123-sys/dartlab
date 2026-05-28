"""회귀 가드 — sections Priority 1 (`topic + freqScope` semanticRegistry) +
Priority 4 (analyzer instance cache) 가 미래 변경에서 깨지면 감지.

본 테스트는 sections.md line 215~220 우선순위 5 가지 중 1+4 는 이미 closed
상태인 사실을 잠근다. 실 종목 호출 없이 mock fixture 로 OOM 안전.

다종목 시뮬레이션은 stockCode 컬럼 라벨 6 개 (005930/000660/035720/035420/
373220/068270) 로 같은 sections schema 를 다중 fixture 로 만들어 group_by 가
종목 간 cross-pollute 안 되는지 검증. 실 docs 데이터 의존 0 (CLAUDE.md
메모리 안전 준수).
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.unit

import polars as pl

from dartlab.providers.dart.docs.sectionsArchive.analysis import (
    projectFreqRows,
    semanticRegistry,
    structureRegistry,
)

_TICKERS = ["005930", "000660", "035720", "035420", "373220", "068270"]


def _buildMockSections(*, ticker: str = "005930", freqScopes: list[str] | None = None) -> pl.DataFrame:
    """semanticRegistry/structureRegistry 가 요구하는 최소 schema mock.

    같은 textSemanticPathKey 를 freqScope 다양화 row 로 구성 →
    semanticRegistry 가 freqScope 별로 row 를 분리 유지하는지 검증.
    """
    scopes = freqScopes or ["annual", "quarterly", "mixed"]
    rows = []
    for idx, scope in enumerate(scopes):
        rows.append(
            {
                "topic": "businessOverview",
                "blockType": "text",
                "textStructural": True,
                "textNodeType": "body",
                "textLevel": 1,
                "freqScope": scope,
                "textSemanticPathKey": "@topic:businessOverview/매출구성",
                "textSemanticParentPathKey": "@topic:businessOverview",
                "textPathKey": "II. 사업의 내용/매출구성",
                "textParentPathKey": "II. 사업의 내용",
                "textComparablePathKey": "@topic:businessOverview/매출구성",
                "textComparableParentPathKey": "@topic:businessOverview",
                "segmentKey": f"{ticker}-seg-{idx}",
                "sourceBlockOrder": idx,
                "blockOrder": idx,
                "latestAnnualPeriod": "2024" if scope in {"annual", "mixed"} else None,
                "latestQuarterlyPeriod": "2024Q3" if scope in {"quarterly", "mixed"} else None,
            }
        )
    return pl.DataFrame(rows)


# ── projectFreqRows ──


def test_project_freq_rows_annual_keeps_annual_and_mixed_when_includeMixed_true() -> None:
    df = _buildMockSections(freqScopes=["annual", "quarterly", "mixed"])
    out = projectFreqRows(df, freqScope="annual", includeMixed=True)
    scopes = sorted(out.get_column("freqScope").unique().to_list())
    assert scopes == ["annual", "mixed"]


def test_project_freq_rows_annual_excludes_mixed_when_includeMixed_false() -> None:
    df = _buildMockSections(freqScopes=["annual", "quarterly", "mixed"])
    out = projectFreqRows(df, freqScope="annual", includeMixed=False)
    scopes = sorted(out.get_column("freqScope").unique().to_list())
    assert scopes == ["annual"]


def test_project_freq_rows_quarterly_excludes_annual() -> None:
    df = _buildMockSections(freqScopes=["annual", "quarterly", "mixed"])
    out = projectFreqRows(df, freqScope="quarterly", includeMixed=True)
    scopes = sorted(out.get_column("freqScope").unique().to_list())
    assert scopes == ["mixed", "quarterly"]


def test_project_freq_rows_all_returns_unfiltered() -> None:
    df = _buildMockSections(freqScopes=["annual", "quarterly", "mixed"])
    out = projectFreqRows(df, freqScope="all", includeMixed=True)
    assert out.height == df.height


def test_project_freq_rows_unsupported_scope_raises() -> None:
    df = _buildMockSections()
    with pytest.raises(ValueError):
        projectFreqRows(df, freqScope="weekly")


# ── semanticRegistry — Priority 1 ──


def test_semantic_registry_separates_rows_by_freqscope() -> None:
    """같은 textSemanticPathKey 라도 freqScope 가 다르면 별도 registry row."""
    df = _buildMockSections(freqScopes=["annual", "quarterly", "mixed"])
    registry = semanticRegistry(df, freqScope="all")
    scopes_in_registry = sorted(registry.get_column("freqScope").unique().to_list())
    assert scopes_in_registry == ["annual", "mixed", "quarterly"]
    # 같은 semantic path 가 freqScope 차원으로 3 group 분리
    same_semantic = registry.filter(pl.col("textSemanticPathKey") == "@topic:businessOverview/매출구성")
    assert same_semantic.height == 3


def test_semantic_registry_freqscope_filter_isolates_lane() -> None:
    df = _buildMockSections(freqScopes=["annual", "quarterly", "mixed"])
    annual_only = semanticRegistry(df, freqScope="annual", includeMixed=False)
    scopes = sorted(annual_only.get_column("freqScope").unique().to_list())
    assert scopes == ["annual"]


# ── structureRegistry — Priority 1 ──


def test_structure_registry_groups_by_freqscope() -> None:
    df = _buildMockSections(freqScopes=["annual", "quarterly", "mixed"])
    registry = structureRegistry(df, freqScope="all")
    scopes_in_registry = sorted(registry.get_column("freqScope").unique().to_list())
    assert scopes_in_registry == ["annual", "mixed", "quarterly"]


# ── 다종목 시뮬레이션 — group_by cross-pollution 회귀 ──


def test_multi_ticker_simulation_isolates_segment_keys() -> None:
    """6 종목 fixture 합쳐도 segment key 가 ticker 별 독립 유지 (회사 간 row leak 0).

    실 데이터에서 sections 는 회사별 호출이지만, 본 테스트는 group_by 가
    freqScope 차원에서 segment key 를 정확히 분리하는지 회귀 가드.
    """
    frames = [_buildMockSections(ticker=t, freqScopes=["annual"]) for t in _TICKERS]
    combined = pl.concat(frames, how="vertical")
    assert combined.height == len(_TICKERS)

    # 같은 textSemanticPathKey, 같은 freqScope=annual 이지만 segment key 6 개 모두 존재
    registry = semanticRegistry(combined, freqScope="annual", includeMixed=False)
    assert registry.height == 1  # 한 group 으로 묶임 (semantic 동일)
    seg_keys = registry.get_column("segmentKeys").to_list()[0]
    assert sorted(seg_keys) == sorted([f"{t}-seg-0" for t in _TICKERS])
    assert registry.get_column("rowCount").to_list()[0] == len(_TICKERS)


def test_multi_ticker_distinct_topics_remain_separate() -> None:
    """다른 topic 은 같은 ticker set 에서도 별개 registry row."""
    df_ticker = _buildMockSections(ticker="005930", freqScopes=["annual"])
    df_other_topic = df_ticker.with_columns(
        pl.lit("companyOverview").alias("topic"),
        pl.lit("@topic:companyOverview/연혁").alias("textSemanticPathKey"),
        pl.lit("@topic:companyOverview").alias("textSemanticParentPathKey"),
    )
    combined = pl.concat([df_ticker, df_other_topic], how="vertical")
    registry = semanticRegistry(combined, freqScope="annual", includeMixed=False)
    topics = sorted(registry.get_column("topic").unique().to_list())
    assert topics == ["businessOverview", "companyOverview"]


# ── analyzer instance cache — Priority 4 ──


class _FakeCompany:
    """SectionsAnalyzer 테스트용 minimal mock."""

    def __init__(self, sections_df: pl.DataFrame, has_docs: bool = True):
        self.stockCode = "005930"
        self._hasDocs = has_docs
        self._cache: dict = {}
        self._sections_df = sections_df

        class _Docs:
            def __init__(self, frame):
                self.sections = frame

        self.docs = _Docs(sections_df)


def test_sections_analyzer_freq_cache_hit() -> None:
    """같은 (freqScope, includeMixed) 두 번 호출 시 두 번째는 cache 반환."""
    from dartlab.providers.dart.builder.docsSectionsAnalyzer import SectionsAnalyzer

    df = _buildMockSections(freqScopes=["annual", "quarterly", "mixed"])
    fake = _FakeCompany(df)
    analyzer = SectionsAnalyzer(fake)  # type: ignore[arg-type]

    first = analyzer.sectionsFreq("annual", includeMixed=True)
    second = analyzer.sectionsFreq("annual", includeMixed=True)
    assert first is second  # identity — cache hit
    cache_keys = [k for k in fake._cache if k.startswith("_docsSectionsFreq:")]
    assert len(cache_keys) == 1


def test_sections_analyzer_semantic_registry_cache_hit() -> None:
    from dartlab.providers.dart.builder.docsSectionsAnalyzer import SectionsAnalyzer

    df = _buildMockSections(freqScopes=["annual", "quarterly", "mixed"])
    fake = _FakeCompany(df)
    analyzer = SectionsAnalyzer(fake)  # type: ignore[arg-type]

    first = analyzer.sectionsSemanticRegistry(freqScope="all")
    second = analyzer.sectionsSemanticRegistry(freqScope="all")
    assert first is second
    cache_keys = [k for k in fake._cache if k.startswith("_docsSectionsSemanticRegistry:")]
    assert len(cache_keys) == 1


def test_sections_analyzer_freq_cache_distinct_scopes_isolated() -> None:
    """다른 freqScope 두 번 호출 시 cache key 분리, 결과도 분리."""
    from dartlab.providers.dart.builder.docsSectionsAnalyzer import SectionsAnalyzer

    df = _buildMockSections(freqScopes=["annual", "quarterly", "mixed"])
    fake = _FakeCompany(df)
    analyzer = SectionsAnalyzer(fake)  # type: ignore[arg-type]

    annual = analyzer.sectionsFreq("annual", includeMixed=True)
    quarterly = analyzer.sectionsFreq("quarterly", includeMixed=True)
    cache_keys = sorted(k for k in fake._cache if k.startswith("_docsSectionsFreq:"))
    assert len(cache_keys) == 2
    assert annual.height != quarterly.height or set(annual.get_column("freqScope").to_list()) != set(
        quarterly.get_column("freqScope").to_list()
    )
