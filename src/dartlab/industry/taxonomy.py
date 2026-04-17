"""taxonomy.json 로드·조회·캐시.

분류체계의 단일 진입점. 모든 빌드 단계와 조회가 이 모듈을 통한다.
"""

from __future__ import annotations

import json
import logging
from functools import lru_cache
from pathlib import Path

from dartlab.industry.types import IndustryDef, StageInfo

logger = logging.getLogger(__name__)

_DATA_DIR = Path(__file__).parent


@lru_cache(maxsize=1)
def loadTaxonomy() -> dict[str, IndustryDef]:
    """taxonomy.json을 로드하여 산업 분류체계 딕셔너리를 반환한다.

    lru_cache로 세션 내 1회만 파싱.

    Returns
    -------
    dict[str, IndustryDef]
        산업ID → IndustryDef 매핑. 각 IndustryDef에 ksicCodes, stages 포함.
    """
    path = _DATA_DIR / "taxonomy.json"
    raw = json.loads(path.read_text(encoding="utf-8"))

    result: dict[str, IndustryDef] = {}
    for indId, indData in raw.get("industries", {}).items():
        stages: list[StageInfo] = []
        for stageKey, stageData in indData.get("stages", {}).items():
            stages.append(
                StageInfo(
                    key=stageKey,
                    name=stageData.get("name", stageKey),
                    role=stageData.get("role", ""),
                    stream=stageData.get("stream", ""),
                    keywords=stageData.get("keywords", []),
                )
            )
        result[indId] = IndustryDef(
            industryId=indId,
            name=indData.get("name", indId),
            ksicCodes=indData.get("ksicCodes", []),
            stages=stages,
        )
    return result


def getIndustry(industryId: str) -> IndustryDef | None:
    """산업 ID로 IndustryDef를 조회한다.

    Parameters
    ----------
    industryId : str
        taxonomy에 등록된 산업 ID (예: "semiconductor").

    Returns
    -------
    IndustryDef | None
        매칭된 산업 정의. 없으면 None.
    """
    return loadTaxonomy().get(industryId)


def listIndustries() -> list[dict[str, str]]:
    """등록된 전체 산업 목록을 반환한다.

    Returns
    -------
    list[dict[str, str]]
        각 dict에 industryId (str), name (str), stages (int, 공정 수) 포함.
    """
    return [
        {
            "industryId": ind.industryId,
            "name": ind.name,
            "stages": len(ind.stages),
        }
        for ind in loadTaxonomy().values()
    ]


def findIndustryByKsic(ksicName: str) -> str | None:
    """KSIC 업종명으로 산업 ID를 찾는다.

    Parameters
    ----------
    ksicName : str
        KindList의 업종 컬럼값 (예: "반도체 제조업").

    Returns
    -------
    str | None
        매칭된 산업 ID. 없으면 None.
    """
    for indId, ind in loadTaxonomy().items():
        for code in ind.ksicCodes:
            if code in ksicName or ksicName in code:
                return indId
    return None


def matchStageByKeywords(
    industryId: str,
    text: str,
) -> tuple[str | None, float, list[str]]:
    """텍스트에서 키워드 매칭으로 stage를 판별한다.

    Parameters
    ----------
    industryId : str
        산업 ID.
    text : str
        매칭 대상 텍스트.

    Returns
    -------
    tuple[str | None, float, list[str]]
        (best_stage_key, confidence, matched_keywords).
    """
    ind = getIndustry(industryId)
    if ind is None or not text:
        return None, 0.0, []

    textLower = text.lower()
    scores: dict[str, tuple[int, list[str]]] = {}

    for stage in ind.stages:
        hits: list[str] = []
        for kw in stage.keywords:
            if kw.lower() in textLower:
                hits.append(kw)
        scores[stage.key] = (len(hits), hits)

    if not scores:
        return None, 0.0, []

    best = max(scores.items(), key=lambda x: x[1][0])
    bestKey, (hitCount, hitKws) = best

    if hitCount == 0:
        return None, 0.0, []

    # confidence: 키워드 매칭 수 기반, 최대 1.0
    maxHits = max(s[0] for s in scores.values())
    confidence = min(1.0, hitCount / max(maxHits, 1))

    # 2위와의 격차 반영
    sortedScores = sorted(scores.values(), key=lambda x: x[0], reverse=True)
    if len(sortedScores) >= 2:
        gap = sortedScores[0][0] - sortedScores[1][0]
        gapRatio = gap / max(sortedScores[0][0], 1)
        confidence = min(1.0, confidence * (0.6 + 0.4 * gapRatio))

    if hitCount <= 1:
        confidence *= 0.5

    return bestKey, round(confidence, 3), hitKws


def invalidateCache() -> None:
    """taxonomy lru_cache를 무효화한다.

    Notes
    -----
    taxonomy.json 수정 후 호출하면 다음 loadTaxonomy() 때 재파싱.
    """
    loadTaxonomy.cache_clear()
