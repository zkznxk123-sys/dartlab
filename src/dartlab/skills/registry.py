"""Skill registry and linting for shared DartLab analysis skills."""

from __future__ import annotations

import json
import builtins
from pathlib import Path
from typing import Any

from .models import EvidenceCheckResult, SkillMatch, SkillSpec

_FORBIDDEN_DUPLICATE_KEYS = {"parameters", "params", "returns", "signature", "outputShape", "schema"}
_FORBIDDEN_TEMPLATE_MARKERS = ("final answer", "최종 답변:", "답변 템플릿", "{{answer", "{answer}")
_MAX_PROCEDURE_ITEM_CHARS = 1200
_BASIC_ENGINE_ORDER = (
    "company",
    "gather",
    "scan",
    "analysis",
    "quant",
    "macro",
    "story",
    "credit",
    "industry",
    "viz",
)
_BASIC_ENGINE_CAPABILITY_SELECTORS: dict[str, dict[str, Any]] = {
    "company": {"exact": ("Company",), "prefix": ("Company.",), "title": "Company 기업 분석 엔진"},
    "gather": {"exact": ("gather",), "prefix": ("gather.",), "title": "gather 데이터 수집 엔진"},
    "scan": {"exact": ("scan",), "prefix": ("scan.",), "title": "scan 횡단 분석 엔진"},
    "analysis": {"exact": ("analysis", "Company.analysis"), "prefix": ("analysis.",), "title": "analysis 재무 분석 엔진"},
    "quant": {"exact": ("quant", "Company.quant"), "prefix": ("quant.",), "title": "quant 가격·팩터 분석 엔진"},
    "macro": {"exact": ("macro", "Company.macro"), "prefix": ("macro.",), "title": "macro 거시 분석 엔진"},
    "story": {"exact": ("Story", "Company.story"), "prefix": ("Story.", "Company.story"), "title": "story 보고서 조합 엔진"},
    "credit": {"exact": ("credit", "Company.credit"), "prefix": ("credit.",), "title": "credit 신용 분석 엔진"},
    "industry": {"exact": ("industry", "Company.industry"), "prefix": ("industry.", "scan.industry"), "title": "industry 산업 분석 엔진"},
    "viz": {"exact": ("ChartResult",), "prefix": ("chart.", "viz.", "visual."), "title": "viz 시각 설명 엔진"},
}


def listSkills(*, includeUser: bool = True) -> list[SkillSpec]:
    """Skill 목록 — builtin 과 user skill 을 함께 반환.

    Description
    -----------
    DartLab 공용 분석 절차 명세를 로드한다. basic 엔진 skill 과 capability
    view 는 generated output 이고, builtin 수기 skill 은 `specs/domain/`만
    읽는다. user skill 은 project-local `.dartlab/skills`에서 읽는다.

    Parameters
    ----------
    includeUser : bool, optional
        True 면 현재 workspace 의 user skill 도 포함한다.

    Returns
    -------
    list[SkillSpec]
        id : str — skill 식별자
        kind : str — generated/curated/user
        scope : str — builtin/project/user
        status : str — 검증 상태

    Raises
    ------
    ValueError
        skill spec lint 실패.

    Examples
    --------
    >>> any(s.id == "krxIndexStrengthReview" for s in listSkills())
    True

    Notes
    -----
    Skill 은 실행 코드가 아니라 절차 명세다.

    Guide
    -----
    사용자 확장은 `.dartlab/skills/*.yaml`에 두되 API details 를 중복하지 않는다.

    See Also
    --------
    searchSkills : 질의 기반 skill 검색.
    """

    specs = [
        *_generated_basic_engine_skill_specs(),
        *_generated_capability_skill_specs(),
        *[_load_spec(path, default_scope="builtin") for path in _builtin_spec_paths()],
    ]
    if includeUser:
        specs.extend(_load_spec(path, default_scope="user", force_user=True) for path in _user_spec_paths())
    _validate_unique_ids(specs)
    for spec in specs:
        lintSkill(spec)
    return sorted(specs, key=lambda item: item.id)


def getSkill(skillId: str, *, includeUser: bool = True) -> SkillSpec:
    """id 로 SkillSpec 조회."""

    for spec in listSkills(includeUser=includeUser):
        if spec.id == skillId:
            return spec
    raise KeyError(f"unknown DartLab skill: {skillId}")


