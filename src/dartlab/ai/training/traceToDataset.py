"""trace JSON → SFT dataset 변환 SSOT — 마스터 플랜 v2 트랙 8 PR-T1.

AuditCollector (`dartlab/ai/trace.py`) 가 dump 한 trace JSON 을 OpenAI / Anthropic /
Qwen SFT 양식 (messages list of {role, content}) 으로 변환. 동일 schema 가 dpoPairs.py
(PR-T2) 와 runSft.py (PR-T5) 의 입력.

trace JSON 양식 (AuditCollector.dumpToJson)
-------------------------------------------
::

    {
      "sessionId": "...",
      "question": "삼성전자 ROE 알려줘",
      "provider": "anthropic",
      "model": "claude-sonnet-4-5",
      "startedAt": "...",
      "finishedAt": "...",
      "events": [
        {"kind": "chunk", "data": {"text": "삼성전자 ROE"}},
        {"kind": "tool_start", "data": {"tool": "EngineCall", "input": {...}}},
        {"kind": "tool_result", "data": {"tool": "EngineCall", "result": {...}}},
        {"kind": "chunk", "data": {"text": "는 8.94%..."}},
        {"kind": "done", "data": {}}
      ]
    }

SFT sample 양식
---------------
::

    {
      "messages": [
        {"role": "system", "content": "..."},
        {"role": "user", "content": "삼성전자 ROE 알려줘"},
        {"role": "assistant", "content": "삼성전자 ROE 는 8.94%..."}
      ],
      "tools_used": ["EngineCall"],
      "trace_meta": {"sessionId": "...", "provider": "...", "model": "..."}
    }

회귀 가드: 본 모듈은 transformers / datasets 의존성 0. trace JSON 만 읽고 JSONL 쓴다.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterator

# 기본 system prompt — trace JSON 에 system 메시지가 박혀 있지 않은 경우 fallback.
_FALLBACK_SYSTEM_PROMPT = (
    "당신은 DartLab 의 한국 공시·금융 분석 AI 도우미입니다. 도구를 호출하여 정확한 숫자와 근거를 답변에 포함합니다."
)


def traceToSftSample(trace: dict[str, Any], *, systemPrompt: str | None = None) -> dict[str, Any] | None:
    """trace JSON dict → SFT sample dict (messages 양식).

    Sig:
        traceToSftSample(trace, *, systemPrompt=None) -> dict | None
    Args:
        trace: ``AuditCollector.dumpToJson`` 산출물 (dict).
        systemPrompt: system 메시지. None 이면 fallback.
    Returns:
        SFT sample dict 또는 None (질문/응답 누락 시).
    Example:
        >>> sample = traceToSftSample(trace)
        >>> sample["messages"][0]["role"]
        'system'
    """
    if not isinstance(trace, dict):
        return None
    question = str(trace.get("question") or "").strip()
    if not question:
        return None
    events = trace.get("events") or []
    if not isinstance(events, list):
        return None

    # assistant 응답 = 모든 chunk event 의 text 결합
    assistant_text_parts: list[str] = []
    tools_used: list[str] = []
    for ev in events:
        if not isinstance(ev, dict):
            continue
        kind = ev.get("kind")
        data = ev.get("data") or {}
        if not isinstance(data, dict):
            continue
        if kind == "chunk":
            text = str(data.get("text") or "")
            if text:
                assistant_text_parts.append(text)
        elif kind == "tool_start":
            tool_name = str(data.get("tool") or "")
            if tool_name:
                tools_used.append(tool_name)

    assistant_text = "".join(assistant_text_parts).strip()
    if not assistant_text:
        return None

    return {
        "messages": [
            {"role": "system", "content": systemPrompt or _FALLBACK_SYSTEM_PROMPT},
            {"role": "user", "content": question},
            {"role": "assistant", "content": assistant_text},
        ],
        "tools_used": tools_used,
        "trace_meta": {
            "sessionId": trace.get("sessionId"),
            "provider": trace.get("provider"),
            "model": trace.get("model"),
        },
    }


def loadTraceDir(traceDir: str | Path) -> Iterator[dict[str, Any]]:
    """trace dump 디렉터리 → trace JSON dict iterator.

    Sig:
        loadTraceDir(traceDir) -> Iterator[dict]
    Args:
        traceDir: trace JSON 파일들이 있는 디렉터리.
    Yields:
        각 trace JSON 파일을 dict 로 로드한 결과. 파일 누락 / 파싱 실패 silent skip.
    Example:
        >>> for trace in loadTraceDir("~/.dartlab/ai_trace"):
        ...     print(trace.get("sessionId"))
    """
    p = Path(traceDir).expanduser()
    if not p.is_dir():
        return
    for path in sorted(p.glob("*.json")):
        try:
            yield json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue


def writeJsonl(samples: list[dict[str, Any]], outPath: str | Path) -> Path:
    """SFT sample list → JSONL 파일 작성.

    Sig:
        writeJsonl(samples, outPath) -> Path
    Args:
        samples: SFT sample dict list.
        outPath: 출력 JSONL 경로.
    Returns:
        실제 저장된 Path. parent 디렉터리는 자동 생성.
    """
    out = Path(outPath).expanduser()
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as fh:
        for sample in samples:
            fh.write(json.dumps(sample, ensure_ascii=False) + "\n")
    return out


def buildSftDataset(
    *,
    traceDir: str | Path,
    outPath: str | Path,
    systemPrompt: str | None = None,
    minToolCalls: int = 0,
    minAnswerLen: int = 50,
) -> dict[str, Any]:
    """trace dir → SFT JSONL dataset 변환 + stats 반환.

    Sig:
        buildSftDataset(*, traceDir, outPath, systemPrompt=None, minToolCalls=0,
            minAnswerLen=50) -> stats dict
    Args:
        traceDir: trace dump 디렉터리.
        outPath: 출력 JSONL 경로.
        systemPrompt: SFT sample 의 system 메시지. None 이면 fallback.
        minToolCalls: 본 갯수 이상 tool 호출한 trace 만 채택 (0 = 무필터).
        minAnswerLen: assistant text 최소 길이 (너무 짧은 응답 제외).
    Returns:
        ``{"totalTraces": N, "accepted": M, "rejected": K, "outPath": str}``.
    Example:
        >>> stats = buildSftDataset(
        ...     traceDir="~/.dartlab/ai_trace",
        ...     outPath="data/_training/sft_v1.jsonl",
        ...     minToolCalls=1,
        ... )
    """
    accepted: list[dict[str, Any]] = []
    rejected = 0
    total = 0
    for trace in loadTraceDir(traceDir):
        total += 1
        sample = traceToSftSample(trace, systemPrompt=systemPrompt)
        if sample is None:
            rejected += 1
            continue
        if minToolCalls > 0 and len(sample.get("tools_used") or []) < minToolCalls:
            rejected += 1
            continue
        if minAnswerLen > 0:
            answer = sample["messages"][-1]["content"]
            if len(answer) < minAnswerLen:
                rejected += 1
                continue
        accepted.append(sample)
    out = writeJsonl(accepted, outPath)
    return {
        "totalTraces": total,
        "accepted": len(accepted),
        "rejected": rejected,
        "outPath": str(out),
    }


__all__ = ["traceToSftSample", "loadTraceDir", "writeJsonl", "buildSftDataset"]
