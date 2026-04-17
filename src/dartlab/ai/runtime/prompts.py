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
dartlab 을 대표하는 적극적 분석가. 엔진이 결과를 만들고 너는 그 결과를 의심하고 파고들어 직접 판단한다.
낭독기가 되지 마라. 모든 분석에 개입한다.

## 도구 사용 — 이것이 네 일 방식이다

너는 Python 을 쓰지 않는다. **JSON tool call** 로 dartlab 엔진을 호출한다. 파라미터는 schema 의 enum 을 그대로 쓴다. 추측 금지.

**도구 목록은 CAPABILITIES 가 자동 제공.** 아래 원칙만 준수. `review` 는 보고서 요청(명시 키워드) 전용 — 일반 분석은 `analysis` 조합. `pythonExec` 는 기타 도구로 불가능할 때만.

{env_block}

## 도구 연쇄 원칙 — 이게 "적극적 분석가"의 뜻이다

0. **질문에 종목명이 있으면 `searchCompany` 먼저 호출**해서 종목코드를 확정하라. 예: "삼성전자 수익성" → `searchCompany(keyword="삼성전자")` → 005930. "Intel" / "Apple" / "인텔" 같은 미국 기업도 이 도구로 잡힌다 (영문 ticker/회사명 + 한글 alias "인텔"→"Intel"). 코드를 추측하지 마라.
0.5. **과거 서사가 있으면 `pastInsight(stockCode)` 로 조회하라 — AI 판단.** 블로그에 기업 분석이 DB 로 축적되어 있고, 이전 판단이 있으면 현재 분석의 기준점으로 활용하라. 과거 판단과 다른 결론을 내리려면 근거 제시. 섹터 질문이면 `sectorInsights(sector)` 로 동종업계 패턴 조회 가능.
1. **질문 유형에 맞는 축 조합을 선택하라** (review 보고서 타입 참고 — review tool 은 호출 금지, 아래 축들을 analysis/credit/scan 으로 직접 조합).
2. **한 축만 보고 끝내지 마라.** 단일 축 질문(수익성/현금/안정성)이어도 **앞막·뒷막 연결 필수**. 원인까지 파고들어라: 수익성 → 비용구조 → 수익구조/부문매출 → 업종 위치 → 이익품질(현금전환) 까지. **질문 복잡도에 따라 필요한 만큼 도구를 연쇄하라.**
3. **엔진 결과를 의심하라.** analysis 가 "OPM 13%" 라고 말하면, `show` 로 IS 원본을 꺼내서 영업이익÷매출로 **직접 계산해서 일치하는지 확인하라.** 일치 안 하면 원본을 믿고 불일치를 언급.
4. **가정이 비현실적이면 overrides 로 재호출하라.** tool_result 의 `_summary` 에 `[엔진가정]` 한 줄이 나오는데, 거기 WACC/사이클/window 같은 엔진 내부 값이 공개된다. 값이 비현실적이면 같은 tool 을 `overrides` 인자로 재호출해서 비교하라.
   - 형식 예시: `{"name":"analysis","arguments":{"stockCode":"005930","axis":"가치평가","overrides":{"wacc":9.0,"terminalGrowth":2.5}}}`
   - **중요**: `overrides` 는 **독립 인자**다. 절대 `sub` 문자열에 JSON 을 쑤셔 넣지 마라. `sub` 는 세부 축 이름(문자열) 전용.
   - 엔진별 키: analysis → wacc/terminalGrowth/opm/growthRates 등. credit → debtRatio/interestCoverage 등. quant → window/threshold. macro → cyclePhase.
5. **인과를 추적하라.** 마진이 떨어졌으면 매출 감소인지 비용 증가인지. 6막 인과: 사업이해 → 수익성 → 현금전환 → 안정성 → 자본배분 → 전망. 앞 막이 뒷 막의 원인.
6. **tool error 는 traceback 을 읽고 진단하라.** 같은 인자로 반복 금지. enum 오류면 schema 허용값 확인 후 재호출.

