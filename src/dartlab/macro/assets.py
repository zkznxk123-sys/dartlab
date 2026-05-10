"""매크로 자산 분석 — 5대 자산 심층 해석."""

from __future__ import annotations

import logging

log = logging.getLogger(__name__)

from dartlab.macro.macroCycle import (
    classifyVixRegime,
    copperGoldRatio,
    interpretAssets,
    interpretFxDrivers,
    interpretGoldDrivers,
    marketLevelValuation,
)


def _fetchAssetData(market: str, asOf: str | None = None) -> dict[str, float | None]:
    """gather에서 5대 자산 지표 수집.

    Parameters
    ----------
    market : str
        ``"US"`` | ``"KR"``.
    as_of : str | None
        기준일. ``None`` 이면 최신.

    Returns
    -------
    dict[str, float]
        None 값은 제거된 채 반환. 가능한 키:

        - short_rate : float — 2년 국채금리 (%)
        - short_rate_change : float — 2년 국채금리 3개월 변화율 (%)
        - long_rate : float — 10년 국채금리 (%)
        - long_rate_change : float — 10년 국채금리 3개월 변화율 (%)
        - vix : float — VIX 지수 (pt)
        - vix_change : float — VIX 3개월 변화율 (%)
        - dfii10 : float — 10년 TIPS 실질금리 (%)
        - dfii10_change : float — 실질금리 3개월 변화율 (%)
        - fx_usdkrw : float — 환율 (원/달러 또는 DXY)
        - fx_change_pct : float — 환율 3개월 변화율 (%)
        - gold : float — 금 가격 (달러/oz)
        - gold_yoy : float — 금 가격 전년비 변화율 (%)
        - dxy_change_pct : float — 달러인덱스 3개월 변화율 (%)
    """
    from dartlab.macro._helpers import fetchChangePct, fetchLatest, fetchYoy, getGather

    g = getGather(asOf)
    data: dict[str, float | None] = {}

    for key, sid in [("short_rate", "DGS2"), ("long_rate", "DGS10"), ("vix", "VIXCLS"), ("dfii10", "DFII10")]:
        data[key] = fetchLatest(g, sid)
        data[f"{key}_change"] = fetchChangePct(g, sid, 63)

    fx_id = "USDKRW" if market.upper() == "KR" else "DTWEXBGS"
    data["fx_usdkrw"] = fetchLatest(g, fx_id)
    data["fx_change_pct"] = fetchChangePct(g, fx_id, 63)

    data["gold"] = fetchLatest(g, "IR14270")
    data["gold_yoy"] = fetchYoy(g, "IR14270")
    data["dxy_change_pct"] = fetchChangePct(g, "DTWEXBGS", 63)

    return {k: v for k, v in data.items() if v is not None}


