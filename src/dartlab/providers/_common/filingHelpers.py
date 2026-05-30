"""Company live filing 공통 helper — 날짜 정규화 · 기간 윈도우 · 키워드 필터.

dart/edgar Company 의 ``liveFilings``/``filings``/``readFiling`` 가 공유하는 시장
무관 유틸. 외부 입력(문자열 날짜·키워드)을 정규화하고, 조회 결과 DataFrame 을
키워드로 거른다. provider 별 로직 없음 — 순수 입출력 변환.
"""

from __future__ import annotations

import re
from datetime import date, datetime, timedelta
from typing import Any

import polars as pl


def coerceDate(value: str | date | datetime | None) -> date | None:
    """다양한 날짜 입력을 ``date`` 로 정규화한다.

    Capabilities:
        - ``date``/``datetime`` 객체는 그대로(또는 ``.date()``) 통과.
        - 문자열 4 양식 허용: ``YYYYMMDD`` · ``YYYY-MM-DD`` · ``YYYY-MM``(1 일) ·
          ``YYYY``(1 월 1 일). 공백 strip 후 판별.
        - None / 빈 문자열 → None (조회 기간 미지정 의미).

    Args:
        value: 날짜 입력. ``str`` / ``date`` / ``datetime`` / None.

    Returns:
        정규화된 ``date``. 입력이 None 또는 빈 문자열이면 None.

    Raises:
        ValueError: 4 양식 어디에도 맞지 않는 문자열.

    Example:
        >>> coerceDate("20240331")
        datetime.date(2024, 3, 31)
        >>> coerceDate("2024") and coerceDate("2024").isoformat()
        '2024-01-01'
        >>> coerceDate(None) is None
        True

    Guide:
        사용자/AI 가 넘긴 자유 양식 날짜를 OpenDART/SEC 조회 직전 단일 ``date`` 로
        모을 때 진입점. 범위 계산은 ``resolveDateWindow`` 가 본 함수를 호출.

    SeeAlso:
        - resolveDateWindow : 본 함수로 start/end 를 정규화 후 윈도우 계산.

    Requires:
        - 표준 라이브러리만 (datetime · re).

    AIContext:
        liveFilings 인자 검증 1 차 — 양식 위반은 즉시 ValueError 로 사용자에게 노출
        (silent None 회피).

    LLM Specifications:
        AntiPatterns:
            - 양식 미상 문자열을 None 으로 silent 흡수 금지 — ValueError 로 알린다.
            - 월/분기 문자열을 임의 말일로 추정 금지 — 1 일로 고정(예측가능).
        OutputSchema:
            - ``date | None``.
        Prerequisites:
            - 없음 (stdlib).
        Freshness:
            - 순수 변환 — 데이터 의존 없음.
        Dataflow:
            - str → strip → regex 매칭 → ``datetime.strptime`` → ``date``.
        TargetMarkets:
            - KR + US 공통 (날짜 양식 동일).
    """
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value

    text = str(value).strip()
    if not text:
        return None
    if re.fullmatch(r"\d{8}", text):
        return datetime.strptime(text, "%Y%m%d").date()
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", text):
        return datetime.strptime(text, "%Y-%m-%d").date()
    if re.fullmatch(r"\d{4}-\d{2}", text):
        return datetime.strptime(f"{text}-01", "%Y-%m-%d").date()
    if re.fullmatch(r"\d{4}", text):
        return datetime.strptime(f"{text}-01-01", "%Y-%m-%d").date()
    raise ValueError(f"올바르지 않은 날짜 형식: {value!r}")


