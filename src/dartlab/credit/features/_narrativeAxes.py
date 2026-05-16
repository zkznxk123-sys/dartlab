"""credit/features/narrative 7 축 narrate 함수 분리.

credit/features/narrative.py 가 823 줄 god module 이라 7 축 서사 함수를 분리.
identity 보존을 위해 narrative.py 가 본 모듈에서 re-export 한다.

축별 narrate 함수:
- narrateRepayment — 채무상환능력 (이자보상배율 + Debt/EBITDA)
- narrateCapitalStructure — 자본구조 (부채비율 + 차입금의존도)
- narrateLiquidity — 유동성 (current/quick ratio)
- narrateCashFlow — 현금흐름 (OCF + FCF + CFO 안정성)
- narrateBusinessStability — 사업안정성 (매출 변동성)
- narrateReliability — 재무신뢰성 (감사의견 + 발생주의 비율)
- narrateDisclosureRisk — 공시리스크 (정정공시 + Beneish M-Score)
"""

from __future__ import annotations

from dartlab.core.formatting import formatDecimal, formatKr
from dartlab.credit.features._narrativeTypes import AxisNarrative


def _severity(score: float | None) -> str:
    if score is None:
        return "adequate"
    if score < 10:
        return "strong"
    if score < 25:
        return "adequate"
    if score < 45:
        return "weak"
    return "critical"


def _fmt(v, suffix="", decimals=1) -> str:
    """고정 소수 + suffix (None → N/A)."""
    return formatDecimal(v, decimals=decimals, suffix=suffix, nullStr="N/A")


def _fmtTril(v) -> str:
    """금액을 조/억 단위로 변환 (원 접미사 포함)."""
    return formatKr(v, withWon=True, nullStr="N/A")


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


def narrateLiquidity(latest: dict, axisScore: float | None) -> AxisNarrative:
    """축 3: 유동성."""
    details = []
    sev = _severity(axisScore)

    cr = latest.get("currentRatio")
    if cr is not None:
        if cr > 200:
            details.append(f"유동비율 {_fmt(cr, '%', 0)}로 단기 유동성이 매우 우수하다.")
        elif cr > 150:
            details.append(f"유동비율 {_fmt(cr, '%', 0)}로 단기 유동성이 양호하다.")
        elif cr > 100:
            details.append(f"유동비율 {_fmt(cr, '%', 0)}로 단기 유동성이 적정하다.")
        else:
            details.append(f"유동비율 {_fmt(cr, '%', 0)}로 단기 유동성이 부족하다.")

    stdr = latest.get("shortTermDebtRatio")
    if stdr is not None and stdr > 50:
        details.append(f"단기차입금 비중 {_fmt(stdr, '%', 0)}로 차환 리스크가 존재한다.")

    cashR = latest.get("cashRatio")
    if cashR is not None and cashR > 30:
        details.append(f"현금비율 {_fmt(cashR, '%', 0)}로 즉시 동원 가능한 현금이 충분하다.")

    # 유동성 지표 모순 설명: 유동비율/현금비율은 좋은데 단기차입금비중이 높은 경우
    if cr is not None and cr > 150 and stdr is not None and stdr > 50:
        details.append(
            f"유동비율({_fmt(cr, '%', 0)})과 현금비율은 우수하나, "
            f"단기차입금 비중({_fmt(stdr, '%', 0)})이 높아 차환 시점의 유동성 관리가 필요하다. "
            f"현금 보유량이 충분하므로 실질적 차환 위험은 낮다."
        )

    summary = "유동성은 "
    if sev == "strong":
        summary += "매우 충분하다."
    elif sev == "adequate":
        summary += "적정 수준이다."
    elif sev == "weak":
        summary += "주의가 필요한 수준이다."
    else:
        summary += "부족하여 차환/유동성 위험이 높다."

    return AxisNarrative("유동성", summary, details, sev)


