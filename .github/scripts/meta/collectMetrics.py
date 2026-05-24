"""T1-2 metrics workflow — 7 신호 수집 진입점.

GitHub Actions metrics.yml 가 매일 호출. 산출물: landing/static/metrics/{date}.json.
짝: aggregateMetrics.py (30일 rolling) + landing /health route (T1-5).

수집 신호 (7):
    1. ci_fast_pass_rate_7d — 최근 7일 CI Fast workflow 통과율
    2. ci_fast_avg_duration_min — 최근 7일 평균 시간
    3. test_count_unit — pytest unit marker 갯수 (git ls 기반)
    4. test_loc_ratio — test/prod LOC 비율 (testLocRatio.py)
    5. public_api_count — dartlab.__all__ 심볼 수
    6. dependency_count — pyproject.toml dependencies 수
    7. open_incidents_count — docs/INCIDENTS.md 안 미해결 항목 (placeholder, 정밀화는 후속)

실행::

    python -X utf8 .github/scripts/meta/collectMetrics.py \
        --repo owner/repo --output path.json
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import subprocess
import sys
from pathlib import Path

try:
    import requests
except ImportError:
    requests = None  # type: ignore[assignment]


REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent


def fetchCiFastStats(repo: str, token: str | None) -> tuple[float, float]:
    """GitHub API 로 최근 7일 CI Fast workflow runs 통계.

    Returns (passRate, avgDurationMin). 실패 시 (None, None) 으로 placeholder.
    """
    if requests is None:
        return -1.0, -1.0
    headers = {"Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    url = f"https://api.github.com/repos/{repo}/actions/workflows/ci-fast.yml/runs"
    params = {"per_page": 100, "branch": "master"}
    try:
        resp = requests.get(url, headers=headers, params=params, timeout=30)
        resp.raise_for_status()
        runs = resp.json().get("workflow_runs", [])
    except (requests.RequestException, KeyError, ValueError):
        return -1.0, -1.0

    cutoff = dt.datetime.now(dt.UTC) - dt.timedelta(days=7)
    recent = []
    for run in runs:
        try:
            created = dt.datetime.fromisoformat(run["created_at"].replace("Z", "+00:00"))
        except (KeyError, ValueError):
            continue
        if created < cutoff:
            continue
        recent.append(run)

    if not recent:
        return 0.0, 0.0

    success = sum(1 for r in recent if r.get("conclusion") == "success")
    passRate = round(success / len(recent) * 100, 2)

    durations = []
    for r in recent:
        try:
            start = dt.datetime.fromisoformat(r["run_started_at"].replace("Z", "+00:00"))
            end = dt.datetime.fromisoformat(r["updated_at"].replace("Z", "+00:00"))
            durations.append((end - start).total_seconds() / 60.0)
        except (KeyError, ValueError):
            continue
    avgDuration = round(sum(durations) / len(durations), 2) if durations else 0.0

    return passRate, avgDuration


def countUnitTests() -> int:
    """pytest unit marker 갯수 — `@pytest.mark.unit` AST 등가 grep."""
    pattern = re.compile(r"@pytest\.mark\.unit\b")
    count = 0
    testsDir = REPO_ROOT / "tests"
    for pyFile in testsDir.rglob("*.py"):
        if "_attempts" in pyFile.parts or "_drafts" in pyFile.parts:
            continue
        try:
            text = pyFile.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        count += len(pattern.findall(text))
    return count


def fetchTestLocRatio() -> float:
    """testLocRatio.py 호출 → JSON parse → 비율 추출."""
    try:
        result = subprocess.run(
            [sys.executable, "-X", "utf8", "tests/audit/testLocRatio.py", "--json"],
            capture_output=True,
            text=True,
            timeout=60,
            cwd=REPO_ROOT,
            check=False,
        )
        if result.returncode != 0:
            return -1.0
        data = json.loads(result.stdout)
        return float(data.get("ratio", -1.0))
    except (subprocess.SubprocessError, json.JSONDecodeError, ValueError, OSError):
        return -1.0


def countPublicApi() -> int:
    """dartlab.__all__ 심볼 수 — `__init__.py` 의 `__all__` grep."""
    initPath = REPO_ROOT / "src" / "dartlab" / "__init__.py"
    if not initPath.exists():
        return 0
    text = initPath.read_text(encoding="utf-8")
    match = re.search(r"__all__\s*=\s*\[(.*?)\]", text, re.DOTALL)
    if not match:
        return 0
    body = match.group(1)
    return len(re.findall(r'["\'][\w.]+["\']', body))


def countDependencies() -> int:
    """pyproject.toml `[project].dependencies` 수."""
    pyproject = REPO_ROOT / "pyproject.toml"
    if not pyproject.exists():
        return 0
    text = pyproject.read_text(encoding="utf-8")
    match = re.search(r"dependencies\s*=\s*\[(.*?)\]", text, re.DOTALL)
    if not match:
        return 0
    body = match.group(1)
    # 각 entry 는 "package..." 형식 string literal
    return len(re.findall(r'["\'][^"\']+["\']', body))


def countOpenIncidents() -> int:
    """docs/INCIDENTS.md 안 항목 수 placeholder.

    정밀화 (resolved vs open) 는 후속. 현재 ## 헤딩 수 카운트.
    """
    path = REPO_ROOT / "docs" / "INCIDENTS.md"
    if not path.exists():
        return 0
    text = path.read_text(encoding="utf-8")
    # "## YYYY-MM-DD" 패턴
    return len(re.findall(r"^## \d{4}-\d{2}", text, re.MULTILINE))


def main() -> int:
    parser = argparse.ArgumentParser(description="T1-2 metrics 7 신호 수집")
    parser.add_argument("--repo", required=False, default=os.getenv("GITHUB_REPOSITORY", ""))
    parser.add_argument("--output", required=True, help="산출 JSON 파일 경로")
    args = parser.parse_args()

    token = os.getenv("GITHUB_TOKEN")
    passRate, avgDuration = fetchCiFastStats(args.repo, token) if args.repo else (-1.0, -1.0)

    metrics = {
        "measuredAt": dt.datetime.now(dt.UTC).isoformat(),
        "repo": args.repo,
        "signals": {
            "ci_fast_pass_rate_7d": passRate,
            "ci_fast_avg_duration_min": avgDuration,
            "test_count_unit": countUnitTests(),
            "test_loc_ratio": fetchTestLocRatio(),
            "public_api_count": countPublicApi(),
            "dependency_count": countDependencies(),
            "open_incidents_count": countOpenIncidents(),
        },
    }

    outputPath = Path(args.output)
    outputPath.parent.mkdir(parents=True, exist_ok=True)
    outputPath.write_text(json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[metrics] 산출 {outputPath} — 신호 {len(metrics['signals'])} 개")
    return 0


if __name__ == "__main__":
    sys.exit(main())
