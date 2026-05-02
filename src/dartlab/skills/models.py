"""SkillSpec models for DartLab analysis procedures.

SkillSpec is a shared procedure description, not an execution runner.  API
parameters and return schemas stay in public docstrings and generated
capabilities; skills only reference those capabilities.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal

SkillKind = Literal["generated", "curated", "user"]
SkillScope = Literal["builtin", "project", "user"]
SkillStatus = Literal["unverified", "observed", "auditP", "official", "deprecated"]
SkillCategory = Literal[
    "start",
    "runtime",
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
    """분석 절차 명세 — capability 를 조합하는 공유 skill 단위.

    Description
    -----------
    DartLab AI, MCP, story, UI, audit, GitHub Pages 가 함께 읽는 분석 절차
    명세다. 이 객체는 실행 코드를 포함하지 않고, 필요한
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
    API signature/returns 중복은 금지한다. capabilityRefs 로 연결한다.

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
    visualRefs: list[str] = field(default_factory=list)
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

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class SkillMatch:
    """검색 결과 — query 와 SkillSpec 의 매칭 점수."""

    skill: SkillSpec
    score: float
    reasons: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["skill"] = self.skill.to_dict()
        return data


@dataclass(frozen=True)
class EvidenceCheckResult:
    """skill evidence 충족 여부."""

    ok: bool
    skillId: str
    present: list[str] = field(default_factory=list)
    missing: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
