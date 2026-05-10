"""시나리오 실행 + 비교 엔진.

프리셋 → overrides → dartlab.macro("종합") → 결과 비교.
"""

from __future__ import annotations

import logging

log = logging.getLogger(__name__)


def runScenario(
    name: str,
    *,
    severity: str | None = None,
    market: str = "US",
    compare: bool = True,
) -> dict:
    """시나리오 실행.

    프리셋 overrides 를 매크로 종합에 적용하고, 선택적으로
    현재 baseline 과 비교 delta 를 산출한다.

    Parameters
    ----------
    name : str
        시나리오 이름. ``"2008 금융위기"``, ``"신용 충격"``,
        ``"금리 충격 + 유가 충격"`` (복합) 등.
    severity : str | None
        심각도. ``"mild"`` / ``"moderate"`` / ``"severe"`` / ``"extreme"``.
        유형별·구조적 시나리오에서 사용.
    market : str
        시장 구분. ``"US"`` | ``"KR"``.
    compare : bool
        ``True`` 이면 현재 baseline 과 비교 delta 포함.

    Returns
    -------
    dict
        scenario : dict — 시나리오 적용 매크로 종합 결과 (macro 종합과 동일 구조)
        baseline : dict | None — 현재 상태 (compare=True 일 때만 포함)
        delta : dict | None — 주요 지표 변화량 (compare=True 일 때만 포함)
        meta : dict — 시나리오 메타데이터 (name:str, description:str,
            type:str, severity:str, transmission:str, reference:str,
            outcome:str, overrides:dict)
    """
    from .presets import getScenario

    preset = getScenario(name, severity=severity, market=market)
    if preset is None:
        msg = f"시나리오 '{name}'을 찾을 수 없습니다. dartlab.macro.scenarios.scenario()로 목록을 확인하세요."
        raise ValueError(msg)

    overrides = preset["overrides"]

    # 시나리오 적용 실행
    from dartlab.macro.summary import analyzeSummary

    scenario_result = analyzeSummary(market=market, overrides=overrides)

    result: dict = {
        "scenario": scenario_result,
        "meta": {
            "name": name,
            "description": preset.get("description"),
            "type": preset.get("type"),
            "severity": preset.get("severity"),
            "transmission": preset.get("transmission"),
            "reference": preset.get("reference"),
            "outcome": preset.get("outcome"),
            "overrides": overrides,
        },
    }

    # baseline 비교
    if compare:
        baseline_result = analyzeSummary(market=market)
        result["baseline"] = baseline_result
        result["delta"] = _computeDelta(baseline_result, scenario_result)

    return result


def compareScenarios(
    scenarios: list[str],
    *,
    severity: str | None = None,
    market: str = "US",
) -> dict:
    """여러 시나리오 동시 비교.

    각 시나리오를 실행하고, baseline 대비 점수·국면·위기 수준 등을
    비교 테이블로 정리한다.

    Parameters
    ----------
    scenarios : list[str]
        시나리오 이름 리스트.
    severity : str | None
        모든 시나리오에 공통 적용할 심각도.
    market : str
        시장 구분. ``"US"`` | ``"KR"``.

    Returns
    -------
    dict
        baseline : dict — 현재 상태 요약
            score : float — 매크로 종합 점수 (점)
            overall : str — 종합 판정 (bullish/neutral/bearish 등)
        scenarios : dict[str, dict] — {시나리오명: run_scenario 결과}
        comparison : list[dict] — 비교 테이블. 각 항목:
            scenario : str — 시나리오명
            severity : str — 심각도
            type : str — 충격 유형
            score : float — 시나리오 점수 (점)
            score_delta : float — baseline 대비 점수 변화 (점)
            overall : str — 종합 판정
            cycle_phase : str — 경기 국면
            crisis_zone : str — 위기 수준
            transmission : str — 전파 경로
            outcome : str — 예상 결과
    """
    from dartlab.macro.summary import analyzeSummary

    baseline = analyzeSummary(market=market)
    results: dict[str, dict] = {}

    for name in scenarios:
        try:
            r = runScenario(name, severity=severity, market=market, compare=False)
            results[name] = r
        except ValueError:
            log.warning("시나리오 '%s' 실행 실패", name)
            continue

    # 비교 테이블
    comparison: list[dict] = []
    baseline_score = baseline.get("score", 0)
    baseline_overall = baseline.get("overall", "neutral")

    for name, r in results.items():
        sc = r["scenario"]
        comparison.append(
            {
                "scenario": name,
                "severity": r["meta"].get("severity", ""),
                "type": r["meta"].get("type", ""),
                "score": sc.get("score", 0),
                "score_delta": round(sc.get("score", 0) - baseline_score, 2),
                "overall": sc.get("overall", ""),
                "cycle_phase": (sc.get("cycle") or {}).get("phase", ""),
                "crisis_zone": ((sc.get("crisis") or {}).get("recessionDashboard") or {}).get("zone", ""),
                "transmission": r["meta"].get("transmission", ""),
                "outcome": r["meta"].get("outcome", ""),
            }
        )

    return {
        "baseline": {
            "score": baseline_score,
            "overall": baseline_overall,
        },
        "scenarios": results,
        "comparison": comparison,
    }


