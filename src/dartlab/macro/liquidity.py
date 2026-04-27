"""매크로 유동성 분석 — M2 + 연준 B/S + 신용스프레드 + FCI."""

from __future__ import annotations

from dartlab.core.finance.liquidity import classifyLiquidityRegime
from dartlab.macro._helpers import (
    apply_overrides,
    collect_timeseries,
    fetch_change_pct,
    fetch_latest,
    fetch_series_list,
    fetch_yoy,
    get_gather,
)


def _fetch_liquidity_data(market: str, as_of: str | None = None) -> dict[str, float | None]:
    """gather에서 유동성 지표 수집.

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

        - m2_yoy : float — M2 통화량 전년비 증가율 (%)
        - fed_bs_change_pct : float — 연준 대차대조표 13주 변화율 (%)
        - hy_spread : float — HY 스프레드 (bp)
        - ig_spread : float — IG 스프레드 (bp)
        - rrp_change_pct : float — 역레포 잔액 3개월 변화율 (%)
    """
    g = get_gather(as_of)
    data: dict[str, float | None] = {}

    data["m2_yoy"] = fetch_yoy(g, "M2SL")
    data["fed_bs_change_pct"] = fetch_change_pct(g, "WALCL", 13)

    hy = fetch_latest(g, "BAMLH0A0HYM2")
    if hy is not None:
        data["hy_spread"] = hy * 100

    ig = fetch_latest(g, "BAMLC0A0CM")
    if ig is not None:
        data["ig_spread"] = ig * 100

    data["rrp_change_pct"] = fetch_change_pct(g, "RRPONTSYD", 63)

    return {k: v for k, v in data.items() if v is not None}


def calcLiquidity(*, market: str = "US", as_of: str | None = None, overrides: dict | None = None, **kwargs) -> dict:
    """유동성 환경 종합 분석 — M2 + 연준 B/S + 신용스프레드 + FCI.

    Parameters
    ----------
    market : str
        ``"US"`` | ``"KR"``.
    as_of : str | None
        기준일. ``None`` 이면 최신.
    overrides : dict | None
        지표 강제 치환 (예: ``{"m2_yoy": 5.0}``).

    Returns
    -------
    dict
        - market : str — 시장 코드
        - regime : str — 유동성 국면 (``"abundant"``/``"neutral"``/``"tight"``)
        - regimeLabel : str — 국면 한글명 (``"풍부"``/``"중립"``/``"긴축"``)
        - score : float — 유동성 종합 점수 (점, -100~100)
        - signals : list[str] — 판별에 사용된 신호 목록
        - nfci : dict | None — 시카고 연준 NFCI (value:float, regime:str, regimeLabel:str, description:str). US 전용.
        - fci : dict | None — 자체 FCI (value:float, regime:str, regimeLabel:str, components:dict, description:str)
        - timeseries : dict — m2 / hy_spread / ig_spread 시계열
    """
    data = _fetch_liquidity_data(market, as_of=as_of)
    if overrides:
        data = apply_overrides(data, overrides)

    regime = classifyLiquidityRegime(
        m2_yoy=data.get("m2_yoy"),
        fed_bs_change_pct=data.get("fed_bs_change_pct"),
        hy_spread=data.get("hy_spread"),
        ig_spread=data.get("ig_spread"),
        rrp_change_pct=data.get("rrp_change_pct"),
    )

    result = {
        "market": market.upper(),
        "regime": regime.regime,
        "regimeLabel": regime.regimeLabel,
        "score": regime.score,
        "signals": list(regime.signals),
    }

    # NFCI + 자체 FCI
    result["nfci"] = None
    result["fci"] = None
    g = get_gather(as_of)

    if market.upper() == "US":
        nfci_val = fetch_latest(g, "NFCI")
        if nfci_val is not None:
            result["nfci"] = {
                "value": round(nfci_val, 3),
                "regime": "tight" if nfci_val > 0 else "loose",
                "regimeLabel": "긴축" if nfci_val > 0 else "완화",
                "description": f"NFCI {nfci_val:+.3f} — {'긴축' if nfci_val > 0 else '완화'} (평균=0)",
            }

    # 자체 FCI
    from dartlab.macro.fci import calcFCI

    if market.upper() == "US":
        sid_map = {
            "policy_rate": "FEDFUNDS",
            "long_rate": "DGS10",
            "credit_spread": "BAMLH0A0HYM2",
            "equity": "SP500",
            "fx": "DTWEXBGS",
        }
    else:
        sid_map = {
            "policy_rate": "BASE_RATE",
            "long_rate": "TREASURY_3Y",
            "credit_spread": "CORP_BOND_3Y",
            "fx": "USDKRW",
        }

    fci_vars: dict[str, list[float]] = {}
    for key, sid in sid_map.items():
        series = fetch_series_list(g, sid)
        if series:
            fci_vars[key] = series

    if len(fci_vars) >= 3:
        fci_result = calcFCI(fci_vars, market=market)
        result["fci"] = {
            "value": fci_result.value,
            "regime": fci_result.regime,
            "regimeLabel": fci_result.regimeLabel,
            "components": fci_result.components,
            "description": fci_result.description,
        }

    result["timeseries"] = collect_timeseries(g, {"m2": "M2SL", "hy_spread": "BAMLH0A0HYM2", "ig_spread": "BAMLC0A0CM"})

    return result
