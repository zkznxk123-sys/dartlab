"""panel period 정규화 SSOT (L0) — 보고기간 종료일 → calendar quarter.

panel·finance·report 공유 period 키 = **실제 보고기간 종료일의 달력월 기준**
calendar quarter (결산월 무관). 비-12월결산법인(3월·6월·9월 결산)을 12월결산 그리드에
배치 → 회사 무관 동일 period 축 정렬. **값 환산·합성 0** (lossless · [[feedback_xml_native_truth]]).

XML 표지 파싱(lxml)은 BUILD 층(gather) 책임 — 본 모듈은 (year, month) → YYYYQn 순수
변환만 (core 는 lxml import 0, R2). gather builder 가 표지에서 종료(year, month) 를
추출해 ``periodFromEnd`` 호출.

LLM Specifications:
    AntiPatterns:
        - rcept_no 직접 period 사용 금지 — 표지 사업연도 종료일 기준 (build 가 추출).
        - lxml import 금지 — 순수 (year, month) 변환만 (XML 파싱은 gather build).
        - 결산월별 분기 로직 금지 — 종료 *달력월* 단일 매핑 (12월결산화).
    OutputSchema:
        - ``periodFromEnd(endYear, endMonth) -> str`` ("YYYYQn").
        - ``isPeriodColumn(name) -> bool``.
        - ``sortPeriods(periods, *, descending) -> list[str]``.
    Prerequisites:
        - 없음 (표준 라이브러리만).
    Freshness:
        - period 규약 안정 — 변경 시 build·reader·finance·report 동시 정합.
    Dataflow:
        - build: XML 표지 → (endYear, endMonth) → periodFromEnd → 14-col ``period``.
    TargetMarkets:
        - KR (DART). US/JP 는 자기 fiscal 종료월을 동일 그리드로 normalize.
"""

from __future__ import annotations

import re

# 종료 달력월 → calendar quarter (12월 결산 양식). 결산월 무관:
#   12월결산 1Q(1~3월) → end 03 → Q1 / 3월결산 1Q(4~6월) → end 06 → Q2 (12월결산화)
_MONTH_TO_QUARTER: dict[int, str] = {
    1: "Q4",
    2: "Q4",
    3: "Q1",  # 03/31 종료 = Q1
    4: "Q1",
    5: "Q1",
    6: "Q2",  # 06/30 종료 = Q2
    7: "Q2",
    8: "Q2",
    9: "Q3",  # 09/30 종료 = Q3
    10: "Q3",
    11: "Q3",
    12: "Q4",  # 12/31 종료 = Q4
}

_PERIOD_RE = re.compile(r"^\d{4}Q[1-4]$")


def periodFromEnd(endYear: int, endMonth: int) -> str:
    """보고기간 종료 (year, month) → calendar quarter "YYYYQn".

    결산월 무관 universal — 회사의 *실제 보고기간 종료일* 의 *달력월* 기반. 종료월이
    1~2월(이상 case)이면 직전 연도 Q4 양식으로 12월결산화한다.

    Args:
        endYear: 보고기간 종료 연도 (예: 2024).
        endMonth: 보고기간 종료 월 (1~12).

    Returns:
        "YYYYQn" 형식 period 키 (예: "2024Q3").

    Raises:
        없음 — endMonth 범위 밖이면 Q4 로 fallback (KeyError 회피).

    Example:
        >>> periodFromEnd(2024, 9)
        '2024Q3'
        >>> periodFromEnd(2024, 1)
        '2023Q4'

    SeeAlso:
        - ``sortPeriods`` — period 키 정렬.
        - gather build ``builder`` — XML 표지에서 (endYear, endMonth) 추출 후 본 함수 호출.

    Requires:
        - 없음 (표준 라이브러리).

    Capabilities:
        - 비-12월결산법인을 12월결산 그리드에 배치 → 회사 무관 동일 period 축 정렬.

    Guide:
        - build 단계에서만 호출 — runtime read 는 이미 저장된 ``period`` 컬럼 사용.

    AIContext:
        - 순수 변환 함수 — 값 환산 0, 종료일 그대로 분기 매핑.

    LLM Specifications:
        AntiPatterns:
            - endMonth 를 결산월로 보정 금지 — 달력월 그대로 매핑.
            - 1~2월 종료를 당해 Q1 처리 금지 — 직전년도 Q4 (12월결산 양식).
        OutputSchema:
            - ``str`` ("YYYYQn", regex ``^\\d{4}Q[1-4]$``).
        Prerequisites:
            - endYear int, endMonth int.
        Freshness:
            - 정적 규약.
        Dataflow:
            - (endYear, endMonth) → _MONTH_TO_QUARTER → "YYYYQn".
        TargetMarkets:
            - KR + US + JP (종료 달력월 단일 매핑).
    """
    suffix = _MONTH_TO_QUARTER.get(endMonth, "Q4")
    year = endYear
    if endMonth in (1, 2):
        year = endYear - 1
    return f"{year}{suffix}"


