"""dartZip stage (Job 1) — DART 정기보고서 원본 zip archive + panel 빌드 + HF.

원본=SSOT 전략([[project_original_ssot_strategy]]): 정기보고서(사업/분기/반기) document.xml
zip 을 보관(``dartlab-dart-original`` private, 회사당 tar 번들) + 그 zip 으로 14-col panel
빌드. ``archiveDartOriginals(scope="periodic")`` 가 신규 zip 받은 종목(``changedCodes``)을
반환 → 그 종목만 ① 회사당 tar 재번들 업로드(증분) ② **panel within-company 증분 빌드**
(``_buildPanelIncremental``: 신규 zip만 ``buildPanelFromStream`` merge=True 로 기존 parquet 에
period upsert — 전이력 재파싱 OOM 회피) ③ panel 변경분 업로드.

옛 full-rebuild(전 zip 재파싱 + 통째 overwrite)는 ``DART_PANEL_FULL_REBUILD=1`` 일 때만 — 빌드 단계
추출 로직 변경을 과거 전 period 에 전파하는 self-heal 용(EDGAR ``EDGAR_FULL_REBUILD`` 와 동형).

lookback 일수는 ``SYNC_LOOKBACK_DAYS`` env(기본 7).
"""

from __future__ import annotations

import os
import tarfile
import tempfile
from datetime import date, timedelta
from pathlib import Path

from dartlab.pipeline.types import PipelineMode, StageResult


def _seedChangedFromHf(codes: list[str], *, token: str | None) -> tuple[int, set[str]]:
    """변경 종목의 회사 tar 를 dartlab-dart-original 에서 받아 추출 — CI panel 빌드 전제.

    CI 러너엔 회사 zip 이력이 없으므로 archive 직후 변경 종목의 전체 tar 를 HF 에서
    내려받아 ``data/original/dart/docs/{code}/`` 에 풀어 ``buildPanelAll`` 이 완전 이력으로
    빌드하게 한다. 방금 archive 된 신규 zip 은 보존(같은 이름=동일 내용).

    **404(HF tar 미존재)와 일시 실패를 구분한다** — 이게 데이터 손실 가드의 핵심:
    404 면 *신규 종목*(이력 없음)이라 archive 분만으로 빌드해도 정당 → safe. 그러나
    네트워크/5xx 등 *일시 실패* 면 이력이 불완전한 채 빌드하면 잘린 panel 이 정상 HF
    panel 을, 부분 tar 가 원본 SSOT 를 덮어쓴다(영구 손실) → **unsafe → 빌드/업로드 제외**
    (다음 run 자연 회복). 호출부는 safe 집합만 build/bundle/upload 한다.

    Args:
        codes: 변경 종목코드 list.
        token: HF 토큰.

    Returns:
        tuple[int, set[str]] — (seed 한 종목 수, *안전* 종목 집합 = seed 성공 ∪ 404 신규).

    Raises:
        없음 (종목별 미존재/일시실패는 분기 처리).

    Example:
        >>> _seedChangedFromHf(["005930"], token=None)  # doctest: +SKIP
        (1, {'005930'})
    """
    from huggingface_hub import hf_hub_download
    from huggingface_hub.utils import EntryNotFoundError, RepositoryNotFoundError

    import dartlab.config as cfg
    from dartlab.core.dataConfig import repoFor
    from dartlab.core.hfRetry import retryHfCall
    from dartlab.pipeline.hfUpload import _resolveHfToken

    base = Path(cfg.dataDir) / "original" / "dart" / "docs"
    repo = repoFor("dartOriginal")
    tok = _resolveHfToken(token)
    n = 0
    safe: set[str] = set()
    for code in codes:
        try:
            local = retryHfCall(
                hf_hub_download, repo_id=repo, repo_type="dataset", filename=f"docs/{code}.tar", token=tok
            )
        except (EntryNotFoundError, RepositoryNotFoundError):
            safe.add(code)  # 신규 종목 — HF 미존재(404) → archive 분만으로 빌드 정당
            continue
        except Exception:  # noqa: BLE001 — 일시 실패(네트워크/5xx) → 이력 불완전, build/upload 제외
            continue
        dest = base / code
        dest.mkdir(parents=True, exist_ok=True)
        # 무결성 검증: 추출된 zip 수가 tar 멤버 수 이상이어야 *완전* 이력. dest 에 바로 풀면 이전
        # run 잔재 zip 이 카운트를 부풀려 *부분 추출*을 통과시킨다(idempotency 위반) → 격리된 임시
        # 디렉터리에 풀어 거기서 검증 후 통과분만 dest 로 옮긴다(잔재 오염 0). 부분 추출이면 unsafe →
        # 제외(부분 이력으로 빌드+재번들하면 정상 panel·원본 tar 를 잘라 덮어쓰는 컴파운딩 truncation).
        # 통과 시 dest ⊇ tar 보장 → _bundleAndUpload 재번들은 항상 superset(축소 0).
        try:
            with tarfile.open(local, "r") as tf:
                memberCount = sum(1 for m in tf.getmembers() if m.isfile())
                with tempfile.TemporaryDirectory(dir=str(base)) as td:
                    tf.extractall(td, filter="data")  # 평탄 zip 파일명만 — filter='data' 안전 추출
                    extracted = list(Path(td).glob("*.zip"))
                    if len(extracted) < memberCount:
                        raise OSError(f"부분 추출 {code}: zip {len(extracted)} < tar 멤버 {memberCount}")
                    for z in extracted:  # 검증 통과분만 dest 로 이동(동일 fs atomic per-file rename)
                        z.replace(dest / z.name)
        except Exception as exc:  # noqa: BLE001 — tar 손상/부분추출 → unsafe(이번 run 제외, 다음 회복)
            print(f"[pipeline] dartZip seed {code} 무결성 실패(제외): {exc}", flush=True)
            continue
        n += 1
        safe.add(code)
    return n, safe


