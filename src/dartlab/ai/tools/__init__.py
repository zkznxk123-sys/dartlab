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

# 자동 수집에서 제외할 이름. AI tool 이 될 수 없거나 되면 안 되는 것들.
_BLACKLIST: set[str] = {
    # 데이터 수집 / 배포
    "setup",
    "collect",
    "collectAll",
    "downloadAll",
    # facade class / 래퍼 class
    "Company",
    "Fred",
    "OpenDart",
    "OpenEdgar",
    "ChartResult",
    "SelectResult",
    "Review",
    # 설정 / 메타
    "config",
    "dataDir",
    "verbose",
    "capabilities",
    # 진입점 자체
    "ask",
    # 유틸 (searchCompany 로 대체)
    "codeToName",
    "nameToCode",
    # listing = 카탈로그. AI 가 직접 쓸 일 없음
    "listing",
    # Company 내부 helper
    "select",  # show(fields=...) 가 위임 처리
    # Provider protocol (AI 가 알 필요 없음)
    "canHandle",
    "priority",
    "resolve",
    # 데이터 유지보수 (AI 가 쓰면 안 됨)
    "status",
    "update",
    # 인터랙티브 (AI runtime 에 부적합)
    "view",
    # Low-level parser helper
    "table",
}


def _autoDiscover() -> dict[str, tuple[str, str]]:
    """dartlab.__all__ + Company 공개 method 자동 순회 + 블랙리스트.

    우선순위: **module-level (시장 전체) > Company-bound (개별 종목)**.
    이유: AI tool 은 기본이 "시장 전체 / 종목 비의존" 의미. 같은 이름이 둘 다 있으면
    module 이 더 범용. 예: `search` = dartlab.search (시장 공시) vs Company.search
    (이 회사 공시) — AI 는 전자가 기본 유용.
    """
    import dartlab
    from dartlab.providers.dart.company import Company as _C

    tools: dict[str, tuple[str, str]] = {}

    # 1. Module-level 먼저
    _MODULE_WHITELIST = {"scan", "macro", "quant", "gather", "industry", "topdown"}
    for name in getattr(dartlab, "__all__", []):
        if name in _BLACKLIST or name.startswith("_"):
            continue
        obj = getattr(dartlab, name, None)
        if obj is None or inspect.isclass(obj):
            continue
        if inspect.ismodule(obj) and name not in _MODULE_WHITELIST:
            continue
        if not callable(obj):
            continue
        tools[name] = ("module", name)

    # 2. Company-bound — module 에 없는 것만 (analysis/credit/review/show/... 은 여기서)
    for attr in dir(_C):
        if attr.startswith("_") or attr in _BLACKLIST or attr in tools:
            continue
        # dual-access property (_xxxImpl 존재) 우선
        if getattr(_C, f"_{attr}Impl", None) is not None:
            tools[attr] = ("company", attr)
            continue
        # 직접 method (gather, quant 등)
        obj = getattr(_C, attr, None)
        if callable(obj) and (inspect.isfunction(obj) or inspect.ismethod(obj)):
            if not isinstance(obj, type):
                tools[attr] = ("company", attr)

    # 3. searchName → searchCompany (AI 친화적 이름)
    if "searchName" in tools:
        tools["searchCompany"] = tools.pop("searchName")

    return tools


def buildTools() -> list[AITool]:
    """CAPABILITIES + inspect.signature → [AITool]. 매 호출 시 신선."""
    from dartlab.guide._generated import CAPABILITIES

    tools: list[AITool] = []
    registry = _autoDiscover()

    for name, (kind, target) in registry.items():
        capKey = f"Company.{target}" if kind == "company" else target
        cap = CAPABILITIES.get(capKey, {})
        callable_ = _resolveCallable(kind, target)
        if callable_ is None:
            continue
        tools.append(
            AITool(
                name=name,
                description=_mergeDescWithReturns(cap.get("summary", ""), callable_, name),
                parameters=_buildSchema(callable_, name, kind, CAPABILITIES),
                handler=_buildHandler(name, kind, target),
            )
        )

    # pastInsight / sectorInsights 는 dartlab.__all__ 에 노출되어 위 _autoDiscover 가 자동 등록.

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
        if target == "quant":
            try:
                from dartlab.quant import Quant  # type: ignore

                return Quant.__call__
            except ImportError:
                pass
        if target == "industry":
            from dartlab.industry import Industry

            return Industry.__call__
        if target == "topdown":
            from dartlab.topdown import topdown as _topdownFn

            return _topdownFn
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
        _SKIP_NAMES = {"self", "cls"} | ({"stockCode"} if kind == "company" else set())
        args_desc = _parseDocstringArgs(obj)
        for pName, param in sig.parameters.items():
            if pName in _SKIP_NAMES or param.kind in (
                inspect.Parameter.VAR_POSITIONAL,
                inspect.Parameter.VAR_KEYWORD,
            ):
                continue
            prop: dict[str, Any] = {"type": _paramType(param)}
            enumValues = _enumFromCapabilities(name, pName, caps)
            if enumValues:
                prop["enum"] = enumValues
            desc = args_desc.get(pName)
            if desc:
                prop["description"] = desc
            props[pName] = prop
            if param.default is inspect.Parameter.empty:
                required.append(pName)

    # overrides — 4 엔진 공통 + Company method (validateStory). AI 가 엔진 계산 가정 직접 조율.
    if name in ("analysis", "credit", "quant", "macro"):
        try:
            from dartlab.core.overrides import describeOverrides

            props["overrides"] = {
                "type": "object",
                "description": describeOverrides(name),
                "additionalProperties": True,
            }
        except ImportError:
            pass
    # Phase 4 G14a: validateStory 도 VALUATION_KEYS override 노출 (analysis 경로 재사용)
    elif name == "validateStory":
        try:
            from dartlab.core.overrides import describeOverrides

            props["overrides"] = {
                "type": "object",
                "description": describeOverrides("analysis"),
                "additionalProperties": True,
            }
        except ImportError:
            pass

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
    """CAPABILITIES 에서 enum 값 자동 수집. dict dispatch 로 조건 nesting 제거."""
    # axis 파라미터 → 엔진 자체 공간의 축 entry 수집 (scan/macro/gather 공통)
    if paramName == "axis" and toolName in ("scan", "macro", "gather"):
        prefix = f"{toolName}."
        return sorted(k[len(prefix) :] for k in caps if k.startswith(prefix))
    # 특수 해석기 — (toolName, paramName) → resolver
    resolver = _ENUM_RESOLVERS.get((toolName, paramName))
    if resolver:
        try:
            return resolver()
        except (ImportError, AttributeError):
            return []
    return []


