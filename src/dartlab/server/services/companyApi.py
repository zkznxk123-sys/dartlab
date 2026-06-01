from __future__ import annotations

import re as _re
from typing import Any

from dartlab import Company

from ..api.common import HANDLED_API_ERRORS
from ..cache import companyCache
from ..models import TocBlock, TocChapter, TocResponse, TocSection

_VALID_CODE = _re.compile(r"^[A-Za-z0-9가-힣]{1,20}$")


def getCompany(code: str) -> Company:
    """종목코드로 Company를 조회하거나 생성한다 (캐시 활용)."""
    if not _VALID_CODE.match(code):
        raise ValueError(f"유효하지 않은 종목코드: {code!r}")
    cached = companyCache.get(code)
    if cached:
        return cached[0]
    company = Company(code)
    companyCache.put(code, company, None)
    return company


get_company = getCompany


def safeTopicLabel(company, topic: str) -> str:
    """topic의 한글 라벨을 안전하게 반환한다."""
    try:
        return company._topicLabel(topic)
    except AttributeError:
        return topic


# period (예 "2024Q1") → 정기보고서 기준월 패턴 (예 "(2024.03)").
def _periodToReportPattern(period: str) -> str | None:
    import re as _re

    match = _re.fullmatch(r"(\d{4})(?:Q([1-4]))?", period.strip())
    if not match:
        return None
    year = match.group(1)
    quarter = match.group(2)
    if quarter is None or quarter == "4":
        return f"({year}.12)"  # 사업보고서 (연간 또는 Q4)
    if quarter == "1":
        return f"({year}.03)"
    if quarter == "2":
        return f"({year}.06)"
    if quarter == "3":
        return f"({year}.09)"
    return None


def _dartUrlForPeriod(company: Company, period: str | None = None) -> str | None:
    """period 에 해당하는 정기보고서의 DART 뷰어 URL.

    period=None → 최신 보고서. period 매칭 row 없으면 최신으로 fallback.
    """
    try:
        df = company.filings()
        if df is None or df.is_empty():
            return None
        latest_url = df.row(0, named=True).get("dartUrl")
        if period is None:
            return latest_url

        import polars as pl

        pattern = _periodToReportPattern(period)
        if pattern is None:
            return latest_url
        matched = df.filter(pl.col("reportType").str.contains(pattern, literal=True))
        if matched.is_empty():
            return latest_url
        return matched.row(0, named=True).get("dartUrl")
    except (AttributeError, ValueError, KeyError):
        return None


# 옛 별칭 — 외부 caller 호환.
_latestDartUrl = _dartUrlForPeriod


def _panelFor(company: Company, *, periods: list[str] | None = None):
    """Company 의 panel wide (항목 × 기간) — viewer/TOC 의 단일 데이터 소스 (SSOT).

    ``marketNs`` 는 ``Company.market`` 으로 분기 (DART=kr, EDGAR=us). ``periods``
    지정 시 read 단계에서 파일 prune (대형 종목 메모리/페이로드 절감). artifact 부재
    시 panel read 내부 ``ensurePanelFromHf`` 가 lazy 다운로드 (조달은 read 책임).
    """
    from dartlab.providers.dart.panel import Panel

    ns = "us" if getattr(company, "market", "") == "US" else "kr"
    return Panel(company.stockCode, marketNs=ns, periods=periods, tag=True)


_PANEL_PERIOD_RE = _re.compile(r"^\d{4}(?:Q[1-4])?$")
_SECTION_KEY_SEP = "␟"  # ␟ — chapter / sectionLeaf 구분자 (동명 sectionLeaf 충돌 방지).


def _periodColumns(wide) -> list[str]:
    """panel wide 의 period 컬럼만 (panel 이 이미 최신좌측 정렬 — 순서 보존)."""
    return [c for c in wide.columns if _PANEL_PERIOD_RE.fullmatch(c)]


def sectionKeyFor(chapter: str, sectionLeaf: str) -> str:
    """``"{chapter}␟{sectionLeaf}"`` — 동명 sectionLeaf 의 chapter 간 충돌 방지 키."""
    return f"{chapter}{_SECTION_KEY_SEP}{sectionLeaf}"


def splitSectionKey(sectionKey: str) -> tuple[str | None, str]:
    """sectionKey → (chapter, sectionLeaf). 구분자 없으면 chapter=None (sectionLeaf 단독)."""
    if _SECTION_KEY_SEP in sectionKey:
        chapter, sectionLeaf = sectionKey.split(_SECTION_KEY_SEP, 1)
        return chapter, sectionLeaf
    return None, sectionKey


