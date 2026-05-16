"""매크로 재고순환 분석 — ISM 재고사이클 + 자산배분 바로미터.

투자전략 7: 재고 흐름이 예상하지 못한 성과를 결정한다
투자전략 8: 재고순환지표로 주가 상승을 예측하자
투자전략 13: ISM지수가 세계 자산배분의 바로미터다
투자전략 34: ISM제조업지수가 55를 하회하면 미국 금리인상 종결
"""

from __future__ import annotations

from dartlab.macro.cycles.inventoryCycle import classifyInventoryPhase, ismBarometer
from dartlab.macro.cycles.sentiment import ismAssetAllocation


def _fetchIsmData(market: str, asOf: str | None = None) -> dict[str, float | None]:
    """gather에서 ISM/재고 지표 수집.

    Parameters
    ----------
    market : str
        시장 코드 ("US" | "KR").
    as_of : str | None
        기준일 (YYYY-MM-DD). None이면 최신.

    Returns
    -------
    dict[str, float | None]
        US 시장:
            ism_pmi : float — ISM 제조업 PMI (pt)
            ism_pmi_prev : float — 전기 ISM PMI (pt)
            ism_new_orders : float — ISM 신규주문 (pt)
            ism_new_orders_prev : float — 전기 ISM 신규주문 (pt)
            ism_inventories : float — ISM 재고 (pt)
            ism_inventories_prev : float — 전기 ISM 재고 (pt)
            new_orders : float — 제조업 신규주문 (백만달러)
            inventories : float — 제조업 재고 (백만달러)
        KR 시장:
            manufacturing : float — 광공업생산지수 (pt)
            manufacturing_prev : float — 전기 광공업생산지수 (pt)
            bsi : float — 기업경기실사지수 (pt, 100 기준)
            bsi_prev : float — 전기 BSI (pt)
    """
    from dartlab.macro.seriesFetch import fetchLatestWithPrev, getGather

    g = getGather(asOf)
    data: dict[str, float | None] = {}

    if market.upper() == "US":
        for label, sid in [
            ("ism_pmi", "AMTMNO"),
            ("ism_new_orders", "AMTMNO"),
            ("ism_inventories", "AMTMUO"),
            ("new_orders", "NEWORDER"),
            ("inventories", "BUSINV"),
        ]:
            val, prev = fetchLatestWithPrev(g, sid)
            if val is not None:
                data[label] = val
            if prev is not None:
                data[f"{label}_prev"] = prev
    else:
        for label, sid in [("manufacturing", "MANUFACTURING"), ("bsi", "BSI_ALL")]:
            val, prev = fetchLatestWithPrev(g, sid)
            if val is not None:
                data[label] = val
            if prev is not None:
                data[f"{label}_prev"] = prev

    return data