def _resolveShowFreq() -> list[str]:
    from dartlab.core.show import SHOW_FREQS

    return list(SHOW_FREQS)


def _resolveSearchScope() -> list[str]:
    from dartlab.core.search import SEARCH_SCOPES

    return list(SEARCH_SCOPES)


def _resolveAnalysisAxis() -> list[str]:
    from dartlab.analysis.financial import _AXIS_REGISTRY as _AR

    return sorted(_AR.keys())


def _resolveCreditAxis() -> list[str]:
    from dartlab.credit import _CREDIT_AXES  # type: ignore[attr-defined]

    return list(_CREDIT_AXES.keys())


def _resolveReviewType() -> list[str]:
    from dartlab.review.reportTypes import REPORT_TYPES

    return sorted(REPORT_TYPES.keys())


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


_ENUM_RESOLVERS: dict[tuple[str, str], Callable[[], list[str]]] = {
    ("show", "topic"): _showTopics,
    ("show", "freq"): _resolveShowFreq,
    ("search", "scope"): _resolveSearchScope,
    ("analysis", "axis"): _resolveAnalysisAxis,
    ("credit", "axis"): _resolveCreditAxis,
    ("review", "type"): _resolveReviewType,
}


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


def _splitKwargs(target: str, kwargs: dict) -> tuple[dict, dict]:
    """함수 시그니처 자동 분석으로 허용 파라미터 / 추가 파라미터 분리.

    수동 whitelist 금지 원칙 (CAPABILITIES 자동). pastInsight/sectorInsights
    포함 모든 module-level tool 에 일관 적용.
    """
    fn = _resolveCallable("module", target)
    if fn is None:
        return {}, kwargs
    try:
        sig = inspect.signature(fn)
        core_keys = {
            n
            for n, p in sig.parameters.items()
            if n not in ("self", "cls")
            and p.kind not in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD)
        }
    except (ValueError, TypeError):
        core_keys = set()
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


_DOCSTRING_SECTIONS = {
    "Args:",
    "Parameters:",
    "Returns:",
    "Raises:",
    "Notes:",
    "Examples:",
    "See Also:",
    "반환:",
    "인자:",
}


def _mergeDescWithReturns(summary: str, callable_: Any, fallback_name: str) -> str:
    """CAPABILITIES summary + docstring Returns 합체. AI 가 결과 구조를 아는 것이 핵심."""
    full_desc = _toolDescription(callable_)
    if summary:
        if full_desc and "\n\nReturns:" in full_desc:
            returns_part = full_desc.split("\n\nReturns:", 1)[1]
            return f"{summary}\n\nReturns:{returns_part}"
        return summary
    return full_desc or fallback_name


def _toolDescription(obj: Any) -> str:
    """docstring summary + Returns 추출. AI 가 tool 결과 구조를 아는 것이 핵심."""
    doc = inspect.getdoc(obj)
    if not doc:
        return ""
    lines = doc.strip().split("\n")
    summary = lines[0].strip()
    returns_lines: list[str] = []
    in_returns = False
    for line in lines[1:]:
        stripped = line.strip()
        if stripped.startswith("Returns") or stripped.startswith("반환"):
            in_returns = True
            continue
        if in_returns:
            if stripped in _DOCSTRING_SECTIONS:
                break
            if stripped:
                returns_lines.append(stripped)
    if returns_lines:
        returns_text = " ".join(returns_lines[:8])
        return f"{summary}\n\nReturns: {returns_text}"
    return summary


def _parseDocstringArgs(obj: Any) -> dict[str, str]:
    """docstring Args/Parameters 섹션에서 파라미터별 설명 추출."""
    doc = inspect.getdoc(obj)
    if not doc:
        return {}
    result: dict[str, str] = {}
    in_args = False
    current_param: str | None = None
    for line in doc.split("\n"):
        stripped = line.strip()
        if stripped in ("Args:", "Parameters:", "인자:"):
            in_args = True
            continue
        if not in_args:
            continue
        if stripped and stripped[0].isalpha() and stripped.endswith(":") and " " not in stripped.rstrip(":"):
            break
        if stripped.startswith("Returns") or stripped.startswith("Raises") or stripped.startswith("반환"):
            break
        if ":" in stripped and not stripped.startswith("-") and not stripped.startswith("*"):
            parts = stripped.split(":", 1)
            param_name = parts[0].strip().split("(")[0].strip()
            desc = parts[1].strip() if len(parts) > 1 else ""
            if param_name and param_name.isidentifier():
                result[param_name] = desc
                current_param = param_name
            elif current_param and stripped:
                result[current_param] += " " + stripped
        elif current_param and stripped:
            result[current_param] += " " + stripped
    return result


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
