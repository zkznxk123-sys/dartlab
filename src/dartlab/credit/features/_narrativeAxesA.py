"""credit/features narrate 분리 — Repayment + CapitalStructure (A 그룹).

_narrativeAxes.py 731 줄 분할. narrateRepayment (158) + narrateCapitalStructure (85)
약 243 줄. _narrativeAxes.py 의 facade (Liquidity · CashFlow · BusinessStability ·
Reliability · DisclosureRisk · buildNarratives) 책임 유지.

BC: credit.features.narrative 모듈에서 두 함수 모두 import 가능 (re-export 체인).
순환 import 회피: _severity · _fmt · _fmtTril 헬퍼는 _narrativeAxes 의 정의를 함수 내부 lazy import.
"""

from __future__ import annotations

from dartlab.core.formatting import formatDecimal, formatKr
from dartlab.credit.features._narrativeTypes import AxisNarrative


def _severity(score):
    """lazy proxy → _narrativeAxes._severity (순환 import 회피)."""
    from dartlab.credit.features._narrativeAxes import _severity as _f

    return _f(score)


def _fmt(v, suffix="", decimals=1):
    """lazy proxy → _narrativeAxes._fmt."""
    from dartlab.credit.features._narrativeAxes import _fmt as _f

    return _f(v, suffix, decimals)


def _fmtTril(v):
    """lazy proxy → _narrativeAxes._fmtTril."""
    from dartlab.credit.features._narrativeAxes import _fmtTril as _f

    return _f(v)


