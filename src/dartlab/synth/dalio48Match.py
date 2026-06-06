"""Dalio 48 Case Compendium Matching SSOT.

Ray Dalio *Big Debt Crises* Part 3 — 48 historical deleveraging episodes compendium.
현재 상태를 48 케이스와 특성 공간 거리로 비교해 **가장 근접한 N 케이스** +
**archetype (deflationary/inflationary)** 분포를 반환.

데이터: `reference/data/dalio48Cases.json`. 공개 가능한 20+ 케이스 수록 (subset),
미수록은 향후 데이터 세션으로.
"""

from __future__ import annotations

import json
import logging
import math
from importlib import resources

log = logging.getLogger(__name__)


_SIG_KEYS = ["peakDebtToGdp", "peakCreditGap", "troughRealRate", "troughGdpGrowth"]
_SCALE = {
    "peakDebtToGdp": 150.0,
    "peakCreditGap": 15.0,
    "troughRealRate": 20.0,
    "troughGdpGrowth": 8.0,
}


def _loadCases() -> list[dict]:
    """Dalio 48 케이스 compendium 로드.

    과거 사고 (2026-04-19 class): 번들 리소스 누락 시 조용히 `[]` 리턴 →
    match48Cases 가 빈 결과를 "매칭 없음" 으로 반환 → 사용자는 crisis
    감지 파이프라인이 정상 동작하는 줄 착각. silent-fail 대신 loud-fail.
    """
    try:
        with resources.files("dartlab.reference.data").joinpath("dalio48Cases.json").open("r", encoding="utf-8") as f:
            return json.load(f).get("cases", [])
    except (FileNotFoundError, OSError) as e:
        raise FileNotFoundError(
            f"필수 번들 리소스 누락: dartlab/reference/data/dalio48Cases.json ({e})\n"
            f"  → pip install -U --force-reinstall dartlab\n"
            f"  (wheel 패키징 사고 시 이 파일이 빠질 수 있음)"
        ) from e
    except json.JSONDecodeError as e:
        raise RuntimeError(f"dalio48Cases.json 포맷 손상: {e}") from e


def _vec(d: dict) -> list[float | None]:
    return [(d[k] / _SCALE[k]) if (k in d and d[k] is not None) else None for k in _SIG_KEYS]


def _euclideanDist(a: list[float | None], b: list[float | None]) -> float:
    pairs = [(x, y) for x, y in zip(a, b) if x is not None and y is not None]
    if len(pairs) < 2:
        return float("inf")
    return math.sqrt(sum((x - y) ** 2 for x, y in pairs))


def match48Cases(
    currentState: dict[str, float | None],
    *,
    topK: int = 5,
) -> dict:
    """현재 상태 vs 48 케이스 → top-K 최근접 매칭.

    Capabilities:
        Dalio "Principles for Navigating Big Debt Crises" 48 부채 위기 케이스
        DB 와 현재 매크로 상태 (peakDebtToGdp/peakCreditGap/troughRealRate/
        troughGdpGrowth) Euclidean 거리 매칭 → top-K + archetype 분포
        (deflationary/inflationary) + outcome 분포.

    Args:
        currentState: dict 키 (peakDebtToGdp/peakCreditGap/troughRealRate/
            troughGdpGrowth). 결측 None 허용.
        topK: 반환할 상위 매칭 수. 기본 5.

    Returns:
        dict — matches(list of caseId/label/country/archetype/outcome/distance/
        reserveCurrency)/archetypeDistribution/outcomeDistribution/
        dominantArchetype.

    Example:
        >>> r = match48Cases({"peakDebtToGdp": 110, "peakCreditGap": 8})
        >>> r["dominantArchetype"]
        'deflationary'

    Guide:
        dominantArchetype = top-K 분포의 최빈값. distance < 1.0 = 매우 유사.
        매크로 시나리오 베이스로 활용.

    When:
        ``runScenario`` "Dalio 48 매칭" + AI 부채 위기 답변.

    How:
        _loadCases (JSON) → _vec 정규화 (각 신호 / scale) → Euclidean → sort →
        top-K → archetype/outcome 분포.

    Requires:
        Dalio 48 cases JSON (dartlab 패키지 정적 자산).

    Raises:
        없음 — 빈 cases 면 빈 dict 반환.

    See Also:
        - matchDalioDetailCase : 단일 케이스 상세 매칭
        - runScenario : 시나리오 실행

    AIContext:
        top 1~2 케이스 label + dominantArchetype 인용으로 "1990 일본과 유사
        (deflationary)" 답변.

    LLM Specifications:
        AntiPatterns:
            - 단일 케이스 (top 1) 만 인용 + 분포 미노출
            - distance 절대값 단정 (≥ 2.0 면 신뢰 약함)
        OutputSchema:
            ``{matches, archetypeDistribution, outcomeDistribution,
            dominantArchetype}``.
        Prerequisites: cases JSON 로드 가능.
        Freshness: 정적 (Dalio 책 발간 후 갱신 없음).
        Dataflow: currentState → 정규화 → Euclidean → top-K → 분포.
        TargetMarkets: Global (48 케이스 다국적). KR/US 적용.
    """
    cases = _loadCases()
    if not cases:
        return {
            "matches": [],
            "archetypeDistribution": {},
            "outcomeDistribution": {},
            "dominantArchetype": None,
        }

    v_curr = _vec(currentState)

    scored: list[dict] = []
    for c in cases:
        dist = _euclideanDist(v_curr, _vec(c))
        scored.append(
            {
                "caseId": c["id"],
                "label": f"{c['country']} {c['startYear']}-{c['endYear']}",
                "country": c["country"],
                "archetype": c["archetype"],
                "outcome": c["outcome"],
                "distance": round(dist, 4),
                "reserveCurrency": c.get("reserveCurrency", False),
            }
        )

    scored.sort(key=lambda x: x["distance"])
    top = scored[:topK]

    arch_dist: dict[str, int] = {}
    out_dist: dict[str, int] = {}
    for m in top:
        arch_dist[m["archetype"]] = arch_dist.get(m["archetype"], 0) + 1
        out_dist[m["outcome"]] = out_dist.get(m["outcome"], 0) + 1

    dominant = max(arch_dist.items(), key=lambda x: x[1])[0] if arch_dist else None

    return {
        "matches": top,
        "archetypeDistribution": arch_dist,
        "outcomeDistribution": out_dist,
        "dominantArchetype": dominant,
    }
