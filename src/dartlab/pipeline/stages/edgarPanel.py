"""edgarPanel stage (Job 3) — EDGAR 원본 archive + panel 빌드 + deploy.

원본=SSOT 전략([[project_original_ssot_strategy]]): EDGAR = panel only(fetch→build→raw 폐기).
기존 pipeline ``edgar`` stage 는 companyfacts/분기 **벌크**(별 경로) — 본 stage 가 panel 트랙.

흐름: (선택, ``EDGAR_ARCHIVE=1``) ``archiveEdgarOriginals`` 로 신규 txt fetch →
``buildEdgarPanelAll(overwrite=False)`` 증분 빌드(기존 board skip) → ``edgarPanel``/
``edgarPanelCell`` HF deploy. archive 는 무겁고(universe enumeration) rate-limited 이라
기본 off — 워크플로가 주간만 ``EDGAR_ARCHIVE=1`` 로 켜고, 일간은 build+deploy 만.
overwrite 는 ``EDGAR_PANEL_OVERWRITE=1`` 로 강제 재빌드.
"""

from __future__ import annotations

import os

from dartlab.pipeline.types import PipelineMode, StageResult

_REGULAR_FORMS = ["10-K", "10-Q", "20-F", "40-F"]


def runEdgarPanel(
    *,
    category: str = "edgarPanel",
    mode: PipelineMode = "incremental",
    codes: list[str] | None = None,
    upload: bool = True,
    token: str | None = None,
) -> StageResult:
    """EDGAR panel 빌드(증분) + deploy. 선택적 원본 archive(EDGAR_ARCHIVE=1).

    Args:
        category: 미사용("edgarPanel" 고정).
        mode: 미사용.
        codes: 미사용.
        upload: HF deploy(edgarPanel/edgarPanelCell) 여부.
        token: HF 토큰.

    Returns:
        StageResult.

    Raises:
        없음 (archive/build/deploy 예외는 StageResult 로 격리).

    Example:
        >>> runEdgarPanel(upload=False)  # doctest: +SKIP
        StageResult(category='edgarPanel', ...)
    """
    res = StageResult(category="edgarPanel")

    # 1. (선택) 원본 archive — 무겁고 rate-limited, 기본 off
    if os.environ.get("EDGAR_ARCHIVE") == "1":
        try:
            from dartlab.core.dataLoader import loadEdgarListedUniverse
            from dartlab.gather.original.edgar.collect import archiveEdgarOriginals

            universe = loadEdgarListedUniverse(forceUpdate=False)
            tickers = [t for t in universe["ticker"].to_list() if t]
            sinceYear = int(os.environ.get("EDGAR_SINCE_YEAR") or "2015")
            archiveEdgarOriginals(tickers, forms=_REGULAR_FORMS, sinceYear=sinceYear)
        except Exception as exc:  # noqa: BLE001 — archive 실패 격리(build 진행)
            res.report.fail = 1
            res.report.failures.append(f"edgar archive: {type(exc).__name__}: {exc}")
            print(f"[pipeline] edgarPanel archive 실패(격리): {exc}", flush=True)

    # 2. panel 빌드 — overwrite=False 면 기존 board skip(증분)
    try:
        from dartlab.providers.edgar.panel.build import buildEdgarPanelAll

        overwrite = os.environ.get("EDGAR_PANEL_OVERWRITE") == "1"
        results = buildEdgarPanelAll(None, overwrite=overwrite, verbose=False)
        res.rows = sum(int(v.get("rows", 0)) for v in results.values()) if isinstance(results, dict) else 0
        res.report.ok = 1
    except Exception as exc:  # noqa: BLE001 — build 실패 격리
        res.report.err = 1
        res.report.failures.append(f"edgar panel build: {type(exc).__name__}: {exc}")
        print(f"[pipeline] edgarPanel build 실패(격리): {exc}", flush=True)
        return res

    # 3. deploy — edgarPanel + edgarPanelCell (full folder, HF dedup)
    if upload:
        from dartlab.pipeline.hfUpload import uploadCategoryToHf

        for cat in ("edgarPanel", "edgarPanelCell"):
            try:
                uploadCategoryToHf(cat, token=token)
            except Exception as exc:  # noqa: BLE001 — deploy 실패 격리
                res.report.fail = 1
                res.report.failures.append(f"deploy {cat}: {type(exc).__name__}: {exc}")
                print(f"[pipeline] edgarPanel deploy {cat} 실패(격리): {exc}", flush=True)
    return res