def isPeriodColumn(name: str) -> bool:
    """컬럼명이 "YYYYQn" period 키인지 판정.

    wide pivot 결과에서 period 열(값 열)과 index 열(메타)을 구분할 때 사용.

    Args:
        name: 컬럼명.

    Returns:
        "YYYYQn" 형식이면 True.

    Raises:
        없음.

    Example:
        >>> isPeriodColumn("2024Q3")
        True
        >>> isPeriodColumn("disclosureKey")
        False

    SeeAlso:
        - ``periodFromEnd`` — period 키 생성.
        - ``sortPeriods`` — period 열 정렬.

    Requires:
        - 없음.

    Capabilities:
        - wide board 의 period 열 자동 식별 (index/value 분리).

    Guide:
        - reader/pivot 에서 열 분류에 사용.

    AIContext:
        - regex 단순 판정 — 부작용 0.

    LLM Specifications:
        AntiPatterns:
            - 부분일치 금지 — 완전 일치 regex (``^\\d{4}Q[1-4]$``).
        OutputSchema:
            - ``bool``.
        Prerequisites:
            - name str.
        Freshness:
            - 정적.
        Dataflow:
            - name → regex match → bool.
        TargetMarkets:
            - 전 시장 공통 (period 키 형식 동일).
    """
    return bool(_PERIOD_RE.match(name))


def sortPeriods(periods: list[str], *, descending: bool = False) -> list[str]:
    """ "YYYYQn" period 키 리스트 정렬.

    YYYYQn 은 사전식 정렬이 곧 시간순 — 별도 파싱 없이 문자열 정렬.

    Args:
        periods: "YYYYQn" 문자열 리스트.
        descending: True 면 최신 우선 (내림차순).

    Returns:
        정렬된 새 리스트 (원본 불변).

    Raises:
        없음.

    Example:
        >>> sortPeriods(["2024Q1", "2023Q4", "2024Q3"])
        ['2023Q4', '2024Q1', '2024Q3']
        >>> sortPeriods(["2024Q1", "2023Q4"], descending=True)
        ['2024Q1', '2023Q4']

    SeeAlso:
        - ``isPeriodColumn`` — period 열 식별.
        - ``periodFromEnd`` — period 키 생성.

    Requires:
        - 없음.

    Capabilities:
        - wide board period 축 시간순 정렬 (anchorLatest 의 "최신" 기준 = max).

    Guide:
        - reader/pivot 의 열 순서 결정에 사용.

    AIContext:
        - 순수 정렬 — 부작용 0.

    LLM Specifications:
        AntiPatterns:
            - 정수 분해 후 정렬 금지 — YYYYQn 사전식 == 시간순.
        OutputSchema:
            - ``list[str]`` (정렬됨).
        Prerequisites:
            - periods list[str].
        Freshness:
            - 정적.
        Dataflow:
            - periods → sorted → list.
        TargetMarkets:
            - 전 시장 공통.
    """
    return sorted(periods, reverse=descending)