def resolveDateWindow(
    start: str | date | datetime | None = None,
    end: str | date | datetime | None = None,
    *,
    days: int | None = None,
) -> tuple[str | None, str | None]:
    """live filings 조회용 (start, end) ISO 문자열 윈도우를 결정한다.

    Capabilities:
        - start/end 를 ``coerceDate`` 로 정규화.
        - ``days`` 지정 시 누락된 경계 보정: end 없으면 오늘, start 없으면
          ``end - (days-1)`` (days 일 포함 윈도우).
        - 셋 다 None 이면 (None, None) — 호출자가 provider 기본 범위 사용.

    Args:
        start: 시작일 (자유 양식). None 허용.
        end: 종료일 (자유 양식). None 허용.
        days: 최근 N 일 윈도우. 양수만. start/end 보정에만 사용.

    Returns:
        ``(startIso, endIso)`` — 각 ``YYYY-MM-DD`` 또는 None.

    Raises:
        ValueError: ``days`` 가 0 이하, 또는 start/end 양식 위반(coerceDate 전파).

    Example:
        >>> resolveDateWindow("2024-01-01", "2024-03-31")
        ('2024-01-01', '2024-03-31')
        >>> s, e = resolveDateWindow(days=7)  # doctest: +SKIP
        >>> (e is not None, s is not None)
        (True, True)

    Guide:
        - "최근 30 일 공시" → ``resolveDateWindow(days=30)``.
        - "특정 구간" → ``resolveDateWindow(start, end)``.

    SeeAlso:
        - coerceDate : 경계 정규화.
        - filterFilingsByKeyword : 윈도우 조회 결과를 키워드로 추가 필터.

    Requires:
        - 표준 라이브러리만.

    AIContext:
        liveFilings(days=) / (start,end) 두 호출 양식을 단일 윈도우로 수렴 — 호출자
        분기 제거.

    LLM Specifications:
        AntiPatterns:
            - days 와 start/end 를 모두 줬을 때 days 로 start/end 를 덮어쓰기 금지 —
              명시 경계 우선, days 는 빈 경계만 채움.
            - days ≤ 0 을 0 건으로 silent 처리 금지 — ValueError.
        OutputSchema:
            - ``tuple[str | None, str | None]`` (ISO 날짜).
        Prerequisites:
            - 없음 (stdlib).
        Freshness:
            - ``days`` 경로는 ``date.today()`` 기준 — 호출 시점 의존.
        Dataflow:
            - coerceDate(start/end) → days 보정 → isoformat.
        TargetMarkets:
            - KR + US 공통.
    """
    startDate = coerceDate(start)
    endDate = coerceDate(end)

    if days is not None:
        if days <= 0:
            raise ValueError("days는 1 이상이어야 합니다.")
        if endDate is None:
            endDate = date.today()
        if startDate is None:
            startDate = endDate - timedelta(days=days - 1)

    return (
        startDate.isoformat() if startDate is not None else None,
        endDate.isoformat() if endDate is not None else None,
    )


def splitKeywords(keyword: str | None) -> list[str]:
    """콤마/슬래시/파이프/개행 구분 키워드 문자열을 토큰 리스트로 분리한다.

    Capabilities:
        - 구분자 ``, / | 개행`` 다중 분리 + 각 토큰 strip + 빈 토큰 제거.
        - None → 빈 리스트 (필터 미적용 의미).

    Args:
        keyword: 단일/다중 키워드 문자열. None 허용.

    Returns:
        공백 제거된 토큰 ``list[str]``. 입력 None/빈값이면 ``[]``.

    Raises:
        없음.

    Example:
        >>> splitKeywords("배당, 유상증자")
        ['배당', '유상증자']
        >>> splitKeywords(None)
        []

    Guide:
        ``filterFilingsByKeyword`` 가 사용자 keyword 인자를 OR 매칭 토큰으로 쪼갤 때
        진입점.

    SeeAlso:
        - filterFilingsByKeyword : 본 토큰으로 DataFrame 필터.

    Requires:
        - 표준 라이브러리 (re).

    AIContext:
        "배당/유상증자" 같은 복합 키워드를 OR 조건으로 분해 — 사용자 의도 보존.

    LLM Specifications:
        AntiPatterns:
            - 단일 구분자만 처리 금지 — 4 구분자 모두 허용.
            - 빈 토큰 잔류 금지 (strip 후 제거).
        OutputSchema:
            - ``list[str]``.
        Prerequisites:
            - 없음.
        Freshness:
            - 순수 변환.
        Dataflow:
            - re.split(구분자) → strip → 빈값 필터.
        TargetMarkets:
            - KR + US 공통.
    """
    if keyword is None:
        return []
    tokens = [token.strip() for token in re.split(r"[,/|\n]+", str(keyword)) if token.strip()]
    return tokens


