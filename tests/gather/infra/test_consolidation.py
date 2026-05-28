"""dartlab.gather.infra.consolidation 단위 테스트.

분기 3 종 (under/equal/over threshold) + ValueError + archive 라운드트립.
mirror 슬롯 smoke import 동행.
"""

from __future__ import annotations

import importlib

import polars as pl
import pytest

from dartlab.gather.infra import consolidation
from dartlab.gather.infra.consolidation import (
    ConsolidationResult,
    checkDiff,
)
from dartlab.gather.types import PriceSnapshot

pytestmark = pytest.mark.unit


def _makeSnap(source: str, current: float, market: str = "KR") -> PriceSnapshot:
    """헬퍼 — 최소 필드만 채운 PriceSnapshot."""
    snap = PriceSnapshot()
    snap.source = source
    snap.current = current
    snap.market = market
    return snap


def test_smoke_import() -> None:
    """모듈 import 회귀 차단."""
    importlib.import_module("dartlab.gather.infra.consolidation")


def test_checkDiff_under_threshold_not_breached() -> None:
    """diff 가 threshold 미만 → breached=False, 정량 결과 보존."""
    primary = _makeSnap("naver", 70_000)
    fallback = _makeSnap("naver_global", 70_100)  # 0.143% diff

    result = checkDiff(primary, fallback, threshold=0.005, archive=False)

    assert isinstance(result, ConsolidationResult)
    assert not result.breached
    assert result.primary_source == "naver"
    assert result.fallback_source == "naver_global"
    assert result.diff_pct == pytest.approx(100 / 70_000, rel=1e-6)


def test_checkDiff_equal_zero_diff() -> None:
    """두 소스 동일 가격 → diff_pct=0, breached=False."""
    primary = _makeSnap("naver", 50_000)
    fallback = _makeSnap("fmp", 50_000)

    result = checkDiff(primary, fallback, threshold=0.005, archive=False)

    assert result.diff_pct == 0.0
    assert not result.breached


def test_checkDiff_over_threshold_breached_no_archive() -> None:
    """diff > threshold → breached=True. archive=False 면 디스크 영향 0."""
    primary = _makeSnap("yahoo_chart", 100.0)
    fallback = _makeSnap("fmp", 102.0)  # 2% diff

    result = checkDiff(primary, fallback, threshold=0.005, archive=False)

    assert result.breached
    assert result.diff_pct == pytest.approx(0.02, rel=1e-6)
    assert result.threshold == 0.005


def test_checkDiff_zero_primary_raises() -> None:
    """primary.current=0 → ValueError (zero-division 회피)."""
    primary = _makeSnap("naver", 0.0)
    fallback = _makeSnap("fmp", 100.0)

    with pytest.raises(ValueError, match="primary.current"):
        checkDiff(primary, fallback, archive=False)


def test_archiveIncident_roundtrip(tmp_path, monkeypatch) -> None:
    """archive=True 시 parquet 1 row append + 재호출 시 누적."""
    incident_dir = tmp_path / "qualityIncidents"
    incident_file = incident_dir / "priceConsolidation.parquet"
    monkeypatch.setattr(consolidation, "_INCIDENT_DIR", incident_dir)
    monkeypatch.setattr(consolidation, "_INCIDENT_FILE", incident_file)

    primary = _makeSnap("naver", 100.0, market="KR")
    fallback = _makeSnap("fmp", 110.0, market="KR")  # 10% breach

    result1 = checkDiff(primary, fallback, threshold=0.005, archive=True)
    assert result1.breached
    assert incident_file.exists()

    df1 = pl.read_parquet(incident_file)
    assert df1.height == 1
    assert df1["primary_source"][0] == "naver"
    assert df1["fallback_source"][0] == "fmp"
    assert df1["market"][0] == "KR"

    # 두번째 호출 — append (누적 2 row)
    checkDiff(primary, fallback, threshold=0.005, archive=True)
    df2 = pl.read_parquet(incident_file)
    assert df2.height == 2


def test_archiveIncident_not_called_when_not_breached(tmp_path, monkeypatch) -> None:
    """breached=False 시 parquet 안 만들어짐."""
    incident_dir = tmp_path / "qualityIncidents"
    incident_file = incident_dir / "priceConsolidation.parquet"
    monkeypatch.setattr(consolidation, "_INCIDENT_DIR", incident_dir)
    monkeypatch.setattr(consolidation, "_INCIDENT_FILE", incident_file)

    primary = _makeSnap("naver", 70_000)
    fallback = _makeSnap("naver_global", 70_010)  # 0.014% — under 0.5%

    result = checkDiff(primary, fallback, threshold=0.005, archive=True)
    assert not result.breached
    assert not incident_file.exists()
