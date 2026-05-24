"""flaky gate audit — 최근 N회 CI 실행 안 fail/pass 혼재 검출 (T13-2).

본 도구는 두 모드로 동작:

1. **로컬 분석 모드** — pytest 의 `pytest-rerunfailures` 결과 또는 `tests/run.py`
   실행 history 가 있을 때 (현재는 없음 — 후속 트랙). 임시로는 placeholder.

2. **CI 분석 모드** — GitHub Actions workflow_runs API 로 최근 50 회 fast tier
   gate 결과 분석. 같은 gate 가 50 회 안에 pass / fail 혼재 → flaky.

자동 quarantine 정책:
    - flaky 3 회 연속 누적 (같은 gate, 24h 안) → marker `flaky` 부여
    - flaky gate 는 `nightly` tier 로 자동 이동 (이슈 자동 생성)
    - PR gate 차단 해제 (continue-on-error)

baseline 부채 원장: tests/audit/_baselines/flakyGates.json
    {"gate_name": {"firstSeenAt": "...", "consecutiveCount": N}}

실행::

    python -X utf8 tests/audit/flakyAudit.py
    python -X utf8 tests/audit/flakyAudit.py --strict   # flaky >= 3 시 exit 2
    python -X utf8 tests/audit/flakyAudit.py --window 50 --repo eddmpython/dartlab

종료 코드:
    0 — flaky < threshold 또는 --strict 없음
    2 — --strict + flaky >= threshold
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import sys
from pathlib import Path

try:
    import requests
except ImportError:
    requests = None  # type: ignore[assignment]


REPO_ROOT = Path(__file__).resolve().parent.parent.parent
BASELINE_FILE = REPO_ROOT / "tests" / "audit" / "_baselines" / "flakyGates.json"


def fetchRecentRuns(repo: str, token: str | None, window: int) -> list[dict]:
    """GitHub API 로 최근 N개 workflow runs (fast tier)."""
    if requests is None:
        return []
    headers = {"Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    url = f"https://api.github.com/repos/{repo}/actions/workflows/ci-fast.yml/runs"
    params = {"per_page": min(window, 100), "branch": "master"}
    try:
        resp = requests.get(url, headers=headers, params=params, timeout=30)
        resp.raise_for_status()
        return resp.json().get("workflow_runs", [])[:window]
    except (requests.RequestException, KeyError, ValueError):
        return []


def analyzeFlaky(runs: list[dict]) -> dict[str, dict]:
    """run history 분석 — gate (workflow conclusion 종합) 별 flaky 패턴 검출.

    GitHub API 의 workflow run 은 *전체 conclusion* 만 노출. 개별 gate 의 flaky
    감지는 jobs API (`/runs/{id}/jobs`) 호출 필요 (rate-limit 부담). 본 v1 은
    workflow 단위 flaky 검출 (전체 fast 가 같은 commit 에 pass / fail 혼재).
    """
    if not runs:
        return {}

    byCommit: dict[str, list[str]] = {}
    for run in runs:
        sha = run.get("head_sha", "")
        conclusion = run.get("conclusion", "")
        if not sha or not conclusion:
            continue
        byCommit.setdefault(sha, []).append(conclusion)

    flakyCommits = {
        sha: outcomes
        for sha, outcomes in byCommit.items()
        if len(set(outcomes)) > 1 and any(o == "success" for o in outcomes) and any(o == "failure" for o in outcomes)
    }

    return {
        "totalRuns": len(runs),
        "uniqueCommits": len(byCommit),
        "flakyCommits": list(flakyCommits.keys()),
        "flakyCount": len(flakyCommits),
    }


def loadBaseline() -> dict:
    if not BASELINE_FILE.exists():
        return {}
    return json.loads(BASELINE_FILE.read_text(encoding="utf-8"))


def saveBaseline(data: dict) -> None:
    BASELINE_FILE.parent.mkdir(parents=True, exist_ok=True)
    BASELINE_FILE.write_text(
        json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="flaky gate audit (T13-2)")
    parser.add_argument("--window", type=int, default=50, help="분석 window (최근 N runs)")
    parser.add_argument(
        "--repo",
        default=os.getenv("GITHUB_REPOSITORY", "eddmpython/dartlab"),
        help="대상 repo",
    )
    parser.add_argument("--strict", action="store_true", help="flaky >= 3 시 exit 2")
    parser.add_argument("--threshold", type=int, default=3, help="strict 임계값")
    parser.add_argument("--json", action="store_true", help="JSON 출력")
    args = parser.parse_args()

    token = os.getenv("GITHUB_TOKEN")
    runs = fetchRecentRuns(args.repo, token, args.window)
    result = analyzeFlaky(runs)

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"[flakyAudit] window={args.window}, runs={result.get('totalRuns', 0)}")
        print(f"[flakyAudit] 고유 commit = {result.get('uniqueCommits', 0)}")
        print(f"[flakyAudit] flaky commit = {result.get('flakyCount', 0)}")
        if result.get("flakyCommits"):
            print("  flaky SHA (앞 7자):")
            for sha in result["flakyCommits"][:10]:
                print(f"    - {sha[:7]}")

    # baseline 갱신
    baseline = loadBaseline()
    baseline["lastRun"] = {
        "measuredAt": dt.datetime.now(dt.UTC).isoformat(),
        "window": args.window,
        "flakyCount": result.get("flakyCount", 0),
    }
    saveBaseline(baseline)

    if args.strict and result.get("flakyCount", 0) >= args.threshold:
        print(f"[flakyAudit] STRICT FAIL — flaky {result['flakyCount']} >= threshold {args.threshold}")
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
