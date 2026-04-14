"""AI tool JSON Schema 생성기.

dartlab 공개 API를 LLM tool calling 규격 (OpenAI function calling 호환) 으로 변환.
각 엔진의 spec.py 메타데이터에서 axis/topic enum 을 동적 추출 → 드리프트 방지.
"""

from __future__ import annotations


# ── 정적 enum 소스 ──────────────────────────────────────────
# 동적 import 로 순환참조 방지. 모듈 로딩이 늦어도 registry bootstrap 시점에는 안전.


def _scanAxes() -> list[str]:
    from dartlab.scan.spec import buildSpec

    return list(buildSpec()["summary"].keys())


def _macroAxes() -> list[str]:
    from dartlab.macro.spec import SPEC

    return list(SPEC["axes"].keys())


def _creditAxes() -> list[str]:
    # credit.__init__ 에서 _CREDIT_AXES 노출. 실패 시 스펙상 7축 + grade fallback.
    try:
        from dartlab.credit import _CREDIT_AXES  # type: ignore[attr-defined]

        return list(_CREDIT_AXES.keys())
    except (ImportError, AttributeError):
        return [
            "repayment",
            "leverage",
            "liquidity",
            "cashflow",
            "business",
            "reliability",
            "disclosure",
            "grade",
        ]


def _showTopics() -> list[str]:
    """show tool 의 topic enum.

    3개 소스 합집합:
      - 재무제표: IS/BS/CF/CIS/SCE + ratios/ratioSeries
      - docs topic: TOPIC_KEYWORDS 33개
      - finance notes: inventory/borrowings/tangibleAsset 등 12개는 TOPIC_KEYWORDS 에 이미 포함
    """
    from dartlab.core.docs.topicGraph import TOPIC_KEYWORDS

    financeTopics = ["IS", "BS", "CF", "CIS", "SCE", "ratios", "ratioSeries"]
    # 재무제표 주석 (12종, ops/company.md)
    notesTopics = [
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
    docsTopics = list(TOPIC_KEYWORDS.keys())
    seen: set[str] = set()
    result: list[str] = []
    for t in financeTopics + notesTopics + docsTopics:
        if t not in seen:
            seen.add(t)
            result.append(t)
    return result


def _analysisAxes() -> list[str]:
    # c.analysis() 가이드 DataFrame 기반 14축. 동적 추출이 안전하지만 부트스트랩
    # 시점에 Company 로드가 무거워 정적 fallback 유지 (ops/analysis.md 기준).
    return [
        "수익구조",
        "자금조달",
        "자산구조",
        "현금흐름",
        "수익성",
        "성장성",
        "안정성",
        "효율성",
        "종합평가",
        "이익품질",
        "비용구조",
        "자본배분",
        "투자효율",
        "재무정합성",
        "매크로민감도",
        "밸류에이션밴드",
        "가치평가",
        "매출전망",
    ]


# ── Tool Schema 정의 ────────────────────────────────────────


def buildToolSchemas() -> list[dict]:
    """OpenAI function calling 규격 tool list 반환.

    각 tool: {"type": "function", "function": {"name", "description", "parameters": JSON Schema}}
    Claude Anthropic 네이티브는 providers/claude.py::_openai_tools_to_anthropic 이 자동 변환.
    """
    return [
        _showTool(),
        _selectTool(),
        _analysisTool(),
        _scanTool(),
        _macroTool(),
        _creditTool(),
        _gatherTool(),
        _searchTool(),
        _reviewTool(),
        _pythonExecTool(),
    ]


def _fn(name: str, description: str, properties: dict, required: list[str]) -> dict:
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": description,
            "parameters": {
                "type": "object",
                "properties": properties,
                "required": required,
                "additionalProperties": False,
            },
        },
    }


