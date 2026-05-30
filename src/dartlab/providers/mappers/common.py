"""매퍼 공통 유틸리티 — 단일 정의, 전체 사용.

여러 파서/매퍼에서 중복 정의되던 함수를 한 곳으로 통합.
모든 호출자는 여기서 import한다.
"""

from __future__ import annotations

import re

# ── 한글 정규화 ──

_RE_KO_SPACE = re.compile(r"(?<=[\uAC00-\uD7A3])\s+(?=[\uAC00-\uD7A3])")
_RE_NOTE_REF = re.compile(r"\(\*?\d+\)$|\(주\d*\)$")  # (*1), (주1), (*2) 등 주석번호


def normalizeName(name: str) -> str:
    """항목명 정규화 — 공백·주석번호 제거로 매핑 키 안정화.

    1. 앞뒤 공백 제거
    2. 한글 사이 공백 제거 ("기 초" → "기초")
    3. 주석번호 제거 ("담보부차입금(*1)" → "담보부차입금")

    Args:
        name: 원본 항목명 (DART 표 cell 텍스트 등).

    Returns:
        정규화된 항목명. 매퍼 lookup 키로 직접 사용 가능.

    Example:
        >>> normalizeName("기 초")
        '기초'
        >>> normalizeName("담보부차입금(*1)")
        '담보부차입금'

    Raises:
        없음 — 순수 문자열 변환. None 입력 시 AttributeError(호출자가 str 보장).
    """
    s = name.strip()
    s = _RE_KO_SPACE.sub("", s)
    s = _RE_NOTE_REF.sub("", s).strip()
    return s


# ── 기간 판정 ──

_RE_CURRENT_PERIOD = re.compile(r"(당기|당기말|당반기|당분기|현재|전체)")
_RE_PREV_PERIOD = re.compile(r"(전기|전반기|전분기)")


def isCurrentPeriod(period: str) -> bool:
    """당기 계열 period 인지 판정. 전기/전반기/전분기는 제외.

    Args:
        period: period 라벨 텍스트 (예 "당기", "전기말", "당반기").

    Returns:
        당기 계열(당기·당기말·당반기·당분기·현재·전체)이면 True.
        전기 계열이 먼저 매칭되면 False.

    Example:
        >>> isCurrentPeriod("당기")
        True
        >>> isCurrentPeriod("전기말")
        False

    Raises:
        없음 — 순수 정규식 판정.
    """
    if _RE_PREV_PERIOD.search(period):
        return False
    return bool(_RE_CURRENT_PERIOD.search(period))


# ── 값 선택 ──

_FOREIGN_CURRENCY_RE = re.compile(
    r"(USD|JPY|EUR|GBP|CNY|HKD|SGD|AUD|CAD|CHF|TWD|THB|INR|VND|MYR|IDR|PHP|BRL|MXN|ZAR)"
    r"|(\[.*?천\])"
    r"|(JP￥|US\$|€|£|¥|￥)"
    r"|(\(.*?천\))"
)


def hasForeignCurrencyInValue(value: str) -> bool:
    """값에 외화 통화코드/기호가 포함되어 있는지 판정.

    USD/JPY/EUR 등 통화코드, ￥/€/£/US$ 등 기호, "[...천]"/"(...천)" 단위 표기를 탐지.

    Args:
        value: 표 cell 값 텍스트.

    Returns:
        외화 표기가 하나라도 매칭되면 True.

    Example:
        >>> hasForeignCurrencyInValue("USD 1,000")
        True
        >>> hasForeignCurrencyInValue("1,000")
        False

    Raises:
        없음 — 순수 정규식 판정.
    """
    return bool(_FOREIGN_CURRENCY_RE.search(value))


def pickValue(values: list[str]) -> str:
    """값 리스트에서 대표값 선택 — 원화 값 우선.

    뒤(최신 열)에서부터 훑어 외화 통화코드 없는 첫 유효값을 고른다. 원화 값이
    없으면 외화 포함 유효값으로 fallback, 그래도 없으면 첫 원소.

    Args:
        values: 동일 항목의 후보 값 리스트 (열 순서).

    Returns:
        대표값 문자열. 모두 비거나 "-" 면 빈 문자열.

    Example:
        >>> pickValue(["USD 100", "1,000"])
        '1,000'
        >>> pickValue(["USD 100"])
        'USD 100'

    Raises:
        없음 — 빈 리스트면 빈 문자열 반환.
    """
    # 1차: 원화 값
    for v in reversed(values):
        v_stripped = (v or "").strip()
        if not v_stripped or v_stripped == "-":
            continue
        if hasForeignCurrencyInValue(v_stripped):
            continue
        return v_stripped

    # 2차: fallback
    for v in reversed(values):
        v_stripped = (v or "").strip()
        if v_stripped and v_stripped != "-":
            return v_stripped

    return values[0] if values else ""