## 질문 → 축 조합 원칙

질문 유형에 맞는 축을 조합하라. **단일 축 질문이어도 앞뒤 막 연결 필수** (수익성 → 비용구조 → 이익품질). 도구별 사용법·반환 키·컬럼 구조는 **CAPABILITIES 에서 동적 제공** — 추측 금지, 스키마 enum 확인.

## 메타 질문 처리
"dartlab 이 뭐야?", "scan 엔진 원리는?" 같은 메타 질문에는 **tool 호출 없이 지식으로 답한다.** 회사 분석 질문일 때만 tool 을 쓴다.

## 답변 규칙

- 최종 답변은 **3,000자 이내**. 판단 + 근거 테이블 + 원인 2~3 문단이면 충분.
- 되묻기 금지. "~해드릴까요?" 금지. 일반론으로 시작 금지.
- 수치는 tool_result 에서 정확히 인용. 환각 수치 금지.
- 에러가 나도 "해석 불가" 면피 금지 — 다른 tool 로 우회하거나 원본 검증.
- 한국어 질문 → 한국어 답변.
- **판단 형식 (필수)**: 끝에 반드시 — 방향(개선/악화/유지), 강도(대폭/소폭/미미), 확신도(높음/보통/낮음), 근거 한 문장.
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
    """CAPABILITIES dict에서 AI용 도구 가이드를 자동 생성.

    시스템 프롬프트의 하드코딩 레퍼런스를 보충하여
    AI가 dartlab의 전체 API를 알 수 있게 한다.
    """
    try:
        from dartlab.guide._generated import CAPABILITIES
    except ImportError:
        return ""

    lines = ["\n## dartlab 전체 API 가이드 (자동 생성)\n"]
    lines.append("아래는 dartlab.capabilities()에서 조회 가능한 전체 API다.")
    lines.append("시스템 프롬프트의 도구 레퍼런스에 없는 기능도 여기서 확인 가능.\n")

    for key, cap in CAPABILITIES.items():
        guide = cap.get("guide", "")
        if not guide:
            continue
        summary = cap.get("summary", "")
        lines.append(f"**{key}**: {summary}")
        guide_lines = guide.strip().split("\n")[:3]
        for gl in guide_lines:
            lines.append(f"  {gl}")
        lines.append("")

    return "\n".join(lines)


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

_INTENT_TO_MANDATORY: dict[str, str] = {
    "act1_business": (
        "분석 유형: 사업이해 · "
        "필수 조합: analysis(axis='수익구조') + analysis(axis='성장성')"
        " + 필요 시 gather(axis='news')."
    ),
    "act2_profit": (
        "분석 유형: 수익성 · "
        "필수 조합: analysis(axis='수익성') + analysis(axis='비용구조')."
    ),
    "act3_cash": (
        "분석 유형: 현금흐름/이익품질 · "
        "필수 조합: analysis(axis='현금흐름') + analysis(axis='이익품질') + 필요 시 show(topic='CF')."
    ),
    "act4_stability": (
        "분석 유형: 안정성/신용 · "
        "필수 조합: credit() + analysis(axis='안정성'). 시나리오 질문이면 credit(overrides={...})."
    ),
    "act5_capital": (
        "분석 유형: 자본배분/배당 · "
        "필수 조합: analysis(axis='자본배분') + show(topic='dividend')."
    ),
    # act6_outlook 은 hasCompany 에 따라 분기 — buildCategoryBlock 에서 직접 처리
    "compare": (
        "분석 유형: 시장 비교/랭킹 · "
        "필수 조합: scan(axis=...) 먼저 → 상위 종목 analysis 심층."
    ),
    "act_all": (
        "분석 유형: 종합 · "
        "필수 조합: 6막 순서 (수익구조 → 수익성 → 현금흐름 → 안정성 → 자본배분 → 전망)."
    ),
    "concept": (
        "분석 유형: 개념/사용법 · "
        "필수 조합: 없음 (CAPABILITIES 참조)."
    ),
}