def _showTool() -> dict:
    return _fn(
        name="show",
        description=(
            "기업 재무제표/공시/주석 원본 데이터를 DataFrame 으로 반환. "
            "IS/BS/CF/CIS/SCE 같은 재무제표, inventory/borrowings 같은 주석, "
            "dividend/employee 같은 report 를 모두 같은 진입점으로 조회. "
            "analysis 결과가 의심스러우면 이 tool 로 원본을 직접 검증한다."
        ),
        properties={
            "stockCode": {
                "type": "string",
                "description": "종목코드 (DART 6자리 예: '005930', EDGAR ticker 예: 'AAPL')",
            },
            "topic": {
                "type": "string",
                "enum": _showTopics(),
                "description": (
                    "조회할 topic. 재무제표: IS/BS/CF/CIS/SCE. "
                    "주석: inventory/borrowings/tangibleAsset/intangibleAsset/receivables/provisions/eps/segments/costByNature/lease/affiliates/investmentProperty. "
                    "report: dividend/employee/executive/majorShareholder 등."
                ),
            },
            "period": {
                "type": "string",
                "description": "기간 필터. 예: '2024', '2025Q3'. 생략 시 전체 기간.",
            },
            "freq": {
                "type": "string",
                "enum": ["Q", "Y"],
                "description": "분기(Q) 또는 연간(Y). 기본 Q. 연간 분석은 반드시 Y.",
            },
        },
        required=["stockCode", "topic"],
    )


def _selectTool() -> dict:
    return _fn(
        name="select",
        description=(
            "show 의 행/열 필터 버전. 특정 계정만 뽑아 비교할 때 사용. 예: 매출액 + 영업이익 두 행만, 2022~2024 기간만."
        ),
        properties={
            "stockCode": {"type": "string", "description": "종목코드"},
            "topic": {"type": "string", "enum": _showTopics(), "description": "topic (show 와 동일)"},
            "fields": {
                "type": "array",
                "items": {"type": "string"},
                "description": "계정명 리스트. 한국어/snakeId 모두 자동 인식 (예: ['매출액','영업이익'] 또는 ['sales','operating_income']).",
            },
            "period": {"type": "string", "description": "기간 필터 (선택)"},
            "freq": {"type": "string", "enum": ["Q", "Y"], "description": "분기/연간"},
        },
        required=["stockCode", "topic", "fields"],
    )


def _analysisTool() -> dict:
    return _fn(
        name="analysis",
        description=(
            "6막 인과 구조 기반 재무분석. 수익성/성장성/안정성 등 14축. "
            "dict 반환 — 수치 + history + summary. 결과를 읽어주지 말고 직접 판단하라. "
            "가정이 비현실적이면 overrides 로 재호출 (WACC, 성장률 등)."
        ),
        properties={
            "stockCode": {"type": "string", "description": "종목코드"},
            "axis": {
                "type": "string",
                "enum": _analysisAxes(),
                "description": (
                    "분석 축. 6막 매핑: "
                    "1막(수익구조/성장성), 2막(수익성/비용구조), 3막(현금흐름/이익품질), "
                    "4막(자금조달/안정성), 5막(자산구조/효율성/종합평가/자본배분/투자효율/재무정합성), "
                    "6막(매출전망/가치평가/매크로민감도/밸류에이션밴드)."
                ),
            },
            "overrides": {
                "type": "object",
                "description": (
                    "가정값 override. 가치평가: {wacc:9.0, terminalGrowth:2.5}. "
                    "매출전망: {growthRate:10.0}. 비현실적 엔진 가정 재계산용."
                ),
                "additionalProperties": True,
            },
        },
        required=["stockCode", "axis"],
    )


def _scanTool() -> dict:
    return _fn(
        name="scan",
        description=(
            "전 상장사 횡단 비교. 15축. 특정 기업 기준이 아닌 '시장 전체에서 어떤 회사가' 질문. "
            "growth 축은 매출CAGR/영업이익CAGR/순이익CAGR + 6종 패턴. "
            "반환 컬럼은 한글 (매출CAGR, 영업이익률 등)."
        ),
        properties={
            "axis": {
                "type": "string",
                "enum": _scanAxes(),
                "description": (
                    "횡단분석 축. governance/workforce/capital/debt/cashflow/audit/insider/"
                    "quality/liquidity/growth/profitability/network/account/ratio/digest"
                ),
            },
            "stockCode": {
                "type": "string",
                "description": "특정 종목 필터 (선택). 해당 종목 1행만 반환.",
            },
            "sortBy": {
                "type": "string",
                "description": "정렬 컬럼 (반환 컬럼명. 예: '매출CAGR', 'ROE').",
            },
            "descending": {
                "type": "boolean",
                "description": "내림차순 정렬 (기본 true — 상위부터).",
            },
            "limit": {
                "type": "integer",
                "description": "상위 N개 (기본 20).",
                "minimum": 1,
                "maximum": 200,
            },
        },
        required=["axis"],
    )


