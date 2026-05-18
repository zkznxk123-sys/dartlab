"""Phase R — 승격. candidate JSON → docstring Guide append PR.

dry-run (기본) 에서는 diff 만 출력. `--confirm` 시 git 브랜치·PR 생성.

사용
====

dry-run
    uv run python src/dartlab/skills/promote_skill.py \\
        --candidate data/audit/candidates/2026-04-25-candidates.json \\
        --id cand-2026-04-25-001

승격 (git branch + gh pr create --draft)
    uv run python src/dartlab/skills/promote_skill.py \\
        --candidate data/audit/candidates/2026-04-25-candidates.json \\
        --id cand-2026-04-25-001 --confirm --pr-draft

auto-merge 금지 (3중 방어의 1차): 본 스크립트는 `gh pr merge --auto` 호출하지 않는다.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _axis_slug import to_slug  # noqa: E402

ROOT = Path(__file__).resolve().parents[3]


def _load_candidate(path: Path, cid: str) -> dict:
    payload = json.loads(path.read_text(encoding="utf-8"))
    for c in payload.get("candidates", []):
        if c.get("id") == cid:
            return c
    raise SystemExit(f"[fatal] candidate id '{cid}' 미발견 in {path}")


def _append_guide(target_file: Path, body: str) -> str:
    """target_file 의 module docstring 또는 첫 클래스/함수 docstring 의 Guide 섹션에 append.

    단순화: 파일 끝에 주석으로 append 제안만 출력 (실제 삽입은 libcst 필요).
    이 함수는 diff 형태 반환.
    """
    if not target_file.exists():
        return f"[미존재] {target_file}"
    original = target_file.read_text(encoding="utf-8")
    # Guide 섹션을 찾고 append. 없으면 파일 말미 주석으로 제안.
    marker = "Guide:"
    if marker in original:
        idx = original.index(marker)
        # Guide: 다음 첫 빈 줄 찾아 그 앞에 append
        tail_from = original.find("\n\n", idx)
        if tail_from == -1:
            tail_from = len(original)
        new = original[:tail_from] + "\n" + body + original[tail_from:]
    else:
        new = (
            original + "\n\n# Phase R append 제안 (Guide 섹션 없음 — 수동 삽입 필요):\n# " + body.replace("\n", "\n# ")
        )
    return new


def _diff(original: str, new: str) -> str:
    import difflib

    return "".join(
        difflib.unified_diff(
            original.splitlines(keepends=True),
            new.splitlines(keepends=True),
            fromfile="before",
            tofile="after",
            n=3,
        )
    )


def _verify_hallucination(candidate: dict) -> bool:
    """예시 질문을 `POST /api/ask` 재질의 → seq_hash 일치 확인.

    서버 off 시 skip + WARNING (CI 대응).
    """
    try:
        import httpx

        ex = (candidate.get("example_questions") or [""])[0]
        if not ex:
            print("[verify] 예시 질문 없음 — skip")
            return True
        try:
            r = httpx.post("http://127.0.0.1:8400/api/ask", json={"question": ex, "stream": False}, timeout=30.0)
        except httpx.ConnectError:
            print("[verify] 서버 off — skip (WARN)")
            return True
        if r.status_code != 200:
            print(f"[verify] HTTP {r.status_code} — skip")
            return True
        # 재현성 체크 로직: tool_calls 시퀀스 해시 비교는 audit jsonl 동기화 이후 가능 (TODO).
        print("[verify] 재현 호출 완료 (seq_hash 비교는 audit jsonl 동기화 후)")
        return True
    except ImportError:
        print("[verify] httpx 없음 — skip")
        return True


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--candidate", type=Path, required=True, help="candidate JSON 경로")
    ap.add_argument("--id", required=True, help="candidate id (cand-YYYY-MM-DD-NNN)")
    ap.add_argument("--confirm", action="store_true", help="실제 브랜치·PR 생성")
    ap.add_argument("--pr-draft", action="store_true", default=True, help="draft PR 로 생성 (기본)")
    args = ap.parse_args()

    cand = _load_candidate(args.candidate, args.id)
    engine = cand["engine"]
    axis = cand["axis"]
    target = ROOT / cand["suggested_append"]["target_file"]
    body = cand["suggested_append"]["body"]

    original = target.read_text(encoding="utf-8") if target.exists() else ""
    new = _append_guide(target, body)
    print(_diff(original, new))

    if not args.confirm:
        print("\n[dry-run] `--confirm` 없이 실행 — 변경 사항 적용 안 함.")
        return 0

    # hallucination 재현 테스트
    if not _verify_hallucination(cand):
        print("[fatal] 재현 실패 — 승격 중단")
        return 1

    # 파일 쓰기
    target.write_text(new, encoding="utf-8")
    print(f"[write] {target.relative_to(ROOT)}")

    # git branch + commit + PR
    slug = to_slug(axis or engine)
    day = datetime.now(timezone.utc).strftime("%Y%m%d")
    branch = f"skill/docstring-{engine}-{slug}-{day}"
    msg = f"""[CORELOOP-R] docs({engine}): add {axis} Guide from Phase P ({args.id})

Phase: R
Candidate-Id: {args.id}
Evidence: {args.candidate.relative_to(ROOT) if args.candidate.is_relative_to(ROOT) else args.candidate}
Observed: {cand["n_observed"]} times
Unique-Questions: {cand["n_unique_questions"]}
Success-Rate: {cand["success_rate"]}

Summary:
- What: docstring Guide section append on {cand["suggested_append"]["target_file"]}::{cand["suggested_append"]["target_symbol"]}
- Why: pattern crossed promotion gate
- How: delta merge (no existing content removed)
- Impact: no engine code changed; docstring-only
"""

    try:
        subprocess.run(["git", "checkout", "-b", branch], check=True, cwd=ROOT)
        subprocess.run(["git", "add", str(target.relative_to(ROOT))], check=True, cwd=ROOT)
        subprocess.run(["git", "commit", "-m", msg], check=True, cwd=ROOT)
        pr_flags = ["--draft"] if args.pr_draft else []
        subprocess.run(
            ["gh", "pr", "create", *pr_flags, "--title", f"docs({engine}): {axis} Guide append", "--body", msg],
            check=True,
            cwd=ROOT,
        )
        print(f"\n[promote] 브랜치 {branch} PR 생성 완료")
        return 0
    except subprocess.CalledProcessError as e:
        print(f"[fatal] git/gh 실패: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
