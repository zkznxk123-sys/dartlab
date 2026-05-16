"""Company → CHS feature 추출 SSOT.

L1.5 synth/distress 본체. credit engine 과 valuation survival 이 동일 경로로
CHS 부도확률을 계산할 수 있도록 feature 추출 로직을 한 곳에 보관.

credit/engine.py::_calcCHSAdjustment 에서 분리 — 순환 의존 방지.
"""

from __future__ import annotations

from typing import Any

from dartlab.synth.distress.chsModel import CHSResult, calcCHS


def extractChsFeatures(company: Any) -> dict | None:
    """Company → Campbell-Hilscher-Szilagyi (CHS) feature dict 추출.

    Capabilities:
        company 의 BS/IS + 주가 시계열에서 CHS 부도예측 모델 8 변수를 한 번에
        뽑아 dict 로 반환. credit engine 과 valuation survival 양쪽이
        동일 경로로 CHS 부도확률을 계산하도록 하는 L1.5 SSOT.

    Args:
        company: Company 객체. ``select("BS"|"IS", [...])``, ``stockCode``
            속성 필요.

    Returns:
        dict | None: 다음 8 키. 입력 부족 또는 주가 미수집 시 ``None``.
            - ``netIncome`` (float): 당기순이익 (원)
            - ``totalLiabilities`` (float): 부채총계 (원)
            - ``cash`` (float): 현금및현금성자산 (원)
            - ``totalAssets`` (float): 자산총계 (원)
            - ``marketCap`` (float): 시가총액 (원)
            - ``equityVolatility`` (float): 일별 수익률 연환산 표준편차
            - ``excessReturn`` (float): 전체 기간 누적 수익률
            - ``stockPrice`` (float): 최신 종가 (원)

    Raises:
        없음 — 모든 예외 (AttributeError, KeyError, ValueError, TypeError,
        ImportError, IndexError) 는 내부에서 catch → ``None`` 반환.

    Example:
        >>> from dartlab import Company
        >>> features = extractChsFeatures(Company("005930"))
        >>> if features:
        ...     print(features["totalAssets"], features["marketCap"])

    Guide:
        BS 에서 자산총계 · 부채총계 · 현금, IS 에서 당기순이익을 가져온다.
        주가/시가총액/변동성/excessReturn 은 ``_gatherMarketData`` 가 macro
        provider 의 gather("price") 로 30 영업일 이상 시계열을 받아 산출.
        주식수는 ``analysis.calcDcf`` 의 equityValue/perShareValue 역산을
        시도 (importlib 동적 호출 — credit ↔ analysis 순환 회피).

    SeeAlso:
        - ``computeChsProbability`` — 본 feature 를 ``calcCHS`` 에 넣어 PD 출력
        - ``dartlab.synth.distress.chsModel.calcCHS`` — CHS logit 모델 본체

    Requires:
        company.select("BS", ...), company.select("IS", ...),
        company.stockCode, macro provider gather("price").

    AIContext:
        CHS 입력 부족 (재무 dict 비거나 주가 30 봉 미만) 시 None 이라
        호출자 (credit engine, valuation survival) 는 이를 "CHS 적용 불가"
        시그널로 받아 다른 신용판단 경로로 폴백한다.

    LLM Specifications:
        AntiPatterns:
            - 결과 dict 의 ``stockPrice`` 만 보고 시총·변동성 추정 금지. 일부
              필드가 None 일 수 있는 build path (computeChsProbability) 와
              혼동 가능.
            - 주식수 역산 (calcDcf) 실패 시 marketCap=None → 함수 전체 None.
              부분 결과를 노출하지 않으므로 호출자 분기 단순화.
        OutputSchema:
            ``{netIncome, totalLiabilities, cash, totalAssets, marketCap,
            equityVolatility, excessReturn, stockPrice}`` 8 키, 모두 float.
        Prerequisites:
            BS/IS 최신 분기 데이터 + 종가 시계열 30 봉 이상 + analysis.calcDcf
            가 equityValue & perShareValue 둘 다 반환.
        Freshness:
            BS/IS = 최신 보고기간 (분기). 주가 = gather("price") 의 cache.
        Dataflow:
            company.select → toDictBySnakeId → latest period dict
            → _gatherMarketData (price → variance · cumulative return)
            → _estimateShares (calcDcf 역산) → marketCap.
        TargetMarkets: KR (DART), US (EDGAR). 통화 단위는 company.currency.
    """
    try:
        from dartlab.core.utils.helpers import toDictBySnakeId
    except ImportError:
        return None

    # 재무 추출
    try:
        bs = company.select("BS", ["자산총계", "부채총계", "현금및현금성자산"])
        income = company.select("IS", ["당기순이익"])
        bs_parsed = toDictBySnakeId(bs)
        is_parsed = toDictBySnakeId(income)
        if not bs_parsed or not is_parsed:
            return None
        bs_data, bs_periods = bs_parsed
        is_data, _ = is_parsed
        if not bs_periods:
            return None
        latest = bs_periods[0]

        def _bs(*keys: str) -> float | None:
            for k in keys:
                v = (bs_data.get(k) or {}).get(latest)
                if v:
                    return float(v)
            return None

        def _is(*keys: str) -> float | None:
            for k in keys:
                v = (is_data.get(k) or {}).get(latest)
                if v:
                    return float(v)
            return None

        ta = _bs("total_assets", "자산총계")
        tl = _bs("total_liabilities", "부채총계")
        cash = _bs("cash_and_cash_equivalents", "cash_and_equivalents")
        ni = _is("net_profit", "net_income", "당기순이익")
    except (AttributeError, KeyError, TypeError, ValueError):
        return None

    if any(v is None for v in (ta, tl, cash, ni)):
        return None

    # 주가 수집 (시가총액, 변동성, excessReturn)
    marketCap, sigma, exret, stock_price = _gatherMarketData(company)
    if marketCap is None:
        return None

    return {
        "netIncome": ni,
        "totalLiabilities": tl,
        "cash": cash,
        "totalAssets": ta,
        "marketCap": marketCap,
        "equityVolatility": sigma,
        "excessReturn": exret,
        "stockPrice": stock_price,
    }