def _macroTool() -> dict:
    return _fn(
        name="macro",
        description=(
            "시장 레벨 매크로 분석. 사이클/금리/자산/심리/유동성/예측/위기 등 11축. "
            "Company 불필요 — 시장 전체 환경 질문용."
        ),
        properties={
            "axis": {
                "type": "string",
                "enum": _macroAxes(),
                "description": "매크로 축. summary(종합), cycle, rates, assets, sentiment, liquidity, forecast, crisis, inventory, corporate, trade",
            },
        },
        required=["axis"],
    )


def _creditTool() -> dict:
    return _fn(
        name="credit",
        description=("신용평가 20단계 등급 (AAA~D). 7축 + 종합등급. 재무건전성 질문, 채권/여신 관점에 사용."),
        properties={
            "stockCode": {"type": "string", "description": "종목코드"},
            "axis": {
                "type": "string",
                "enum": _creditAxes(),
                "description": (
                    "repayment(채무상환)/leverage(레버리지)/liquidity(유동성)/cashflow(현금흐름)/"
                    "business(사업안정성)/reliability(재무신뢰성)/disclosure(공시리스크)/grade(종합등급). "
                    "생략 시 종합."
                ),
            },
        },
        required=["stockCode"],
    )


def _gatherTool() -> dict:
    return _fn(
        name="gather",
        description=(
            "기업 외부 데이터 수집. 주가, 뉴스, 수급, 컨센서스 등. "
            "4축: price (주가 OHLCV), flow (외국인/기관 수급, KR 전용), macro (외생변수), news (뉴스)."
        ),
        properties={
            "stockCode": {"type": "string", "description": "종목코드"},
            "axis": {
                "type": "string",
                "enum": ["price", "flow", "macro", "news"],
                "description": "수집 축",
            },
        },
        required=["stockCode", "axis"],
    )


def _searchTool() -> dict:
    return _fn(
        name="search",
        description=(
            "DART 공시 검색. 제목형(유형) 또는 본문형(내용) 쿼리 지원. "
            "scope='title' 기본 (공시명/섹션제목 ngram), scope='content' 는 본문 BM25."
        ),
        properties={
            "query": {"type": "string", "description": "검색어"},
            "scope": {
                "type": "string",
                "enum": ["title", "content"],
                "description": "title=공시명/섹션제목, content=본문",
            },
            "corp": {"type": "string", "description": "종목코드 필터 (선택)"},
            "start": {"type": "string", "description": "시작일 YYYYMMDD (선택)"},
            "end": {"type": "string", "description": "종료일 YYYYMMDD (선택)"},
            "limit": {
                "type": "integer",
                "description": "상위 N개 (기본 10)",
                "minimum": 1,
                "maximum": 50,
            },
        },
        required=["query"],
    )


def _reviewTool() -> dict:
    return _fn(
        name="review",
        description=(
            "종합 보고서 조립. 11종 보고서 타입 × 7종 기업유형 템플릿. "
            "주의: review 전체 호출은 60~80초 소요. analysis 축 조합으로 대체 가능하면 그쪽 우선. "
            "단일 섹션 조회는 빠르다."
        ),
        properties={
            "stockCode": {"type": "string", "description": "종목코드"},
            "type": {
                "type": "string",
                "enum": [
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
                ],
                "description": "보고서 타입",
            },
            "section": {
                "type": "string",
                "description": "단일 섹션 조회 (예: '수익성', '현금흐름'). 지정 시 빠름.",
            },
            "template": {
                "type": "string",
                "enum": ["auto", "사이클", "프랜차이즈", "턴어라운드", "성장", "자본집약", "지주", "현금부자"],
                "description": "기업유형 템플릿 (강조 블록 조정). auto=자동 감지.",
            },
        },
        required=["stockCode"],
    )


def _pythonExecTool() -> dict:
    return _fn(
        name="pythonExec",
        description=(
            "[escape hatch] 도메인 tool (show/analysis/scan/macro/credit/gather/search/review) "
            "로 풀 수 없을 때만 사용하는 최후 수단. 커스텀 비율/override 이외 조합/특수 계산용. "
            "`dartlab`, `pl` (polars), 종목코드 지정 시 `c` (Company) 가 사용 가능. "
            "단순 조회는 이 tool 쓰지 마라 — show/scan 로 해결 가능."
        ),
        properties={
            "code": {
                "type": "string",
                "description": "실행할 Python 코드. print() 로 결과 출력. pandas 금지, polars 사용.",
            },
            "stockCode": {
                "type": "string",
                "description": "Company 바인딩용 종목코드 (선택). 지정 시 `c` 변수 자동 생성.",
            },
        },
        required=["code"],
    )
