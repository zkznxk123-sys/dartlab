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
    """항목명 정규화.

    1. 앞뒤 공백 제거
    2. 한글 사이 공백 제거 ("기 초" → "기초")
    3. 주석번호 제거 ("담보부차입금(*1)" → "담보부차입금")
    """
    s = name.strip()
    s = _RE_KO_SPACE.sub("", s)
    s = _RE_NOTE_REF.sub("", s).strip()
    return s


# ── 기간 판정 ──

_RE_CURRENT_PERIOD = re.compile(r"(당기|당기말|당반기|당분기|현재|전체)")
_RE_PREV_PERIOD = re.compile(r"(전기|전반기|전분기)")


def isCurrentPeriod(period: str) -> bool:
    """당기 계열 period인지 판정. 전기/전기말은 제외."""
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
    """값에 외화 통화코드/기호가 포함되어 있는지."""
    return bool(_FOREIGN_CURRENCY_RE.search(value))


def pickValue(values: list[str]) -> str:
    """값 리스트에서 대표값 선택.

    원화 값 우선 (외화 통화코드 없는 것).
    원화 값이 없으면 fallback으로 아무 유효값.
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
