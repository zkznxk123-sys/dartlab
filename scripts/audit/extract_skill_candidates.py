"""Phase P — 후보 감지.

audit ai-ask jsonl 을 읽어 동일 `(category_hash, tool_sequence_hash)` 가
N 회 이상 성공 반복된 패턴을 docstring Guide append 초안으로 생성.

사용
====

dry-run (기본) — candidate JSON + draft md 만 생성
    uv run python scripts/audit/extract_skill_candidates.py \\
        --since 30d --min-repeat 3 --min-unique-questions 3 \\
        --out data/audit/candidates/

sanitize 모드 — 공개 공유용 (question 원문 제외)
    uv run python scripts/audit/extract_skill_candidates.py \\
        --since 30d --sanitize --out data/audit/candidates/

auditAnalysis 3차 근거 포함 (dry-run 강제)
    uv run python scripts/audit/extract_skill_candidates.py \\
        --include-audit-analysis --dry-run
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
DATA_AUDIT = ROOT / "data" / "audit"


def _parse_since(s: str) -> datetime:
    """`--since 30d`, `2026-04-01`, `7d`."""
    if re.match(r"^\d+d$", s):
        days = int(s[:-1])
        return datetime.now(timezone.utc) - timedelta(days=days)
    try:
        return datetime.fromisoformat(s).replace(tzinfo=timezone.utc)
    except ValueError as e:
        raise ValueError(f"--since 형식 오류: {s} (예: '30d' 또는 '2026-04-01')") from e


def _iter_jsonl(in_dir: Path, since: datetime, until: datetime | None = None):
    for path in sorted(in_dir.glob("*.jsonl")):
        # 파일명 YYYY-MM-DD.jsonl 로 날짜 필터 (빠른 cut)
        try:
            day = datetime.strptime(path.stem, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        except ValueError:
            day = None
        if day is not None:
            if day < since.replace(hour=0, minute=0, second=0, microsecond=0):
                continue
            if until is not None and day > until:
                continue
        with path.open("r", encoding="utf-8") as f:
            for line in f:
                try:
                    yield json.loads(line)
                except json.JSONDecodeError:
                    continue


def _collect(
    in_dir: Path,
    since: datetime,
    until: datetime | None,
    min_repeat: int,
    min_unique_q: int,
    min_chunk_len: int,
    require_success: bool,
) -> list[dict[str, Any]]:
    """집계: (cat_hash, seq_hash) → 후보."""
    # 그룹 bucket
    groups: dict[tuple[str, str], dict[str, Any]] = {}
    for entry in _iter_jsonl(in_dir, since, until):
        if require_success:
            if entry.get("error"):
                continue
            if entry.get("violation"):
                continue
            if entry.get("chunk_len", 0) < min_chunk_len:
                continue
        cat = entry.get("category_hash") or ""
        seq = entry.get("tool_sequence_hash") or ""
        if not seq:
            continue
        key = (cat, seq)
        g = groups.setdefault(
            key,
            {
                "cat_hash": cat,
                "seq_hash": seq,
                "n": 0,
                "unique_q_hashes": set(),
                "example_questions": [],
                "tool_pattern": entry.get("tool_calls", []),
                "chunk_lens": [],
            },
        )
        g["n"] += 1
        qh = entry.get("question_hash") or _hash_q(entry.get("question", ""))
        g["unique_q_hashes"].add(qh)
        q = entry.get("question", "")
        if q and len(g["example_questions"]) < 3 and q not in g["example_questions"]:
            g["example_questions"].append(q)
        g["chunk_lens"].append(entry.get("chunk_len", 0))

    candidates = []
    for (cat, seq), g in groups.items():
        if g["n"] < min_repeat:
            continue
        if len(g["unique_q_hashes"]) < min_unique_q:
            continue
        engine, axis = _infer_engine_axis(g["tool_pattern"])
        cid = f"cand-{datetime.now(timezone.utc).strftime('%Y-%m-%d')}-{len(candidates) + 1:03d}"
        candidates.append(
            {
                "id": cid,
                "engine": engine,
                "axis": axis,
                "cat_hash": cat,
                "seq_hash": seq,
                "tool_pattern": _summarize_pattern(g["tool_pattern"]),
                "n_observed": g["n"],
                "n_unique_questions": len(g["unique_q_hashes"]),
                "example_questions": g["example_questions"],
                "success_rate": 1.0,
                "avg_chunk_len": int(sum(g["chunk_lens"]) / max(len(g["chunk_lens"]), 1)),
                "suggested_append": _suggest_append(engine, axis, g),
            }
        )
    return candidates


def _hash_q(q: str) -> str:
    import re as _re

    q = _re.sub(r"[^\w\s가-힣]", "", q.lower().strip())
    q = _re.sub(r"\s+", " ", q)
    return "sha256:" + hashlib.sha256(q.encode("utf-8")).hexdigest()[:16]


def _infer_engine_axis(toolCalls: list[dict]) -> tuple[str, str]:
    """tool_calls 의 첫 엔진 호출에서 engine/axis 추론."""
    for tc in toolCalls:
        name = tc.get("name", "")
        if name in {"analysis", "credit", "quant", "macro", "industry", "scan", "gather"}:
            args = tc.get("args") or {}
            axis = args.get("axis") or args.get("sub") or args.get("target") or ""
            return name, str(axis)
    return "unknown", ""


def _summarize_pattern(toolCalls: list[dict]) -> list[dict]:
    """tool_calls 를 hash-friendly 요약으로."""
    out = []
    for tc in toolCalls:
        args = tc.get("args") or {}
        shape = {k: type(v).__name__ for k, v in args.items()}
        out.append({"name": tc.get("name"), "args_shape": shape})
    return out


def _suggest_append(engine: str, axis: str, g: dict) -> dict:
    body = (
        f"### {axis or engine} 질문 패턴 ({g['n']} 회 관측)\n\n"
        f"- tool 시퀀스 `{g['seq_hash']}` 가 `{g['n']}` 회 동일하게 반복.\n"
        f"- 예시 질문:\n"
    )
    for q in g["example_questions"]:
        body += f"  - {q[:100]}\n"
    body += f"- 근거: audit 창 {datetime.now(timezone.utc).strftime('%Y-%m-%d')} 까지.\n"
    target = _infer_target_path(engine)
    return {
        "target_file": target,
        "target_symbol": engine,
        "section": "Guide",
        "body": body,
    }


def _infer_target_path(engine: str) -> str:
    mapping = {
        "analysis": "src/dartlab/analysis/financial/__init__.py",
        "credit": "src/dartlab/credit/__init__.py",
        "quant": "src/dartlab/quant/__init__.py",
        "macro": "src/dartlab/macro/__init__.py",
        "industry": "src/dartlab/industry/__init__.py",
        "scan": "src/dartlab/scan/__init__.py",
        "gather": "src/dartlab/gather/entry.py",
    }
    return mapping.get(engine, f"src/dartlab/{engine}/__init__.py")


def _write_outputs(candidates: list[dict], out_dir: Path, sanitize: bool = False) -> tuple[Path, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    json_path = out_dir / f"{today}-candidates.json"
    md_path = out_dir / f"{today}-draft.md"

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "candidates": _sanitize(candidates) if sanitize else candidates,
    }
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    md = [f"# Phase P candidates — {today}", "", f"총 {len(candidates)} 건 후보.", ""]
    for c in candidates:
        md.append(f"## {c['id']} · {c['engine']} · {c['axis']}")
        md.append(
            f"- observed: {c['n_observed']} · unique Q: {c['n_unique_questions']} · avg len: {c['avg_chunk_len']}"
        )
        md.append(f"- cat: `{c['cat_hash']}` · seq: `{c['seq_hash']}`")
        if not sanitize and c["example_questions"]:
            md.append("- examples:")
            for q in c["example_questions"]:
                md.append(f"  - {q}")
        md.append("")
        md.append("```markdown")
        md.append(c["suggested_append"]["body"])
        md.append("```")
        md.append("")
    md_path.write_text("\n".join(md), encoding="utf-8")

    return json_path, md_path


def _sanitize(candidates: list[dict]) -> list[dict]:
    out = []
    for c in candidates:
        d = dict(c)
        d["example_questions"] = [f"[REDACTED {i + 1}]" for i in range(len(c.get("example_questions", [])))]
        out.append(d)
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--since", default="7d", help="시작 (예: 30d, 2026-04-01)")
    ap.add_argument("--until", default=None, help="종료 (기본: today)")
    ap.add_argument("--min-repeat", type=int, default=3)
    ap.add_argument("--min-unique-questions", type=int, default=3)
    ap.add_argument("--min-chunk-len", type=int, default=400)
    ap.add_argument("--in-dir", type=Path, default=DATA_AUDIT / "ai-ask")
    ap.add_argument("--out", type=Path, default=DATA_AUDIT / "candidates")
    ap.add_argument("--sanitize", action="store_true", help="question 원문 제외")
    ap.add_argument(
        "--include-audit-analysis",
        action="store_true",
        help="auditAnalysis/*.md 엔진 개선 섹션을 3차 근거로 편입 (dry-run 강제)",
    )
    ap.add_argument("--dry-run", action="store_true", default=True, help="파일 작성만 (PR 안 만듦). 기본 on")
    ap.add_argument("--no-dry-run", dest="dry_run", action="store_false")
    args = ap.parse_args()

    if args.include_audit_analysis:
        # 안전: 자유양식 파싱 위험 높아 dry-run 강제.
        assert args.dry_run, "--include-audit-analysis 는 --dry-run 필수"

    since = _parse_since(args.since)
    until = _parse_since(args.until) if args.until else None

    if not args.in_dir.is_dir():
        print(f"[info] audit 디렉토리 없음: {args.in_dir}")
        return 0

    candidates = _collect(
        args.in_dir,
        since,
        until,
        args.min_repeat,
        args.min_unique_questions,
        args.min_chunk_len,
        require_success=True,
    )

    if args.include_audit_analysis:
        from _parse_audit_analysis import parse_all

        extra_dir = ROOT / "data" / "dart" / "auditAnalysis"
        bullets = parse_all(extra_dir)
        if bullets:
            candidates.append(
                {
                    "id": f"cand-audit-analysis-{datetime.now(timezone.utc).strftime('%Y-%m-%d')}",
                    "engine": "analysis",
                    "axis": "review-annotations",
                    "cat_hash": "AUDIT-ANALYSIS",
                    "seq_hash": "",
                    "n_observed": sum(len(v) for v in bullets.values()),
                    "n_unique_questions": len(bullets),
                    "example_questions": [],
                    "success_rate": 1.0,
                    "avg_chunk_len": 0,
                    "suggested_append": {
                        "target_file": "src/dartlab/analysis/financial/__init__.py",
                        "target_symbol": "analysis",
                        "section": "Guide",
                        "body": "### 사람 auditAnalysis 제안 (수동 검토 필요)\n\n"
                        + "\n".join(f"- {b}" for v in bullets.values() for b in v[:3]),
                    },
                }
            )

    json_path, md_path = _write_outputs(candidates, args.out, sanitize=args.sanitize)
    print(f"\n후보 {len(candidates)} 건")
    print(f"  JSON: {json_path.relative_to(ROOT)}")
    print(f"  draft md: {md_path.relative_to(ROOT)}")
    if args.dry_run:
        print("\n[dry-run] PR 생성 안 함. 사용자 검토 후 `promote_skill.py --candidate <id> --confirm` 로 승격.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
