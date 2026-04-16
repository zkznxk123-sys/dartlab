"""한글 → 영문 회사명 alias (Phase 11 A3).

사용자가 "인텔" / "애플" 등 한글 음역으로 질의해도 EDGAR 티커 매칭 되도록.
간단한 고정 사전 — 무한 확장 금지, 명확한 대형 기업만.
"""

from __future__ import annotations


_KR_EN_ALIASES: dict[str, str] = {
    # Tech
    "인텔": "Intel",
    "애플": "Apple",
    "아마존": "Amazon",
    "구글": "Alphabet",
    "알파벳": "Alphabet",
    "마이크로소프트": "Microsoft",
    "엔비디아": "NVIDIA",
    "테슬라": "Tesla",
    "메타": "Meta",
    "페이스북": "Meta",
    "넷플릭스": "Netflix",
    "오라클": "Oracle",
    "어도비": "Adobe",
    "세일즈포스": "Salesforce",
    "아이비엠": "IBM",
    # 반도체
    "티에스엠씨": "Taiwan Semiconductor",
    "티에스엠": "Taiwan Semiconductor",
    "에이엠디": "AMD",
    "퀄컴": "Qualcomm",
    "마이크론": "Micron",
    "브로드컴": "Broadcom",
    # 금융
    "제이피모건": "JPMorgan",
    "뱅크오브아메리카": "Bank of America",
    "버크셔해서웨이": "Berkshire Hathaway",
    "골드만삭스": "Goldman Sachs",
    # 소비재
    "월마트": "Walmart",
    "코카콜라": "Coca-Cola",
    "맥도날드": "McDonald",
    "나이키": "Nike",
    "스타벅스": "Starbucks",
    # 미디어
    "디즈니": "Disney",
    # 에너지
    "엑손모빌": "Exxon",
    "쉐브론": "Chevron",
}


def resolveEnglishAlias(keyword: str) -> str | None:
    """한글 키워드 → 영문 회사명 변환 (없으면 None)."""
    return _KR_EN_ALIASES.get(keyword.strip())
