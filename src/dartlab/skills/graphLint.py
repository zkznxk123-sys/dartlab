"""Skill Graph lint — 257 sub-spec 의 연결 정합성 검증.

trrack 3 lint 본체. registry.py::lintSkill 가 본 모듈 함수들을 호출하지만, lint
정책 (warn vs error) 은 phase 별 정책 표를 따른다.

Description
-----------
- phase 1 (현재): warn-only — logger.warning 출력, raise 없음. 257 spec 의
  current state 를 가시화하는 단계.
- phase 2 (장래): 신규/수정 spec 에 한해 raise — validateSkills.py CI 차단.
- phase 3 (장래): listSkills 전수 raise — 모든 spec 정합 후 활성.

본 모듈은 phase 1 기본. phase 2/3 는 호출자 (registry.lintSkill 또는
validateSkills.py) 가 raise 결정.
"""

from __future__ import annotations

import logging
import re

from .graph import SkillGraph
from .models import SkillSpec

logger = logging.getLogger(__name__)

_REF_FIELDS = ("knowledgeRefs", "sourceRefs", "toolRefs", "datasetRefs")
# skill id namespace 5 카테고리 — 이 prefix 결로 시작하는 ref 만 skill id 결로 검증.
# `dart.scan` · `krx.prices` · `market.flow` · `CHANGELOG.md` 같은 dataset/tool/파일 결은 namespace 다름.
_SKILL_ID_PREFIXES = ("engines.", "operation.", "start.", "runtime.", "recipes.")
_QUOTE_PATTERN = re.compile(r'^\s*-\s*[\'"][a-z][a-zA-Z0-9.]+[\'"]\s*$', re.MULTILINE)


def validateRefExistence(spec: SkillSpec, allIds: frozenset[str]) -> list[str]:
    """spec 의 4 참조 필드 (knowledgeRefs · sourceRefs · toolRefs · datasetRefs) id 존재성 검사.

    Description
    -----------
    sourceRefs 는 `dartlab://skills/{id}` scheme 안 path 만 검증. 그 외는
    skip. linkedSkills 는 buildSkillGraph 가 edge 만들 때 자체 skip 하므로
    별도 검증 불요.

    Parameters
    ----------
    spec : SkillSpec
    allIds : frozenset[str]
        listSkills() 모든 id.

    Returns
    -------
    list[str]
        깨진 ref 메시지 리스트. 빈 리스트면 OK.

    Examples
    --------
    >>> from dartlab.skills.registry import listSkills
    >>> specs = listSkills()
    >>> ids = frozenset(s.id for s in specs)
    >>> validateRefExistence(specs[0], ids)
    []

    Notes
    -----
    phase 1 은 warn-only — 본 함수는 *메시지* 만 반환, raise 없음.

    Guide
    -----
    호출자가 phase 별 정책 적용.

    See Also
    --------
    dartlab.skills.graph.buildSkillGraph : edge 빌드 시 깨진 ref 자동 skip.
    """
    broken: list[str] = []
    for field_name in _REF_FIELDS:
        values = getattr(spec, field_name, None) or []
        if not isinstance(values, list):
            continue
        for raw in values:
            if not isinstance(raw, str):
                continue
            ref = raw.strip().strip('"').strip("'")
            if field_name == "sourceRefs":
                if ref.startswith("dartlab://skills/"):
                    target = ref.removeprefix("dartlab://skills/")
                    if target and target not in allIds:
                        broken.append(f"{spec.id}.sourceRefs -> {target} (missing)")
                continue
            if not ref or "." not in ref or ref.startswith("dartlab.") or ref.startswith("http"):
                continue
            # toolRefs · datasetRefs 는 namespace 다름 (tool id · dataset id). skill id prefix 결로
            # 시작하는 ref 만 검증 — 그 외 (`dart.scan` · `krx.prices` · `CHANGELOG.md`) 는 skip.
            if not ref.startswith(_SKILL_ID_PREFIXES):
                continue
            if ref not in allIds:
                broken.append(f"{spec.id}.{field_name} -> {ref} (missing)")
    return broken


def validateRefNoQuotes(spec: SkillSpec, rawText: str) -> list[str]:
    """frontmatter raw text 안 list ref 항목의 둘레 따옴표 detect.

    Description
    -----------
    YAML 표준상 따옴표는 valid 하지만, 본 프로젝트는 ref id 둘레 따옴표 *없는*
    스타일을 새 spec 의 표준으로 한다. 기존 113 spec 의 따옴표는 *유지* —
    회귀 차단 lint 가 *새 spec* 에만 적용.

    Parameters
    ----------
    spec : SkillSpec
    rawText : str
        frontmatter 영역 본문 (---- 사이).

    Returns
    -------
    list[str]
        따옴표 발견 위치 메시지.

    Examples
    --------
    >>> validateRefNoQuotes(spec, '- "engines.x"\\n')
    ['follows ref id surrounded by quotes (use unquoted style)']

    Notes
    -----
    phase 2 부터 활성 — 새 spec 만 차단. 기존 113 은 운영자 수동 정리.

    Guide
    -----
    호출자가 phase 별 정책 결정. 본 함수는 *메시지* 만 반환.

    See Also
    --------
    validateRefExistence : 깨진 ref 검출.
    """
    findings: list[str] = []
    for match in _QUOTE_PATTERN.finditer(rawText):
        findings.append(f"{spec.id}: quoted ref id found: {match.group(0).strip()}")
    return findings


