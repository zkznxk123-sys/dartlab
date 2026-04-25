"""`dartlab-coreloop` CLI — 자가개선 루프 (Phase O/P/R/F/A) 조작.

사용
====

    dartlab-coreloop pattern --since 7d
    dartlab-coreloop refine --since 30d
    dartlab-coreloop promote --candidate <path> --id <id> --confirm
    dartlab-coreloop propose-axis --engine analysis
    dartlab-coreloop sanitize --in data/audit/ai-ask/ --out /tmp/sanitized --mode hash
    dartlab-coreloop status
    dartlab-coreloop backfill-blog --blog-root blog/ --confirm
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[3] / "scripts" / "audit"
ROOT = Path(__file__).resolve().parents[3]


def _run(script: str, extra_args: list[str]) -> int:
    path = SCRIPTS / script
    if not path.exists():
        print(f"[fatal] 스크립트 없음: {path}")
        return 1
    cmd = [sys.executable, str(path), *extra_args]
    return subprocess.call(cmd)


def _status() -> int:
    """audit 로그 · candidates · counterexamples 현황 요약."""
    audit_dir = ROOT / "data" / "audit" / "ai-ask"
    cand_dir = ROOT / "data" / "audit" / "candidates"
    ce_dir = ROOT / "data" / "audit" / "counterexamples"

    jsonl = sorted(audit_dir.glob("*.jsonl")) if audit_dir.is_dir() else []
    total_lines = 0
    for p in jsonl:
        with p.open("r", encoding="utf-8") as f:
            total_lines += sum(1 for _ in f)
    cand_json = sorted(cand_dir.glob("*-candidates.json")) if cand_dir.is_dir() else []
    ce_json = sorted(ce_dir.glob("*-counterexamples.json")) if ce_dir.is_dir() else []

    pending_c = 0
    for p in cand_json[-5:]:
        try:
            pending_c += len(json.loads(p.read_text(encoding="utf-8")).get("candidates", []))
        except json.JSONDecodeError:
            continue

    pending_f = 0
    for p in ce_json[-5:]:
        try:
            pending_f += len(json.loads(p.read_text(encoding="utf-8")).get("counterexamples", []))
        except json.JSONDecodeError:
            continue

    print("── coreloop status ──")
    print(f"  audit 로그: {len(jsonl)} 파일 · {total_lines} 라인")
    print(f"  Phase P candidates: {len(cand_json)} 파일 · 최근 5 파일에 후보 {pending_c} 개")
    print(f"  Phase F counterexamples: {len(ce_json)} 파일 · 최근 5 파일에 반례 {pending_f} 개")
    print(f"  코드 경로: {SCRIPTS.relative_to(ROOT)}/")
    print(f"  현재 시각 (UTC): {datetime.now(timezone.utc).isoformat()}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(
        prog="dartlab-coreloop", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    sub = ap.add_subparsers(dest="cmd", required=True)

    sub.add_parser("status", help="audit · candidates · counterexamples 현황")

    sub.add_parser("pattern", help="Phase P 후보 감지 (extract_skill_candidates.py)", add_help=False)
    sub.add_parser("refine", help="Phase F 반례 집계 (refine_skill.py)", add_help=False)
    sub.add_parser("promote", help="Phase R docstring Guide append PR (promote_skill.py)", add_help=False)
    sub.add_parser("propose-axis", help="Phase A axis proposal (propose_axis.py)", add_help=False)
    sub.add_parser("verify", help="Hallucination 재현 테스트 (verify_candidate.py)", add_help=False)
    sub.add_parser("sanitize", help="audit jsonl 민감정보 마스킹 (sanitize_audit.py)", add_help=False)
    sub.add_parser("backfill-blog", help="블로그 frontmatter → insights 백필", add_help=False)

    # subcommand 는 argparse 에서 pass-through — 나머지 args 를 그대로 하위 스크립트로
    args, rest = ap.parse_known_args()

    if args.cmd == "status":
        return _status()

    mapping = {
        "pattern": "extract_skill_candidates.py",
        "refine": "refine_skill.py",
        "promote": "promote_skill.py",
        "propose-axis": "propose_axis.py",
        "verify": "verify_candidate.py",
        "sanitize": "sanitize_audit.py",
        "backfill-blog": "backfill_blog_insights.py",
    }
    script = mapping.get(args.cmd)
    if script is None:
        ap.print_help()
        return 2
    return _run(script, rest)


if __name__ == "__main__":
    sys.exit(main())
