"""Bai-Perron 구조변화 검정 — Bai & Perron (1998, 2003).

평균/분산의 다중 미지 시점 break 동시 추정.

dartlab 단순화 (single-break 우선) :
    Quandt-Andrews supremum LR test
    각 후보 시점 t* 에서 두 sub-sample 평균 차이의 t-stat
    sup over t* = sup-Wald

다중 break 는 sequential 적용 (1차 break 이후 sub-sample 에서 재검정).
"""

from __future__ import annotations

import numpy as np


def _meanBreakStat(series: np.ndarray, tStar: int) -> float:
    """t_star 시점 평균 break 의 t-stat (등분산 가정)."""
    s1 = series[:tStar]
    s2 = series[tStar:]
    if len(s1) < 5 or len(s2) < 5:
        return float("nan")
    m1, m2 = float(s1.mean()), float(s2.mean())
    v1, v2 = float(s1.var(ddof=1)), float(s2.var(ddof=1))
    n1, n2 = len(s1), len(s2)
    pooled_se = np.sqrt(v1 / n1 + v2 / n2)
    if pooled_se <= 0:
        return float("nan")
    return abs(m1 - m2) / pooled_se


def detectStructuralBreak(
    series: np.ndarray,
    *,
    trim: float = 0.15,
    threshold: float = 3.0,
) -> dict:
    """Quandt-Andrews supremum break test — 단일 미지 시점 평균 break.

    Capabilities:
        - 모든 후보 시점 t* ∈ [trim·n, (1-trim)·n] sup t-stat
        - threshold 초과 시 break 감지
        - break 시점 + 전후 평균 차이

    AIContext:
        - Sprint 6 risk — regime change 탐지
        - 한국 시장 macro 전환점, 종목 펀더멘털 shift

    Args:
        series: 1D 시계열.
        trim: 양 끝 trim 비율. 기본 ``0.15`` (양 끝 15% 제외).
        threshold: |t-stat| 임계. 기본 ``3.0`` (Andrews-Quandt 보수적).

    Returns:
        dict
            n : int
            stats : np.ndarray — 후보 시점별 t-stat
            supStat : float — 최대 t-stat
            breakIdx : int | None
            isBreak : bool
            mean_pre / mean_post : float | None
            interpretation : str

    Guide:
        Quandt-Andrews (1993) — 미지 break 시점. threshold 3.0 보수적, 2.5 완화.
        trim 0.15 표준 (양 끝 sampling bias 제거).

    When:
        Regime change 탐지 + AI 매크로/펀더멘털 shift 답변.

    How:
        후보 시점 t* sweep → 전후 평균 t-stat → sup → threshold 비교.

    Requires:
        시계열 n ≥ 30.

    Raises:
        없음 — invalid 시 error 키.

    Example:
        >>> r = detectStructuralBreak(series)
        >>> r["isBreak"]
        True

    See Also:
        - calcSADF : 단위근/버블 break
        - hamiltonRegime : Markov regime
    """
    s = np.asarray(series, dtype=np.float64)
    n = len(s)
    if n < 30:
        return {"error": "n < 30"}

    lo = max(int(n * trim), 5)
    hi = min(n - lo, n - 5)
    if hi <= lo:
        return {"error": "trim too large"}

    stats = np.full(n, np.nan, dtype=np.float64)
    for tStar in range(lo, hi):
        stats[tStar] = _meanBreakStat(s, tStar)

    valid = ~np.isnan(stats)
    if valid.sum() == 0:
        return {"error": "no valid stats"}
    sup = float(np.nanmax(stats))
    break_idx = int(np.nanargmax(stats))
    is_break = sup > threshold
    pre = float(s[:break_idx].mean()) if is_break else None
    post = float(s[break_idx:].mean()) if is_break else None

    return {
        "n": n,
        "stats": stats,
        "supStat": round(sup, 3),
        "breakIdx": break_idx if is_break else None,
        "isBreak": bool(is_break),
        "meanPre": round(pre, 4) if pre is not None else None,
        "meanPost": round(post, 4) if post is not None else None,
        "threshold": threshold,
        "interpretation": (
            f"sup t-stat={round(sup, 2)} at idx {break_idx}. "
            + (f"break 감지 (mean {round(pre, 3)} → {round(post, 3)})." if is_break else "break 미감지.")
        ),
    }


def detectMultipleBreaks(
    series: np.ndarray,
    *,
    maxBreaks: int = 3,
    trim: float = 0.15,
    threshold: float = 3.0,
) -> dict:
    """Sequential break detection — 1차 break 후 sub-sample 재귀.

    Bai-Perron 정식이 아닌 단순 sequential — 빠르고 robust.

    Returns:
        dict — breaks (list of {idx, stat, meanPre, meanPost}), nBreaks
    """
    s = np.asarray(series, dtype=np.float64)
    breaks = []

    def _recurse(start: int, end: int, depth: int):
        if depth >= maxBreaks or end - start < 30:
            return
        sub = s[start:end]
        r = detectStructuralBreak(sub, trim=trim, threshold=threshold)
        if not r.get("isBreak"):
            return
        bi = r["breakIdx"] + start
        breaks.append(
            {
                "idx": bi,
                "stat": r["supStat"],
                "meanPre": r["meanPre"],
                "meanPost": r["meanPost"],
            }
        )
        _recurse(start, bi, depth + 1)
        _recurse(bi, end, depth + 1)

    _recurse(0, len(s), 0)
    breaks.sort(key=lambda x: x["idx"])

    return {
        "n": len(s),
        "breaks": breaks,
        "nBreaks": len(breaks),
        "interpretation": (
            f"{len(breaks)} breaks 감지: " + ", ".join(f"idx {b['idx']} (t={b['stat']})" for b in breaks)
            if breaks
            else "구조변화 없음."
        ),
    }
