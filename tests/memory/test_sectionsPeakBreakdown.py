"""sections() peak RSS stage 별 breakdown 회귀 가드.

005380 baseline 실측 stage 분포 (column-by-column 변환 후):

  Stage                                  peak Δ      비고
  ──────────────────────────────────────────────────────────
  _getPrepared (loadData + 41x polars)   +285MB      parquet 압축 해제 + 51167 row
  41x main loop (topicMap 누적)           +208MB      반환 데이터 weight (회피 불가)
  freqMeta + topicKeysByTopic              +7MB      python dict
  dataColumns build loop                  +14MB
  pl.DataFrame (col-by-col 변환)           +88MB      Categorical encoding
  ──────────────────────────────────────────────────────────
  sections() 전체 cold peak              ~+595MB    회귀 한계 800MB (margin)

audit baseline (2026-04-22) 13GB → sections() 595MB = 22× / c.story() 836MB = 15.6× 감소.

마커: ``memory + slow + realData``. realData fixture 부재 시 skip.
"""

from __future__ import annotations

import gc
import sys

import polars as pl
import pytest

pytestmark = [
    pytest.mark.memory,
    pytest.mark.slow,
    pytest.mark.realData,
    pytest.mark.skipif(sys.platform != "win32", reason="Windows GetProcessMemoryInfo 전용"),
]

if sys.platform == "win32":
    import ctypes
    from ctypes import byref, sizeof, wintypes

    class _PMC(ctypes.Structure):
        _fields_ = [
            ("cb", wintypes.DWORD),
            ("pageFaultCount", wintypes.DWORD),
            ("peakWorkingSetSize", ctypes.c_size_t),
            ("workingSetSize", ctypes.c_size_t),
            ("quotaPeakPagedPoolUsage", ctypes.c_size_t),
            ("quotaPagedPoolUsage", ctypes.c_size_t),
            ("quotaPeakNonPagedPoolUsage", ctypes.c_size_t),
            ("quotaNonPagedPoolUsage", ctypes.c_size_t),
            ("pagefileUsage", ctypes.c_size_t),
            ("peakPagefileUsage", ctypes.c_size_t),
        ]

    _psapi = ctypes.WinDLL("psapi", use_last_error=True)
    _psapi.GetProcessMemoryInfo.argtypes = [wintypes.HANDLE, ctypes.POINTER(_PMC), wintypes.DWORD]
    _psapi.GetProcessMemoryInfo.restype = wintypes.BOOL
    _kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

    def _peakMb() -> float:
        pmc = _PMC()
        pmc.cb = sizeof(_PMC)
        _psapi.GetProcessMemoryInfo(_kernel32.GetCurrentProcess(), byref(pmc), pmc.cb)
        return pmc.peakWorkingSetSize / 1024 / 1024
else:

    def _peakMb() -> float:  # type: ignore[misc]
        raise RuntimeError("Windows 전용 — skipif 가 collection 단계 차단")


def _hasDocs(stockCode: str) -> bool:
    from dartlab.core.dataLoader import _dataDir

    return (_dataDir("docs") / f"{stockCode}.parquet").exists()


def _stockCode() -> str:
    return "005380"


def test_load_data_peak_under_200mb() -> None:
    """loadData(docs) — parquet 압축 해제 후 peak < 200MB.

    005380 baseline: +150MB. 회귀 한계 200MB.
    """
    if not _hasDocs(_stockCode()):
        pytest.skip("docs parquet 부재")

    from dartlab.core.dataLoader import loadData
    from dartlab.providers.dart.docs.sectionsArchive.pipeline import _SECTIONS_REQUIRED_COLS

    gc.collect()
    p0 = _peakMb()
    df = loadData(_stockCode(), sinceYear=2016, columns=_SECTIONS_REQUIRED_COLS)
    p1 = _peakMb()
    delta = p1 - p0
    assert delta < 200, (
        f"loadData peak +{delta:.0f}MB ≥ 200MB — docs parquet 컬럼 추가 또는 압축 해제 비용 증가 회귀 의심"
    )
    assert df.height > 0


