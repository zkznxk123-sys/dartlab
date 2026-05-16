"""매크로 regime → 자산배분 가중치 매핑.

순수 판정 함수. L1.5 synth SSOT — macro/summary 가 소비.

학술 근거:
- Ilmanen (2011): "Expected Returns" — regime-based allocation
- Bridgewater: All-Weather + Pure Alpha regime decomposition
- CFA Institute (2025): "Mind the Cycle: From Macro Shifts to Portfolio Plays"
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AllocationResult:
    """자산배분 가중치 결과."""

    equity: int  # 주식 (%)
    bond: int  # 채권 (%)
    gold: int  # 금 (%)
    cash: int  # 현금 (%)
    regime: str  # 적용된 regime
    rationale: list[str]  # 배분 근거


# ── 기본 배분 테이블 (regime × phase) ──

_BASE_ALLOCATION = {
    ("favorable", "expansion"): (70, 20, 5, 5),
    ("favorable", "recovery"): (60, 25, 5, 10),
    ("favorable", ""): (60, 25, 5, 10),
    ("neutral", "expansion"): (55, 25, 10, 10),
    ("neutral", "recovery"): (50, 30, 10, 10),
    ("neutral", "slowdown"): (40, 35, 15, 10),
    ("neutral", ""): (50, 30, 10, 10),
    ("unfavorable", "slowdown"): (30, 40, 15, 15),
    ("unfavorable", "contraction"): (20, 40, 20, 20),
    ("unfavorable", ""): (25, 40, 20, 15),
}


def regimeToAllocation(macroResult: dict) -> AllocationResult:
    """매크로 종합 결과 → 4 자산 배분 + 근거.

    Capabilities:
        macro/summary 의 통합 dict (overall + cycle + sentiment + liquidity
        + crisis) 를 받아 주식/채권/금/현금 4 자산 배분 비중 (%) 과 산정
        근거 리스트를 반환. (overall, phase) base 룩업 후 sentiment/FCI/
        Minsky 시그널로 단계적 조정.

    Args:
        macroResult: summary 축 결과 dict.
            필수 키: ``overall`` (favorable/neutral/unfavorable),
            ``cycle.phase``. 선택 키: ``sentiment.fearGreed.score``,
            ``liquidity.fci.regime``, ``crisis.minskyPhase.phase``.

    Returns:
        AllocationResult dataclass:
            - ``equity``/``bond``/``gold``/``cash`` (int): 비중 % (합계 100)
            - ``regime`` (str): 적용된 regime 라벨 (e.g. "favorable/expansion")
            - ``rationale`` (list[str]): 배분 결정 근거 라인 리스트

    Raises:
        없음.

    Example:
        >>> r = regimeToAllocation({"overall": "favorable", "cycle": {"phase": "expansion"}})
        >>> r.equity + r.bond + r.gold + r.cash
        100

    Guide:
        base 테이블 (10 조합) → fearGreed 극단 → FCI tight/loose → Minsky
        overtrading/discredit 순서로 점진 조정. 합계 100 보정은 cash 흡수.
        Bridgewater All-Weather + Ilmanen regime allocation.

    SeeAlso:
        - ``dartlab.synth.quadrant.classifyQuadrant``
        - ``dartlab.macro.summary`` (호출자)

    Requires:
        macroResult 가 macro.summary 의 출력 스키마와 일치.

    AIContext:
        rationale 리스트는 각 조정 단계의 근거 시그널을 한 줄씩 추적. UI/
        리포트에서 "왜 이 비중인가" 설명에 그대로 사용. cash 잔량 보정
        라인은 명시되지 않으므로 합계 != 100 발견 시 cash 보정 라인 추가
        주의.

    LLM Specifications:
        AntiPatterns:
            - 결과 비중을 즉시 매수/매도 신호로 변환 금지. 정성 권고이며
              개별 종목/만기/통화는 별도 결정.
            - rationale 가 적다고 confidence 가 낮다고 단정 금지 — base
              테이블만으로도 충분히 신뢰 가능한 케이스 존재.
        OutputSchema:
            AllocationResult (frozen dataclass):
            ``{equity:int, bond:int, gold:int, cash:int, regime:str,
            rationale:list[str]}``.
        Prerequisites:
            macro/summary 의 ``overall``, ``cycle.phase`` 둘 다 존재.
            sentiment/liquidity/crisis 는 선택.
        Freshness:
            macro/summary 의 freshness (보통 일/주간 갱신).
        Dataflow:
            (overall, phase) → _BASE_ALLOCATION 룩업 → fearGreed/FCI/Minsky
            조정 → cash 합계 100 보정.
        TargetMarkets: Global (4 자산 vehicle 은 시장 무관).
    """
    overall = macroResult.get("overall", "neutral")
    cycle = macroResult.get("cycle") or {}
    phase = cycle.get("phase", "")
    rationale: list[str] = []

    key = (overall, phase)
    if key not in _BASE_ALLOCATION:
        key = (overall, "")
    base = _BASE_ALLOCATION.get(key, (50, 30, 10, 10))
    equity, bond, gold, cash = base
    rationale.append(f"기본: {overall}/{phase or '?'} → 주식{equity}/채권{bond}/금{gold}/현금{cash}")

    fg = (macroResult.get("sentiment") or {}).get("fearGreed") or {}
    fg_score = fg.get("score")
    if fg_score is not None:
        if fg_score < 20:
            equity = min(equity + 10, 80)
            cash = max(cash - 10, 0)
            rationale.append(f"극단공포({fg_score:.0f}) → 주식 +10%p (역투자)")
        elif fg_score > 80:
            equity = max(equity - 10, 10)
            cash = min(cash + 10, 40)
            rationale.append(f"극단탐욕({fg_score:.0f}) → 주식 -10%p (경계)")

    fci = (macroResult.get("liquidity") or {}).get("fci") or {}
    fci_regime = fci.get("regime")
    if fci_regime == "tight":
        bond = min(bond + 5, 60)
        equity = max(equity - 5, 10)
        rationale.append("FCI 긴축 → 채권 +5%p")
    elif fci_regime == "loose":
        equity = min(equity + 5, 80)
        bond = max(bond - 5, 10)
        rationale.append("FCI 완화 → 주식 +5%p")

    crisis = macroResult.get("crisis") or {}
    minsky = crisis.get("minskyPhase") or {}
    if minsky.get("phase") in ("overtrading", "discredit"):
        gold = min(gold + 5, 30)
        equity = max(equity - 5, 10)
        rationale.append(f"Minsky {minsky.get('phaseLabel', '')} → 금 +5%p")

    total = equity + bond + gold + cash
    if total != 100:
        diff = 100 - total
        cash = max(cash + diff, 0)

    regime_label = f"{overall}/{phase}" if phase else overall

    return AllocationResult(
        equity=equity,
        bond=bond,
        gold=gold,
        cash=cash,
        regime=regime_label,
        rationale=rationale,
    )
