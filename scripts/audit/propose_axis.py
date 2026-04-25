"""Phase A — 축 승격 proposal 생성 (반자동).

Phase R merge 이력 + Phase F 반례 누적을 검토해 엔진 axis 승격 proposal.md
를 생성한다. **엔진 코드는 건드리지 않음** — 사람 판단이 주.

게이트 (AND)
- 해당 engine/axis-slug 로 Phase R merge 3+
- Phase F counterexample 2+
- 첫 R merge 로부터 30 일+
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PROPOSAL_DIR = ROOT / "docs" / "phase-a-proposals"


def _git_log_phase_r(engine: str) -> list[dict]:
    """[CORELOOP-R] docs({engine}): ... Phase R commit 이력 파싱."""
    result = subprocess.run(
        ["git", "log", "--all", "--grep=Phase: R", "--pretty=format:%H%n%s%n%at%n---"],
        capture_output=True,
        text=True,
        check=True,
        cwd=ROOT,
    )
    commits = []
    for block in result.stdout.split("---\n"):
        block = block.strip()
        if not block:
            continue
        lines = block.splitlines()
        if len(lines) < 3:
            continue
        sha, subject, ts = lines[0], lines[1], lines[2]
        if f"docs({engine})" not in subject:
            continue
        commits.append({"sha": sha, "subject": subject, "ts": int(ts)})
    return commits


def _count_counterexamples(engine: str, axis: str) -> int:
    ce_dir = ROOT / "data" / "audit" / "counterexamples"
    if not ce_dir.is_dir():
        return 0
    total = 0
    for path in ce_dir.glob("*.json"):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        for ce in payload.get("counterexamples", []):
            if ce.get("engine") == engine and (not axis or ce.get("axis") == axis):
                total += ce.get("n_failures", 1)
    return total


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--engine", required=True)
    ap.add_argument("--axis", default="", help="axis 이름 (비우면 engine 전체)")
    ap.add_argument("--min-phase-r-merges", type=int, default=3)
    ap.add_argument("--min-phase-f-caveats", type=int, default=2)
    ap.add_argument("--min-age-days", type=int, default=30)
    args = ap.parse_args()

    commits = _git_log_phase_r(args.engine)
    if args.axis:
        commits = [c for c in commits if args.axis.lower() in c["subject"].lower()]

    if len(commits) < args.min_phase_r_merges:
        print(f"[gate fail] Phase R merge: {len(commits)} < {args.min_phase_r_merges}")
        return 1
    first_ts = min(c["ts"] for c in commits)
    age = (datetime.now(timezone.utc) - datetime.fromtimestamp(first_ts, timezone.utc)).days
    if age < args.min_age_days:
        print(f"[gate fail] 첫 merge 이후 {age} 일 < {args.min_age_days} 일")
        return 1
    ce_count = _count_counterexamples(args.engine, args.axis)
    if ce_count < args.min_phase_f_caveats:
        print(f"[gate fail] Phase F 반례: {ce_count} < {args.min_phase_f_caveats}")
        return 1

    PROPOSAL_DIR.mkdir(parents=True, exist_ok=True)
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    slug = (args.axis or args.engine).lower().replace(" ", "-")
    out = PROPOSAL_DIR / f"{args.engine}-{slug}.md"

    body = [
        f"# Phase A proposal — {args.engine} / {args.axis or '(엔진 전체)'}",
        "",
        f"생성: {today}",
        "",
        "## 근거",
        f"- Phase R merge: {len(commits)} 건",
        f"- Phase F 반례: {ce_count} 건",
        f"- 첫 R merge 이후: {age} 일",
        "",
        "## 관련 Phase R commits",
        "",
    ]
    for c in commits[:10]:
        body.append(f"- `{c['sha'][:10]}` {c['subject']}")
    body.extend(
        [
            "",
            "## 승격 작업 (수동)",
            "",
            "1. `src/dartlab/core/overrides.py` 에 override key 추가 (필요 시)",
            f"2. `src/dartlab/{args.engine}/__init__.py` 에 새 axis enum 또는 공개 함수",
            "3. docstring 9 섹션 전부 채움 (ops/code.md 규격)",
            f"4. `tests/unit/{args.engine}/test_axis_{slug}.py` 추가",
            "5. 일반 engine PR workflow 진입 ([CORELOOP-R] 마킹 없음)",
            "6. CODEOWNERS 리뷰 → merge",
        ]
    )
    out.write_text("\n".join(body), encoding="utf-8")
    print(f"\n[proposal] {out.relative_to(ROOT)} 생성")
    print("엔진 코드 작성은 수동. proposal 검토 후 진행.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
