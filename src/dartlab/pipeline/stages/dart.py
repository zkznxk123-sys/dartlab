"""DART stage — recent(증분)/full(88분기)/newStocks/sections/panel.

W2 전환기: 검증된 sync 스크립트(syncRecent·syncData·syncNewStocks·buildSections·
onlinePanel/buildPanel)를 ``runScript`` 로 동형 호출 + ``uploadCategoryToHf`` 로 업로드.
후속 웨이브에서 본체를 인라인하며 스크립트는 shim 으로 역전한다.
"""

from __future__ import annotations

from dartlab.pipeline.changed import readChanged
from dartlab.pipeline.hfUpload import uploadCategoryToHf
from dartlab.pipeline.stages._runner import runScript
from dartlab.pipeline.types import PipelineMode, StageResult


def _result(category: str, rc: int, scriptLabel: str) -> StageResult:
    res = StageResult(category=category)
    if rc != 0:
        res.report.err = 1
        res.report.failures.append(f"{scriptLabel} rc={rc}")
    else:
        res.report.ok = 1
    return res


def _upload(res: StageResult, category: str, upload: bool, token: str | None) -> StageResult:
    """수집 성공 시 changed 매니페스트 기반 HF 업로드(격리)."""
    if not upload or res.report.err:
        return res
    try:
        res.changedFiles = readChanged(category)
        res.uploaded = uploadCategoryToHf(category, token=token)
    except Exception as exc:  # noqa: BLE001 — 업로드 실패 격리(다음 sync 자연 회복)
        res.report.fail = 1
        res.report.failures.append(f"upload {category}: {type(exc).__name__}: {exc}")
        print(f"[pipeline] {category} 업로드 실패(격리): {exc}", flush=True)
    return res


def runDartRecent(
    *,
    category: str,
    mode: PipelineMode = "recent",
    codes: list[str] | None = None,
    upload: bool = True,
    token: str | None = None,
) -> StageResult:
    """DART 증분 수집(finance/report/docs) — syncRecent 동형 + HF 업로드.

    Args:
        category: finance/report/docs.
        mode: 미사용(증분 고정).
        codes: 미사용(syncRecent 가 lookback 발견).
        upload: HF 업로드 여부.
        token: HF 토큰.

    Returns:
        StageResult.

    Raises:
        없음 (스크립트 rc·업로드 예외는 StageResult 로 격리).

    Example:
        >>> runDartRecent(category="finance", upload=False)  # doctest: +SKIP
        StageResult(category='finance', ...)
    """
    rc = runScript(".github/scripts/sync/syncRecent.py", env={"SYNC_CATEGORIES": category})
    return _upload(_result(category, rc, "syncRecent"), category, upload, token)


def runDartFull(
    *,
    category: str,
    mode: PipelineMode = "full",
    codes: list[str] | None = None,
    upload: bool = True,
    token: str | None = None,
) -> StageResult:
    """DART 88분기 전수 수집 — syncData 동형 + HF 업로드.

    Args:
        category: 업로드 카테고리.
        mode: 미사용(full 고정).
        codes: 미사용.
        upload: HF 업로드 여부.
        token: HF 토큰.

    Returns:
        StageResult.

    Raises:
        없음 (스크립트 rc·업로드 예외는 StageResult 로 격리).

    Example:
        >>> runDartFull(category="finance", upload=False)  # doctest: +SKIP
        StageResult(category='finance', ...)
    """
    rc = runScript(".github/scripts/sync/syncData.py")
    return _upload(_result(category, rc, "syncData"), category, upload, token)


def runDartNewStocks(
    *,
    category: str,
    mode: PipelineMode = "new",
    codes: list[str] | None = None,
    upload: bool = True,
    token: str | None = None,
) -> StageResult:
    """신규 상장 부트스트랩 — syncNewStocks 동형 + HF 업로드.

    Args:
        category: 업로드 카테고리.
        mode: 미사용(new 고정).
        codes: 미사용.
        upload: HF 업로드 여부.
        token: HF 토큰.

    Returns:
        StageResult.

    Raises:
        없음.

    Example:
        >>> runDartNewStocks(category="docs", upload=False)  # doctest: +SKIP
        StageResult(category='docs', ...)
    """
    rc = runScript(".github/scripts/sync/syncNewStocks.py")
    return _upload(_result(category, rc, "syncNewStocks"), category, upload, token)


def runDartSections(
    *,
    category: str = "sections",
    mode: PipelineMode = "changed",
    codes: list[str] | None = None,
    upload: bool = True,
    token: str | None = None,
) -> StageResult:
    """DART sections artifact 빌드 — buildSections 동형 + HF 업로드.

    Args:
        category: 미사용("sections" 고정).
        mode: 미사용(changed 고정).
        codes: 미사용.
        upload: HF 업로드 여부.
        token: HF 토큰.

    Returns:
        StageResult.

    Raises:
        없음.

    Example:
        >>> runDartSections(upload=False)  # doctest: +SKIP
        StageResult(category='sections', ...)
    """
    rc = runScript(".github/scripts/sync/buildSections.py")
    return _upload(_result("sections", rc, "buildSections"), "sections", upload, token)


def runDartPanel(
    *,
    category: str = "panel",
    mode: PipelineMode = "online",
    codes: list[str] | None = None,
    upload: bool = True,
    token: str | None = None,
) -> StageResult:
    """DART panel 수평화 — online(1-pass) 또는 offline(zip) + HF 업로드.

    online: onlinePanel(docs.parquet → stream → 14-col). offline: buildPanel(로컬 zip).
    refDf(panelXbrlRef) 부재 등 전제 미충족 시 stage 가 graceful skip(rc=0, 산출 0).

    Args:
        category: 미사용("panel" 고정).
        mode: "online"(기본) 또는 "offline".
        codes: 미사용.
        upload: HF 업로드 여부.
        token: HF 토큰.

    Returns:
        StageResult (전제 미충족 시 skipped=True).

    Raises:
        없음.

    Example:
        >>> runDartPanel(mode="online", upload=False)  # doctest: +SKIP
        StageResult(category='panel', skipped=True)
    """
    script = ".github/scripts/sync/onlinePanel.py" if mode == "online" else ".github/scripts/sync/buildPanel.py"
    rc = runScript(script)
    res = _result("panel", rc, "panel")
    if rc == 0 and not readChanged("panel"):
        res.skipped = True
    return _upload(res, "panel", upload, token)
