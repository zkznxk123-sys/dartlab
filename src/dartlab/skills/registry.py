"""Skill registry and linting for shared DartLab execution skills."""

from __future__ import annotations

import builtins
import json
import re
from pathlib import Path
from typing import Any

from .models import EvidenceCheckResult, SkillMatch, SkillSpec

_FORBIDDEN_TEMPLATE_MARKERS = ("final answer", "최종 답변:", "답변 템플릿", "{{answer", "{answer}")
_MAX_PROCEDURE_ITEM_CHARS = 1200
_TICKER_QUERY_RE = re.compile(r"\b[A-Z]{1,5}\b")
_INTENT_BOOSTS_CACHE: tuple[dict[str, Any], ...] | None = None
_INTENT_BOOSTS_SOURCE = "specs/operation/intentBoosts.md"


def _load_intent_boosts() -> tuple[dict[str, Any], ...]:
    """``operation.intentBoosts`` skill frontmatter 에서 의도 boost 규칙을 로드.

    SSOT 는 ``src/dartlab/skills/specs/operation/intentBoosts.md`` 의 frontmatter
    ``intentBoosts[]``. 코드 하드코딩 금지 — 새 규칙은 markdown 에만 추가한다.
    Lazy 캐시 — 첫 호출 시 로드, 이후 동일 tuple 재사용.
    """
    global _INTENT_BOOSTS_CACHE
    if _INTENT_BOOSTS_CACHE is not None:
        return _INTENT_BOOSTS_CACHE
    path = _builtin_specs_root() / "operation" / "intentBoosts.md"
    if not path.exists():
        _INTENT_BOOSTS_CACHE = ()
        return _INTENT_BOOSTS_CACHE
    data = _read_mapping(path)
    raw = data.get("intentBoosts") or []
    out: list[dict[str, Any]] = []
    for entry in raw:
        if not isinstance(entry, dict):
            continue
        skill_ids = tuple(entry.get("skillIds") or ())
        terms = tuple(entry.get("terms") or ())
        boost = entry.get("boost")
        if not skill_ids or not terms or boost is None:
            continue
        try:
            boost_val = float(boost)
        except (TypeError, ValueError):
            continue
        out.append({"skillIds": skill_ids, "terms": terms, "boost": boost_val})
    _INTENT_BOOSTS_CACHE = tuple(out)
    return _INTENT_BOOSTS_CACHE


_MANUAL_SKILL_CATEGORIES = {"start", "runtime", "operation", "engines", "user"}


def listSkills(*, includeUser: bool = True) -> list[SkillSpec]:
    """Skill 목록 — builtin 과 user skill 을 함께 반환.

    Description
    -----------
    DartLab 공용 실행 스킬을 로드한다. builtin skill 은 `dartlab.skills`
    package 안의 `specs/**` Markdown source 만 읽는다. capability/docstring 기반
    자동 skill 은 생성하지 않는다. user skill 은 project-local
    `.dartlab/skills`에서 읽는다.

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
    >>> any(s.id == "engines.scan.krxIndexStrength" for s in listSkills())
    True

    Notes
    -----
    Skill 은 공개 호출 방식, 동작, 대표 반환 형태, 검증 기준을 담는 실행 문서다.

    Guide
    -----
    사용자 확장은 `.dartlab/skills/**/*.md`에 둔다. 공개 API 변경이나 운영 방식 변경이 있으면 관련 skill 도 함께 갱신한다.

    See Also
    --------
    searchSkills : 질의 기반 skill 검색.
    """

    specs = [_load_spec(path, default_scope="builtin") for path in _builtin_spec_paths()]
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
        score, reasons = _score(spec, terms, query=query)
        if score > 0 or not terms:
            matches.append(SkillMatch(skill=spec, score=score, reasons=reasons))
    return sorted(matches, key=lambda item: (item.score, item.skill.status == "official", item.skill.id), reverse=True)[
        :limit
    ]


