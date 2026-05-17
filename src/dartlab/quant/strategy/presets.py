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
    """스타일 레지스트리 dict (lazy).

    Capabilities:
        - 8 검증 스타일 (trendFollow/meanReversion/breakout/dipBuy/eventDriven/flowFollow/lowVolDefensive/seasonalKR) 빌더 매핑
        - lazy + module 캐시 (lru 효과)

    Returns:
        dict[str, Callable] — ``{styleKey: build_fn}``.

    Guide:
        모든 Quant strategy 진입점의 SSOT. 새 스타일 추가 시 본 dict 에 등록.

    When:
        Strategy 일괄 백테스트 + AI 스타일 enumerate.

    How:
        ``_REGISTRY_CACHE`` 모듈 변수 lazy build → 재사용.

    Requires:
        styles/*.py 모듈 import.

    Raises:
        없음.

    Example:
        >>> list(STYLE_REGISTRY().keys())[:3]
        ['trendFollow', 'meanReversion', 'breakout']

    See Also:
        - resolveStyle : alias 해석
        - listStyles : 카탈로그 dict

    AIContext:
        "사용 가능 스타일" 답변 시 keys 인용.
    """
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

    Capabilities:
        - 한글/영문 양방향 매칭 + 대소문자 무시 fallback
        - 매칭 실패 시 원본 그대로 (verbose fallback)

    Guide:
        한글 alias 매핑 (``"추세추종"`` → ``"trendFollow"``) 입력 받는 모든 진입점에 적용.

    When:
        사용자 한글 입력 정규화 + AI/CLI 진입.

    How:
        STYLE_ALIASES 직접 lookup → lower 시도 → fallback 원본.

    Requires:
        STYLE_ALIASES dict 등록.

    Raises:
        없음.

    Example:
        >>> resolveStyle("추세추종")
        'trendFollow'

    See Also:
        - STYLE_REGISTRY : 등록된 스타일
        - listStyles : 카탈로그

    AIContext:
        한글 스타일 명령 정규화 답변 시 사용.
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

    Capabilities:
        - STYLE_REGISTRY 순회 → build 함수 docstring 첫 줄 추출 → 카탈로그 dict 변환
        - kr_only 플래그로 시장 제약 표시

    Guide:
        ``c.quant("style")`` 인자 없는 호출의 응답 카탈로그.

    When:
        Style 카탈로그 조회 + AI "어떤 스타일 있나" 답변.

    How:
        STYLE_REGISTRY → 함수 docstring split → dict 생성.

    Requires:
        styles 각 ``build`` 의 docstring 첫 줄.

    Raises:
        없음.

    Example:
        >>> listStyles()[0]["key"]
        'trendFollow'

    See Also:
        - STYLE_REGISTRY : 등록
        - resolveStyle : alias

    AIContext:
        "사용 가능 스타일 목록" 답변 시 list 인용.
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
