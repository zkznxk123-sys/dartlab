"""매크로 교역 분석 — 교역조건 + 대용치 + 수출이익 선행.

투자전략 5: 우리나라 종합주가는 미국의 소비와 유사한 흐름을 보인다
투자전략 10: 우리나라 주가 흐름은 수출기업이 좌우한다
투자전략 11: 선행지수 중에 가장 앞선 모습을 보이는 것은 교역조건이다
투자전략 12: 교역조건대용치는 환율상승률과 유가상승률의 차다
투자전략 14: 환율의 방향성은 양국 선행지수의 상대강도에 의해 결정된다
투자전략 31: 교역조건대용치는 수출기업의 이익에 선행한다
"""

from __future__ import annotations

from dartlab.macro.trade.termsOfTrade import (
    calcToT,
    exportProfitLeading,
    leadingIndexRelativeStrength,
    totProxy,
)


def _yoy(series: list[float], idx: int = -1) -> float | None:
    """시계열에서 12개월 전 대비 YoY% 계산 (월간 데이터 가정).

    Parameters
    ----------
    series : list[float]
        월간 시계열 데이터. 최소 13개 이상 필요.
    idx : int
        기준 시점 인덱스. 기본 -1 (최신).

    Returns
    -------
    float | None
        전년동기 대비 변화율 (%). 데이터 부족 또는 전기값 0이면 None.
    """
    if len(series) < 13:
        return None
    current = series[idx]
    prev = series[idx - 12]
    if prev == 0:
        return None
    return ((current - prev) / abs(prev)) * 100


def _mom(series: list[float]) -> float | None:
    """최근 2개 값의 MoM 차이.

    Parameters
    ----------
    series : list[float]
        시계열 데이터. 최소 2개 이상 필요.

    Returns
    -------
    float | None
        전월 대비 차이 (원 단위 그대로). 데이터 부족이면 None.
    """
    if len(series) < 2:
        return None
    return series[-1] - series[-2]


def _momPct(series: list[float]) -> float | None:
    """최근 2개 값의 MoM 변화율 (%). 절대값 차이가 아닌 % 단위가 필요한 비교용."""
    if len(series) < 2:
        return None
    prev = series[-2]
    if prev == 0:
        return None
    return ((series[-1] - prev) / abs(prev)) * 100


def _fetchTradeData(market: str, asOf: str | None = None) -> dict[str, float | list | None]:
    """gather에서 교역/환율/유가 지표 수집.

    Parameters
    ----------
    market : str
        시장 코드 ("US" | "KR").
    as_of : str | None
        기준일 (YYYY-MM-DD). None이면 최신.

    Returns
    -------
    dict[str, float | list | None]
        KR 시장:
            export_price : float — 수출물가지수 (pt)
            export_price_series : list[float] — 수출물가 시계열
            export_price_prev : float — 전기 수출물가
            import_price : float — 수입물가지수 (pt)
            import_price_series : list[float] — 수입물가 시계열
            export_vol : float — 수출액 (백만달러)
            export_vol_series : list[float] — 수출액 시계열
            usdkrw : float — 원/달러 환율 (원)
            usdkrw_series : list[float] — 환율 시계열
            cli : float — 경기선행지수 (pt)
            cli_series : list[float] — 선행지수 시계열
        공통:
            oil : float — WTI 유가 (달러/배럴)
            oil_series : list[float] — 유가 시계열
            us_retail_series : list[float] — 미국 소매판매 시계열 (백만달러)
    """
    from dartlab.macro.seriesFetch import fetchSeriesList, getGather

    g = getGather(asOf)
    data: dict[str, float | list | None] = {}

    if market.upper() == "KR":
        for label, sid in [
            ("export_price", "EXPORT_PRICE"),
            ("import_price", "IMPORT_PRICE"),
            ("export_vol", "EXPORT"),
            ("usdkrw", "USDKRW"),
            ("cli", "CLI"),
        ]:
            series = fetchSeriesList(g, sid)
            if series:
                data[f"{label}_series"] = series
                data[label] = series[-1]
                if len(series) > 1:
                    data[f"{label}_prev"] = series[-2]

    data["oil_series"] = fetchSeriesList(g, "DCOILWTICO")
    oil_list = data.get("oil_series")
    if oil_list:
        data["oil"] = oil_list[-1]

    data["us_retail_series"] = fetchSeriesList(g, "RSAFS")

    return data


