"""AI Tool 로더 — CAPABILITIES 직접 소비.

사상:
    - dartlab 공개 API (docstring) → generateSpec.py → CAPABILITIES → tool schemas
    - registry/bootstrap 수동 등록 없음. CAPABILITIES 가 단일 원천.
    - 축은 CAPABILITIES 안의 `{engine}.{axis}` entry 로 자동 수집됨.

소비자 (runtime/toolLoop.py) 는 `buildTools()` 한 번 호출 → [AITool] 리스트 획득.
"""

from __future__ import annotations

import inspect
from dataclasses import dataclass
from typing import Any, Callable


@dataclass
class AITool:
    name: str
    description: str
    parameters: dict
    handler: Callable[..., Any]


# ── AI 가 tool 로 쓸 공개 API ────────────────────────────────

# CAPABILITIES 의 key → (kind, target). kind: "company" / "module".
# 이 매핑은 공개 API 전수 중 "LLM 이 자율로 호출하는" 것만 선별하기 위함.
# review 는 보고서 요청 전용 가이드로 시스템 프롬프트에서 유도 — tool 은 포함.
_TOOLS: dict[str, tuple[str, str]] = {
    "show": ("company", "show"),
    "analysis": ("company", "analysis"),
    "credit": ("company", "credit"),
    "gather": ("company", "gather"),
    "review": ("company", "review"),
    "scan": ("module", "scan"),
    "macro": ("module", "macro"),
    "search": ("module", "search"),
    "searchCompany": ("module", "searchName"),
}


def buildTools() -> list[AITool]:
    """CAPABILITIES + inspect.signature → [AITool]. 매 호출 시 신선."""
    from dartlab.guide._generated import CAPABILITIES

    tools: list[AITool] = []

    for name, (kind, target) in _TOOLS.items():
        capKey = f"Company.{target}" if kind == "company" else target
        cap = CAPABILITIES.get(capKey, {})
        callable_ = _resolveCallable(kind, target)
        if callable_ is None:
            continue
        tools.append(
            AITool(
                name=name,
                description=cap.get("summary") or _firstDocLine(callable_) or name,
                parameters=_buildSchema(callable_, name, kind, CAPABILITIES),
                handler=_buildHandler(name, kind, target),
            )
        )

    # pythonExec — 유일 특수 케이스 (subprocess)
    tools.append(
        AITool(
            name="pythonExec",
            description=(
                "[escape hatch] 도메인 tool 로 못 풀 때만. 커스텀 비율/override 이외 조합/특이 계산. "
                "dartlab · pl (polars) 사용 가능. stockCode 지정 시 c (Company) 바인딩."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "code": {"type": "string", "description": "실행할 Python 코드. print() 로 결과 출력."},
                    "stockCode": {"type": "string", "description": "Company 바인딩용 종목코드 (선택)."},
                },
                "required": ["code"],
                "additionalProperties": False,
            },
            handler=_pythonExec,
        )
    )

    return tools


# ── Resolve / Handler ─────────────────────────────────────


def _resolveCallable(kind: str, target: str) -> Any:
    """signature 추출용 callable."""
    if kind == "company":
        try:
            from dartlab.providers.dart.company import Company as _C
        except ImportError:
            return None
        # Company 는 property 로 dual-access — 실제 구현은 `_{target}Impl`
        return getattr(_C, f"_{target}Impl", None) or getattr(_C, target, None)
    if kind == "module":
        # _CallableModule wrapper 우회 — 원본 class 의 __call__ 사용
        if target == "scan":
            from dartlab.scan import Scan

            return Scan.__call__
        if target == "macro":
            from dartlab.macro import Macro

            return Macro.__call__
        # 일반 모듈 함수 (search / searchName 등)
        try:
            import dartlab

            return getattr(dartlab, target, None)
        except ImportError:
            return None
    return None


def _buildHandler(name: str, kind: str, target: str) -> Callable[..., Any]:
    if kind == "company":

        def _companyHandler(stockCode: str, **kwargs: Any) -> Any:
            import dartlab

            c = dartlab.Company(stockCode)
            clean = {k: v for k, v in kwargs.items() if v is not None}
            # show 의 fields 인자 → select 위임 (Read 하나로 단순화)
            if name == "show":
                fields = clean.pop("fields", None)
                if fields:
                    topic = clean.pop("topic", None)
                    selectKwargs = {k: v for k, v in clean.items() if k in ("freq", "scope")}
                    return c.select(topic, fields, **selectKwargs)
            return getattr(c, target)(**clean)

        return _companyHandler

    if kind == "module":

        def _moduleHandler(**kwargs: Any) -> Any:
            import dartlab

            # LLM 이 미지정 파라미터를 "" 로 보내는 케이스 정규화
            clean = {k: v for k, v in kwargs.items() if v not in (None, "")}
            fn = getattr(dartlab, target)
            core, post = _splitKwargs(target, clean)
            if target == "search" and clean.get("limit"):
                core["topK"] = clean["limit"]
            result = fn(**core)
            return _scanPostProcess(result, post) if target == "scan" else result

        return _moduleHandler

    raise ValueError(f"unknown kind: {kind}")


