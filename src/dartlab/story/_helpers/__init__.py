"""story 8 막 builders 의 공유 helper (T9-5 step 2/4).

builders.py 의 순수 utility 함수 일부를 본 모듈로 이전. 기존 builders.py 는
re-import 로 호환 유지.

이전 완료:
    - currencyUnit(): builders._unitForCurrency 의 신 이름 — 현재 통화 단위 단순 조회

순서 (BUILDERS_SPLIT_PLAN.md 정합):
    Step 1 ✓ — scaffold + 4 step 명문화
    Step 2 (현재) — 1 helper 이전 시작 (currencyUnit)
    Step 3 — _fmtAmtShort 등 format helper 이전
    Step 4 — builders.py 5 토픽 분리 + facade
"""

from __future__ import annotations

import contextvars

_storyCurrency: contextvars.ContextVar[str] = contextvars.ContextVar("review_currency", default="KRW")


def currencyUnit() -> str:
    """현재 통화에 맞는 unifyTableScale unit 반환 (T9-5).

    Returns:
        'usd' 또는 'won' — _storyCurrency contextvar 값 기준.

    Example:
        >>> from dartlab.story._helpers import currencyUnit
        >>> currencyUnit()
        'won'
    """
    return "usd" if _storyCurrency.get() == "USD" else "won"


__all__ = ["currencyUnit", "_storyCurrency"]