def analyzeTrade(*, market: str = "US", asOf: str | None = None, overrides: dict | None = None, **kwargs) -> dict:
    """교역 종합 분석.

    교역조건, 교역조건 대용치(환율-유가), 수출이익 선행,
    양국 선행지수 상대강도, 미국 소비 연계를 종합한다.

    Parameters
    ----------
    market : str
        시장 코드 ("US" | "KR"). 기본 "US".
    as_of : str | None
        기준일 (YYYY-MM-DD). None이면 최신.
    overrides : dict | None
        AI 가정 교체 (예: ``{"usdkrw": 1350}``).

    Returns
    -------
    dict
        market : str — 시장 코드
        termsOfTrade : dict | None — 교역조건 (KR 전용)
            level : float — 교역조건 수준 (수출물가/수입물가, 배)
            momentum : float — 전기비 변화
            direction : str — 방향 ("improving" | "deteriorating" | "stable")
            directionLabel : str — 한글 레이블
            earningsImplication : str — 수출이익 시사
            earningsLabel : str — 한글 레이블
            description : str — 해설
        totProxy : dict | None — 교역조건 대용치 (KR 전용)
            value : float — 환율 YoY - 유가 YoY (%p)
            direction : str — 방향
            directionLabel : str — 한글 레이블
            components : dict — 구성요소 (fxYoy, oilYoy)
            description : str — 해설
        exportProfit : dict | None — 수출이익 선행 신호 (KR 전용)
            signal : str — 시그널 코드
            signalLabel : str — 한글 레이블
            confidence : float — 신뢰도 (0~1)
            components : dict — 구성요소
            description : str — 해설
        leadingRelativeStrength : dict | None — 양국 선행지수 상대강도 (KR 전용)
            relativeStrength : float — 상대강도 값
            fxDirection : str — 환율 방향 시사
            fxLabel : str — 한글 레이블
            description : str — 해설
        usConsumptionLink : dict | None — 미국 소비 ↔ 한국 주가 연계 (KR 전용)
            usRetailYoy : float — 미국 소매판매 YoY (%)
            implication : str — 시사 해설
        timeseries : dict — 주요 시계열 (oil, export_price, usdkrw 등)
    """
    data = _fetchTradeData(market, asOf=asOf)
    if overrides:
        from dartlab.macro.seriesFetch import applyOverrides

        data = applyOverrides(data, overrides)
    result: dict = {"market": market.upper()}

    if market.upper() == "KR":
        # 교역조건 직접 계산
        exp_price = data.get("export_price")
        imp_price = data.get("import_price")
        if exp_price is not None and imp_price is not None:
            exp_prev = data.get("export_price_prev")
            imp_prev = data.get("import_price_prev")
            tot = calcToT(exp_price, imp_price, exp_prev, imp_prev)
            result["termsOfTrade"] = {
                "level": tot.level,
                "momentum": tot.momentum,
                "direction": tot.direction,
                "directionLabel": tot.directionLabel,
                "earningsImplication": tot.earningsImplication,
                "earningsLabel": tot.earningsLabel,
                "description": tot.description,
            }
        else:
            result["termsOfTrade"] = None

        # 교역조건 대용치 (환율 - 유가)
        usdkrw_series = data.get("usdkrw_series")
        oil_series = data.get("oil_series")
        if usdkrw_series and oil_series:
            fx_yoy = _yoy(usdkrw_series)
            oil_yoy = _yoy(oil_series)
            if fx_yoy is not None and oil_yoy is not None:
                proxy = totProxy(fx_yoy, oil_yoy)
                result["totProxy"] = {
                    "value": proxy.value,
                    "direction": proxy.direction,
                    "directionLabel": proxy.directionLabel,
                    "components": proxy.components,
                    "description": proxy.description,
                }
            else:
                result["totProxy"] = None
        else:
            result["totProxy"] = None

        # 수출이익 선행 신호
        tot_data = result.get("termsOfTrade")
        export_series = data.get("export_vol_series")
        if tot_data and export_series:
            tot_mom = tot_data["momentum"]
            export_yoy = _yoy(export_series)
            if export_yoy is not None:
                profit = exportProfitLeading(tot_mom, export_yoy)
                result["exportProfit"] = {
                    "signal": profit.signal,
                    "signalLabel": profit.signalLabel,
                    "confidence": profit.confidence,
                    "components": profit.components,
                    "description": profit.description,
                }
            else:
                result["exportProfit"] = None
        else:
            result["exportProfit"] = None

        # 양국 선행지수 상대강도 (전략 14)
        cli_series = data.get("cli_series")
        us_retail = data.get("us_retail_series")
        if cli_series:
            # leadingIndexRelativeStrength 가 기대하는 단위는 % (전월대비). _mom 은 단순 차이값이라 단위 불일치 — _momPct 사용.
            kr_cli_mom = _momPct(cli_series)
            # US LEI는 아직 구현 전이므로 US 소매판매 모멘텀으로 근사
            us_mom = _momPct(us_retail) if us_retail else None
            if kr_cli_mom is not None and us_mom is not None:
                leading = leadingIndexRelativeStrength(us_mom, kr_cli_mom)
                result["leadingRelativeStrength"] = {
                    "relativeStrength": leading.relativeStrength,
                    "fxDirection": leading.fxDirection,
                    "fxLabel": leading.fxLabel,
                    "description": leading.description,
                }
            else:
                result["leadingRelativeStrength"] = None
        else:
            result["leadingRelativeStrength"] = None

        # 한국 주가 ≈ 미국 소비 (전략 5)
        if us_retail:
            us_retail_yoy = _yoy(us_retail)
            if us_retail_yoy is not None:
                if us_retail_yoy > 5:
                    link = "미국 소비 강세 → 한국 수출 호조 → KOSPI 긍정"
                elif us_retail_yoy < -2:
                    link = "미국 소비 약세 → 한국 수출 부진 → KOSPI 부정"
                else:
                    link = "미국 소비 보합 → 한국 주가 중립"
                result["usConsumptionLink"] = {
                    "usRetailYoy": round(us_retail_yoy, 1),
                    "implication": link,
                }
            else:
                result["usConsumptionLink"] = None
        else:
            result["usConsumptionLink"] = None

    else:
        # US market: 교역조건은 KR 위주이므로 제한적
        result["termsOfTrade"] = None
        result["totProxy"] = None
        result["exportProfit"] = None
        result["leadingRelativeStrength"] = None
        result["usConsumptionLink"] = None

    from dartlab.macro.seriesFetch import collectTimeseries, getGather

    g_ts = getGather(asOf)
    ts_map = {"oil": "DCOILWTICO"}
    if market.upper() == "KR":
        ts_map.update(
            {"export_price": "EXPORT_PRICE", "import_price": "IMPORT_PRICE", "usdkrw": "USDKRW", "export": "EXPORT"}
        )
    result["timeseries"] = collectTimeseries(g_ts, ts_map)

    return result
