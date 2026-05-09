"""Stateless ref ↔ requiredEvidence 검증.

`feedback_no_graph_regression.md` 준수 — workbench/gate.py 의 graph node 어휘 재사용 금지.
순수 함수: refs (recipe 실행 결과의 ref id 목록) 와 requiredEvidence (recipe frontmatter 의 필요
ref kind 목록) 를 입력받아 일치 여부 + 누락 종류 반환.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

# 본 매핑은 ref id prefix → 권장 ref kind alias 변환. workbench/gate.py 의 _KNOWN_KIND_ALIASES
# 와 의미상 같지만 graph 모듈 의존을 끊기 위해 본 모듈 안에 자체 정의.
# 운영 SSOT: src/dartlab/ai/contracts.py 의 Ref.kind 와 일치해야 한다 (kind 가 명시되면 prefix
# 추론 불필요 — prefix 추론은 id-string 만 받는 fallback 경로).
_REF_PREFIX_TO_KIND: dict[str, str] = {
    "skill:": "skillRef",
    "table:": "tableRef",
    "value:": "valueRef",
    "date:": "dateRef",
    "execution:": "executionRef",
    "verify:": "verifyRef",
    "source:": "sourceRef",
    "visual:": "visualRef",
    "exec:": "executionRef",
    "url:": "sourceRef",
}


@dataclass(frozen=True)
class RefValidationResult:
    """validateRefs 반환.

    Parameters
    ----------
    ok : bool
        모든 requiredEvidence kind 가 refs 안에 등장했는지.
    present : list[str]
        실제 등장한 evidence kind 목록 (정렬됨).
    missing : list[str]
        requiredEvidence 중 등장하지 않은 kind.
    extras : list[str]
        refs 에 있지만 requiredEvidence 에는 없는 kind (정보용).
    """

    ok: bool
    present: list[str] = field(default_factory=list)
    missing: list[str] = field(default_factory=list)
    extras: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _refKindOf(ref: Any) -> str | None:
    """단일 ref 의 kind 를 추출. dict / Ref dataclass / id-string 입력 허용."""
    if ref is None:
        return None
    if isinstance(ref, dict):
        kind = ref.get("kind")
        if isinstance(kind, str) and kind.strip():
            return kind.strip()
        ref_id = ref.get("id")
        if isinstance(ref_id, str):
            return _kindFromId(ref_id)
        return None
    kind_attr = getattr(ref, "kind", None)
    if isinstance(kind_attr, str) and kind_attr.strip():
        return kind_attr.strip()
    id_attr = getattr(ref, "id", None)
    if isinstance(id_attr, str):
        return _kindFromId(id_attr)
    if isinstance(ref, str):
        return _kindFromId(ref)
    return None


def _kindFromId(ref_id: str) -> str | None:
    for prefix, kind in _REF_PREFIX_TO_KIND.items():
        if ref_id.startswith(prefix):
            return kind
    return None


def validateRefs(
    refs: list[Any] | tuple[Any, ...] | None,
    requiredEvidence: list[str] | tuple[str, ...] | None,
) -> RefValidationResult:
    """recipe `requiredEvidence` 가 실제 refs 에 모두 등장했는지 검증.

    Parameters
    ----------
    refs : list[Any]
        recipe 실행이 emit 한 ref 목록. dict / Ref dataclass / id-string 혼합 허용.
    requiredEvidence : list[str]
        recipe frontmatter 의 `requiredEvidence` (skillRef/tableRef/valueRef/dateRef 등).

    Returns
    -------
    RefValidationResult
        ok / present / missing / extras 분리.

    Notes
    -----
    workbench gate.py 의 5-pass GATE 와 의미는 같지만 phase chain 어휘를 끊었다. 본 함수는
    ValidateRecipe 가 한 번 호출하는 stateless 검증 — recipe 실행 결과의 ref 목록 ↔ 요구
    종류 일치 검사만.
    """
    needed: set[str] = {token for token in (requiredEvidence or []) if token}
    seen: set[str] = set()
    for ref in refs or []:
        kind = _refKindOf(ref)
        if kind:
            seen.add(kind)
    missing = sorted(needed - seen)
    present = sorted(needed & seen)
    extras = sorted(seen - needed)
    return RefValidationResult(ok=not missing, present=present, missing=missing, extras=extras)