def buildToc(company: Company, *, metaOnly: bool = False) -> dict[str, Any]:
    """뷰어 목차 — panel 의 chapter > sectionLeaf > blockLeaf 트리.

    panel 이 정부 표준 서식(SPINE)으로 이미 정렬·라벨링하므로 chapter/sectionLeaf 를
    first-appearance(=SPINE 순서) 그대로 그룹한다. 옛 topicStandard 재정렬·chapter III
    그루핑·로마숫자 정렬은 전부 불필요 (panel 이 정렬 SSOT). diff(hasChanges)는 프론트
    인접셀 비교로 이전 — 백엔드 계산 0.

    Args:
        company: Company 인스턴스.
        metaOnly: 하위호환 인자. panel TOC 는 period 간 비교를 하지 않으므로 무영향
            (트리 구조는 항상 동일).
    """
    import polars as pl

    def _empty() -> dict[str, Any]:
        return TocResponse(stockCode=company.stockCode, corpName=company.corpName, chapters=[], periods=[]).model_dump()

    wide = _panelFor(company)
    if wide is None or wide.is_empty():
        return _empty()
    if "chapter" not in wide.columns or "sectionLeaf" not in wide.columns:
        return _empty()

    periodCols = _periodColumns(wide)
    idx = wide.select(["chapter", "sectionLeaf", "blockLeaf"]).with_columns(
        pl.col("chapter").fill_null(""),
        pl.col("sectionLeaf").fill_null(""),
        pl.col("blockLeaf").fill_null(""),
    )

    chapters: list[TocChapter] = []
    for chapter in idx["chapter"].unique(maintain_order=True).to_list():
        if not chapter:
            continue
        chFrame = idx.filter(pl.col("chapter") == chapter)
        sections: list[TocSection] = []
        for sectionLeaf in chFrame["sectionLeaf"].unique(maintain_order=True).to_list():
            if not sectionLeaf or sectionLeaf == chapter:
                continue  # 빈 절 / chapter 헤더 행 제외
            secFrame = chFrame.filter(pl.col("sectionLeaf") == sectionLeaf)
            blocks: list[TocBlock] = []
            for blockLeaf in secFrame["blockLeaf"].unique(maintain_order=True).to_list():
                if not blockLeaf:
                    continue  # narrative anchor 행 (blockLeaf 없음) 은 chip 에서 제외
                cnt = secFrame.filter(pl.col("blockLeaf") == blockLeaf).height
                blocks.append(TocBlock(blockLeaf=blockLeaf, rowCount=int(cnt)))
            sections.append(
                TocSection(
                    sectionLeaf=sectionLeaf,
                    sectionKey=sectionKeyFor(chapter, sectionLeaf),
                    rowCount=int(secFrame.height),
                    blocks=blocks,
                )
            )
        if sections:
            chapters.append(TocChapter(chapter=chapter, sections=sections))

    return TocResponse(
        stockCode=company.stockCode,
        corpName=company.corpName,
        chapters=chapters,
        periods=periodCols,
    ).model_dump()


def serializePanelRows(wide, periodCols: list[str]) -> list[dict[str, Any]]:
    """panel wide → row dict 배열 (서버 직렬화 — 표현 변환 0, pass-through).

    각 행 = panel index(chapter/sectionLeaf/blockLeaf/disclosureKey/scope) + 본문 cells.
    ``cells`` 는 period→contentRaw(raw XML 무손실, tag=True). 빈 셀 drop, 본문 0 행 skip
    (visible window 의 ghost row 차단). ``blockType`` 은 셀에 ``"<TABLE"`` 포함 여부 파생
    (panel 14-col 에 blockType 컬럼 없음 — frontend content-sniffing 과 동일 규칙 1회).
    """
    rows: list[dict[str, Any]] = []
    for r in wide.iter_rows(named=True):
        cells = {p: r[p] for p in periodCols if isinstance(r.get(p), str) and r[p]}
        if not cells:
            continue
        isTable = any("<TABLE" in v for v in cells.values())
        rows.append(
            {
                "chapter": r.get("chapter") or "",
                "sectionLeaf": r.get("sectionLeaf") or "",
                "blockLeaf": r.get("blockLeaf") or "",
                "disclosureKey": r.get("disclosureKey"),
                "scope": r.get("scope"),
                "blockType": "table" if isTable else "text",
                "cells": cells,
            }
        )
    return rows


def buildPanelGrid(
    company: Company,
    *,
    chapter: str | None = None,
    section: str | None = None,
    windowPeriods: tuple[str, ...] | None = None,
) -> dict[str, Any]:
    """panel wide 의 한 절(section) 격자 — viewer 본문 (buildViewer 대체).

    ``windowPeriods`` 지정 시 read 파일단위 prune (50MB→수백KB). ``section`` 지정 시
    (chapter, sectionLeaf) 로 필터 (panel 이 이미 SPINE 정렬 — 추가 정렬 0). 셀은 raw
    XML 무손실(tag=True), 직렬화는 ``serializePanelRows`` (표현 변환 0). diff/timeline 은
    frontend (인접셀 비교 + window slice) — 백엔드 계산 0.

    Args:
        chapter: panel chapter (정부 라벨). section 과 함께 행 필터.
        section: panel sectionLeaf (옛 topic). None 이면 전체 격자.
        windowPeriods: 표시할 period (최신좌측). None 이면 전체 기간 (full-period).
    """
    periodsArg = list(windowPeriods) if windowPeriods else None
    wide = _panelFor(company, periods=periodsArg)

    base = {
        "stockCode": company.stockCode,
        "corpName": company.corpName,
        "chapter": chapter,
        "sectionLeaf": section,
        "sectionKey": sectionKeyFor(chapter, section) if (chapter and section) else (section or ""),
    }
    if wide is None or wide.is_empty():
        return {**base, "periods": [], "rows": [], "dartUrlByPeriod": {}}

    import polars as pl

    if section is not None and "sectionLeaf" in wide.columns:
        cond = pl.col("sectionLeaf") == section
        if chapter is not None and "chapter" in wide.columns:
            cond = cond & (pl.col("chapter") == chapter)
        wide = wide.filter(cond)

    periodCols = _periodColumns(wide)
    rows = serializePanelRows(wide, periodCols)
    dartUrlByPeriod = {p: _dartUrlForPeriod(company, p) for p in periodCols}
    return {
        **base,
        "periods": periodCols,
        "rows": rows,
        "dartUrlByPeriod": dartUrlByPeriod,
    }
