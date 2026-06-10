"""제품-산업 지표 매핑 — kindList 주요제품 → FRED/ECOS 시리즈.

kindList의 `주요제품` 텍스트에서 키워드를 매칭하여
해당 기업에 관련된 산업 지표(생산지수, PPI 등)를 자동 결정한다.
calcMacroRegression에서 회귀 변수로 사용.
"""

from __future__ import annotations

import logging

log = logging.getLogger(__name__)


# ── 제품 키워드 → 산업 지표 매핑 ──

PRODUCT_INDICATOR_MAP: dict[str, dict] = {
    # 반도체/전자 (customs: 8542 집적회로 · 8541 소자 · 8524 평판디스플레이)
    "반도체": {"fred": ["IPG3344S", "PCU33443344"], "customs": ["8542", "8541"], "label": "반도체 생산/가격"},
    "메모리": {"fred": ["IPG3344S", "PCU33443344"], "customs": ["8542"], "label": "반도체 생산/가격"},
    "DRAM": {"fred": ["IPG3344S"], "customs": ["8542"], "label": "반도체 생산"},
    "NAND": {"fred": ["IPG3344S"], "customs": ["8542"], "label": "반도체 생산"},
    "웨이퍼": {"fred": ["IPG3344S"], "customs": ["8542"], "label": "반도체 생산"},
    "파운드리": {"fred": ["IPG3344S"], "customs": ["8542"], "label": "반도체 생산"},
    "디스플레이": {"fred": ["IPG3344S"], "customs": ["8524"], "label": "전자부품 생산"},
    "OLED": {"fred": ["IPG3344S"], "customs": ["8524"], "label": "전자부품 생산"},
    "LCD": {"fred": ["IPG3344S"], "customs": ["8524"], "label": "전자부품 생산"},
    "LED": {"fred": ["IPG3344S"], "customs": ["8541"], "label": "전자부품 생산"},
    # 자동차 (customs: 8703 승용차 · 8708 부품 · 4011 타이어)
    "자동차": {"fred": ["IPG3361T3S"], "customs": ["8703", "8708"], "label": "자동차 생산"},
    "자동차부품": {"fred": ["IPG3361T3S"], "customs": ["8708"], "label": "자동차 생산"},
    "자동차용": {"fred": ["IPG3361T3S"], "customs": ["8708"], "label": "자동차 생산"},
    "차량": {"fred": ["IPG3361T3S"], "customs": ["8703"], "label": "자동차 생산"},
    "타이어": {"fred": ["IPG3361T3S"], "customs": ["4011"], "label": "자동차 생산"},
    # 2차전지/배터리 (customs: 8507 축전지)
    "2차전지": {"fred": ["PCU335911335911"], "customs": ["8507"], "label": "배터리 가격"},
    "이차전지": {"fred": ["PCU335911335911"], "customs": ["8507"], "label": "배터리 가격"},
    "배터리": {"fred": ["PCU335911335911"], "customs": ["8507"], "label": "배터리 가격"},
    "양극재": {"fred": ["PCU335911335911"], "customs": ["8507"], "label": "배터리 가격"},
    "음극재": {"fred": ["PCU335911335911"], "customs": ["8507"], "label": "배터리 가격"},
    "전해질": {"fred": ["PCU335911335911"], "customs": ["8507"], "label": "배터리 가격"},
    # 화학 (customs: 39 합성수지·플라스틱 · 29 유기화학)
    "화학": {"fred": ["IPG325S"], "customs": ["29"], "label": "화학 생산"},
    "석유화학": {"fred": ["IPG325S", "DCOILWTICO"], "customs": ["39", "29"], "label": "화학 생산/유가"},
    "합성수지": {"fred": ["IPG325S"], "customs": ["39"], "label": "화학 생산"},
    "플라스틱": {"fred": ["IPG325S"], "customs": ["39"], "label": "화학 생산"},
    # 철강/금속 (customs: 72 철강)
    "철강": {"fred": ["WPU101"], "customs": ["72"], "label": "금속 가격"},
    "강판": {"fred": ["WPU101"], "customs": ["72"], "label": "금속 가격"},
    "주물": {"fred": ["WPU101"], "customs": ["72"], "label": "금속 가격"},
    "알루미늄": {"fred": ["WPU101"], "label": "금속 가격"},
    "동박": {"fred": ["WPU101"], "label": "금속 가격"},
    # 에너지 (customs: 2710 석유제품)
    "석유": {"fred": ["DCOILWTICO"], "customs": ["2710"], "label": "WTI 유가"},
    "정유": {"fred": ["DCOILWTICO"], "customs": ["2710"], "label": "WTI 유가"},
    "가스": {"fred": ["DCOILWTICO"], "label": "유가"},
    "에너지": {"fred": ["DCOILWTICO"], "label": "유가"},
    "태양광": {"fred": ["IPG3344S"], "customs": ["8541"], "label": "전자부품 생산"},
    # 식품
    "식품": {"fred": ["IPG311A2S"], "label": "식품 생산"},
    "음료": {"fred": ["IPG311A2S"], "label": "식품 생산"},
    "식료품": {"fred": ["IPG311A2S"], "label": "식품 생산"},
    # 의약/바이오 (customs: 30 의약품)
    "의약품": {"fred": ["PCUOMFGOMFG"], "customs": ["30"], "label": "제조업 PPI"},
    "바이오": {"fred": ["PCUOMFGOMFG"], "customs": ["30"], "label": "제조업 PPI"},
    "치료제": {"fred": ["PCUOMFGOMFG"], "customs": ["30"], "label": "제조업 PPI"},
    "의료기기": {"fred": ["PCUOMFGOMFG"], "label": "제조업 PPI"},
    # 건설
    "건설": {"ecos": ["IPI"], "label": "산업생산"},
    "건축": {"ecos": ["IPI"], "label": "산업생산"},
    "시멘트": {"ecos": ["IPI"], "label": "산업생산"},
    # 물류/운송
    "물류": {"fred": ["TSIFRGHT"], "label": "화물운송"},
    "운송": {"fred": ["TSIFRGHT"], "label": "화물운송"},
    "해운": {"fred": ["TSIFRGHT"], "label": "화물운송"},
    "항공": {"fred": ["TSIFRGHT"], "label": "화물운송"},
    # 소프트웨어/IT (거시 지표 약함 — 범용)
    "소프트웨어": {"fred": ["PCUOMFGOMFG"], "label": "제조업 PPI"},
    "플랫폼": {"fred": ["PCUOMFGOMFG"], "label": "제조업 PPI"},
    # 섬유/의류
    "섬유": {"fred": ["IPG313T6S"], "label": "섬유 생산"},
    "의류": {"fred": ["IPG313T6S"], "label": "섬유 생산"},
}