def describeSkill(skillId: str, *, includeUser: bool = True) -> dict[str, Any]:
    """Skill 설명 dict 반환."""

    return getSkill(skillId, includeUser=includeUser).to_dict()


def checkEvidence(
    skillId: str, refs: list[dict[str, Any]] | list[Any], *, includeUser: bool = True
) -> EvidenceCheckResult:
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
    for item in [*spec.procedure, *spec.examples]:
        if len(item) > _MAX_PROCEDURE_ITEM_CHARS:
            raise ValueError(f"skill {spec.id} contains an oversized procedure/example item")
        lowered = item.lower()
        if any(marker in lowered for marker in _FORBIDDEN_TEMPLATE_MARKERS):
            raise ValueError(f"skill {spec.id} contains a final-answer template marker")
    _validate_runtime_compatibility(spec)
    _validate_status_evidence(spec)
    if spec.kind == "curated" and "pyodide" not in spec.runtimeCompatibility:
        raise ValueError(f"curated skill {spec.id} must declare runtimeCompatibility.pyodide")
    if spec.kind == "recipe":
        _validate_recipe_skill(spec)
    else:
        _validate_execution_skill_contract(spec)
    _validate_capability_refs(spec)


def _validate_recipe_skill(spec: SkillSpec) -> None:
    """recipe kind 검증 — 본문 ## 연계 절차 + linkedSkills 또는 step list 비어있지 않음.

    순환 의존 검사는 listSkills() 재귀 위험으로 본 단계에서 수행하지 않는다 — 별도
    validateRecipes() 후속 작업으로 분리. 여기서는 구조 검증만.
    """
    body = str(spec.source.get("body") or "")
    if "## 연계 절차" not in body:
        raise ValueError(f"recipe skill {spec.id} missing '## 연계 절차' section")
    has_linked = bool(spec.linkedSkills)
    has_body_steps = bool(_steps_from_recipe_body(body))
    if not (has_linked or has_body_steps):
        raise ValueError(f"recipe skill {spec.id} must declare linkedSkills frontmatter or '## 연계 절차' step list")


_RECIPE_STEP_RE = re.compile(r"^\s*(?:\d+\.|-)\s*([\w.]+)(?:\s*[—\-:]\s*(.*))?$")


def _steps_from_recipe_body(body: str) -> list[dict[str, str]]:
    """recipe 본문의 '## 연계 절차' 섹션에서 step list 파싱.

    인식 형식:
        1. engines.macro — 매크로 환경
        - engines.scan — peer 5 종

    반환: [{"skillId": "engines.macro", "note": "매크로 환경"}, ...]
    """
    if not body:
        return []
    text = str(body)
    marker = "## 연계 절차"
    idx = text.find(marker)
    if idx < 0:
        return []
    section = text[idx + len(marker) :]
    next_heading = section.find("\n## ")
    if next_heading >= 0:
        section = section[:next_heading]
    steps: list[dict[str, str]] = []
    for line in section.splitlines():
        match = _RECIPE_STEP_RE.match(line)
        if not match:
            continue
        skill_id = match.group(1).strip()
        note = (match.group(2) or "").strip()
        if "." in skill_id:
            steps.append({"skillId": skill_id, "note": note})
    return steps


def _validate_execution_skill_contract(spec: SkillSpec) -> None:
    if spec.category != "engines":
        return
    body = str(spec.source.get("body") or "")
    required = ("## 공개 호출 방식", "## 호출 동작", "## 대표 반환 형태")
    missing = [heading for heading in required if heading not in body]
    if missing:
        raise ValueError(f"engine skill {spec.id} missing execution sections: {', '.join(missing)}")


def _builtin_spec_paths() -> list[Path]:
    root = _builtin_specs_root()
    if not root.exists():
        return []
    return sorted([*root.rglob("*.md"), *root.rglob("*.yaml"), *root.rglob("*.yml"), *root.rglob("*.json")])