def analyzeInventory(*, market: str = "US", asOf: str | None = None, overrides: dict | None = None, **kwargs) -> dict:
    """재고순환 종합 분석 — ISM 4 국면 + 바로미터 + 자산배분.

    Capabilities:
        ISM 신규주문/재고 비율로 재고순환 4 국면 판별 (recovery/expansion/
        slowdown/contraction) + ISM PMI 수준에 따른 자산배분 바로미터 +
        equityImplication + bondWeight 권고. Damodaran/Howard Marks 의 cycle
        positioning 표준 입력. KR 은 BOK PMI fallback.

    Args:
        market: "US" | "KR" (기본 "US").
        asOf: 기준일 (YYYY-MM-DD). None 시 최신.
        overrides: AI 가정 교체 (예: ``{"ism_pmi": 52}``).

    Returns:
        dict:
            - ``market`` (str): 시장 코드.
            - ``inventoryPhase`` (dict | None): 4 국면 + ratio + Mom +
              equityImplication.
            - ``ismBarometer`` (dict | None, US 전용): PMI level + zone +
              equityStance + rateImplication.
            - ``ismAllocation`` (dict | None, US 전용): stance + equity/bond
              weight.
            - ``timeseries`` (dict): ism_pmi, new_orders, inventories.

    Raises:
        없음.

    Example:
        >>> r = analyzeInventory(market="US")
        >>> r["inventoryPhase"]["phase"], r["ismBarometer"]["level"]
        ('recovery', 51.5)

    Guide:
        - recovery (신규주문 ↑ 재고 ↓): 주식 bullish, 경기민감주 매수.
        - expansion (둘 다 ↑): 주식 모멘텀 강함.
        - slowdown (신규주문 ↓ 재고 ↑): 주식 bearish, 채권 강세.
        - contraction (둘 다 ↓): 주식 매도, 안전자산.
        ISM 50 = 확장/수축 경계.

    See Also:
        - ``classifyInventoryPhase``: 4 국면 단독
        - ``calcLiquidity``: 유동성 regime
        - ``analyzeCycle``: macro cycle 종합 (본 함수 입력)

    When:
        ``analyzeSummary`` 의 inventory 축 진입점. AI 자산배분 답변 1 차.

    How:
        ISM 신규주문/재고 → 비율 + MoM → 4 국면 → equityImplication. PMI 수준 →
        barometer zone → allocation stance.

    Requires:
        ISM PMI + 신규주문 + 재고 시계열 (KR 은 BOK 분기).

    AIContext:
        phase + ratio + Mom 함께 인용. overrides 사용 시 가정 명시.
        zone label (확장/위축/회복/축소) 직역 인용.

    LLM Specifications:
        AntiPatterns:
            - ratio 단독 인용 — Mom (방향) 함께.
            - KR 에 ISM 직접 인용 — KR 은 BOK PMI fallback.
        OutputSchema:
            ``{market: str, inventoryPhase: dict, ismBarometer: dict,
              ismAllocation: dict, timeseries: dict}``.
        Prerequisites:
            ISM (US) 또는 BOK PMI (KR) 시계열.
        Freshness:
            월별 (ISM 발표 직후).
        Dataflow:
            ISM data → 신규주문/재고 비율 → 4 국면 라벨 → PMI level →
            barometer zone → allocation stance.
        TargetMarkets: US (ISM), KR (BOK PMI fallback).
    """
    data = _fetchIsmData(market, asOf=asOf)
    if overrides:
        from dartlab.macro.seriesFetch import applyOverrides

        data = applyOverrides(data, overrides)
    result: dict = {"market": market.upper()}

    if market.upper() == "US":
        # ISM 기반 재고순환
        new_orders = data.get("ism_new_orders")
        inventories = data.get("ism_inventories")
        if new_orders is not None and inventories is not None:
            prev_no = data.get("ism_new_orders_prev")
            prev_inv = data.get("ism_inventories_prev")
            prev_ratio = (prev_no / prev_inv) if prev_no and prev_inv and prev_inv > 0 else None
            phase = classifyInventoryPhase(new_orders, inventories, prev_ratio)
            result["inventoryPhase"] = {
                "phase": phase.phase,
                "phaseLabel": phase.phaseLabel,
                "ratio": phase.ratio,
                "ratioMom": phase.ratioMom,
                "equityImplication": phase.equityImplication,
                "equityLabel": phase.equityLabel,
                "description": phase.description,
            }
        else:
            # fallback: 제조업 신규수주/재고
            no = data.get("new_orders")
            inv = data.get("inventories")
            if no is not None and inv is not None and inv > 0:
                prev_no2 = data.get("new_orders_prev")
                prev_inv2 = data.get("inventories_prev")
                prev_ratio2 = (prev_no2 / prev_inv2) if prev_no2 and prev_inv2 and prev_inv2 > 0 else None
                phase = classifyInventoryPhase(no, inv, prev_ratio2)
                result["inventoryPhase"] = {
                    "phase": phase.phase,
                    "phaseLabel": phase.phaseLabel,
                    "ratio": phase.ratio,
                    "ratioMom": phase.ratioMom,
                    "equityImplication": phase.equityImplication,
                    "equityLabel": phase.equityLabel,
                    "description": phase.description,
                    "source": "manufacturing_orders",
                }
            else:
                result["inventoryPhase"] = None

        # ISM 바로미터
        ism = data.get("ism_pmi")
        if ism is not None:
            ism_prev = data.get("ism_pmi_prev")
            barometer = ismBarometer(ism, ism_prev)
            result["ismBarometer"] = {
                "level": barometer.level,
                "zone": barometer.zone,
                "zoneLabel": barometer.zoneLabel,
                "equityStance": barometer.equityStance,
                "equityLabel": barometer.equityLabel,
                "rateImplication": barometer.rateImplication,
                "rateLabel": barometer.rateLabel,
                "description": barometer.description,
            }

            # ISM 자산배분 (투자전략 13)
            alloc = ismAssetAllocation(ism)
            result["ismAllocation"] = {
                "stance": alloc.stance,
                "stanceLabel": alloc.stanceLabel,
                "equityWeight": alloc.equityWeight,
                "bondWeight": alloc.bondWeight,
                "description": alloc.description,
            }
        else:
            result["ismBarometer"] = None
            result["ismAllocation"] = None

    else:
        # KR: 광공업생산 모멘텀(출하 프록시) + BSI(재고판단 프록시)
        mfg = data.get("manufacturing")
        bsi = data.get("bsi")
        if mfg is not None and bsi is not None:
            mfg_prev = data.get("manufacturing_prev")
            bsi_prev = data.get("bsi_prev")
            # 광공업생산 = 출하 프록시 (수준), BSI = 재고 판단 (50 기준)
            # BSI > 100 = 긍정, < 100 = 부정. 재고 해소 = 출하 대비 재고 감소
            # classifyInventoryPhase에 맞게: 생산(수요 프록시) vs BSI 역수(재고 프록시)
            # BSI 높으면 기업 낙관 = 재고 적극 보충 → 재고 증가
            # 200 - BSI = BSI 역수 (100 기준 대칭). 생산 / (200-BSI) ≈ 수요/재고
            inv_proxy = 200.0 - bsi  # BSI 역수: 높을수록 재고 과잉
            prev_ratio = None
            if mfg_prev is not None and bsi_prev is not None:
                inv_prev = 200.0 - bsi_prev
                if inv_prev > 0:
                    prev_ratio = mfg_prev / inv_prev
            phase = classifyInventoryPhase(mfg, inv_proxy, prev_ratio)
            result["inventoryPhase"] = {
                "phase": phase.phase,
                "phaseLabel": phase.phaseLabel,
                "ratio": phase.ratio,
                "ratioMom": phase.ratioMom,
                "equityImplication": phase.equityImplication,
                "equityLabel": phase.equityLabel,
                "description": phase.description,
                "source": "kr_manufacturing_bsi_proxy",
            }
        else:
            result["inventoryPhase"] = None

        result["ismBarometer"] = None
        result["ismAllocation"] = None

    from dartlab.macro.seriesFetch import collectTimeseries, getGather

    g = getGather(asOf)
    if market.upper() == "US":
        result["timeseries"] = collectTimeseries(
            g, {"ism_pmi": "AMTMNO", "new_orders": "AMTMNO", "inventories": "AMTMUO"}
        )
    else:
        result["timeseries"] = collectTimeseries(g, {"manufacturing": "MANUFACTURING", "bsi": "BSI_ALL"})

    return result