def computeChsProbability(company: Any) -> dict | None:
    """Company → CHS 12 개월 부도확률 + zone + feature 추적.

    Capabilities:
        ``extractChsFeatures`` 로 8 변수 dict 를 뽑은 뒤 ``calcCHS`` 의 logit
        모델을 통과시켜 12M PD 와 zone 분류 (safe/watch/distress) 를 산출.
        credit engine 의 chsAdjustment 와 valuation 의 survivalWeight 가
        공유하는 단일 entry point.

    Args:
        company: Company 객체.

    Returns:
        dict | None: 다음 4 키, 또는 입력 부족 시 ``None``.
            - ``probability`` (float): 12 개월 부도확률 (0~1)
            - ``zone`` (str): ``"safe"``/``"watch"``/``"distress"``
            - ``logitScore`` (float): CHS logit raw score (해석용)
            - ``features`` (dict): ``extractChsFeatures`` 결과 (디버깅용)

    Raises:
        없음 — 내부 모든 예외 catch → ``None``.

    Example:
        >>> from dartlab import Company
        >>> r = computeChsProbability(Company("005930"))
        >>> if r:
        ...     print(r["zone"], r["probability"])

    Guide:
        CHS (Campbell, Hilscher, Szilagyi 2008, JF) 의 8 변수 logit 모델로
        12 개월 부도확률을 추정한다. zone 은 probability 분위로 cut.
        valuation 측은 ``applySurvivalWeight`` 로 PD 를 fair value 에 반영.

    SeeAlso:
        - ``extractChsFeatures`` — 8 변수 추출 (단독 호출 가능)
        - ``dartlab.synth.distress.survival.applySurvivalWeight``
        - ``dartlab.synth.distress.chsModel.calcCHS``

    Requires:
        Company 객체 + analysis.calcDcf + macro provider gather("price").

    AIContext:
        ``zone == "distress"`` 종목은 valuation 가중을 낮추거나 credit notch
        다운을 트리거. probability 만 단독으로 인용하지 말고 zone 과 함께
        제시 (분위 컷이 시장환경별로 조정될 수 있음을 명시).

    LLM Specifications:
        AntiPatterns:
            - probability 가 정확한 1 년 부도율이라고 단정 금지. 모델은
              미국 표본 (1981~2003) 기반 calibration. KR 적용 시 zone 만
              상대 신호로 사용 권장.
            - features dict 의 marketCap 이 BS 의 자기자본과 다를 수 있음
              (시장 평가 vs 장부). DCF 역산 결과라 정밀도 한정.
        OutputSchema:
            ``{probability: float, zone: str, logitScore: float, features: dict}``.
        Prerequisites:
            ``extractChsFeatures`` 가 정상 dict 반환 + ``calcCHS`` 가
            ``CHSResult`` 인스턴스 반환.
        Freshness:
            features 의 freshness 와 동일 (BS/IS 최신 분기 + 주가 cache).
        Dataflow:
            extractChsFeatures → calcCHS(**features) → CHSResult
            → {probability, zone, logitScore, features}.
        TargetMarkets: KR, US.
    """
    features = extractChsFeatures(company)
    if not features:
        return None

    result: CHSResult | None = calcCHS(**features)
    if not isinstance(result, CHSResult):
        return None

    return {
        "probability": result.probability,
        "zone": result.zone,
        "logitScore": result.logitScore,
        "features": features,
    }


