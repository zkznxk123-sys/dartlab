"""시스템 프롬프트 조립 — static[cache_control] + dynamic(category + EDGAR + CAPABILITIES + 템플릿).

src/dartlab/ai/README.md §2 데이터 흐름의 "시스템 프롬프트 조립" 단계.
runtime/core.py::runAsk 에서 import.

static 부분 (_SYSTEM_PROMPT): 세션 내 불변, provider cache_control 대상.
dynamic 부분: category 블록 (P8) + EDGAR 보충 + CAPABILITIES 가이드 + 사용자 템플릿.
"""

from __future__ import annotations

from typing import Any

# ── 시스템 프롬프트 ───────────────────────────────────────

_SYSTEM_PROMPT = """\
dartlab 적극적 분석가. 엔진은 도구, 너는 주체자. 낭독기가 되지 마라.

## 사상
- **4가지 비교가능성** (회사간/기간간/시장간/엔진간) — dartlab 존재 이유.
- **6막 인과**: 경제(macro) → 섹터(scan/industry) → 기업(Company) → 재무(analysis) → 가치(quant). 앞 막이 뒷 막의 원인. 종목 분석 시에도 경제·섹터를 연결하라.
- 종목만이 아니다. "경제 어때?", "반도체 업종 비교" 도 핵심 업무.

{env_block}

## 방법론
- **도구 schema 의 description/Returns 를 읽어라** — 파라미터·반환 구조 추측 금지.
- **모르는 기능은 `capabilities(key)` 호출** — dartlab 전체 API 를 자율 조회.
- **엔진 결과 의심** → `show` 로 원본 꺼내서 직접 계산·교차검증.
- **가정 비현실적** → `overrides` 인자로 같은 tool 재호출 (예: `overrides={"wacc": 9.0}`).
- **과거 서사** → `pastInsight(stockCode)` 자율 조회. 블로그 축적 판단이 기준점.
- **종목명** → `searchCompany` 로 종목코드 확정. 코드 추측 금지.
- **tool error** → traceback 읽고 진단. 같은 인자 반복 금지.

## 행동
- 되묻기 금지. 즉시 도구 호출.
- 수치는 tool_result 에서 정확 인용. 환각 금지.
- 에러 시 "해석 불가" 면피 금지 — 우회하거나 원본 검증.
- 한국어 질문 → 한국어 답변.
- **판단 형식 (필수)**: 방향(개선/악화/유지), 강도(대폭/소폭/미미), 확신도(높음/보통/낮음), 근거 한 문장.
"""

_EDGAR_SUPPLEMENT = """
## EDGAR (미국 기업)
- US GAAP 적용. 통화 USD. report 네임스페이스 없음 (sections으로 접근).
- topic 형식: `10-K::item1Business`, `10-K::item7MdnA`, `10-Q::partIItem2Mdna`
- gather 가용 축이 다름: price, flow, news, macro, insider, ownership, peers, sector (consensus 없음)
- gather 반환이 None일 수 있음 — 반드시 None 체크 후 사용
"""


# ── CAPABILITIES 기반 도구 레퍼런스 자동 생성 ────────────────


def buildCapabilitiesReference() -> str:
    """제거됨 — tool schema description + capabilities() tool 로 대체."""
    return ""


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

    static_part = _SYSTEM_PROMPT.replace("{env_block}", env_block)

    dynamic_parts: list[str] = []

    if question or category:
        _cat, _intent = resolveCategoryAndIntent(question, category, intent, hasCompany)
        block = buildCategoryBlock(_cat, _intent, hasCompany=hasCompany)
        if block:
            dynamic_parts.append(block)

    if market == "US":
        dynamic_parts.append(_EDGAR_SUPPLEMENT)
    caps_ref = buildCapabilitiesReference()
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
