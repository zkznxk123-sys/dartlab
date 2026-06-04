"""edgarPanel stage (Job 3) — EDGAR panel **per-filing 증분** + deploy.

원본=SSOT 전략([[project_original_ssot_strategy]]): EDGAR = panel only(fetch→build→raw 폐기).
EDGAR panel 빌드는 *회사당 전체 재빌드*(``buildEdgarPanel`` 이 cik 디렉터리 전 ``.txt`` 재독)라
raw 를 폐기하면 클린 러너에서 증분이 원천 불가했다(옛 daily job = 0행 no-op). 본 stage 는 그
모순을 **per-filing append** 로 해소한다:

  ① SEC daily-index(``master.idx``)로 최근 N일 재무 공시 발견(윈도 일수만큼의 요청).
  ② cik→상장 universe ticker 매핑 → 영향 ticker 만 추림.
  ③ 영향 ticker 의 기존 ``edgar/panel``·``edgar/panelCell`` 을 HF 에서 selective seed.
  ④ seed 성공(기존 종목) → 신규 accession 의 .txt 만 받아 ``appendFilingsToPanel``(중복 dedup).
     404(신규 종목) → 전체 history archive + ``buildEdgarPanel(overwrite=True)``.
  ⑤ 변경 ticker 만 deploy → 받은 raw .txt 폐기.

``EDGAR_FULL_REBUILD=1`` 이면 전 universe archive+재빌드 부트스트랩(무겁다 — 디스크 floor 가드 +
dispatch 전용). lookback 은 ``SYNC_LOOKBACK_DAYS``/``EDGAR_LOOKBACK`` env(기본 7). raw 폐기는
``EDGAR_DISCARD_RAW``(기본 1, 로컬 보존 시 0).

알려진 한계: 정정 보고서(``10-K/A`` 등 amended form)는 현재 discovery/parse 에서 제외 —
원본 form 만 반영(staleness, 손상 X). 정정 supersede 는 dedup 키를 accession→period 로 바꾸는
후속 작업 필요(regular form 은 period 가 고유라 안전하나 별도 검증 동반). → TODO.
"""

from __future__ import annotations

import os
import shutil
from datetime import date, timedelta
from pathlib import Path

from dartlab.pipeline.types import PipelineMode, StageResult

_REGULAR_FORMS = ("10-K", "10-Q", "20-F", "40-F")


def _recentDates(days: int) -> list[str]:
    """오늘 포함 최근 ``days`` 일의 YYYYMMDD 리스트(최신→과거)."""
    today = date.today()
    return [(today - timedelta(days=i)).strftime("%Y%m%d") for i in range(days)]


def _universeTickerByCik() -> dict[str, list[str]]:
    """상장 universe 의 ``{cik(10-pad): [ticker, ...]}`` 맵 — daily-index cik 를 ticker 로 해소.

    한 CIK 가 여러 ticker(주식 클래스 GOOG/GOOGL, BRK.A/BRK.B 등)를 가지므로 **list** 로
    모은다 — 단일 맵이면 한 클래스만 갱신되고 나머지는 영구 stale.

    Returns:
        dict[str, list[str]] — cik→ticker list. universe 부재/컬럼 부재 시 빈 dict(honest skip).
    """
    try:
        from dartlab.core.dataLoader import loadEdgarListedUniverse

        # 일간 증분은 universe 를 *강제 갱신* — TTL(24h) 안의 stale universe 면 지난 24h 신규 상장
        # (IPO)의 CIK 가 빠져 daily-index 의 그 공시가 조용히 누락되고 0 changed 로 녹색 보고된다.
        # forceUpdate fetch 실패 시엔 universe.updateListedUniverse 가 stale 캐시를 서빙(무중단).
        uni = loadEdgarListedUniverse(forceUpdate=True)
    except Exception:  # noqa: BLE001 — universe 부재면 빈 맵(상위가 0 changed 로 보고)
        return {}
    if "cik" not in uni.columns or "ticker" not in uni.columns:
        return {}
    out: dict[str, list[str]] = {}
    for c, t in zip(uni["cik"].to_list(), uni["ticker"].to_list()):
        if t and c is not None:
            out.setdefault(str(c).strip().zfill(10), []).append(str(t).strip())
    return out


