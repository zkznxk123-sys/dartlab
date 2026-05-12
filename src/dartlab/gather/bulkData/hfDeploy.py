"""HuggingFace 데이터셋 업로드 — KRX raw parquet (Mode 2 SSOT 의 publish 단).

운영자 cron (`.github/workflows/buildKrxData.yml`) 만 호출.
사용자 직접 호출 (`gather/krxApi.py`) 은 이 모듈 사용 안 함 — `engines.gather §9`.

EDGAR 의 `providers/edgar/openapi/deploy.deployEdgarToHF` 와 시그니처 일관.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

log = logging.getLogger(__name__)

# dartlab 표준 단일 dataset (`core/dataConfig.HF_REPO`) — DATA_RELEASES["krxPrices"] SSOT.
DEFAULT_REPO_ID = "eddmpython/dartlab-data"
DEFAULT_PATH_IN_REPO = "krx/prices"
DEFAULT_INDEX_PATH_IN_REPO = "krx/indices"


def deployKrxToHF(
    localDir: str | Path,
    *,
    repoId: str = DEFAULT_REPO_ID,
    pathInRepo: str = DEFAULT_PATH_IN_REPO,
    token: str | None = None,
) -> dict:
    """로컬 디렉토리의 ``raw-{YYYY}.parquet`` 들을 HF dataset repo 에 업로드.

    Capabilities:
        - 데이터셋 repo 자동 생성 (없을 때만, exist_ok=True)
        - 디렉토리 통째 upload_folder (변경된 파일만 commit)
        - HF_TOKEN 환경변수 또는 token 인자

    AIContext:
        - 운영자 cron 빌드의 마지막 단계 — 빌드된 parquet 을 공개 데이터셋으로 publish
        - 엔진 (quant/scan/analysis) 은 이 결과를 `_hfBulk.loadFiltered` 로 소비

    Guide:
        - workflow yml 에서 `HF_TOKEN: ${{ secrets.HF_TOKEN }}` 후 호출
        - 로컬 테스트는 `export HF_TOKEN=hf_...` 후 직접 호출 가능

    SeeAlso:
        - gather/krxApi.py — KRX OpenAPI 수집 (Mode 1)
        - gather/_hfBulk.py — 엔진 내부 HF 소비 (Mode 2)
        - engines.gather §9 — KRX 수집 경로 SSOT

    Args:
        localDir: 업로드할 로컬 디렉토리 (예: ``data/market/prices/kr``).
        repoId: HF dataset repo (``namespace/name``).
        pathInRepo: repo 내 디렉토리 (기본 ``"data"``).
        token: HF write token. None 이면 ``HF_TOKEN`` 환경변수 사용.

    Returns:
        dict — ``repoId``, ``pathInRepo``, ``files`` (업로드된 파일 수), ``commitUrl``.

    Raises:
        RuntimeError: HF_TOKEN 부재.
        FileNotFoundError: localDir 없음.

    When:
        ``.github/workflows/buildKrxData.yml`` cron 마지막 단계 / 로컬 dev 가 새 dataset
        publish 시.

    How:
        HF_TOKEN env / token 인자 → create_repo (exist_ok) → HfApi.upload_folder
        (디렉토리 통째, 변경 파일만 commit) → commit URL 반환.

    Requires:
        ``HF_TOKEN`` 환경변수 (또는 token 인자) + ``huggingface-hub`` 패키지.

    Example:
        >>> deployKrxToHF("data/market/prices/kr", token=os.environ["HF_TOKEN"])
    """
    from huggingface_hub import HfApi, create_repo

    tok = token or os.environ.get("HF_TOKEN", "").strip()
    if not tok:
        raise RuntimeError(
            "HF_TOKEN 미설정 — HuggingFace write token 이 필요합니다. "
            "https://huggingface.co/settings/tokens 에서 발급 후 "
            "환경변수 또는 GitHub Actions secret 으로 등록하세요."
        )

    src = Path(localDir)
    if not src.is_dir():
        raise FileNotFoundError(f"업로드 디렉토리 없음: {src}")

    files = sorted(p.name for p in src.glob("*.parquet"))
    if not files:
        log.warning("업로드 대상 parquet 0건: %s", src)
        return {"repoId": repoId, "pathInRepo": pathInRepo, "files": 0}

    create_repo(repoId, token=tok, repo_type="dataset", exist_ok=True)
    api = HfApi(token=tok)
    commit = api.upload_folder(
        folder_path=str(src),
        path_in_repo=pathInRepo,
        repo_id=repoId,
        repo_type="dataset",
        commit_message=f"build: KRX raw parquet ({len(files)} files)",
    )
    log.info("HF push: %s → %s/%s (%d files)", src, repoId, pathInRepo, len(files))
    return {
        "repoId": repoId,
        "pathInRepo": pathInRepo,
        "files": len(files),
        "commitUrl": getattr(commit, "commit_url", None),
    }


def deployKrxIndexToHF(
    localDir: str | Path,
    *,
    repoId: str = DEFAULT_REPO_ID,
    pathInRepo: str = DEFAULT_INDEX_PATH_IN_REPO,
    token: str | None = None,
) -> dict:
    """KRX 지수 raw parquet 을 HF dataset ``krx/indices`` 로 업로드.

    Capabilities: deployKrxToHF wrapper — 지수 path (``krx/indices``) 만 다름.
    AIContext: KRX 지수 bulk publish — ``buildKrxIndexData.yml`` cron 마지막 단계.
    Guide: pathInRepo 기본값만 다르고 본문은 deployKrxToHF 위임.
    When: 지수 bulk 빌드 + HF push 시.
    How: pathInRepo 를 ``krx/indices`` 로 고정 후 deployKrxToHF 위임.

    Args:
        localDir: 업로드 대상 parquet 들이 모인 로컬 디렉터리.
        repoId: HF dataset repo ID (예: ``"eddmpython/dartlab-data"``).
        pathInRepo: HF repo 내부 경로 (예: ``"krx/indices"``).
        token: HF 토큰. None이면 환경변수/세션 키 사용.

    Returns:
        ``{"uploaded": int, "files": int, "commitUrl": str | None}`` — 업로드 결과 요약.

    Raises:
        FileNotFoundError: ``localDir`` 부재.
        huggingface_hub.HfHubHTTPError: HF API 오류 (인증/권한/네트워크).

    Requires:
        ``HF_TOKEN`` 환경변수 + ``huggingface-hub`` 패키지.

    Example:
        >>> deployKrxIndexToHF("data/krx/indices", token=os.environ["HF_TOKEN"])

    See Also:
        deployKrxToHF : 위임 대상 (종목 prices path).
        scripts/build/buildKrxIndexData.py : 호출 caller (운영자 cron).
    """
    return deployKrxToHF(localDir, repoId=repoId, pathInRepo=pathInRepo, token=token)
