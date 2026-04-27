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
    "Story",
    # 설정 / 메타
    "config",
    "dataDir",
    "verbose",
    # 진입점 자체
    "ask",
    # 유틸 (searchCompany 로 대체)
    "codeToName",
    "nameToCode",
    # 종목코드→이름은 Company(stockCode).corpName 으로 이미 접근 가능 (AI 가 stockCode 없이 호출하면 실패)
    "codeName",
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

    # 2. Company-bound — module 에 없는 것만 (analysis/credit/story/show/... 은 여기서)
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
    from dartlab.core._generated import CAPABILITIES

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
                "Python 코드 실행. 두 가지 용도: "
                "(1) 복합 분석 — 여러 엔진을 한 번에 조합할 때 "
                "(예: analysis + credit + macro 결과를 교차 분석). "
                "(2) 커스텀 계산 — override 시뮬레이션, 비율 계산, 데이터 가공. "
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

    # Read — 파일 내용을 문자열로 반환. SKILL.md · ops 문서 · blog 포스트 · 코드 열람 전용.
    # Claude Code Read 와 동일 개념. repo 루트 기준 상대경로 또는 절대경로 허용.
    tools.append(
        AITool(
            name="Read",
            description=(
                "파일 내용을 문자열로 반환. 주요 용도: "
                "(1) `src/dartlab/skills/{name}/SKILL.md` — skill 본문 로드해 How 절차 따르기. "
                "(2) `src/dartlab/skills/{name}/reference/*.md` — 업종별 임계값 · 실전 예시 등 참고자료. "
                "(3) `ops/*.md` — 엔진 설계 문서. (4) `blog/**/index.md` — 과거 기업분석 서사. "
                "(5) 코드 구현 확인용 `src/dartlab/**/*.py`. "
                "경로는 저장소 루트 기준 상대 또는 절대. UTF-8 텍스트만."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "filePath": {"type": "string", "description": "읽을 파일 경로 (상대 또는 절대)."},
                    "maxBytes": {
                        "type": "integer",
                        "description": "최대 바이트 (기본 100000). 큰 파일은 제한.",
                        "minimum": 1,
                        "maximum": 1000000,
                    },
                },
                "required": ["filePath"],
                "additionalProperties": False,
            },
            handler=_readFile,
        )
    )

    return tools