def searchSkills(query: str, *, limit: int = 8, includeUser: bool = True) -> list[SkillMatch]:
    """Skill 검색 — 분석 목적과 capability ref 를 기준으로 매칭."""

    terms = _terms(query)
    matches: list[SkillMatch] = []
    for spec in listSkills(includeUser=includeUser):
        score, reasons = _score(spec, terms)
        if score > 0 or not terms:
            matches.append(SkillMatch(skill=spec, score=score, reasons=reasons))
    return sorted(matches, key=lambda item: (item.score, item.skill.status == "official", item.skill.id), reverse=True)[:limit]


def describeSkill(skillId: str, *, includeUser: bool = True) -> dict[str, Any]:
    """Skill 설명 dict 반환."""

    return getSkill(skillId, includeUser=includeUser).to_dict()


def checkEvidence(skillId: str, refs: list[dict[str, Any]] | list[Any], *, includeUser: bool = True) -> EvidenceCheckResult:
    """Skill evidence 충족도 확인.

    Notes
    -----
    이 검사는 근거 이름의 존재 여부를 보는 경량 점검이다. 숫자·날짜 claim 의
    실제 값 대조는 Ask Workbench verifier 가 담당한다.
    """

    spec = getSkill(skillId, includeUser=includeUser)
    present_names = _evidence_names(refs)
    required = set(spec.requiredEvidence)
    present = sorted(required & present_names)
    missing = sorted(required - present_names)
    return EvidenceCheckResult(ok=not missing, skillId=spec.id, present=present, missing=missing)


def lintSkill(spec: SkillSpec) -> None:
    """SkillSpec 정합성 검사."""

    if not spec.id or not spec.title or not spec.purpose:
        raise ValueError("skill id/title/purpose are required")
    if _contains_forbidden_api_schema(spec.source):
        raise ValueError(f"skill {spec.id} duplicates API schema in source")
    payload = spec.to_dict()
    for key in _FORBIDDEN_DUPLICATE_KEYS:
        if key in payload and payload.get(key):
            raise ValueError(f"skill {spec.id} duplicates API field: {key}")
    for item in [*spec.procedure, *spec.examples]:
        if len(item) > _MAX_PROCEDURE_ITEM_CHARS:
            raise ValueError(f"skill {spec.id} contains an oversized procedure/example item")
        lowered = item.lower()
        if any(marker in lowered for marker in _FORBIDDEN_TEMPLATE_MARKERS):
            raise ValueError(f"skill {spec.id} contains a final-answer template marker")
    _validate_runtime_compatibility(spec)
    _validate_capability_refs(spec)


def _builtin_spec_paths() -> list[Path]:
    root = Path(__file__).resolve().parent / "specs"
    domain = root / "domain"
    if not domain.exists():
        return []
    return sorted([*domain.rglob("*.yaml"), *domain.rglob("*.yml"), *domain.rglob("*.json")])


def _user_spec_paths() -> list[Path]:
    root = _repo_root() / ".dartlab" / "skills"
    if not root.exists():
        return []
    return sorted([*root.glob("*.yaml"), *root.glob("*.yml"), *root.glob("*.json")])


def _load_spec(path: Path, *, default_scope: str, force_user: bool = False) -> SkillSpec:
    data = _read_mapping(path)
    if force_user:
        data["kind"] = "user"
        data["scope"] = "user"
        data["category"] = "user"
        data.setdefault("status", "unverified")
    else:
        data.setdefault("kind", "curated")
        data.setdefault("scope", default_scope)
        data.setdefault("category", "domain")
    data.setdefault("source", {})
    data["source"].setdefault("path", str(path))
    return SkillSpec(**_normalize_spec_data(data))


