"""매크로 심리 분석 — 공포탐욕 근사 + VIX 구간."""

from __future__ import annotations

from dartlab.core.finance.macroCycle import classifyVixRegime
from dartlab.core.finance.sentiment import calcFearGreedProxy
from dartlab.macro._helpers import (
    apply_overrides,
    collect_timeseries,
    fetch_change_pct,
    fetch_latest,
    fetch_series_list,
    get_gather,
)


def _fetch_sentiment_data(market: str, as_of: str | None = None) -> dict[str, float | None]:
    """gather에서 심리 지표 수집.

    Parameters
    ----------
    market : str
        ``"US"`` | ``"KR"``.
    as_of : str | None
        기준일. ``None`` 이면 최신.

    Returns
    -------
    dict[str, float | None]
        가능한 키:

        - vix : float — VIX 지수 (pt)
        - sp500_vs_ma125 : float — S&P 500 / 125일 이평 비율 (배)
        - hy_spread : float — HY 스프레드 (bp)
        - gold_equity_ratio : float — 금/S&P 500 비율 (배)
        - crypto_momentum : float — BTC 90일 변화율 (%)
    """
    g = get_gather(as_of)
    data: dict[str, float | None] = {}

    data["vix"] = fetch_latest(g, "VIXCLS")

    sp_list = fetch_series_list(g, "SP500")
    if sp_list and len(sp_list) >= 125:
        current = sp_list[-1]
        ma125 = sum(sp_list[-125:]) / 125
        if ma125 > 0:
            data["sp500_vs_ma125"] = current / ma125

    hy = fetch_latest(g, "BAMLH0A0HYM2")
    if hy is not None:
        data["hy_spread"] = hy * 100

    gold = fetch_latest(g, "IR14270")
    sp = fetch_latest(g, "SP500")
    if gold is not None and sp is not None and sp > 0:
        data["gold_equity_ratio"] = gold / sp

    # BTC 90일 모멘텀 — 위험자산 선호도의 극단 지표
    btc_chg = fetch_change_pct(g, "CBBTCUSD", 90)
    if btc_chg is not None:
        data["crypto_momentum"] = btc_chg

    return data


def calcSentiment(*, market: str = "US", as_of: str | None = None, overrides: dict | None = None, **kwargs) -> dict:
    """시장 심리 종합 분석 — 공포탐욕 근사 + VIX 구간 + JLN 불확실성.

    Parameters
    ----------
    market : str
        ``"US"`` | ``"KR"``.
    as_of : str | None
        기준일. ``None`` 이면 최신.
    overrides : dict | None
        지표 강제 치환 (예: ``{"vix": 35}``).

    Returns
    -------
    dict
        - market : str — 시장 코드
        - fearGreed : dict | None — 공포탐욕 근사 (score:float(점, 0-100), zone:str, zoneLabel:str, components:dict)
        - vixRegime : dict | None — VIX 구간 판정 (level:float(pt), zone:str, zoneLabel:str, buySignal:bool)
        - timeseries : dict — vix / sp500 / hy_spread 시계열
        - macroUncertainty : dict | None — JLN 실물 불확실성 (value:float, zone:str, zoneLabel:str, vsVix:str, description:str)
    """
    data = _fetch_sentiment_data(market, as_of=as_of)
    if overrides:
        data = apply_overrides(data, overrides)
    result: dict = {"market": market.upper()}

    vix = data.get("vix")
    sp_ratio = data.get("sp500_vs_ma125")
    hy = data.get("hy_spread")
    if vix is not None and sp_ratio is not None and hy is not None:
        fg = calcFearGreedProxy(
            vix,
            sp_ratio,
            hy,
            gold_equity_ratio=data.get("gold_equity_ratio"),
            crypto_momentum=data.get("crypto_momentum"),
        )
        result["fearGreed"] = {
            "score": fg.score,
            "zone": fg.zone,
            "zoneLabel": fg.zoneLabel,
            "components": fg.components,
        }
    else:
        result["fearGreed"] = None

    if vix is not None:
        vr = classifyVixRegime(vix)
        result["vixRegime"] = {"level": vr.level, "zone": vr.zone, "zoneLabel": vr.zoneLabel, "buySignal": vr.buySignal}
    else:
        result["vixRegime"] = None

    g = get_gather(as_of)
    result["timeseries"] = collect_timeseries(g, {"vix": "VIXCLS", "sp500": "SP500", "hy_spread": "BAMLH0A0HYM2"})

    # ── JLN Macro Uncertainty Index — Jurado, Ludvigson, Ng (2015) AER ──
    # VIX = 금융 불확실성 (옵션 내재), JLN = 실물 불확실성 (132개 시계열 예측오차)
    try:
        jln = fetch_latest(g, "WLEMUINDXD")
        if jln is not None:
            if jln < 0.8:
                zone, zone_label = "low", "낮음"
            elif jln < 1.0:
                zone, zone_label = "moderate", "보통"
            elif jln < 1.2:
                zone, zone_label = "high", "높음"
            else:
                zone, zone_label = "extreme", "극단"

            # VIX-JLN 괴리 감지
            vix_high = vix is not None and vix > 25
            vix_low = vix is not None and vix < 15
            jln_high = jln > 1.0
            jln_low = jln < 0.8
            if (vix_high and jln_low) or (vix_low and jln_high):
                vs_vix = "divergent"
                vs_desc = "금융(VIX)과 실물(JLN) 불확실성이 괴리"
            else:
                vs_vix = "aligned"
                vs_desc = "금융과 실물 불확실성 방향 일치"

            result["macroUncertainty"] = {
                "value": round(jln, 3),
                "zone": zone,
                "zoneLabel": zone_label,
                "vsVix": vs_vix,
                "description": f"실물 불확실성 {jln:.3f} ({zone_label}). {vs_desc}.",
            }
    except (KeyError, ValueError, TypeError, AttributeError):
        pass

    return result