def test_subsets_build_peak_under_30mb() -> None:
    """41 subsets (no iter_rows) — polars op 자체 peak < 30MB.

    005380 baseline: +2MB. 회귀 한계 30MB (jemalloc fragmentation 마진).
    """
    if not _hasDocs(_stockCode()):
        pytest.skip("docs parquet 부재")

    from dartlab.core.dataLoader import loadData
    from dartlab.providers.dart.docs.sectionsArchive.pipeline import _SECTIONS_REQUIRED_COLS
    from dartlab.providers.dart.docs.sectionsArchive.sectionsBase import REPORT_KINDS, detectContentCol
    from dartlab.providers.reportSelector import selectReport

    df = loadData(_stockCode(), sinceYear=2016, columns=_SECTIONS_REQUIRED_COLS)
    ccol = detectContentCol(df)
    years = sorted({int(y) for y in df["year"].unique().to_list()}, reverse=True)

    gc.collect()
    p0 = _peakMb()
    for year in years:
        for kind, _ in REPORT_KINDS:
            r = selectReport(df, str(year), reportKind=kind)
            if r is None or ccol not in r.columns:
                continue
            _ = (
                r.select(["section_order", "section_title", ccol])
                .with_columns(pl.col("section_title").cast(pl.Utf8))
                .filter(pl.col(ccol).is_not_null() & (pl.col(ccol).str.len_chars() > 0))
                .sort("section_order")
            )
    p1 = _peakMb()
    delta = p1 - p0
    assert delta < 30, f"41x subsets peak +{delta:.0f}MB ≥ 30MB — polars op 회귀 의심"


def test_report_rows_polars_accumulation_under_200mb() -> None:
    """41x _reportRowsToTopicRows 결과 polars DataFrame 51167 row 누적 — peak < 200MB.

    이전 list[dict] 51167 누적 +163MB → polars DataFrame 변환 후 +118MB.
    9 컬럼 list 누적 → 단일 polars 변환. 회귀 한계 200MB (variance 마진).
    """
    if not _hasDocs(_stockCode()):
        pytest.skip("docs parquet 부재")

    from dartlab.providers.dart.docs.sectionsArchive.pipeline import _reportRowsToTopicRows, iterPeriodSubsets

    subsets = list(iterPeriodSubsets(_stockCode()))

    gc.collect()
    p0 = _peakMb()
    accumulated = {}
    for periodKey, reportKind, ccol, subset in subsets:
        accumulated[(periodKey, reportKind)] = _reportRowsToTopicRows(subset, ccol)
    p1 = _peakMb()
    delta = p1 - p0
    totalRows = sum(d.height for d in accumulated.values())
    assert delta < 200, (
        f"_reportRowsToTopicRows 51167 polars row 누적 peak +{delta:.0f}MB ≥ 200MB — "
        f"polars refactor 회귀 의심 (현재 {totalRows} rows)"
    )


def test_full_sections_peak_under_800mb() -> None:
    """sections(005380) 전체 cold call peak < 800MB.

    column-by-column DataFrame 변환 후 baseline: +595MB (실측). 회귀 한계 800MB.
    audit baseline 13GB → 현 595MB = 22× 감소 가드.
    """
    if not _hasDocs(_stockCode()):
        pytest.skip("docs parquet 부재")

    from dartlab.providers.dart.docs.sectionsArchive.pipeline import clearPreparedCache, sections

    clearPreparedCache()
    gc.collect()
    p0 = _peakMb()
    df = sections(_stockCode())
    p1 = _peakMb()
    delta = p1 - p0
    assert df is not None and df.height > 0
    assert delta < 800, f"sections() cold peak +{delta:.0f}MB ≥ 800MB — column-by-column 회귀 의심"