def _read_mapping(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() == ".json":
        data = json.loads(text)
    else:
        try:
            import yaml
        except ImportError:
            data = _read_simple_yaml(text)
        else:
            data = yaml.safe_load(text)
    if not isinstance(data, dict):
        raise ValueError(f"skill spec must be a mapping: {path}")
    return data


def _normalize_spec_data(data: dict[str, Any]) -> dict[str, Any]:
    list_fields = {
        "whenToUse",
        "requiredInputs",
        "capabilityRefs",
        "toolRefs",
        "knowledgeRefs",
        "procedure",
        "requiredEvidence",
        "expectedOutputs",
        "visualGuidance",
        "failureModes",
        "forbidden",
        "examples",
        "verifiedBy",
    }
    for field in list_fields:
        value = data.get(field)
        if value is None:
            data[field] = []
        elif isinstance(value, str):
            data[field] = [value]
        else:
            data[field] = builtins.list(value)
    return data


def _validate_unique_ids(specs: list[SkillSpec]) -> None:
    seen: set[str] = set()
    for spec in specs:
        if spec.id in seen:
            raise ValueError(f"duplicate DartLab skill id: {spec.id}")
        seen.add(spec.id)


def _validate_capability_refs(spec: SkillSpec) -> None:
    if not spec.capabilityRefs:
        return
    known = _known_capabilities()
    missing = [ref for ref in spec.capabilityRefs if ref not in known]
    if missing:
        raise ValueError(f"skill {spec.id} references unknown capabilities: {', '.join(missing)}")


def _generated_basic_engine_skill_specs() -> list[SkillSpec]:
    try:
        from dartlab.core._generated import CAPABILITIES
    except Exception:
        return []

    specs: list[SkillSpec] = []
    for engine in _BASIC_ENGINE_ORDER:
        selector = _BASIC_ENGINE_CAPABILITY_SELECTORS[engine]
        capability_refs = _engine_capability_refs(CAPABILITIES, selector)
        if not capability_refs:
            continue
        snippets = [_capability_snippet(CAPABILITIES[ref]) for ref in capability_refs if isinstance(CAPABILITIES.get(ref), dict)]
        evidence = _aggregate_capability_list(CAPABILITIES, capability_refs, "requiredEvidence", limit=8)
        failure_modes = _aggregate_capability_list(CAPABILITIES, capability_refs, "failureModes", limit=8)
        examples = _aggregate_examples(CAPABILITIES, capability_refs, limit=5)
        specs.append(
            SkillSpec(
                id=f"basic.{engine}",
                title=str(selector["title"]),
                kind="generated",
                scope="builtin",
                status="observed",
                category="basic",
                purpose=f"DartLab `{engine}` 엔진의 역할과 capability 묶음을 찾기 위한 generated basic engine skill.",
                whenToUse=[item for item in snippets[:8] if item],
                capabilityRefs=capability_refs,
                toolRefs=[],
                procedure=[
                    "이 skill은 엔진 능력 지도다. API 상세는 capabilityRefs의 docstring/generated capability에서 확인한다.",
                    "필요 입력, 반환 형태, 단위, 실제 반환 키를 이 skill에 중복하지 않는다.",
                    "분석 중 생성한 숫자·날짜·표·한계는 ref로 남겨 최종 답변 검산에 연결한다.",
                ],
                requiredEvidence=evidence,
                expectedOutputs=["engine capability map", "capability-backed evidence refs"],
                failureModes=failure_modes,
                forbidden=[
                    "API parameters/returns/unit/actual return keys를 SkillSpec에 중복하지 않는다.",
                    "workbench tool 사용법을 basic engine skill에 넣지 않는다.",
                ],
                examples=examples,
                source={"type": "generated_basic_engine", "engine": engine, "capabilityRefs": capability_refs},
            )
        )
    return specs


def _generated_capability_skill_specs() -> list[SkillSpec]:
    try:
        from dartlab.core._generated import CAPABILITIES
    except Exception:
        return []

    specs: list[SkillSpec] = []
    for key, value in CAPABILITIES.items():
        if not isinstance(value, dict):
            continue
        summary = str(value.get("summary") or key)
        guide = str(value.get("guide") or value.get("whenToUse") or "")
        examples = value.get("example")
        if isinstance(examples, str):
            example_items = [examples]
        elif isinstance(examples, list):
            example_items = [str(item) for item in examples[:3]]
        else:
            example_items = []
        specs.append(
            SkillSpec(
                id=f"capability:{key}",
                title=f"{key} capability view",
                kind="generated",
                scope="builtin",
                status="observed",
                category="capability",
                purpose=f"공개 capability `{key}`를 찾고 실행에 연결하기 위한 generated skill view.",
                whenToUse=[summary, _short_text(guide)] if guide else [summary],
                capabilityRefs=[str(key)],
                toolRefs=[],
                procedure=[
                    "capability ref의 공개 docstring/generated capability를 확인한다.",
                    "필요 입력과 반환 형태는 SkillSpec이 아니라 capability ref에서 읽는다.",
                    "실제 계산이나 조회 결과는 작업대 실행 결과 ref로 남긴다.",
                ],
                requiredEvidence=["sourceRef"],
                expectedOutputs=["capability-backed execution or limitation"],
                runtimeCompatibility=_generated_runtime_compatibility(str(key)),
                forbidden=["API parameters/returns를 SkillSpec에 중복하지 않는다."],
                examples=example_items,
                source={"type": "generated_capability_view", "capabilityRef": str(key)},
            )
        )
    return specs


def _engine_capability_refs(capabilities: dict[str, Any], selector: dict[str, Any]) -> list[str]:
    exact = {str(item) for item in selector.get("exact", ())}
    prefixes = tuple(str(item) for item in selector.get("prefix", ()))
    refs: list[str] = []
    for key in capabilities:
        key_str = str(key)
        if key_str in exact or any(key_str.startswith(prefix) for prefix in prefixes):
            refs.append(key_str)
    return sorted(dict.fromkeys(refs), key=lambda item: (item.count("."), item.lower()))


def _capability_snippet(value: dict[str, Any], *, limit: int = 220) -> str:
    summary = _short_text(str(value.get("summary") or ""), limit=limit)
    guide = _short_text(str(value.get("guide") or value.get("whenToUse") or ""), limit=limit)
    if summary and guide:
        return f"{summary} / {guide}"
    return summary or guide


def _aggregate_capability_list(capabilities: dict[str, Any], refs: list[str], field: str, *, limit: int) -> list[str]:
    out: list[str] = []
    for ref in refs:
        value = capabilities.get(ref)
        if not isinstance(value, dict):
            continue
        raw = value.get(field)
        if isinstance(raw, str):
            items = [raw]
        elif isinstance(raw, list):
            items = [str(item) for item in raw]
        else:
            items = []
        for item in items:
            item = item.strip()
            if item and item not in out:
                out.append(item)
            if len(out) >= limit:
                return out
    return out


def _aggregate_examples(capabilities: dict[str, Any], refs: list[str], *, limit: int) -> list[str]:
    out: list[str] = []
    for ref in refs:
        value = capabilities.get(ref)
        if not isinstance(value, dict):
            continue
        raw = value.get("example")
        if isinstance(raw, str):
            items = [raw]
        elif isinstance(raw, list):
            items = [str(item) for item in raw]
        else:
            items = []
        for item in items:
            compact = _short_text(item, limit=300)
            if compact and compact not in out:
                out.append(compact)
            if len(out) >= limit:
                return out
    return out


def _short_text(text: str, *, limit: int = 500) -> str:
    return " ".join(text.split())[:limit]


def _known_capabilities() -> set[str]:
    try:
        from dartlab.core._generated import CAPABILITIES
    except Exception:
        return set()
    return {str(key) for key in CAPABILITIES}


def _validate_runtime_compatibility(spec: SkillSpec) -> None:
    allowed = {"supported", "limited", "unsupported", "unknown"}
    for runtime, value in spec.runtimeCompatibility.items():
        if not isinstance(value, dict):
            raise ValueError(f"skill {spec.id} runtimeCompatibility.{runtime} must be a mapping")
        status = str(value.get("status") or "unknown")
        if status not in allowed:
            raise ValueError(f"skill {spec.id} runtimeCompatibility.{runtime}.status is invalid: {status}")


def _generated_runtime_compatibility(capability_ref: str) -> dict[str, Any]:
    return {
        "server": {"status": "supported"},
        "mcp": {"status": "supported"},
        "pyodide": {
            "status": "unknown",
            "notes": [
                "Generated capability view는 API 사용법만 나타낸다.",
                "Pyodide 가능 여부는 curated/user SkillSpec 또는 ops/pyodide.md를 확인한다.",
            ],
            "capabilityRef": capability_ref,
        },
    }


def _read_simple_yaml(text: str) -> dict[str, Any]:
    lines = text.splitlines()
    parsed, _ = _parse_yaml_block(lines, 0, 0)
    if not isinstance(parsed, dict):
        raise ValueError("skill yaml fallback parser expected a mapping")
    return parsed


def _parse_yaml_block(lines: list[str], start: int, indent: int) -> tuple[Any, int]:
    index = _skip_yaml_blank(lines, start)
    if index >= len(lines):
        return {}, index
    current = lines[index]
    current_indent = len(current) - len(current.lstrip(" "))
    if current_indent < indent:
        return {}, index
    if current.lstrip().startswith("- "):
        return _parse_yaml_list(lines, index, current_indent)
    return _parse_yaml_mapping(lines, index, indent)


def _parse_yaml_mapping(lines: list[str], start: int, indent: int) -> tuple[dict[str, Any], int]:
    out: dict[str, Any] = {}
    index = start
    while index < len(lines):
        index = _skip_yaml_blank(lines, index)
        if index >= len(lines):
            break
        line = lines[index]
        current_indent = len(line) - len(line.lstrip(" "))
        if current_indent < indent:
            break
        if current_indent > indent:
            break
        stripped = line.strip()
        if stripped.startswith("- ") or ":" not in stripped:
            break
        key, raw = stripped.split(":", 1)
        raw = raw.strip()
        if raw == ">":
            value, index = _parse_yaml_folded(lines, index + 1, current_indent + 2)
        elif raw:
            value = _parse_yaml_scalar(raw)
            index += 1
        else:
            value, index = _parse_yaml_block(lines, index + 1, current_indent + 2)
        out[key] = value
    return out, index


def _parse_yaml_list(lines: list[str], start: int, indent: int) -> tuple[list[Any], int]:
    out: list[Any] = []
    index = start
    while index < len(lines):
        index = _skip_yaml_blank(lines, index)
        if index >= len(lines):
            break
        line = lines[index]
        current_indent = len(line) - len(line.lstrip(" "))
        stripped = line.strip()
        if current_indent != indent or not stripped.startswith("- "):
            break
        item = stripped[2:].strip()
        out.append(_parse_yaml_scalar(item))
        index += 1
    return out, index


def _parse_yaml_folded(lines: list[str], start: int, indent: int) -> tuple[str, int]:
    parts: list[str] = []
    index = start
    while index < len(lines):
        line = lines[index]
        if not line.strip():
            index += 1
            continue
        current_indent = len(line) - len(line.lstrip(" "))
        if current_indent < indent:
            break
        parts.append(line.strip())
        index += 1
    return " ".join(parts), index


def _parse_yaml_scalar(raw: str) -> Any:
    if raw == "[]":
        return []
    if raw == "{}":
        return {}
    if (raw.startswith('"') and raw.endswith('"')) or (raw.startswith("'") and raw.endswith("'")):
        return raw[1:-1]
    lowered = raw.lower()
    if lowered == "true":
        return True
    if lowered == "false":
        return False
    if lowered in {"null", "none"}:
        return None
    try:
        return int(raw)
    except ValueError:
        pass
    try:
        return float(raw)
    except ValueError:
        return raw


def _skip_yaml_blank(lines: list[str], start: int) -> int:
    index = start
    while index < len(lines) and (not lines[index].strip() or lines[index].lstrip().startswith("#")):
        index += 1
    return index


def _contains_forbidden_api_schema(value: Any) -> bool:
    if isinstance(value, dict):
        return any(key in _FORBIDDEN_DUPLICATE_KEYS for key in value) or any(_contains_forbidden_api_schema(v) for v in value.values())
    if isinstance(value, list):
        return any(_contains_forbidden_api_schema(item) for item in value)
    return False


def _score(spec: SkillSpec, terms: list[str]) -> tuple[float, list[str]]:
    haystacks = {
        "id": spec.id,
        "title": spec.title,
        "category": spec.category,
        "purpose": spec.purpose,
        "whenToUse": " ".join(spec.whenToUse),
        "capabilityRefs": " ".join(spec.capabilityRefs),
        "knowledgeRefs": " ".join(spec.knowledgeRefs),
        "runtimeCompatibility": json.dumps(spec.runtimeCompatibility, ensure_ascii=False),
    }
    score = 0.0
    reasons: list[str] = []
    for term in terms:
        for name, hay in haystacks.items():
            if term in hay.lower():
                weight = 2.0 if name in {"id", "title", "whenToUse"} else 1.0
                if spec.category == "basic":
                    weight += 0.5
                elif spec.category == "domain":
                    weight += 0.25
                score += weight
                reasons.append(f"{name}:{term}")
    if spec.status in {"auditP", "official"}:
        score += 0.5
    return score, reasons


def _terms(query: str) -> list[str]:
    terms: list[str] = []
    for raw in query.replace("/", " ").replace(".", " ").split():
        term = raw.lower()
        if len(term) < 2:
            continue
        terms.append(term)
        if _contains_hangul(term) and len(term) >= 3:
            terms.extend(term[index : index + 2] for index in range(len(term) - 1))
    return list(dict.fromkeys(terms))


def _contains_hangul(text: str) -> bool:
    return any("\uac00" <= char <= "\ud7a3" for char in text)


def _evidence_names(refs: list[dict[str, Any]] | list[Any]) -> set[str]:
    names: set[str] = set()
    for ref in refs:
        payload = ref.get("payload", ref) if isinstance(ref, dict) else getattr(ref, "payload", {})
        if not isinstance(payload, dict):
            continue
        for key in ("target", "metric", "period", "asOf", "observedDate", "basis", "universe"):
            if payload.get(key) is not None:
                names.add(key)
        if payload.get("rows"):
            names.add("table")
        if payload.get("latest"):
            names.add("latestAsOf")
    return names


def _repo_root() -> Path:
    here = Path.cwd()
    for base in [here, *here.parents]:
        if (base / "pyproject.toml").exists() and (base / "src" / "dartlab").exists():
            return base
    return here


search = searchSkills
get = getSkill
describe = describeSkill
