"""순주주환원 분류 — 환원형 / 중립 / 희석형."""

from __future__ import annotations


def classifyReturn(
    hasDividend: bool,
    hasBuyback: bool,
    recentIncrease: bool,
) -> tuple[str, bool]:
    """순주주환원 방향 분류.

    Returns:
        (분류, 모순형여부)
        분류: "적극환원" / "환원형" / "중립" / "희석형"
        모순형: 배당하면서 최근 증자
    """
    return_score = 0
    if hasDividend:
        return_score += 1
    if hasBuyback:
        return_score += 1
    if recentIncrease:
        return_score -= 1

    if return_score >= 2:
        category = "적극환원"
    elif return_score >= 1:
        category = "환원형"
    elif return_score == 0:
        category = "중립"
    else:
        category = "희석형"

    contradiction = hasDividend and recentIncrease
    return category, contradiction
