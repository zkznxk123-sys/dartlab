"""macroCycle 헬퍼 — 정규분포 CDF · 시계열 트리거 매핑.

macro/cycles/macroCycle.py 가 1055 줄이라 isolate 헬퍼 분리.
identity 보존을 위해 macroCycle.py 가 본 모듈에서 re-export 한다.

상수:
- _SIGNAL_SERIES_MAP — 신호→시계열 매핑 (14 종)

함수:
- _normCdf — 표준정규 CDF 근사 (Abramowitz & Stegun 26.2.17)
- _findFirstTriggerDates — 발현 신호의 최초 트리거 날짜 역추적
"""

from __future__ import annotations

import math

_SIGNAL_SERIES_MAP: dict[str, tuple[str, str, float]] = {
    "hy_spread_declining": ("hy_spread_3m_change", "lt", -30),
    "hy_spread_widening": ("hy_spread_3m_change", "gt", 50),
    "hy_spread_stable": ("hy_spread_3m_change", "abs_lt", 30),
    "gold_declining": ("gold_yoy", "lt", -3),
    "gold_surging": ("gold_yoy", "gt", 15),
    "long_rate_rising": ("long_rate_change", "gt", 0.2),
    "vix_stable": ("vix", "lt", 18),
    "vix_rising": ("vix", "gt", 22),
    "vix_spiking": ("vix", "gt", 30),
    "term_spread_normalizing": ("term_spread", "gt", 0.5),
    "term_spread_flattening": ("term_spread", "gt", 0),
    "term_spread_inverted": ("term_spread", "lt", 0),
    "bei_rising": ("bei_10y", "gt", 2.3),
    "bei_overheating": ("bei_10y", "gt", 2.8),
}


def _normCdf(z: float) -> float:
    """표준정규분포 CDF 근사 (|오차| < 7.5e-8). Abramowitz & Stegun 26.2.17."""
    if z < -6:
        return 0.0
    if z > 6:
        return 1.0
    a1, a2, a3, a4, a5 = 0.254829592, -0.284496736, 1.421413741, -1.453152027, 1.061405429
    p = 0.3275911
    sign = 1.0
    if z < 0:
        sign = -1.0
        z = -z
    t = 1.0 / (1.0 + p * z)
    y = 1.0 - (((((a5 * t + a4) * t) + a3) * t + a2) * t + a1) * t * math.exp(-z * z / 2)
    return 0.5 * (1.0 + sign * y)


def _findFirstTriggerDates(
    sequence: tuple[str, ...],
    signalChecks: dict[str, bool],
    history: dict[str, list[tuple[str, float]]],
) -> dict[str, str]:
    """발현된 신호의 최초 트리거 날짜를 시계열에서 역추적."""
    result: dict[str, str] = {}
    for signal_name in sequence:
        if not signalChecks.get(signal_name, False):
            continue
        mapping = _SIGNAL_SERIES_MAP.get(signal_name)
        if mapping is None:
            continue
        series_key, comparison, threshold = mapping
        ts_data = history.get(series_key)
        if not ts_data:
            continue
        for dateStr, value in ts_data:
            if comparison == "lt" and value < threshold:
                result[signal_name] = dateStr
                break
            elif comparison == "gt" and value > threshold:
                result[signal_name] = dateStr
                break
            elif comparison == "abs_lt" and abs(value) < threshold:
                result[signal_name] = dateStr
                break
    return result


__all__ = ["_SIGNAL_SERIES_MAP", "_findFirstTriggerDates", "_normCdf"]
