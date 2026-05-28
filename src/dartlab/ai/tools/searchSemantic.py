"""SearchSemantic — RAG semantic search 도구.

runtime.ragPipeline SSOT 4 단계 (chunk → embed → retrieve → cite). dartlab DART 공시
section_content 본문 cosine top-k 검색 + cite (`runtime.citationFormat`).

Status: stub — 실 retrieve 는 별 commit (sectionEmbedding cache 활성화 후).

Sig
---
searchSemantic(query: str, corpCode: str | None = None, topK: int = 10) -> ToolResult

Args
----
query : str — 자연어 검색 쿼리
corpCode : str | None — 종목 filter (None = 전체)
topK : int — top-k 결과 (기본 10)

Returns
-------
ToolResult — data 안 results list[dict] (chunkId, score, sectionId, rcept_no, snippet)

Example
-------
result = searchSemantic("HBM 양산 계획", corpCode="005930", topK=5)
"""

from __future__ import annotations

import numpy as np

from dartlab.gather.sectionEmbedding import loadSectionEmbeddings
from dartlab.providers.embeddingProvider import LocalEmbeddingProvider

from .types import ToolResult


def _cosineTopK(queryVec: np.ndarray, docMatrix: np.ndarray, k: int) -> tuple[np.ndarray, np.ndarray]:
    """cosine similarity top-k 인덱스 + 점수 반환.

    Sig
    ---
    _cosineTopK(queryVec, docMatrix, k) -> (idx, scores)
    """
    if docMatrix.size == 0:
        return np.array([], dtype=int), np.array([], dtype=float)
    qNorm = np.linalg.norm(queryVec) or 1.0
    dNorms = np.linalg.norm(docMatrix, axis=1)
    dNorms[dNorms == 0] = 1.0
    scores = (docMatrix @ queryVec) / (dNorms * qNorm)
    k = min(k, len(scores))
    idx = np.argpartition(-scores, k - 1)[:k] if k > 0 else np.array([], dtype=int)
    idx = idx[np.argsort(-scores[idx])]
    return idx, scores[idx]


def searchSemantic(query: str, corpCode: str | None = None, topK: int = 10) -> ToolResult:
    """RAG semantic search — cache 로드 + cosine top-k.

    cache parquet 미존재 시 빈 결과 정상 반환 (drafted status). 실 indexing 은 별 트랙.
    """
    if not query or not query.strip():
        return ToolResult(False, "query 미지정", error="missing_query")

    provider = LocalEmbeddingProvider()
    queryVec = provider.embed(query)

    results: list[dict] = []
    status = "active"
    if corpCode:
        df = loadSectionEmbeddings(corpCode)
        if df.is_empty() or "embedding" not in df.columns:
            status = "drafted — sectionEmbedding cache 미빌드 (buildSectionEmbeddings 선결)"
        else:
            docMatrix = np.vstack(df["embedding"].to_list())
            idx, scores = _cosineTopK(queryVec, docMatrix, topK)
            for i, score in zip(idx.tolist(), scores.tolist()):
                row = df.row(i, named=True)
                results.append(
                    {
                        "chunkId": row.get("chunkId"),
                        "score": round(float(score), 4),
                        "sectionId": row.get("sectionId"),
                        "rcept_no": row.get("rcept_no"),
                    }
                )
    else:
        status = "drafted — corpCode 미지정 시 전 corpus 미지원 (별 트랙)"

    data = {
        "query": query,
        "corpCode": corpCode,
        "topK": topK,
        "results": results,
        "status": status,
    }
    # 실 retrieve 결과 Ref(sourceType="external") 추가 + wrapExternalInResult 적용 (별 commit)
    return ToolResult(True, f"searchSemantic — {len(results)} results", data=data)
