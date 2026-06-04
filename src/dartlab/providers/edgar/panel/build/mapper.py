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
# role URI 마지막 세그먼트에 패턴 매칭. us-gaap("StatementsOfIncome")·IFRS("StatementOfProfitOrLoss")·
# 짧은 이름("BalanceSheet"/"CashFlows", Statement prefix 없음) 모두 흡수.
_ROLE_RULES: tuple[tuple[str, str], ...] = (
    ("comprehensiveincome", "CIS"),
    ("comprehensiveloss", "CIS"),
    ("stockholdersequity", "EF"),
    ("shareholdersequity", "EF"),
    ("changesinequity", "EF"),
    ("changesinshareholders", "EF"),
    ("cashflow", "CF"),
    ("balancesheet", "BS"),
    ("financialposition", "BS"),  # IFRS
    ("statementsofoperations", "IS"),
    ("statementofoperations", "IS"),
    ("statementsofincome", "IS"),
    ("statementofincome", "IS"),
    ("incomestatement", "IS"),
    ("profitorloss", "IS"),  # IFRS
    ("incomeloss", "IS"),
    ("resultsofoperations", "IS"),
)
# 본표 아님(주석·디테일·표지·괄호표) — 패턴 매칭 전 배제. 짧은 statement 이름("BalanceSheet")을
# 살리려 "statement" prefix 요구는 버리고, 비-본표를 명시 배제(disclosure/detail/parenthetical 등).
_ROLE_REJECT: tuple[str, ...] = (
    "disclosure",
    "parenthetic",
    "detail",
    "policies",
    "policy",
    "schedule",
    "cover",
    "document",
    "highlight",
    "tables",
)
_NONNUM_RE = re.compile(r"[^a-z0-9]")

# 표 캡션(HTML 제목 텍스트) → statement. role 이 아닌 **본문 표 캡션**으로 앵커(INS-era·pre-inline
# 필링은 inline fact 가 0 → role-concept 커버리지 불가, 캡션이 유일 신호). 검사 순서 = 특이도 높은 것
# 먼저(CIS·EF 가 IS·BS 보다 먼저). **제목 형식만**("Statements of X") — prose("...comprehensive income
# is as follows:") 오탐 차단. BS 는 "off-balance sheet" 음성 룩비하인드로 서술 표 배제.
_CAPTION_RULES: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"statements?\s+of\s+comprehensive\s+(income|loss)", re.IGNORECASE), "CIS"),
    (
        re.compile(
            r"statements?\s+of\s+(changes\s+in\s+)?(stockholders|shareholders|share-?owners)?['’]?\s*equity",
            re.IGNORECASE,
        ),
        "EF",
    ),
    (re.compile(r"statements?\s+of\s+cash\s+flows", re.IGNORECASE), "CF"),
    (
        re.compile(
            r"consolidated\s+balance\s+sheets?|statements?\s+of\s+financial\s+position|(?<!off[\s-])\bbalance\s+sheets?",
            re.IGNORECASE,
        ),
        "BS",
    ),
    (re.compile(r"statements?\s+of\s+(operations|income|earnings|profit)", re.IGNORECASE), "IS"),
)


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
        - 비-본표(disclosure/detail/parenthetical/cover) 배제 후 패턴 매칭 — 짧은 이름(BalanceSheet)·
          IFRS(ProfitOrLoss/FinancialPosition)·us-gaap 모두 흡수. "Statement" prefix 요구 안 함.

    When:
        - 재무표 concept 의 statement 귀속·disclosureKey 산출.

    How:
        - 마지막 세그먼트 정규화 → _ROLE_REJECT 배제 → _ROLE_RULES 순서 첫 매치.

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
    if any(r in norm for r in _ROLE_REJECT):
        return None  # 주석·디테일·표지·괄호표 = 본표 아님(서술)
    for pat, stmt in _ROLE_RULES:
        if pat in norm:
            return stmt
    return None