# ── Schema 자동 생성 ──────────────────────────────────────


def _buildSchema(obj: Any, name: str, kind: str, caps: dict) -> dict:
    """inspect.signature + CAPABILITIES 축 entry → JSON Schema."""
    props: dict[str, dict] = {}
    required: list[str] = []

    if kind == "company":
        props["stockCode"] = {"type": "string", "description": "종목코드 (예: '005930', 'AAPL')"}
        required.append("stockCode")

    try:
        sig = inspect.signature(obj)
    except (ValueError, TypeError):
        sig = None

    if sig is not None:
        for pName, param in sig.parameters.items():
            if pName in ("self", "cls", "stockCode") or param.kind in (
                inspect.Parameter.VAR_POSITIONAL,
                inspect.Parameter.VAR_KEYWORD,
            ):
                continue
            prop: dict[str, Any] = {"type": _paramType(param)}
            enumValues = _enumFromCapabilities(name, pName, caps)
            if enumValues:
                prop["enum"] = enumValues
            props[pName] = prop
            if param.default is inspect.Parameter.empty:
                required.append(pName)

    # show: select 통합을 위한 fields
    if name == "show":
        props["fields"] = {
            "type": "array",
            "items": {"type": "string"},
            "description": "계정명 필터 (선택). 예: ['매출액','영업이익']. 지정 시 해당 행만 반환 (select 위임).",
        }

    # scan: target 의미 명확화 + 후처리 파라미터
    if name == "scan":
        # target 은 account/ratio/screen 축에서만 의미. 다른 축에선 절대 쓰면 안 됨.
        if "target" in props:
            props["target"]["description"] = (
                "axis='account' 일 때 계정명(예: '매출액'), axis='ratio' 일 때 비율명(예: 'roe'), "
                "axis='screen' 일 때 프리셋(예: 'value'). **그 외 축에서는 생략**. "
                "종목 필터는 stockCode 파라미터를 쓸 것."
            )
        props.update(
            {
                "stockCode": {"type": "string", "description": "특정 종목만 필터 (선택). 예: '005930'"},
                "sortBy": {"type": "string", "description": "정렬 컬럼명 (예: '매출CAGR', 'ROE')"},
                "descending": {"type": "boolean", "description": "내림차순 (기본 true)"},
                "limit": {"type": "integer", "description": "상위 N개 (기본 20)", "minimum": 1, "maximum": 200},
            }
        )
    if name == "search":
        props["limit"] = {"type": "integer", "description": "상위 N개 (기본 10)", "minimum": 1, "maximum": 50}

    return {"type": "object", "properties": props, "required": required, "additionalProperties": False}


def _enumFromCapabilities(toolName: str, paramName: str, caps: dict) -> list[str]:
    """CAPABILITIES 에서 `{engine}.{axis}` entry 를 수집해 enum 으로."""
    # axis 파라미터 → 엔진 자체 공간의 축 entry 수집
    if paramName == "axis" and toolName in ("scan", "macro", "gather"):
        prefix = f"{toolName}."
        return sorted(k[len(prefix):] for k in caps if k.startswith(prefix))
    # show.topic — 재무제표/주석/docs topic 합집합 (엔진 메타에 모든게 있진 않음)
    if toolName == "show" and paramName == "topic":
        return _showTopics()
    # show.freq
    if toolName == "show" and paramName == "freq":
        return ["Q", "Y", "YTD"]
    # search.scope
    if toolName == "search" and paramName == "scope":
        return ["title", "content", "auto"]
    # analysis.axis — docstring 의 "14축 분석: A, B, C, ..." 패턴 파싱
    if toolName == "analysis" and paramName == "axis":
        return _parseAxesFromDocstring("analysis")
    # credit.axis — 실제 _CREDIT_AXES 를 직접 사용 (추측 방지)
    if toolName == "credit" and paramName == "axis":
        try:
            from dartlab.credit import _CREDIT_AXES  # type: ignore[attr-defined]

            return list(_CREDIT_AXES.keys())
        except (ImportError, AttributeError):
            return _parseAxesFromDocstring("credit")
    # review.type
    if toolName == "review" and paramName == "type":
        return [
            "full",
            "executive",
            "credit",
            "valuation",
            "growth",
            "crisis",
            "audit",
            "dividend",
            "governance",
            "macro",
            "thesis",
        ]
    return []


