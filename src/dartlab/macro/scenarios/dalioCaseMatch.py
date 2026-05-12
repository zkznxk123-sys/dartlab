"""Dalio Part 2 Detail Case Matching SSOT.

Ray Dalio *Big Debt Crises* Part 2 — 3 detailed case studies (Weimar, Great Depression,
Subprime). 각 사례의 연도별 매크로 시그니처와 **현재 상태** 를 코사인 유사도로 비교해
"지금 어느 역사 국면에 가까운가" + "다음 단계 진행 경로 힌트" 를 반환.

데이터: `reference/data/dalioDetailCases.json`.
"""

from __future__ import annotations

import json
import logging
import math
from importlib import resources
from typing import Any

log = logging.getLogger(__name__)


_SIG_KEYS = ["totalDebtToGdp", "creditGap", "realRate", "gdpGrowth", "debtServiceYoY"]
# 각 키의 정규화 스케일 (평균적 변동 폭)
_SCALE = {
    "totalDebtToGdp": 100.0,  # 100%
    "creditGap": 10.0,  # 10 %p
    "realRate": 5.0,  # 5 %
    "gdpGrowth": 5.0,  # 5 %
    "debtServiceYoY": 3.0,  # 3 %p
}


def _loadCases() -> dict:
    """Dalio detail case compendium 로드.

    과거 사고 class (2026-04-19): 번들 리소스 누락 시 silent `{"cases": []}` →
    consumer 가 "매칭 없음" 으로 처리 → 사용자에게 crisis 비교 엔진이 깨졌음을
    알리지 않음. loud-fail 로 전환.
    """
    try:
        with (
            resources.files("dartlab.reference.data").joinpath("dalioDetailCases.json").open("r", encoding="utf-8") as f
        ):
            return json.load(f)
    except (FileNotFoundError, OSError) as e:
        raise FileNotFoundError(
            f"필수 번들 리소스 누락: dartlab/reference/data/dalioDetailCases.json ({e})\n"
            f"  → pip install -U --force-reinstall dartlab"
        ) from e
    except json.JSONDecodeError as e:
        raise RuntimeError(f"dalioDetailCases.json 포맷 손상: {e}") from e


def _vectorize(state: dict[str, Any]) -> list[float | None]:
    """상태 → (정규화된) 시그니처 벡터."""
    return [(state[k] / _SCALE[k]) if (k in state and state[k] is not None) else None for k in _SIG_KEYS]


def _cosineSim(a: list[float | None], b: list[float | None]) -> float:
    """공통 유효 축만 사용하는 코사인 유사도."""
    pairs = [(x, y) for x, y in zip(a, b) if x is not None and y is not None]
    if len(pairs) < 2:
        return 0.0
    dot = sum(x * y for x, y in pairs)
    na = math.sqrt(sum(x * x for x, _ in pairs))
    nb = math.sqrt(sum(y * y for _, y in pairs))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


def matchDalioDetailCase(
    currentState: dict[str, float | None],
    *,
    topK: int = 3,
) -> dict:
    """현재 매크로 상태 → Dalio Part 2 3 사례 중 가장 가까운 stage.

    Parameters
    ----------
    currentState : 현재 상태 dict. 키: totalDebtToGdp, creditGap, realRate, gdpGrowth,
        debtServiceYoY. 결측은 None 허용.
    topK : 상위 몇 개 매치를 반환할지 (기본 3).

    Returns
    -------
    dict
        matches : list of top-K matches, 각각
            {caseId, caseLabel, year, phase, similarity, note, nextStage}
        bestPhase : 가장 유사한 사례의 phase
        bestRegimeVariant : 가장 유사한 사례의 regimeVariant
        bestOutcome : 해당 사례의 최종 결과 (beautiful_deleveraging / ugly_* / ...)
    """
    cases_doc = _loadCases()
    cases = cases_doc.get("cases", [])
    if not cases:
        return {"matches": [], "bestPhase": None, "bestRegimeVariant": None, "bestOutcome": None}

    v_curr = _vectorize(currentState)

    candidates: list[dict] = []
    for case in cases:
        stages = case.get("stages", [])
        for i, st in enumerate(stages):
            v_st = _vectorize(st)
            sim = _cosineSim(v_curr, v_st)
            next_stage = stages[i + 1] if i + 1 < len(stages) else None
            candidates.append(
                {
                    "caseId": case["id"],
                    "caseLabel": case["label"],
                    "year": st.get("year"),
                    "phase": st.get("phase"),
                    "similarity": round(sim, 4),
                    "note": st.get("note", ""),
                    "nextStage": {
                        "year": next_stage.get("year"),
                        "phase": next_stage.get("phase"),
                        "note": next_stage.get("note"),
                    }
                    if next_stage
                    else None,
                    "_caseRegime": case.get("regimeVariant"),
                    "_caseOutcome": case.get("outcome"),
                }
            )

    candidates.sort(key=lambda x: x["similarity"], reverse=True)
    top = candidates[:topK]

    best = top[0] if top else None
    return {
        "matches": [{k: v for k, v in c.items() if not k.startswith("_")} for c in top],
        "bestPhase": best["phase"] if best else None,
        "bestRegimeVariant": best["_caseRegime"] if best else None,
        "bestOutcome": best["_caseOutcome"] if best else None,
    }
