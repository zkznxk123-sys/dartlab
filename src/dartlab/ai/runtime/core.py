"""AI 분석 통합 오케스트레이터 — tool calling 기반 순수 스트리밍.

dartlab.ask(), server UI, CLI가 모두 이 코어를 소비한다.
동기 제너레이터로 AnalysisEvent를 생산하며, 소비자가 형식(SSE/텍스트/제너레이터)을 결정.

구조::

    질문 → ContextBuilder → 시스템 프롬프트 조립
         → streamWithTools (LLM tool call ↔ 엔진 실행 루프) → 최종 텍스트
"""

from __future__ import annotations

import concurrent.futures
import dataclasses
import logging
import os
import re
import sqlite3
import time
from typing import Any, Generator

log = logging.getLogger(__name__)

from dartlab.ai.runtime.events import AnalysisEvent

# ── company=None 사전 종목 검색 ───────────────────────────

_COMPARE_SPLIT_RE = re.compile(r"(랑|와|과|이랑|하고|vs\.?|VS\.?|versus)", re.IGNORECASE)


def _detectCompanyNames(question: str) -> list[str]:
    """질문에서 종목명/종목코드 후보를 추출."""
    parts = _COMPARE_SPLIT_RE.split(question)
    candidates: list[str] = []
    for p in parts:
        p = p.strip()
        if not p or _COMPARE_SPLIT_RE.fullmatch(p):
            continue
        cleaned = re.sub(r"\s*(비교|분석|알려|설명|해줘|해주세요|해봐|좀).*$", "", p).strip()
        if cleaned and len(cleaned) >= 2:
            candidates.append(cleaned)
    return candidates[:4]


def _searchCompanyCodes(question: str) -> str:
    """질문에서 종목명을 추출하고 dartlab.searchName()으로 종목코드를 사전 확인."""
    candidates = _detectCompanyNames(question)
    if not candidates:
        return ""

    results: list[str] = []
    try:
        import dartlab

        for name in candidates:
            try:
                df = dartlab.searchName(name)
                if df is not None and len(df) > 0:
                    row = df.row(0, named=True)
                    corpName = row.get("corp_name", row.get("회사명", name))
                    stockCode = row.get("stock_code", row.get("종목코드", ""))
                    if stockCode:
                        results.append(f"- {corpName}: 종목코드 **{stockCode}**")
            except (FileNotFoundError, OSError, RuntimeError, TypeError, ValueError):
                continue
    except ImportError:
        return ""

    if not results:
        return ""

    body = "\n".join(results)
    return (
        '<external-data source="company-search">\n'
        "## 사전 종목코드 확인 결과\n"
        "아래 종목코드가 확인되었습니다. 코드 작성 시 이 코드를 사용하세요:\n"
        f"{body}\n"
        "</external-data>"
    )


# ── 외부 검색 Pre-Grounding ──────────────────────────────

_SEARCH_TRIGGER_KEYWORDS = (
    "최근",
    "시장",
    "이슈",
    "동향",
    "전망",
    "뉴스",
    "소식",
    "올해",
    "지금",
    "현재",
    "요즘",
    "실적발표",
    "규제",
    "금리",
    "환율",
    "유가",
    "반도체",
    "AI",
    "인공지능",
    "트렌드",
    "업황",
    "산업",
    "정책",
)


def _needsExternalSearch(question: str) -> bool:
    """질문에 외부 검색이 필요한 키워드가 포함되어 있는지 판단."""
    q = question.lower()
    return any(kw.lower() in q for kw in _SEARCH_TRIGGER_KEYWORDS)


def _preGroundDisclosure(stockCode: str | None = None) -> str:
    """companyProfile에서 해당 종목의 공시 프로필을 추출하여 주입."""
    if not stockCode:
        return ""
    try:
        from dartlab.core.search.derived import loadProfile

        row = loadProfile(stockCode)
    except (ImportError, FileNotFoundError, OSError):
        return ""
    if row is None:
        return ""

    return (
        '<external-data source="disclosure-brief">\n'
        "## 공시 프로필 (자동 조회)\n"
        f"- 총 공시: {row['total_filings']}건 ({row['first_dt']}~{row['last_dt']})\n"
        f"- 주요 유형: {row['top3_summary']}\n"
        f"- 공시 속도: {row['velocity_text']}\n"
        f"- 특이사항: {row['rare_text']}\n"
        "</external-data>"
    )


