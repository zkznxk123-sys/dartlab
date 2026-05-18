"""Phase F — 자가 개선. 실패 신호 집계 → docstring Caveats 섹션 추가 PR.

Phase P 와 차이: 성공 패턴이 아닌 **실패 신호** 를 찾는다.
- error 필드 non-null
- chunk_len < 200
- extreme_flags triggered
- override 후 동일 flag 재발 (override_calls[].succeeded == false)
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _axis_slug import to_slug  # noqa: E402

ROOT = Path(__file__).resolve().parents[3]
DATA_AUDIT = ROOT / "data" / "audit"

FAILURE_TYPES = ["error", "violation", "chunk_len_low", "extreme_flags", "override_failed"]


def _parse_since(s: str) -> datetime:
    import re

    if re.match(r"^\d+d$", s):
        return datetime.now(timezone.utc) - timedelta(days=int(s[:-1]))
    return datetime.fromisoformat(s).replace(tzinfo=timezone.utc)


def _classify(entry: dict) -> list[str]:
    labels = []
    if entry.get("error"):
        labels.append("error")
    if entry.get("violation"):
        labels.append("violation")
    if entry.get("chunk_len", 0) < 200:
        labels.append("chunk_len_low")
    for tc in entry.get("tool_calls", []):
        if tc.get("extreme_flags"):
            labels.append("extreme_flags")
            break
    for oc in entry.get("override_calls", []):
        if not oc.get("succeeded", True):
            labels.append("override_failed")
            break
    return labels


def _collect(in_dir: Path, since: datetime, exclude_types: set[str], min_failures: int):
    buckets: dict[tuple[str, str], dict] = defaultdict(
        lambda: {
            "n_failures": 0,
            "examples": [],
            "labels": set(),
        }
    )
    for path in sorted(in_dir.glob("*.jsonl")):
        try:
            day = datetime.strptime(path.stem, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        except ValueError:
            day = None
        if day and day < since.replace(hour=0, minute=0, second=0, microsecond=0):
            continue
        with path.open("r", encoding="utf-8") as f:
            for line in f:
                try:
                    e = json.loads(line)
                except json.JSONDecodeError:
                    continue
                labels = _classify(e)
                if not labels:
                    continue
                if any(lb in exclude_types for lb in labels):
                    continue
                tcs = e.get("tool_calls") or []
                engine = (tcs[0].get("name") if tcs else "") or "unknown"
                axis = ""
                if tcs:
                    args = tcs[0].get("args") or {}
                    axis = args.get("axis") or args.get("sub") or args.get("target") or ""
                key = (engine, axis)
                bucket = buckets[key]
                bucket["n_failures"] += 1
                bucket["labels"].update(labels)
                if len(bucket["examples"]) < 3:
                    bucket["examples"].append(
                        {
                            "question": e.get("question", ""),
                            "error": e.get("error"),
                            "labels": labels,
                        }
                    )

    counterexamples = []
    for (engine, axis), b in buckets.items():
        if b["n_failures"] < min_failures:
            continue
        cid = f"ce-{datetime.now(timezone.utc).strftime('%Y-%m-%d')}-{len(counterexamples) + 1:03d}"
        counterexamples.append(
            {
                "id": cid,
                "engine": engine,
                "axis": axis,
                "n_failures": b["n_failures"],
                "labels": sorted(b["labels"]),
                "examples": b["examples"],
            }
        )
    return counterexamples


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--since", default="30d")
    ap.add_argument("--in-dir", type=Path, default=DATA_AUDIT / "ai-ask")
    ap.add_argument("--out", type=Path, default=DATA_AUDIT / "counterexamples")
    ap.add_argument("--min-failures", type=int, default=2)
    ap.add_argument("--exclude-types", default="", help="comma-separated; 예: transient_network,rate_limit")
    args = ap.parse_args()

    since = _parse_since(args.since)
    exclude = set(t.strip() for t in args.exclude_types.split(",") if t.strip())

    if not args.in_dir.is_dir():
        print(f"[info] audit 디렉토리 없음: {args.in_dir}")
        return 0

    ces = _collect(args.in_dir, since, exclude, args.min_failures)
    args.out.mkdir(parents=True, exist_ok=True)
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    out_json = args.out / f"{today}-counterexamples.json"
    out_json.write_text(
        json.dumps(
            {"generated_at": datetime.now(timezone.utc).isoformat(), "counterexamples": ces},
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"\n반례 {len(ces)} 건 → {out_json.relative_to(ROOT)}")
    for ce in ces:
        slug = to_slug(ce["axis"] or ce["engine"])
        print(f"  {ce['id']} · {ce['engine']}/{slug} · {ce['n_failures']} 건 · labels={','.join(ce['labels'])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
