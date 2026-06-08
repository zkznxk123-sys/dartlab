"""category 단위 로컬 ↔ HF 양방향 reconcile — flat per-entity 카테고리(panel·edgarPanel).

forward 파이프라인(dartZip/edgarPanel)은 *변경 종목만* push 한다. 본 모듈은 로컬·HF 의
**파일명 집합 차분**으로 합집합 수렴시킨다 — HF 에만 있으면 로컬로 pull, 로컬에만 있으면
HF 로 push. allFilings(날짜 immutable + ``_meta`` 보조파일)는 자체 reconcile
(``gather.dart.allFilingsSync.reconcileAllFilings``)을 갖고, 본 모듈은 회사당/티커당 1 parquet
인 flat 카테고리를 다룬다. 콘텐츠 신선도(같은 파일 내용 변화)는 forward 가 담당.
"""

from __future__ import annotations

from pathlib import Path


def reconcileCategory(
    category: str,
    *,
    pull: bool = True,
    push: bool = True,
    token: str | None = None,
    dataDir: str | None = None,
) -> dict:
    """flat per-entity 카테고리(panel·edgarPanel)를 로컬 ↔ HF 파일집합 차분으로 reconcile.

    로컬 ``{dir}/*.parquet`` 파일명 집합과 HF 동일 prefix 파일명 집합을 비교해:
        - **HF 에만 있음** → ``pull`` 이면 로컬로 다운로드(``downloadCategoryFiles``).
        - **로컬에만 있음** → ``push`` 이면 HF 로 업로드(``uploadCategoryToHf`` 증분).
    이미 양쪽에 있는 파일은 건드리지 않는다(idempotent). nested 카테고리는 거부한다.

    Args:
        category: ``DATA_RELEASES`` flat 카테고리 키 (예: ``"panel"``, ``"edgarPanel"``).
        pull: HF→로컬 (HF 에만 있는 파일 다운로드).
        push: 로컬→HF (로컬에만 있는 파일 업로드).
        token: HF 토큰. None 이면 env ``HF_TOKEN``.
        dataDir: 데이터 루트. None 이면 ``dartlab.config.dataDir``.

    Returns:
        dict — ``{"category", "localBefore", "remoteBefore", "pull", "push", "pulled",
        "pushed", "inSync"}``. ``inSync`` 는 활성 방향 기준 처리 대상 0 여부.

    Raises:
        ValueError: 미등록 category 또는 nested 카테고리.

    Example:
        >>> reconcileCategory("panel")  # doctest: +SKIP
        {'category': 'panel', 'localBefore': 2928, 'pulled': 13, 'pushed': 0, ...}

    Guide:
        - 운영자 로컬 머신용 — 영속 로컬 store ↔ HF 합집합 수렴. forward(변경분 push)와 보완.
        - 콘텐츠 변화(같은 회사 새 분기 추가)는 forward 재빌드→push 가 담당(본 reconcile 은 집합만).
    """
    import dartlab.config as _cfg
    from dartlab.core.dataConfig import DATA_RELEASES
    from dartlab.pipeline.hfUpload import uploadCategoryToHf
    from dartlab.pipeline.seed import downloadCategoryFiles, listRemoteFiles

    if category not in DATA_RELEASES:
        raise ValueError(f"unknown category '{category}' — {list(DATA_RELEASES)}")
    if DATA_RELEASES[category].get("nested"):
        raise ValueError(f"reconcileCategory 는 flat 카테고리만 — '{category}' 는 nested")

    dirPath = DATA_RELEASES[category]["dir"]
    root = Path(dataDir) if dataDir else Path(_cfg.dataDir)
    localDir = root / Path(dirPath)
    local = {f"{dirPath}/{p.name}" for p in localDir.glob("*.parquet")} if localDir.exists() else set()
    remote = {k for k in listRemoteFiles(category, token=token) if k.endswith(".parquet")}

    pullRels = sorted(remote - local) if pull else []
    pushRels = sorted(local - remote) if push else []

    pulled = 0
    if pullRels:
        pulled, _skip = downloadCategoryFiles(category, pullRels, dataDir=str(root), token=token)
    pushed = 0
    if pushRels:
        names = [r.rsplit("/", 1)[-1] for r in pushRels]  # category dir 기준 파일명
        uploadCategoryToHf(category, changedFiles=names, dataDir=str(root), token=token)
        pushed = len(names)

    return {
        "category": category,
        "localBefore": len(local),
        "remoteBefore": len(remote),
        "pull": len(pullRels),
        "push": len(pushRels),
        "pulled": pulled,
        "pushed": pushed,
        "inSync": not pullRels and not pushRels,
    }