def _seedTickerPanel(ticker: str, *, token: str | None) -> bool | None:
    """영향 ticker 의 기존 panel/panelCell 을 HF 에서 받아 로컬 배치 — append 전제.

    Returns:
        bool | None — True=기존 panel seed(증분 append 대상), False=404 신규 종목(full build),
        None=일시 실패(이번 run skip).
    """
    from huggingface_hub import hf_hub_download
    from huggingface_hub.utils import EntryNotFoundError, RepositoryNotFoundError

    import dartlab.config as cfg
    from dartlab.core.dataConfig import HF_REPO
    from dartlab.core.hfRetry import retryHfCall
    from dartlab.pipeline.hfUpload import _resolveHfToken

    root = str(Path(cfg.dataDir))
    tok = _resolveHfToken(token)
    try:
        retryHfCall(
            hf_hub_download,
            repo_id=HF_REPO,
            repo_type="dataset",
            filename=f"edgar/panel/{ticker.upper()}.parquet",
            token=tok,
            local_dir=root,
        )
    except (EntryNotFoundError, RepositoryNotFoundError):
        return False  # 신규 종목 — HF 미존재(404)
    except Exception as exc:  # noqa: BLE001 — 일시 실패 → skip(다음 run)
        # 근본 원인 관측화 — 호출부는 None 만 받아 exc 를 잃으므로 여기서 1줄 남긴다(간헐 패턴 추적).
        print(f"[pipeline] edgarPanel seed {ticker} panel 일시실패: {type(exc).__name__}: {exc}", flush=True)
        return None
    # panelCell: 404(셀 0 종목)는 정상이나 *일시 실패*는 unsafe — append 시 기존 셀
    # 전체를 덮어쓰는 손실(board 와 동일 클래스)이라 None 으로 이번 run skip.
    try:
        retryHfCall(
            hf_hub_download,
            repo_id=HF_REPO,
            repo_type="dataset",
            filename=f"edgar/panelCell/{ticker.upper()}.parquet",
            token=tok,
            local_dir=root,
        )
    except (EntryNotFoundError, RepositoryNotFoundError):
        pass  # 셀 0 종목 — 정상
    except Exception as exc:  # noqa: BLE001 — 일시 실패 → 기존 셀 손실 방지 위해 이번 run skip
        print(f"[pipeline] edgarPanel seed {ticker} panelCell 일시실패: {type(exc).__name__}: {exc}", flush=True)
        return None
    return True


