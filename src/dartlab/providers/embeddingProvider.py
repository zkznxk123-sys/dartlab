"""Embedding provider Protocol + 2 구현 stub.

runtime.embeddingSearch spec SSOT 의 표준 인터페이스. RAG pipeline / semantic search
도구 (`ai/tools/searchSemantic.py`) 가 본 provider 호출.

Status: stub — 실 SDK 호출 코드는 별 commit 추가 (Phase 3.B 후속). 본 파일은
인터페이스 + skeleton + docstring 표준.

Sig
---
class EmbeddingProvider(Protocol): embed / embedBatch
class LocalEmbeddingProvider: numpy-direct (SDK 의존성 0)

Args
----
text : str | list[str] — query 또는 document chunk

Returns
-------
np.ndarray — embedding vector (dim provider-specific)

Example
-------
provider = LocalEmbeddingProvider(dim=384)
vec = provider.embed("HBM 양산")
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

import numpy as np


@runtime_checkable
class EmbeddingProvider(Protocol):
    """embedding 표준 인터페이스 (runtime.embeddingSearch SSOT)."""

    dim: int

    def embed(self, text: str) -> np.ndarray:
        """단일 텍스트 → vector."""
        ...

    def embedBatch(self, texts: list[str], batchSize: int = 100) -> np.ndarray:
        """배치 텍스트 → matrix (n × dim)."""
        ...


class LocalEmbeddingProvider:
    """numpy-direct fallback (SDK 의존성 0).

    Sig
    ---
    LocalEmbeddingProvider(dim: int = 384)

    Args
    ----
    dim : int — embedding 차원 (기본 384)

    Returns
    -------
    np.ndarray — 결정론적 hash-based vector (stub, 실 모델 X)

    Example
    -------
    p = LocalEmbeddingProvider()
    v = p.embed("text")
    assert v.shape == (384,)

    Raises
    ------
    ValueError — text 가 빈 문자열일 때
    """

    def __init__(self, dim: int = 384) -> None:
        self.dim = dim

    def embed(self, text: str) -> np.ndarray:
        """단일 텍스트 → 정규화된 vector (numpy hash-seeded RNG, stub 구현)."""
        if not text or not text.strip():
            raise ValueError("text required")
        seed = abs(hash(text)) % (2**32)
        rng = np.random.default_rng(seed)
        vec = rng.standard_normal(self.dim)
        return vec / np.linalg.norm(vec)

    def embedBatch(self, texts: list[str], batchSize: int = 100) -> np.ndarray:
        """배치 텍스트 → matrix (n × dim). embed 반복 호출 stub."""
        return np.vstack([self.embed(t) for t in texts])