def _user_spec_paths() -> list[Path]:
    root = _repo_root() / ".dartlab" / "skills"
    if not root.exists():
        return []
    return sorted([*root.rglob("*.md"), *root.rglob("*.yaml"), *root.rglob("*.yml"), *root.rglob("*.json")])


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
        data.setdefault("category", _category_from_path(path))
    data.setdefault("source", {})
    data["source"].setdefault("path", str(path))
    return SkillSpec(**_normalize_spec_data(data))


def _read_mapping(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    suffix = path.suffix.lower()
    if suffix == ".md":
        data = _read_markdown_skill(text, path)
    elif suffix == ".json":
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


def _read_markdown_skill(text: str, path: Path) -> dict[str, Any]:
    text = text.lstrip("\ufeff").lstrip()
    if not text.startswith("---"):
        raise ValueError(f"markdown skill requires frontmatter: {path}")
    parts = text.split("---", 2)
    if len(parts) < 3:
        raise ValueError(f"markdown skill frontmatter is not closed: {path}")
    raw_meta = parts[1].strip()
    body = parts[2].strip()
    try:
        import yaml
    except ImportError:
        data = _read_simple_yaml(raw_meta)
    else:
        data = yaml.safe_load(raw_meta)
    if not isinstance(data, dict):
        raise ValueError(f"markdown skill frontmatter must be a mapping: {path}")
    data.setdefault("source", {})
    data["source"]["format"] = "markdown"
    data["source"]["body"] = body
    if body and not data.get("procedure"):
        data["procedure"] = _procedure_from_markdown_body(body)
    if body and not data.get("purpose"):
        data["purpose"] = _short_text(body, limit=220)
    return data


def _procedure_from_markdown_body(body: str) -> list[str]:
    items: list[str] = []
    for raw in body.splitlines():
        line = raw.strip()
        if line.startswith("- "):
            item = line[2:].strip()
            if item:
                items.append(item)
        if len(items) >= 12:
            break
    return items


def _normalize_spec_data(data: dict[str, Any]) -> dict[str, Any]:
    list_fields = {
        "inputs",
        "outputs",
        "whenToUse",
        "requiredInputs",
        "capabilityRefs",
        "datasetRefs",
        "toolRefs",
        "knowledgeRefs",
        "sourceRefs",
        "visualRefs",
        "linkedSkills",
        "requires",
        "alternatives",
        "succeededBy",
        "deprecatedBy",
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
    # recipeSteps 는 list[dict] — frontmatter 에 박혀 있을 수 있다 (운영자 명시).
    rs = data.get("recipeSteps")
    if rs is None:
        data["recipeSteps"] = []
    elif isinstance(rs, list):
        data["recipeSteps"] = [item if isinstance(item, dict) else {"skillId": str(item)} for item in rs]
    else:
        data["recipeSteps"] = []
    for field in ("runtimeCompatibility", "pyodide", "docs", "quality", "source"):
        value = data.get(field)
        if value is None:
            data[field] = {}
        elif not isinstance(value, dict):
            raise ValueError(f"skill field must be a mapping: {field}")
    if data.get("pyodide") and not data["runtimeCompatibility"].get("pyodide"):
        data["runtimeCompatibility"]["pyodide"] = data["pyodide"]
    # SkillSpec field 가 아닌 frontmatter 키는 drop — markdown 에 자유 메타 (intentBoosts 등) 허용.
    import dataclasses as _dc

    spec_fields = {f.name for f in _dc.fields(SkillSpec)}
    for key in list(data.keys()):
        if key not in spec_fields:
            data.pop(key)
    return data


def _category_from_path(path: Path) -> str:
    specs = _builtin_specs_root()
    try:
        relative = path.relative_to(specs)
    except ValueError:
        return "engines"
    first = relative.parts[0] if relative.parts else "engines"
    if first in _MANUAL_SKILL_CATEGORIES:
        return first
    return "engines"


def _builtin_specs_root() -> Path:
    """Builtin SkillSpec root.

    `src/dartlab/skills/specs`가 repo checkout과 wheel에서 모두 같은 공식
    SkillSpec 원본이다.
    """

    return Path(__file__).resolve().parent / "specs"


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


def _short_text(text: str, *, limit: int = 500) -> str:
    return " ".join(text.split())[:limit]


def _known_capabilities() -> set[str]:
    try:
        from dartlab.core.capability._generated import CAPABILITIES
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


def _validate_status_evidence(spec: SkillSpec) -> None:
    if spec.status == "auditP":
        count = int(spec.quality.get("serverAuditPCount") or 0)
        if count < 2 or not spec.verifiedBy:
            raise ValueError(f"skill {spec.id} auditP requires two server audit P records and verifiedBy")
    if spec.status == "official":
        if not spec.verifiedBy:
            raise ValueError(f"skill {spec.id} official requires verifiedBy")
        if not spec.quality.get("serverAuditP") or not spec.quality.get("userConfirmed"):
            raise ValueError(f"skill {spec.id} official requires serverAuditP and userConfirmed quality evidence")


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


_DICT_LIST_KEY_RE = re.compile(r"^[A-Za-z_][\w]*\s*:")


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
        # dict-list 처리: "- key: value" 형식 + 다음 줄도 같은 들여쓰기 dict key 면 dict.
        # 단순 문장 안 콜론 (예: "When: 분석") 은 string 으로 보존 — 정규식으로 첫 단어가 식별자 + 콜론인지 검사.
        is_dict_form = _DICT_LIST_KEY_RE.match(item) is not None and not item.startswith("[") and not item.endswith(":")
        next_indent_is_dict = False
        if is_dict_form and index + 1 < len(lines):
            nxt = lines[index + 1]
            nxt_strip = nxt.strip()
            nxt_indent = len(nxt) - len(nxt.lstrip(" "))
            if nxt_strip and nxt_indent == current_indent + 2 and _DICT_LIST_KEY_RE.match(nxt_strip):
                next_indent_is_dict = True
        if is_dict_form and next_indent_is_dict:
            key, raw = item.split(":", 1)
            entry: dict[str, Any] = {key.strip(): _parse_yaml_scalar(raw.strip()) if raw.strip() else None}
            index += 1
            inner_indent = current_indent + 2
            while index < len(lines):
                next_line = lines[index]
                next_indent = len(next_line) - len(next_line.lstrip(" "))
                next_stripped = next_line.strip()
                if not next_stripped:
                    index += 1
                    continue
                if next_indent < inner_indent or next_stripped.startswith("- "):
                    break
                if not _DICT_LIST_KEY_RE.match(next_stripped):
                    break
                k2, r2 = next_stripped.split(":", 1)
                entry[k2.strip()] = _parse_yaml_scalar(r2.strip()) if r2.strip() else None
                index += 1
            out.append(entry)
            continue
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


def _score(spec: SkillSpec, terms: list[str], *, query: str = "") -> tuple[float, list[str]]:
    haystacks = {
        "id": spec.id,
        "title": spec.title,
        "category": spec.category,
        "purpose": spec.purpose,
        "whenToUse": " ".join(spec.whenToUse),
        "inputs": " ".join(spec.inputs),
        "outputs": " ".join(spec.outputs),
        "capabilityRefs": " ".join(spec.capabilityRefs),
        "datasetRefs": " ".join(spec.datasetRefs),
        "visualRefs": " ".join(spec.visualRefs),
        "knowledgeRefs": " ".join(spec.knowledgeRefs),
        "linkedSkills": " ".join(spec.linkedSkills),
        "requires": " ".join(spec.requires),
        "alternatives": " ".join(spec.alternatives),
        "succeededBy": " ".join(spec.succeededBy),
        "deprecatedBy": " ".join(spec.deprecatedBy),
        "sourceRefs": " ".join(spec.sourceRefs),
        "runtimeCompatibility": json.dumps(spec.runtimeCompatibility, ensure_ascii=False),
        "docs": json.dumps(spec.docs, ensure_ascii=False),
        "procedure": " ".join(spec.procedure),
        "requiredEvidence": " ".join(spec.requiredEvidence),
        "expectedOutputs": " ".join(spec.expectedOutputs),
        "failureModes": " ".join(spec.failureModes),
        "forbidden": " ".join(spec.forbidden),
        "examples": " ".join(spec.examples),
        "body": str(spec.source.get("body") or ""),
    }
    score = 0.0
    reasons: list[str] = []
    normalized_query = query.lower()
    for term in terms:
        for name, hay in haystacks.items():
            field = hay.lower()
            if term in field:
                weight = _field_weight(name)
                if spec.category in {"engines", "runtime", "operation", "start"}:
                    weight += 0.75
                if normalized_query and normalized_query in field:
                    weight += 3.0
                score += weight
                reasons.append(f"{name}:{term}")
    boost, boost_reasons = _intent_boost(spec, query)
    if boost:
        score += boost
        reasons.extend(boost_reasons)
    if spec.status in {"auditP", "official"}:
        score += 0.5
    domain_bonus, domain_reasons = _domainBonus(spec, normalized_query)
    if domain_bonus:
        score += domain_bonus
        reasons.extend(domain_reasons)
    return score, reasons


_COMPOSITE_TERMS: tuple[str, ...] = (
    "종합",
    "깊이",
    "비교",
    "추세",
    "사이클",
    "다단",
    "deep",
    "comprehensive",
    "compare",
)


def _domainBonus(spec: SkillSpec, normalized_query: str) -> tuple[float, list[str]]:
    """recipe / engines kind 우선 — 종합 키워드 매칭 시 recipe 추가 가중.

    base 가중:
    - recipe: +1.0 (다단 절차)
    - 종합 키워드 매칭 시 recipe: +2.5 추가 (회사명 매칭 점수와 경쟁 가능 수준)
    - engines.* category: +0.3
    """
    bonus = 0.0
    reasons: list[str] = []
    if spec.kind == "recipe":
        bonus += 1.0
        reasons.append("kind:recipe")
        if normalized_query and any(term in normalized_query for term in _COMPOSITE_TERMS):
            bonus += 2.5
            reasons.append("composite_query+recipe")
    elif spec.category == "engines":
        bonus += 0.3
        reasons.append("category:engines")
    return bonus, reasons


def _field_weight(name: str) -> float:
    if name == "id":
        return 4.0
    if name == "title":
        return 3.5
    if name in {"whenToUse", "purpose"}:
        return 2.75
    if name in {"capabilityRefs", "toolRefs", "requiredEvidence", "expectedOutputs"}:
        return 2.0
    if name in {
        "procedure",
        "examples",
        "body",
        "linkedSkills",
        "requires",
        "alternatives",
        "succeededBy",
        "deprecatedBy",
    }:
        return 1.25
    return 1.0


def _intent_boost(spec: SkillSpec, query: str) -> tuple[float, list[str]]:
    query_text = query.lower()
    score = 0.0
    reasons: list[str] = []
    for entry in _load_intent_boosts():
        if spec.id not in entry["skillIds"]:
            continue
        matched = [term for term in entry["terms"] if term.lower() in query_text]
        if not matched:
            continue
        score += float(entry["boost"])
        reasons.append(f"intent:{matched[0]}")
    if spec.id == "engines.company.usEdgarReview" and _TICKER_QUERY_RE.search(query):
        score += 8.0
        reasons.append("intent:ticker")
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
    module_path = Path(__file__).resolve()
    for base in [here, *here.parents, *module_path.parents]:
        if (base / "pyproject.toml").exists() and (base / "src" / "dartlab").exists():
            return base
    return here


search = searchSkills
get = getSkill
describe = describeSkill