def _seedPanelFromHf(codes: list[str], *, token: str | None) -> tuple[int, set[str]]:
    """변경 종목의 기존 panel parquet 를 HF 에서 받아 merge base 배치 — 증분 데이터손실 가드.

    증분 빌드(``buildPanelFromStream`` merge=True)는 기존 ``data/dart/panel/{code}.parquet`` 을 읽어
    이번 신규 분기 period 만 교체하고 나머지 period 를 보존한다. CI 러너엔 그 기존 파일이 없으므로 빌드
    전 HF ``panel`` repo 에서 받아 merge base 로 깔아둔다 (``_seedChangedFromHf`` 가 zip 이력을 받는 것의
    panel 짝). **404 와 일시 실패를 구분** — 이게 데이터 손실 가드의 핵심: 404 면 *신규 종목*(HF panel
    미존재) 이라 base 없이 merge=신규 전부 write 가 정당(잃을 이력 0) → safe. 네트워크/5xx 등 *일시 실패*
    면 base 부재로 merge 하면 신규 period 만 남아 *정상 HF panel 을 파괴적으로 덮어쓴다*(history 소실) →
    **unsafe → 빌드/업로드 제외**(다음 run 자연 회복). 호출부는 safe 집합만 build/upload 한다.

    Args:
        codes: 변경 종목코드 list.
        token: HF 토큰.

    Returns:
        tuple[int, set[str]] — (seed 한 종목 수, *안전* 종목 집합 = seed 성공 ∪ 404 신규).

    Raises:
        없음 (종목별 미존재/일시실패는 분기 처리).

    Example:
        >>> _seedPanelFromHf(["005930"], token=None)  # doctest: +SKIP
        (1, {'005930'})
    """
    from huggingface_hub import hf_hub_download
    from huggingface_hub.utils import EntryNotFoundError, RepositoryNotFoundError

    import dartlab.config as cfg
    from dartlab.core.dataConfig import DATA_RELEASES, repoFor
    from dartlab.core.hfRetry import retryHfCall
    from dartlab.pipeline.hfUpload import _resolveHfToken

    relDir = DATA_RELEASES["panel"]["dir"]  # "dart/panel" — local_dir 하위로 풀려 merge base 위치와 일치
    repo = repoFor("panel")
    tok = _resolveHfToken(token)
    n = 0
    safe: set[str] = set()
    for code in codes:
        try:
            retryHfCall(  # HF read SSOT(core.hfRetry) — 429/503/504 단일 백오프
                hf_hub_download,
                repo_id=repo,
                repo_type="dataset",
                filename=f"{relDir}/{code}.parquet",
                local_dir=str(cfg.dataDir),  # → data/dart/panel/{code}.parquet (merge base)
                token=tok,
            )
        except (EntryNotFoundError, RepositoryNotFoundError):
            safe.add(code)  # 신규 종목 — HF panel 미존재(404) → base 없이 merge=신규 전부 write 정당
            continue
        except Exception:  # noqa: BLE001 — 일시 실패(네트워크/5xx): merge base 부재 → 파괴적 덮어쓰기 가드로 제외
            continue
        n += 1
        safe.add(code)
    return n, safe


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