def narrateCashFlow(
    latest: dict,
    axisScore: float | None,
    metrics: dict,
    *,
    captive: bool = False,
) -> AxisNarrative:
    """축 4: 현금흐름 서사 생성.

    OCF/매출, FCF 추이, 현금흐름 패턴(+/-/-)을 해석하여
    현금 창출력과 투자 부담에 대한 서사를 생성한다.

    Parameters
    ----------
    latest : dict
        최신 분기 지표. 주요 키: ``ocfToSales`` (%),
        ``fcf`` (원), ``ocf`` (원).
    axisScore : float | None
        현금흐름 축 점수 (점). None이면 평가 불가.
    metrics : dict
        전체 메트릭스 딕셔너리 (추이 분석용).
    captive : bool
        캡티브 금융 복합기업 여부.

    Returns
    -------
    AxisNarrative
        axisName : str — 축 이름 (``"현금흐름"``)
        summary : str — 한 줄 요약 문장
        details : list[str] — 세부 해석 문장 목록
        severity : str — 심각도 (``"strong"`` / ``"moderate"`` / ``"weak"`` / ``"critical"``)
    """
    details = []
    sev = _severity(axisScore)

    os = latest.get("ocfToSales")
    if os is not None:
        if os > 100:
            # 지주사 등: 매출 < OCF (배당수입/지분법이 OCF에 포함)
            details.append(
                f"OCF/매출 {_fmt(os, '%')}로 자체 매출 대비 현금흐름이 매우 크다. "
                f"이는 자회사 배당수입 등 영업외 현금이 포함된 것으로 판단된다."
            )
        elif os > 15:
            details.append(f"OCF/매출 {_fmt(os, '%')}로 매출 대비 현금 창출력이 우수하다.")
        elif os > 5:
            details.append(f"OCF/매출 {_fmt(os, '%')}로 현금 창출이 양호하다.")
        elif os > 0:
            details.append(f"OCF/매출 {_fmt(os, '%')}로 현금 창출이 제한적이다.")
        else:
            details.append(f"OCF/매출 {_fmt(os, '%')}로 영업에서 현금이 유출되고 있다.")

    fcf = latest.get("fcf")
    if fcf is not None:
        if fcf > 0:
            details.append("투자 이후에도 잉여현금흐름(FCF)이 양수로 자체 성장 여력이 있다.")
        else:
            details.append("투자 부담으로 잉여현금흐름(FCF)이 음수이다.")

    # OCF 추세
    history = metrics.get("history", [])
    if len(history) >= 3:
        ocfs = [h.get("ocf") for h in history[:3]]
        if all(o is not None and o > 0 for o in ocfs):
            details.append("영업현금흐름이 3기 연속 양수로 안정적이다.")

    # 캡티브 맥락: OCF 음수는 금융자회사 대출 유출 포함 가능
    if captive:
        ocfVal = latest.get("ocf")
        if ocfVal is not None and ocfVal < 0:
            details.append(
                "참고: OCF가 음수인 것은 연결 기준으로 금융자회사의 대출 원금 유출이 포함되기 때문이다. "
                "제조 모회사 단독으로는 OCF가 정상 범위일 수 있다."
            )

    summary = "현금흐름 창출 능력은 "
    if sev == "strong":
        summary += "우수하다."
    elif sev == "adequate":
        summary += "양호하다."
    elif sev == "weak":
        summary += "보통 수준이다."
    else:
        summary += "취약하여 외부 조달 의존도가 높다."

    return AxisNarrative("현금흐름", summary, details, sev)


def narrateBusinessStability(biz: dict, axisScore: float | None) -> AxisNarrative:
    """축 5: 사업 안정성."""
    details = []
    sev = _severity(axisScore)

    revCV = biz.get("revenueCV")
    if revCV is not None:
        if revCV < 10:
            details.append(f"매출 변동계수 {_fmt(revCV, '%')}로 매출이 매우 안정적이다.")
        elif revCV < 20:
            details.append(f"매출 변동계수 {_fmt(revCV, '%')}로 적정한 안정성을 보인다.")
        else:
            details.append(f"매출 변동계수 {_fmt(revCV, '%')}로 실적 변동성이 크다.")

    latestRev = biz.get("latestRevenue")
    if latestRev is not None:
        revTril = latestRev / 1e12
        if revTril > 10:
            details.append(f"매출 규모 {revTril:.0f}조원으로 대형 기업의 사업 안정성을 보유한다.")
        elif revTril > 1:
            details.append(f"매출 규모 {revTril:.1f}조원 수준이다.")

    hhi = biz.get("segmentHHI")
    if hhi is not None:
        if hhi < 1500:
            details.append("사업 부문이 분산되어 다각화 효과가 있다.")
        elif hhi > 5000:
            details.append("사업이 단일 부문에 집중되어 있어 분산 효과가 제한적이다.")

    summary = "사업 안정성은 "
    if sev == "strong":
        summary += "매우 높다."
    elif sev == "adequate":
        summary += "양호한 수준이다."
    else:
        summary += "변동성이 존재한다."

    return AxisNarrative("사업안정성", summary, details, sev)


