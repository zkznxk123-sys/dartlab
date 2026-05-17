"""매크로 자산 분석 — 5대 자산 심층 해석."""

from __future__ import annotations

import logging

log = logging.getLogger(__name__)

from dartlab.macro.cycles.macroCycle import (
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
    from dartlab.macro.seriesFetch import fetchChangePct, fetchLatest, fetchYoy, getGather

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

    Capabilities:
        주식/채권/원자재/환율/금 5 자산 해석 + 금 3 요인 (실질금리·달러·안전자산)
        + VIX regime + 환율 3 요인 (금리차·교역·리스크) + 구리/금 비율 + Buffett
        Indicator (US) 를 단일 dict 로 합성. macro/summary 의 assets 축이 직접
        호출.

    Args:
        market: ``"US"`` | ``"KR"``.
        asOf: 기준일 ``YYYY-MM-DD``. ``None`` 이면 최신.
        overrides: 지표 강제 치환 (예: ``{"vix": 30}``).

    Returns:
        dict — market/assets(5 자산 list)/goldDrivers/vixRegime/fxDrivers/
        copperGold/marketValuation(US 전용) 키.

    Example:
        >>> r = analyzeAssets(market="US")
        >>> r["vixRegime"]["zone"], r["assets"][0]["asset"]
        ('normal', 'short_rate')

    Guide:
        VIX regime "panic" + goldDrivers.dominant "safe_haven" 동시 = 위험회피
        강화. fxDrivers.divergence=True 면 환율 요인 충돌 — 단기 해석 보류.

    When:
        ``analyzeSummary`` assets 축 + AI 자산 답변 진입점.

    How:
        _fetchAssetData → overrides → interpretAssets + interpretGoldDrivers +
        classifyVixRegime + interpretFxDrivers + copperGoldRatio +
        marketLevelValuation (US) → dict 합성.

    Requires:
        FRED (DGS2/DGS10/T10YIE/DFII10/VIXCLS/DTWEXBGS/IR14270) + KOSIS (KR
        USDKRW/기준금리).

    Raises:
        없음 — 개별 드라이버 실패는 None 으로 흡수.

    See Also:
        - analyzeCycle : 사이클 4 국면 (assets 와 합성)
        - dartlab.synth.quadrant.classifyQuadrant : 성장 × 인플레

    AIContext:
        assets 5 종 중 1~2 자산 해설 + vixRegime/goldDrivers.dominant 두 필드 +
        marketValuation.zone (US) 가 한 단락 답변 완성.

    LLM Specifications:
        AntiPatterns:
            - assets list 만 인용 + goldDrivers/fxDrivers 무시
            - KR 시장에 marketValuation 기대 (US 전용)
            - VIX 수준만 인용 + zone 라벨 미사용
        OutputSchema:
            ``{market, assets, goldDrivers, vixRegime, fxDrivers, copperGold,
            marketValuation}``.
        Prerequisites: FRED + KOSIS 활성.
        Freshness: FRED 일간 + KOSIS 분기.
        Dataflow: _fetchAssetData → 5 드라이버 함수 → dict 합성.
        TargetMarkets: US (풀세트), KR (assets 5 종 + fxDrivers).
    """
    data = _fetchAssetData(market, asOf=asOf)
    if overrides:
        from dartlab.macro.seriesFetch import applyOverrides

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
        from dartlab.core.di import getMacroProvider

        bei_df = getMacroProvider().getDefaultGather().macro("T10YIE")
        if bei_df is not None and len(bei_df) > 0:
            vals = bei_df.get_column("value").drop_nulls()
            if len(vals) >= 63:
                asset_input["bei_change"] = float(vals[-1]) - float(vals[-63])
    except (KeyError, ValueError, TypeError, AttributeError):
        pass

    # 금리차-환율 교차 해석용: US 2Y - KR 기준금리
    if market.upper() == "KR":
        try:
            from dartlab.core.di import getMacroProvider

            g = getMacroProvider().getDefaultGather()
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
            from dartlab.macro.seriesFetch import fetchYoy as _fy
            from dartlab.macro.seriesFetch import getGather as _gg

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
        from dartlab.core.di import getMacroProvider

        g = getMacroProvider().getDefaultGather()
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
            from dartlab.macro.seriesFetch import fetchLatest as _fl
            from dartlab.macro.seriesFetch import getGather as _gg

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
