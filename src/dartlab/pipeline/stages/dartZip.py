"""dartZip stage (Job 1) — DART 정기보고서 원본 zip archive + panel 빌드 + HF.

원본=SSOT 전략([[project_original_ssot_strategy]]): 정기보고서(사업/분기/반기) document.xml
zip 을 보관(``dartlab-dart-original`` private, 회사당 tar 번들) + 그 zip 으로 14-col panel
빌드. ``archiveDartOriginals(scope="periodic")`` 가 신규 zip 받은 종목(``changedCodes``)을
반환 → 그 종목만 ① 회사당 tar 재번들 업로드(증분) ② ``buildPanelAll`` 증분 재빌드
(``skipExisting=False`` 로 변경 종목 overwrite) ③ panel 변경분 업로드.

lookback 일수는 ``SYNC_LOOKBACK_DAYS`` env(기본 7).
"""

from __future__ import annotations

import os
import tarfile
from datetime import date, timedelta
from pathlib import Path

from dartlab.pipeline.types import PipelineMode, StageResult


def _seedChangedFromHf(codes: list[str], *, token: str | None) -> int:
    """변경 종목의 회사 tar 를 dartlab-dart-original 에서 받아 추출 — CI panel 빌드 전제.

    CI 러너엔 회사 zip 이력이 없으므로 archive 직후 변경 종목의 전체 tar 를 HF 에서
    내려받아 ``data/original/dart/docs/{code}/`` 에 풀어 ``buildPanelAll`` 이 완전 이력으로
    빌드하게 한다. 방금 archive 된 신규 zip 은 보존(같은 이름=동일 내용). 신규 종목
    (HF tar 미존재)은 archive 분만으로 빌드.

    Args:
        codes: 변경 종목코드 list.
        token: HF 토큰.

    Returns:
        int — seed 한 종목 수.

    Raises:
        없음 (종목별 미존재는 skip).

    Example:
        >>> _seedChangedFromHf(["005930"], token=None)  # doctest: +SKIP
    """
    from huggingface_hub import hf_hub_download

    import dartlab.config as cfg
    from dartlab.core.dataConfig import repoFor
    from dartlab.core.hfRetry import retryHfCall
    from dartlab.pipeline.hfUpload import _resolveHfToken

    base = Path(cfg.dataDir) / "original" / "dart" / "docs"
    repo = repoFor("dartOriginal")
    tok = _resolveHfToken(token)
    n = 0
    for code in codes:
        try:
            local = retryHfCall(
                hf_hub_download, repo_id=repo, repo_type="dataset", filename=f"docs/{code}.tar", token=tok
            )
        except Exception:  # noqa: BLE001 — 신규 종목(HF 미존재) → seed 없이 archive 분만
            continue
        dest = base / code
        dest.mkdir(parents=True, exist_ok=True)
        with tarfile.open(local, "r") as tf:
            tf.extractall(dest, filter="data")  # 평탄 zip 파일명만 — filter='data' 안전 추출
        n += 1
    return n


def _bundleAndUpload(codes: list[str], *, token: str | None) -> int:
    """변경 종목의 zip 을 회사당 tar 로 묶어 dartlab-dart-original 에 증분 업로드.

    Args:
        codes: 변경 종목코드 list.
        token: HF 토큰.

    Returns:
        int — 업로드한 tar 수.

    Raises:
        없음 (호출부에서 격리).

    Example:
        >>> _bundleAndUpload(["005930"], token=None)  # doctest: +SKIP
    """
    from huggingface_hub import HfApi

    import dartlab.config as cfg
    from dartlab.core.dataConfig import repoFor
    from dartlab.core.hfRetry import retryHfCall
    from dartlab.pipeline.hfUpload import _resolveHfToken

    base = Path(cfg.dataDir) / "original" / "dart" / "docs"
    stage = Path(cfg.dataDir) / "original" / "_bundleStage" / "docs"
    stage.mkdir(parents=True, exist_ok=True)
    api = HfApi(token=_resolveHfToken(token))
    repo = repoFor("dartOriginal")
    n = 0
    for code in codes:
        d = base / code
        zips = sorted(d.glob("*.zip")) if d.exists() else []
        if not zips:
            continue
        tp = stage / f"{code}.tar"
        with tarfile.open(tp, "w") as tf:
            for z in zips:
                tf.add(z, arcname=z.name)
        retryHfCall(
            api.upload_file,
            path_or_fileobj=str(tp),
            path_in_repo=f"docs/{code}.tar",
            repo_id=repo,
            repo_type="dataset",
        )
        tp.unlink()
        n += 1
    return n


