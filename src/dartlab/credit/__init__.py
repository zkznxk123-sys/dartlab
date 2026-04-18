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

src/dartlab/analysis/CREDIT.md 참조.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

# ── 7축 레지스트리 (Phase 8 A4: 4엔진 통일 — @dataclass _AxisEntry) ──


@dataclass(frozen=True)
class _AxisEntry:
    """credit 축 메타데이터. analysis/quant/macro 와 동일 패턴."""

    axis: str  # 영문 키 (정규)
    label: str  # 한글 라벨 = 과거 _CREDIT_AXES 의 fullName
    description: str
    example: str
    group: str = "dCR"  # 그룹 분류 (가이드 DF 표준 컬럼)


_AXIS_REGISTRY: dict[str, _AxisEntry] = {
    "grade": _AxisEntry(
        axis="grade",
        label="등급",
        description="dCR 종합 등급 + 점수 + 7축 가중평균 (default)",
        example='c.credit("등급")',
        group="dCR",
    ),
    "repayment": _AxisEntry(
        axis="repayment",
        label="채무상환능력",
        description="이자보상배율, 부채상환능력",
        example='c.credit("채무상환")',
        group="dCR",
    ),
    "leverage": _AxisEntry(
        axis="leverage",
        label="자본구조",
        description="부채비율, 자본 안정성",
        example='c.credit("자본구조")',
        group="dCR",
    ),
    "liquidity": _AxisEntry(
        axis="liquidity",
        label="유동성",
        description="유동비율, 단기 상환 여력",
        example='c.credit("유동성")',
        group="dCR",
    ),
    "cashflow": _AxisEntry(
        axis="cashflow",
        label="현금흐름",
        description="OCF, FCF 안정성",
        example='c.credit("현금흐름")',
        group="dCR",
    ),
    "business": _AxisEntry(
        axis="business",
        label="사업안정성",
        description="매출 변동성, 사업 지속성",
        example='c.credit("사업안정성")',
        group="dCR",
    ),
    "reliability": _AxisEntry(
        axis="reliability",
        label="재무신뢰성",
        description="감사의견, 회계 일관성",
        example='c.credit("재무신뢰성")',
        group="dCR",
    ),
    "disclosure": _AxisEntry(
        axis="disclosure",
        label="공시리스크",
        description="공시 변경, 정정 빈도",
        example='c.credit("공시리스크")',
        group="dCR",
    ),
}

