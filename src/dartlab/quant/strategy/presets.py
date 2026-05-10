"""Style preset registry — 8 검증된 dartlab 스타일.

각 스타일 파일: quant/strategy/styles/<key>.py — `def build(company, **kw) -> Rule`
+ 한글 docstring (~30줄, [언제 강한가]/[어떤 종목]/[진입 의미]/[청산]/[주의점]/[대표 사례]/[관련 dartlab 축]/[복제 예시]).

KR 전용 스타일은 `STYLE_KR_ONLY` set 에 등록 — EdgarCompany 호출 시 NotApplicable sentinel.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

# 8 스타일 — Phase E 에서 styles/*.py 채워짐. 여기는 lazy import.

STYLE_KR_ONLY: set[str] = {"flowFollow", "seasonalKR"}

# 한글 alias → 영문 key
STYLE_ALIASES: dict[str, str] = {
    "추세추종": "trendFollow",
    "trendfollow": "trendFollow",
    "평균회귀": "meanReversion",
    "meanreversion": "meanReversion",
    "돌파": "breakout",
    "눌림목매수": "dipBuy",
    "눌림목": "dipBuy",
    "dipbuy": "dipBuy",
    "이벤트드리븐": "eventDriven",
    "이벤트": "eventDriven",
    "eventdriven": "eventDriven",
    "수급추종": "flowFollow",
    "수급": "flowFollow",
    "flowfollow": "flowFollow",
    "저변동방어": "lowVolDefensive",
    "저변동성": "lowVolDefensive",
    "lowvol": "lowVolDefensive",
    "lowvoldefensive": "lowVolDefensive",
    "한국캘린더": "seasonalKR",
    "캘린더": "seasonalKR",
    "seasonalkr": "seasonalKR",
}


def _lazyStyles() -> dict[str, Callable[..., Any]]:
    """스타일 레지스트리 lazy import — circular import 방지."""
    from .styles import (
        breakout,
        dipBuy,
        eventDriven,
        flowFollow,
        lowVolDefensive,
        meanReversion,
        seasonalKR,
        trendFollow,
    )

    return {
        "trendFollow": trendFollow.build,
        "meanReversion": meanReversion.build,
        "breakout": breakout.build,
        "dipBuy": dipBuy.build,
        "eventDriven": eventDriven.build,
        "flowFollow": flowFollow.build,
        "lowVolDefensive": lowVolDefensive.build,
        "seasonalKR": seasonalKR.build,
    }


# 모듈 레벨 캐시
_REGISTRY_CACHE: dict[str, Callable[..., Any]] | None = None


def STYLE_REGISTRY() -> dict[str, Callable[..., Any]]:  # noqa: N802
    """스타일 레지스트리 dict (lazy)."""
    global _REGISTRY_CACHE
    if _REGISTRY_CACHE is None:
        _REGISTRY_CACHE = _lazyStyles()
    return _REGISTRY_CACHE


def resolveStyle(name: str) -> str:
    """한글/영문 alias → 정규 스타일 키 변환.

    Parameters
    ----------
    name : str
        스타일명 (한글 또는 영문). 예: "추세추종", "trendFollow".

    Returns
    -------
    str
        정규 영문 키. 예: "trendFollow". 매칭 실패 시 원본 반환.
    """
    if not name:
        return name
    s = name.strip()
    if s in STYLE_ALIASES:
        return STYLE_ALIASES[s]
    low = s.lower()
    if low in STYLE_ALIASES:
        return STYLE_ALIASES[low]
    return s


def listStyles() -> list[dict]:
    """가이드 카탈로그 — c.quant("style") (인자 없이) 반환용.

    Returns
    -------
    list[dict]
        각 원소:
        key : str — 정규 스타일 키 (예: "trendFollow")
        label : str — 스타일 한 줄 요약
        description : str — build 함수 docstring 첫 줄
        kr_only : bool — KR 전용 여부
    """
    reg = STYLE_REGISTRY()
    items = []
    for key, fn in reg.items():
        doc = (fn.__doc__ or "").strip().split("\n")[0]
        items.append(
            {
                "key": key,
                "label": doc.split("(")[0].strip() if doc else key,
                "description": doc,
                "kr_only": key in STYLE_KR_ONLY,
            }
        )
    return items


# 0.10 BC 깸 — snake_case alias 제거.
