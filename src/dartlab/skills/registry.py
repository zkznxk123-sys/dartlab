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
_INTENT_SKILL_BOOSTS: tuple[dict[str, Any], ...] = (
    {
        "skillIds": ("start.useSkillsCatalog",),
        "terms": (
            "skills",
            "skill",
            "스킬",
            "스킬스",
            "catalog",
            "카탈로그",
            "어떻게 써",
            "사용법",
            "뭐 할 수",
            "할 수 있어",
            "할수",
            "기능",
            "뭘 분석",
        ),
        "boost": 16.0,
    },
    {
        "skillIds": ("start.dartlabSkillOs",),
        "terms": (
            "처음",
            "최초",
            "진입점",
            "입문",
            "전체 체계",
            "문서 체계",
            "skill os",
            "스킬 os",
            "어디서 시작",
            "llm이 와도",
            "외부 ai",
            "운영 문서",
            "ops",
        ),
        "boost": 18.0,
    },
    {
        "skillIds": ("operation.opsAsSkills",),
        "terms": (
            "ops를 스킬",
            "ops 문서",
            "운영 규칙",
            "규칙 통합",
            "문서 중복",
            "ssot",
            "sourceRefs",
            "문서 정리",
            "체계 단순화",
        ),
        "boost": 17.0,
    },
    {
        "skillIds": ("operation.extendSkills",),
        "terms": (
            "스킬 추가",
            "스킬 확장",
            "확장 규칙",
            "새 skill",
            "user skill",
            "curated skill",
            "공식 승격",
            "독스트링 승격",
        ),
        "boost": 16.0,
    },
    {
        "skillIds": ("runtime.skillDevelopmentLoop",),
        "terms": (
            "스킬 개발",
            "skill 개발",
            "엔진 조합",
            "엔진에 없는",
            "정의되지 않은",
            "응용",
            "조합",
            "새 분석",
            "audit 반영",
            "독스트링 보강",
        ),
        "boost": 15.0,
    },
    {
        "skillIds": ("runtime.workbenchEvidenceFlow",),
        "terms": ("근거", "검산", "마무리", "evidence", "ref", "refs", "finalize", "실행하고", "답변"),
        "boost": 15.0,
    },
    {
        "skillIds": ("runtime.dataAvailabilityCheck",),
        "terms": ("데이터가", "데이터", "dataset", "있는지", "가용", "최신", "기준일", "확인"),
        "boost": 14.0,
    },
    {
        "skillIds": ("engines.company.researchStarter",),
        "terms": ("종목 분석", "기업 분석", "분석 시작", "첫 단계", "시작", "company research"),
        "boost": 13.0,
    },
    {
        "skillIds": ("engines.data.foundation",),
        "terms": (
            "데이터 엔진",
            "데이터 기본기",
            "기본 데이터",
            "company gather scan",
            "company/gather/scan",
            "원자료 횡단",
            "데이터 확보 순서",
            "응용 분석 시작",
        ),
        "boost": 15.0,
    },
    {
        "skillIds": ("engines.scan", "engines.scan.growth"),
        "terms": (
            "찾아",
            "찾아줘",
            "후보",
            "상위",
            "랭킹",
            "순위",
            "스크리닝",
            "스캔",
            "screen",
            "ranking",
            "candidate",
            "growth company",
            "성장하는 회사",
        ),
        "boost": 16.0,
    },
    {
        "skillIds": ("engines.viz.tableBackedChart",),
        "terms": ("차트", "시각화", "그래프", "랭킹 차트", "비교 차트", "chart", "visual"),
        "boost": 14.0,
    },
    {
        "skillIds": ("engines.company.usEdgarReview",),
        "terms": ("미국", "미장", "edgar", "filings", "filing", "10-k", "10-q", "ticker", "티커"),
        "boost": 13.0,
    },
    {
        "skillIds": ("engines.macro.marketReview",),
        "terms": ("금리", "환율", "매크로", "거시", "경기", "유동성", "macro", "rates", "fx"),
        "boost": 12.0,
    },
    {
        "skillIds": ("engines.credit.creditRisk",),
        "terms": ("신용", "위험", "안정성", "부채", "이자보상", "credit", "risk"),
        "boost": 11.0,
    },
    {
        "skillIds": ("engines.analysis.profitability",),
        "terms": ("수익성", "이익률", "마진", "영업이익", "profitability", "margin"),
        "boost": 10.0,
    },
    {
        "skillIds": ("engines.analysis.cashflow",),
        "terms": ("현금흐름", "영업현금", "fcf", "cashflow", "cash flow"),
        "boost": 10.0,
    },
    {
        "skillIds": ("engines.analysis.dividendCapitalReturn",),
        "terms": ("배당", "주주환원", "자사주", "dividend", "buyback"),
        "boost": 10.0,
    },
    {
        "skillIds": ("engines.analysis.governanceAudit",),
        "terms": ("지배구조", "감사", "내부통제", "분식", "governance", "audit"),
        "boost": 10.0,
    },
)
_TICKER_QUERY_RE = re.compile(r"\b[A-Z]{1,5}\b")

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
    _validate_execution_skill_contract(spec)
    _validate_capability_refs(spec)


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
    for field in ("runtimeCompatibility", "pyodide", "docs", "quality", "source"):
        value = data.get(field)
        if value is None:
            data[field] = {}
        elif not isinstance(value, dict):
            raise ValueError(f"skill field must be a mapping: {field}")
    if data.get("pyodide") and not data["runtimeCompatibility"].get("pyodide"):
        data["runtimeCompatibility"]["pyodide"] = data["pyodide"]
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
    return score, reasons


def _field_weight(name: str) -> float:
    if name == "id":
        return 4.0
    if name == "title":
        return 3.5
    if name in {"whenToUse", "purpose"}:
        return 2.75
    if name in {"capabilityRefs", "toolRefs", "requiredEvidence", "expectedOutputs"}:
        return 2.0
    if name in {"procedure", "examples", "body"}:
        return 1.25
    return 1.0


def _intent_boost(spec: SkillSpec, query: str) -> tuple[float, list[str]]:
    query_text = query.lower()
    score = 0.0
    reasons: list[str] = []
    for entry in _INTENT_SKILL_BOOSTS:
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
