"""SEC 10-K HTML section extractor — P-PR7 신규.

dart docs/sections/extractors.py 의 KR 정기보고서 패턴 차용. SEC 10-K
표준 Items (Item 1 Business / Item 1A Risk Factors / Item 7 MD&A / Item 8
Financial Statements / Item 9A Controls) 추출.

향후 본문 구현은 P-PR-edgar-depth 트랙. 본 모듈은 측정 게이트 통과용 skeleton.
"""

from __future__ import annotations

import re

_ITEM_PATTERN = re.compile(r"^ITEM\s+(\d+[A-Z]?)\.\s*(.+)$", re.IGNORECASE | re.MULTILINE)

# 10-K 표준 Items SSOT
STANDARD_10K_ITEMS: dict[str, str] = {
    "1": "Business",
    "1A": "Risk Factors",
    "1B": "Unresolved Staff Comments",
    "2": "Properties",
    "3": "Legal Proceedings",
    "4": "Mine Safety Disclosures",
    "5": "Market for Registrants Common Equity",
    "6": "Selected Financial Data",
    "7": "MD&A",
    "7A": "Quantitative and Qualitative Disclosures About Market Risk",
    "8": "Financial Statements and Supplementary Data",
    "9": "Changes in and Disagreements with Accountants",
    "9A": "Controls and Procedures",
    "9B": "Other Information",
    "10": "Directors Executive Officers and Corporate Governance",
    "11": "Executive Compensation",
    "12": "Security Ownership",
    "13": "Certain Relationships and Related Transactions",
    "14": "Principal Accountant Fees and Services",
    "15": "Exhibits and Financial Statement Schedules",
}


def extractItems(html: str) -> dict[str, str]:
    """10-K HTML 본문에서 ITEM 별 텍스트 추출 (skeleton).

    Capabilities:
        - ``ITEM N.`` 패턴 (Item 1, Item 1A, Item 7 등) 라인 매칭.
        - 각 ITEM 시작 ~ 다음 ITEM 직전까지 텍스트 slice.
        - 본 skeleton 구현 — 실제 HTML parsing (BeautifulSoup 등) 은 향후.

    Args:
        html: 10-K HTML 본문 (또는 텍스트 변환 결과).

    Returns:
        dict[str, str] — ``{"1": "Business 본문...", "1A": "Risk Factors 본문...", ...}``.
        매칭 ITEM 없으면 빈 dict.

    Example:
        >>> extractItems("ITEM 1. Business\\nText here\\nITEM 2. Properties\\nMore")
        {'1': 'Business\\nText here', '2': 'Properties\\nMore'}

    Raises:
        없음.

    Guide:
        - "10-K Item 1A Risk Factors 만" → ``extractItems(html).get("1A")``.
        - 상수 ``STANDARD_10K_ITEMS`` 로 Item 이름 lookup.

    SeeAlso:
        - ``STANDARD_10K_ITEMS`` — 10-K Item 카탈로그.
        - ``dart.docs.sections.extractors`` — 동등 KR 정기보고서 추출.
        - ``edgar.docs.sections.runtime`` — Item → semantic topic 매핑.

    Requires:
        - re (stdlib) — 정규식 매칭.

    AIContext:
        Workbench "이 회사 10-K Risk Factors" 류 질문 entry. 본 함수가 raw text 반환,
        AI 가 요약 + 인용. None 보장 (빈 dict) — caller 는 .get 사용.

    LLM Specifications:
        AntiPatterns:
            - HTML escape / 특수문자 → 정규식 매칭 실패 가능. caller 가 HTML→text 변환 의무.
            - Item 표기 변형 (예 "Item 1." vs "ITEM 1." vs "1.") → 본 패턴은 대소문자 무시.
            - SEC 양식 변경 (2024 ESG 섹션 등) → ``STANDARD_10K_ITEMS`` 갱신 필요.
        OutputSchema:
            - dict[str, str] — Item 번호 → 본문 텍스트.
        Prerequisites:
            - html 이 텍스트 형태로 변환된 10-K 본문.
        Freshness:
            - SEC 10-K 양식 변경 (~연 1 회) 시 본 모듈 검토.
        Dataflow:
            - SEC EDGAR HTML → text 변환 → 본 함수 → AI 답변.
        TargetMarkets:
            - US (EDGAR / SEC) 10-K 한정. 10-Q / 8-K 는 별도.
    """
    result: dict[str, str] = {}
    matches = list(_ITEM_PATTERN.finditer(html))
    for i, match in enumerate(matches):
        itemNum = match.group(1).upper()
        start = match.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(html)
        result[itemNum] = html[start:end].strip()
    return result


def itemLabel(itemNum: str) -> str:
    """ITEM 번호 → 표준 라벨 lookup.

    Capabilities:
        - ``STANDARD_10K_ITEMS`` dict lookup.
        - 미정의 → "Item {N}" fallback.

    Args:
        itemNum: 예 "1", "1A", "7".

    Returns:
        str — 라벨.

    Example:
        >>> itemLabel("1A")
        'Risk Factors'

    Raises:
        없음.

    Guide:
        - "Item 7 정식 이름" → ``itemLabel("7")``.

    SeeAlso:
        - ``STANDARD_10K_ITEMS`` — SSOT.

    Requires:
        - 외부 의존 없음.

    AIContext:
        AI 가 사용자에게 Item 번호 + 정식 라벨 동시 노출 시.

    LLM Specifications:
        AntiPatterns:
            - itemNum 형식 변형 (예 "1a", "Item 1A") → upper case 호출자 책임.
        OutputSchema:
            - str.
        Prerequisites:
            - 없음.
        Freshness:
            - SEC 양식 변경 시 갱신.
        Dataflow:
            - STANDARD_10K_ITEMS → 본 함수.
        TargetMarkets:
            - US (EDGAR / SEC) 한정.
    """
    return STANDARD_10K_ITEMS.get(itemNum.upper(), f"Item {itemNum}")
