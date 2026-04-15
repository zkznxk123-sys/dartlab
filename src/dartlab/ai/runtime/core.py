"""AI 분석 통합 오케스트레이터 — tool calling 기반 순수 스트리밍.

dartlab.ask(), server UI, CLI가 모두 이 코어를 소비한다.
동기 제너레이터로 AnalysisEvent를 생산하며, 소비자가 형식(SSE/텍스트/제너레이터)을 결정.

구조::

    질문 → ContextBuilder → 시스템 프롬프트 조립
         → streamWithTools (LLM tool call ↔ 엔진 실행 루프) → 최종 텍스트
"""

from __future__ import annotations

import dataclasses
import logging
import re
import sqlite3
from typing import Any, Generator

log = logging.getLogger(__name__)

from dartlab.ai.runtime.events import AnalysisEvent

# ── 데이터 신선도 추출 ────────────────────────────────────


def _extract_data_date(company: Any) -> str | None:
    """Company에서 최신 데이터 기준일을 추출한다."""
    try:
        filings = company.filings() if callable(getattr(company, "filings", None)) else None
        if filings is not None and hasattr(filings, "columns") and "date" in filings.columns:
            dates = filings["date"].drop_nulls()
            if len(dates) > 0:
                return str(dates.max())
    except (AttributeError, TypeError, KeyError):
        pass
    return None


# ── 에러 분류 ─────────────────────────────────────────────


def _classify_error(e: Exception) -> dict[str, str]:
    """예외 → {error: str, action: str} 매핑."""
    err_type = type(e).__name__
    err_str = str(e)
    err_low = err_str.lower()

    if isinstance(e, FileNotFoundError):
        return {"error": err_str, "action": "install"}
    if isinstance(e, PermissionError):
        return {"error": err_str, "action": "login"}

    # ChatGPT OAuth
    if err_type == "ChatGPTOAuthError":
        if any(kw in err_low for kw in ("token", "expire", "login")):
            return {"error": "ChatGPT 인증이 만료되었습니다. 다시 로그인해주세요.", "action": "relogin"}
        if any(kw in err_low for kw in ("rate", "limit")):
            return {"error": "ChatGPT 요청 한도에 도달했습니다. 잠시 후 다시 시도해주세요.", "action": "rate_limit"}
        return {"error": f"ChatGPT 연결 오류: {err_str}", "action": "relogin"}

    # OpenAI
    if err_type == "OpenAIError" or "api_key" in err_low:
        return {"error": "AI 설정이 필요합니다. API 키를 확인하거나 다른 provider를 선택해주세요.", "action": "config"}

    # Google Gemini 에러
    if (
        err_type in ("ServerError", "ClientError", "APIError")
        or "google" in err_type.lower()
        or "genai" in err_type.lower()
    ):
        if "503" in err_str or "unavailable" in err_low or "high demand" in err_low:
            return {"error": "Gemini 서버가 일시적으로 혼잡합니다. 잠시 후 다시 시도해주세요.", "action": "retry"}
        if "429" in err_str or "rate" in err_low or "quota" in err_low or "resource_exhausted" in err_low:
            return {"error": "Gemini 요청 한도에 도달했습니다. 잠시 후 다시 시도해주세요.", "action": "rate_limit"}
        if "401" in err_str or "403" in err_str or "unauthenticated" in err_low or "permission" in err_low:
            return {"error": "Gemini API 키가 유효하지 않습니다. 설정에서 확인해주세요.", "action": "config"}
        if "400" in err_str or "invalid" in err_low:
            return {"error": f"Gemini 요청 오류: {err_str}", "action": ""}
        return {"error": f"Gemini 연결 오류: {err_str}", "action": "retry"}

    # Ollama / 로컬 모델
    if "connection" in err_low and ("refused" in err_low or "11434" in err_low):
        return {"error": "Ollama가 실행 중이지 않습니다. ollama serve로 시작해주세요.", "action": "config"}

    # 일반 네트워크/서버 에러
    if isinstance(e, (ConnectionError, TimeoutError)):
        return {
            "error": "AI 서버에 연결할 수 없습니다. 네트워크를 확인하거나 잠시 후 다시 시도해주세요.",
            "action": "retry",
        }

    return {"error": err_str, "action": ""}


