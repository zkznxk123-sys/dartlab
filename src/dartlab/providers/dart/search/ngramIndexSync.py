"""ngramIndex HF Hub 동기화 — ngramIndex.py 분할 (규칙 3 LoC).

`ngramIndex.py` 862 LoC 가 규칙 3 임계 (>800) 위반. push / pull / iter helper
(~120 줄) 를 본 모듈로 분리. 호출자 호환 — ngramIndex.py 재내보내기.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterator

import polars as pl

import dartlab.config as _cfg
from dartlab.core.dataConfig import DATA_RELEASES
from dartlab.core.logger import getLogger

_log = getLogger(__name__)


def _stemIndexDir() -> Path:
    d = Path(_cfg.dataDir) / DATA_RELEASES["stemIndex"]["dir"]
    d.mkdir(parents=True, exist_ok=True)
    return d


def pushStemIndex(*, token: str | None = None) -> str:
    """stemIndex를 HuggingFace에 업로드.

    Args:
        token: 인자.

    Raises:
        없음.

    Example:
        >>> pushStemIndex(...)

    Returns:
        str — 결과 문자열.
    """
    from huggingface_hub import HfApi

    from dartlab.core.dataConfig import HF_REPO

    outDir = _stemIndexDir()
    hfDir = DATA_RELEASES["stemIndex"]["dir"]

    api = HfApi(token=token)
    api.upload_folder(
        repo_id=HF_REPO,
        folder_path=str(outDir),
        path_in_repo=hfDir,
        repo_type="dataset",
    )

    url = f"https://huggingface.co/datasets/{HF_REPO}/tree/main/{hfDir}"
    _log.info(f"[stemIndex] HF 업로드 완료: {url}")
    return url


def pullStemIndex(*, token: str | None = None, force: bool = False) -> Path:
    """HuggingFace에서 stemIndex 다운로드 → 즉시 검색 가능.

    Args:
        token: 인자.
        force: 인자.

    Raises:
        없음.

    Example:
        >>> pullStemIndex(...)

    Returns:
        Path — 저장 경로.
    """
    from huggingface_hub import snapshot_download

    from dartlab.core.dataConfig import HF_REPO
    from dartlab.core.messaging import emit

    outDir = _stemIndexDir()
    hfDir = DATA_RELEASES["stemIndex"]["dir"]

    if not force:
        npzPath = outDir / "stemIndex.npz"
        if npzPath.exists():
            from dartlab.providers.dart.search.ngramIndex import ngramStats as _ngramStats

            stats = _ngramStats()
            if stats["documents"] > 0:
                emit("stemindex:local", path=str(outDir))
                return outDir

    emit("stemindex:hf_start", repo=HF_REPO)
    _log.info("[cyan]⬇ HF[/] stemIndex (%s/%s)", HF_REPO, hfDir)
    try:
        snapshot_download(
            repo_id=HF_REPO,
            repo_type="dataset",
            allow_patterns=f"{hfDir}/**",
            local_dir=str(outDir.parent.parent.parent),
            token=token,
        )
    except (OSError, RuntimeError, ValueError) as e:
        emit("stemindex:hf_fail", error=str(e))
        _log.warning("[red]✗[/] stemIndex 다운로드 실패: %s", e)
        raise
    _log.info("[green]✓[/] stemIndex 다운로드 완료")

    global _cachedIndex, _cachedMeta
    _cachedIndex = None
    _cachedMeta = None

    from dartlab.providers.dart.search.ngramIndex import ngramStats as _ngramStats

    stats = _ngramStats()
    sizeStr = f"{stats['sizeMb']}MB ({stats['documents']:,}문서)"
    emit("stemindex:hf_done", sizeStr=sizeStr)
    return outDir


def iterNgram(
    query: str,
    *,
    corpCode: str | None = None,
    stockCode: str | None = None,
    limit: int = 10,
):
    """``searchNgram`` 의 iterator pair (룰 10).

    Args:
        query: 자연어 쿼리.
        corpCode: corp_code 필터.
        stockCode: 종목코드 필터.
        limit: 반환 건수.

    Yields:
        검색 결과 row dict.

    Example:
        >>> for row in iterNgram("유상증자", limit=5):
        ...     print(row.get("rcept_no"))

    Raises:
        없음.
    """
    from dartlab.providers.dart.search.ngramIndex import searchNgram

    df = searchNgram(query, corpCode=corpCode, stockCode=stockCode, limit=limit)
    if df is None or df.is_empty():
        return
    yield from df.iter_rows(named=True)
