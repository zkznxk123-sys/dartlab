"""Story 템플릿 자동 선택 — Track H (기업유형 → 답변 양식 매핑).

LLM 이 "이 회사 어떻게 봐?" 같은 종합 분석 의도일 때 호출. 본 도구는 *추천* 도구이지
*강제 흐름* 아님 (graph 회귀 가드). agent.py 본체 노드 추가 0.

분류 신호:
- dCR 등급 (credit/engine.evaluateCompany) — BB 이하 = credit_risk, B 이하 = financial_distress.
- industry phase (industry.calcs.lifecycle) — 도입/성장 = growth, 성숙 = value, 쇠퇴 = value_decline,
  재도약 = turnaround.
- 지주사·금융사 (credit/engine 내부 분기) — holding/financial 별도.
- 사용자 question 키워드 — "가치"·"valuation" → value 강화, "신용"·"부도" → credit 강화.

반환:
- corporateType (7 enum)
- templateId — story.catalog 의 section 조합 식별자
- focusSections — list[str] (story section key)
- rationale — 한국어 한 줄
- confidence (0-100)
"""

from __future__ import annotations

from typing import Any, Literal

from dartlab.ai.contracts import Ref
from dartlab.core.confidence import baseScore

from .companyResolve import resolveCompanyOrNone
from .types import ToolResult

CorporateType = Literal[
    "growth",
    "value",
    "value_decline",
    "turnaround",
    "credit_risk",
    "financial_distress",
    "holding",
    "financial",
    "general",
]

_GROWTH_SECTIONS = ["성장성", "수익구조", "투자효율", "매출전망", "비교분석"]
_VALUE_SECTIONS = ["가치평가", "현금흐름", "이익품질", "자본배분", "비교분석"]
_VALUE_DECLINE_SECTIONS = ["수익성", "자본배분", "안정성", "가치평가", "신용평가"]
_TURNAROUND_SECTIONS = ["성장성", "이익품질", "현금흐름", "안정성", "improvementPlan"]
_CREDIT_RISK_SECTIONS = ["신용평가", "안정성", "자금조달", "현금흐름", "공시변화"]
_FINANCIAL_DISTRESS_SECTIONS = ["신용평가", "안정성", "자금조달", "공시변화", "improvementPlan"]
_HOLDING_SECTIONS = ["자본배분", "투자효율", "지배구조", "비교분석", "가치평가"]
_FINANCIAL_SECTIONS = ["수익성", "안정성", "자금조달", "신용평가", "지배구조"]
_GENERAL_SECTIONS = ["수익구조", "성장성", "수익성", "현금흐름", "가치평가"]

_TYPE_TO_SECTIONS: dict[str, list[str]] = {
    "growth": _GROWTH_SECTIONS,
    "value": _VALUE_SECTIONS,
    "value_decline": _VALUE_DECLINE_SECTIONS,
    "turnaround": _TURNAROUND_SECTIONS,
    "credit_risk": _CREDIT_RISK_SECTIONS,
    "financial_distress": _FINANCIAL_DISTRESS_SECTIONS,
    "holding": _HOLDING_SECTIONS,
    "financial": _FINANCIAL_SECTIONS,
    "general": _GENERAL_SECTIONS,
}

_QUESTION_KEYWORDS_VALUE = ("가치", "valuation", "적정주가", "intrinsic", "DCF")
_QUESTION_KEYWORDS_CREDIT = ("신용", "부도", "default", "등급", "credit")
_QUESTION_KEYWORDS_GROWTH = ("성장", "growth", "CAGR")

_DISTRESS_GRADES = {"D", "C", "CCC-", "CCC", "CCC+"}
_HIGH_YIELD_GRADES = {"BB-", "BB", "BB+", "B-", "B", "B+"}


def _classify(company: Any, question: str) -> tuple[str, str, int]:
    """기업유형 + 분류 근거 + confidence."""
    qLower = (question or "").lower()
    keywordCredit = any(kw in qLower or kw in (question or "") for kw in _QUESTION_KEYWORDS_CREDIT)
    keywordValue = any(kw in qLower or kw in (question or "") for kw in _QUESTION_KEYWORDS_VALUE)
    keywordGrowth = any(kw in qLower or kw in (question or "") for kw in _QUESTION_KEYWORDS_GROWTH)

    try:
        from dartlab.credit.engine import evaluateCompany
    except ImportError:
        evaluateCompany = None  # type: ignore[assignment]

    creditResult = None
    if company is not None and evaluateCompany is not None:
        try:
            creditResult = evaluateCompany(company, detail=False)
        except Exception:
            creditResult = None

    if isinstance(creditResult, dict):
        gradeRaw = str(creditResult.get("gradeRaw") or "")
        if gradeRaw in _DISTRESS_GRADES:
            return "financial_distress", f"dCR {gradeRaw} (부실 등급)", 90
        if gradeRaw in _HIGH_YIELD_GRADES or keywordCredit:
            return "credit_risk", f"dCR {gradeRaw} (신용 비투자등급)" if gradeRaw else "사용자 질문이 신용 중심", 80

    industryBadge: dict[str, Any] | None = None
    if company is not None:
        try:
            from .industryContext import getIndustryBadge

            industryBadge = getIndustryBadge(company)
        except Exception:
            industryBadge = None
    phase = (industryBadge or {}).get("phase") if isinstance(industryBadge, dict) else None

    if phase == "재도약":
        return "turnaround", "산업 재도약 phase (쇠퇴 후 성장 전환)", 75
    if keywordValue and phase in ("성숙", "쇠퇴"):
        return "value_decline", "사용자 가치 의도 + 성숙/쇠퇴 산업", 70
    if keywordValue:
        return "value", "사용자 가치/valuation 의도", 70
    if phase in ("도입", "성장") or keywordGrowth:
        return "growth", f"산업 phase {phase} 또는 성장 키워드", 70
    if phase == "성숙":
        return "value", "산업 성숙 phase", 65
    if phase == "쇠퇴":
        return "value_decline", "산업 쇠퇴 phase", 65
    return "general", "분류 신호 부족 — 일반 종합 분석", baseScore("llm")


def pickStoryTemplate(stockCode: str = "", question: str = "") -> ToolResult:
    """기업유형 → story section 묶음 추천.

    stockCode 없으면 question 만으로 거친 분류. dartlab Company 조회 실패 시 ``general``.
    """
    company = resolveCompanyOrNone(stockCode)
    corporateType, rationale, confidence = _classify(company, question)
    focusSections = _TYPE_TO_SECTIONS.get(corporateType, _GENERAL_SECTIONS)
    templateId = f"story.{corporateType}"
    ref = Ref(
        id=f"storyTemplate:{stockCode or 'q'}:{corporateType}",
        kind="skillRef",
        title=f"story template · {corporateType}",
        source="pickStoryTemplate",
        payload={
            "corporateType": corporateType,
            "templateId": templateId,
            "focusSections": focusSections,
            "rationale": rationale,
            "confidence": confidence,
            "confidenceMethod": "ratio",
        },
    )
    return ToolResult(
        True,
        f"{templateId} · {rationale} (focus: {', '.join(focusSections)})",
        refs=[ref],
        data={
            "corporateType": corporateType,
            "templateId": templateId,
            "focusSections": focusSections,
            "rationale": rationale,
            "confidence": confidence,
        },
    )


__all__ = ["pickStoryTemplate", "CorporateType"]