def _computeDelta(baseline: dict, scenario: dict) -> dict:
    """baseline vs scenario 주요 지표 변화량.

    Parameters
    ----------
    baseline : dict
        현재 상태 매크로 종합 결과.
    scenario : dict
        시나리오 적용 매크로 종합 결과.

    Returns
    -------
    dict
        score : dict — 종합 점수 변화
            baseline : float — 기존 점수 (점)
            scenario : float — 시나리오 점수 (점)
            change : float — 변화량 (점)
        overall : dict — 종합 판정 변화
            baseline : str — 기존 판정
            scenario : str — 시나리오 판정
        cycle_phase : dict — 경기 국면 변화
            baseline : str — 기존 국면
            scenario : str — 시나리오 국면
            changed : bool — 변화 여부
        crisis_zone : dict — 위기 수준 변화
            baseline : str — 기존 수준
            scenario : str — 시나리오 수준
            changed : bool — 변화 여부
        fear_greed : dict — 공포·탐욕 지수 변화
            baseline : float | None — 기존 점수 (점)
            scenario : float | None — 시나리오 점수 (점)
            change : float | None — 변화량 (점)
        historical_risk : dict — 역사적 리스크 수준 변화
            baseline : str — 기존 수준
            scenario : str — 시나리오 수준
            changed : bool — 변화 여부
        summary : str — 변화 종합 서술
    """
    delta: dict = {}

    # score
    b_score = baseline.get("score", 0)
    s_score = scenario.get("score", 0)
    delta["score"] = {
        "baseline": round(b_score, 2),
        "scenario": round(s_score, 2),
        "change": round(s_score - b_score, 2),
    }

    # overall
    delta["overall"] = {
        "baseline": baseline.get("overall", ""),
        "scenario": scenario.get("overall", ""),
    }

    # cycle phase
    b_cycle = (baseline.get("cycle") or {}).get("phase", "")
    s_cycle = (scenario.get("cycle") or {}).get("phase", "")
    delta["cycle_phase"] = {
        "baseline": b_cycle,
        "scenario": s_cycle,
        "changed": b_cycle != s_cycle,
    }

    # crisis zone
    b_crisis = ((baseline.get("crisis") or {}).get("recessionDashboard") or {}).get("zone", "")
    s_crisis = ((scenario.get("crisis") or {}).get("recessionDashboard") or {}).get("zone", "")
    delta["crisis_zone"] = {
        "baseline": b_crisis,
        "scenario": s_crisis,
        "changed": b_crisis != s_crisis,
    }

    # sentiment
    b_fg = ((baseline.get("sentiment") or {}).get("fearGreed") or {}).get("score", 50)
    s_fg = ((scenario.get("sentiment") or {}).get("fearGreed") or {}).get("score", 50)
    delta["fear_greed"] = {
        "baseline": round(b_fg, 1) if b_fg else None,
        "scenario": round(s_fg, 1) if s_fg else None,
        "change": round(s_fg - b_fg, 1) if b_fg and s_fg else None,
    }

    # historicalContext risk
    b_risk = ((baseline.get("crisis") or {}).get("historicalContext") or {}).get("riskLevel", "low")
    s_risk = ((scenario.get("crisis") or {}).get("historicalContext") or {}).get("riskLevel", "low")
    delta["historical_risk"] = {
        "baseline": b_risk,
        "scenario": s_risk,
        "changed": b_risk != s_risk,
    }

    # 종합 서술
    changes: list[str] = []
    if delta["score"]["change"] < -2:
        changes.append(f"종합 점수 {delta['score']['change']:+.1f} (심각한 악화)")
    elif delta["score"]["change"] < -1:
        changes.append(f"종합 점수 {delta['score']['change']:+.1f} (악화)")
    elif delta["score"]["change"] > 1:
        changes.append(f"종합 점수 {delta['score']['change']:+.1f} (개선)")

    if delta["cycle_phase"]["changed"]:
        changes.append(f"경기 국면: {b_cycle} → {s_cycle}")
    if delta["crisis_zone"]["changed"]:
        changes.append(f"위기 수준: {b_crisis} → {s_crisis}")

    delta["summary"] = ". ".join(changes) if changes else "유의미한 변화 없음"

    return delta
