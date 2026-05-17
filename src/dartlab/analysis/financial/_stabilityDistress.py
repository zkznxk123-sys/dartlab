"""stability.py 부실 진단 calc 분리 — Altman Z + 5 모델 앙상블.

분리 이유: stability.py 945 줄. calcDistressScore (Altman Z 시계열 194 줄) +
calcDistressEnsemble (5 모델 다수결 164 줄) 가 약 360 줄. 별도 모듈로 빼서
stability.py 의 facade 책임 (레버리지/이자보상/만기/플래그) 만 유지.

BC: stability 모듈에서 두 함수 모두 import 가능 (re-export).
"""

from __future__ import annotations

from dartlab.analysis.financial.companyContext import getRatios
from dartlab.core.memory import memoizedCalc
from dartlab.core.utils.helpers import (
    MAX_RATIO_YEARS,
    annualColsFromPeriods,
    toDictBySnakeId,
)

_MAX_YEARS = MAX_RATIO_YEARS


@memoizedCalc
def calcDistressScore(company, *, basePeriod: str | None = None) -> dict | None:
    """Altman Z-Score (1968) 시계열 + 5 변수 분해 — 부실 위험 정량 진단.

    Capabilities:
        Altman (1968, JF) "Financial Ratios, Discriminant Analysis and the
        Prediction of Corporate Bankruptcy" 의 Z-Score 시계열 산출. 5 변수
        (X1~X5) + zScore + zone 분류. 비상장 회사는 Z''-Score (X4 변형) 자동
        사용. 부도 예측 학술 표준.

    Args:
        company: Company 객체.
        basePeriod: 기준 기간. None 시 최신.

    Returns:
        dict | None:
            - ``history`` (list[dict]): 연도별 13 키 (period + 6 BS/IS 원본
              + 5 X 변수 + zScore + zModel + zone)
            - ``latestScore`` (float): 최신 Z-Score
            - ``zone`` (str): "안전"/"회색"/"위험"/"판별 불가"
            - ``diagnosticMeta`` (dict): 진단 메타

    Raises:
        없음.

    Example:
        >>> r = calcDistressScore(Company("005930"))
        >>> r["latestScore"], r["zone"]
        (3.2, '안전')

    Guide:
        Z-Score 임계 (Altman 1968 원형):
        - Z > 2.99: 안전 (safe zone)
        - 1.81 < Z < 2.99: 회색 (grey zone)
        - Z < 1.81: 위험 (distress zone)
        Z''-Score (비상장/제조업 외): 2.6 / 1.1 임계. KR 대기업 평균 ~ 3.5,
        US 대기업 ~ 4.0. distress zone 2~3 년 연속이면 부도 가능성 매우 높음.

    When:
        부실 위험 정량 진단, 신용 평가 보조 시점.

    How:
        BS/IS + 시가총액 → 5 X 변수 → Z = 1.2X1 + 1.4X2 + 3.3X3 + 0.6X4 + 1.0X5.

    SeeAlso:
        - ``analyzeHealth``: Z-Score 포함 종합 건전성
        - ``calcDistressEnsemble``: Altman + Ohlson + Piotroski + CHS 합성
        - ``dartlab.synth.distress.chsModel.calcCHS``: 현대 표준 (Campbell 2008)
        - Altman, E. (1968) "Financial Ratios, Discriminant Analysis"

    Requires:
        BS (자산총계, 운전자본, 이익잉여금, 부채총계) + IS (매출/EBIT)
        + 시가총액 (시장 데이터).

    AIContext:
        Z-Score 절대값 + zone + history 추세 함께 인용. 단년도 위험 진입은
        일회성 (M&A/적자) 가능, 2 년 연속 distress zone 가 진짜 신호.
        Altman 1968 원형은 US 제조업 — KR/금융업 응용 시 Z''-Score 권장.

    LLM Specifications:
        AntiPatterns:
            - Z-Score 1.5 단년도 → "부도 임박" 단정 — 2~3 년 연속 distress
              zone 확인 필수.
            - 금융업/신규 IPO 회사 → Altman Z 적용 부적합. 본 함수가 자동
              Z''-Score 분기.
        OutputSchema:
            ``{history: list[dict 13키], latestScore: float, zone: str,
            diagnosticMeta: dict}``.
        Prerequisites:
            BS/IS 시계열 + 시가총액 (gather).
        Freshness:
            BS/IS 분기, 시가총액 일.
        Dataflow:
            BS/IS → 6 원본 (자산/WC/RE/EBIT/매출/부채) + 시가총액 → 5 X 변수
            → Z = 1.2X1 + 1.4X2 + 3.3X3 + 0.6X4 + 1.0X5 → zone 분류.
        TargetMarkets: KR (DART), US (EDGAR — Altman 원형 최적).
    """
    bsResult = company.select(
        "BS", ["자산총계", "유동자산", "유동부채", "부채총계", "이익잉여금", "미처분이익잉여금(결손금)"]
    )
    isResult = company.select("IS", ["영업이익", "매출액"])

    bsParsed = toDictBySnakeId(bsResult)
    isParsed = toDictBySnakeId(isResult)
    if bsParsed is None or isParsed is None:
        return None

    bsData, bsPeriods = bsParsed
    isData, _ = isParsed

    taRow = bsData.get("total_assets", {})
    caRow = bsData.get("current_assets", {})
    clRow = bsData.get("current_liabilities", {})
    tlRow = bsData.get("total_liabilities", {})
    from dartlab.core.utils.helpers import mergeRows

    reRow = mergeRows(bsData.get("retained_earnings"), bsData.get("unappropriated_retained_earnings_deficit"))
    opRow = isData.get("operating_profit", {})
    revRow = isData.get("sales", {})

    # 시가총액 (X4용) -- ratios에서 가져옴
    ratios = getRatios(company)
    marketCap = ratios.marketCap if ratios else None

    yCols = annualColsFromPeriods(bsPeriods, basePeriod, _MAX_YEARS)
    if not yCols:
        return None
    history = []
    for col in yCols:
        a = taRow.get(col)
        ca = caRow.get(col)
        cl = clRow.get(col)
        tl = tlRow.get(col)
        re = reRow.get(col)
        ebit = opRow.get(col)
        rev = revRow.get(col)

        if a is None or a == 0:
            continue

        wc = (ca or 0) - (cl or 0)
        x1 = round(wc / a, 4) if a else None
        x2 = round(re / a, 4) if re is not None and a else None
        x3 = round(ebit / a, 4) if ebit is not None and a else None
        x4 = round(marketCap / tl, 4) if marketCap is not None and tl and tl > 0 else None
        x5 = round(rev / a, 4) if rev is not None and a else None

        # X4(시가총액/부채) 없으면 Altman Z'' (비제조업) 대체
        zScore = None
        zModel = None
        if all(v is not None for v in [x1, x2, x3, x4, x5]):
            zScore = round(1.2 * x1 + 1.4 * x2 + 3.3 * x3 + 0.6 * x4 + 1.0 * x5, 2)
            zModel = "Z-Score"
        elif all(v is not None for v in [x1, x2, x3, x5]):
            # Z'' = 6.56*X1 + 3.26*X2 + 6.72*X3 + 1.05*X5 (book value 기반)
            zScore = round(6.56 * x1 + 3.26 * x2 + 6.72 * x3 + 1.05 * x5, 2)
            zModel = "Z''-Score"

        if zScore is not None:
            safeThreshold = 2.99 if zModel == "Z-Score" else 2.60
            dangerThreshold = 1.81 if zModel == "Z-Score" else 1.10
            if zScore > safeThreshold:
                zone = "안전"
            elif zScore > dangerThreshold:
                zone = "회색"
            else:
                zone = "위험"
        else:
            zone = None

        history.append(
            {
                "period": col,
                "totalAssets": a,
                "workingCapital": wc,
                "retainedEarnings": re,
                "ebit": ebit,
                "revenue": rev,
                "totalDebt": tl,
                "x1_wcTa": x1,
                "x2_reTa": x2,
                "x3_ebitTa": x3,
                "x4_mcapTl": x4,
                "x5_revTa": x5,
                "zScore": zScore,
                "zModel": zModel,
                "zone": zone,
            }
        )

    if not history:
        return None

    latest = history[0]
    zModel = latest.get("zModel", "")
    result: dict = {
        "history": history,
        "latestScore": latest.get("zScore"),
        "zone": latest.get("zone") or "판별 불가",
        "diagnosticMeta": {
            "model": zModel,
            "precision": 0.95 if zModel == "Z-Score" else 0.82,
            "typeIError": 0.06 if zModel == "Z-Score" else 0.15,
            "reference": "Altman(1968)" if zModel == "Z-Score" else "Altman(1995)",
            "marketNote": "한국 시장: Altman et al.(2014) 신흥시장 Z'' 적용",
        },
    }

    # notes enrichment — 충당부채 (위험/회색 구간일 때 의미)
    from dartlab.analysis.financial.companyContext import fetchNotesDetail

    notesDetail = fetchNotesDetail(company, ["provisions"])
    if notesDetail:
        result["notesDetail"] = notesDetail

    return result


