"""firstResultTime audit — clean env 첫 결과 시간 측정 (T4-6 + T12-5).

DX (T4) + UX (T12) 트랙의 측정 도구. 외부 기여자가 clone → 첫 결과 도달까지
얼마나 걸리는지 weekly CI 로 측정.

3 진입점 별 측정:
    1. **AI**: `python -X utf8 -c "import dartlab; dartlab.ask('...')"` (T12-5)
    2. **Python**: `python -X utf8 -c "import dartlab; print(dartlab.Company('005930').corpName)"`
    3. **CLI**: `dartlab show 005930 IS`

목표:
    - AI ≤ 1 분
    - Python ≤ 3 분
    - CLI ≤ 2 분

실행 환경 (CI):
    - Docker `python:3.12-slim` clean env
    - `pip install dartlab=={current_version}`
    - 3 진입점 각 time 측정

실행 (로컬, mock 모드)::

    uv run python -X utf8 tests/audit/firstResultTime.py --mock
    uv run python -X utf8 tests/audit/firstResultTime.py --entrypoint python
    uv run python -X utf8 tests/audit/firstResultTime.py --json

종료 코드:
    0 — 모든 진입점 임계값 이하
    2 — --strict + 임계값 초과
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import subprocess
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent

# 진입점별 명령 + 임계값 (초)
ENTRYPOINTS: dict[str, dict] = {
    "ai": {
        "cmd": [sys.executable, "-X", "utf8", "-c", "import dartlab; print(dartlab.__version__)"],
        "thresholdSec": 60,
        "label": "AI workbench (dartlab.ask) — 현재 placeholder = import 시간",
    },
    "python": {
        "cmd": [
            sys.executable,
            "-X",
            "utf8",
            "-c",
            "import dartlab; c = dartlab.Company('005930'); print(c.corpName)",
        ],
        "thresholdSec": 180,
        "label": "Python (Company.corpName)",
    },
    "cli": {
        "cmd": ["dartlab", "show", "005930", "IS"],
        "thresholdSec": 120,
        "label": "CLI (dartlab show)",
    },
}


def measureEntrypoint(name: str, mock: bool = False) -> dict:
    """단일 진입점 시간 측정 — subprocess.run 으로 wall-clock.

    Args:
        name: 진입점 이름 (ai/python/cli).
        mock: True 면 실제 호출 없이 placeholder 시간 반환.
    Returns:
        {entrypoint, thresholdSec, elapsedSec, passed, error?}.
    """
    spec = ENTRYPOINTS[name]
    threshold = spec["thresholdSec"]

    if mock:
        # mock 모드 — 기본 빠른 진입 가정
        return {
            "entrypoint": name,
            "thresholdSec": threshold,
            "elapsedSec": 1.0,
            "passed": True,
            "mock": True,
        }

    started = time.monotonic()
    try:
        result = subprocess.run(
            spec["cmd"],
            capture_output=True,
            text=True,
            timeout=threshold + 30,
            cwd=REPO_ROOT,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return {
            "entrypoint": name,
            "thresholdSec": threshold,
            "elapsedSec": threshold + 30,
            "passed": False,
            "error": "timeout",
        }
    except OSError as e:
        return {
            "entrypoint": name,
            "thresholdSec": threshold,
            "elapsedSec": -1.0,
            "passed": False,
            "error": f"OSError: {e}",
        }

    elapsed = round(time.monotonic() - started, 2)
    return {
        "entrypoint": name,
        "thresholdSec": threshold,
        "elapsedSec": elapsed,
        "exitCode": result.returncode,
        "passed": result.returncode == 0 and elapsed <= threshold,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="firstResultTime audit (T4-6 + T12-5)")
    parser.add_argument(
        "--entrypoint",
        choices=list(ENTRYPOINTS.keys()) + ["all"],
        default="all",
    )
    parser.add_argument("--mock", action="store_true", help="실제 호출 없이 placeholder (개발용)")
    parser.add_argument("--strict", action="store_true", help="임계값 초과 시 exit 2")
    parser.add_argument("--json", action="store_true", help="JSON 출력 (CI 산출물)")
    args = parser.parse_args()

    targets = list(ENTRYPOINTS.keys()) if args.entrypoint == "all" else [args.entrypoint]
    results = [measureEntrypoint(name, mock=args.mock) for name in targets]

    summary = {
        "measuredAt": dt.datetime.now(dt.UTC).isoformat(),
        "mock": args.mock,
        "results": results,
        "allPassed": all(r["passed"] for r in results),
    }

    if args.json:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    else:
        for r in results:
            spec = ENTRYPOINTS[r["entrypoint"]]
            status = "OK" if r["passed"] else "FAIL"
            print(
                f"[firstResultTime] {r['entrypoint']:8s} {status}  "
                f"{r['elapsedSec']:.2f}s / {r['thresholdSec']}s — {spec['label']}"
            )
            if "error" in r:
                print(f"  error: {r['error']}")
        print(f"[firstResultTime] 전체 {'PASS' if summary['allPassed'] else 'FAIL'}")

    if args.strict and not summary["allPassed"]:
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