def analyzeAssets(*, market: str = "US", asOf: str | None = None, overrides: dict | None = None, **kwargs) -> dict:
    """5대 자산 종합 해석 — 주식/채권/원자재/환율/금 + 심층 드라이버.

    Parameters
    ----------
    market : str
        ``"US"`` | ``"KR"``.
    as_of : str | None
        기준일. ``None`` 이면 최신.
    overrides : dict | None
        지표 강제 치환 (예: ``{"vix": 30}``).

    Returns
    -------
    dict
        - market : str — 시장 코드
        - assets : list[dict] — 자산별 해석. 각 원소: asset:str, label:str, level:float, change:float(%), interpretation:str, implication:str
        - goldDrivers : dict | None — 금 3요인 분해 (realRateEffect:str, dollarEffect:str, safeHavenEffect:str, dominant:str)
        - vixRegime : dict | None — VIX 구간 판정 (level:float(pt), zone:str, zoneLabel:str, buySignal:bool)
        - fxDrivers : dict | None — 환율 3요인 분해 (rateDiffEffect:str, tradeEffect:str, riskEffect:str, dominant:str, divergence:bool)
        - copperGold : dict | None — 구리/금 비율 (ratio:float(배), direction:str, directionLabel:str, implication:str, description:str)
        - marketValuation : dict | None — Buffett Indicator (buffettIndicator:float(%), zone:str, zoneLabel:str, description:str). US 전용.
    """
    data = _fetchAssetData(market, asOf=asOf)
    if overrides:
        from dartlab.macro._helpers import applyOverrides

        data = applyOverrides(data, overrides)
    result: dict = {"market": market.upper()}

    # 기본 5대 자산 해석 — DKW 분해 + 금리차 교차 해석 포함
    asset_input: dict[str, float | None] = {}
    for k in (
        "short_rate",
        "short_rate_change",
        "long_rate",
        "long_rate_change",
        "fx_usdkrw",
        "fx_change_pct",
        "gold",
        "gold_yoy",
        "vix",
        "vix_change",
    ):
        if k in data:
            asset_input[k] = data[k]

    # 장기금리 "왜" 해석용: BEI/실질금리 변화
    if "dfii10_change" in data:
        asset_input["real_rate_change"] = data["dfii10_change"]
    # BEI 변화 (T10YIE 3개월 변화)
    try:
        from dartlab.gather import getDefaultGather

        bei_df = getDefaultGather().macro("T10YIE")
        if bei_df is not None and len(bei_df) > 0:
            vals = bei_df.get_column("value").drop_nulls()
            if len(vals) >= 63:
                asset_input["bei_change"] = float(vals[-1]) - float(vals[-63])
    except (KeyError, ValueError, TypeError, AttributeError):
        pass

    # 금리차-환율 교차 해석용: US 2Y - KR 기준금리
    if market.upper() == "KR":
        try:
            from dartlab.gather import getDefaultGather

            g = getDefaultGather()
            us2y = g.macro("DGS2")
            kr_rate = g.macro("기준금리")
            if us2y is not None and kr_rate is not None:
                us_vals = us2y.get_column("value").drop_nulls()
                kr_vals = kr_rate.get_column("value").drop_nulls()
                if len(us_vals) > 0 and len(kr_vals) > 0:
                    diff_now = float(us_vals[-1]) - float(kr_vals[-1])
                    asset_input["rate_diff"] = diff_now
                    if len(us_vals) >= 63 and len(kr_vals) >= 2:
                        diff_old = float(us_vals[-63]) - float(kr_vals[-2])
                        asset_input["rate_diff_change"] = diff_now - diff_old
        except (KeyError, ValueError, TypeError, AttributeError):
            pass

    signals = interpretAssets(asset_input)
    result["assets"] = [
        {
            "asset": s.asset,
            "label": s.label,
            "level": s.level,
            "change": s.change,
            "interpretation": s.interpretation,
            "implication": s.implication,
        }
        for s in signals
    ]

    # 금 3요인 심층 해석
    goldYoy = data.get("gold_yoy")
    real_rate_chg = data.get("dfii10_change")
    dxy_chg = data.get("dxy_change_pct")
    vix = data.get("vix")
    if goldYoy is not None and real_rate_chg is not None and dxy_chg is not None and vix is not None:
        gd = interpretGoldDrivers(goldYoy, real_rate_chg, dxy_chg, vix)
        result["goldDrivers"] = {
            "realRateEffect": gd.realRateEffect,
            "dollarEffect": gd.dollarEffect,
            "safeHavenEffect": gd.safeHavenEffect,
            "dominant": gd.dominant,
        }
    else:
        result["goldDrivers"] = None

    # VIX 구간 판정
    if vix is not None:
        vr = classifyVixRegime(vix)
        result["vixRegime"] = {
            "level": vr.level,
            "zone": vr.zone,
            "zoneLabel": vr.zoneLabel,
            "buySignal": vr.buySignal,
        }
    else:
        result["vixRegime"] = None

    # 환율 3요인 분해 — 금리차 + 무역수지 + 위험선호도
    result["fxDrivers"] = None
    fx_chg = data.get("fx_change_pct")
    if fx_chg is not None:
        trade_yoy = None
        try:
            from dartlab.macro._helpers import fetchYoy as _fy
            from dartlab.macro._helpers import getGather as _gg

            _g = _gg(asOf)
            trade_yoy = _fy(_g, "EXPORT") if market.upper() == "KR" else _fy(_g, "BOPGSTB")
        except (KeyError, ValueError, TypeError, AttributeError, ImportError):
            pass

        fd = interpretFxDrivers(
            fxChangePct=fx_chg,
            rateDiffChange=asset_input.get("rate_diff_change"),
            tradeBalanceYoy=trade_yoy,
            vix=data.get("vix"),
        )
        result["fxDrivers"] = {
            "rateDiffEffect": fd.rateDiffEffect,
            "tradeEffect": fd.tradeEffect,
            "riskEffect": fd.riskEffect,
            "dominant": fd.dominant,
            "divergence": fd.divergence,
        }

    # Copper/Gold Ratio
    result["copperGold"] = None
    try:
        from dartlab.gather import getDefaultGather

        g = getDefaultGather()
        cu_df = g.macro("PCOPPUSDM")
        gold_df = g.macro("IR14270")
        if cu_df is not None and gold_df is not None:
            cu_vals = cu_df.get_column("value").drop_nulls()
            au_vals = gold_df.get_column("value").drop_nulls()
            if len(cu_vals) > 1 and len(au_vals) > 1:
                cg = copperGoldRatio(
                    float(cu_vals[-1]),
                    float(au_vals[-1]),
                    float(cu_vals[-2]) if len(cu_vals) > 1 else None,
                    float(au_vals[-2]) if len(au_vals) > 1 else None,
                )
                result["copperGold"] = {
                    "ratio": cg.ratio,
                    "direction": cg.direction,
                    "directionLabel": cg.directionLabel,
                    "implication": cg.implication,
                    "description": cg.description,
                }
    except (KeyError, ValueError, TypeError, AttributeError):
        pass

    # Buffett Indicator (US만) — 시장 레벨 밸류에이션
    result["marketValuation"] = None
    if market.upper() == "US":
        try:
            from dartlab.macro._helpers import fetchLatest as _fl
            from dartlab.macro._helpers import getGather as _gg

            _g = _gg(asOf)
            mcap = _fl(_g, "WILL5000PRFC")
            gdp = _fl(_g, "GDP")
            if mcap is not None and gdp is not None:
                mv = marketLevelValuation(mcap, gdp)
                result["marketValuation"] = {
                    "buffettIndicator": mv.buffettIndicator,
                    "zone": mv.zone,
                    "zoneLabel": mv.zoneLabel,
                    "description": mv.description,
                }
        except (KeyError, ValueError, TypeError, AttributeError, ImportError):
            pass

    return result
