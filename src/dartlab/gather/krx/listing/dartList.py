"""OpenDART 전체 법인 목록 (CORPCODE.xml) — HuggingFace 미러 + 24h TTL 캐시.

DART API 키 불필요 — eddmpython/dartlab-data HF dataset 에서 사전 빌드된
``metadata/dartList.parquet`` 다운로드. registry.py 의 KIND 목록과 별개.
"""

from __future__ import annotations

import logging
import threading
import time
from pathlib import Path

import polars as pl

from dartlab.gather.infra.ttl import TTL_LISTING as CACHE_TTL

log = logging.getLogger(__name__)


def _dartListCacheFile() -> Path:
    """OpenDART 법인 목록 캐시 파일 경로 반환.

    Returns
    -------
    Path
        ``{dataRoot}/dartList/dartList.parquet`` 경로.
    """
    from dartlab.core.dataLoader import _getDataRoot

    return _getDataRoot() / "dartList" / "dartList.parquet"


_dartMemory: pl.DataFrame | None = None
_dartMemoryTs: float = 0.0
_dartMemoryLock = threading.Lock()


def _loadDartListFromHf() -> pl.DataFrame | None:
    """HuggingFace에서 dartList.parquet 다운로드.

    ``eddmpython/dartlab-data`` 데이터셋에서 ``metadata/dartList.parquet`` 를 가져온다.
    huggingface_hub 미설치 또는 네트워크 실패 시 None.

    Returns
    -------
    pl.DataFrame | None
        corp_code : str — DART 고유 법인코드 (8자리)
        corp_name : str — 법인명
        stock_code : str — 종목코드 (6자리, 비상장은 빈 문자열)
        modify_date : str — 최종 수정일
    """
    try:
        from huggingface_hub import hf_hub_download

        path = hf_hub_download(
            repo_id="eddmpython/dartlab-data",
            repo_type="dataset",
            filename="metadata/dartList.parquet",
        )
        return pl.read_parquet(path)
    except (ImportError, OSError, ValueError, KeyError):
        return None


def getDartList(*, forceRefresh: bool = False) -> pl.DataFrame:
    """OpenDART 전체 법인 목록 (corp_code 8자리 매핑 포함).

    Capabilities: KIND (상장) 와 별개로 비상장 포함 DART 전수 법인 목록 + HF 캐시.
    AIContext: DART 공시 lookup, EDGAR 와 대비되는 KR 1차 출처 mapping SSOT.
    Guide: forceRefresh=True 시 HF 강제 재다운로드 (TTL 무시).
    When: DART corp_code ↔ 회사명 mapping 필요 (공시 조회, 비상장 포함) 시.
    How: 메모리 → 파일 → HuggingFace 3-tier fetch 후 캐시 저장.

    캐시 우선순위: 메모리 → 파일(24h TTL) → HuggingFace.
    DART API 키 불필요 — HuggingFace에서 자동 다운로드.

    Args:
        forceRefresh: True면 캐시 무시하고 HF에서 새로 다운로드.

    Returns:
        DataFrame (corp_code, corp_name, stock_code, modify_date).

    Raises:
        없음 — HF 다운로드 실패 시 캐시 fallback 또는 빈 DataFrame.

    Example:
        >>> df = getDartList()

    Requires:
        ``huggingface_hub`` 설치 + 네트워크 (``eddmpython/dartlab-data``). 미설치/네트워크
        실패 시 캐시 파일 또는 빈 DataFrame fallback. DART API 키 불필요.

    See Also:
        registry.getKindList : 상장 한정 (KIND).
        krxList.getKrxList : 상장 한정 (data.krx).
        resolver.codeToName : Protocol 위임 진입점.
    """
    global _dartMemory, _dartMemoryTs

    if not forceRefresh and _dartMemory is not None:
        if (time.time() - _dartMemoryTs) < CACHE_TTL:
            return _dartMemory

    with _dartMemoryLock:
        if not forceRefresh and _dartMemory is not None:
            if (time.time() - _dartMemoryTs) < CACHE_TTL:
                return _dartMemory

        cacheFile = _dartListCacheFile()
        if not forceRefresh and cacheFile.exists():
            age = time.time() - cacheFile.stat().st_mtime
            if age < CACHE_TTL:
                _dartMemory = pl.read_parquet(str(cacheFile))
                _dartMemoryTs = time.time()
                return _dartMemory

        from dartlab.core.messaging import emit

        emit("listing:dartlist:download")
        df = _loadDartListFromHf()
        if df is None or df.height == 0:
            log.warning("dartList HF 다운로드 실패")
            if cacheFile.exists():
                _dartMemory = pl.read_parquet(str(cacheFile))
                _dartMemoryTs = time.time()
                return _dartMemory
            return pl.DataFrame(
                schema={"corp_code": pl.Utf8, "corp_name": pl.Utf8, "stock_code": pl.Utf8, "modify_date": pl.Utf8}
            )

        cacheFile.parent.mkdir(parents=True, exist_ok=True)
        df.write_parquet(str(cacheFile))
        _dartMemory = df
        _dartMemoryTs = time.time()
        emit("listing:dartlist:done", count=df.height)
        return df
