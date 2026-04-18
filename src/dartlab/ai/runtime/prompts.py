"""시스템 프롬프트 조립 — static[cache_control] + dynamic(category + EDGAR + CAPABILITIES + 템플릿).

src/dartlab/ai/README.md §2 데이터 흐름의 "시스템 프롬프트 조립" 단계.
runtime/core.py::runAsk 에서 import.

static 부분 (_SYSTEM_PROMPT): 세션 내 불변, provider cache_control 대상.
dynamic 부분: category 블록 (P8) + EDGAR 보충 + CAPABILITIES 가이드 + 사용자 템플릿.
"""

from __future__ import annotations

from typing import Any

# ── Layer 0: Self-Description — dartlab 이 스스로를 설명 ──


def buildSelfDescription() -> str:
    """dartlab 이 매 세션마다 자기를 동적으로 설명. 코드 바뀌면 자동 반영."""
    parts: list[str] = []

    # 1. 사상 (상수)
    parts.append(
        "dartlab 적극적 분석가. 엔진은 도구, 너는 주체자.\n"
        "사상: 4가지 비교가능성 (회사간/기간간/시장간/엔진간). "
        "6막 인과 — 경제(macro)→섹터(scan/industry)→기업(Company)→재무(analysis)→가치(quant). "
        "앞 막이 뒷 막의 원인. 종목만이 아니다."
    )

    # 2. 능력 (동적 — tool 추가 시 자동)
    try:
        from dartlab.ai.tools import buildTools

        tools = buildTools()
        parts.append(f"도구: {len(tools)}개. capabilities(key) 로 상세 조회 가능.")
    except ImportError:
        parts.append("도구: tool schema 참조.")

    # 3. 경험 (동적 — 블로그 추가 시 자동)
    try:
        from dartlab.ai.persistence import _get_db

        db = _get_db()
        if db:
            stats = db.stats()
            ins = stats.get("insights", 0)
            if ins > 0:
                parts.append(f"경험: {ins}개 기업 분석 축적. pastInsight(stockCode) 로 과거 판단 조회.")
    except (ImportError, OSError):
        pass

    # 4. 데이터 (동적 — 종목 추가 시 자동)
    try:
        from dartlab.gather.listing import getKindList

        kr = len(getKindList())
        parts.append(f"데이터: KR {kr:,}종목 + US EDGAR.")
    except (ImportError, OSError):
        parts.append("데이터: KR + US EDGAR.")

    # 5. 분석 방식 (chain-of-thought 유도)
    parts.append(
        "분석 방식: 질문을 받으면 어떤 도구를 왜 쓸지 먼저 생각하라. "
        "tool 1개로 끝내지 마라. 종목이어도 경제→섹터→과거서사→기업→원본검증 순서. "
        "엔진 결과 의심 → show 원본 교차검증. 가정 비현실적 → overrides 재호출."
    )

    return "\n".join(parts)


_EDGAR_SUPPLEMENT = """
## EDGAR (미국 기업)
- US GAAP. 통화 USD. topic: `10-K::item1Business` 형식.
- gather 반환 None 가능 — 체크 필수.
"""


_SYSTEM_PROMPT = """\
{self_description}

{env_block}

## 행동
- 되묻기 금지. 즉시 도구 호출.
- 수치는 tool_result 에서 정확 인용. 환각 금지.
- 한국어 질문 → 한국어 답변.
- 판단 형식: 방향/강도/확신도/근거 1줄.
"""


# ── 프롬프트 조립 ─────────────────────────────────────────


