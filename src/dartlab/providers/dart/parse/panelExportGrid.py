"""공시 panel 표 → export 격자 PanelTableAccessor 구현 (DIP register-side).

import 시 ``registerPanelTableAccessor`` 호출 → ``viz/export/excel.py`` 가
``from dartlab.providers`` 직접 import 없이 (layer 합법) ``getPanelTableAccessor()`` 로
공시 표 격자를 얻는다. 결과는 평면 ``PanelExportSheet`` (위치·병합·정합값·단위) 라
viz 는 openpyxl 쓰기만 한다.

provider 격자 빌드 = ``readWide``(panel wide, raw XML 셀) → 행 선택(7-필드 식별, leafSeq
디스앰비그) → ``normalizeDartXml``(대문자→표준) → ``cellGrid``(병합 직사각 전개, 동일
인스턴스 공유) → ``coerceCell``(숫자/음수/빈셀). 병합은 id() extent 로 앵커 1개 + span.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import polars as pl

from dartlab.core.panelTableAccessor import (
    PanelExportCell,
    PanelExportSheet,
    registerPanelTableAccessor,
)
from dartlab.providers.dart.panel.read import readWide
from dartlab.providers.dart.parse.dartXmlNormalize import coerceCell, detectUnit, normalizeDartXml
from dartlab.providers.dart.parse.htmlTableParser import cellGrid

if TYPE_CHECKING:
    from dartlab.providers.dart.parse.htmlTableParser import HtmlTableCell

# panel wide 행을 유일 식별하는 7-필드 (실측 005930 1627행 0충돌). disclosureKey/scope/leafSeq 는
# 대부분의 공시 표에서 None → 제공된(non-None) 필드만으로 필터한다. 문자열 "" 는 *빈값 매칭*
# (예 blockLeaf="" 인 행)이라 필터에 포함된다 (None 만 skip).
_PANEL_ID_FIELDS = ("chapter", "sectionLeaf", "blockLeaf", "leafType", "disclosureKey", "scope", "leafSeq")


def _loadWide(stockCode: str, marketNs: str) -> pl.DataFrame | None:
    """panel wide DataFrame (raw XML 셀, tag=True) 로드 — 실패는 None."""
    try:
        return readWide(stockCode, marketNs=marketNs, tag=True)
    except (RuntimeError, ValueError, OSError):
        return None


def _selectRow(wide: pl.DataFrame, ids: dict) -> dict | None:
    """제공된(non-None) 식별 필드로 행 1개 — 다중이면 leafSeq 오름차순 첫 행."""
    flt = wide
    for fld in _PANEL_ID_FIELDS:
        val = ids.get(fld)
        if val is None or fld not in wide.columns:
            continue
        flt = flt.filter(pl.col(fld) == val)
    if flt.height == 0:
        return None
    if flt.height > 1 and "leafSeq" in flt.columns:
        flt = flt.sort("leafSeq")
    return flt.head(1).to_dicts()[0]


def _gridToCells(grid: list[list["HtmlTableCell | None"]]) -> list[PanelExportCell]:
    """병합 격자 → 앵커 셀 리스트 (id() extent 로 병합 span, 극단 rowspan 도 셀 1개)."""
    coords: dict[int, tuple[HtmlTableCell, list[tuple[int, int]]]] = {}
    for r, row in enumerate(grid):
        for c, cell in enumerate(row):
            if cell is None:
                continue
            entry = coords.get(id(cell))
            if entry is None:
                coords[id(cell)] = (cell, [(r, c)])
            else:
                entry[1].append((r, c))
    cells: list[PanelExportCell] = []
    for _cid, (cell, cl) in coords.items():
        rs = [r for r, _ in cl]
        cs = [c for _, c in cl]
        minR, minC, maxR, maxC = min(rs), min(cs), max(rs), max(cs)
        cells.append(
            PanelExportCell(
                row=minR,
                col=minC,
                value=coerceCell(cell.text),
                isHeader=cell.isHeader,
                align=(cell.align or ""),
                rowspan=maxR - minR + 1,
                colspan=maxC - minC + 1,
            )
        )
    return cells


def _latestPeriodWithContent(wide: pl.DataFrame, row: dict) -> str | None:
    """식별 컬럼 제외한 period 컬럼 중 셀 내용이 있는 첫(최신 좌측) 기간."""
    idxCols = set(_PANEL_ID_FIELDS) | {"leafSeq"}
    for col in wide.columns:
        if col in idxCols:
            continue
        if row.get(col):
            return col
    return None


class _PanelTableImpl:
    """PanelTableAccessor 구현 — readWide + 선택 + 정규화 + cellGrid + coerce."""

    def panelTableGrid(
        self,
        stockCode: str,
        *,
        marketNs: str = "kr",
        chapter: str = "",
        sectionLeaf: str = "",
        blockLeaf: str = "",
        leafType: str = "table",
        disclosureKey: str | None = None,
        scope: str | None = None,
        leafSeq: int | None = None,
        periodMode: str = "asFiled",
        period: str | None = None,
    ) -> PanelExportSheet | None:
        """식별 필드로 공시 표 1개 → PanelExportSheet (앵커 셀+병합+단위).

        Args:
            stockCode: 6자리 종목코드.
            marketNs: panel namespace (기본 "kr").
            chapter/sectionLeaf/blockLeaf/leafType: 표 식별 라벨 ("" = 빈값 매칭).
            disclosureKey/scope: 회사간 이식 키·연결구분 (없으면 None = 매칭 제외).
            leafSeq: 같은 섹션 다중 표 디스앰비그 ordinal (None = 첫 매칭).
            periodMode: "asFiled"(단일 기간 원본 격자) / "horizontalized"(일반표 폴백+노트).
            period: asFiled 단일 기간; 없으면 셀 내용 있는 최신 기간 자동.

        Returns:
            PanelExportSheet (앵커 셀+병합 span+단위/노트) 또는 None
            (panel/행/기간 부재 = graceful skip).

        Example:
            >>> _PanelTableImpl().panelTableGrid("005930", sectionLeaf="1. 회사의 개요")  # doctest: +SKIP

        Raises:
            없음 — 로드/선택/기간 실패는 모두 None 으로 흡수.
        """
        wide = _loadWide(stockCode, marketNs or "kr")
        if wide is None:
            return None
        ids = {
            "chapter": chapter,
            "sectionLeaf": sectionLeaf,
            "blockLeaf": blockLeaf,
            "leafType": leafType,
            "disclosureKey": disclosureKey,
            "scope": scope,
            "leafSeq": leafSeq,
        }
        row = _selectRow(wide, ids)
        if row is None:
            return None

        if periodMode == "horizontalized":
            # 일반 공시 표는 기간 간 라벨 정렬 불확실 → as-filed 폴백 + 노트 (거짓 정렬 금지).
            usePeriod = _latestPeriodWithContent(wide, row)
            note = f"수평화 미지원(원본 구조) — as-filed {usePeriod}" if usePeriod else ""
        else:
            usePeriod = period if (period and row.get(period)) else _latestPeriodWithContent(wide, row)
            note = ""
        if not usePeriod or not row.get(usePeriod):
            return None

        rawXml = row[usePeriod]
        grid = cellGrid(normalizeDartXml(rawXml))
        if not grid:
            return None
        return PanelExportSheet(cells=_gridToCells(grid), unit=detectUnit(rawXml), note=note)


registerPanelTableAccessor(_PanelTableImpl())