def _parseAxesFromDocstring(target: str) -> list[str]:
    """Company._{target}Impl docstring 에서 "N축 분석: A, B, C, ..." 패턴 추출."""
    import re

    try:
        from dartlab.providers.dart.company import Company as _C
    except ImportError:
        return []
    impl = getattr(_C, f"_{target}Impl", None)
    if impl is None:
        return []
    doc = inspect.getdoc(impl) or ""
    # "14축 분석: 수익구조, 자금조달, ..." 또는 "축 이름 (\"채무상환\", \"자본구조\" 등)"
    m = re.search(r"축[^\n:]*:\s*([^\n]+)", doc)
    if m:
        parts = [p.strip().strip('"').strip("'") for p in re.split(r"[,、]", m.group(1)) if p.strip()]
        # 꼬리 "등" 제거
        parts = [p for p in parts if p and p != "등"]
        if parts:
            return parts
    # 따옴표 패턴 fallback: "A", "B"
    quoted = re.findall(r'"([^"]+)"', doc)
    if quoted:
        return quoted[:20]
    return []


def _showTopics() -> list[str]:
    finance = ["IS", "BS", "CF", "CIS", "SCE", "ratios", "ratioSeries"]
    notes = [
        "inventory",
        "borrowings",
        "tangibleAsset",
        "intangibleAsset",
        "receivables",
        "provisions",
        "eps",
        "segments",
        "costByNature",
        "lease",
        "affiliates",
        "investmentProperty",
        "financialNotes",
        "consolidatedNotes",
    ]
    try:
        from dartlab.core.docs.topicGraph import TOPIC_KEYWORDS

        docs = list(TOPIC_KEYWORDS.keys())
    except ImportError:
        docs = []
    seen: set[str] = set()
    out: list[str] = []
    for t in finance + notes + docs:
        if t not in seen:
            seen.add(t)
            out.append(t)
    return out


def _paramType(param: inspect.Parameter) -> str:
    if param.annotation is inspect.Parameter.empty:
        return "string"
    ann = str(param.annotation).lower()
    if "str" in ann:
        return "string"
    if "bool" in ann:
        return "boolean"
    if "int" in ann:
        return "integer"
    if "float" in ann:
        return "number"
    if "dict" in ann:
        return "object"
    return "string"


# ── Module tool post-processing ───────────────────────────


_MODULE_CORE: dict[str, set[str]] = {
    "scan": {"axis", "target"},
    "macro": {"axis", "target", "market"},
    "search": {"query", "corp", "start", "end", "topK", "scope"},
    "searchName": {"keyword"},
}


def _splitKwargs(target: str, kwargs: dict) -> tuple[dict, dict]:
    core_keys = _MODULE_CORE.get(target, set())
    core = {k: v for k, v in kwargs.items() if k in core_keys and v is not None}
    post = {k: v for k, v in kwargs.items() if k not in core_keys and v is not None}
    return core, post


def _scanPostProcess(df: Any, post: dict) -> Any:
    if df is None or not post:
        return df
    try:
        stockCode = post.get("stockCode")
        if stockCode:
            col = "종목코드" if "종목코드" in df.columns else "stockCode" if "stockCode" in df.columns else None
            if col:
                df = df.filter(df[col] == stockCode)
        if post.get("sortBy"):
            df = df.sort(post["sortBy"], descending=post.get("descending", True), nulls_last=True)
        limit = post.get("limit", 20)
        if limit and limit > 0:
            df = df.head(limit)
    except (AttributeError, KeyError, ValueError):
        pass
    return df


def _pythonExec(code: str, stockCode: str | None = None) -> str:
    from dartlab.ai.tools.coding import DartlabCodeExecutor

    return DartlabCodeExecutor().execute(code, stockCode=stockCode, timeout=60)


def _firstDocLine(obj: Any) -> str:
    doc = inspect.getdoc(obj)
    return doc.split("\n", 1)[0].strip() if doc else ""


# ── OpenAI function calling 스키마 변환 (소비자용 헬퍼) ──


def toolsToOpenAiSchemas(tools: list[AITool]) -> list[dict]:
    return [
        {
            "type": "function",
            "function": {"name": t.name, "description": t.description, "parameters": t.parameters},
        }
        for t in tools
    ]


def executeTool(tools: list[AITool], name: str, arguments: dict) -> Any:
    for t in tools:
        if t.name == name:
            return t.handler(**arguments)
    raise ValueError(f"알 수 없는 tool: {name}. 등록됨: {[t.name for t in tools]}")