def _gatherInsightHints(stock_id: str, company: Any | None) -> str:
    """KnowledgeDB 인사이트 + 동종업계 패턴 → 단일 텍스트 블록.

    P1-1 백그라운드 thread 에서 호출 가능. 실패 시 빈 문자열.
    """
    try:
        from dartlab.ai.persistence import KnowledgeDB

        db = KnowledgeDB.get()
        # blog source 우선 (검증된 고품질 경험)
        insight = db.get_insight(stock_id, source="blog")
        if not insight:
            insight = db.get_insight(stock_id)
    except (ImportError, OSError):
        return ""

    if insight:
        try:
            import time as _t

            expired_tag = ""
            if insight.expires_at and _t.time() > insight.expires_at:
                expired_tag = " (90일+ 전 분석, 업데이트 필요)"
            strengths_str = ", ".join(insight.strengths[:3]) if insight.strengths else ""
            weaknesses_str = ", ".join(insight.weaknesses[:3]) if insight.weaknesses else ""
            text = f"## 이전 분석 인사이트{expired_tag}\n서사: {insight.narrative[:300]}\n"
            if strengths_str:
                text += f"강점: {strengths_str}\n"
            if weaknesses_str:
                text += f"약점: {weaknesses_str}\n"
            if insight.source == "blog":
                text += "이 기업의 dartlab 블로그 상세 분석이 있다. 응답 마지막에 블로그 링크를 안내하라.\n"
            text += "참고하되 최신 데이터로 자기 판단하라."
            return text
        except (AttributeError, TypeError):
            return ""

    if company is None:
        return ""
    sector = getattr(company, "sector", None) or getattr(company, "sectorName", None) or ""
    if not sector:
        return ""
    try:
        sector_insights = db.get_sector_insights(sector, limit=2)
    except (OSError, sqlite3.Error):
        return ""
    if not sector_insights:
        return ""
    lines = [f"## 동종업계 분석 패턴 참고 ({sector})"]
    for si in sector_insights:
        lines.append(f"- {si.stock_code}: {si.narrative[:150]}")
    return "\n".join(lines)


def _preGroundSearch(
    question: str,
    stockCode: str | None = None,
    corpName: str | None = None,
) -> str:
    """질문 기반 자동 검색 — 결과를 user 컨텍스트에 주입할 텍스트로 반환."""
    try:
        from dartlab.gather.search import formatResults, newsSearch, searchAvailable, webSearch
    except ImportError:
        return ""

    avail = searchAvailable()
    if not avail["any"]:
        return ""

    # 검색 쿼리 구성: 종목명이 있으면 포함
    baseQuery = question[:100]
    if corpName:
        baseQuery = f"{corpName} {baseQuery}"

    try:
        results = newsSearch(baseQuery, maxResults=5, days=7)
        if not results:
            results = webSearch(baseQuery, maxResults=5, days=7)
    except (OSError, RuntimeError, TimeoutError, ValueError):
        return ""

    if not results:
        return ""

    formatted = formatResults(results, maxChars=2000)
    return (
        '<external-data source="web-search">\n'
        "## 관련 최신 정보 (자동 검색)\n"
        "아래는 질문과 관련된 최신 검색 결과입니다. 참고하되, "
        "출처(URL)를 인용하고, 검색 결과만으로 판단하지 마세요.\n\n"
        f"{formatted}\n"
        "</external-data>"
    )


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

### 주요 도구 (11종)

