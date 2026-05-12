"""순주주환원 분류 — 환원형 / 중립 / 희석형."""

from __future__ import annotations


def classifyReturn(
    hasDividend: bool,
    hasBuyback: bool,
    recentIncrease: bool,
) -> tuple[str, bool]:
    """순주주환원 방향 분류.

    Parameters
    ----------
    hasDividend : bool
        현금배당 여부.
    hasBuyback : bool
        자사주 매입 여부.
    recentIncrease : bool
        최근 유상증자 여부.

    Returns
    -------
    tuple[str, bool]
        (분류, 모순형여부) — 분류는 "적극환원/환원형/중립/희석형",
        모순형은 배당 + 최근 증자 동시일 때 True.

    Raises
    ------
    없음 — 순수 분기 함수.

    Examples
    --------
    >>> from dartlab.scan.capital.classifier import classifyReturn
    >>> classifyReturn(True, True, False)
    ('적극환원', False)
    >>> classifyReturn(True, False, True)
    ('중립', True)
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
