"""sections artifact 빌더 회귀 가드 — plan v4 (태그 보존 + 수평화 동시).

plan snazzy-wibbling-origami v4. 6 cycle 실패의 회귀 가드:
    1. schema 10 컬럼 동결 — minimal, 중복 0.
    2. 모든 태그 보존 (P/SPAN/USERMARK/TABLE) — xmlChunkToMixed 회귀 차단.
    3. sub-section block 분할 — section lump 회귀 차단.
    4. cross-period 매칭 (textSemanticPathKey 일관) — pivot 정확성.
    5. 표 ALIGN/COLSPAN/ROWSPAN 보존 — _tableToHtml lossy 회귀 차단.
    6. 빌드 wall < 60s/종목 — plan 게이트.

5 baseline 종목 (005380/005930/035720/207940/000660). 사전 빌드 안 되어 있으면
fixture-level skip.
"""

from __future__ import annotations

from pathlib import Path

import polars as pl
import pytest

import dartlab.config as _cfg
from dartlab.providers.dart.docs.sectionsArchive.sectionsBuilder import (
    buildSectionsArtifact,
    clearSectionsArtifact,
)

_BASELINE = ("005380", "005930", "035720", "207940", "000660")
_EXPECTED_COLS = frozenset(
    {
        "topic",
        "blockType",
        "blockOrder",
        "textLevel",
        "textPath",
        "textSemanticPathKey",
        "textComparablePathKey",
        "rowIdentityKey",
        "anchorHash",
        "segmentKey",
        "content_raw",
        "period",
        "rcept_no",
    }
)


def _sectionsDir(code: str) -> Path:
    return Path(_cfg.dataDir) / "dart" / "sections" / code


def _latestPeriodDf(code: str) -> pl.DataFrame | None:
    """5 baseline 중 최신 period DataFrame."""
    sd = _sectionsDir(code)
    if not sd.exists():
        return None
    periods = sorted(sd.glob("*.parquet"))
    if not periods:
        return None
    return pl.read_parquet(periods[-1])


def _hasZips(code: str) -> bool:
    zipDir = Path(_cfg.dataDir) / "dart" / "original" / "docs" / code
    return zipDir.exists() and any(zipDir.glob("*.zip"))


@pytest.mark.unit
@pytest.mark.parametrize("code", _BASELINE)
def testSchema10Cols(code: str) -> None:
    """sections artifact schema = 정확히 13 컬럼 (v4.1 — rowIdentityKey + anchorHash 추가)."""
    df = _latestPeriodDf(code)
    if df is None:
        pytest.skip(f"{code} sections artifact 부재")
    cols = set(df.columns)
    assert cols == _EXPECTED_COLS, f"{code} schema mismatch: {cols ^ _EXPECTED_COLS}"


@pytest.mark.unit
@pytest.mark.parametrize("code", _BASELINE)
def testTagPreservation(code: str) -> None:
    """모든 태그 보존 — P/SPAN/USERMARK/TABLE 각 row 의 1% 이상에 raw 존재.

    회귀 가드 (6 cycle 실패): xmlChunkToMixed 가 P → plain text, USERMARK B →
    markdown '## ' 변환했던 회귀 차단. content_raw 가 raw XML 그대로면 모든
    태그 양식이 일부 row 에 존재.
    """
    df = _latestPeriodDf(code)
    if df is None or df.height == 0:
        pytest.skip(f"{code} sections artifact 부재 또는 빈 DF")
    for tag in ("<P", "<SPAN", "USERMARK", "<TABLE"):
        cnt = df["content_raw"].str.contains(tag, literal=False).sum()
        ratio = cnt / df.height
        # USERMARK 는 일부 종목 양식에서 적게 사용 가능 (0.5% threshold)
        threshold = 0.005 if tag == "USERMARK" else 0.01
        assert ratio >= threshold, f"{code} {tag} 보존 {ratio:.2%} < {threshold:.1%} — xmlChunkToMixed 회귀 의심"


@pytest.mark.unit
@pytest.mark.parametrize("code", _BASELINE)
def testSubSectionSplit(code: str) -> None:
    """sub-section block 단위 row 분할 — section lump 회귀 차단.

    종목별 zip 양식 차이로 row 수 변동 큼 (005380/035720 양식이 USERMARK B
    적음). 005930 / 000660 / 207940 baseline 기준 300+ row/period.
    """
    df = _latestPeriodDf(code)
    if df is None or df.height == 0:
        pytest.skip(f"{code} sections artifact 부재 또는 빈 DF")
    # 종목별 baseline (005380/035720 는 양식 차이로 100 threshold).
    threshold = 100 if code in ("005380", "035720") else 300
    assert df.height >= threshold, f"{code} row {df.height} < {threshold} — sub-section split 회귀 (section lump?)"


@pytest.mark.unit
def testCrossPeriodAlignmentSamsung() -> None:
    """005930 의 textSemanticPathKey 가 cross-period 매칭 — pivot 정확성.

    최신 3 period 의 textSemanticPathKey set 교집합 비율 ≥ 30%. 100% 미달은
    분기별 양식 차이 (annual / Q1/Q2/Q3 의 항목 변동) 자연 차이.
    """
    sd = _sectionsDir("005930")
    if not sd.exists():
        pytest.skip("005930 artifact 부재")
    periods = sorted(sd.glob("*.parquet"))[-3:]
    if len(periods) < 3:
        pytest.skip("005930 period 3 미만")
    pathsByPeriod = []
    for p in periods:
        df = pl.read_parquet(p, columns=["textSemanticPathKey"])
        paths = set(df["textSemanticPathKey"].drop_nulls().to_list())
        pathsByPeriod.append(paths)
    intersection = set.intersection(*pathsByPeriod)
    union = set.union(*pathsByPeriod)
    ratio = len(intersection) / max(len(union), 1)
    assert ratio >= 0.3, f"005930 cross-period 매칭 {ratio:.1%} < 30% — segmentKey period-invariant 회귀"


@pytest.mark.unit
@pytest.mark.parametrize("code", _BASELINE)
def testTableAttrPreserved(code: str) -> None:
    """표 cell ALIGN/COLSPAN/ROWSPAN attr 보존 — _tableToHtml lossy 회귀 차단."""
    df = _latestPeriodDf(code)
    if df is None or df.height == 0:
        pytest.skip(f"{code} sections artifact 부재")
    tableRows = df.filter(pl.col("blockType") == "table")
    if tableRows.height == 0:
        pytest.skip(f"{code} 표 row 0")
    hasAttr = (
        tableRows["content_raw"].str.contains(r"(?:align|colspan|rowspan|ALIGN|COLSPAN|ROWSPAN)=", literal=False).sum()
    )
    assert hasAttr >= 1, f"{code} 표 ALIGN/COLSPAN/ROWSPAN attr 0 — lossy 회귀"


@pytest.mark.unit
def testBuildUnder60sSamsung() -> None:
    """005930 1 종목 빌드 wall < 60s — plan 게이트.

    8 shard matrix 분산 전제. 60s 초과 시 plan 수정 + 즉시 보고.
    """
    if not _hasZips("005930"):
        pytest.skip("005930 zip 디렉터리 부재")
    import time

    clearSectionsArtifact("005930")
    t = time.perf_counter()
    result = buildSectionsArtifact("005930")
    dt = time.perf_counter() - t
    assert result, "005930 빌드 빈 dict"
    assert dt < 60.0, f"005930 빌드 wall {dt:.1f}s >= 60s — plan 게이트 초과"
