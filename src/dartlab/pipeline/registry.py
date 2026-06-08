"""STAGES 레지스트리 — category → StageSpec(run 함수) 매핑 SSOT.

각 stage 모듈이 ``run*`` 함수를 제공하고, 본 레지스트리가 category 명으로 묶는다.
orchestrator/CLI/__main__ 이 이 레지스트리만 보고 dispatch — 새 stage 추가는 여기
한 줄 등록이면 끝. 순환 회피 위해 stage 모듈은 lazy import(함수 내부).
"""

from __future__ import annotations

from dartlab.pipeline.types import StageSpec

# recent set — `dartlab sync`(인자 없음) 기본 수집 카테고리.
# DART 공시 본문은 panel SSOT 이므로 finance/report/panel 만 유지.
RECENT_SET: tuple[str, ...] = ("finance", "report", "panel")


def buildRegistry() -> dict[str, StageSpec]:
    """전 stage 를 lazy import 해 {category: StageSpec} 레지스트리 구성.

    Returns:
        category → StageSpec dict.

    Raises:
        없음.

    Example:
        >>> "finance" in buildRegistry()
        True
    """
    from dartlab.pipeline.stages import allFilings, dart, dartZip, edgar, edgarPanel, krx, macro, news, reconcile

    specs: list[StageSpec] = [
        StageSpec("finance", run=dart.runDartRecent, uploadCategories=("finance",), label="DART 재무 (증분)"),
        StageSpec("report", run=dart.runDartRecent, uploadCategories=("report",), label="DART 보고서 (증분)"),
        StageSpec(
            "allFilings",
            run=allFilings.runAllFilings,
            uploadCategories=("allFilings",),
            label="DART 비정기 공시 일별 parquet (forward 7일 증분)",
        ),
        StageSpec(
            "allFilingsReconcile",
            run=allFilings.runAllFilingsReconcile,
            uploadCategories=("allFilings",),
            label="DART allFilings 로컬↔HF 양방향 reconcile (운영자 트리거)",
        ),
        StageSpec("full", run=dart.runDartFull, uploadCategories=("finance", "report"), label="DART 88분기 전수"),
        StageSpec(
            "newStocks",
            run=dart.runDartNewStocks,
            uploadCategories=("finance", "report"),
            label="DART 신규상장 부트스트랩",
        ),
        StageSpec("panel", run=dart.runDartPanel, uploadCategories=("panel",), label="DART panel 수평화"),
        StageSpec(
            "dartZip",
            run=dartZip.runDartZip,
            uploadCategories=("dartOriginal", "panel"),
            label="DART 정기 원본 zip archive + panel 빌드 (Job 1, 증분)",
        ),
        StageSpec(
            "edgarPanel",
            run=edgarPanel.runEdgarPanel,
            uploadCategories=("edgarPanel",),
            label="EDGAR panel per-filing 증분 (Job 3, daily-index 발견→append)",
        ),
        StageSpec(
            "panelReconcile",
            run=reconcile.runPanelReconcile,
            uploadCategories=("panel",),
            label="DART panel 로컬↔HF 양방향 reconcile (운영자 트리거)",
        ),
        StageSpec(
            "edgarPanelReconcile",
            run=reconcile.runEdgarPanelReconcile,
            uploadCategories=("edgarPanel",),
            label="EDGAR panel 로컬↔HF 양방향 reconcile (운영자 트리거)",
        ),
        StageSpec("krx", run=krx.runKrx, uploadCategories=("krxPrices",), label="KRX 일별 가격"),
        StageSpec("krxIndex", run=krx.runKrxIndex, uploadCategories=("krxIndices",), label="KRX 지수"),
        StageSpec("macro", run=macro.runMacro, uploadCategories=("macroFred", "macroEcos"), label="거시 FRED/ECOS"),
        StageSpec("news", run=news.runNewsHeadlines, uploadCategories=("newsHeadlines",), label="뉴스 헤드라인"),
        StageSpec(
            "edgar",
            run=edgar.runEdgar,
            uploadCategories=("edgar", "edgarMeta"),
            label="EDGAR 벌크+분기(companyfacts/sub/pre/tag)",
        ),
    ]
    return {s.category: s for s in specs}