def filterFilingsByKeyword(df: pl.DataFrame, *, keyword: str | None, columns: list[str]) -> pl.DataFrame:
    """지정 컬럼 중 하나라도 키워드(OR)를 포함하는 행만 남긴다.

    Capabilities:
        - ``splitKeywords`` 토큰을 case-insensitive OR regex 로 결합.
        - 존재하는 컬럼만 대상(없는 컬럼 skip), 각 컬럼 Utf8 캐스팅 + null 안전.
        - keyword 없음 / 빈 df / 대상 컬럼 0 → 원본 그대로 반환(무필터).

    Args:
        df: 공시 목록 DataFrame.
        keyword: 필터 키워드(다중 가능). None = 무필터.
        columns: 검색 대상 컬럼명 후보 (예: 보고서명·제목).

    Returns:
        키워드 매칭 행만 남은 DataFrame (무필터 조건이면 입력 그대로).

    Raises:
        없음.

    Example:
        >>> import polars as pl
        >>> df = pl.DataFrame({"report_nm": ["배당결정", "유상증자", "분기보고서"]})
        >>> filterFilingsByKeyword(df, keyword="배당", columns=["report_nm"]).height
        1

    Guide:
        liveFilings/filings 결과를 사용자 keyword 로 좁힐 때. 차트/표 추가 가공 전 1 차 필터.

    SeeAlso:
        - splitKeywords : 키워드 토큰화.
        - resolveDateWindow : 기간 윈도우 (직교 필터).

    Requires:
        - polars.

    AIContext:
        키워드 부재/컬럼 부재 시 *원본 반환* (빈 df 아님) — "필터 못 했으니 전체"
        의미 보존.

    LLM Specifications:
        AntiPatterns:
            - 대상 컬럼 부재 시 빈 df 반환 금지 — 원본 통과(무필터).
            - 대소문자 구분 매칭 금지 — ``(?i)`` 적용.
        OutputSchema:
            - ``pl.DataFrame`` (입력과 동일 컬럼, 행 subset).
        Prerequisites:
            - polars DataFrame.
        Freshness:
            - 순수 변환.
        Dataflow:
            - splitKeywords → 존재 컬럼 OR contains regex → df.filter.
        TargetMarkets:
            - KR + US 공통.
    """
    tokens = splitKeywords(keyword)
    if not tokens or df.is_empty():
        return df

    available = [column for column in columns if column in df.columns]
    if not available:
        return df

    pattern = "(?i)" + "|".join(re.escape(token) for token in tokens)
    expr = pl.lit(False)
    for column in available:
        expr = expr | pl.col(column).cast(pl.Utf8).fill_null("").str.contains(pattern)
    return df.filter(expr)


def filingRecord(value: Any) -> dict[str, Any] | None:
    """row-like filing 입력을 얕은 복사 dict 로 정규화한다.

    Capabilities:
        - dict 입력 → 얕은 복사(원본 보호). 그 외 타입 → None.

    Args:
        value: filing row 후보 (dict 기대).

    Returns:
        dict 면 복사본, 아니면 None.

    Raises:
        없음.

    Example:
        >>> filingRecord({"rcept_no": "20240101000001"})
        {'rcept_no': '20240101000001'}
        >>> filingRecord("not-a-row") is None
        True

    Guide:
        ``readFiling`` 이 받은 filing 인자(dict row vs 기타)를 안전 dict 로 모을 때.

    SeeAlso:
        - truncateText : readFiling 본문 길이 제한.

    Requires:
        - 없음.

    AIContext:
        readFiling 입력 방어 — dict 아닌 입력은 None 으로 명확히 분기.

    LLM Specifications:
        AntiPatterns:
            - 원본 dict 를 그대로 반환(공유) 금지 — 얕은 복사로 mutation 격리.
        OutputSchema:
            - ``dict[str, Any] | None``.
        Prerequisites:
            - 없음.
        Freshness:
            - 순수 변환.
        Dataflow:
            - isinstance(dict) → dict(value) else None.
        TargetMarkets:
            - KR + US 공통.
    """
    if isinstance(value, dict):
        return dict(value)
    return None


def truncateText(text: str, maxChars: int | None = None) -> tuple[str, bool]:
    """문자열을 최대 길이로 자르고 잘림 여부를 함께 반환한다.

    Capabilities:
        - ``maxChars`` None/0 이하/길이 이내면 원본 + False.
        - 초과 시 앞 ``maxChars`` 자 + True.

    Args:
        text: 원본 문자열.
        maxChars: 최대 길이. None/0 이하 = 무제한.

    Returns:
        ``(잘린 텍스트, 잘림 여부)``.

    Raises:
        없음.

    Example:
        >>> truncateText("hello world", 5)
        ('hello', True)
        >>> truncateText("hi", 5)
        ('hi', False)

    Guide:
        ``readFiling`` 이 공시 원문을 응답 크기 제한에 맞춰 자를 때. 잘림 플래그로
        호출자가 "...더 있음" 표시 가능.

    SeeAlso:
        - filingRecord : readFiling 입력 정규화.

    Requires:
        - 없음.

    AIContext:
        LLM 컨텍스트 토큰 절약용 본문 절단 — 잘림 여부 플래그로 truncation 명시.

    LLM Specifications:
        AntiPatterns:
            - 잘림 여부 미반환 금지 — 호출자가 truncation 인지 못 함.
            - maxChars 0/음수를 0 길이로 처리 금지 — 무제한 의미.
        OutputSchema:
            - ``tuple[str, bool]``.
        Prerequisites:
            - 없음.
        Freshness:
            - 순수 변환.
        Dataflow:
            - len 비교 → slice + 플래그.
        TargetMarkets:
            - KR + US 공통.
    """
    if maxChars is None or maxChars <= 0 or len(text) <= maxChars:
        return text, False
    return text[:maxChars], True