# ── 부실 앙상블 (기존 유지 -- getRatios 사용) ──


@memoizedCalc
def calcDistressEnsemble(company, *, basePeriod: str | None = None) -> dict | None:
    """4 개 부실예측 모델 앙상블 — 다수결 투표.

    Capabilities:
        Altman Z (제조) + Altman Z'' (비제조/신흥) + Ohlson O + Springate S +
        Zmijewski X 각 모델 verdict (safe/warning/danger) 집계 → 다수결로
        종합 등급 (안전/주의/위험) + agreement (일치도). 단일 모델 의존
        편향 제거. 신흥시장에선 Altman Z'' 가 신뢰성 높음 (KR/EM 회사).

    Args:
        company: Company 객체.
        basePeriod: 기준 기간. None 시 최신.

    Returns:
        dict | None:
            - ``models`` (list[dict]): 모델별 (model, score, verdict, threshold)
            - ``ensemble`` (str): "안전"|"주의"|"위험"
            - ``agreement`` (float): 다수파 일치도 (%)
            - ``dangerCount``/``safeCount``/``total`` (int): 카운트

    Raises:
        없음.

    Example:
        >>> r = calcDistressEnsemble(Company("005930"))
        >>> r["ensemble"], r["agreement"]
        ('안전', 100.0)  # 5/5 모델 safe

    Guide:
        - agreement < 60% = 모델 간 불일치 → 단일 모델 결과 신뢰 어려움.
        - 다수결 "위험" + agreement > 80% = 강한 부실 신호 (3+ 모델 동의).
        - Ohlson O / Zmijewski X = logit 모델로 확률 (%) 출력, Altman = z-score.

    When:
        부실 위험 다중 모델 교차검증, 단일 모델 편향 제거 시점.

    How:
        getRatios 5 모델 score → 임계 비교 verdict → 다수결 + agreement 계산.

    SeeAlso:
        - ``calcDistressScore``: Altman Z 단독 시계열
        - ``credit.features.chsFeatures``: CHS (Campbell-Hilscher-Szilagyi)
        - ``calcLeverageTrend``: 부실 모델의 입력 (부채/자본/EBIT)

    Requires:
        IS + BS + (시가총액 — Altman Z 의 X4 입력 marketCap).

    AIContext:
        ensemble + agreement + 모델별 verdict 함께 인용. KR 신흥시장 회사는
        Altman Z'' 가중치 더 높게 해석. 한 모델만 "위험" 이고 나머지 safe 면
        해당 모델 한정 신호 (예: Ohlson 은 자본잠식·과거 적자에 민감).

    LLM Specifications:
        AntiPatterns:
            - 모델 1 개 결과 단독 인용 — 앙상블 다수결 인용 (편향 제거).
            - agreement 60% 미만에 강한 단정 — 모델 간 불일치 명시.
        OutputSchema:
            ``{models: list, ensemble: str, agreement: float, dangerCount: int,
              safeCount: int, total: int}``.
        Prerequisites:
            IS + BS + 시가총액 (Altman Z X4).
        Freshness:
            분기 (시가총액 일간 갱신, 회계 분기).
        Dataflow:
            getRatios → 5 모델 score → 각 verdict → 다수결 → ensemble +
            agreement.
        TargetMarkets: KR (Altman Z'' 가중), US (Altman Z 가중).
    """
    ratios = getRatios(company)
    if ratios is None:
        return None

    models = []

    # Altman Z-Score: >2.99 safe, 1.81~2.99 gray, <1.81 danger
    z = ratios.altmanZScore
    if z is not None:
        if z > 2.99:
            verdict = "safe"
        elif z > 1.81:
            verdict = "warning"
        else:
            verdict = "danger"
        models.append(
            {
                "model": "Altman Z-Score",
                "score": z,
                "verdict": verdict,
                "threshold": "안전 >2.99 / 회색 1.81~2.99 / 위험 <1.81",
            }
        )

    # Altman Z'' (비제조/신흥): >2.60 safe, 1.10~2.60 gray, <1.10 danger
    zpp = ratios.altmanZppScore
    if zpp is not None:
        if zpp > 2.60:
            verdict = "safe"
        elif zpp > 1.10:
            verdict = "warning"
        else:
            verdict = "danger"
        models.append(
            {
                "model": "Altman Z''-Score",
                "score": zpp,
                "verdict": verdict,
                "threshold": "안전 >2.60 / 회색 1.10~2.60 / 위험 <1.10",
            }
        )

    # Ohlson O-Score: P(default) < 10% safe, 10~50% warning, >50% danger
    oProb = ratios.ohlsonProbability
    if oProb is not None:
        if oProb < 10:
            verdict = "safe"
        elif oProb < 50:
            verdict = "warning"
        else:
            verdict = "danger"
        models.append(
            {
                "model": "Ohlson O-Score",
                "score": ratios.ohlsonOScore,
                "probability": oProb,
                "verdict": verdict,
                "threshold": "안전 <10% / 경고 10~50% / 위험 >50%",
            }
        )

    # Springate S-Score: >0.862 safe, else danger
    ss = ratios.springateSScore
    if ss is not None:
        verdict = "safe" if ss > 0.862 else "danger"
        models.append(
            {"model": "Springate S-Score", "score": ss, "verdict": verdict, "threshold": "안전 >0.862 / 위험 <0.862"}
        )

    # Zmijewski X-Score: <0 safe, else danger
    xz = ratios.zmijewskiXScore
    if xz is not None:
        verdict = "safe" if xz < 0 else "danger"
        models.append({"model": "Zmijewski X-Score", "score": xz, "verdict": verdict, "threshold": "안전 <0 / 위험 >0"})

    if not models:
        return None

    # 다수결
    dangerCount = sum(1 for m in models if m["verdict"] == "danger")
    safeCount = sum(1 for m in models if m["verdict"] == "safe")
    total = len(models)

    if dangerCount > total / 2:
        ensemble = "위험"
    elif safeCount > total / 2:
        ensemble = "안전"
    else:
        ensemble = "주의"

    agreement = max(dangerCount, safeCount) / total * 100

    return {
        "models": models,
        "ensemble": ensemble,
        "agreement": round(agreement, 1),
        "dangerCount": dangerCount,
        "safeCount": safeCount,
        "total": total,
    }