def getProductIndicators(stockCode: str) -> list[dict]:
    """kindList 주요제품 → 관련 산업 지표 목록.

    Capabilities: kindList 의 ``주요제품`` 텍스트 keyword 매칭 → FRED/ECOS 시리즈 list.
    AIContext: calcMacroRegression 의 산업 지표 자동 결정 — 반도체/배터리/화학 등.
    Guide: PRODUCT_INDICATOR_MAP keyword 매칭 (substring). 중복 seriesId 제거.
    When: 회사의 산업-특화 외생변수 회귀 분석 시.
    How: ``_getProductText`` → keyword in product → mapping list 누적 + seen 중복 제거.

    Args:
        stockCode: 종목코드 (예: "005930").

    Returns:
        [{"seriesId": "IPG3344S", "source": "fred", "label": "반도체 생산"}, ...]
        빈 리스트이면 매핑 실패.

    Raises:
        없음 — kindList 조회 실패 시 빈 리스트.

    Requires:
        ``getKindList`` 캐시 (KIND HTTP fetch) + ``PRODUCT_INDICATOR_MAP`` 사전.

    Example:
        >>> inds = getProductIndicators("005930")

    See Also:
        getProductSummary : 본 함수 결과 + 메타 dict.
        exogenousAxes.getExogenousIndicators : 더 넓은 외생변수 매핑 (업종 기반).
    """
    product = _getProductText(stockCode)
    if not product:
        return []

    matched: list[dict] = []
    seen: set[str] = set()

    for keyword, mapping in PRODUCT_INDICATOR_MAP.items():
        if keyword in product:
            for source_key in ["fred", "ecos", "customs"]:
                for seriesId in mapping.get(source_key, []):
                    if seriesId not in seen:
                        seen.add(seriesId)
                        matched.append(
                            {
                                "seriesId": seriesId,
                                "source": source_key,
                                "label": mapping["label"],
                                "matchedKeyword": keyword,
                            }
                        )

    return matched


def _getProductText(stockCode: str) -> str:
    """kindList에서 주요제품 텍스트 조회."""
    try:
        from dartlab.gather.krx.listing import getKindList

        df = getKindList()
        row = df.filter(df["종목코드"] == stockCode)
        if row.is_empty():
            return ""
        return str(row["주요제품"][0] or "")
    except (ImportError, KeyError, IndexError):
        return ""


def getProductSummary(stockCode: str) -> dict | None:
    """기업의 제품-지표 매핑 요약.

    Capabilities: stockCode → product + indicators + matched keywords dict.
    AIContext: AI 가 분석 narrative 에서 "왜 이 산업 지표를 봤는지" 보여줄 때 진입.
    Guide: 사용자 friendly summary (product 전문 + 매칭 keyword set).
    When: 분석 결과 narrative 의 외생변수 선택 이유 noting 시.
    How: _getProductText + getProductIndicators → dict + dedup keywords.

    Args:
        stockCode: 종목코드.

    Returns:
        {"product": "반도체...", "indicators": [...], "keywords": ["반도체", "메모리"]}.
        kindList 조회 실패 시 None.

    Raises:
        없음 — kindList 실패 시 None.

    Requires:
        ``getKindList`` 캐시 + ``getProductIndicators`` 가용.

    Example:
        >>> summary = getProductSummary("005930")

    See Also:
        getProductIndicators : 본 함수의 indicator source.
        exogenousAxes.getExogenousSummary : 동행 broader summary (업종 기반).
    """
    product = _getProductText(stockCode)
    if not product:
        return None

    indicators = getProductIndicators(stockCode)
    keywords = [ind["matchedKeyword"] for ind in indicators]

    return {
        "product": product,
        "indicators": indicators,
        "keywords": list(set(keywords)),
    }
