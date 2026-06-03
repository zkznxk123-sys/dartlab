"""EDGAR panel mapper — role→statement·context→cell·period·item (DART ``panel.mapper`` analog, 순수).

- ``roleToStatement``: presentation role URI → 정규 statement key (BS/IS/CF/CIS/EF) — DART
  ``canonicalKey(ACLASS)`` 의 EDGAR 미러(role name 패턴, scope-strip 불필요/연결-only).
- ``contextToCell``: 해소 context(instant|start/end+members) → (ctxYear,ctxFlow,ctxQuarter,ctxMode,
  axisPath) — DART ``decodeAcontext``(ACONTEXT 토큰)의 EDGAR 미러(실제 날짜→기간일수→mode).
- ``periodFromReport``: CONFORMED PERIOD OF REPORT → "YYYYQn" (core ``calendarQuarterFromEnd`` 위임).
- ``canonicalItem`` + ITEM 카탈로그: 서술 Item 제목 정규화.

LLM Specifications:
    AntiPatterns:
        - role 의미 hardcode 금지 — role name 형식 패턴(BalanceSheet/CashFlow…)만.
        - 기간일수→mode 산수 금지 — 토큰 선택 아님, 실제 duration 길이 분류(Y/A/Q).
        - ComprehensiveIncome 를 Income 으로 오분류 금지 — CIS 우선 검사.
    OutputSchema:
        - ``roleToStatement(roleURI) -> str | None``.
        - ``contextToCell(ctx) -> tuple[int,str,int,str,str] | None``.
        - ``periodFromReport(form, date) -> str | None``.
        - ``canonicalItem(form, rawTitle) -> tuple[str, str]``.
    Prerequisites:
        - core.utils.period (calendarQuarterFromEnd / formatPeriod).
    Freshness:
        - 순수 — 입력 외 의존 0.
    Dataflow:
        - role/context/header → statement/cell-meta/period.
    TargetMarkets:
        - US (us-gaap presentation role + xbrli context).
"""

from __future__ import annotations

import re
from datetime import date

from dartlab.core.utils.period import calendarQuarterFromEnd

# presentation role → statement (검사 순서 중요: CIS·EF 를 IS 보다 먼저).
# role URI 마지막 세그먼트(예 "StatementConsolidatedBalanceSheets")에 패턴 매칭.
_ROLE_RULES: tuple[tuple[str, str], ...] = (
    ("parenthetic", ""),  # parenthetical = 본표 아님 → skip (빈 statement)
    ("comprehensiveincome", "CIS"),
    ("comprehensiveloss", "CIS"),
    ("stockholdersequity", "EF"),
    ("shareholdersequity", "EF"),
    ("changesinequity", "EF"),
    ("cashflow", "CF"),
    ("balancesheet", "BS"),
    ("financialposition", "BS"),
    ("statementsofoperations", "IS"),
    ("statementsofincome", "IS"),
    ("incomeloss", "IS"),
    ("resultsofoperations", "IS"),
)
_NONNUM_RE = re.compile(r"[^a-z0-9]")


def roleToStatement(roleUri: str) -> str | None:
    """presentation role URI → 정규 statement key (BS/IS/CF/CIS/EF) 또는 None.

    role URI 마지막 세그먼트를 소문자·비영숫자 제거 후 ``_ROLE_RULES`` 순서대로 패턴 매칭. "Statement"
    prefix 재무제표만 매칭(Disclosure/Cover/Document 는 None=서술). parenthetical 은 본표 아님(None).

    Args:
        roleUri: presentation linkbase role URI (예 ".../role/StatementConsolidatedBalanceSheets").

    Returns:
        "BS"/"IS"/"CF"/"CIS"/"EF" 또는 None (서술/주석/cover/parenthetical).

    Raises:
        없음.

    Example:
        >>> roleToStatement("http://x.com/role/StatementConsolidatedBalanceSheets")
        'BS'
        >>> roleToStatement("http://x.com/role/StatementConsolidatedStatementsOfCashFlows")
        'CF'
        >>> roleToStatement("http://x.com/role/StatementBalanceSheetsParenthetical") is None
        True
        >>> roleToStatement("http://x.com/role/DisclosureLeases") is None
        True

    SeeAlso:
        - ``providers.dart.panel.mapper.canonicalKey`` — DART ACLASS analog.

    Requires:
        - 없음.

    Capabilities:
        - 재무제표를 role 형식 패턴으로 정규 key 앵커링 — 손매핑 0(DART 사상 동일).

    Guide:
        - cell/builder 가 호출. 순수.

    AIContext:
        - "Statement" 계열만 본표. Disclosure=주석(None→narrative).

    When:
        - 재무표 concept 의 statement 귀속·disclosureKey 산출.

    How:
        - 마지막 세그먼트 정규화 → _ROLE_RULES 순서 첫 매치.

    LLM Specifications:
        AntiPatterns:
            - 전체 URI 매칭 금지 — 마지막 세그먼트(도메인 노이즈 배제).
        OutputSchema:
            - ``str | None``.
        Prerequisites:
            - 없음.
        Freshness:
            - 순수.
        Dataflow:
            - roleURI → segment 정규화 → 패턴.
        TargetMarkets:
            - US.
    """
    if not roleUri:
        return None
    seg = roleUri.rstrip("/").rsplit("/", 1)[-1]
    norm = _NONNUM_RE.sub("", seg.lower())
    if "statement" not in norm and "financialposition" not in norm:
        return None  # Disclosure/Cover/Document 등 = 서술
    for pat, stmt in _ROLE_RULES:
        if pat in norm:
            return stmt or None
    return None