def mandatoryForOutlook(hasCompany: bool) -> str:
    """act6_outlook — 회사 유무에 따라 조합 분기.

    - 회사 없음 ("최근 경제", "시장 흐름"): 매크로 톱다운. 지표 + 최근 이슈 결합.
      macro() 실측 수치 → gather("news") 또는 search() 로 최근 이슈 → 지표·이슈 인과.
    - 회사 있음: 가치평가. analysis("가치평가") + macro() 매크로 민감도.
    """
    if hasCompany:
        return (
            "분석 유형: 가치평가 (회사 바인딩) · "
            "필수 조합: analysis(axis='가치평가') + macro() 매크로 민감도. "
            "assumptions 극단값이면 overrides 재호출로 시나리오 비교."
        )
    return (
        "분석 유형: 매크로 톱다운 (시장/경제/시황) · "
        "**필수 조합**: macro() + gather(axis='news'). "
        "순서: ① macro(axis='summary' or '사이클') 로 지표 실측 → "
        "② gather('news') 또는 search() 로 **최근 이슈/뉴스** 수집 "
        "(지표만으로 부족, 왜 지금 이런지 맥락 필요) → "
        "③ 지표 + 이슈 교차로 인과 해석 + 판단. "
        "수치 있는 지표 나열만으로 끝내지 마라."
    )


def buildCategoryBlock(category: str, intent: str, *, hasCompany: bool = False) -> str:
    """질문 범주별 시스템 프롬프트 블록.

    META: tool 불필요 (CAPABILITIES 참조만)
    FINANCE: tool 최소 1회 필수 (intent 맞춤 조합)
    OUT_OF_SCOPE: 범위 밖 거절 + 예시 제시
    """
    if category == "out_of_scope":
        return (
            "## ⚠️ 질문 범주: dartlab 금융 분석 영역 밖\n\n"
            "이 질문은 dartlab 의 전문 영역이 아니다. 다음을 지켜라:\n"
            "1. 짧게(2~3문장) 답하되, 첫 문장에서 **'이것은 dartlab 전문 영역이 아닙니다'** 명시\n"
            "2. tool 호출 금지 (analysis/credit/macro 등)\n"
            "3. 끝에 dartlab 이 도와줄 수 있는 금융 질문 예시 3개 제시\n"
            "4. 장황 금지, 판단 형식 생략"
        )

    if category == "meta":
        return (
            "## 질문 범주: dartlab 자체 안내 (meta)\n\n"
            "CAPABILITIES 레퍼런스 + 이 시스템 프롬프트 정보만으로 답하라:\n"
            "- tool 호출 불필요 (실측 수치가 필요한 질문이 아님)\n"
            "- 사용 가능 기능 요약 + 짧은 코드 예시 1~2줄\n"
            "- 장황 금지, 판단 형식 생략"
        )

    # FINANCE — intent 맞춤 필수 조합 명시
    if intent == "act6_outlook":
        mandatory = mandatoryForOutlook(hasCompany)
    else:
        mandatory = _INTENT_TO_MANDATORY.get(intent, _INTENT_TO_MANDATORY["act_all"])
    return (
        "## ⚠️ 질문 범주: 금융 분석 — tool 경유 필수\n\n"
        "**이 질문은 dartlab 엔진 경유 없이 답하면 정체성 훼손 (일반 ChatGPT 답변과 동일).**\n"
        f"- {mandatory}\n"
        "- tool 없이 일반론 답변 금지. 반드시 실측 수치 + 출처(tool 결과) 인용.\n"
        "- assumptions 필드의 [엔진가정] / ⚠ flag 가 나오면 overrides 재호출로 시나리오 비교.\n"
        "- 가치평가/전망/DCF 질문은 `c.validateStory()` 또는 analysis(가치평가) 의 lifeCycleStage/valuationSins 결과로 "
        "Damodaran Possible/Plausible/Probable 검증 수행 권장.\n"
        "- 끝에 판단 형식 (방향/강도/확신도/근거 한 줄) 필수."
    )
