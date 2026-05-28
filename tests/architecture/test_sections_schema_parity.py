"""DART/EDGAR sections artifact schema parity 가드 (plan v4 PR-E10).

provider 분기 path 의 SSOT 가드. _common/sectionsSchema.PROVIDER_AGNOSTIC_COLS
(10 컬럼) 와 일치해야 분석 코드 (quant/industry/frame/scan) 가 provider 무관
동일 코드로 동작.

DART artifact 는 5 baseline 종목 기준. EDGAR 는 artifact 있을 때만 검증 (없으면
skip — EDGAR PR-E11~15 미완성 시).
"""

from __future__ import annotations

from pathlib import Path

import polars as pl
import pytest

import dartlab.config as _cfg
from dartlab.providers._common.sectionsSchema import (
    PROVIDER_AGNOSTIC_COL_NAMES,
    validateProviderAgnosticSchema,
)

_DART_BASELINE = ("005380", "005930", "035720", "207940", "000660")


def _firstDartPeriod(code: str) -> Path | None:
    sd = Path(_cfg.dataDir) / "dart" / "sections" / code
    if not sd.exists():
        return None
    periods = sorted(sd.glob("*.parquet"))
    return periods[0] if periods else None


def _firstEdgarPeriod(ticker: str) -> Path | None:
    sd = Path(_cfg.dataDir) / "edgar" / "sections" / ticker.upper()
    if not sd.exists():
        return None
    periods = sorted(sd.glob("*.parquet"))
    return periods[0] if periods else None


@pytest.mark.architecture
@pytest.mark.parametrize("code", _DART_BASELINE)
def testDartSchemaParity(code: str) -> None:
    """DART sections artifact 가 PROVIDER_AGNOSTIC_COLS (10 컬럼) parity."""
    path = _firstDartPeriod(code)
    if path is None:
        pytest.skip(f"{code} DART sections artifact 부재")
    df = pl.read_parquet(path)
    violations = validateProviderAgnosticSchema(df)
    if violations:
        msg = f"{code} DART parity 위반:\n" + "\n".join(f"  - {v}" for v in violations)
        pytest.fail(msg)


@pytest.mark.architecture
def testEdgarSchemaParity() -> None:
    """EDGAR sections artifact 가 있으면 schema parity 검증.

    EDGAR PR-E11~15 미완성 시 artifact 부재로 skip. EDGAR 빌드 후 자동 활성화.
    """
    # EDGAR 5 baseline 중 1 개라도 artifact 있으면 검증.
    tickers = ("AAPL", "MSFT", "GOOGL", "AMZN", "NVDA")
    foundAny = False
    violations: list[str] = []
    for ticker in tickers:
        path = _firstEdgarPeriod(ticker)
        if path is None:
            continue
        foundAny = True
        df = pl.read_parquet(path)
        v = validateProviderAgnosticSchema(df)
        if v:
            violations.append(f"{ticker}: " + "; ".join(v))
    if not foundAny:
        pytest.skip("EDGAR sections artifact 부재 (PR-E11~15 후 자동 활성화)")
    if violations:
        msg = "EDGAR schema parity 위반:\n" + "\n".join(f"  - {v}" for v in violations)
        pytest.fail(msg)


@pytest.mark.architecture
def testProviderAgnosticColsConstant() -> None:
    """PROVIDER_AGNOSTIC_COLS 가 정확히 10 컬럼 (plan v4 §1 #4)."""
    assert len(PROVIDER_AGNOSTIC_COL_NAMES) == 10, (
        f"PROVIDER_AGNOSTIC_COLS = {len(PROVIDER_AGNOSTIC_COL_NAMES)} 컬럼, 10 기대"
    )
    # 필수 컬럼 — drop 불가.
    required = {"topic", "blockType", "blockOrder", "textPath", "content_raw", "period"}
    assert required <= PROVIDER_AGNOSTIC_COL_NAMES, f"필수 컬럼 누락: {required - PROVIDER_AGNOSTIC_COL_NAMES}"