def narrateRepayment(
    latest: dict,
    axisScore: float | None,
    sectorLabel: str,
    *,
    captive: bool = False,
    separateMetrics: dict | None = None,
) -> AxisNarrative:
    """축 1: 채무상환능력 서사 — EBITDA 이자보상 + Debt/EBITDA + 차입금 규모.

    Capabilities:
        EBITDA 이자보상배율 + Debt/EBITDA + FFO/Debt + 총차입금 규모를 업종
        기준표 위치와 결합해 신평사 수준의 한국어 해석 문장 (요약 + details
        list) 생성. 캡티브 금융 복합기업은 별도재무 보정 적용.

    Args:
        latest: 최신 분기 지표 dict. 주요 키:
            - ``ebitda`` (원), ``totalBorrowing`` (원), ``revenue`` (원)
            - ``ebitdaInterestCoverage`` (배)
            - ``debtToEbitda`` (배), ``ffoToDebt`` (%)
        axisScore: 채무상환능력 축 점수 (0~100, 0=최우량). None 이면 평가 불가.
        sectorLabel: 업종 분류 (예 ``"제조업"``).
        captive: 캡티브 금융 복합기업 여부. True 이면 별도 D/EBITDA 보정.
        separateMetrics: 별도 재무 dict. 캡티브 회사 제조 부문만 분리 평가용.

    Returns:
        AxisNarrative dataclass:
            - ``axisName`` (str): ``"채무상환능력"``
            - ``summary`` (str): 한 줄 요약
            - ``details`` (list[str]): 세부 해석
            - ``severity`` (str): ``"strong"``/``"adequate"``/``"weak"``/``"critical"``

    Raises:
        없음.

    Example:
        >>> n = narrateRepayment({"ebitda": 5e12, "totalBorrowing": 1e13,
        ...                       "ebitdaInterestCoverage": 15, "debtToEbitda": 2.0,
        ...                       "revenue": 3e14}, axisScore=15, sectorLabel="제조업")
        >>> n.severity, n.summary
        ('strong', '채무상환능력은 제조업 업종 기준 매우 우수하다.')

    Guide:
        ICR ≥ 100 = 무차입에 준 (이자비용 극소). Debt/EBITDA < 3 = 적정,
        > 5 = 장기 상환 부담. FFO/Debt > 40% = 우수 내부 현금창출. 캡티브
        금융 복합기업은 연결 D/EBITDA 보다 별도 D/EBITDA 가 핵심 (separate
        Metrics 입력).

    SeeAlso:
        - ``narrateCapitalStructure``: 자본구조 (부채비율) 서사
        - ``narrateLiquidity``: 유동성 (current/quick) 서사
        - ``narrateCashFlow``: 현금흐름 (OCF) 서사
        - ``credit.engine.evaluateCompany``: 본 함수 호출

    When:
        채무상환능력 narrative 가 필요할 때. ``buildNarratives`` 진입점.

    How:
        ebitda/ICR/Debt-EBITDA/FFO 추출 → 임계 분기 → details 누적 → 캡티브 보정 (separate
        D/EBITDA) → severity / summary.

    Requires:
        latest dict 의 필수 키 (ebitda, ebitdaInterestCoverage, debtToEbitda).

    AIContext:
        severity 만 단독 인용 금지 — summary + details (시계열 변화 포함) 함께
        노출. 캡티브 기업 (현대차/기아 등) 은 captive=True 누락 시 부채비율
        과대 평가.

    LLM Specifications:
        AntiPatterns:
            - ICR=999 같은 극단치를 그대로 인용 — "999배" 보다 "무차입 수준"
              표현 (본 함수가 자동 변환).
            - 캡티브 기업에서 captive=False 호출 — 금융자회사 차입금이
              제조업 차입금처럼 표시되는 오해 발생.
        OutputSchema:
            AxisNarrative ``{axisName, summary, details, severity}``.
        Prerequisites:
            latest dict 에 ebitda + ebitdaInterestCoverage 최소 보유.
        Freshness:
            latest = 최신 분기 (마감 후 30~45 일).
        Dataflow:
            latest dict → ICR/Debt-EBITDA/FFO 분기 룰 → details 누적 →
            severity (axisScore 기반) → summary 합성.
        TargetMarkets: KR (DART 표준 계정), US 일부 (EBITDA 표준 동일).
    """
    details = []
    sev = _severity(axisScore)

    # 금액 맥락
    ebitda = latest.get("ebitda")
    totalBorrowing = latest.get("totalBorrowing")
    revenue = latest.get("revenue")

    if ebitda is not None and revenue is not None:
        if ebitda > 0:
            details.append(f"매출 {_fmtTril(revenue)} 기반 EBITDA {_fmtTril(ebitda)}을 창출한다.")
        elif ebitda < 0:
            details.append(
                f"매출 {_fmtTril(revenue)} 대비 EBITDA {_fmtTril(ebitda)}로 본업에서 적자다. "
                f"다만 이는 지주사/특수 구조에서는 배당수입 등 영업외 현금흐름으로 보완될 수 있다."
            )

    icr = latest.get("ebitdaInterestCoverage")
    if icr is not None:
        if icr >= 100:
            # 이자비용이 극소 — "999배"보다 의미 있는 표현
            if totalBorrowing:
                details.append(
                    f"총차입금 {_fmtTril(totalBorrowing)} 대비 이자 부담이 사실상 없어 무차입에 준하는 재무구조다."
                )
            else:
                details.append("이자 부담이 사실상 없어 무차입에 준하는 재무구조다.")
        elif icr > 10:
            details.append(f"이자보상배율 {_fmt(icr)}배로 충분한 이자 지급 여력을 보유한다.")
        elif icr > 5:
            details.append(f"이자보상배율 {_fmt(icr)}배로 양호한 채무상환 여력이 있다.")
        elif icr > 2:
            details.append(f"이자보상배율 {_fmt(icr)}배로 이자 지급은 가능하나 여유는 제한적이다.")
        elif icr > 1:
            details.append(f"이자보상배율 {_fmt(icr)}배로 이자 지급 여력이 빠듯하다. 수익성 악화 시 위험.")
        else:
            details.append(f"이자보상배율 {_fmt(icr)}배로 이자 지급 능력이 부족하다.")

    de = latest.get("debtToEbitda")
    if de is not None:
        if de < 1:
            details.append(f"Debt/EBITDA {_fmt(de)}배로 차입금을 1년 내 상환 가능한 수준이다.")
        elif de < 3:
            details.append(f"Debt/EBITDA {_fmt(de)}배로 차입금 부담이 적정하다.")
        elif de < 5:
            details.append(f"Debt/EBITDA {_fmt(de)}배로 차입금 부담이 다소 높다.")
        else:
            details.append(f"Debt/EBITDA {_fmt(de)}배로 차입금 상환에 장기간이 소요된다.")

    ffo = latest.get("ffoToDebt")
    if ffo is not None and ffo < 999:
        if ffo > 40:
            details.append(f"FFO/총차입금 {_fmt(ffo, '%', 0)}로 우수한 내부 현금 창출력을 보인다.")
        elif ffo > 20:
            details.append(f"FFO/총차입금 {_fmt(ffo, '%', 0)}로 양호한 부채상환 능력이다.")
        elif ffo > 10:
            details.append(f"FFO/총차입금 {_fmt(ffo, '%', 0)}로 부채상환 능력이 제한적이다.")
        elif ffo > 0:
            details.append(f"FFO/총차입금 {_fmt(ffo, '%', 0)}로 부채상환 능력이 취약하다.")

    # 캡티브 맥락: 별도 기준 D/EBITDA 참고
    if captive and separateMetrics:
        sepDE = separateMetrics.get("separateDebtToEbitda")
        if sepDE is not None:
            details.append(f"참고: 별도 기준 D/EBITDA는 {sepDE:.1f}x로, 연결 대비 크게 양호하다.")

    summary = f"채무상환능력은 {sectorLabel} 업종 기준 "
    if sev == "strong":
        summary += "매우 우수하다."
    elif sev == "adequate":
        summary += "양호한 수준이다."
    elif sev == "weak":
        summary += "보통 이하 수준으로 모니터링이 필요하다."
    else:
        summary += "취약하여 즉각적인 개선이 요구된다."

    return AxisNarrative("채무상환능력", summary, details, sev)