def _buildPanelIncremental(
    changed: list[str], newZipsByCode: dict[str, list[Path]], res: StageResult, *, token: str | None
) -> list[str]:
    """within-company 증분 panel 빌드 — 신규 zip만 파싱해 기존 parquet 에 period upsert(merge=True).

    각 변경 종목의 *방금 archive 된* zip(``newZipsByCode``)을 bytes 로 읽어 ``buildPanelFromStream``
    (merge=True) 에 흘린다. ``_readZip``↔``_readZipBytes`` 가 동일 ``_zipToXmls`` 코어라 디스크 zip 을
    bytes 로 먹여도 ``buildPanel`` 과 row-동형 — 전이력 lxml 재파싱(거대 금융지주 OOM 근본)을 제거한다.
    빌드 전 HF panel parquet 을 merge base 로 seed(``_seedPanelFromHf``); base 부재(일시 실패) 종목은
    history 파괴적 덮어쓰기 방지로 제외. 순차 루프는 ``onlinePanel.py`` 의 검증된 패턴(per-corp stream)과
    동형이되 신규 zip만 파싱이라 더 가벼움(메모리 bound). 종목 단위 예외 격리(한 종목 실패가 나머지 안 막음).

    Args:
        changed: 변경 종목코드 list.
        newZipsByCode: ``{code: [신규 zip Path]}`` (archive 전후 차분).
        res: StageResult — 실패/제외 보고 누적(부수효과).
        token: HF 토큰.

    Returns:
        실제 빌드(merge)된 종목코드 list (panel upload 대상).

    Raises:
        없음 (종목별 예외는 res.report 로 격리).

    Example:
        >>> _buildPanelIncremental(["005930"], {"005930": [p]}, res, token=None)  # doctest: +SKIP
        ['005930']
    """
    import polars as pl

    import dartlab.config as cfg
    from dartlab.providers.dart.panel.build import buildPanelFromStream, panelXbrlRefPath

    try:
        pseeded, panelSafe = _seedPanelFromHf(changed, token=token)
    except Exception as exc:  # noqa: BLE001 — seed 전체 실패 → 이번 run 무빌드(안전)
        res.report.fail = 1
        res.report.failures.append(f"dartZip panel seed: {type(exc).__name__}: {exc}")
        return []
    pSkipped = [c for c in changed if c not in panelSafe]
    print(
        f"[pipeline] dartZip panel seed: {pseeded}/{len(changed)}종목 merge base · "
        f"빌드대상 {len(panelSafe)} · 제외(일시실패) {len(pSkipped)}",
        flush=True,
    )
    if pSkipped:
        res.report.failures.append(f"dartZip panel seed 불완전 {len(pSkipped)}종목 제외(다음 run 회복): {pSkipped[:5]}")

    refDf = pl.read_parquet(str(panelXbrlRefPath()))  # 패키지 동봉 ref 1회 로드(zip 부재라 자동 scan 금지)
    panelBase = Path(cfg.dataDir) / "dart" / "panel"
    built: list[str] = []
    for code in sorted(panelSafe):
        zips = newZipsByCode.get(code) or []
        if not zips:
            continue  # 신규 zip 없으면 merge 할 분기 없음 — skip
        stream = ((zp.stem, zp.read_bytes()) for zp in zips)  # zp.stem = rcept ({rcept}.zip)
        try:
            out = buildPanelFromStream(code, stream, refDf=refDf, outBaseDir=panelBase, overwrite=True)
            if out:
                built.append(code)
        except Exception as exc:  # noqa: BLE001 — 종목 단위 격리(나머지 진행)
            res.report.failures.append(f"dartZip panel build {code}: {type(exc).__name__}: {exc}")
    print(f"[pipeline] dartZip panel 증분: {len(built)}/{len(panelSafe)}종목 merge(신규 분기만)", flush=True)
    return built


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
    import dartlab.config as cfg
    from dartlab.gather.original.dart.collect import archiveDartOriginals
    from dartlab.providers.dart.panel.build import buildPanelAll, panelXbrlRefPath

    days = int(os.environ.get("SYNC_LOOKBACK_DAYS") or "7")
    today = date.today()
    start = (today - timedelta(days=days - 1)).strftime("%Y%m%d")
    end = today.strftime("%Y%m%d")
    fullRebuild = os.environ.get("DART_PANEL_FULL_REBUILD", "0") == "1"
    res = StageResult(category="dartOriginal")
    docsBase = Path(cfg.dataDir) / "original" / "dart" / "docs"

    # 1. 정기보고서 원본 zip archive (idempotent) → 변경 종목 + 신규 zip 차분(증분 빌드 입력).
    #    archive 전후 docs/*/*.zip 집합 차분으로 *방금 받은* zip 만 식별한다 (CI=빈 before·로컬=full
    #    before 모두 정상, archiveDartOriginals signature 무변경). 회사 1건 신규 공시 → 그 zip 만 파싱.
    zipsBefore = set(docsBase.glob("*/*.zip"))
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

    newZipsByCode: dict[str, list[Path]] = {}
    for zp in set(docsBase.glob("*/*.zip")) - zipsBefore:
        newZipsByCode.setdefault(zp.parent.name, []).append(zp)

    # 1.5 원본 tar 아카이브용 seed — 변경 종목 전체 zip 이력을 HF 에서 복원(러너 이력 0).
    #     _bundleAndUpload 가 로컬 zip 전체를 re-tar 해 HF docs/{code}.tar 를 덮으므로 full 이력 필수
    #     (부분 tar 업로드=원본 SSOT 파괴). 완전 복원(또는 404 신규) 종목만 archive-safe. ⚠ panel 증분
    #     빌드는 이 이력 zip 이 아니라 newZipsByCode(신규분)+panel parquet seed 를 쓴다(관심사 분리).
    if os.environ.get("DART_ZIP_SEED", "1") == "1":
        try:
            seeded, archiveSafe = _seedChangedFromHf(changed, token=token)
            skipped = [c for c in changed if c not in archiveSafe]
            print(
                f"[pipeline] dartZip seed: {seeded}/{len(changed)}종목 HF tar 추출 · "
                f"archive대상 {len(archiveSafe)} · 제외(이력불완전) {len(skipped)}",
                flush=True,
            )
            if skipped:
                res.report.failures.append(f"dartZip seed 불완전 {len(skipped)}종목 제외(다음 run 회복): {skipped[:5]}")
        except Exception as exc:  # noqa: BLE001 — seed 단계 전체 실패 → 이번 run 안전하게 무 archive
            res.report.fail = 1
            res.report.failures.append(f"dartZip seed: {type(exc).__name__}: {exc}")
            return res
    else:
        archiveSafe = set(changed)  # 로컬: 완전 이력 보유 전제(seed 불요)

    # 2. panel 빌드 — 기본 within-company 증분(신규 zip만 merge), DART_PANEL_FULL_REBUILD=1 시 전이력 재빌드.
    if fullRebuild:
        # self-heal: 빌드 단계 추출 로직 변경을 과거 전 period 에 전파(archive seed 의 full 이력 필요).
        panelBuilt = sorted(archiveSafe)
        try:
            buildPanelAll(
                refPath=str(panelXbrlRefPath()),
                codes=panelBuilt,
                numWorkers=int(os.environ.get("PANEL_WORKERS") or "2"),
                skipExisting=False,
                verbose=False,
            )
        except Exception as exc:  # noqa: BLE001 — build 실패 격리
            res.report.fail = 1
            res.report.failures.append(f"dartZip panel full-rebuild: {type(exc).__name__}: {exc}")
            print(f"[pipeline] dartZip panel full-rebuild 실패(격리): {exc}", flush=True)
    else:
        panelBuilt = _buildPanelIncremental(changed, newZipsByCode, res, token=token)

    res.changedFiles = panelBuilt

    # 3. 업로드 — 원본 zip tar 번들(archive-safe) + panel 변경분(실제 빌드분만).
    if upload:
        try:
            res.uploaded = _bundleAndUpload(sorted(archiveSafe), token=token)
        except Exception as exc:  # noqa: BLE001 — 업로드 실패 격리
            res.report.fail = 1
            res.report.failures.append(f"dartZip original upload: {type(exc).__name__}: {exc}")
        if panelBuilt:
            try:
                from dartlab.pipeline.hfUpload import uploadCategoryToHf

                uploadCategoryToHf("panel", changedFiles=[f"{c}.parquet" for c in panelBuilt], token=token)
            except Exception as exc:  # noqa: BLE001 — panel 업로드 실패 격리
                res.report.fail = 1
                res.report.failures.append(f"dartZip panel upload: {type(exc).__name__}: {exc}")
    return res