def captionToStatement(caption: str) -> str | None:
    """표 캡션(HTML 제목 텍스트) → 정규 statement key (BS/IS/CF/CIS/EF) 또는 None.

    ``roleToStatement`` 의 캡션 짝 — role URI 대신 **본문 재무제표 표 직전 텍스트**(예 "AAR CORP. AND
    SUBSIDIARIES CONSOLIDATED BALANCE SHEETS")로 statement 판정. inline fact 가 0 인 INS-era(≈2012~2020,
    facts 가 별도 EX-101.INS)·pre-inline 필링은 role-concept 커버리지가 불가능 → 캡션이 유일한 앵커 신호.
    ``_CAPTION_RULES`` 는 **제목 형식만**("Statements of X") 매칭 — prose("comprehensive income is as
    follows:")·"off-balance sheet" 같은 서술 표 오탐을 배제.

    Args:
        caption: 표 직전 텍스트(끝 ~160자 권장 — 표 바로 앞 제목이 캡션).

    Returns:
        "BS"/"IS"/"CF"/"CIS"/"EF" 또는 None (재무제표 제목 아님).

    Raises:
        없음.

    Example:
        >>> captionToStatement("AAR CORP. AND SUBSIDIARIES CONSOLIDATED BALANCE SHEETS ASSETS")
        'BS'
        >>> captionToStatement("CONSOLIDATED STATEMENTS OF COMPREHENSIVE INCOME (LOSS)")
        'CIS'
        >>> captionToStatement("A summary of the components of comprehensive income is as follows:") is None
        True
        >>> captionToStatement("contractual cash obligations and off-balance sheet arrangements") is None
        True

    SeeAlso:
        - ``roleToStatement`` — role URI 짝(inline era 의 정밀 신호).
        - ``walker.walkBody`` — fact-coverage primary + 본 캡션 fallback 앵커.

    Requires:
        - 없음.

    Capabilities:
        - inline fact 부재(INS-era·pre-inline) 필링의 재무제표 표를 캡션으로 앵커 — 전 시대 보드 수평화.

    Guide:
        - walker 가 fact-coverage 0 인 statement 에 대해서만 호출(fallback). 순수.

    AIContext:
        - 제목 형식 패턴(Statements of X)만 — prose 임베드·off-balance 오탐 차단. CIS·EF 가 IS·BS 보다 먼저.

    When:
        - inline fact 가 없는 필링에서 재무제표 표를 disclosureKey 로 앵커할 때.

    How:
        - 캡션 → _CAPTION_RULES 순서 첫 매치(제목 noun-phrase 요구).

    LLM Specifications:
        AntiPatterns:
            - 단순 substring 매칭 금지 — 제목 형식("Statements of X") 요구(prose 오탐 차단).
            - "off-balance sheet" 를 BS 로 매칭 금지 — 음성 룩비하인드.
        OutputSchema:
            - ``str | None``.
        Prerequisites:
            - 없음.
        Freshness:
            - 순수.
        Dataflow:
            - caption → _CAPTION_RULES 패턴 첫 매치.
        TargetMarkets:
            - US.
    """
    if not caption:
        return None
    for pat, stmt in _CAPTION_RULES:
        if pat.search(caption):
            return stmt
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
    "16": "Form 10-K Summary",
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
        # 카탈로그 우선(클린 표준명). 미등재만 캡처 텍스트 — 첫 문장/단어 몇개로 trim(TOC·페이지번호 노이즈 차단).
        name = catalog.get(num) or _trimItemName(m.group(2)) or num
        sectionLeaf = f"Item {num}. {name}"
    else:
        sectionLeaf = re.sub(r"\s+", " ", title)[:120] or "Document"
    return sectionLeaf, f"{form}␟{sectionLeaf}"


def _trimItemName(raw: str) -> str:
    """미등재 item 의 캡처 제목 정리 — 첫 마침표 전 + 최대 6단어(TOC·페이지번호 꼬리 제거)."""
    clean = re.sub(r"\s+", " ", (raw or "").strip())
    clean = clean.split(".", 1)[0]  # 첫 문장
    words = clean.split()
    # 숫자(페이지번호) 시작 단어부터 잘라냄
    cut: list[str] = []
    for w in words[:6]:
        if w.isdigit():
            break
        cut.append(w)
    return " ".join(cut).title()