def narrateCapitalStructure(
    latest: dict,
    axisScore: float | None,
    *,
    captive: bool = False,
    separateMetrics: dict | None = None,
) -> AxisNarrative:
    """축 2: 자본구조 서사 생성.

    Capabilities:
        부채비율 + 차입금의존도 + 순차입금/자기자본 + 차입구조 (단기/장기) 를 업종 기준표 위치와
        결합해 자본구조 narrative 생성. captive=True 일 때 별도 부채비율 단서 자동 첨부.

    부채비율, 차입금의존도, 순차입금/자기자본 등을
    업종 기준표 위치와 결합하여 자본구조 해석 문장을 생성한다.

    Parameters
    ----------
    latest : dict
        최신 분기 지표. 주요 키: ``debtRatio`` (%),
        ``borrowingDependency`` (%), ``netDebtToEquity`` (%).
    axisScore : float | None
        자본구조 축 점수 (점). None이면 평가 불가.
    captive : bool
        캡티브 금융 복합기업 여부.
    separateMetrics : dict | None
        별도 재무제표 기반 지표.

    Returns
    -------
    AxisNarrative
        axisName : str — 축 이름 (``"자본구조"``)
        summary : str — 한 줄 요약 문장
        details : list[str] — 세부 해석 문장 목록
        severity : str — 심각도 (``"strong"`` / ``"moderate"`` / ``"weak"`` / ``"critical"``)

    Raises:
        없음.

    Example:
        >>> narrateCapitalStructure({"debtRatio": 80, "borrowingDependency": 35}, 12)

    Guide:
        부채비율 < 100% = 우수 (지역/업종 차이 큼). 캡티브 회사는 separate debt ratio 가 핵심.

    When:
        자본구조 narrative 가 필요할 때. ``buildNarratives`` 진입점.

    How:
        debtRatio/borrowingDependency/netDebtToEquity → 임계 분기 → captive 별도 보정 →
        severity / summary.

    Requires:
        - latest dict 의 debtRatio (필수) + borrowingDependency / netDebtToEquity (optional)

    See Also:
        - ``dartlab.credit.features._narrativeAxesA.narrateRepayment`` : 부채상환 narrative
        - ``dartlab.credit.features._narrativeAxes.buildNarratives`` : 본 함수 사용자

    AIContext:
        부채비율 단독 인용 금지 — borrowingDependency / netDebtToEquity 결합. captive 회사는
        "별도 부채비율" 단서 명시.
    """
    details = []
    sev = _severity(axisScore)

    dr = latest.get("debtRatio")
    if dr is not None:
        if dr < 50:
            details.append(f"부채비율 {_fmt(dr, '%', 0)}로 재무구조가 매우 보수적이다.")
        elif dr < 100:
            details.append(f"부채비율 {_fmt(dr, '%', 0)}로 건전한 재무구조를 유지한다.")
        elif dr < 200:
            details.append(f"부채비율 {_fmt(dr, '%', 0)}로 적정 수준의 레버리지를 활용한다.")
        elif dr < 300:
            details.append(f"부채비율 {_fmt(dr, '%', 0)}로 레버리지가 다소 높은 편이다.")
        else:
            details.append(f"부채비율 {_fmt(dr, '%', 0)}로 과도한 레버리지를 사용하고 있다.")

    bd = latest.get("borrowingDependency")
    if bd is not None:
        if bd > 30:
            details.append(f"차입금의존도 {_fmt(bd, '%', 0)}로 외부 자금 의존도가 높다.")
        elif bd > 15:
            details.append(f"차입금의존도 {_fmt(bd, '%', 0)}로 적정 수준이다.")

    nde = latest.get("netDebtToEbitda")
    if nde is not None:
        if nde < 0:
            details.append("순차입금이 마이너스(순현금 포지션)로 실질적 부채 부담이 없다.")
        elif nde < 2:
            details.append(f"순차입금/EBITDA {_fmt(nde)}배로 실질 부채 부담이 낮다.")

    # 캡티브 맥락: 별도 기준 부채비율 참고
    if captive and separateMetrics:
        sepDR = separateMetrics.get("separateDebtRatio")
        if sepDR is not None:
            details.append(
                f"참고: 별도 재무 기준 부채비율은 {sepDR:.0f}%로, "
                f"연결({dr:.0f}%) 대비 크게 낮다. "
                "이는 금융자회사 차입금이 연결에 포함되기 때문이다."
            )

    summary = "자본구조는 "
    if sev == "strong":
        summary += "매우 건전하다."
    elif sev == "adequate":
        summary += "양호하다."
    elif sev == "weak":
        summary += "레버리지 부담이 있다."
    else:
        summary += "과도한 부채로 구조적 위험이 존재한다."

    return AxisNarrative("자본구조", summary, details, sev)
