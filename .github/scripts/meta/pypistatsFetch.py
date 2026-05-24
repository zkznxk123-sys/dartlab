"""PyPI 다운로드 통계 수집 (T12-2).

pypistats.org API 로 dartlab 패키지의 최근 다운로드 추세 수집.
산출물: `landing/static/metrics/pypi/{date}.json` — T1-5 health dashboard 통합.

실행::

    python -X utf8 .github/scripts/meta/pypistatsFetch.py
    python -X utf8 .github/scripts/meta/pypistatsFetch.py --package dartlab --output ...

API: https://pypistats.org/api/packages/dartlab/recent
형식: {data: {last_day, last_week, last_month}, package, type}
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from pathlib import Path

try:
    import requests
except ImportError:
    requests = None  # type: ignore[assignment]


REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent


def fetchRecent(packageName: str) -> dict:
    """pypistats recent endpoint 호출 — last_day/last_week/last_month."""
    if requests is None:
        return {"error": "requests not installed"}
    try:
        resp = requests.get(f"https://pypistats.org/api/packages/{packageName}/recent", timeout=30)
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException as e:
        return {"error": str(e)}


def fetchOverall(packageName: str) -> dict:
    """pypistats overall endpoint — Python version + system 분포."""
    if requests is None:
        return {"error": "requests not installed"}
    try:
        resp = requests.get(f"https://pypistats.org/api/packages/{packageName}/overall", timeout=30)
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException as e:
        return {"error": str(e)}


def main() -> int:
    parser = argparse.ArgumentParser(description="PyPI stats fetch (T12-2)")
    parser.add_argument("--package", default="dartlab", help="대상 패키지명")
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="출력 JSON 파일 (기본 landing/static/metrics/pypi/{date}.json)",
    )
    args = parser.parse_args()

    recent = fetchRecent(args.package)
    overall = fetchOverall(args.package)

    result = {
        "fetchedAt": dt.datetime.now(dt.UTC).isoformat(),
        "package": args.package,
        "recent": recent,
        "overall": overall,
    }

    if args.output is None:
        today = dt.datetime.now(dt.UTC).strftime("%Y-%m-%d")
        args.output = REPO_ROOT / "landing" / "static" / "metrics" / "pypi" / f"{today}.json"

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[pypistats] {args.package} → {args.output}")
    if "error" in recent or "error" in overall:
        print(
            f"[pypistats] WARN — recent.error: {recent.get('error', 'none')}, overall.error: {overall.get('error', 'none')}"
        )
    else:
        last_month = recent.get("data", {}).get("last_month", "?")
        last_week = recent.get("data", {}).get("last_week", "?")
        print(f"[pypistats] last_month: {last_month}, last_week: {last_week}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
