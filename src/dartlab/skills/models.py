"""SkillSpec models for DartLab execution skills.

SkillSpec is a public execution document for people and AI.  Public call
patterns, behavior, and representative return contracts belong in skills so a
reader can run the skill directly.  Generated capabilities remain the API
source used to validate capabilityRefs and keep skills synchronized with code.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal

SkillKind = Literal["generated", "curated", "user", "recipe"]
SkillScope = Literal["builtin", "project", "user"]
# recipe 6-stage lifecycle (drafted → unverified → tested → verified → curated → deprecated) 와
# 비-recipe 의 기존 ladder (unverified → observed → auditP → official → deprecated) 를 합집합으로 보존.
# 변환·승격은 scripts/dev/recipe_promote.py CLI 가 단독 권한.
SkillStatus = Literal[
    "drafted",
    "unverified",
    "observed",
    "tested",
    "verified",
    "auditP",
    "official",
    "curated",
    "deprecated",
]
SkillCategory = Literal[
    "start",
    "runtime",
    "operation",
    "engines",
    "screens",
    "finance",
    "visuals",
    "basic",
    "user",
    "capability",
]


@dataclass(frozen=True)
class SkillSpec:
    """실행 스킬 명세 — 사람과 AI가 함께 쓰는 공개 skill 단위.

    Description
    -----------
    DartLab AI, MCP, story, UI, audit, GitHub Pages 가 함께 읽는 공개 실행
    문서다. 공개 호출 방식, 호출 동작, 대표 반환 형태, 필요한
    capability/tool/knowledge 와 evidence 계약을 설명한다.

    Parameters
    ----------
    id : str
        skill 식별자.
    title : str
        사용자에게 보일 제목.
    kind : SkillKind
        generated/curated/user 구분.
    scope : SkillScope
        builtin/project/user 범위.
    status : SkillStatus
        검증 상태.
    category : SkillCategory
        start/runtime/engines/screens/finance/visuals/basic/user/capability 검색 계층.

    Returns
    -------
    SkillSpec
        id : str — skill 식별자
        category : str — 검색/문서 렌더링 카테고리
        capabilityRefs : list[str] — 참조 capability id 목록
        runtimeCompatibility : dict — server/localPython/pyodide/webAi/mcp 지원 상태
        requiredEvidence : list[str] — 필요한 evidence 이름 목록

    Raises
    ------
    없음
        검증은 registry lint 에서 수행한다.

    Examples
    --------
    >>> SkillSpec(id="x", title="X", purpose="...", whenToUse=["x"]).id
    'x'

    Notes
    -----
    기능 개선, API 변경, 반환 형태 변경, 운영 방식 변경이 있으면 관련
    SkillSpec 을 함께 갱신한다. 스킬과 공개 API가 충돌하면 스킬 갱신 누락이다.

    Guide
    -----
    새 분석법은 먼저 user/curated skill 로 실험하고, 반복 audit P 이후 엔진
    axis/function 으로 승격한다.

    See Also
    --------
    dartlab.skills.registry : SkillSpec 로딩과 검색.
    """

    id: str
    title: str
    purpose: str
    whenToUse: list[str] = field(default_factory=list)
    kind: SkillKind = "curated"
    scope: SkillScope = "builtin"
    status: SkillStatus = "unverified"
    category: SkillCategory = "finance"
    inputs: list[str] = field(default_factory=list)
    outputs: list[str] = field(default_factory=list)
    requiredInputs: list[str] = field(default_factory=list)
    capabilityRefs: list[str] = field(default_factory=list)
    datasetRefs: list[str] = field(default_factory=list)
    toolRefs: list[str] = field(default_factory=list)
    knowledgeRefs: list[str] = field(default_factory=list)
    sourceRefs: list[str] = field(default_factory=list)
    visualRefs: list[str] = field(default_factory=list)
    linkedSkills: list[str] = field(default_factory=list)
    requires: list[str] = field(default_factory=list)
    alternatives: list[str] = field(default_factory=list)
    succeededBy: list[str] = field(default_factory=list)
    deprecatedBy: list[str] = field(default_factory=list)
    recipeSteps: list[dict[str, Any]] = field(default_factory=list)
    procedure: list[str] = field(default_factory=list)
    requiredEvidence: list[str] = field(default_factory=list)
    expectedOutputs: list[str] = field(default_factory=list)
    visualGuidance: list[str] = field(default_factory=list)
    runtimeCompatibility: dict[str, Any] = field(default_factory=dict)
    pyodide: dict[str, Any] = field(default_factory=dict)
    docs: dict[str, Any] = field(default_factory=dict)
    quality: dict[str, Any] = field(default_factory=dict)
    failureModes: list[str] = field(default_factory=list)
    forbidden: list[str] = field(default_factory=list)
    examples: list[str] = field(default_factory=list)
    source: dict[str, Any] = field(default_factory=dict)
    verifiedBy: list[str] = field(default_factory=list)
    lastUpdated: str | None = None
    # ── recipe 메타데이터 (kind == "recipe" 일 때만 의미) ──
    gap: dict[str, Any] = field(default_factory=dict)
    testUniverse: dict[str, Any] = field(default_factory=dict)
    falsifier: dict[str, Any] = field(default_factory=dict)
    expectedNovelty: list[str] = field(default_factory=list)
    validationRuns: list[dict[str, Any]] = field(default_factory=list)
    validatedAt: str | None = None
    storyboardKey: str | None = None

    def toDict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class SkillMatch:
    """검색 결과 — query 와 SkillSpec 의 매칭 점수."""

    skill: SkillSpec
    score: float
    reasons: list[str] = field(default_factory=list)

    def toDict(self) -> dict[str, Any]:
        data = asdict(self)
        data["skill"] = self.skill.toDict()
        return data


@dataclass(frozen=True)
class EvidenceCheckResult:
    """skill evidence 충족 여부."""

    ok: bool
    skillId: str
    present: list[str] = field(default_factory=list)
    missing: list[str] = field(default_factory=list)

    def toDict(self) -> dict[str, Any]:
        return asdict(self)