def runDartZip(
    *,
    category: str = "dartOriginal",
    mode: PipelineMode = "incremental",
    codes: list[str] | None = None,
    upload: bool = True,
    token: str | None = None,
) -> StageResult:
    """DART 정기보고서 zip archive(증분) + panel 빌드 + HF 업로드.

    Args:
        category: 미사용("dartOriginal" 고정).
        mode: 미사용(incremental 고정).
        codes: 미사용(날짜 윈도 기반 archive).
        upload: HF 업로드 여부.
        token: HF 토큰.

    Returns:
        StageResult (changedFiles=변경 종목, uploaded=업로드 tar 수).

    Raises:
        없음 (archive/build/upload 예외는 StageResult 로 격리).

    Example:
        >>> runDartZip(upload=False)  # doctest: +SKIP
        StageResult(category='dartOriginal', ...)
    """
    from dartlab.gather.original.dart.collect import archiveDartOriginals
    from dartlab.providers.dart.panel.build import buildPanelAll, panelXbrlRefPath

    days = int(os.environ.get("SYNC_LOOKBACK_DAYS") or "7")
    today = date.today()
    start = (today - timedelta(days=days - 1)).strftime("%Y%m%d")
    end = today.strftime("%Y%m%d")
    res = StageResult(category="dartOriginal")

    # 1. 정기보고서 원본 zip archive (idempotent) → 변경 종목
    try:
        stats = archiveDartOriginals(start, end, scope="periodic", showProgress=False)
        changed = list(stats.get("changedCodes") or [])
        res.changedFiles = changed
        res.report.ok = 1
        print(f"[pipeline] dartZip archive {start}~{end}: 변경 {len(changed)}종목", flush=True)
    except Exception as exc:  # noqa: BLE001 — archive 실패 격리
        res.report.err = 1
        res.report.failures.append(f"dartZip archive: {type(exc).__name__}: {exc}")
        print(f"[pipeline] dartZip archive 실패(격리): {exc}", flush=True)
        return res

    if not changed:
        return res

    # 1.5 CI 전제: 변경 종목 전체 zip 이력을 HF 에서 seed (러너엔 이력 0)
    if os.environ.get("DART_ZIP_SEED", "1") == "1":
        try:
            seeded = _seedChangedFromHf(changed, token=token)
            print(f"[pipeline] dartZip seed: {seeded}/{len(changed)}종목 HF tar 추출", flush=True)
        except Exception as exc:  # noqa: BLE001 — seed 실패는 빌드 진행(부분 이력)
            res.report.failures.append(f"dartZip seed: {type(exc).__name__}: {exc}")

    # 2. panel 증분 재빌드 (변경 종목만, offline zip → flat {code}.parquet)
    try:
        buildPanelAll(
            refPath=str(panelXbrlRefPath()),
            codes=changed,
            numWorkers=int(os.environ.get("PANEL_WORKERS") or "2"),
            skipExisting=False,
            verbose=False,
        )
    except Exception as exc:  # noqa: BLE001 — build 실패 격리
        res.report.fail = 1
        res.report.failures.append(f"dartZip panel build: {type(exc).__name__}: {exc}")
        print(f"[pipeline] dartZip panel build 실패(격리): {exc}", flush=True)

    # 3. 업로드 — 원본 zip tar 번들(증분) + panel 변경분
    if upload:
        try:
            res.uploaded = _bundleAndUpload(changed, token=token)
        except Exception as exc:  # noqa: BLE001 — 업로드 실패 격리
            res.report.fail = 1
            res.report.failures.append(f"dartZip original upload: {type(exc).__name__}: {exc}")
        try:
            from dartlab.pipeline.hfUpload import uploadCategoryToHf

            uploadCategoryToHf("panel", changedFiles=[f"{c}.parquet" for c in changed], token=token)
        except Exception as exc:  # noqa: BLE001 — panel 업로드 실패 격리
            res.report.fail = 1
            res.report.failures.append(f"dartZip panel upload: {type(exc).__name__}: {exc}")
    return res