def _runIncremental(res: StageResult, *, lookback: int, upload: bool, token: str | None) -> StageResult:
    """per-filing 증분: daily-index 발견 → 영향 ticker append/build → 변경분 deploy."""
    import dartlab.config as cfg
    from dartlab.gather.original.edgar.collect import (
        archiveEdgarOriginals,
        fetchFilings,
        listRecentFilings,
    )
    from dartlab.providers.edgar.panel.build import (
        appendFilingsToPanel,
        buildEdgarPanel,
        existingAccessions,
    )

    dates = _recentDates(lookback)

    # 0. builder cik 해소용 tickers.parquet 보장(클린 러너엔 부재 — 없으면 신규 종목 full-build 가
    #    cik 미해소로 0행). loadTickers 가 SEC company_tickers.json(UA 설정)로 자체 생성.
    try:
        from dartlab.gather.edgar.identity import loadTickers

        loadTickers(refresh=False)
    except Exception as exc:  # noqa: BLE001 — 실패해도 진행(해소 안 되는 신규 종목만 skip)
        res.report.failures.append(f"edgar tickers seed: {type(exc).__name__}: {exc}")

    # 1. 최근 공시 발견 (daily-index, 재무 폼만)
    try:
        rows = listRecentFilings(dates, forms=_REGULAR_FORMS)
    except Exception as exc:  # noqa: BLE001 — 발견 실패 격리
        res.report.err = 1
        res.report.failures.append(f"edgar listRecent: {type(exc).__name__}: {exc}")
        print(f"[pipeline] edgarPanel listRecent 실패(격리): {exc}", flush=True)
        return res

    # 2. cik → 상장 universe ticker(주식클래스 다중) 매핑 → CIK 그룹
    tickerByCik = _universeTickerByCik()
    if not tickerByCik:
        # universe 는 loadEdgarListedUniverse 가 SEC 에서 자체 fetch — 비면 SEC 차단/장애 등
        # *진짜 실패*다. 조용한 ok(녹색) 가 아니라 err=1 로 CI 를 red 로(silent no-op 방지).
        res.report.err = 1
        res.report.failures.append("edgar universe 부재(listedUniverse SEC fetch 실패) — 증분 불가")
        print("[pipeline] edgarPanel: universe 부재 → 실패(err)", flush=True)
        return res
    byCik: dict[str, list] = {}
    for r in rows:
        if r["cik"] in tickerByCik:
            byCik.setdefault(r["cik"], []).append(r)
    if not byCik:
        res.report.ok = 1
        print(f"[pipeline] edgarPanel: 최근 {lookback}일 universe 신규 재무공시 0", flush=True)
        return res

    sinceYear = int(os.environ.get("EDGAR_SINCE_YEAR") or "2015")
    discardRaw = os.environ.get("EDGAR_DISCARD_RAW", "1") == "1"  # 로컬 dev 는 0 으로 보존 가능
    changed: list[str] = []
    for cik, crows in byCik.items():
        cikComplete = True  # 이 CIK 의 모든 ticker 가 완전 처리됐는가 — raw 폐기 안전 판정
        for ticker in tickerByCik[cik]:  # 한 CIK 의 모든 ticker(공유 클래스 전부 갱신)
            try:
                seeded = _seedTickerPanel(ticker, token=token)
                if seeded is None:
                    res.report.failures.append(f"edgar seed {ticker}: 일시 실패 skip(다음 run 재시도)")
                    cikComplete = False  # 일시 실패 → 미완(raw 보존, 다음 run 재시도)
                    continue
                if seeded:  # 기존 종목 — 신규 accession 만 append
                    existing = existingAccessions(ticker)
                    newRows = [r for r in crows if r["accession_no"] not in existing]
                    if not newRows:
                        continue
                    grouped = fetchFilings(newRows)
                    paths = [p for ps in grouped.values() for p in ps]
                    if not paths:
                        continue
                    stat = appendFilingsToPanel(ticker, paths, verbose=False)
                    if stat["appended"]:
                        changed.append(ticker)
                else:  # 신규 종목 — 전체 history archive + 빌드
                    arc = archiveEdgarOriginals(
                        [ticker], forms=list(_REGULAR_FORMS), sinceYear=sinceYear, showProgress=False
                    )
                    # archiveEdgarOriginals 는 개별 공시 실패를 raise 없이 error 카운트로 흡수한다.
                    # error>0 = 불완전 이력 — 그대로 빌드+upload 하면 부분 panel 이 '완전'으로 박제되고
                    # 이후 append 가 그 위에서만 진행돼 빠진 이력이 영구 누락(silent gap). skip 후
                    # raw 보존 → 다음 run 이 full-build 재시도.
                    if arc.get("error"):
                        res.report.failures.append(
                            f"edgar new {ticker}: archive error={arc['error']} → 불완전, skip(다음 run 재시도)"
                        )
                        cikComplete = False
                        continue
                    stat = buildEdgarPanel(ticker, overwrite=True, verbose=False)
                    if stat.get("rows"):
                        changed.append(ticker)
            except Exception as exc:  # noqa: BLE001 — ticker 단위 격리(1건 실패가 run 중단 X)
                res.report.failures.append(f"edgar ticker {ticker}: {type(exc).__name__}: {exc}")
                cikComplete = False  # 예외 → 미완(raw 보존)
                continue
        # raw 폐기는 *완전 처리된* CIK 만 — 부분 실패(일시/예외/archive error)면 raw 를 보존해
        # 다음 run 이 빠진 이력을 재수집하게 한다(데이터 완전성 > 디스크 절약).
        if discardRaw and cikComplete:
            shutil.rmtree(Path(cfg.dataDir) / "original" / "edgar" / "docs" / cik, ignore_errors=True)

    res.rows = len(changed)
    res.changedFiles = [f"{t.upper()}.parquet" for t in changed]
    res.report.ok = 1
    print(f"[pipeline] edgarPanel 증분: 영향 CIK {len(byCik)} 중 {len(changed)} ticker 변경", flush=True)

    # 3. deploy(변경분만)
    if upload and changed:
        from dartlab.pipeline.hfUpload import uploadCategoryToHf

        cf = [f"{t.upper()}.parquet" for t in changed]
        for cat in ("edgarPanel", "edgarPanelCell"):
            try:
                uploadCategoryToHf(cat, changedFiles=cf, token=token)
            except Exception as exc:  # noqa: BLE001 — deploy 격리
                res.report.fail = 1
                res.report.failures.append(f"deploy {cat}: {type(exc).__name__}: {exc}")
                print(f"[pipeline] edgarPanel deploy {cat} 실패(격리): {exc}", flush=True)
    return res