def _enrich_with_guide(result: dict[str, str], error: Exception | None = None) -> dict[str, str]:
    """에러에 guide 안내 데스크 메시지를 추가."""
    try:
        from dartlab.guide import guide

        guideMsg = guide.handleError(
            error or RuntimeError(result.get("error", "")),
            feature="ai",
        )
        result["guide"] = guideMsg
    except ImportError:
        if result.get("action") in ("config", "install", "login", "relogin"):
            try:
                from dartlab.guide.aiSetup import no_provider_message

                result["guide"] = no_provider_message()
            except ImportError:
                pass
    return result


# ── Config 해석 ──────────────────────────────────────────


def _resolveAnalysisConfig(
    provider: str | None,
    role: str | None,
    model: str | None,
    api_key: str | None,
    base_url: str | None,
    **kwargs: Any,
) -> Any:
    """Config 해석 — free provider chain, get_config, merge overrides."""
    from dartlab.ai import get_config

    if provider == "free":
        from dartlab.ai.providers.fallback import buildFreeChain

        free_chain = buildFreeChain()
        if free_chain:
            provider = free_chain[0]
        else:
            provider = None

    config_ = get_config(role=role)

    # LLMConfig 필드만 통과 — deprecated 파라미터(use_tools 등)가 kwargs로
    # 흘러들어와도 LLMConfig.merge()에 전달되지 않도록 필터링
    _LLMCONFIG_FIELDS = frozenset(f.name for f in dataclasses.fields(config_))
    llm_kwargs = {k: v for k, v in kwargs.items() if k in _LLMCONFIG_FIELDS}

    overrides = {
        k: v
        for k, v in {
            "provider": provider,
            "model": model,
            "api_key": api_key,
            "base_url": base_url,
            **llm_kwargs,
        }.items()
        if v is not None
    }
    if overrides:
        config_ = config_.merge(overrides)

    return config_


# ── 대화 상태 빌드 (history만 유지) ─────────────────────────


def _buildHistoryMessages(
    history: list | None,
    history_messages: list[dict] | None,
) -> list[dict] | None:
    """히스토리 messages 자동 빌드."""
    if history_messages is not None:
        return history_messages

    if history is None:
        return None

    from dartlab.ai.conversation.history import build_history_messages, compress_history
    from dartlab.ai.types import history_from_dicts

    light_history = history_from_dicts(history)
    compressed = compress_history(light_history)
    return build_history_messages(compressed)


# ── 시스템 프롬프트 ───────────────────────────────────────