def _readFile(filePath: str = "", maxBytes: int = 100_000, **_: Any) -> str:
    """`Read` tool 핸들러 — 파일 UTF-8 텍스트 반환.

    Tool dispatch 는 keyword args 로 unwrap 하므로 ``filePath`` / ``maxBytes`` 를
    직접 받는다 (이전 ``args: dict`` 시그니처는 OpenAI tool calling 과 호환되지 않아
    ``unexpected keyword argument 'filePath'`` 로 fail 했다).
    """
    from pathlib import Path

    maxBytes = int(maxBytes or 100_000)
    if not filePath:
        return "[error] filePath required"

    p = Path(filePath)
    if not p.is_absolute():
        # 저장소 루트 기준 — src/dartlab/ai/tools/__init__.py → parents[4]
        root = Path(__file__).resolve().parents[4]
        p = root / filePath
    try:
        if not p.exists():
            return f"[error] file not found: {p}"
        if p.is_dir():
            return f"[error] path is a directory: {p}"
        data = p.read_bytes()
        if len(data) > maxBytes:
            truncated = data[:maxBytes].decode("utf-8", errors="replace")
            return f"{truncated}\n\n[... truncated at {maxBytes} bytes / total {len(data)} bytes ...]"
        return data.decode("utf-8", errors="replace")
    except OSError as exc:
        return f"[error] read failed: {exc}"


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
            # request-scoped Company 캐시 — 같은 요청 안에서 같은 stockCode 는 인스턴스 1개 공유.
            # ctx 없으면 매번 새 인스턴스 (notebook/CLI 사용자 영향 없음).
            from dartlab.ai.runtime.companyCache import getOrCreateCompany

            c = getOrCreateCompany(stockCode)
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

            # market 자동 감지: stockCode 힌트가 있으면 core/market SSOT 사용
            if "market" not in clean and target in ("macro", "gather", "scan"):
                sc = clean.get("stockCode") or clean.get("target")
                if sc and isinstance(sc, str):
                    from dartlab.core.market import detectMarket

                    clean["market"] = detectMarket(sc)

            # scan axis='ratio' · 'account' 은 기본 freq='Y' (연간) 로 주입 — AI 는 광역 발굴에
            # 연간 수치를 써야 임계값 필터가 의미 있다. Company.show 와 달리 scan 은 본질적으로
            # 연간 횡단 비교가 표준 용도. 사용자가 freq='Q' 명시하면 그대로 존중.
            if target == "scan" and clean.get("axis") in ("ratio", "account") and "freq" not in clean:
                clean["freq"] = "Y"

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
        # axis 선택 가이드 — 광역 발굴은 primitive 조합 필수.
        if "axis" in props:
            base_desc = props["axis"].get("description") or "전종목 횡단 축"
            props["axis"]["description"] = (
                f"{base_desc}\n\n"
                "⛔ 광역 발굴 질문 (투자할만한/좋은/성장세 좋은/배당 좋은/저평가/"
                "턴어라운드) 은 axis='profitability' 같은 프리셋 한 번만 호출하고 끝내지 말 것. "
                "axis='ratio' (여러 ratioName) + axis='account' 를 최소 3~4 번 호출해 polars join 으로 "
                "교집합 낸 뒤 후보 표 출력하고 응답 종료. "
                "구체 레시피·7 관점 스크리닝·5 단계 발굴 워크플로 SSOT 는 "
                "scanRatio / scanAccount 의 docstring Guide 섹션."
            )
        # target 은 account/ratio/screen 축에서만 의미. 다른 축에선 절대 쓰면 안 됨.
        if "target" in props:
            props["target"]["description"] = (
                "axis='account' 일 때 계정명(예: '매출액'), axis='ratio' 일 때 비율명(예: 'roe'), "
                "axis='screen' 일 때 프리셋(예: 'value'). **그 외 축에서는 생략**. "
                "종목 필터는 stockCode 파라미터를 쓸 것.\n\n"
                "⛔ axis='ratio' 가용 비율 (정확히 이 13 개만): "
                "roe, roa, operatingMargin, netMargin, grossMargin, debtRatio, currentRatio, equityRatio, "
                "revenueGrowth, operatingProfitGrowth, netProfitGrowth, totalAssetTurnover, operatingCfMargin. "
                "⛔ pbr · per · psr · dividendYield · evEbitda · debt_to_equity (= debtRatio) 등은 호출 금지 → ValueError. "
                "시가총액 기반 밸류에이션은 **반드시** axis='valuation' (target 생략). "
                "이자보상배율 · CCC · accrual 등 미구현 지표는 pythonExec 에서 axis='account' 결과 조합으로 계산.\n\n"
                "⛔ operatingMargin · netMargin 결과 해석 — 지주사·금융업·라이센싱사는 매출 정의 차이로 100 % 초과 비정상치 raw 반환 "
                "(예 2024: LG 161 %, 한솔케미칼 234 %, 파마리서치 379 %, 대성홀딩스 69 %). "
                "후보 표에 그대로 인용 금지 — listing() 의 시장구분/업종으로 1차 필터 또는 분석 대상에서 제외."
            )
        props.update(
            {
                "stockCode": {
                    "type": "string",
                    "description": (
                        "[주의] scan 은 전종목 횡단 비교 전용. 단일 종목 분석이면 이 도구를 호출하지 말고 "
                        "`analysis` / `credit` / `show` / `quant` / `debt` / `capital` / `governance` 를 사용할 것. "
                        "정 필요할 때만 전종목 결과에서 특정 종목 1개로 post-filter. 예: '005930'."
                    ),
                },
                "freq": {
                    "type": "string",
                    "enum": ["Q", "Y"],
                    "description": (
                        "axis='ratio' / 'account' 전용 기간 단위. "
                        "`'Q'` 분기 컬럼 (`2025Q4` · `2025Q3` …, 기본). "
                        "`'Y'` 연간 컬럼 (`2025` · `2024` …, 사업보고서 기준). "
                        "⛔ 광역 발굴 질문 (투자할만한 / 좋은 회사 / 요즘 투자하기 좋은) 에는 **반드시 `freq='Y'`** — "
                        "분기값으로 필터하면 ROE 5%대가 정상처럼 보여 임계값 (ROE 12% 이상 등) 적용 불가. "
                        "분기 추이 · 턴어라운드 조짐 같은 특수 질문에만 `freq='Q'`."
                    ),
                },
                "sortBy": {"type": "string", "description": "정렬 컬럼명 (예: '매출CAGR', 'ROE')"},
                "descending": {"type": "boolean", "description": "내림차순 (기본 true)"},
                "limit": {"type": "integer", "description": "상위 N개 (기본 20)", "minimum": 1, "maximum": 200},
                "refresh": {
                    "type": "boolean",
                    "description": "axis='valuation' 전용 — true 면 네이버 API 재수집 (~50초). 기본값 false 는 일일 prebuild snapshot 로드 (1초 이내). 장중 급변 질문에만 true.",
                },
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


def _resolveStoryType() -> list[str]:
    from dartlab.story.reportTypes import REPORT_TYPES

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
    ("story", "type"): _resolveStoryType,
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
        sortBy = post.get("sortBy")
        if sortBy:
            # AI 가 실재하지 않는 컬럼명("이익품질" 등) 을 sortBy 로 보내는 케이스 — sort 스킵하고 df 반환.
            # 도구 호출 자체를 실패시키면 AI 는 데이터 자체를 못 받음.
            if hasattr(df, "columns") and sortBy in df.columns:
                df = df.sort(sortBy, descending=post.get("descending", True), nulls_last=True)
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
    # google-style (콜론 포함)
    "Args:",
    "Parameters:",
    "Returns:",
    "Raises:",
    "Notes:",
    "Examples:",
    "Example:",
    "See Also:",
    "Guide:",
    "Verified:",
    "반환:",
    "인자:",
    # numpy-style (헤더 단독줄, 콜론 없음 — 다음 줄 underline 으로 식별)
    "Args",
    "Parameters",
    "Returns",
    "Raises",
    "Notes",
    "Examples",
    "Example",
    "See Also",
    "Guide",
    "Verified",
}


def _isUnderline(line: str) -> bool:
    """numpy-style ``-----`` underline 여부."""
    s = line.strip()
    return bool(s) and set(s) <= {"-"}


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
    """docstring 핵심 본문 추출 — Summary + Returns + Notes + Guide + Verified.

    AI 가 tool 호출 시 보는 description. summary 만으로는 호출 결정에 정보 부족 →
    Returns (결과 구조) · Notes (제약·예외) · Guide (관점·워크플로) · Verified (audit
    P 통과 조합 누적) 까지 합쳐 skill-grade docstring 의 본문이 AI 에 도달하게 한다.
    numpy-style (헤더 단독줄 + ``-----`` underline) 과 google-style (``Returns:``)
    모두 인식.
    """
    doc = inspect.getdoc(obj)
    if not doc:
        return ""
    lines = doc.strip().split("\n")
    summary = lines[0].strip()

    # 섹션별 라인 누적 (Returns/Notes/Guide/Verified 만 — Examples/See Also 등은 schema 에 무게)
    sections: dict[str, list[str]] = {"Returns": [], "Notes": [], "Guide": [], "Verified": []}
    current: str | None = None
    # 라인 cap (token 폭주 방지). Verified 누적 정책은 ops/code.md 운영 룰에서 별도 결정.
    cap = {"Returns": 12, "Notes": 16, "Guide": 40, "Verified": 16}

    i = 1
    while i < len(lines):
        stripped = lines[i].strip()

        # numpy-style 헤더: "Returns" 단독 + 다음줄 underline
        if (
            stripped in ("Returns", "Notes", "Guide", "Verified", "반환")
            and i + 1 < len(lines)
            and _isUnderline(lines[i + 1])
        ):
            current = "Returns" if stripped == "반환" else stripped
            i += 2
            continue
        # google-style 헤더: "Returns:"
        if stripped in ("Returns:", "Notes:", "Guide:", "Verified:", "반환:"):
            key = stripped.rstrip(":").strip()
            current = "Returns" if key == "반환" else key
            i += 1
            continue
        # 다른 섹션 진입 → current 종료
        if stripped in _DOCSTRING_SECTIONS:
            current = None
            i += 1
            continue
        # numpy-style header underline 단독줄 (이미 처리된 경우 외)
        if _isUnderline(stripped):
            i += 1
            continue
        if current and stripped and len(sections[current]) < cap[current]:
            sections[current].append(stripped)
        i += 1

    parts = [summary]
    if sections["Returns"]:
        parts.append("Returns: " + " ".join(sections["Returns"]))
    if sections["Notes"]:
        parts.append("Notes: " + " ".join(sections["Notes"]))
    if sections["Guide"]:
        parts.append("Guide: " + " ".join(sections["Guide"]))
    if sections["Verified"]:
        parts.append("Verified: " + " ".join(sections["Verified"]))
    return "\n\n".join(parts)


def _parseDocstringArgs(obj: Any) -> dict[str, str]:
    """docstring Args/Parameters 섹션에서 파라미터별 설명 추출.

    google-style (``param: type, desc``) + numpy-style (``param : type`` 헤더 +
    indent desc 줄) 둘 다 인식. desc 가 여러 줄이면 누적.
    """
    doc = inspect.getdoc(obj)
    if not doc:
        return {}
    result: dict[str, str] = {}
    in_args = False
    current_param: str | None = None

    lines = doc.split("\n")
    i = 0
    while i < len(lines):
        stripped = lines[i].strip()

        # google-style 진입
        if stripped in ("Args:", "Parameters:", "인자:"):
            in_args = True
            current_param = None
            i += 1
            continue
        # numpy-style 진입: "Parameters" 단독 + 다음줄 underline
        if stripped in ("Args", "Parameters", "인자") and i + 1 < len(lines) and _isUnderline(lines[i + 1]):
            in_args = True
            current_param = None
            i += 2
            continue

        if not in_args:
            i += 1
            continue

        # 다른 섹션 진입 → in_args 종료
        if stripped in _DOCSTRING_SECTIONS and stripped not in (
            "Args:",
            "Parameters:",
            "인자:",
            "Args",
            "Parameters",
            "인자",
        ):
            in_args = False
            current_param = None
            i += 1
            continue
        # underline 단독줄
        if _isUnderline(stripped):
            i += 1
            continue
        if not stripped:
            i += 1
            continue

        # numpy-style 파라미터 헤더: "ratioName : str" 또는 "ratioName : {'a','b'}, default 'a'"
        if " : " in stripped and not stripped.startswith(("-", "*")):
            head, _ = stripped.split(" : ", 1)
            head = head.strip()
            if head.isidentifier():
                result[head] = ""
                current_param = head
                i += 1
                continue
        # google-style: "param: desc" 또는 "param (type): desc"
        if ":" in stripped and not stripped.startswith(("-", "*")):
            head, rest = stripped.split(":", 1)
            head = head.strip().split("(")[0].strip()
            if head.isidentifier():
                result[head] = rest.strip()
                current_param = head
                i += 1
                continue

        # indent 줄 — current_param desc 누적
        if current_param:
            sep = " " if result[current_param] else ""
            result[current_param] += sep + stripped
        i += 1

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
