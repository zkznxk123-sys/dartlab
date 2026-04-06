"""dartlab 독립 신용분석 엔진 (dCR).

공시 데이터만으로 재현 가능한 독립 신용등급을 산출한다.
7축 정량 스코어링 + 업종별 차등 + 시계열 안정화 → dCR-AAA ~ dCR-D.

사용법::

    import dartlab

    # 루트 함수
    dartlab.credit("005930")                # 삼성전자 등급 종합
    dartlab.credit("005930", "채무상환")     # 채무상환 축만

    # Company-bound
    c = dartlab.Company("005930")
    c.credit()                              # 등급 종합
    c.credit("채무상환")                     # 축별 접근
    c.credit(detail=True)                   # 7축 상세 + 지표 시계열

    # review 경유 보고서
    c.review("신용분석")                     # 신용분석 전문 보고서
    c.review("신용분석").toMarkdown()         # 마크다운 출력

ops/credit.md 참조.
"""

from __future__ import annotations

# ── 7축 레지스트리 ──

_CREDIT_AXES: dict[str, str] = {
    "채무상환": "채무상환능력",
    "자본구조": "자본구조",
    "유동성": "유동성",
    "현금흐름": "현금흐름",
    "사업안정성": "사업안정성",
    "재무신뢰성": "재무신뢰성",
    "공시리스크": "공시리스크",
}

# 가이드 메타: axis(영문) | label(한글) | description | example
_AXIS_META: list[dict[str, str]] = [
    {
        "axis": "grade",
        "label": "등급",
        "description": "dCR 종합 등급 + 점수 + 7축 가중평균 (default)",
        "example": 'c.credit("등급")',
    },
    {
        "axis": "repayment",
        "label": "채무상환",
        "description": "이자보상배율, 부채상환능력",
        "example": 'c.credit("채무상환")',
    },
    {
        "axis": "leverage",
        "label": "자본구조",
        "description": "부채비율, 자본 안정성",
        "example": 'c.credit("자본구조")',
    },
    {
        "axis": "liquidity",
        "label": "유동성",
        "description": "유동비율, 단기 상환 여력",
        "example": 'c.credit("유동성")',
    },
    {
        "axis": "cashflow",
        "label": "현금흐름",
        "description": "OCF, FCF 안정성",
        "example": 'c.credit("현금흐름")',
    },
    {
        "axis": "business",
        "label": "사업안정성",
        "description": "매출 변동성, 사업 지속성",
        "example": 'c.credit("사업안정성")',
    },
    {
        "axis": "reliability",
        "label": "재무신뢰성",
        "description": "감사의견, 회계 일관성",
        "example": 'c.credit("재무신뢰성")',
    },
    {
        "axis": "disclosure",
        "label": "공시리스크",
        "description": "공시 변경, 정정 빈도",
        "example": 'c.credit("공시리스크")',
    },
]

_ALIASES: dict[str, str] = {
    "repayment": "채무상환",
    "leverage": "자본구조",
    "capital": "자본구조",
    "liquidity": "유동성",
    "cashflow": "현금흐름",
    "business": "사업안정성",
    "reliability": "재무신뢰성",
    "disclosure": "공시리스크",
    "채무상환능력": "채무상환",
    "사업위험": "사업안정성",
    "사업": "사업안정성",
    "신뢰성": "재무신뢰성",
    "공시": "공시리스크",
}

# 종합 등급 alias (가이드 무인자 호출과 구분)
_GRADE_ALIASES = {"등급", "grade", "종합", "종합등급", "credit", "신용등급"}


def guide():
    """credit 엔진 7축 + 종합 가이드 DataFrame.

    Returns:
        polars DataFrame (axis, label, description, example)
    """
    import polars as pl

    return pl.DataFrame(_AXIS_META)


def _resolveAxis(axis: str) -> str | None:
    """축 이름 또는 alias → 정규 축 이름."""
    if axis in _CREDIT_AXES:
        return axis
    if axis in _ALIASES:
        return _ALIASES[axis]
    lower = axis.lower()
    if lower in _ALIASES:
        return _ALIASES[lower]
    return None


def _filterAxis(result: dict, axis: str) -> dict | None:
    """등급 결과에서 특정 축만 추출."""
    resolved = _resolveAxis(axis)
    if resolved is None:
        available = ", ".join(sorted(_CREDIT_AXES))
        raise ValueError(
            f"알 수 없는 신용분석 축: '{axis}'. 가용 축: {available}\n"
            f"  사용법: c.credit() 으로 전체 신용분석 결과를 확인하세요."
        )

    fullName = _CREDIT_AXES[resolved]
    for a in result.get("axes", []):
        if a.get("name") == fullName:
            return {
                "axis": fullName,
                "score": a.get("score"),
                "weight": a.get("weight"),
                "metrics": a.get("metrics", []),
                "grade": result.get("grade"),
                "overallScore": result.get("score"),
                # R22-1: 단일 축 추출에도 score 의미 안내 전달
                "_scoreMeaning": result.get("_scoreMeaning"),
            }
    return None


def credit(
    stockCode: str | None = None, axis: str | None = None, *, detail: bool = False, basePeriod: str | None = None
):
    """신용등급 산출 단일 진입점.

    Parameters
    ----------
    stockCode : 종목코드 또는 ticker. None이면 7축 가이드 DataFrame 반환.
    axis : 축 이름 ("등급" → 종합, "채무상환" 등 → 해당 축만)
    detail : True이면 7축 상세 + 모든 지표 포함
    basePeriod : 분석 기준 기간 (None이면 최신)

    Returns
    -------
    DataFrame | dict | None
        - stockCode=None → 가이드 DataFrame
        - axis="등급" 또는 None+stockCode → 종합 등급 dict
        - axis=축이름 → 해당 축 dict
    """
    if stockCode is None:
        return guide()

    from dartlab.credit.engine import evaluate

    # "등급"/"grade" 등 종합 alias는 axis로 처리하지 않음 (전체 결과)
    if axis is not None and axis in _GRADE_ALIASES:
        axis = None

    result = evaluate(stockCode, detail=detail or (axis is not None), basePeriod=basePeriod)
    if result is None:
        return None

    if axis is not None:
        return _filterAxis(result, axis)

    return result


def creditCompany(
    company, axis: str | None = None, *, detail: bool = False, basePeriod: str | None = None
):
    """Company 객체로 신용등급 산출 (Company-bound용).

    axis=None → 가이드 DataFrame (self-discovery)
    axis="등급" → 종합 등급 dict
    axis="채무상환" → 해당 축 dict
    """
    if axis is None:
        return guide()

    from dartlab.credit.engine import evaluateCompany

    # "등급"/"grade" 등 종합 alias는 axis로 처리하지 않음
    if axis in _GRADE_ALIASES:
        axis_filter: str | None = None
    else:
        axis_filter = axis

    result = evaluateCompany(company, detail=detail or (axis_filter is not None), basePeriod=basePeriod)
    if result is None:
        return None

    if axis_filter is not None:
        return _filterAxis(result, axis_filter)

    return result


def axes() -> dict[str, str]:
    """가용한 7축 목록."""
    return dict(_CREDIT_AXES)