def _durationToQuarterMode(start: date, end: date) -> tuple[int, str]:
    """duration (start~end) → (ctxQuarter, ctxMode) — DART marker→quarter/mode 의 EDGAR 미러.

    기간일수로 mode 분류(≈365 Y 연간 / ≈270·180 A YTD누적 / ≈90 Q 단독분기), quarter 는 end 의
    calendar quarter (``calendarQuarterFromEnd``). 비-12월 결산 흡수.
    """
    days = (end - start).days
    _y, q = calendarQuarterFromEnd(end)
    if days >= 350:
        return (q, "Y")  # 연간(FY)
    if days >= 60 and days <= 130:
        return (q, "Q")  # 단독 분기 3M
    return (q, "A")  # 누적 YTD (6M/9M 등)


def contextToCell(ctx: dict, *, fyEndMonth: int | None = None) -> tuple[int, str, int, str, str] | None:
    """해소 context → (ctxYear, ctxFlow, ctxQuarter, ctxMode, axisPath) — DART decodeAcontext 미러.

    instant(BS 시점) → ctxFlow="e", mode = 회계연말 월(``fyEndMonth``)과 같은 달이면 "Y"(연말 잔액),
    아니면 "A"(중간 잔액) — DART freq mask(quarter=e&A/Y, year=Y) 와 정합. duration(flow) → ctxFlow="d",
    기간일수로 mode(Y/A/Q). quarter·year 는 instant/end 의 calendar quarter. axisPath = dimension member
    local-name "|" join (DART axisPath 대응, 없으면 "").

    Args:
        ctx: ``instance.extractContexts`` 항목 — ``{instant, start, end, members}``.
        fyEndMonth: 회계연도 종료 월(1~12, SGML FISCAL YEAR END MMDD 의 MM). instant mode Y/A 판정용.

    Returns:
        ``(ctxYear, ctxFlow, ctxQuarter, ctxMode, axisPath)`` 또는 None (날짜 파싱 불가).

    Raises:
        없음.

    Example:
        >>> contextToCell({"instant": "2025-05-31", "start": None, "end": None, "members": []}, fyEndMonth=5)
        (2025, 'e', 2, 'Y', '')
        >>> contextToCell({"instant": "2024-08-31", "start": None, "end": None, "members": []}, fyEndMonth=5)
        (2024, 'e', 3, 'A', '')
        >>> contextToCell({"instant": None, "start": "2024-06-01", "end": "2025-05-31", "members": []})
        (2025, 'd', 2, 'Y', '')

    SeeAlso:
        - ``providers.dart.panel.build.cell.decodeAcontext`` — DART analog.

    Requires:
        - core.utils.period.calendarQuarterFromEnd.

    Capabilities:
        - context 간접참조를 셀 period/축으로 — DART ACONTEXT 토큰 디코드 미러.

    Guide:
        - cell.buildCells 가 호출. 순수.

    AIContext:
        - 실제 날짜 기반(EDGAR 는 토큰 마커 없음) — 기간일수로 Y/A/Q.

    When:
        - fact 를 (period, mode, axis) 셀로 묶을 때.

    How:
        - instant→P / duration→_durationToQuarterMode + members→axisPath.

    LLM Specifications:
        AntiPatterns:
            - members axis 포함 금지 — member local-name 만(DART axisPath 동형).
        OutputSchema:
            - ``tuple | None``.
        Prerequisites:
            - core period.
        Freshness:
            - 순수.
        Dataflow:
            - ctx → period 분류 + members.
        TargetMarkets:
            - US.
    """
    members = ctx.get("members") or []
    axisPath = "|".join((mem.split(":", 1)[-1]) for _ax, mem in members)
    instant = ctx.get("instant")
    if instant:
        d = _parseDate(instant)
        if d is None:
            return None
        y, q = calendarQuarterFromEnd(d)
        mode = "Y" if fyEndMonth and d.month == fyEndMonth else "A"  # 연말 잔액=Y, 중간 잔액=A (freq mask 정합)
        return (y, "e", q, mode, axisPath)
    start, end = _parseDate(ctx.get("start")), _parseDate(ctx.get("end"))
    if start is None or end is None:
        return None
    q, mode = _durationToQuarterMode(start, end)
    return (end.year if mode == "Y" else calendarQuarterFromEnd(end)[0], "d", q, mode, axisPath)