| 도구 | 용도 |
|---|---|
| `analysis` | 6막 인과 구조 기반 재무분석 (14축: 수익성/성장성/안정성/현금흐름/비용구조/자본배분 …). dict 반환. `overrides` 로 가정 재계산. |
| `show` | 재무제표/주석/공시 원본 DataFrame. IS/BS/CF + inventory/borrowings/dividend 등. **analysis 결과 검증용 필수 도구**. |
| `select` | show 의 행/열 필터. 계정 한두 개만 뽑을 때. |
| `scan` | 전종목 횡단 비교 (15축). growth/profitability/liquidity 등 시장 전체에서 누가 높은지. |
| `macro` | 시장 매크로 (사이클/금리/자산/심리/유동성 …). Company 불필요. |
| `credit` | 신용평가 20단계 (AAA~D). 7축 + 종합등급. |
| `gather` | 주가/뉴스/수급/외생변수. flow 는 KR 전용. |
| `search` | DART 공시 검색 (제목형/본문형). |
| `review` | 종합 보고서 (11종 타입). **느림(60~80초)** — 축 조합으로 대체 가능하면 analysis 우선. |
| `pythonExec` | [escape hatch] 위 도구로 못 풀 때만. 커스텀 비율/override 이외 조합/특이 계산. 단순 조회는 이 도구 쓰지 마라. |

{env_block}

## 도구 연쇄 원칙 — 이게 "적극적 분석가"의 뜻이다

