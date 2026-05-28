"""소스 간 가격 일치도 검증 — 동시 2 소스 fetch 후 |Δprice| 측정.

`SourceHealthTracker` (resilience.py) 가 *alive* 만 추적했던 빈틈을 메움 —
fallback chain 안의 두 소스가 서로 다른 가격을 줄 때 (정확도 drift) 감지하고
`data/qualityIncidents/` parquet 에 박제. circuit breaker 와 직교 (alive 와 별개).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import polars as pl

from ..types import PriceSnapshot

log = logging.getLogger(__name__)

_INCIDENT_DIR = Path("data/qualityIncidents")
_INCIDENT_FILE = _INCIDENT_DIR / "priceConsolidation.parquet"

DEFAULT_THRESHOLD = 0.005  # 0.5% — 글로벌 거래소 normal noise 상한


@dataclass(frozen=True, slots=True)
class ConsolidationResult:
    """두 source PriceSnapshot 간 일치도 결과.

    Attributes
    ----------
    primary_source : str
        1순위 소스 이름.
    fallback_source : str
        2순위 소스 이름.
    primary_price : float
        primary current price.
    fallback_price : float
        fallback current price.
    diff_pct : float
        ``|primary - fallback| / primary`` (0.0~1.0+).
    breached : bool
        ``diff_pct > threshold`` 여부.
    threshold : float
        본 검증의 임계값.
    """

    primary_source: str
    fallback_source: str
    primary_price: float
    fallback_price: float
    diff_pct: float
    breached: bool
    threshold: float


def checkDiff(
    primary: PriceSnapshot,
    fallback: PriceSnapshot,
    *,
    threshold: float = DEFAULT_THRESHOLD,
    archive: bool = True,
) -> ConsolidationResult:
    """두 PriceSnapshot 의 ``current`` 차이 측정 + 임계 초과 시 archive.

    Sig: ``checkDiff(primary, fallback, *, threshold=0.005, archive=True) -> ConsolidationResult``

    Capabilities: 동시 2 소스 일치도 정량화 + threshold 초과 시 logger.warning + parquet append.
    AIContext: ``sources/price.fetch(consolidate=True)`` 의 backend — health alive 와 직교 검증.
    Guide: 임계값 0.5% 는 글로벌 거래소 noise 상한. KR/US 시장 동일.
    When: fallback chain 첫 2 source 가 모두 성공 응답한 경우.
    How: ``|primary.current - fallback.current| / primary.current`` → threshold 비교 →
        breached 면 ``_archiveIncident`` 호출.

    Args:
        primary: 1순위 소스 응답.
        fallback: 2순위 소스 응답.
        threshold: 임계 비율 (기본 0.005 = 0.5%). 0 이면 모든 diff 가 breached.
        archive: True 면 breached 결과를 parquet 에 박제. 테스트에서 False.

    Returns:
        ConsolidationResult — diff_pct/breached 등.

    Raises:
        ValueError: ``primary.current <= 0`` (zero-division 회피).

    Example:
        >>> result = checkDiff(primarySnap, fallbackSnap)
        >>> if result.breached: log.warning("price drift %s", result.diff_pct)

    See Also:
        ``infra.resilience.SourceHealthTracker`` — alive 추적과 직교.
        ``sources.price.fetch`` — 본 함수의 caller (consolidate=True 진입 시).
    """
    if primary.current <= 0:
        raise ValueError(f"primary.current 가 0 이하: {primary.current}")

    diff = abs(primary.current - fallback.current)
    diff_pct = diff / primary.current
    breached = diff_pct > threshold

    result = ConsolidationResult(
        primary_source=primary.source,
        fallback_source=fallback.source,
        primary_price=primary.current,
        fallback_price=fallback.current,
        diff_pct=diff_pct,
        breached=breached,
        threshold=threshold,
    )

    if breached:
        log.warning(
            "price consolidation drift %.4f%% (%s=%s vs %s=%s)",
            diff_pct * 100,
            primary.source,
            primary.current,
            fallback.source,
            fallback.current,
        )
        if archive:
            _archiveIncident(result, primary, fallback)

    return result


def _archiveIncident(
    result: ConsolidationResult,
    primary: PriceSnapshot,
    fallback: PriceSnapshot,
) -> None:
    """incident 1 row 를 ``data/qualityIncidents/priceConsolidation.parquet`` 에 append.

    Sig: ``_archiveIncident(result, primary, fallback) -> None``

    Capabilities: parquet append (existing concat or create new) + UTC timestamp + market/exchange 보존.
    AIContext: ``checkDiff`` breached 분기에서만 진입 — 사용자 직접 호출 금지.
    Guide: append-only. 기존 row 삭제/수정 금지. 파일 없으면 신규 생성.
    When: drift > threshold.
    How: 기존 parquet 있으면 read → concat → write. 없으면 신규 write.

    Args:
        result: ConsolidationResult 본체.
        primary: 1순위 snapshot (market/exchange 추출용).
        fallback: 2순위 snapshot.

    Returns:
        None.

    Raises:
        OSError: 디스크 쓰기 실패 (gather workflow 가 catch).

    Example:
        내부 헬퍼. 직접 호출 안 함.

    See Also:
        ``checkDiff`` — 본 함수의 유일한 caller.
    """
    _INCIDENT_DIR.mkdir(parents=True, exist_ok=True)

    row = pl.DataFrame(
        {
            "ts_utc": [datetime.now(timezone.utc).isoformat()],
            "market": [primary.market or ""],
            "exchange": [primary.exchange or ""],
            "primary_source": [result.primary_source],
            "fallback_source": [result.fallback_source],
            "primary_price": [result.primary_price],
            "fallback_price": [result.fallback_price],
            "diff_pct": [result.diff_pct],
            "threshold": [result.threshold],
        }
    )

    if _INCIDENT_FILE.exists():
        try:
            old = pl.read_parquet(_INCIDENT_FILE)
            row = pl.concat([old, row], how="diagonal_relaxed")
        except (OSError, pl.exceptions.PolarsError) as exc:
            # 기존 파일 corrupt → 신규로 덮어쓰기 (incident archive 는 best-effort)
            log.debug("priceConsolidation.parquet read 실패: %s — 신규 작성", exc)

    row.write_parquet(_INCIDENT_FILE)
