"""Workbench usage digest — heuristic.py / runWorkbench 호출 빈도 측정.

마스터 플랜 트랙 3 PR-W1 (cryptic-discovering-kettle.md). PR-O4 활성 후 누적된
~/.dartlab/ai_trace/*.json 분석 → workbench/heuristic.py 실 사용 빈도 측정.

PR-W2 결정 트리:
- 빈도 < 1% → heuristic.py 844 줄 삭제 (PR-W2-A)
- 빈도 ≥ 1% → heuristic.py 유지 + docstring 명문화 (PR-W2-B)

집계 지표:
- 전체 trace 수
- runWorkbench tool 호출 횟수 + 빈도 (vs 전체 tool_result)
- workbench-related event kind (BRIEF/WORK/CRITIQUE/COMPOSE/GATE 의 5 패스 노드명) 빈도

본 스크립트는 *측정 SSOT* — 실제 PR-W2 결정은 운영자가 출력 본 뒤 명시 판단.

사용법:
    uv run python -X utf8 tests/audit/workbenchUsageDigest.py --last 7d
    uv run python -X utf8 tests/audit/workbenchUsageDigest.py --json
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Any


def _resolveDefaultTraceDir() -> Path:
    """기본 trace 디렉토리 — agent._resolveTraceDir 동일 SSOT."""
    custom = os.getenv("DARTLAB_AI_TRACE_DIR")
    if custom:
        return Path(custom)
    return Path.home() / ".dartlab" / "ai_trace"


def _parseDuration(text: str) -> float:
    """aiMetricsDigest._parseDuration 와 동일 SSOT (간이 복제)."""
    import re

    m = re.fullmatch(r"(\d+)([dhm]?)", text.strip())
    if not m:
        raise ValueError(f"invalid duration: {text!r}")
    n = int(m.group(1))
    unit = m.group(2) or "d"
    multiplier = {"d": 86400, "h": 3600, "m": 60}[unit]
    return float(n * multiplier)


def _loadTraces(directory: Path, *, since: float | None = None) -> list[dict[str, Any]]:
    """trace dir glob + mtime 필터. 잘못된 JSON skip."""
    if not directory.is_dir():
        return []
    out: list[dict[str, Any]] = []
    cutoff = (time.time() - since) if since else 0.0
    for path in sorted(directory.glob("*.json")):
        try:
            if path.stat().st_mtime < cutoff:
                continue
            out.append(json.loads(path.read_text(encoding="utf-8")))
        except (OSError, json.JSONDecodeError) as exc:
            print(f"[workbench-digest] skip {path.name}: {type(exc).__name__}", file=sys.stderr)
    return out


# workbench heuristic / sub-agent 활성 표식 event kinds.
_WORKBENCH_EVENT_KINDS = {
    "BRIEF",
    "WORK",
    "CRITIQUE",
    "COMPOSE",
    "GATE",
    "HARVEST",
}


def aggregate(traces: list[dict[str, Any]]) -> dict[str, Any]:
    """trace list → workbench 사용 빈도 집계.

    Returns
    -------
    dict
        sessionCount / totalToolCalls / runWorkbenchCalls / workbenchPercent /
        workbenchEvents / verdict (str)
    """
    session_count = len(traces)
    tool_total = 0
    run_workbench_count = 0
    workbench_event_counter: Counter[str] = Counter()

    for tr in traces:
        events = tr.get("events") or []
        for ev in events:
            kind = ev.get("kind")
            data = ev.get("data") or {}
            if kind == "tool_result":
                tool_total += 1
                if str(data.get("tool", "")) == "RunWorkbench":
                    run_workbench_count += 1
            elif kind in _WORKBENCH_EVENT_KINDS:
                workbench_event_counter[str(kind)] += 1

    pct = (run_workbench_count / tool_total * 100.0) if tool_total > 0 else 0.0
    if session_count == 0:
        verdict = "측정 불가 — trace dump 활성 후 1+ 일 누적 필요"
    elif pct < 1.0:
        verdict = f"workbench 빈도 {pct:.2f}% < 1% — PR-W2-A (heuristic.py 삭제) 권장"
    else:
        verdict = f"workbench 빈도 {pct:.2f}% ≥ 1% — PR-W2-B (유지 + docstring 명문화) 권장"

    return {
        "sessionCount": session_count,
        "totalToolCalls": tool_total,
        "runWorkbenchCalls": run_workbench_count,
        "workbenchPercent": round(pct, 2),
        "workbenchEvents": dict(workbench_event_counter),
        "verdict": verdict,
    }


def renderText(stats: dict[str, Any], *, since: float | None = None) -> str:
    """집계 stats → 사람 가독 텍스트."""
    lines: list[str] = []
    period = f"--last {int(since / 86400)}d" if since else "전체 기간"
    lines.append(f"=== workbench usage digest ({period}) ===")
    lines.append(f"세션 수: {stats['sessionCount']}")
    lines.append(f"전체 tool 호출: {stats['totalToolCalls']}")
    lines.append(f"RunWorkbench 호출: {stats['runWorkbenchCalls']} ({stats['workbenchPercent']}%)")
    if stats["workbenchEvents"]:
        lines.append("\n5 패스 event 빈도 (sub-agent 활성 표식):")
        for kind, n in sorted(stats["workbenchEvents"].items(), key=lambda x: -x[1]):
            lines.append(f"  {n:>5}  {kind}")
    lines.append(f"\n>> 결정: {stats['verdict']}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="workbench usage digest")
    parser.add_argument("--dir", default=None)
    parser.add_argument("--last", default=None)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    directory = Path(args.dir) if args.dir else _resolveDefaultTraceDir()
    since = _parseDuration(args.last) if args.last else None
    traces = _loadTraces(directory, since=since)
    stats = aggregate(traces)

    if args.json:
        print(json.dumps(stats, ensure_ascii=False, indent=2))
    else:
        print(renderText(stats, since=since))
    return 0


if __name__ == "__main__":
    sys.exit(main())
