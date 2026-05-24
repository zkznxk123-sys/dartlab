"""importLinter exception 카운트 measure + monthly quota 가드 (T9-2).

pyproject.toml [tool.importlinter] 의 ignore_imports / forbidden 등 예외 라인을
세고 baseline 대비 *신규 증가 시 차단*. monthly 5건 정리 quota 강제 (TODO 부록 F.9).

baseline: tests/audit/_baselines/importLinterExceptions.json
목표: Q4 ≤ 50 (현재 baseline 측정).

실행::

    uv run python -X utf8 tests/audit/importLinterExceptionAudit.py
    uv run python -X utf8 tests/audit/importLinterExceptionAudit.py --strict
    uv run python -X utf8 tests/audit/importLinterExceptionAudit.py --update-baseline
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
PYPROJECT = REPO_ROOT / "pyproject.toml"
BASELINE_FILE = REPO_ROOT / "tests" / "audit" / "_baselines" / "importLinterExceptions.json"


def countExceptions() -> dict[str, int]:
    """pyproject.toml 안 importlinter 예외 라인 카운트.

    측정 패턴:
        - `ignore_imports = ...` 또는 `ignore_imports = [...]`
        - `forbidden_modules = ...`
        - `allowed_imports = ...`
    """
    if not PYPROJECT.exists():
        return {"total": 0}
    text = PYPROJECT.read_text(encoding="utf-8")

    # `[tool.importlinter*]` 섹션 추출
    importlinterSection = re.search(
        r"\[tool\.importlinter[^\]]*\](.*?)(?=^\[|\Z)",
        text,
        re.MULTILINE | re.DOTALL,
    )
    if not importlinterSection:
        return {"total": 0}

    body = importlinterSection.group(1)

    ignoreImportsCount = len(re.findall(r"ignore_imports\s*=", body))
    forbiddenCount = len(re.findall(r"forbidden_modules\s*=", body))
    allowedCount = len(re.findall(r"allowed_imports\s*=", body))

    # 인용 라인 (list 안 string literals) 도 카운트
    quotedLines = len(re.findall(r'^\s*"dartlab\.[^"]+",?\s*$', body, re.MULTILINE))

    return {
        "ignore_imports_directives": ignoreImportsCount,
        "forbidden_modules_directives": forbiddenCount,
        "allowed_imports_directives": allowedCount,
        "quoted_module_lines": quotedLines,
        "total": ignoreImportsCount + forbiddenCount + allowedCount + quotedLines,
    }


def loadBaseline() -> dict:
    if not BASELINE_FILE.exists():
        return {}
    try:
        return json.loads(BASELINE_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def saveBaseline(data: dict) -> None:
    BASELINE_FILE.parent.mkdir(parents=True, exist_ok=True)
    BASELINE_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="importLinter exception count audit (T9-2)")
    parser.add_argument("--strict", action="store_true", help="신규 exception 증가 시 exit 2")
    parser.add_argument("--update-baseline", action="store_true", help="현재 카운트를 baseline 으로 저장")
    parser.add_argument("--json", action="store_true", help="JSON 출력")
    args = parser.parse_args()

    current = countExceptions()
    baseline = loadBaseline()
    baselineTotal = baseline.get("total", -1)

    if args.update_baseline:
        baseline = {
            "measuredAt": dt.datetime.now(dt.UTC).isoformat(),
            **current,
        }
        saveBaseline(baseline)
        print(f"[importLinter] baseline 갱신 — total = {current['total']}")
        return 0

    delta = current["total"] - baselineTotal if baselineTotal >= 0 else 0

    if args.json:
        print(json.dumps({"current": current, "baseline": baseline, "delta": delta}, ensure_ascii=False, indent=2))
    else:
        print("[importLinter] 현재 예외 카운트:")
        for k, v in current.items():
            print(f"  {k}: {v}")
        if baselineTotal >= 0:
            print(f"[importLinter] baseline total: {baselineTotal} (delta {delta:+d})")
            if delta > 0:
                print(f"[importLinter] WARN — exception {delta} 건 증가 (monthly quota 5)")
        else:
            print("[importLinter] baseline 없음 — --update-baseline 으로 첫 측정")

    if args.strict and delta > 0:
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
