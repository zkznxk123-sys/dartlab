"""trace JSON → DPO preference pair 추출 — 마스터 플랜 v2 트랙 8 PR-T2.

DPO (Direct Preference Optimization) 학습 dataset 양식: ``{prompt, chosen, rejected}``.
chosen = verify pass 한 답변 (= 도구 호출 성공 + assistant text 충분). rejected = verify fail
한 답변 (= error event 있거나 dead_loop 종료 또는 너무 짧음). 같은 sessionId 안에 둘 다 있을
필요는 없고, *동일 질문 multiple sessions* 안에서 pair 구성.

회귀 가드: PR-T1 의 traceToSftSample 의 schema 와 호환. ML 의존성 0.
"""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any

from dartlab.ai.training.traceToDataset import loadTraceDir, writeJsonl


def _isVerifyPass(trace: dict[str, Any], *, minAnswerLen: int) -> tuple[bool, str]:
    """trace 1 건의 verify 결과 = (passed, answerText).

    passed = error event 0 + assistant text 충분 + tool 호출 ≥ 1 (도구 활용 evidence).
    """
    events = trace.get("events") or []
    if not isinstance(events, list):
        return (False, "")
    has_error = False
    tool_call_count = 0
    text_parts: list[str] = []
    for ev in events:
        if not isinstance(ev, dict):
            continue
        kind = ev.get("kind")
        data = ev.get("data") or {}
        if kind == "error":
            has_error = True
        elif kind == "tool_start":
            tool_call_count += 1
        elif kind == "chunk" and isinstance(data, dict):
            text_parts.append(str(data.get("text") or ""))
    answer = "".join(text_parts).strip()
    passed = (not has_error) and tool_call_count >= 1 and len(answer) >= minAnswerLen
    return (passed, answer)


def extractDpoPairs(
    traces: list[dict[str, Any]],
    *,
    minAnswerLen: int = 50,
) -> list[dict[str, Any]]:
    """trace list → DPO preference pair list.

    Sig:
        extractDpoPairs(traces, *, minAnswerLen=50) -> list[dict]
    Args:
        traces: AuditCollector dump JSON dict list.
        minAnswerLen: chosen 의 answer 최소 길이.
    Returns:
        DPO pair list — 각 dict = ``{"prompt": str, "chosen": str, "rejected": str}``.
    Algorithm:
        1. 질문별 group (질문 string 기준).
        2. 각 그룹에서 passed 1 개 + failed 1 개 ≥ 추출 → cartesian product.
        3. 같은 질문에서 passed/failed 둘 다 없으면 그 질문 skip.
    Example:
        >>> pairs = extractDpoPairs(traces, minAnswerLen=50)
    """
    by_question: dict[str, dict[str, list[str]]] = defaultdict(lambda: {"chosen": [], "rejected": []})
    for trace in traces:
        if not isinstance(trace, dict):
            continue
        q = str(trace.get("question") or "").strip()
        if not q:
            continue
        passed, answer = _isVerifyPass(trace, minAnswerLen=minAnswerLen)
        if not answer:
            continue
        if passed:
            by_question[q]["chosen"].append(answer)
        else:
            by_question[q]["rejected"].append(answer)

    pairs: list[dict[str, Any]] = []
    for q, group in by_question.items():
        if not group["chosen"] or not group["rejected"]:
            continue
        for chosen in group["chosen"]:
            for rejected in group["rejected"]:
                pairs.append({"prompt": q, "chosen": chosen, "rejected": rejected})
    return pairs


def buildDpoDataset(
    *,
    traceDir: str | Path,
    outPath: str | Path,
    minAnswerLen: int = 50,
) -> dict[str, Any]:
    """trace dir → DPO JSONL dataset + stats.

    Sig:
        buildDpoDataset(*, traceDir, outPath, minAnswerLen=50) -> stats dict
    Args:
        traceDir: trace dump 디렉터리.
        outPath: 출력 JSONL 경로 (DPO 양식).
        minAnswerLen: chosen 의 최소 길이 (PR-T1 와 동일 룰).
    Returns:
        ``{"totalTraces": N, "uniqueQuestions": K, "pairs": M, "outPath": str}``.
    """
    traces = list(loadTraceDir(traceDir))
    pairs = extractDpoPairs(traces, minAnswerLen=minAnswerLen)
    out = writeJsonl(pairs, outPath)
    return {
        "totalTraces": len(traces),
        "uniqueQuestions": len({str(t.get("question") or "") for t in traces if isinstance(t, dict)} - {""}),
        "pairs": len(pairs),
        "outPath": str(out),
    }


__all__ = ["extractDpoPairs", "buildDpoDataset"]
