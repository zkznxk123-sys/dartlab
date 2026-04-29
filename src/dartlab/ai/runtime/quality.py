"""AI 응답 품질 계약 — FINANCE 최종 답변 게이트의 단일 원천.

프롬프트 문구를 늘려 품질을 기대하지 않고, 런타임이 최종 답변의 최소
계약을 검사한다. 공개 API 가 아니며 `toolLoop` 와 audit 로그만 소비한다.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date
from typing import Any

from dartlab.ai.runtime.contract_graph import requiresVisualExplanation
from dartlab.ai.runtime.contracts import (
    latestDateFromToolArgs,
    resolveAnswerContracts,
    staleCutoff,
    validateToolArguments,
)

QUALITY_ISSUES = (
    "missing_tool_evidence",
    "missing_numeric_table",
    "missing_reading_notes",
    "missing_judgment",
    "company_mismatch_risk",
    "stale_date_risk",
    "partial_comparison",
    "unsupported_claim",
    "answer_table_conflict",
    "bad_tool_args",
    "weak_disclosure_analysis",
    "missing_visual_explanation",
    "unsupported_visual",
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
    "봅니다",
    "보입니다",
    "해석",
    "우위",
    "열위",
    "강합니다",
    "약합니다",
    "중립",
    "긍정",
    "부정",
    "위험",
    "필요",
    "맞습니다",
    "판단",
    "결론",
    "결과",
    "보입니다",
    "입니다",
    "봐야",
    "해석",
    "가능성",
    "필요",
    "위험",
    "양호",
    "부진",
    "강점",
    "약점",
    "경계",
    "중립",
    "매력",
    "장세",
    "집중",
    "흐름",
    "급등",
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
_DATE_RE = re.compile(r"(20\d{2})[-./년\s]*(\d{1,2})[-./월\s]*(\d{1,2})")
_PERCENT_RE = re.compile(r"[-+]?\d+(?:\.\d+)?\s*%")
_NEGATIVE_FCF_RE = re.compile(r"(FCF|잉여현금흐름)[^\n|]*(?:-\s*\d|적자)", re.IGNORECASE)
_POSITIVE_FCF_MARGIN_RE = re.compile(r"(FCF|잉여현금흐름)\s*/\s*매출[^\n-]*\d+(?:\.\d+)?\s*%", re.IGNORECASE)
_STRONG_COMPARISON_WORDS = (
    "우위",
    "더 좋",
    "더 낫",
    "선호",
    "매력",
    "앞섭",
    "강합니다",
    "뛰어납니다",
)
_MISSING_DATA_WORDS = ("데이터 미제공", "데이터 없음", "확인 불가", "미확인", "누락")
_UNSUPPORTED_CLAIM_HINTS = (
    "점유율",
    "nvidia",
    "엔비디아",
    "hbm3e",
    "수율",
    "고객사",
    "수주",
)


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
    workspace: Any | None = None,
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
    contracts = resolveAnswerContracts(q, toolCalls)
    isComparisonQuestion = "comparison" in contracts or _looksLikeComparisonQuestion(q)
    isMetaHelp = _isMetaHelpQuestion(q, toolCalls)

    if not isMetaHelp and not _hasEngineEvidence(toolCalls):
        issues.append("missing_tool_evidence")

    if validateToolArguments(question=q, toolCalls=toolCalls):
        issues.append("bad_tool_args")

    if not isMetaHelp and _requiresAnalyticShape(q, toolCalls):
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

    if "recent" in contracts and _hasStaleDateRisk(q, text, toolCalls):
        issues.append("stale_date_risk")

    if isComparisonQuestion and _hasPartialComparison(q, text, toolCalls):
        issues.append("partial_comparison")

    if _hasAnswerTableConflict(text):
        issues.append("answer_table_conflict")

    if _hasUnsupportedClaim(text, toolCalls):
        issues.append("unsupported_claim")

    if "disclosure" in contracts and _hasWeakDisclosureAnalysis(q, text, toolCalls):
        issues.append("weak_disclosure_analysis")

    if workspace is not None:
        graph = workspace.graphSummary() if hasattr(workspace, "graphSummary") else {}
        if graph and not graph.get("requiredEvidenceSatisfied", True):
            issues.append("missing_tool_evidence")
        if graph and graph.get("artifactRequired") and not graph.get("artifactSatisfied", True):
            issues.append("missing_numeric_table")
        if graph and graph.get("visualRequired") and not graph.get("visualSatisfied", True):
            issues.append("missing_visual_explanation")
        if requiresVisualExplanation(q) and not _hasVisualExplanation(text, workspace):
            issues.append("missing_visual_explanation")
        if _hasUnsupportedVisual(workspace):
            issues.append("unsupported_visual")
        if _workspaceStaleFreshness(workspace, text):
            issues.append("stale_date_risk")
        if "disclosure" in contracts and _workspaceDisclosureDepthRisk(workspace, text):
            issues.append("weak_disclosure_analysis")
        if isComparisonQuestion and _workspacePartialComparison(workspace, text):
            issues.append("partial_comparison")
        if _workspaceUnsupportedClaim(workspace):
            issues.append("unsupported_claim")

    if not issues:
        return QualityResult(True, [], "")
    return QualityResult(False, _dedupe(issues), buildRepairPrompt(_dedupe(issues)))


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
        "pythonExec 에서 전체 DataFrame 의 첫/마지막 거래일 수익률을 계산해 정렬하세요.\n"
        "7. 최근/현재 질문은 asOf, 기간, universe, metric 을 명시하고 낡은 기준일이면 한계로 고지하세요.\n"
        "8. 비교 질문은 각 대상에 같은 축의 수치가 있을 때만 강한 결론을 내리세요.\n"
        "9. 공시는 제목만 본 경우 제목 기준이라고 쓰고, 중요한 내용/영향을 단정하지 마세요."
    )


def _hasEngineEvidence(toolCalls: list[dict[str, Any]]) -> bool:
    return any(str(call.get("name", "")) in _ENGINE_TOOLS for call in toolCalls)


def _isMetaHelpQuestion(question: str, toolCalls: list[dict[str, Any]]) -> bool:
    if not any(str(call.get("name", "")) == "capabilities" for call in toolCalls):
        return False
    q = question.lower()
    return any(
        word in q
        for word in (
            "dartlab",
            "capabilities",
            "company.",
            "show",
            "analysis",
            "scan",
            "gather",
            "함수",
            "어떻게 써",
            "사용법",
            "기능",
            "할 수 있어",
        )
    )


def _looksLikeComparisonQuestion(question: str) -> bool:
    q = question.lower()
    if not any(word in q for word in ("비교", "대비", " vs ", "versus")):
        return False
    return any(word in q for word in ("와", "과", "랑", "하고", " vs ", "versus", "업종", "섹터"))


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


def _hasStaleDateRisk(question: str, text: str, toolCalls: list[dict[str, Any]]) -> bool:
    if _requiresFxEvidence(question) and not _hasFxEvidence(toolCalls):
        return True
    if _declaresDataLimit(text):
        return False
    latest = _latestDateInText(text) or latestDateFromToolArgs(toolCalls)
    if latest is None:
        return _requiresFreshStructuredData(question, toolCalls)
    if latest < staleCutoff():
        return True
    required = ("asof", "as of", "기준", "기간", "universe", "metric", "대상")
    lowered = text.lower()
    if _requiresFreshStructuredData(question, toolCalls) and not any(word in lowered for word in required):
        return True
    return False


def _hasPartialComparison(question: str, text: str, toolCalls: list[dict[str, Any]]) -> bool:
    lowered = text.lower()
    hasMissing = any(word in text for word in _MISSING_DATA_WORDS)
    hasStrongConclusion = any(word in text for word in _STRONG_COMPARISON_WORDS)
    if hasMissing and _declaresComparisonLimit(text):
        return False
    if hasMissing and hasStrongConclusion and _hasSameAxisComparisonEvidence(text, toolCalls):
        return False
    if hasMissing and hasStrongConclusion:
        return True

    searched = 0
    companyEvidence: set[str] = set()
    for call in toolCalls:
        name = str(call.get("name", ""))
        args = call.get("arguments") or call.get("args") or {}
        if name == "searchCompany":
            searched += 1
        if isinstance(args, dict) and args.get("stockCode") and name in _ENGINE_TOOLS - {"searchCompany"}:
            companyEvidence.add(str(args["stockCode"]))
    if searched >= 2 and len(companyEvidence) == 1 and hasStrongConclusion:
        return True
    return any(word in lowered for word in ("only one side", "single target only")) and hasStrongConclusion


def _hasSameAxisComparisonEvidence(text: str, toolCalls: list[dict[str, Any]]) -> bool:
    companyEvidence: set[str] = set()
    for call in toolCalls:
        name = str(call.get("name", ""))
        args = call.get("arguments") or call.get("args") or {}
        if isinstance(args, dict) and args.get("stockCode") and name in _ENGINE_TOOLS - {"searchCompany"}:
            companyEvidence.add(str(args["stockCode"]))
    if len(companyEvidence) < 2:
        return False

    for line in text.splitlines():
        if not _TABLE_RE.match(line.strip()):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 3:
            continue
        numericCells = [cell for cell in cells[1:] if _PERCENT_RE.search(cell) or re.search(r"\d", cell)]
        missingCells = [cell for cell in cells[1:] if any(word in cell for word in _MISSING_DATA_WORDS)]
        if len(numericCells) >= 2 and not missingCells:
            return True
    return False


def _hasUnsupportedClaim(text: str, toolCalls: list[dict[str, Any]]) -> bool:
    lowered = text.lower()
    if not any(hint in lowered for hint in _UNSUPPORTED_CLAIM_HINTS):
        return False
    if not _hasUnsupportedClaimAssertion(text):
        return False
    evidenceTools = {
        "pastInsight",
        "sectorInsights",
        "story",
        "search",
        "filings",
        "liveFilings",
        "disclosure",
        "gather",
        "pythonExec",
    }
    return not any(str(call.get("name", "")) in evidenceTools for call in toolCalls)


def _hasUnsupportedClaimAssertion(text: str) -> bool:
    """Return True when unsupported-claim hints are asserted, not disclosed as missing."""
    limit_terms = (
        "없어",
        "없습니다",
        "미제공",
        "미확인",
        "확인 불가",
        "포함하지 않았",
        "한계",
        "데이터가 없",
        "원문 숫자가 없어",
    )
    assertion_found = False
    for line in text.splitlines():
        lowered = line.lower()
        if not any(hint in lowered for hint in _UNSUPPORTED_CLAIM_HINTS):
            continue
        if any(term in line for term in limit_terms):
            continue
        assertion_found = True
    return assertion_found


def _hasAnswerTableConflict(text: str) -> bool:
    if _NEGATIVE_FCF_RE.search(text) and _POSITIVE_FCF_MARGIN_RE.search(text):
        return True

    tableValues: dict[str, set[str]] = {}
    nonTableLines: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if _TABLE_RE.match(stripped):
            cells = [c.strip() for c in stripped.strip("|").split("|")]
            if len(cells) >= 2 and not all(set(c) <= {"-", ":", " "} for c in cells):
                label = cells[0]
                if label.isdigit():
                    continue
                if label in {"구분", "항목", "지표"} or "플래그" in label:
                    continue
                values = {_percentKey(v) for cell in cells[1:] for v in _PERCENT_RE.findall(cell)}
                if values and label and label != "---":
                    tableValues.setdefault(label, set()).update(values)
        else:
            nonTableLines.append(line)

    for label, values in tableValues.items():
        if len(label) < 2:
            continue
        for line in nonTableLines:
            if not _lineMentionsTableLabel(line, label):
                continue
            bodyValues = {_percentKey(v) for v in _PERCENT_RE.findall(line)}
            if len(bodyValues) == 1 and not _percentValuesCovered(bodyValues, values):
                return True
    return False


def _lineMentionsTableLabel(line: str, label: str) -> bool:
    """Return True when a prose line mentions the table row label as a term.

    Korean financial labels are often short (for example "자본"). Plain substring
    matching incorrectly treats "자기자본비율" as a mention of the separate "자본"
    row, so require a non-word prefix and either a boundary or common particle
    suffix.
    """
    import re

    escaped = re.escape(label)
    particle = "은는이가을를도와과에의로"
    pattern = rf"(?<![0-9A-Za-z가-힣]){escaped}(?=$|[^0-9A-Za-z가-힣]|[{particle}](?:$|[^0-9A-Za-z가-힣]))"
    return re.search(pattern, line) is not None


def _percentKey(value: str) -> str:
    text = value.replace(" ", "").replace("%", "")
    try:
        return f"{float(text):.1f}%"
    except ValueError:
        return value.replace(" ", "")


def _percentValuesCovered(bodyValues: set[str], tableValues: set[str]) -> bool:
    if bodyValues.issubset(tableValues):
        return True
    tableNums = [_percentFloat(v) for v in tableValues]
    for body in bodyValues:
        bodyNum = _percentFloat(body)
        if bodyNum is None:
            if body not in tableValues:
                return False
            continue
        if not any(tableNum is not None and abs(bodyNum - tableNum) <= 0.15 for tableNum in tableNums):
            return False
    return True


def _percentFloat(value: str) -> float | None:
    try:
        return float(str(value).replace("%", ""))
    except ValueError:
        return None


def _hasWeakDisclosureAnalysis(question: str, text: str, toolCalls: list[dict[str, Any]]) -> bool:
    if not any(word in question for word in ("중요", "내용", "영향", "리스크", "호재", "악재")):
        return False
    hasDisclosureTool = any(
        str(call.get("name", "")) in {"search", "filings", "liveFilings", "disclosure"} for call in toolCalls
    )
    if not hasDisclosureTool:
        return False
    if "제목 기준" in text and not any(word in text for word in ("본문", "원문", "영향", "유형", "내용 확인")):
        return True
    if "중요" in text and not any(word in text for word in ("본문", "원문", "영향", "유형", "한계")):
        return True
    return False


def _latestDateInText(text: str) -> date | None:
    latest: date | None = None
    for match in _DATE_RE.finditer(text):
        try:
            parsed = date(int(match.group(1)), int(match.group(2)), int(match.group(3)))
        except ValueError:
            continue
        if latest is None or parsed > latest:
            latest = parsed
    return latest


def _declaresDataLimit(text: str) -> bool:
    return any(
        word in text
        for word in (
            "데이터 한계",
            "최신 데이터가 없습니다",
            "기준일 한계",
            "확인 불가",
            "최신 시점 단정에는 한계",
            "최신 환율 수준은 여기서 확인되지 않았습니다",
            "최근 확인 가능한 기준일 기준",
            "현재라기보다",
        )
    )


def _declaresComparisonLimit(text: str) -> bool:
    return any(
        word in text for word in ("강한 결론을 일부 유보", "결론은 보류", "한계", "데이터 미수신", "데이터 미확보")
    )


def _requiresFreshStructuredData(question: str, toolCalls: list[dict[str, Any]]) -> bool:
    if not any(word in question for word in ("최근", "현재", "어제", "오늘", "latest", "recent")):
        return False
    for call in toolCalls:
        name = str(call.get("name", ""))
        args = call.get("arguments") or call.get("args") or {}
        axis = str(args.get("axis") or "").lower() if isinstance(args, dict) else ""
        if name in {"macro", "scan", "pythonExec"}:
            return True
        if name == "gather" and axis in {"krx", "macro", "price"}:
            return True
    return False


def _requiresFxEvidence(question: str) -> bool:
    q = question.lower()
    return any(word in q for word in ("환율", "원달러", "원/달러", "usdkrw", "krwusd", "fx", "exchange"))


def _hasFxEvidence(toolCalls: list[dict[str, Any]]) -> bool:
    try:
        from dartlab.gather.ecos.catalog import resolveId
    except Exception:  # pragma: no cover

        def resolveId(value: str) -> str:
            return value

    for call in toolCalls:
        name = str(call.get("name", ""))
        args = call.get("arguments") or call.get("args") or {}
        if not isinstance(args, dict):
            continue
        if name == "gather" and str(args.get("axis") or "").lower() == "macro":
            if resolveId(str(args.get("target") or "")) == "USDKRW":
                return True
    return False


def _hasVisualExplanation(text: str, workspace: Any) -> bool:
    visuals = getattr(workspace, "visuals", []) or []
    if visuals:
        return True
    lowered = text.lower()
    return "visualplan" in lowered or "visual plan" in lowered or "시각 설명" in text


def _hasUnsupportedVisual(workspace: Any) -> bool:
    visuals = getattr(workspace, "visuals", []) or []
    evidence = getattr(workspace, "evidence", []) or []
    if not visuals:
        return False
    return any(not getattr(visual, "evidenceIds", []) for visual in visuals) and bool(evidence)


def _workspaceStaleFreshness(workspace: Any, text: str) -> bool:
    freshness = getattr(workspace, "freshness", {}) or {}
    stale = any(isinstance(v, dict) and v.get("staleDaily") for v in freshness.values())
    if not stale:
        return False
    lowered = text.lower()
    disclosureWords = (
        "가용 데이터",
        "데이터 한계",
        "최신 데이터",
        "기준일",
        "기준",
        "같은 시점",
        "서로 다르",
        "단정",
        "한계",
        "가용 데이터",
        "데이터 한계",
        "최신 데이터",
        "snapshot",
        "available through",
        "available data",
        "freshness",
        "한계",
    )
    return not any(word in lowered or word in text for word in disclosureWords)


def _workspaceDisclosureDepthRisk(workspace: Any, text: str) -> bool:
    limits = getattr(workspace, "limits", []) or []
    titleListOnly = any("basis=title_list" in str(limit) for limit in limits)
    if not titleListOnly:
        return False
    disclosureWords = ("제목 기준", "목록 기준", "본문", "원문", "title", "list basis", "body")
    return not any(word in text.lower() or word in text for word in disclosureWords)


def _workspacePartialComparison(workspace: Any, text: str) -> bool:
    evidence = getattr(workspace, "evidence", []) or []
    targets = {getattr(item, "target", None) for item in evidence if getattr(item, "target", None)}
    if len(targets) >= 2:
        return False
    if _declaresComparisonLimit(text):
        return False
    return any(word in text for word in _STRONG_COMPARISON_WORDS)


def _workspaceUnsupportedClaim(workspace: Any) -> bool:
    claims = getattr(workspace, "claims", []) or []
    if not claims:
        return False
    return any(
        getattr(claim, "kind", "") == "judgment"
        and getattr(claim, "status", "") != "supported"
        and not getattr(claim, "evidenceIds", [])
        for claim in claims
    )


def _dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            out.append(item)
    return out
