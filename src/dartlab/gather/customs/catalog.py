"""관세청 무역통계 — 한국 수출주력 품목(HS) 카탈로그.

월별 수출입은 분기 기업 실적을 6~8주 선행하는 산업 사이클 신호. group 은
``mapping/productIndicators.py`` 의 제품 키와 정렬해, 회사 주요제품 → 업종 수출
시계열을 매크로 회귀 외생변수로 연결한다. HS 코드는 2/4자리 산업 집계 기준
(하위코드·국가 분해는 API 가 합산해 국가총계 월별 시계열로 환원).
"""

from __future__ import annotations

from .types import CatalogEntry

# ── 카탈로그 정의 (group → HS 품목들) ──

CATALOG: dict[str, list[CatalogEntry]] = {
    "반도체": [
        CatalogEntry(
            "8542", "반도체(집적회로)", "반도체", "Monthly", "USD", "전자집적회로 — 메모리·시스템반도체 수출입"
        ),
        CatalogEntry("8541", "반도체소자", "반도체", "Monthly", "USD", "다이오드·트랜지스터·개별소자"),
    ],
    "자동차": [
        CatalogEntry("8703", "승용차", "자동차", "Monthly", "USD", "승용 자동차 완성차 수출입"),
        CatalogEntry("8708", "자동차부품", "자동차", "Monthly", "USD", "자동차 부분품·부속품"),
    ],
    "석유화학": [
        CatalogEntry("39", "합성수지·플라스틱", "석유화학", "Monthly", "USD", "플라스틱과 그 제품(HS 39장)"),
        CatalogEntry("29", "유기화학품", "석유화학", "Monthly", "USD", "유기화학물(HS 29장)"),
    ],
    "석유제품": [
        CatalogEntry("2710", "석유제품", "석유제품", "Monthly", "USD", "석유와 역청유(원유 제외 정제품)"),
    ],
    "철강": [
        CatalogEntry("72", "철강", "철강", "Monthly", "USD", "철강(HS 72장) — 열연·냉연·강판"),
    ],
    "선박": [
        CatalogEntry("89", "선박", "선박", "Monthly", "USD", "선박과 수상구조물(HS 89장)"),
    ],
    "무선통신기기": [
        CatalogEntry("8517", "무선통신기기", "무선통신기기", "Monthly", "USD", "전화기·휴대폰·통신장비"),
    ],
    "디스플레이": [
        CatalogEntry("8524", "평판디스플레이", "디스플레이", "Monthly", "USD", "평판디스플레이 모듈(HS2022 신설)"),
    ],
    "2차전지": [
        CatalogEntry("8507", "축전지", "2차전지", "Monthly", "USD", "축전지 — 리튬이온 등 2차전지"),
    ],
    "컴퓨터": [
        CatalogEntry("8471", "컴퓨터", "컴퓨터", "Monthly", "USD", "자동자료처리기계와 그 단위기기"),
    ],
    "가전": [
        CatalogEntry("8528", "영상기기", "가전", "Monthly", "USD", "모니터·프로젝터·TV 수신기기"),
    ],
    "타이어": [
        CatalogEntry("4011", "타이어", "타이어", "Monthly", "USD", "고무제 공기타이어(신품)"),
    ],
    "의약품": [
        CatalogEntry("30", "의약품", "의약품", "Monthly", "USD", "의료용품(HS 30장) — 바이오·완제의약품"),
    ],
    "화장품": [
        CatalogEntry("3304", "화장품", "화장품", "Monthly", "USD", "미용·메이크업·기초화장품(K-뷰티)"),
    ],
}


def getAllEntries() -> list[CatalogEntry]:
    """카탈로그 전체 HS 품목 엔트리 (group 순서·정의 순서 보존).

    Capabilities: buildCustoms 가 순회하며 각 HS 의 월별 수출 시계열 빌드.
    AIContext: customs 빌드/수집의 HS universe — FRED catalog.getAllEntries 대응.
    Guide: CATALOG dict 의 group 순서·정의 순서 그대로 평탄화.
    When: buildCustoms / collectIndustryIndicators 가 수집 대상 결정 시.
    How: CATALOG.values() 순회 + extend.

    Returns:
        list[CatalogEntry] — 등록 HS 품목 전체.

    Raises:
        없음.

    Requires:
        없음 — 정적 카탈로그(네트워크·인증 불필요).

    Example:
        >>> [e.id for e in getAllEntries()][:2]
        ['8542', '8541']

    SeeAlso:
        getEntry : HS 코드 단건 조회.
        CATALOG : group → 엔트리 정의 SSOT.
    """
    out: list[CatalogEntry] = []
    for entries in CATALOG.values():
        out.extend(entries)
    return out


def getEntry(hsCode: str) -> CatalogEntry | None:
    """HS 코드로 카탈로그 엔트리 조회.

    Args:
        hsCode: HS 코드 문자열 (예 ``"8542"``).

    Returns:
        CatalogEntry 또는 미등록 시 None.

    Raises:
        없음.

    Requires:
        없음 — 정적 카탈로그(네트워크·인증 불필요).

    Example:
        >>> getEntry("8542").group
        '반도체'
    """
    for entry in getAllEntries():
        if entry.id == hsCode:
            return entry
    return None