# 하위 호환 — 기존 코드가 _CREDIT_AXES (한글키→fullName) 참조하는 곳용.
_CREDIT_AXES: dict[str, str] = {
    "채무상환": "채무상환능력",
    "자본구조": "자본구조",
    "유동성": "유동성",
    "현금흐름": "현금흐름",
    "사업안정성": "사업안정성",
    "재무신뢰성": "재무신뢰성",
    "공시리스크": "공시리스크",
}

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

    공시 재무제표만으로 독립 신용등급(dCR)을 산출하는 엔진의 축 카탈로그.
    외부 API 키 불필요 — DART/EDGAR 재무 데이터 기반.

    Returns
    -------
    polars.DataFrame
        axis : str — 영문 축 키 (grade, repayment, leverage, …)
        label : str — 한글 라벨 (등급, 채무상환능력, 자본구조, …)
        description : str — 축 설명
        example : str — 호출 예시
        group : str — 그룹 분류 (dCR)
        apiKey : str — API 키 필요 여부 ("불필요" — 재무 데이터 기반)

    Examples
    --------
    >>> import dartlab
    >>> dartlab.credit()                        # 이 가이드
    >>> dartlab.credit("005930")                # 삼성전자 종합 등급
    >>> dartlab.credit("005930", "채무상환")     # 채무상환 축만
    >>> c = dartlab.Company("005930")
    >>> c.credit()                              # Company-bound 가이드
    >>> c.credit("등급")                        # 종합 등급
    >>> c.credit("채무상환", detail=True)        # 채무상환 축 상세
    """
    import polars as pl

    rows = [asdict(e) for e in _AXIS_REGISTRY.values()]
    for row in rows:
        row["apiKey"] = "불필요"
    df = pl.DataFrame(rows)

    # 빠른 시작 안내 출력
    _lines = [
        "",
        "dCR — 독립 신용등급 (7축 정량 스코어링)",
        "",
        "━━━ 빠른 시작 ━━━",
        '  c = dartlab.Company("005930")',
        '  c.credit("등급")                        # dCR 종합 등급',
        '  c.credit("채무상환")                     # 채무상환능력 축',
        '  c.credit("등급", detail=True)            # 7축 상세 + 시계열',
        "",
        "━━━ 7축 ━━━",
        "  채무상환능력 · 자본구조 · 유동성 · 현금흐름",
        "  사업안정성 · 재무신뢰성 · 공시리스크",
        "",
        "━━━ 데이터 ━━━",
        "  재무제표: DART/EDGAR 공시 (API 키 불필요)",
        "  등급 범위: dCR-AAA ~ dCR-D",
        "",
    ]
    print("\n".join(_lines))

    return df


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
    stockCode : str | None
        종목코드 또는 ticker. None이면 7축 가이드 DataFrame 반환.
    axis : str | None
        축 이름 ("등급" → 종합, "채무상환"/"자본구조"/"유동성"/"현금흐름"/
        "사업안정성"/"재무신뢰성"/"공시리스크" → 해당 축만).
        영문 alias("repayment", "leverage" 등)도 지원.
    detail : bool
        True이면 7축 상세 + 모든 지표 시계열 + 서사(narrative) 포함.
    basePeriod : str | None
        분석 기준 기간 (예: "2024"). None이면 최신.

    Returns
    -------
    DataFrame | dict | None
        - stockCode=None → 가이드 DataFrame (axis, label, description, example, group)
        - axis="등급" 또는 None+stockCode → 종합 등급 dict

          grade : str — dCR 등급 (예: "dCR-AA+")
          score : float — 위험 점수 (0=최우량, 100=최위험) (점)
          healthScore : float — 건전성 점수 (100-score) (점)
          axes : list[dict] — 7축 상세 (name, score, weight, metrics)
          eCR : str | None — 현금흐름등급
          outlook : str — 전망 ("안정적"/"긍정적"/"부정적")

        - axis=축이름 → 해당 축 dict

          axis : str — 축 풀네임
          score : float — 해당 축 위험 점수 (점)
          weight : int — 가중치 (%)
          metrics : list[dict] — 개별 지표 (name, value, score)

    Examples
    --------
    >>> import dartlab
    >>> dartlab.credit("005930")                # 삼성전자 종합
    >>> dartlab.credit("005930", "채무상환")     # 채무상환 축만
    >>> dartlab.credit()                        # 가이드 DataFrame
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
    company,
    axis: str | None = None,
    *,
    detail: bool = False,
    basePeriod: str | None = None,
    overrides: dict | None = None,
):
    """Company 객체로 신용등급 산출 (Company-bound용).

    Parameters
    ----------
    company : Company
        DartCompany 또는 EdgarCompany 인스턴스.
    axis : str | None
        None → 가이드 DataFrame (self-discovery).
        "등급"/"grade" → 종합 등급 dict.
        "채무상환"/"자본구조" 등 → 해당 축 dict.
    detail : bool
        True이면 7축 상세 + 서사 + 시계열 포함.
    basePeriod : str | None
        분석 기준 기간 (예: "2024"). None이면 최신.
    overrides : dict | None
        AI/사용자 시나리오 가정 교체. core/overrides.py CREDIT_KEYS 참조.
        예: ``{"debtRatio": 150}`` → 부채비율을 150%로 가정한 시나리오.

    Returns
    -------
    DataFrame | dict | None
        axis=None → 가이드 DataFrame.
        axis 지정 시 → 해당 축 또는 종합 등급 dict.
        overrides 적용 시 결과 dict에 ``assumptions`` 키가 추가됨.

    Examples
    --------
    >>> c = dartlab.Company("005930")
    >>> c.credit("등급")                      # 종합
    >>> c.credit("채무상환", detail=True)      # 채무상환 축 상세
    """
    if axis is None:
        return guide()

    from dartlab.credit.engine import evaluateCompany

    # "등급"/"grade" 등 종합 alias는 axis로 처리하지 않음
    if axis in _GRADE_ALIASES:
        axis_filter: str | None = None
    else:
        axis_filter = axis

    # overrides 전달 (engine 이 소비 가능하면 사용, 아니면 TypeError fallback 없이 무시)
    kwargs: dict = {}
    if overrides:
        kwargs["overrides"] = overrides
    try:
        result = evaluateCompany(
            company,
            detail=detail or (axis_filter is not None),
            basePeriod=basePeriod,
            **kwargs,
        )
    except TypeError:
        # engine 이 아직 overrides 수용 전 — 경고 없이 자동 계산
        result = evaluateCompany(company, detail=detail or (axis_filter is not None), basePeriod=basePeriod)
    if result is None:
        return None

    if axis_filter is not None:
        result = _filterAxis(result, axis_filter)

    # assumptions 투명화 — 4 엔진 공통 utility (core/overrides.py)
    if isinstance(result, dict):
        from dartlab.core.overrides import buildAssumptions

        assumptions = buildAssumptions(result, engine="credit", overrides=overrides)
        if assumptions:
            result["assumptions"] = assumptions

    return result


def axes() -> dict[str, str]:
    """가용한 7축 목록."""
    return dict(_CREDIT_AXES)
