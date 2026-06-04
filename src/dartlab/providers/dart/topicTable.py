"""topicTable — 정형 공시 topic 표 추출 단일 SSOT (docs.finance/disclosure 파서 농장 대체).

docs 농장은 topic 마다 파일을 따로 둔 35 파서(dividend.py·majorHolder/parser.py·segment/…)
였으나, 모든 파서의 골격은 동일하다: **섹션 필터 → 표 찾기(헤더) → 행 파싱 → 컬럼맵**.
차이는 코드가 아니라 *데이터*(섹션 패턴·헤더 키워드·후처리)일 뿐이라, panel 시대엔 한 곳으로
일괄한다 — ``sections.sectionTables``(panel contentRaw raw XML → 표 행)가 이미 표를 주고,
본 모듈의 ``TOPIC_REGISTRY`` 선언적 설정 + 범용 ``topicTable`` 추출기 하나로 끝낸다.

[[feedback_no_patterns]] "파서 농장 금지" 정합 — 35 파일 → 1 추출기 + 데이터.
정형 변형(시계열 조립·다중 표)은 topic 별 작은 ``post`` 콜백으로(파일 신설 0).
"""

from __future__ import annotations

import polars as pl

# 정형 공시 topic 선언적 설정. section=sectionLeaf 필터, headers=표 식별 헤더 키워드,
# inherit=rowspan 상속 컬럼, post=DataFrame 후처리(시계열/다중표). 농장 파서가 코드로
# 하던 것을 데이터로. (panel raw XML 표를 sectionTables 가 행으로 주므로 markdown 파싱 0.)
_Cfg = dict[str, object]
TOPIC_REGISTRY: dict[str, _Cfg] = {
    "majorHolder": {"section": "최대주주", "headers": ["구분", "주주명"]},
    "dividend": {"section": "배당", "headers": ["배당", "주당"]},
    "segment": {"section": "부문", "headers": ["부문", "매출"]},
    "boardOfDirectors": {"section": "임원", "headers": ["성명", "직위"]},
    "executive": {"section": "임원", "headers": ["성명", "직위"]},
    "employee": {"section": "직원", "headers": ["직원", "급여"]},
    "shareCapital": {"section": "주식의 총수", "headers": ["주식의 종류"]},
    "capitalChange": {"section": "자본금 변동", "headers": ["주식발행"]},
    "tangibleAsset": {"section": "설비", "headers": ["소재지"]},
    "subsidiary": {"section": "계열회사", "headers": ["회사명"]},
    "costByNature": {"section": "비용의 성격", "headers": ["비용"]},
    "sanction": {"section": "제재", "headers": ["제재기관"]},
    "contingentLiability": {"section": "우발부채", "headers": ["채권자"]},
    "rnd": {"section": "연구개발", "headers": ["연구개발비"]},
    "salesOrder": {"section": "수주", "headers": ["품목"]},
    "rawMaterial": {"section": "원재료", "headers": ["매입처"]},
}


def topicTable(
    code: str,
    topic: str,
    *,
    period: str | None = None,
    marketNs: str = "kr",
) -> pl.DataFrame | None:
    """정형 공시 topic 표 추출 — 단일 SSOT (35 파서 대체).

    Args:
        code: 종목코드.
        topic: ``TOPIC_REGISTRY`` 키 (예 "dividend"·"majorHolder").
        period: panel period (예 "2025Q4"). None = 전 기간.
        marketNs: 시장 namespace.

    Returns:
        pl.DataFrame | None — 표 행(헤더 컬럼 기반 dict). 미등록 topic·표 부재 시 None.

    Raises:
        없음 — 추출 실패는 None.

    Example:
        >>> topicTable("005930", "majorHolder", period="2025Q4")  # doctest: +SKIP
    """
    cfg = TOPIC_REGISTRY.get(topic)
    if cfg is None:
        return None
    from dartlab.providers.dart.sections import sectionTables
    from dartlab.providers.dart.tableRows import findTableByHeaders, tableToRowDictsWithHeaderRow

    tables = sectionTables(code, sectionPattern=str(cfg["section"]), period=period, marketNs=marketNs)
    if not tables:
        return None
    found = findTableByHeaders(tables, list(cfg["headers"]))  # type: ignore[arg-type]
    if not found:
        return None
    table, headerIdx = found
    inherit = list(cfg.get("inherit", []))  # type: ignore[arg-type]
    rows = tableToRowDictsWithHeaderRow(table, headerIdx, inheritColumns=inherit)
    if not rows:
        return None
    df = pl.DataFrame(rows)
    post = cfg.get("post")
    if callable(post):
        return post(df)
    return df


__all__ = ["topicTable", "TOPIC_REGISTRY"]
