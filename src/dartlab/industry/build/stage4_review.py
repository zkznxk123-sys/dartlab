"""4단계: overrides.json 적용 + 저신뢰 종목 리포트.

AI/사람이 확정한 override를 자동 추출 결과에 병합한다.
저신뢰 종목 목록을 생성하여 AI 검수 대상으로 제공한다.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from dartlab.industry.types import IndustryNode

logger = logging.getLogger(__name__)

_DATA_DIR = Path(__file__).resolve().parents[1]
_OVERRIDES_FILE = _DATA_DIR / "overrides.json"


def _loadOverrides() -> dict[str, list[dict]]:
    """overrides.json 로드."""
    if not _OVERRIDES_FILE.exists():
        return {}
    try:
        return json.loads(_OVERRIDES_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        logger.warning("overrides.json 로드 실패")
        return {}


def applyOverrides(nodes: list[IndustryNode]) -> list[IndustryNode]:
    """overrides.json의 확정 매핑을 노드에 적용한다.

    Capabilities:
        ``data/industry/overrides.json`` 의 운영자 확정 매핑을 빌드된 노드에 강제 반영.
        exclude entry → (stockCode, industryId) 제거. 일반 entry → stage/confidence 덮어쓰기
        또는 신규 노드 추가 (source="manual").

    Override entry 포맷:
    - 일반 매핑: ``{"stockCode": "X", "stage": "Y", "confidence": 1.0, ...}``
      → (stockCode, industryId) 노드 stage/confidence 덮어쓰기 또는 신규 추가.
    - 제외 (exclude): ``{"stockCode": "X", "exclude": true}``
      → (stockCode, industryId) 매핑을 노드 리스트에서 제거. stage1-3 의 KSIC/제품/
      docs 분류 오류 (예: SK 지주사가 software 로 잘못 매핑) 를 영구 차단.

    Parameters
    ----------
    nodes : list[IndustryNode]
        3단계까지 처리된 노드 리스트.

    Returns
    -------
    list[IndustryNode]
        override 적용 후 노드 리스트 (제외된 노드는 빠지고 신규 매핑은 추가).

    Raises:
        없음 — overrides.json 손상 시 warning + 입력 그대로 반환.

    Example:
        >>> from dartlab.industry.build.stage4_review import applyOverrides
        >>> nodes = applyOverrides(nodes)  # in-place 보정

    Guide:
        ``buildIndustryMap`` 파이프라인의 마지막 단계. ``addOverride()`` 로 운영자/AI 가 추가한
        보정 매핑이 본 함수에서 강제 반영.

    When:
        manifest 빌드 종료 직전에만 호출. 일반 분석 흐름에서 직접 호출 없다.

    How:
        overrides.json 로드 → exclude 쌍 set 구성 → 노드 필터 → 일반 entry 루프로 in-place
        덮어쓰기 또는 신규 노드 append.

    Requires:
        - ``data/industry/overrides.json`` (없으면 nodes 그대로)
        - 입력 nodes 의 (stockCode, industry) 키 의미 보존

    See Also:
        - ``dartlab.industry.addOverride`` : override 추가 API
        - ``dartlab.industry.build.stage4_review.findLowConfidence`` : 검수 대상

    AIContext:
        AI 가 직접 호출하지 않는다 (배치 stage 4 내부). 답변 시 source="manual" 노드는 "운영자
        확정" 단서 인용 가능.
    """
    overrides = _loadOverrides()
    if not overrides:
        return nodes

    # 1) exclude 적용 — (stockCode, industryId) 쌍 제거.
    excludePairs: set[tuple[str, str]] = set()
    for industryId, ovList in overrides.items():
        for ov in ovList:
            code = ov.get("stockCode", "")
            if code and ov.get("exclude"):
                excludePairs.add((code, industryId))

    if excludePairs:
        nodes = [n for n in nodes if (n.stockCode, n.industry) not in excludePairs]
        for code, ind in sorted(excludePairs):
            logger.info("override exclude: %s × %s 제거", code, ind)

    # 2) 일반 매핑 적용 — stage 덮어쓰기 또는 신규 추가.
    nodeIndex: dict[tuple[str, str], IndustryNode] = {}
    for node in nodes:
        nodeIndex[(node.stockCode, node.industry)] = node

    for industryId, ovList in overrides.items():
        for ov in ovList:
            code = ov.get("stockCode", "")
            stage = ov.get("stage", "")
            if not code or not stage or ov.get("exclude"):
                continue

            key = (code, industryId)
            if key in nodeIndex:
                # 기존 노드 덮어쓰기
                existing = nodeIndex[key]
                existing.stage = stage
                existing.confidence = ov.get("confidence", 1.0)
                existing.source = "manual"
                if ov.get("corpName"):
                    existing.corpName = ov["corpName"]
            else:
                # 새 노드 추가
                newNode = IndustryNode(
                    stockCode=code,
                    corpName=ov.get("corpName", ""),
                    industry=industryId,
                    stage=stage,
                    confidence=ov.get("confidence", 1.0),
                    source="manual",
                )
                nodes.append(newNode)
                nodeIndex[key] = newNode

    return nodes


def findLowConfidence(
    nodes: list[IndustryNode],
    threshold: float = 0.5,
) -> list[IndustryNode]:
    """저신뢰 종목 목록. AI 검수 대상.

    Returns
    -------
    list[IndustryNode]
        confidence < threshold 또는 stage가 빈 노드.

    Raises:
        없음.

    Example:
        >>> from dartlab.industry.build.stage4_review import findLowConfidence
        >>> low = findLowConfidence(nodes, threshold=0.5)
        >>> [n.stockCode for n in low[:3]]

    Requires:
        - 입력 nodes 의 confidence / stage 필드 의미.
    """
    return [n for n in nodes if n.confidence < threshold or not n.stage]
