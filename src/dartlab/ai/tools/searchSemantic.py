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

from .types import ToolResult


def searchSemantic(query: str, corpCode: str | None = None, topK: int = 10) -> ToolResult:
    """RAG semantic search.

    Stub: provider/cache 미활성. 현재는 빈 결과 + drafted 표기.
    """
    if not query or not query.strip():
        return ToolResult(False, "query 미지정", error="missing_query")

    data = {
        "query": query,
        "corpCode": corpCode,
        "topK": topK,
        "results": [],
        "status": "drafted — sectionEmbedding cache 미활성",
    }
    # 실 retrieve 시 Ref(sourceType="external") 추가 + wrapExternalInResult(result.toDict()) 적용
    return ToolResult(True, "searchSemantic stub", data=data)
