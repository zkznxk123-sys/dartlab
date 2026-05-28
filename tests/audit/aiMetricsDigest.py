"""KPI Daily Digest — ~/.dartlab/ai_trace/*.json 글로브 → 일간 집계.

마스터 플랜 트랙 2 PR-O5 (cryptic-discovering-kettle.md). 7 KPI 중 4 종 자동 측정:

1. **turn count / session** — 세션당 평균/p95 turn 수 (마스터 플랜 KPI 목표 < 5)
2. **first_chunk_ms p95** — 첫 chunk 까지 ms (마스터 플랜 KPI 목표 < 2000 ms)
3. **turn elapsed ms p50/p95** — 단일 turn ms
4. **tool 호출 빈도 top 20** — registry 사용도 + 도구 선택 패턴 가시화

추가:
- 세션 수 / 기간 / question 샘플
- error 이벤트 빈도 (provider_error / dead_loop / max_iter)
- KPI 미달 항목 명시 (목표값 비교)

사용법:
    uv run python -X utf8 tests/audit/aiMetricsDigest.py --last 30d
    uv run python -X utf8 tests/audit/aiMetricsDigest.py --dir ~/.dartlab/ai_trace --last 7d
    uv run python -X utf8 tests/audit/aiMetricsDigest.py --json  # stdout JSON

운영 가시성: CI ci-fast 에서 정보성 출력 (비차단). digest 가 priced=False 비율 추적 →
가격표 갱신 트리거.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Any


def _resolveDefaultTraceDir() -> Path:
    """기본 trace 디렉토리 — agent._resolveTraceDir 동일 SSOT.

    환경변수 DARTLAB_AI_TRACE_DIR override. 기본 ~/.dartlab/ai_trace/.
    """
    custom = os.getenv("DARTLAB_AI_TRACE_DIR")
    if custom:
        return Path(custom)
    return Path.home() / ".dartlab" / "ai_trace"


def _parseDuration(text: str) -> float:
    """'30d' / '7d' / '24h' / '60m' → 초.

    기본 unit 'd'. 잘못된 양식 ValueError.
    """
    m = re.fullmatch(r"(\d+)([dhm]?)", text.strip())
    if not m:
        raise ValueError(f"invalid duration: {text!r}")
    n = int(m.group(1))
    unit = m.group(2) or "d"
    multiplier = {"d": 86400, "h": 3600, "m": 60}[unit]
    return float(n * multiplier)


def _loadTraces(directory: Path, *, since: float | None = None) -> list[dict[str, Any]]:
    """글로브 + mtime 필터. 잘못된 JSON 은 skip + warning."""
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
            print(f"[digest] skip {path.name}: {type(exc).__name__}", file=sys.stderr)
    return out


def _percentile(values: list[float], p: float) -> float | None:
    """간단 percentile (linear interpolation)."""
    if not values:
        return None
    s = sorted(values)
    if len(s) == 1:
        return s[0]
    k = (len(s) - 1) * (p / 100.0)
    f = int(k)
    c = min(f + 1, len(s) - 1)
    if f == c:
        return s[f]
    d = k - f
    return s[f] + (s[c] - s[f]) * d


def _aggregate(traces: list[dict[str, Any]]) -> dict[str, Any]:
    """trace 리스트 → 통계 dict.

    KPI 목표 (마스터 플랜):
    - turnsPerSession p95 < 5
    - firstChunkMsP95 < 2000
    - turnElapsedMsP95: 정보성
    """
    session_count = len(traces)
    turn_counts: list[int] = []
    first_chunk_ms_list: list[float] = []
    turn_elapsed_ms_list: list[float] = []
    tool_counter: Counter[str] = Counter()
    error_kinds: Counter[str] = Counter()
    questions_sample: list[str] = []

    for tr in traces:
        events = tr.get("events") or []
        turns_in_session = sum(1 for e in events if e.get("kind") == "turn_timing")
        turn_counts.append(turns_in_session)
        for ev in events:
            kind = ev.get("kind")
            data = ev.get("data") or {}
            if kind == "first_chunk_ms":
                ms = data.get("ms")
                if isinstance(ms, (int, float)):
                    first_chunk_ms_list.append(float(ms))
            elif kind == "turn_timing":
                ms = data.get("elapsedMs")
                if isinstance(ms, (int, float)):
                    turn_elapsed_ms_list.append(float(ms))
            elif kind == "tool_result":
                name = data.get("tool") or "?"
                tool_counter[str(name)] += 1
            elif kind == "error":
                err = data.get("error") or "unknown_error"
                error_kinds[str(err)[:80]] += 1
        q = tr.get("question") or ""
        if q and len(questions_sample) < 5:
            questions_sample.append(q[:100])

    return {
        "sessionCount": session_count,
        "turnsPerSession": {
            "mean": (sum(turn_counts) / len(turn_counts)) if turn_counts else None,
            "p50": _percentile([float(x) for x in turn_counts], 50),
            "p95": _percentile([float(x) for x in turn_counts], 95),
            "max": max(turn_counts) if turn_counts else None,
        },
        "firstChunkMs": {
            "count": len(first_chunk_ms_list),
            "p50": _percentile(first_chunk_ms_list, 50),
            "p95": _percentile(first_chunk_ms_list, 95),
        },
        "turnElapsedMs": {
            "count": len(turn_elapsed_ms_list),
            "p50": _percentile(turn_elapsed_ms_list, 50),
            "p95": _percentile(turn_elapsed_ms_list, 95),
        },
        "toolTop20": tool_counter.most_common(20),
        "errors": dict(error_kinds.most_common(10)),
        "questionsSample": questions_sample,
    }


# 마스터 플랜 KPI 목표 (cryptic-discovering-kettle.md).
_KPI_TARGETS = {
    "turnsPerSession.p95": ("< 5", lambda v: v is not None and v < 5),
    "firstChunkMs.p95": ("< 2000 ms", lambda v: v is not None and v < 2000),
}


def _kpiVerdict(stats: dict[str, Any]) -> list[tuple[str, str, bool]]:
    """KPI 목표 vs 실측 — (지표명, 목표, 통과여부) 목록.

    측정값 없으면 (None) → 미통과 분류 (측정 부재 자체가 문제).
    """
    out: list[tuple[str, str, bool]] = []
    out.append(
        (
            "turnsPerSession.p95",
            "< 5",
            stats["turnsPerSession"]["p95"] is not None and stats["turnsPerSession"]["p95"] < 5,
        )
    )
    out.append(
        (
            "firstChunkMs.p95",
            "< 2000 ms",
            stats["firstChunkMs"]["p95"] is not None and stats["firstChunkMs"]["p95"] < 2000,
        )
    )
    return out


def _renderText(stats: dict[str, Any], *, since: float | None) -> str:
    """집계 stats → 사람 가독 텍스트 (CLI 기본 출력)."""
    lines: list[str] = []
    period = f"--last {int(since / 86400)}d" if since else "전체 기간"
    lines.append(f"=== ai trace KPI digest ({period}) ===")
    lines.append(f"세션 수: {stats['sessionCount']}")
    if stats["sessionCount"] == 0:
        lines.append("trace dump 0 — DARTLAB_AI_TRACE_DUMP=1 활성 후 다시 측정.")
        return "\n".join(lines)

    tps = stats["turnsPerSession"]
    fcm = stats["firstChunkMs"]
    tem = stats["turnElapsedMs"]
    mean = tps["mean"]
    mean_str = f"{mean:.2f}" if isinstance(mean, (int, float)) else "—"
    p50 = tps["p50"]
    p95 = tps["p95"]
    p50_str = f"{p50:.1f}" if isinstance(p50, (int, float)) else "—"
    p95_str = f"{p95:.1f}" if isinstance(p95, (int, float)) else "—"
    max_v = tps["max"]
    max_str = f"{max_v}" if isinstance(max_v, (int, float)) else "—"
    lines.append(f"turns/session — mean={mean_str} p50={p50_str} p95={p95_str} max={max_str}")
    fc_p50 = fcm["p50"]
    fc_p95 = fcm["p95"]
    fc_p50_str = f"{fc_p50:.0f}" if isinstance(fc_p50, (int, float)) else "—"
    fc_p95_str = f"{fc_p95:.0f}" if isinstance(fc_p95, (int, float)) else "—"
    lines.append(f"firstChunk ms — count={fcm['count']} p50={fc_p50_str} p95={fc_p95_str}")
    te_p50 = tem["p50"]
    te_p95 = tem["p95"]
    te_p50_str = f"{te_p50:.0f}" if isinstance(te_p50, (int, float)) else "—"
    te_p95_str = f"{te_p95:.0f}" if isinstance(te_p95, (int, float)) else "—"
    lines.append(f"turn elapsed ms — count={tem['count']} p50={te_p50_str} p95={te_p95_str}")
    if stats["toolTop20"]:
        lines.append("\ntool 호출 빈도 top 20:")
        for name, n in stats["toolTop20"]:
            lines.append(f"  {n:>5}  {name}")
    if stats["errors"]:
        lines.append("\nerror 종류 (top 10):")
        for err, n in stats["errors"].items():
            lines.append(f"  {n:>5}  {err}")
    lines.append("\nKPI 목표 vs 실측:")
    for name, target, passed in _kpiVerdict(stats):
        mark = "✓" if passed else "✗"
        lines.append(f"  {mark} {name}: 목표 {target}")
    return "\n".join(lines)


# PR-L5 — KPI baseline 회귀 가드. 4 KPI 의 ±15% 회귀 시 exit 1.
# 차이가 *나쁜 쪽* (지연 증가, turn 증가) 일 때만 회귀. *좋은 쪽* (지연 감소) 은 OK.
_KPI_REGRESSION_TOLERANCE_PCT: float = 15.0
_KPI_TRACKED_PATHS: tuple[tuple[str, str, str], ...] = (
    # (label, dotted path in stats, direction — "lower" = 작을수록 좋음)
    ("turnsPerSession.p95", "turnsPerSession.p95", "lower"),
    ("firstChunkMs.p95", "firstChunkMs.p95", "lower"),
    ("turnElapsedMs.p50", "turnElapsedMs.p50", "lower"),
    ("turnElapsedMs.p95", "turnElapsedMs.p95", "lower"),
)


def _statsToBaseline(stats: dict[str, Any]) -> dict[str, Any]:
    """현 stats → baseline JSON 양식. 4 KPI + 생성 시각."""
    import datetime as _dt

    out: dict[str, Any] = {
        "createdAt": _dt.datetime.now(_dt.timezone.utc).isoformat(),
        "sessionCount": stats.get("sessionCount", 0),
        "kpis": {},
    }
    for label, path, _direction in _KPI_TRACKED_PATHS:
        head, tail = path.split(".", 1)
        out["kpis"][label] = (stats.get(head) or {}).get(tail)
    return out


def _compareWithBaseline(
    stats: dict[str, Any], baseline: dict[str, Any]
) -> tuple[list[tuple[str, float, float, float, bool]], bool]:
    """baseline 대비 현 stats 회귀 검사.

    Returns:
        (rows, hasRegression) — rows = (label, baselineVal, currentVal, deltaPct, regressed) list.
        deltaPct = (current - baseline) / baseline * 100. lower-better KPI 에서 양수 = 회귀.
    """
    rows: list[tuple[str, float, float, float, bool]] = []
    hasRegression = False
    base_kpis = (baseline or {}).get("kpis") or {}
    for label, path, direction in _KPI_TRACKED_PATHS:
        head, tail = path.split(".", 1)
        cur = (stats.get(head) or {}).get(tail)
        base = base_kpis.get(label)
        if not isinstance(cur, (int, float)) or not isinstance(base, (int, float)) or base == 0:
            continue
        deltaPct = (cur - base) / base * 100.0
        regressed = False
        if direction == "lower":
            regressed = deltaPct > _KPI_REGRESSION_TOLERANCE_PCT
        else:  # higher-better
            regressed = -deltaPct > _KPI_REGRESSION_TOLERANCE_PCT
        if regressed:
            hasRegression = True
        rows.append((label, float(base), float(cur), deltaPct, regressed))
    return rows, hasRegression


def _renderBaselineDiff(rows: list[tuple[str, float, float, float, bool]]) -> str:
    """baseline 비교 결과 텍스트 — 4 KPI 표."""
    if not rows:
        return "(baseline 비교 가능 KPI 없음 — 현 측정값 부재)"
    lines = ["", "── baseline 비교 ──"]
    lines.append(f"{'KPI':<22} {'baseline':>10} {'current':>10} {'delta':>8}  status")
    lines.append("-" * 60)
    for label, base, cur, delta, regressed in rows:
        mark = "✗" if regressed else "✓"
        lines.append(f"{mark} {label:<20} {base:>10.1f} {cur:>10.1f} {delta:>+7.1f}%")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    """digest CLI entry point. 반환 = exit code (회귀 시 1, baseline write 시 0)."""
    parser = argparse.ArgumentParser(description="ai trace KPI daily digest")
    parser.add_argument("--dir", default=None, help="trace 디렉토리 (기본 ~/.dartlab/ai_trace/)")
    parser.add_argument("--last", default=None, help="기간 (예: 30d / 7d / 24h / 60m)")
    parser.add_argument("--json", action="store_true", help="JSON stdout")
    parser.add_argument(
        "--baseline",
        default=None,
        help="baseline JSON 경로 — 비교 후 회귀 (±15%%) 시 exit 1 (PR-L5)",
    )
    parser.add_argument(
        "--write-baseline",
        default=None,
        help="baseline JSON 저장 경로 — 현 측정값을 baseline 으로 박음 (PR-L5)",
    )
    args = parser.parse_args(argv)

    directory = Path(args.dir) if args.dir else _resolveDefaultTraceDir()
    since = _parseDuration(args.last) if args.last else None
    traces = _loadTraces(directory, since=since)
    stats = _aggregate(traces)

    # --write-baseline 박기
    if args.write_baseline:
        baseline = _statsToBaseline(stats)
        out_path = Path(args.write_baseline)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(baseline, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
        print(f"[baseline] 저장 → {out_path} (session={baseline['sessionCount']})")
        return 0

    if args.json:
        print(json.dumps(stats, ensure_ascii=False, indent=2, default=str))
    else:
        print(_renderText(stats, since=since))

    # --baseline 비교
    if args.baseline:
        try:
            baseline = json.loads(Path(args.baseline).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            print(f"[baseline] 로드 실패: {exc}", file=sys.stderr)
            return 2
        rows, hasRegression = _compareWithBaseline(stats, baseline)
        if not args.json:
            print(_renderBaselineDiff(rows))
        if hasRegression:
            print(f"[baseline] 회귀 감지 — {_KPI_REGRESSION_TOLERANCE_PCT:.0f}% 임계 초과", file=sys.stderr)
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
