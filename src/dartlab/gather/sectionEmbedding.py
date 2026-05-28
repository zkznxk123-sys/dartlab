"""Section embedding cache — section_content → embedding parquet.

runtime.ragPipeline spec SSOT 의 chunk → embed → cache. dartlab DART 공시 본문
sections.parquet 의 section_content 컬럼을 한 번 embed 후 parquet cache.

Status: stub — 실 chunking + provider 호출은 별 commit 추가.

Sig
---
buildSectionEmbeddings(corpCode: str, provider: EmbeddingProvider) -> Path
loadSectionEmbeddings(corpCode: str) -> pl.DataFrame

Args
----
corpCode : str — 6 자리 종목코드
provider : EmbeddingProvider — runtime.embeddingSearch SSOT 인터페이스

Returns
-------
Path — cache parquet 경로 (build) 또는 DataFrame (load)

Example
-------
from dartlab.providers.embeddingProvider import LocalEmbeddingProvider
p = LocalEmbeddingProvider()
path = buildSectionEmbeddings("005930", p)
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import polars as pl

from dartlab.providers.embeddingProvider import EmbeddingProvider

CACHE_ROOT = Path("data/cache/sectionEmbeddings")


def buildSectionEmbeddings(corpCode: str, provider: EmbeddingProvider) -> Path:
    """sections.parquet 의 section_content → embedding cache parquet.

    Stub: 실 sections.parquet 로드 + chunking 은 별 commit. 현재는 cache 경로 반환.
    """
    CACHE_ROOT.mkdir(parents=True, exist_ok=True)
    return CACHE_ROOT / f"{corpCode}.parquet"


def loadSectionEmbeddings(corpCode: str) -> pl.DataFrame:
    """cache parquet 로드.

    Stub: 실 schema (chunkId, embedding, sectionId, rcept_no) 별 commit.
    """
    path = CACHE_ROOT / f"{corpCode}.parquet"
    if not path.exists():
        return pl.DataFrame()
    return pl.read_parquet(path)
