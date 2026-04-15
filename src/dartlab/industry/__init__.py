"""산업 매퍼엔진 — 데이터 주도 산업지도.

L2 분석 엔진. KindList(업종+제품) → docs(사업보고서) → AI+사람 검수
4단계 파이프라인으로 살아있는 산업지도를 빌드한다.

분류체계(taxonomy.json)가 데이터. 코드는 파이프라인만 고정.

사용법::

    import dartlab

    dartlab.industry()                              # 가이드 (산업 목록)
    dartlab.industry("semiconductor")               # 반도체 산업지도 DataFrame
    dartlab.industry("semiconductor", "equipment")  # 장비 공정만

    c = dartlab.Company("005930")
    c.industry()                                    # 삼성전자의 산업 내 위치
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import polars as pl


# 섹터/매개변수 공개 API (기존 compat.py 경로 대체 — industry.sector 내부 정의)
from dartlab.industry.sector import (
    Sector,
    IndustryGroup,
    SectorInfo,
    SectorParams,
    MarketParams,
    MARKET_KR,
    MARKET_US,
    MARKET_PARAMS,
    classify,
    getParams,
    getMarketParams,
    getThresholds,
)

_DATA_DIR = Path(__file__).parent


class Industry:
    """산업 매퍼엔진 진입점."""

    def __call__(
        self,
        industryId: str | None = None,
        stage: str | None = None,
        *,
        summary: bool = False,
        timeline: bool = False,
        year: str = "2024",
    ) -> pl.DataFrame:
        """산업지도를 조회한다.

        Parameters
        ----------
        industryId : str | None
            산업 ID. None이면 가이드 반환.
        stage : str | None
            특정 공정만 필터.
        summary : bool
            True이면 공정별 매출/이익 집계.
        timeline : bool
            True이면 연도별 공정 매출 추이.
        year : str
            재무 데이터 기준 연도 (summary 시 사용).

        Returns
        -------
        pl.DataFrame
        """
        if industryId is None:
            return self._guide()
        if summary:
            return self._summary(industryId, year=year)
        if timeline:
            return self._timeline(industryId)
        return self._query(industryId, stage)

    def _guide(self) -> pl.DataFrame:
        """등록된 산업 목록."""
        from dartlab.industry.taxonomy import listIndustries

        entries = listIndustries()
        if not entries:
            return pl.DataFrame({"산업ID": [], "산업명": [], "공정수": []})
        return pl.DataFrame(
            {
                "산업ID": [e["industryId"] for e in entries],
                "산업명": [e["name"] for e in entries],
                "공정수": [e["stages"] for e in entries],
            }
        )

    def _query(self, industryId: str, stage: str | None) -> pl.DataFrame:
        """nodes.json에서 해당 산업의 노드를 DataFrame으로 반환."""
        from dartlab.industry.build.pipeline import loadNodes
        from dartlab.industry.taxonomy import getIndustry

        nodes = loadNodes()
        filtered = [n for n in nodes if n.industry == industryId]
        if stage:
            filtered = [n for n in filtered if n.stage == stage]

        if not filtered:
            return pl.DataFrame(
                schema={
                    "종목코드": pl.Utf8,
                    "종목명": pl.Utf8,
                    "공정": pl.Utf8,
                    "공정명": pl.Utf8,
                    "역할": pl.Utf8,
                    "위치": pl.Utf8,
                    "신뢰도": pl.Float64,
                    "소스": pl.Utf8,
                }
            )

        ind = getIndustry(industryId)
        stageLabels = {s.key: s.name for s in ind.stages} if ind else {}

        df = pl.DataFrame(
            {
                "종목코드": [n.stockCode for n in filtered],
                "종목명": [n.corpName for n in filtered],
                "공정": [n.stage for n in filtered],
                "공정명": [stageLabels.get(n.stage, n.stage) for n in filtered],
                "역할": [n.role for n in filtered],
                "위치": [n.stream for n in filtered],
                "매출(억)": [round(n.revenue / 1e8, 0) if n.revenue else None for n in filtered],
                "신뢰도": [n.confidence for n in filtered],
                "소스": [n.source for n in filtered],
            }
        )
        return df.sort("매출(억)", descending=True, nulls_last=True)

    def _summary(self, industryId: str, *, year: str = "2024") -> pl.DataFrame:
        """공정별 매출/이익 집계."""
        from dartlab.industry.build.financials import buildIndustrySummary
        from dartlab.industry.build.pipeline import loadNodes

        return buildIndustrySummary(loadNodes(), industryId, year=year)

    def _timeline(self, industryId: str) -> pl.DataFrame:
        """연도별 공정 매출 추이."""
        from dartlab.industry.build.financials import buildTimelineSummary
        from dartlab.industry.build.pipeline import loadNodes

        return buildTimelineSummary(loadNodes(), industryId)

    def build(self, *, skipDocs: bool = False) -> None:
        """산업지도를 빌드한다 (4단계 파이프라인)."""
        from dartlab.industry.build.pipeline import buildIndustryMap

        buildIndustryMap(skipDocs=skipDocs)

    def edges(self, industryId: str | None = None, stockCode: str | None = None) -> pl.DataFrame:
        """공급-수요·계열 관계 조회.

        Parameters
        ----------
        industryId : str | None
            산업 ID로 필터.
        stockCode : str | None
            특정 종목의 관계만.

        Returns
        -------
        pl.DataFrame
            columns: from코드, from이름, to코드, to이름, 관계, 산업, 신뢰도, 소스, 근거
        """
        from dartlab.industry.build.pipeline import loadEdges

        allEdges = loadEdges()
        filtered = allEdges

        if industryId:
            filtered = [e for e in filtered if e.industry == industryId]
        if stockCode:
            filtered = [e for e in filtered if e.fromCode == stockCode or e.toCode == stockCode]

        if not filtered:
            return pl.DataFrame(
                schema={
                    "from코드": pl.Utf8,
                    "from이름": pl.Utf8,
                    "to코드": pl.Utf8,
                    "to이름": pl.Utf8,
                    "관계": pl.Utf8,
                    "산업": pl.Utf8,
                    "신뢰도": pl.Float64,
                    "소스": pl.Utf8,
                    "근거": pl.Utf8,
                }
            )

        return pl.DataFrame(
            {
                "from코드": [e.fromCode for e in filtered],
                "from이름": [e.fromName for e in filtered],
                "to코드": [e.toCode for e in filtered],
                "to이름": [e.toName for e in filtered],
                "관계": [e.edgeType for e in filtered],
                "산업": [e.industry for e in filtered],
                "신뢰도": [e.confidence for e in filtered],
                "소스": [e.source for e in filtered],
                "근거": [e.evidence for e in filtered],
            }
        )

    def map(self, industryId: str) -> Any:
        """IndustryDef 객체를 반환 (taxonomy 조회)."""
        from dartlab.industry.taxonomy import getIndustry

        return getIndustry(industryId)


def addOverride(
    industryId: str,
    stockCode: str,
    stage: str,
    *,
    corpName: str = "",
    note: str = "",
    confidence: float = 1.0,
) -> None:
    """overrides.json에 확정 매핑을 추가/갱신한다.

    AI가 코드 실행 루프에서 호출하여 오분류를 보정한다.

    Parameters
    ----------
    industryId : str
        산업 ID (예: "semiconductor").
    stockCode : str
        종목코드.
    stage : str
        공정 단계 key (예: "equipment").
    corpName : str
        회사명 (선택).
    note : str
        보정 근거 (선택).
    confidence : float
        신뢰도 (기본 1.0).
    """
    ovFile = _DATA_DIR / "overrides.json"
    data: dict = {}
    if ovFile.exists():
        try:
            data = json.loads(ovFile.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            data = {}

    ovList = data.setdefault(industryId, [])

    # 기존 항목 갱신 또는 추가
    for ov in ovList:
        if ov.get("stockCode") == stockCode:
            ov["stage"] = stage
            ov["confidence"] = confidence
            if corpName:
                ov["corpName"] = corpName
            if note:
                ov["note"] = note
            break
    else:
        entry: dict = {"stockCode": stockCode, "stage": stage, "confidence": confidence}
        if corpName:
            entry["corpName"] = corpName
        if note:
            entry["note"] = note
        ovList.append(entry)

    ovFile.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