1. **한 축만 보고 끝내지 마라.** 수익성 분석 질문이어도 수익성만 보면 표면이다. 원인까지 파고들어라: 수익성 → 비용구조 → 수익구조/부문매출 → 업종 위치 (scan) → 이익품질(현금전환) 까지. **분석당 tool 3~5회가 정상.**
2. **엔진 결과를 의심하라.** analysis 가 "OPM 13%" 라고 말하면, `show` 로 IS 원본을 꺼내서 영업이익÷매출로 **직접 계산해서 일치하는지 확인하라.** 일치 안 하면 원본을 믿고 불일치를 언급하라.
3. **가정이 비현실적이면 overrides 로 재호출하라.** 가치평가가 WACC 18% 를 쓰면 `analysis(axis="가치평가", overrides={{"wacc": 9.0}})` 로 현실적 값에서 재계산 → 엔진 결과와 비교.
4. **인과를 추적하라.** 마진이 떨어졌으면 매출 감소인지 비용 증가인지. 6막 인과: 사업이해 → 수익성 → 현금전환 → 안정성 → 자본배분 → 전망. 앞 막이 뒷 막의 원인.
5. **tool error 는 traceback 을 읽고 진단하라.** 같은 인자로 반복하지 마라. enum 이 틀렸으면 schema 의 허용값을 확인하고 바꿔서 호출.

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
    market: str = "KR",
    hasCompany: bool = False,
    stockCode: str | None = None,
    corpName: str | None = None,
    templateText: str | None = None,
) -> tuple[str, str]:
    """시스템 프롬프트를 정적/동적으로 분리 반환.

    Claude Code의 SYSTEM_PROMPT_DYNAMIC_BOUNDARY 패턴 흡수:
    정적 부분은 캐시 가능(cache_control), 동적 부분은 매 요청 변동.

    Returns:
        (static_part, dynamic_part)
        - static_part: _SYSTEM_PROMPT + env_block 치환 결과 (세션 내 동일, 캐시 대상)
        - dynamic_part: EDGAR 보충 + 사용자 템플릿 (요청마다 변동 가능)
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

    # 동적: EDGAR 보충 + CAPABILITIES 레퍼런스 + 사용자 템플릿
    dynamic_parts: list[str] = []
    if market == "US":
        dynamic_parts.append(_EDGAR_SUPPLEMENT)
    # CAPABILITIES에서 전체 API 가이드 자동 주입
    caps_ref = _buildCapabilitiesReference()
    if caps_ref:
        dynamic_parts.append(caps_ref)
    if templateText:
        dynamic_parts.append(f"\n## 사용자 분석 템플릿 (이 지시를 반드시 따르라)\n\n{templateText}")

    return static_part, "\n".join(dynamic_parts)


def _buildSystemPrompt(
    config_: Any,
    *,
    market: str = "KR",
    hasCompany: bool = False,
    stockCode: str | None = None,
    corpName: str | None = None,
    templateText: str | None = None,
) -> str:
    """시스템 프롬프트 조립 — 하위 호환 래퍼."""
    static, dynamic = _buildSystemPromptParts(
        config_,
        market=market,
        hasCompany=hasCompany,
        stockCode=stockCode,
        corpName=corpName,
        templateText=templateText,
    )
    return static + dynamic


# ── 통합 오케스트레이터 ──────────────────────────────────


def analyze(
    company: Any | None,
    question: str,
    *,
    # LLM 설정
    provider: str | None = None,
    role: str | None = None,
    model: str | None = None,
    api_key: str | None = None,
    base_url: str | None = None,
    include: list[str] | None = None,
    exclude: list[str] | None = None,
    # 멀티컴퍼니 비교 지원
    companies: list[Any] | None = None,
    # 활성 파라미터
    max_turns: int = 5,
    reflect: bool = False,
    report_mode: bool = False,
    history: list | None = None,
    history_messages: list[dict] | None = None,
    conversation_meta: dict | None = None,
    emit_system_prompt: bool = True,
    # 하위호환 deprecated 파라미터 (내부적으로 무시) — kwargs 로 흡수됨
    # 종목 힌트 (서버가 resolve하지 않음 — AI가 참고만)
    company_hint: str | None = None,
    # 템플릿
    _templateName: str | None = None,
    _templateText: str | None = None,
    # 추가 LLMConfig overrides
    **kwargs: Any,
) -> Generator[AnalysisEvent, None, None]:
    """AI 분석 이벤트 스트림 생산.

    3단계 구조:
        1. Config 해석 + Meta 이벤트
        2. CAPABILITIES 검색 → 시스템 프롬프트 조립
        3. LLM 스트리밍 + 코드블록 자동 실행 → chunk 이벤트

    로그: ``dartlab.askLog = True``로 설정하면 data/ask_logs/에 세션별 JSONL 저장.
    """
    # ── ask 로그 초기화 ──
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
            _stock = getattr(company, "stockCode", getattr(company, "ticker", "unknown")) if company else "none"
            _logPath = logDir / f"{ts}_{_stock}.jsonl"
            _logFile = open(_logPath, "w", encoding="utf-8")  # noqa: SIM115
            # 첫 줄: 질문
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
                company,
                question,
                provider=provider,
                role=role,
                model=model,
                api_key=api_key,
                base_url=base_url,
                history=history,
                history_messages=history_messages,
                conversation_meta=conversation_meta,
                emit_system_prompt=emit_system_prompt,
                _full_response_parts=full_response_parts,
                _templateName=_templateName,
                _templateText=_templateText,
                company_hint=company_hint,
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
    company: Any | None,
    question: str,
    *,
    provider: str | None,
    role: str | None,
    model: str | None,
    api_key: str | None,
    base_url: str | None,
    history: list | None,
    history_messages: list[dict] | None,
    conversation_meta: dict | None,
    emit_system_prompt: bool,
    _full_response_parts: list[str],
    _templateName: str | None = None,
    _templateText: str | None = None,
    company_hint: str | None = None,
    **kwargs: Any,
) -> Generator[AnalysisEvent, None, None]:
    """analyze() 본체 — tool calling 단일 경로."""

    # ── 1. Config 해석 + Meta 이벤트 ──
    config_ = _resolveAnalysisConfig(provider, role, model, api_key, base_url, **kwargs)

    corp_name = getattr(company, "corpName", "Unknown") if company else None
    stock_id = getattr(company, "stockCode", getattr(company, "ticker", "")) if company else None

    meta = conversation_meta or {}
    if corp_name:
        meta.setdefault("company", corp_name)
    if stock_id:
        meta.setdefault("stockCode", stock_id)
    if company is not None:
        _dataDate = _extract_data_date(company)
        if _dataDate:
            meta.setdefault("dataDate", _dataDate)
    yield AnalysisEvent("meta", meta)

    # ── P1-1: ground 데이터 백그라운드 fire ──
    # 3개 호출 (disclosure / 외부검색 / KnowledgeDB 인사이트) 을 병렬 thread 로 시작.
    # 동기 작업 (provider/prompt/few-shot/route 등) 과 오버랩 → 첫 토큰 지연 단축.
    _ground_executor: concurrent.futures.ThreadPoolExecutor | None = None
    _f_disclosure: concurrent.futures.Future | None = None
    _f_search: concurrent.futures.Future | None = None
    _f_insight: concurrent.futures.Future | None = None

    if stock_id:
        _ground_executor = concurrent.futures.ThreadPoolExecutor(max_workers=3, thread_name_prefix="dl-ground")
        _f_disclosure = _ground_executor.submit(_preGroundDisclosure, stockCode=stock_id)
        if _needsExternalSearch(question):
            _f_search = _ground_executor.submit(_preGroundSearch, question, stockCode=stock_id, corpName=corp_name)
        _f_insight = _ground_executor.submit(_gatherInsightHints, stock_id, company)

    # ── 2. LLM provider 생성 (캐시 경계 판단에 필요) ──
    from dartlab.ai.providers import create_provider

    llm = create_provider(config_)

    # ── 3. 시스템 프롬프트 조립 (캐시 경계 적용) ──
    company_market = getattr(company, "market", "KR") if company else "KR"
    # 템플릿 텍스트: 직접 전달된 _templateText 우선, 없으면 _templateName으로 로드
    if _templateText is None and _templateName:
        from dartlab.ai.patterns import get_template

        _templateText = get_template(_templateName)

    # tool calling 단일 프롬프트 — coding mode 분기 제거
    # (코드 작성 요청도 pythonExec tool 로 처리됨)
    static_prompt, dynamic_prompt = _buildSystemPromptParts(
        config_,
        market=company_market,
        hasCompany=company is not None,
        stockCode=stock_id,
        corpName=corp_name,
        templateText=_templateText,
    )

    # 캐시 경계: 정적 부분에 cache_control 마커 삽입 (Claude 네이티브만)
    if llm.supports_cache_control and static_prompt:
        system_content: str | list[dict] = [
            {"type": "text", "text": static_prompt, "cache_control": {"type": "ephemeral"}},
        ]
        if dynamic_prompt:
            system_content.append({"type": "text", "text": dynamic_prompt})
    else:
        system_content = static_prompt + dynamic_prompt

    system_prompt = static_prompt + dynamic_prompt  # emit/로깅용 플랫 문자열

    # company=None이면 종목명 사전 검색 (AI 자율 판단)
    prefetchText = ""
    if company is None:
        prefetchText = _searchCompanyCodes(question)
    # company_hint: 서버/UI가 전달한 종목 힌트 (AI가 참고 여부를 자율 판단)
    companyHintText = ""
    if company is None and company_hint:
        companyHintText = (
            f'<hint source="user-context">사용자가 "{company_hint}" 종목을 지정했습니다. '
            "이 종목이 질문과 관련 있다고 판단되면 활용하세요. "
            "시장/매크로/일반 질문이면 무시하세요.</hint>"
        )

    if emit_system_prompt:
        yield AnalysisEvent("system_prompt", {"text": system_prompt})

    # ── Messages 조립 ──
    messages: list[dict] = [{"role": "system", "content": system_content}]

    # 히스토리 주입
    effective_history = _buildHistoryMessages(history, history_messages)
    if effective_history:
        messages.extend(effective_history)

    # 메모리 (세션 간) — 질문 이력만 참조, 수치/요약은 제외 (코드 실행 유도)
    memoryHints = ""
    if stock_id:
        try:
            from dartlab.ai.memory.store import getMemory

            records = getMemory().recallForStock(stock_id, limit=3)
            if records:
                import datetime

                hints = []
                for r in records:
                    dt = datetime.datetime.fromtimestamp(r.timestamp).strftime("%Y-%m-%d")
                    hints.append(f"- {dt}: {r.question} ({r.questionType})")
                memoryHints = "## 이전 질문 이력\n" + "\n".join(hints)
        except (ImportError, OSError, sqlite3.Error):
            pass

    # user 메시지 조립
    userParts: list[str] = []
    if corp_name and stock_id:
        userParts.append(f"분석 대상: {corp_name} (종목코드: {stock_id})")
    if companyHintText:
        userParts.append(companyHintText)
    if prefetchText:
        userParts.append(prefetchText)

    # ── P1-1: 백그라운드 ground future 회수 (deadline 기반) ──
    # 동기 fallback 모드면 직접 호출, 아니면 future.result(timeout=remaining).
    _ground_timeout = float(os.environ.get("DARTLAB_PREGROUND_TIMEOUT", "1.5"))

    def _safe_future_result(fut: concurrent.futures.Future | None, deadline: float) -> Any:
        if fut is None:
            return None
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            return None
        try:
            return fut.result(timeout=remaining)
        except (concurrent.futures.TimeoutError, Exception):  # noqa: BLE001
            return None

    _deadline = time.monotonic() + _ground_timeout
    disclosureBrief = _safe_future_result(_f_disclosure, _deadline) or ""
    groundingText = _safe_future_result(_f_search, _deadline) or ""
    insightHints = _safe_future_result(_f_insight, _deadline) or ""
    # executor 정리 — wait=False 로 timeout 된 future 는 백그라운드에서 계속 진행
    if _ground_executor is not None:
        _ground_executor.shutdown(wait=False)

    # ── ContextBuilder (기본 경로) ──
    # ACE (arxiv.org/abs/2510.04618) + analysis calc selector + graph traversal.
    # A/B 검증 완료: +31.6% 응답 풍부도, 10/10 성공, 에러 0.
    # DARTLAB_CONTEXT_V1=1 로 legacy 강제 가능 (디버깅용).
    _use_legacy = os.environ.get("DARTLAB_CONTEXT_V1") == "1"
    if not _use_legacy:
        try:
            from dartlab.ai.context import ContextBuilder

            _bundle = ContextBuilder(
                question=question,
                company=company,
                provider=getattr(config_, "provider", None),
            ).build()
            for _text in _bundle.toUserParts():
                if _text and _text not in userParts:
                    userParts.append(_text)
            log.debug(
                "context: intent=%s parts=%d tokens=%d dropped=%s",
                _bundle.intent,
                len(_bundle.parts),
                _bundle.totalTokens,
                _bundle.droppedKeys,
            )
        except Exception:  # noqa: BLE001 — ContextBuilder 실패 시 legacy fallback
            log.exception("ContextBuilder failed, falling back to legacy")
            _use_legacy = True

    if _use_legacy:
        if disclosureBrief:
            userParts.append(disclosureBrief)
        if groundingText:
            userParts.append(groundingText)
        if memoryHints:
            userParts.append(memoryHints)
        if insightHints:
            userParts.append(insightHints)
    userParts.append(f"질문: {question}")
    userContent = "\n\n---\n\n".join(userParts)
    messages.append({"role": "user", "content": userContent})

    # ── 4. LLM tool calling 루프 (Claude Code 방식) ──
    # legacy exec 루프 대체 — 스키마 enum 으로 KeyError 구조적 제거.
    from dartlab.ai.runtime.toolLoop import streamWithTools

    for item in streamWithTools(llm, messages):
        if isinstance(item, AnalysisEvent):
            yield item
        else:
            _full_response_parts.append(item)
            yield AnalysisEvent("chunk", {"text": item})

    # ── 분석 메모리 저장 + 인사이트 갱신 ──
    # R21-4: stock_id 없는 general 질문도 executions 에 저장 (general 추적용)
    if _full_response_parts:
        try:
            from dartlab.ai.memory.store import getMemory
            from dartlab.ai.memory.summarizer import extractGrade, summarizeResponse

            _fullText = "".join(_full_response_parts)
            _mem = getMemory()
            _mem.saveAnalysis(
                stockCode=stock_id or "",  # general 질문은 빈 문자열
                question=question[:200],
                questionType="analysis",
                resultSummary=summarizeResponse(_fullText),
                grade=extractGrade(_fullText),
            )
        except (ImportError, OSError, sqlite3.Error):
            pass

        # 자기성장: stock_id 있고 응답이 충분할 때만 인사이트 갱신
        if stock_id and len("".join(_full_response_parts)) > 500:
            try:
                _updateInsightFromResponse(stock_id, "".join(_full_response_parts), company)
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