def reportOrphans(graph: SkillGraph) -> list[str]:
    """orphan 노드 (in-degree 0 + entry 아님) warn-only 메시지.

    Description
    -----------
    의도적 leaf (frontmatter `isLeafNode: true`) 는 *제외*. 그 외 orphan 만
    warn. 운영자가 진짜 의도적 leaf 면 frontmatter 추가, 의도치 않은
    분류 실수면 fix.

    Parameters
    ----------
    graph : SkillGraph
        buildSkillGraph 결과.

    Returns
    -------
    list[str]
        orphan id 리스트 (warn-only).

    Examples
    --------
    >>> from dartlab.skills.registry import listSkills
    >>> from dartlab.skills.graph import buildSkillGraph
    >>> g = buildSkillGraph(listSkills())
    >>> orphans = reportOrphans(g)

    Notes
    -----
    isLeafNode 플래그가 노드 빌드 시 isLeaf 에 흡수돼 별도 plate 검사 없음 —
    isOrphan True 인 것만 반환.

    Guide
    -----
    호출자 정책: phase 1 warn-only · phase 2 신규 차단 · phase 3 전수 차단.

    See Also
    --------
    dartlab.skills.graph.SkillNode.isOrphan : 노드 플래그.
    """
    return [node.id for node in graph.nodes if node.isOrphan]


def detectThreePlusCycles(graph: SkillGraph) -> list[tuple[str, ...]]:
    """3+ 노드 SCC 만 반환 — 2 노드 양방향 (A↔B) 은 제외.

    Description
    -----------
    buildSkillGraph 가 이미 3+ 만 detectCycles 로 검출 — 본 함수는 의미 강조
    용 thin wrapper.

    Parameters
    ----------
    graph : SkillGraph

    Returns
    -------
    list[tuple[str, ...]]
        3+ 노드 SCC 리스트.

    Examples
    --------
    >>> cycles = detectThreePlusCycles(g)

    Notes
    -----
    A↔B 양방향은 dartlab parent-child / cross-engine 정상 패턴.

    Guide
    -----
    3+ SCC 1 개라도 발견 시 운영자 검토 권장.

    See Also
    --------
    dartlab.skills.graph.detectCycles : Tarjan SCC.
    """
    return list(graph.cycles)


def validateBidirectional(spec: SkillSpec, allSpecs: list[SkillSpec]) -> list[str]:
    """spec.successors[s] 에 대해 s.predecessors 에 spec.id 가 있는지 검증.

    Description
    -----------
    양방향 일관성. successors/predecessors 새 필드용 정합성. linkedSkills 는
    recipe step 결이라 별도 검증 없음.

    Parameters
    ----------
    spec : SkillSpec
    allSpecs : list[SkillSpec]

    Returns
    -------
    list[str]
        비대칭 메시지.

    Examples
    --------
    >>> validateBidirectional(s, all_specs)
    []

    Notes
    -----
    신규 필드라 257 기존 spec 은 모두 빈 successors — phase 1 에서 모두
    OK. 새 spec 작성 후부터 의미.

    Guide
    -----
    phase 2 부터 raise — 사람이 successors 명시하면 자동 predecessors 도출
    또는 차단.

    See Also
    --------
    validateRefExistence : 깨진 ref.
    """
    by_id = {s.id: s for s in allSpecs}
    issues: list[str] = []
    for raw in spec.successors or []:
        if not isinstance(raw, str):
            continue
        target_id = raw.strip().strip('"').strip("'")
        target = by_id.get(target_id)
        if target is None:
            continue
        if spec.id not in (target.predecessors or []):
            issues.append(f"{spec.id} -> {target_id}: missing predecessor back-edge")
    return issues


def validateReachability(graph: SkillGraph, *, maxHops: int = 6) -> list[str]:
    """entry 에서 maxHops 안 도달 못한 노드 리스트.

    Description
    -----------
    sub-spec 이 진입 path 가 없으면 외부 LLM/사람이 발견 못함. 의도적 leaf
    (`isLeafNode: true`) 는 별도 정상 — 본 함수는 단순 도달 불가 노드 반환.

    Parameters
    ----------
    graph : SkillGraph
    maxHops : int, optional
        기본 6.

    Returns
    -------
    list[str]
        unreachable id 리스트.

    Examples
    --------
    >>> validateReachability(g)

    Notes
    -----
    현재 173 unreachable — 67% 가 진입 path 6 hop 안에 없음. 운영자
    successor/predecessor 마이그레이션으로 점진 해소.

    Guide
    -----
    phase 1 warn-only — 본 함수는 데이터만 반환. 정책은 호출자.

    See Also
    --------
    dartlab.skills.graph.reachableFromEntries : BFS.
    """
    return list(graph.unreachableFromEntry)


__all__ = [
    "validateRefExistence",
    "validateRefNoQuotes",
    "reportOrphans",
    "detectThreePlusCycles",
    "validateBidirectional",
    "validateReachability",
]
