"""SearchPastSessions — 과거 세션 transcript FTS5 검색 tool.

`~/.claude/projects/.../*.jsonl` 트랜스크립트 (1 GB+ dark data) 를 BM25 검색하여
과거 분석·결정·도구 호출 흔적을 회수. `decisions.recall` 의 의사결정 memo 검색과
결을 맞춰 — 본 도구는 *전체 대화 transcript* 검색.

자동 인덱싱은 idle 시 백그라운드가 아닌 *명시 호출* (rebuild=True) 만. 운영자 또는
agent 가 명시적으로 갱신 요청해야 sweep 실행 (메모리 부담 회피).
"""

from __future__ import annotations

from dartlab.ai.contracts import Ref

from .types import ToolResult


def searchPastSessions(
    query: str,
    *,
    limit: int = 10,
    role: str | None = None,
    rebuild: bool = False,
) -> ToolResult:
    """과거 세션 transcript 에서 query 매칭 hits 반환.

    Args:
        query: 자유형 검색어 (한국어/영어). 공백 분리 토큰 모두 AND 매칭.
        limit: 반환 hit 수. 기본 10, 최대 50.
        role: "user" / "assistant" 필터. None 이면 둘 다.
        rebuild: True 이면 ~/.claude/projects/ 전체 재인덱싱 후 검색 (느림).
            False 이면 기존 인덱스만 사용 (없으면 빈 결과).

    Returns:
        ToolResult.refs 에 sessionRef 목록 (각 hit). data["hits"] 에 snippet 포함 dict 리스트.

    Example:
        >>> searchPastSessions("삼성전자 매핑 cycle")
        ToolResult(ok=True, refs=[sessionRef × N], ...)
    """
    clean_query = (query or "").strip()
    if not clean_query:
        return ToolResult(False, "query 가 비어 있다", error="empty_query")

    limit_clamped = max(1, min(int(limit or 10), 50))
    role_filter = role if role in ("user", "assistant") else None

    from dartlab.ai.memory.sessionIndex import indexAll, searchSessions, sessionIndexPath

    if rebuild:
        stats = indexAll(forceReindex=False)
    else:
        stats = None

    hits = searchSessions(clean_query, limit=limit_clamped, role=role_filter)

    if not hits:
        summary = "과거 세션에서 매칭 0 건"
        if not sessionIndexPath().exists():
            summary += " (인덱스 미생성 — rebuild=True 로 호출 권장)"
        return ToolResult(
            True,
            summary,
            data={"hits": [], "indexStats": stats},
        )

    refs: list[Ref] = []
    hit_dicts: list[dict[str, object]] = []
    for hit in hits:
        ref_id = f"session:{hit.session_id}:{hit.timestamp or 'na'}"
        refs.append(
            Ref(
                id=ref_id,
                kind="sessionRef",
                title=f"{hit.role} @ {hit.timestamp or '?'} ({hit.block_type})",
                source=f"claude://session/{hit.session_id}",
                payload={
                    "sessionId": hit.session_id,
                    "timestamp": hit.timestamp,
                    "role": hit.role,
                    "blockType": hit.block_type,
                    "toolName": hit.tool_name,
                    "snippet": hit.snippet,
                    "score": hit.score,
                },
            )
        )
        hit_dicts.append(
            {
                "sessionId": hit.session_id,
                "timestamp": hit.timestamp,
                "role": hit.role,
                "blockType": hit.block_type,
                "toolName": hit.tool_name,
                "snippet": hit.snippet,
                "score": hit.score,
            }
        )

    summary = f"과거 세션 hits {len(hits)} 건 (top BM25)"
    return ToolResult(
        True,
        summary,
        refs=refs,
        data={"hits": hit_dicts, "indexStats": stats},
    )


__all__ = ["searchPastSessions"]
