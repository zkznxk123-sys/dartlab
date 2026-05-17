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

    Capabilities:
        ``data/industry/taxonomy.json`` 을 단 1 회 파싱 (lru_cache) 해 industry ID → IndustryDef
        매핑 반환. 모든 매핑 로직 (stage/role/keyword) 의 단일 진입점.

    lru_cache로 세션 내 1회만 파싱.

    Returns
    -------
    dict[str, IndustryDef]
        산업ID → IndustryDef 매핑. 각 IndustryDef에 ksicCodes, stages 포함.

    Raises:
        FileNotFoundError: taxonomy.json 부재 시.
        json.JSONDecodeError: 파일 손상 시.

    Example:
        >>> from dartlab.industry.taxonomy import loadTaxonomy
        >>> taxo = loadTaxonomy()
        >>> taxo["semiconductor"].name
        '반도체'

    Guide:
        ``invalidateCache()`` 호출 후 다시 호출하면 재파싱. 일반적으로 ``getIndustry`` /
        ``findIndustryByKsic`` / ``matchStageByKeywords`` 가 본 함수를 간접 사용.

    When:
        다른 taxonomy 함수가 1 회 lazy 호출. 외부 직접 호출은 드물다 — ``getIndustry`` 권장.

    How:
        JSON 로드 → industries / stages dict 파싱 → IndustryDef + StageInfo 변환.

    Requires:
        - ``src/dartlab/industry/taxonomy.json`` 파일 존재 + valid JSON

    See Also:
        - ``dartlab.industry.taxonomy.getIndustry`` : 단건 조회
        - ``dartlab.industry.taxonomy.invalidateCache`` : 캐시 무효화

    AIContext:
        AI 가 직접 호출하지 않는다 (산업 정의 메타 룩업은 ``getIndustry`` 권장).
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

    Raises:
        없음 — 미등록 ID 면 None.

    Requires:
        - ``loadTaxonomy()`` 가 성공 (taxonomy.json valid).
    """
    return loadTaxonomy().get(industryId)


def listIndustries() -> list[dict[str, str]]:
    """등록된 전체 산업 목록을 반환한다.

    Returns
    -------
    list[dict[str, str]]
        각 dict에 industryId (str), name (str), stages (int, 공정 수) 포함.

    Raises:
        없음.

    Example:
        >>> from dartlab.industry.taxonomy import listIndustries
        >>> [i["industryId"] for i in listIndustries()][:3]

    Requires:
        - ``loadTaxonomy()`` 가 성공.
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

    Raises:
        없음.

    Requires:
        - ``loadTaxonomy()`` 가 성공.
        - KSIC 매칭 키워드가 taxonomy.json 각 산업의 ``ksicCodes`` 에 등록.
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

    Capabilities:
        대상 산업의 각 stage 키워드 리스트와 입력 텍스트를 case-insensitive 매칭. 매칭 키워드
        수 + 2 위와의 격차 비율로 confidence (0~1) 산출. (best_stage_key, confidence, hits)
        튜플 반환.

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

    Raises:
        없음 — 산업 미등록 / 텍스트 빈 경우 (None, 0.0, []).

    Example:
        >>> from dartlab.industry.taxonomy import matchStageByKeywords
        >>> matchStageByKeywords("semiconductor", "DRAM 메모리 반도체 양산")
        ('memory', 0.85, ['DRAM', '메모리'])

    Guide:
        confidence 가 0.5 미만이면 매칭 약함 — stage4 review 의 ``findLowConfidence`` 가 검수
        대상으로 분류. 단일 hit 는 confidence × 0.5.

    When:
        ``stage2_product.classify`` / ``stage3_docs.enrich`` 가 본문 텍스트 → stage 판별 시.

    How:
        ``getIndustry`` 로 stages 추출 → 각 stage keywords case-insensitive substring 매칭 →
        hit 수 최댓값 산출 → 2 위 격차 비율로 confidence 보정.

    Requires:
        - taxonomy.json 의 각 stage 가 keywords 리스트 명시
        - 입력 텍스트가 한글/영문 mix 가능 (lowercase 비교)

    See Also:
        - ``dartlab.industry.build.stage2_product.classify`` : 본 함수 사용자
        - ``dartlab.industry.build.stage4_review.findLowConfidence`` : 저신뢰 검수

    AIContext:
        AI 가 텍스트를 stage 로 직접 매핑할 때. confidence < 0.5 이면 답변에 "키워드 매칭 부족"
        단서 명시 권장.
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

    Raises:
        없음.

    Example:
        >>> from dartlab.industry.taxonomy import invalidateCache, loadTaxonomy
        >>> invalidateCache()
        >>> taxo = loadTaxonomy()  # 디스크에서 재파싱
    """
    loadTaxonomy.cache_clear()