def _runFullRebuild(res: StageResult, *, upload: bool, token: str | None) -> StageResult:
    """전 universe archive + 재빌드 부트스트랩 — 무겁다(dispatch 전용, 디스크 floor 가드)."""
    import dartlab.config as cfg

    floor = float(os.environ.get("EDGAR_DISK_FLOOR_GB") or "5")
    probe = Path(cfg.dataDir)
    while not probe.exists() and probe != probe.parent:  # 미존재/상대경로 대비 — 존재하는 상위로
        probe = probe.parent
    freeGb = shutil.disk_usage(str(probe)).free / 1e9
    if freeGb < floor:
        res.report.err = 1
        res.report.failures.append(f"edgar full-rebuild: 디스크 {freeGb:.1f}GB < floor {floor}GB — 중단")
        print(f"[pipeline] edgarPanel full-rebuild 중단: 디스크 {freeGb:.1f}GB", flush=True)
        return res

    try:
        from dartlab.core.dataLoader import loadEdgarListedUniverse
        from dartlab.gather.original.edgar.collect import archiveEdgarOriginals
        from dartlab.providers.edgar.panel.build import buildEdgarPanelAll

        uni = loadEdgarListedUniverse(forceUpdate=True)  # 전수 재빌드 — universe 도 최신(신규 상장 포함)
        tickers = [t for t in uni["ticker"].to_list() if t]
        sinceYear = int(os.environ.get("EDGAR_SINCE_YEAR") or "2015")
        archiveEdgarOriginals(tickers, forms=list(_REGULAR_FORMS), sinceYear=sinceYear, showProgress=False)
        results = buildEdgarPanelAll(None, overwrite=True, verbose=False)
        res.rows = sum(int(v.get("rows", 0)) for v in results.values()) if isinstance(results, dict) else 0
        res.report.ok = 1
    except Exception as exc:  # noqa: BLE001 — build 실패 격리
        res.report.err = 1
        res.report.failures.append(f"edgar full-rebuild: {type(exc).__name__}: {exc}")
        print(f"[pipeline] edgarPanel full-rebuild 실패(격리): {exc}", flush=True)
        return res

    if upload:
        from dartlab.pipeline.hfUpload import uploadCategoryToHf

        for cat in ("edgarPanel", "edgarPanelCell"):
            try:
                uploadCategoryToHf(cat, token=token)
            except Exception as exc:  # noqa: BLE001 — deploy 격리
                res.report.fail = 1
                res.report.failures.append(f"deploy {cat}: {type(exc).__name__}: {exc}")
    return res


def runEdgarPanel(
    *,
    category: str = "edgarPanel",
    mode: PipelineMode = "incremental",
    codes: list[str] | None = None,
    upload: bool = True,
    token: str | None = None,
) -> StageResult:
    """EDGAR panel per-filing 증분(기본) 또는 전 universe 부트스트랩(``EDGAR_FULL_REBUILD=1``).

    Args:
        category: 미사용("edgarPanel" 고정).
        mode: ``"full"``/``"backfill"`` 이면 전 universe 부트스트랩(``EDGAR_FULL_REBUILD=1`` 동치).
            그 외(기본 incremental)는 per-filing 증분.
        codes: 미사용(daily-index 발견 기반).
        upload: HF deploy(edgarPanel/edgarPanelCell) 여부.
        token: HF 토큰.

    Returns:
        StageResult (rows=변경 ticker 수[증분]/총행수[full], changedFiles=변경 parquet).

    Raises:
        없음 (발견/seed/build/deploy 예외는 StageResult 로 격리).

    Example:
        >>> runEdgarPanel(upload=False)  # doctest: +SKIP
        StageResult(category='edgarPanel', ...)
    """
    res = StageResult(category="edgarPanel")
    fullRebuild = os.environ.get("EDGAR_FULL_REBUILD") == "1" or mode in ("full", "backfill")
    if fullRebuild:
        return _runFullRebuild(res, upload=upload, token=token)
    lookback = int(os.environ.get("SYNC_LOOKBACK_DAYS") or os.environ.get("EDGAR_LOOKBACK") or "7")
    return _runIncremental(res, lookback=lookback, upload=upload, token=token)