def _gatherMarketData(company: Any) -> tuple[float | None, float | None, float | None, float | None]:
    """주가 시계열에서 시가총액 / 변동성 / excessReturn / 주가 추출."""
    try:
        from dartlab.core.di import getMacroProvider

        code = getattr(company, "stockCode", None)
        if not code:
            return None, None, None, None
        g = getMacroProvider().getDefaultGather()
        price_df = g("price", code)
        if price_df is None or not hasattr(price_df, "height") or price_df.height < 30:
            return None, None, None, None
        closes = [float(c) for c in price_df["close"].to_list() if c is not None]
        if len(closes) < 30:
            return None, None, None, None
        latest_price = closes[-1]
        # 변동성 — 연환산 일별 수익률 표준편차
        returns = [(closes[i] - closes[i - 1]) / closes[i - 1] for i in range(1, len(closes)) if closes[i - 1]]
        if len(returns) < 10:
            return None, None, None, latest_price
        mean_r = sum(returns) / len(returns)
        var_r = sum((r - mean_r) ** 2 for r in returns) / len(returns)
        sigma = (var_r**0.5) * (252**0.5)
        exret = (closes[-1] / closes[0] - 1) if closes[0] else 0.0

        # 주식수는 calcDcf 역산 또는 BS 시도 — 여기서는 proxy
        shares = _estimateShares(company, latest_price)
        marketCap = shares * latest_price if shares else None
        return marketCap, sigma, exret, latest_price
    except (ImportError, AttributeError, KeyError, TypeError, ValueError, IndexError):
        return None, None, None, None


def _estimateShares(company: Any, price: float) -> int | None:
    """주식수 역산 — calcDcf 결과의 equityValue / perShareValue.

    analysis.calcDcf 는 importlib 동적 호출 — credit ↔ analysis cycle 회피.
    """
    try:
        import importlib

        calcDcf = getattr(importlib.import_module("dartlab.analysis.financial.valuation"), "calcDcf")

        r = calcDcf(company)
        if isinstance(r, dict):
            eq = r.get("equityValue")
            ps = r.get("perShareValue")
            if eq and ps and ps > 0:
                return int(eq / ps)
    except (ImportError, AttributeError, ValueError, TypeError):
        pass
    return None