def buildSystemPromptParts(
    config_: Any,
    *,
    question: str | None = None,
    category: str | None = None,
    intent: str | None = None,
    market: str = "KR",
    hasCompany: bool = False,
    stockCode: str | None = None,
    corpName: str | None = None,
    templateText: str | None = None,
) -> tuple[str, str]:
    """시스템 프롬프트를 정적/동적으로 분리 반환.

    Claude Code의 SYSTEM_PROMPT_DYNAMIC_BOUNDARY 패턴 흡수:
    정적 부분은 캐시 가능(cache_control), 동적 부분은 매 요청 변동.

    Args:
        question: 사용자 질문 (category/intent 미지정 시 자동 분류)
        category: "meta" / "finance" / "out_of_scope" (외부 계산 가능)
        intent: act1_business / act2_profit / ... (외부 계산 가능)

    Returns:
        (static_part, dynamic_part)
        - static_part: _SYSTEM_PROMPT + env_block 치환 결과 (세션 내 동일, 캐시 대상)
        - dynamic_part: category 블록 + EDGAR 보충 + CAPABILITIES + 사용자 템플릿
    """
    custom = getattr(config_, "system_prompt", None)
    if custom:
        return "", custom

    if hasCompany and stockCode:
        label = f"{corpName}({stockCode})" if corpName else stockCode
        env_block = (
            f"- `c` — {label} Company 객체 (이미 생성됨. c.analysis(), c.show() 등 바로 사용)\n"
            f'- 사용자가 "이 회사", "괜찮아?", "어때?" 등으로 질문하면 {label}을 가리킨다. 되묻지 말고 바로 분석하라.'
        )
    else:
        env_block = (
            "- 종목 분석이 필요하면 `c = dartlab.Company('종목코드')`로 생성하세요\n"
            "- 종목 없이 가능: `dartlab.scan(axis)` (전종목 횡단), `dartlab.macro(axis)` (매크로), `dartlab.search(query)` (공시 검색)\n"
            "- 질문에서 종목을 감지하면 직접 Company를 생성하고 분석하라. 종목을 되묻지 마라."
        )

    self_desc = buildSelfDescription()
    static_part = _SYSTEM_PROMPT.replace("{self_description}", self_desc).replace("{env_block}", env_block)

    dynamic_parts: list[str] = []

    if question or category:
        _cat, _intent = resolveCategoryAndIntent(question, category, intent, hasCompany)
        block = buildCategoryBlock(_cat, _intent, hasCompany=hasCompany)
        if block:
            dynamic_parts.append(block)

    if market == "US":
        dynamic_parts.append(_EDGAR_SUPPLEMENT)
    caps_ref = ""  # Layer 1 (tool schema) + capabilities() tool 이 대체
    if caps_ref:
        dynamic_parts.append(caps_ref)
    if templateText:
        dynamic_parts.append(f"\n## 사용자 분석 템플릿 (이 지시를 반드시 따르라)\n\n{templateText}")

    return static_part, "\n".join(dynamic_parts)


def resolveCategoryAndIntent(
    question: str | None,
    category: str | None,
    intent: str | None,
    hasCompany: bool,
) -> tuple[str, str]:
    """category + intent 자동 분류 (인자로 지정된 값이 우선)."""
    from dartlab.ai.context.intent import classifyCategory, classifyIntent

    if not category and question:
        category = classifyCategory(question).value
    if not intent and question:
        intent = classifyIntent(question, hasCompany=hasCompany).intent.value
    return category or "finance", intent or "act_all"


# ── 범주별 프롬프트 블록 (P8 신설) ───────────────────────────

def buildCategoryBlock(category: str, intent: str, *, hasCompany: bool = False) -> str:
    """질문 범주별 최소 블록 — P8 가드 + META/OUT_OF_SCOPE 분기만."""
    if category == "out_of_scope":
        return (
            "## 질문 범주: dartlab 영역 밖\n"
            "짧게 답하되 'dartlab 전문 영역 아님' 명시. tool 호출 금지. 끝에 금융 질문 예시 3개."
        )
    if category == "meta":
        return (
            "## 질문 범주: dartlab 안내\n"
            "capabilities() 로 기능 조회 후 답하라. tool 호출 불필요. 코드 예시 1~2줄."
        )
    # FINANCE — tool 경유 필수 (P8). 구체적 조합은 AI 자율 판단.
    return (
        "## 질문 범주: 금융 분석 — tool 경유 필수\n"
        "dartlab 엔진 없이 답하면 일반 ChatGPT 와 동일. 반드시 tool 호출 후 실측 수치 인용."
    )
