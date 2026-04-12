"""시나리오 실행 + 비교 엔진.

프리셋 → overrides → dartlab.macro("종합") → 결과 비교.
"""

from __future__ import annotations

import logging

log = logging.getLogger(__name__)


def run_scenario(
    name: str,
    *,
    severity: str | None = None,
    market: str = "US",
    compare: bool = True,
) -> dict:
    """시나리오 실행.

    Args:
        name: 시나리오 이름 ("2008 금융위기", "신용 충격", "금리 충격 + 유가 충격")
        severity: 심각도 (유형별 시나리오용. mild/moderate/severe/extreme)
        market: "US" | "KR"
        compare: True면 현재 baseline과 비교

    Returns:
        dict:
            scenario: 시나리오 적용 결과 (macro 종합과 동일 구조)
            baseline: 현재 상태 (compare=True일 때)
            delta: 주요 지표 변화량 (compare=True일 때)
            meta: 시나리오 메타데이터
    """
    from .presets import get_scenario

    preset = get_scenario(name, severity=severity, market=market)
    if preset is None:
        msg = f"시나리오 '{name}'을 찾을 수 없습니다. dartlab.macro.scenario()로 목록을 확인하세요."
        raise ValueError(msg)

    overrides = preset["overrides"]

    # 시나리오 적용 실행
    from dartlab.macro.summary import analyze_summary

    scenario_result = analyze_summary(market=market, overrides=overrides)

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
        baseline_result = analyze_summary(market=market)
        result["baseline"] = baseline_result
        result["delta"] = _compute_delta(baseline_result, scenario_result)

    return result


def compare_scenarios(
    scenarios: list[str],
    *,
    severity: str | None = None,
    market: str = "US",
) -> dict:
    """여러 시나리오 동시 비교.

    Args:
        scenarios: 시나리오 이름 리스트
        severity: 공통 심각도
        market: "US" | "KR"

    Returns:
        dict:
            baseline: 현재 상태
            scenarios: {name: result}
            comparison: 비교 테이블
    """
    from dartlab.macro.summary import analyze_summary

    baseline = analyze_summary(market=market)
    results: dict[str, dict] = {}

    for name in scenarios:
        try:
            r = run_scenario(name, severity=severity, market=market, compare=False)
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


def _compute_delta(baseline: dict, scenario: dict) -> dict:
    """baseline vs scenario 주요 지표 변화량."""
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