def narrateReliability(
    rel: dict,
    auditOpinion: str | None,
    axisScore: float | None,
    *,
    captive: bool = False,
) -> AxisNarrative:
    """축 6: 재무 신뢰성."""
    details = []
    sev = _severity(axisScore)

    m = rel.get("beneishMScore")
    if m is not None:
        if m < -2.22:
            details.append("Beneish M-Score 기준 이익 조작 가능성이 낮다.")
        elif m > -1.78:
            details.append("Beneish M-Score가 조작 가능성 구간에 해당하여 주의가 필요하다.")

    f = rel.get("piotroskiFScore")
    if f is not None:
        if f >= 7:
            details.append(f"Piotroski F-Score {f}/9로 재무 펀더멘탈이 강건하다.")
        elif f <= 3:
            details.append(f"Piotroski F-Score {f}/9로 재무 펀더멘탈이 취약하다.")
            if captive:
                details.append(
                    "다만, 캡티브 금융 연결 효과로 OCF/유동비율 등이 왜곡되어 "
                    "F-Score가 실제 모회사 체력보다 낮게 산출될 수 있다."
                )

    if auditOpinion:
        if "적정" in auditOpinion and "부적정" not in auditOpinion and "한정" not in auditOpinion:
            details.append("감사의견은 적정으로 재무제표 신뢰성에 문제가 없다.")
        elif "한정" in auditOpinion:
            details.append("감사의견이 한정으로 재무제표 일부 항목에 대한 신뢰성 우려가 있다.")
        elif "부적정" in auditOpinion or "의견거절" in auditOpinion:
            details.append("감사의견이 비적정으로 재무제표 전반의 신뢰성에 심각한 문제가 있다.")

    summary = "재무 신뢰성은 "
    if sev == "strong":
        summary += "우수하다."
    elif sev == "adequate":
        summary += "양호하다."
    else:
        summary += "주의가 필요하다."

    return AxisNarrative("재무신뢰성", summary, details, sev)


def narrateDisclosureRisk(dr: dict | None, axisScore: float | None) -> AxisNarrative:
    """축 7: 공시 리스크."""
    details = []
    sev = _severity(axisScore)

    if dr is None:
        return AxisNarrative(
            "공시리스크", "공시 리스크 신호가 감지되지 않았다.", ["scan 데이터 범위 내 특이 신호 없음."], "strong"
        )

    chronic = dr.get("chronicYears") or dr.get("chronic_years", 0)
    if chronic >= 3:
        details.append(f"우발부채가 {chronic}년 연속 증가하여 만성화 징후가 있다.")
    elif chronic >= 1:
        details.append("우발부채가 증가 추세이나 아직 만성 수준은 아니다.")

    risk = dr.get("riskKeyword") or dr.get("risk_keyword", 0)
    if risk > 0:
        details.append(f"리스크 키워드(횡령/배임/과징금 등)가 {risk}건 감지되었다.")

    if not details:
        details.append("특이한 공시 리스크 신호는 감지되지 않았다.")

    summary = "공시 리스크는 "
    if sev == "strong":
        summary += "낮은 수준이다."
    elif sev == "adequate":
        summary += "양호하다."
    else:
        summary += "모니터링이 필요하다."

    return AxisNarrative("공시리스크", summary, details, sev)


# ═══════════════════════════════════════════════════════════
# 통합
# ═══════════════════════════════════════════════════════════


def buildNarratives(
    result: dict,
    *,
    captive: bool = False,
    holding: bool = False,
    separateMetrics: dict | None = None,
) -> list[AxisNarrative]:
    """engine.py evaluateCompany 결과에서 7축 전체 서사 생성.

    Parameters
    ----------
    captive : bool
        캡티브 금융 복합기업 여부. True이면 연결 재무 왜곡 맥락 문장을 추가한다.
    holding : bool
        지주사 여부. (현재 축별 서사에서 직접 사용하지 않으나 향후 확장용.)
    separateMetrics : dict | None
        별도 재무제표 지표. captive일 때 연결/별도 대비 참고 문장에 사용한다.
    """
    axes = result.get("axes", [])
    latest = {}
    metricsHistory = result.get("metricsHistory", [])
    if metricsHistory:
        latest = metricsHistory[0]

    biz = result.get("businessStability", {})
    rel = result.get("reliability", {})
    audit = result.get("auditOpinion")
    dr = result.get("disclosureRisk")
    sector = result.get("sector", "")

    def _axisScore(name):
        for a in axes:
            if a.get("name") == name:
                return a.get("score")
        return None

    return [
        narrateRepayment(
            latest,
            _axisScore("채무상환능력"),
            sector,
            captive=captive,
            separateMetrics=separateMetrics,
        ),
        narrateCapitalStructure(
            latest,
            _axisScore("자본구조"),
            captive=captive,
            separateMetrics=separateMetrics,
        ),
        narrateLiquidity(latest, _axisScore("유동성")),
        narrateCashFlow(
            latest,
            _axisScore("현금흐름"),
            {"history": metricsHistory},
            captive=captive,
        ),
        narrateBusinessStability(biz or {}, _axisScore("사업안정성")),
        narrateReliability(rel or {}, audit, _axisScore("재무신뢰성"), captive=captive),
        narrateDisclosureRisk(dr, _axisScore("공시리스크")),
    ]


__all__ = [
    "narrateBusinessStability",
    "narrateCapitalStructure",
    "narrateCashFlow",
    "narrateDisclosureRisk",
    "narrateLiquidity",
    "narrateReliability",
    "narrateRepayment",
]
