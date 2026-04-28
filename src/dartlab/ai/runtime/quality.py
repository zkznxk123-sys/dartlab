"""AI 응답 품질 계약 — FINANCE 최종 답변 게이트의 단일 원천.

프롬프트 문구를 늘려 품질을 기대하지 않고, 런타임이 최종 답변의 최소
계약을 검사한다. 공개 API 가 아니며 `toolLoop` 와 audit 로그만 소비한다.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

QUALITY_ISSUES = (
    "missing_tool_evidence",
    "missing_numeric_table",
    "missing_reading_notes",
    "missing_judgment",
    "company_mismatch_risk",
)

_ENGINE_TOOLS = {
    "analysis",
    "show",
    "credit",
    "quant",
    "gather",
    "macro",
    "scan",
    "industry",
    "topdown",
    "pastInsight",
    "sectorInsights",
    "story",
    "capital",
    "debt",
    "governance",
    "disclosure",
    "liveFilings",
    "filings",
    "search",
    "pythonExec",
}

_JUDGMENT_WORDS = (
    "판단",
    "결론",
    "보입니다",
    "입니다",
    "필요",
    "위험",
    "양호",
    "부진",
    "강점",
    "약점",
    "경계",
    "중립",
    "매력",
)

_ANALYTIC_WORDS = (
    "분석",
    "수익성",
    "안정성",
    "현금흐름",
    "가치",
    "밸류",
    "전망",
    "어때",
    "괜찮",
    "좋",
    "나쁘",
    "비교",
    "투자",
    "찾",
    "상승",
    "오른",
    "급등",
    "수익률",
    "모멘텀",
    "랭킹",
    "상위",
)

_TABLE_RE = re.compile(r"^\|.+\|\s*$", re.MULTILINE)
_NUMBER_RE = re.compile(r"\d")


@dataclass(frozen=True)
class QualityResult:
    """품질 게이트 결과."""

    passed: bool
    issues: list[str] = field(default_factory=list)
    repairPrompt: str = ""


def evaluateFinalAnswer(
    *,
    category: str,
    question: str | None,
    answer: str,
    toolCalls: list[dict[str, Any]],
    stockCode: str | None = None,
) -> QualityResult:
    """FINANCE 최종 답변의 최소 계약을 검사한다.

    Parameters
    ----------
    category : str
        질문 범주. ``"finance"`` 만 검사 대상.
    question : str | None
        원 질문.
    answer : str
        최종 응답 텍스트.
    toolCalls : list[dict[str, Any]]
        실행된 도구 호출 목록. 각 항목은 ``name`` 과 ``arguments`` 를 가진다.
    stockCode : str | None
        사용자/UI 가 지정한 종목코드 힌트.

    Returns
    -------
    QualityResult
        passed : bool — 계약 통과 여부
        issues : list[str] — 위반 코드
        repairPrompt : str — 재작성 지시문
    """
    if category != "finance":
        return QualityResult(True, [], "")

    text = answer.strip()
    q = question or ""
    issues: list[str] = []

    if not _hasEngineEvidence(toolCalls):
        issues.append("missing_tool_evidence")

    if _requiresAnalyticShape(q, toolCalls):
        if not _hasNumericTable(text):
            issues.append("missing_numeric_table")
        if "이 표에서 읽을 포인트" not in text:
            issues.append("missing_reading_notes")
        if not _hasJudgment(text):
            issues.append("missing_judgment")

    if _requiresKrxPriceMoverComputation(q, toolCalls) and not _hasPythonComputation(toolCalls):
        if "missing_numeric_table" not in issues:
            issues.append("missing_numeric_table")

    if stockCode and _hasCompanyMismatchRisk(toolCalls, stockCode):
        issues.append("company_mismatch_risk")

    if not issues:
        return QualityResult(True, [], "")
    return QualityResult(False, issues, buildRepairPrompt(issues))


def buildRepairPrompt(issues: list[str]) -> str:
    """위반 코드 → LLM 재작성 지시문."""
    issueText = ", ".join(issues)
    return (
        "[시스템 품질 게이트] 방금 답변은 dartlab AI 응답 품질 계약을 만족하지 못했습니다.\n"
        f"위반 코드: {issueText}\n\n"
        "새 도구 호출이 필요하면 호출하고, 이미 받은 tool_result 수치를 근거로 최종 답변만 다시 작성하세요.\n"
        "필수 형식:\n"
        "1. 첫 문단: 자연스러운 한국어 판단문 1-2문장.\n"
        "2. 수치가 2개 이상이면 markdown 표.\n"
        "3. 표 뒤에 정확히 '이 표에서 읽을 포인트' 섹션과 3개 이하 bullet.\n"
        "4. tool_result 에 없는 숫자는 만들지 말고, 데이터가 없으면 없다고 말하세요.\n"
        "5. 종목 후보가 애매하면 임의로 분석하지 말고 후보 표를 먼저 제시하세요.\n"
        "6. 시장 전체 최근 상승 종목 질문은 gather('krx','close') 원본 head 표본으로 답하지 말고 "
        "pythonExec 에서 전체 DataFrame 의 첫/마지막 거래일 수익률을 계산해 정렬하세요."
    )


def _hasEngineEvidence(toolCalls: list[dict[str, Any]]) -> bool:
    return any(str(call.get("name", "")) in _ENGINE_TOOLS for call in toolCalls)


def _requiresAnalyticShape(question: str, toolCalls: list[dict[str, Any]]) -> bool:
    q = question.lower()
    if any(word.lower() in q for word in _ANALYTIC_WORDS):
        return True
    return any(str(call.get("name", "")) in {"analysis", "credit", "quant", "macro", "scan"} for call in toolCalls)


def _requiresKrxPriceMoverComputation(question: str, toolCalls: list[dict[str, Any]]) -> bool:
    q = question.lower()
    if not any(word in q for word in ("주가", "가격", "종목", "price", "stock")):
        return False
    if not any(word in q for word in ("오른", "상승", "급등", "수익률", "모멘텀", "mover", "return")):
        return False
    return any(_isKrxGatherCall(call) for call in toolCalls)


def _isKrxGatherCall(call: dict[str, Any]) -> bool:
    if str(call.get("name", "")) != "gather":
        return False
    args = call.get("arguments") or call.get("args") or {}
    return isinstance(args, dict) and str(args.get("axis", "")).lower() == "krx"


def _hasPythonComputation(toolCalls: list[dict[str, Any]]) -> bool:
    return any(str(call.get("name", "")) == "pythonExec" for call in toolCalls)


def _hasNumericTable(text: str) -> bool:
    tableLines = _TABLE_RE.findall(text)
    if len(tableLines) < 2:
        return False
    return any(_NUMBER_RE.search(line) for line in tableLines)


def _hasJudgment(text: str) -> bool:
    firstBlock = "\n".join(text.splitlines()[:5])
    return any(word in firstBlock for word in _JUDGMENT_WORDS)


def _hasCompanyMismatchRisk(toolCalls: list[dict[str, Any]], stockCode: str) -> bool:
    companyCalls = [c for c in toolCalls if str(c.get("name", "")) in _ENGINE_TOOLS - {"searchCompany"}]
    for call in companyCalls:
        args = call.get("arguments") or call.get("args") or {}
        if isinstance(args, dict) and args.get("stockCode") and str(args["stockCode"]) != stockCode:
            return True
    return False