def _parseDate(s: str | None) -> date | None:
    """``YYYY-MM-DD`` → date (실패 None)."""
    if not s:
        return None
    try:
        parts = s.split("-")
        return date(int(parts[0]), int(parts[1]), int(parts[2]))
    except (ValueError, IndexError):
        return None


def periodFromReport(form: str, periodOfReport: date | None) -> str | None:
    """CONFORMED PERIOD OF REPORT → "YYYYQn" (calendar quarter, core 위임).

    Args:
        form: 폼 종류(현재 미사용, 시그니처 보존 — 향후 폼별 분기 대비).
        periodOfReport: 보고 기준일 (SGML header).

    Returns:
        "YYYYQn" (하이픈 없음 — panel read 의 ``isPeriodColumn`` 규약 ``^\\d{4}Q[1-4]$``) 또는 None.

    Raises:
        없음.

    Example:
        >>> periodFromReport("10-K", date(2024, 12, 31))
        '2024Q4'
        >>> periodFromReport("10-K", date(2025, 5, 31))
        '2025Q2'

    SeeAlso:
        - core.utils.period.calendarQuarterFromEnd — calendar quarter 매핑(Capital IQ, EDGAR 결산 다양).
        - providers.dart.panel.period.isPeriodColumn — "YYYYQn" 규약(하이픈 금지).
    """
    if periodOfReport is None:
        return None
    y, q = calendarQuarterFromEnd(periodOfReport)
    return f"{y}Q{q}"


# SEC 표준 item 카탈로그 (서술 보드 sectionLeaf 정규화 — panel-local 상수, 폐기 모듈 미import).
ITEM_NAMES_10K: dict[str, str] = {
    "1": "Business",
    "1A": "Risk Factors",
    "1B": "Unresolved Staff Comments",
    "1C": "Cybersecurity",
    "2": "Properties",
    "3": "Legal Proceedings",
    "4": "Mine Safety Disclosures",
    "5": "Market for Registrant's Common Equity",
    "6": "Selected Financial Data",
    "7": "Management's Discussion and Analysis",
    "7A": "Quantitative and Qualitative Disclosures About Market Risk",
    "8": "Financial Statements and Supplementary Data",
    "9": "Changes in and Disagreements with Accountants",
    "9A": "Controls and Procedures",
    "9B": "Other Information",
    "10": "Directors, Executive Officers and Corporate Governance",
    "11": "Executive Compensation",
    "12": "Security Ownership of Certain Beneficial Owners",
    "13": "Certain Relationships and Related Transactions",
    "14": "Principal Accountant Fees and Services",
    "15": "Exhibits, Financial Statement Schedules",
}
ITEM_NAMES_10Q: dict[str, str] = {
    "1": "Financial Statements",
    "2": "Management's Discussion and Analysis",
    "3": "Quantitative and Qualitative Disclosures About Market Risk",
    "4": "Controls and Procedures",
}
_ITEM_RE = re.compile(r"item\s+(\d+[A-Za-z]?)\b\.?\s*(.*)", re.IGNORECASE)


def canonicalItem(form: str, rawTitle: str) -> tuple[str, str]:
    """서술 Item 제목 → (sectionLeaf, sectionPath) 정규화.

    "ITEM 1A. RISK FACTORS" → ("Item 1A. Risk Factors", "{form}␟Item 1A. Risk Factors"). 카탈로그
    매칭 시 표준명, 미매칭 시 원 제목 정리. Item 형식 아니면 제목 그대로.

    Args:
        form: 폼 종류 ("10-K"/"10-Q"/"20-F").
        rawTitle: walker 가 검출한 원 heading.

    Returns:
        ``(sectionLeaf, sectionPath)``.

    Raises:
        없음.

    Example:
        >>> canonicalItem("10-K", "ITEM 1A. RISK FACTORS")
        ('Item 1A. Risk Factors', '10-K␟Item 1A. Risk Factors')
        >>> canonicalItem("10-K", "ITEM 1. ")
        ('Item 1. Business', '10-K␟Item 1. Business')

    SeeAlso:
        - ``walker.walkBody`` — 원 heading 검출.
    """
    title = (rawTitle or "").strip()
    m = _ITEM_RE.match(title)
    if m:
        num = m.group(1).upper()
        catalog = ITEM_NAMES_10Q if form == "10-Q" else ITEM_NAMES_10K
        name = catalog.get(num) or m.group(2).strip().title() or num
        sectionLeaf = f"Item {num}. {name}"
    else:
        sectionLeaf = re.sub(r"\s+", " ", title)[:120] or "Document"
    return sectionLeaf, f"{form}␟{sectionLeaf}"