_SYSTEM_PROMPT = """\
dartlab 을 대표하는 적극적 분석가. 엔진이 결과를 만들고 너는 그 결과를 의심하고 파고들어 직접 판단한다.
낭독기가 되지 마라. 모든 분석에 개입한다.

## 도구 사용 — 이것이 네 일 방식이다

너는 Python 을 쓰지 않는다. **JSON tool call** 로 dartlab 엔진을 호출한다. 파라미터는 schema 의 enum 을 그대로 쓴다. 추측 금지.

### 주요 도구

| 도구 | 용도 |
|---|---|
| `searchCompany` | 회사명 → 종목코드. 질문에 종목명이 있으면 **가장 먼저 호출해서 코드 확정**. |
| `analysis` | 6막 인과 구조 재무분석 (수익성/성장성/안정성/현금흐름/비용구조/자본배분 …). dict 반환. `overrides` 로 가정 재계산. |
| `show` | 재무제표/주석/공시 원본 DataFrame. IS/BS/CF + inventory/borrowings/dividend 등. **analysis 결과 검증용 필수 도구**. `fields` 지정 시 특정 계정만. |
| `scan` | 전종목 횡단 비교. growth/profitability/liquidity 등 시장 전체에서 누가 높은지. |
| `macro` | 시장 매크로 (사이클/금리/자산/심리/유동성 …). Company 불필요. |
| `credit` | 신용평가 (AAA~D 등급). 재무건전성·채무상환·레버리지·현금흐름. |
| `gather` | 주가/뉴스/수급/외생변수. flow 는 KR 전용. |
| `search` | DART 공시 원문 검색 (제목형/본문형). 종목명→코드 변환은 `searchCompany` 를 쓸 것. |
| `review` | **보고서 요청 전용** (사용자가 "보고서", "리포트" 명시할 때만). 느림(60~80초). 일반 분석에는 analysis 조합. |
| `pythonExec` | [escape hatch] 위 도구로 못 풀 때만. 커스텀 비율/override 조합 외 특이 계산. 단순 조회는 이 도구 쓰지 마라. |

{env_block}

## 도구 연쇄 원칙 — 이게 "적극적 분석가"의 뜻이다

0. **질문에 종목명이 있으면 `searchCompany` 먼저 호출**해서 종목코드를 확정하라. 예: "삼성전자 수익성" → `searchCompany(keyword="삼성전자")` → 005930. 코드를 추측하지 마라.
1. **질문 유형에 맞는 축 조합을 선택하라** (review 보고서 타입 참고 — review tool 은 호출 금지, 아래 축들을 analysis/credit/scan 으로 직접 조합).
2. **한 축만 보고 끝내지 마라.** 단일 축 질문(수익성/현금/안정성)이어도 **앞막·뒷막 연결 필수**. 원인까지 파고들어라: 수익성 → 비용구조 → 수익구조/부문매출 → 업종 위치 → 이익품질(현금전환) 까지. **분석당 tool 4~7회가 정상.**
3. **엔진 결과를 의심하라.** analysis 가 "OPM 13%" 라고 말하면, `show` 로 IS 원본을 꺼내서 영업이익÷매출로 **직접 계산해서 일치하는지 확인하라.** 일치 안 하면 원본을 믿고 불일치를 언급.
4. **가정이 비현실적이면 overrides 로 재호출하라.** tool_result 의 `_summary` 에 `[엔진가정]` 한 줄이 나오는데, 거기 WACC/사이클/window 같은 엔진 내부 값이 공개된다. 값이 비현실적이면 같은 tool 을 `overrides` 인자로 재호출해서 비교하라.
   - 형식 예시: `{"name":"analysis","arguments":{"stockCode":"005930","axis":"가치평가","overrides":{"wacc":9.0,"terminalGrowth":2.5}}}`
   - **중요**: `overrides` 는 **독립 인자**다. 절대 `sub` 문자열에 JSON 을 쑤셔 넣지 마라. `sub` 는 세부 축 이름(문자열) 전용.
   - 엔진별 키: analysis → wacc/terminalGrowth/opm/growthRates 등. credit → debtRatio/interestCoverage 등. quant → window/threshold. macro → cyclePhase.
5. **인과를 추적하라.** 마진이 떨어졌으면 매출 감소인지 비용 증가인지. 6막 인과: 사업이해 → 수익성 → 현금전환 → 안정성 → 자본배분 → 전망. 앞 막이 뒷 막의 원인.
6. **tool error 는 traceback 을 읽고 진단하라.** 같은 인자로 반복 금지. enum 오류면 schema 허용값 확인 후 재호출.

## 질문 유형별 분석 축 조합 (review 보고서 타입 참고)

| 질문 유형 | 참고 타입 | 핵심 축 조합 |
|---|---|---|
| 종합 분석 ("분석해줘", "어때?") | full | **6막 전부**: 수익구조/성장성 → 수익성/비용구조 → 현금흐름/이익품질 → 자금조달/안정성 → 자본배분/투자효율 → 가치평가/매출전망 |
| 수익성/현금/안정성 단일 축 | — | 해당 축 + **앞뒤 막 최소 1개씩** (수익성 질문 → 수익구조 + 이익품질 연결 필수) |
| 신용/여신 관점 | credit | 안정성 + 현금흐름 + 자금조달 + `credit(grade)` |
| 가치투자 | valuation | 가치평가(+overrides) + 안정성 + 현금흐름 + 자본배분 |
| 성장주 | growth | 성장성(CAGR) + 수익성(마진확장) + 투자효율(ROIC vs WACC) + 매출전망 |
| 위기 진단 | crisis | 안정성(부실지표) + 자금조달(레버리지) + 현금흐름(유동성) + credit(위험등급) |
| 감사/포렌식 | audit | 이익품질 + 재무정합성 + 공시변화(search) |
| 배당 | dividend | 자본배분(배당성향/FCF커버리지) + 현금흐름 + 안정성 |
| 지배구조 | governance | `scan(governance)` + 공시(search) + 자본배분 |
| 탑다운/매크로 | macro | `macro` 축 + 매크로민감도 + 밸류에이션밴드 |
| 보고서 요청 ("리포트", "보고서") | — | **review tool 호출 허용**. 그 외에는 축 조합으로 대체. |

**원칙**: review 의 6막 구조가 기본 골격. 단일 축 질문이라도 앞뒤 막 생략 금지.

## analysis 결과 해석 규칙 (dict 키 추측 금지)

analysis 가 반환하는 dict 의 주요 키 (tool_result 에서 이 구조로 들어온다):

| 축 | 주요 키 | history 주요 필드 |
|---|---|---|
| 수익성 | marginTrend, returnTrend, roicTree, profitabilityFlags | period, revenue, operatingMargin, netMargin, roe, roa |
| 성장성 | growthTrend, cagrComparison, growthFlags | period, revenue, revenueYoy, operatingIncomeYoy |
| 안정성 | leverageTrend, coverageTrend, distressScore, stabilityFlags | period, debtRatio, equityRatio, netDebtRatio |
| 현금흐름 | cashFlowOverview, cashQuality, cashFlowFlags | period, **ocf**, **icf**, capex, **fcf** |
| 비용구조 | costBreakdown, operatingLeverage, costStructureFlags | period, revenue, costOfSales, sga, costOfSalesRatio |
| 효율성 | turnoverTrend, efficiencyFlags | period, totalAssetTurnover, dso, dio, dpo, ccc |
| 자산구조 | assetStructure, workingCapital, capexPattern | period, totalAssets, receivables, inventory, ppe, cash |

**주의**:
- 현금흐름은 `ocf`/`icf`/`fcf` (짧은 이름). `operatingCashFlow`/`freeCashFlow` 같은 긴 키는 없다.
- Flags 타입이 축별로 다르다. 안정성은 dict, 나머지는 list.

## scan 결과 해석 규칙

scan 반환 DataFrame 은 **한글 컬럼**이다. 예:
- scan("growth") → 종목코드, 종목명, 매출액, **매출CAGR**, **영업이익CAGR**, **순이익CAGR**, 등급, 패턴
- scan("profitability") → 종목코드, 종목명, **영업이익률**, **순이익률**, **ROE**, **ROA**, 등급

적자→흑자 전환 기업은 CAGR 이 None 으로 나올 수 있다. 그 자체가 "성장 실패" 가 아니다 — 원본을 보고 판단하라.

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


def _buildCapabilitiesReference() -> str:
    """CAPABILITIES dict에서 AI용 도구 가이드를 자동 생성.

    시스템 프롬프트의 하드코딩 레퍼런스를 보충하여
    AI가 dartlab의 전체 API를 알 수 있게 한다.
    """
    try:
        from dartlab.guide._generated import CAPABILITIES
    except ImportError:
        return ""

    # AI가 실제로 코드에서 호출할 수 있는 항목만 선별
    lines = ["\n## dartlab 전체 API 가이드 (자동 생성)\n"]
    lines.append("아래는 dartlab.capabilities()에서 조회 가능한 전체 API다.")
    lines.append("시스템 프롬프트의 도구 레퍼런스에 없는 기능도 여기서 확인 가능.\n")

    for key, cap in CAPABILITIES.items():
        guide = cap.get("guide", "")
        if not guide:
            continue
        summary = cap.get("summary", "")
        lines.append(f"**{key}**: {summary}")
        # guide의 첫 3줄만 (토큰 절약)
        guide_lines = guide.strip().split("\n")[:3]
        for gl in guide_lines:
            lines.append(f"  {gl}")
        lines.append("")

    return "\n".join(lines)


# ── 프롬프트 조립 ─────────────────────────────────────────


def _buildSystemPromptParts(
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
        return "", custom  # 커스텀은 전부 동적 처리

    # 실행 환경 블록 동적 생성
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

    # 정적: _SYSTEM_PROMPT + env_block 치환 결과 (~694줄, 세션 내 동일)
    static_part = _SYSTEM_PROMPT.replace("{env_block}", env_block)

    # 동적: category 블록 (최상단) + EDGAR 보충 + CAPABILITIES 레퍼런스 + 사용자 템플릿
    dynamic_parts: list[str] = []

    # category 블록 — 질문 범주별 강제력 차별화 (P8)
    if question or category:
        _cat, _intent = _resolveCategoryAndIntent(question, category, intent, hasCompany)
        block = _buildCategoryBlock(_cat, _intent)
        if block:
            dynamic_parts.append(block)

    if market == "US":
        dynamic_parts.append(_EDGAR_SUPPLEMENT)
    # CAPABILITIES에서 전체 API 가이드 자동 주입
    caps_ref = _buildCapabilitiesReference()
    if caps_ref:
        dynamic_parts.append(caps_ref)
    if templateText:
        dynamic_parts.append(f"\n## 사용자 분석 템플릿 (이 지시를 반드시 따르라)\n\n{templateText}")

    return static_part, "\n".join(dynamic_parts)


def _resolveCategoryAndIntent(
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
    "act6_outlook": (
        "분석 유형: 전망/가치평가/매크로 · "
        "필수 조합: analysis(axis='가치평가') + macro() 또는 gather(axis='macro'). "
        "assumptions 극단값이면 overrides 재호출로 시나리오 비교."
    ),
    "compare": (
        "분석 유형: 시장 비교/랭킹 · "
        "필수 조합: scan(axis=...) 먼저 → 상위 종목 analysis 심층."
    ),
    "act_all": (
        "분석 유형: 종합 · "
        "필수 조합: 6막 순서 (수익구조 → 수익성 → 현금흐름 → 안정성 → 자본배분 → 전망). 최소 4개 축."
    ),
    "concept": (
        "분석 유형: 개념/사용법 · "
        "필수 조합: 없음 (CAPABILITIES 참조)."
    ),
}


def _buildCategoryBlock(category: str, intent: str) -> str:
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
    mandatory = _INTENT_TO_MANDATORY.get(intent, _INTENT_TO_MANDATORY["act_all"])
    return (
        "## ⚠️ 질문 범주: 금융 분석 — tool 경유 필수\n\n"
        "**이 질문은 dartlab 엔진 경유 없이 답하면 정체성 훼손 (일반 ChatGPT 답변과 동일).**\n"
        f"- {mandatory}\n"
        "- tool 없이 일반론 답변 금지. 반드시 실측 수치 + 출처(tool 결과) 인용.\n"
        "- assumptions 필드의 [엔진가정] / ⚠ flag 가 나오면 overrides 재호출로 시나리오 비교.\n"
        "- 끝에 판단 형식 (방향/강도/확신도/근거 한 줄) 필수."
    )


# ── 통합 오케스트레이터 ──────────────────────────────────


def analyze(
    question: str,
    *,
    # LLM 설정
    provider: str | None = None,
    role: str | None = None,
    model: str | None = None,
    api_key: str | None = None,
    base_url: str | None = None,
    # UI/서버가 현재 화면의 종목코드를 힌트로 전달 (선택)
    stockCode: str | None = None,
    # 대화/히스토리
    history: list | None = None,
    history_messages: list[dict] | None = None,
    conversation_meta: dict | None = None,
    emit_system_prompt: bool = True,
    reflect: bool = False,
    # 템플릿
    _templateName: str | None = None,
    _templateText: str | None = None,
    # 추가 LLMConfig overrides (kwargs 로 흡수)
    **kwargs: Any,
) -> Generator[AnalysisEvent, None, None]:
    """AI 분석 이벤트 스트림. AI 가 모든 엔진을 tool 로 자율 호출 (ops/ai.md)."""
    _logFile = None
    try:
        from dartlab import config as _cfg

        if getattr(_cfg, "askLog", False):
            import datetime
            import json
            from pathlib import Path

            logDir = Path(_cfg.dataDir) / "ask_logs"
            logDir.mkdir(parents=True, exist_ok=True)
            ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            _logPath = logDir / f"{ts}_{stockCode or 'none'}.jsonl"
            _logFile = open(_logPath, "w", encoding="utf-8")  # noqa: SIM115
            _logFile.write(json.dumps({"kind": "question", "data": {"question": question}}, ensure_ascii=False) + "\n")
    except (ImportError, OSError):
        _logFile = None

    def _emit(event: AnalysisEvent) -> AnalysisEvent:
        if _logFile is not None:
            import json

            try:
                _logFile.write(
                    json.dumps({"kind": event.kind, "data": event.data}, ensure_ascii=False, default=str) + "\n"
                )
                _logFile.flush()
            except (OSError, TypeError):
                pass
        return event

    try:
        full_response_parts: list[str] = []
        done_payload: dict[str, Any] = {}

        try:
            for ev in _analyze_inner(
                question,
                provider=provider,
                role=role,
                model=model,
                api_key=api_key,
                base_url=base_url,
                stockCode=stockCode,
                history=history,
                history_messages=history_messages,
                conversation_meta=conversation_meta,
                emit_system_prompt=emit_system_prompt,
                _full_response_parts=full_response_parts,
                _templateName=_templateName,
                _templateText=_templateText,
                **kwargs,
            ):
                yield _emit(ev)
        except Exception as e:  # noqa: BLE001 — top-level error boundary for the entire AI pipeline (LLM network/auth/parse/provider errors are unpredictable)
            yield _emit(AnalysisEvent("error", _enrich_with_guide(_classify_error(e), error=e)))

        # ── 후처리: plugin hints ──
        if question:
            from dartlab.ai.runtime.plugin_hints import (
                detect_plugin_hints,
                format_plugin_hints,
            )
            from dartlab.core.plugins import get_loaded_plugins

            loaded_names = [p.name for p in get_loaded_plugins()]
            hints = detect_plugin_hints(question, loaded_names)
            if hints:
                done_payload["pluginHints"] = hints
                hint_text = format_plugin_hints(hints)
                if hint_text:
                    done_payload["pluginHintsText"] = hint_text

        # ── Done 이벤트 ──
        yield _emit(AnalysisEvent("done", done_payload))
    finally:
        if _logFile is not None:
            _logFile.close()


def _analyze_inner(
    question: str,
    *,
    provider: str | None,
    role: str | None,
    model: str | None,
    api_key: str | None,
    base_url: str | None,
    stockCode: str | None = None,
    history: list | None,
    history_messages: list[dict] | None,
    conversation_meta: dict | None,
    emit_system_prompt: bool,
    _full_response_parts: list[str],
    _templateName: str | None = None,
    _templateText: str | None = None,
    **kwargs: Any,
) -> Generator[AnalysisEvent, None, None]:
    """analyze() 본체 — tool calling 단일 경로.

    사상 (ops/ai.md): AI 가 모든 엔진을 tool 로 자율 호출. 종목 감지 · 원본 검증 · override 전부 AI 판단.
    사용자 API 에 Company 파라미터 노출 안 함. Pre-grounding · ContextBuilder 떠먹이기 전부 제거.
    """
    config_ = _resolveAnalysisConfig(provider, role, model, api_key, base_url, **kwargs)

    corp_name: str | None = None
    company: Any | None = None
    if stockCode:
        try:
            import dartlab as _dl

            company = _dl.Company(stockCode)
            corp_name = getattr(company, "corpName", None)
        except (ImportError, AttributeError, ValueError, RuntimeError):
            company = None

    meta = conversation_meta or {}
    if corp_name:
        meta.setdefault("company", corp_name)
    if stockCode:
        meta.setdefault("stockCode", stockCode)
    if company is not None:
        _dataDate = _extract_data_date(company)
        if _dataDate:
            meta.setdefault("dataDate", _dataDate)
    yield AnalysisEvent("meta", meta)

    from dartlab.ai.providers import create_provider

    llm = create_provider(config_)

    company_market = getattr(company, "market", "KR") if company else "KR"
    if _templateText is None and _templateName:
        from dartlab.ai.patterns import get_template

        _templateText = get_template(_templateName)

    # category + intent 산출 — 시스템 프롬프트와 toolLoop 가드 모두에 전달
    from dartlab.ai.context.intent import classifyCategory, classifyIntent

    category = classifyCategory(question, stockCode=stockCode).value
    intent = classifyIntent(question, hasCompany=company is not None).intent.value

    static_prompt, dynamic_prompt = _buildSystemPromptParts(
        config_,
        question=question,
        category=category,
        intent=intent,
        market=company_market,
        hasCompany=company is not None,
        stockCode=stockCode,
        corpName=corp_name,
        templateText=_templateText,
    )

    if llm.supports_cache_control and static_prompt:
        system_content: str | list[dict] = [
            {"type": "text", "text": static_prompt, "cache_control": {"type": "ephemeral"}},
        ]
        if dynamic_prompt:
            system_content.append({"type": "text", "text": dynamic_prompt})
    else:
        system_content = static_prompt + dynamic_prompt

    system_prompt = static_prompt + dynamic_prompt

    if emit_system_prompt:
        yield AnalysisEvent("system_prompt", {"text": system_prompt})

    messages: list[dict] = [{"role": "system", "content": system_content}]

    effective_history = _buildHistoryMessages(history, history_messages)
    if effective_history:
        messages.extend(effective_history)

    # user 메시지 — 떠먹이기 없이 질문만 (+ stockCode 힌트 있으면 표시)
    userParts: list[str] = []
    if corp_name and stockCode:
        userParts.append(f"분석 대상: {corp_name} (종목코드: {stockCode})")
    userParts.append(f"질문: {question}")
    messages.append({"role": "user", "content": "\n\n---\n\n".join(userParts)})

    # ── 4. LLM tool calling 루프 (Claude Code 방식) ──
    # legacy exec 루프 대체 — 스키마 enum 으로 KeyError 구조적 제거.
    from dartlab.ai.runtime.toolLoop import streamWithTools

    for item in streamWithTools(llm, messages, category=category):
        if isinstance(item, AnalysisEvent):
            yield item
        else:
            _full_response_parts.append(item)
            yield AnalysisEvent("chunk", {"text": item})

    # ── 분석 메모리 저장 + 인사이트 갱신 ──
    # R21-4: stockCode 없는 general 질문도 executions 에 저장 (general 추적용)
    if _full_response_parts:
        try:
            from dartlab.ai.memory.store import getMemory
            from dartlab.ai.memory.summarizer import extractGrade, summarizeResponse

            _fullText = "".join(_full_response_parts)
            _mem = getMemory()
            _mem.saveAnalysis(
                stockCode=stockCode or "",  # general 질문은 빈 문자열
                question=question[:200],
                questionType="analysis",
                resultSummary=summarizeResponse(_fullText),
                grade=extractGrade(_fullText),
            )
        except (ImportError, OSError, sqlite3.Error):
            pass

        # 자기성장: stockCode 있고 응답이 충분할 때만 인사이트 갱신
        if stockCode and len("".join(_full_response_parts)) > 500:
            try:
                _updateInsightFromResponse(stockCode, "".join(_full_response_parts), company)
            except (ImportError, OSError, sqlite3.Error, AttributeError, ValueError):
                pass

        # ── ACE Curator (기본 활성) ──
        # 응답 + grade → playbook bullet 추출 → KnowledgeDB delta merge.
        # arxiv.org/abs/2510.04618
        if _full_response_parts:
            try:
                from dartlab.ai.context.intent import classifyIntent
                from dartlab.ai.context.playbook import curate
                from dartlab.ai.memory.summarizer import extractGrade

                _full = "".join(_full_response_parts)
                _intent = classifyIntent(question, hasCompany=company is not None).intent.value
                _sector = ""
                if company is not None:
                    _sector = getattr(company, "sector", None) or getattr(company, "sectorName", None) or ""
                _grade = extractGrade(_full)
                curate(
                    intent=_intent,
                    response_text=_full,
                    grade=_grade,
                    sector=str(_sector),
                    source="reflection",
                )
            except (ImportError, OSError, sqlite3.Error, AttributeError, ValueError):
                pass


# ── 자기성장 인사이트 갱신 ────────────────────────────────

# R21-5: regex 광범위화 — audit 응답 패턴이 "강점:", "약점:" 명시 적음.
# - 명시 키워드 (강점/약점/리스크 등) + 부드러운 표현 (개선/회복/우수/탄탄/감소/취약 등) 추가
# - 키워드 뒤에 콜론 없어도 그 줄 또는 그 다음 절을 매치
_STRENGTH_RE = re.compile(
    r"(?:강점|장점|긍정|양호|우수|탄탄|회복|개선|성장|확대|증가|상승|반등)[:\s은는이가\.]+([^\n]{5,120})",
)
_WEAKNESS_RE = re.compile(
    r"(?:약점|리스크|위험|부정|주의|훼손|악화|하락|감소|취약|부진|침체|압박|우려)[:\s은는이가\.]+([^\n]{5,120})",
)
_NARRATIVE_RE = re.compile(r"(?:결론|종합|요약|핵심|핵심 판단)[:\s]*(.+?)(?:\n\n|\Z)", re.DOTALL)


def _updateInsightFromResponse(
    stock_code: str,
    response_text: str,
    company: Any | None,
) -> None:
    """AI 분석 응답에서 인사이트를 추출하여 KnowledgeDB에 갱신.

    규칙 기반 regex 추출 — LLM 호출 없이 결정론적.
    """
    from dartlab.ai.persistence import KnowledgeDB

    # 강점/약점 추출
    strengths = _STRENGTH_RE.findall(response_text)
    weaknesses = _WEAKNESS_RE.findall(response_text)

    # 서사 추출
    narrative = ""
    match = _NARRATIVE_RE.search(response_text)
    if match:
        narrative = match.group(1).strip()[:500]

    # 서사가 없으면 응답 첫 200자를 서사로
    if not narrative:
        clean = re.sub(r"```[\s\S]*?```", "", response_text)  # 코드블록 제거
        clean = re.sub(r"\|.*\|", "", clean)  # 테이블 제거
        clean = clean.strip()
        if clean:
            narrative = clean[:200]

    if not narrative:
        return

    sector = ""
    if company is not None:
        sector = getattr(company, "sector", None) or getattr(company, "sectorName", None) or ""

    db = KnowledgeDB.get()
    db.save_insight(
        stock_code=stock_code,
        narrative=narrative,
        strengths=strengths[:5],
        weaknesses=weaknesses[:5],
        sector=str(sector),
        source="live",
    )
