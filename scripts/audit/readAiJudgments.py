"""수동 AI audit 판정 JSONL UTF-8 판독기.

PowerShell 출력 인코딩에 기대지 않고 Python UTF-8 reader 로
data/audit/ai-judgment/*.jsonl 의 P/T/C/V 판정을 요약한다.

사용법:
    uv run python -X utf8 scripts/audit/readAiJudgments.py
    uv run python -X utf8 scripts/audit/readAiJudgments.py --file data/audit/ai-judgment/2026-04-28.jsonl
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any


def _resolveDataDir() -> Path:
    try:
        import dartlab

        return Path(dartlab.dataDir())
    except Exception:
        return Path.cwd() / "data"


def _iterRows(paths: list[Path]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in paths:
        if not path.exists():
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            rows.append(json.loads(line))
    return rows


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser()
    parser.add_argument("--file", type=Path, help="특정 ai-judgment JSONL 파일")
    args = parser.parse_args()

    if args.file:
        paths = [args.file]
    else:
        root = _resolveDataDir() / "audit" / "ai-judgment"
        paths = sorted(root.glob("*.jsonl"))

    rows = _iterRows(paths)
    counts = Counter(str(row.get("verdict") or "?") for row in rows)
    print(f"files={len(paths)} rows={len(rows)} P={counts['P']} T={counts['T']} C={counts['C']} V={counts['V']}")
    for row in rows[-20:]:
        print(
            "\t".join(
                [
                    str(row.get("ts", ""))[:19],
                    str(row.get("verdict", "")),
                    str(row.get("issue_code") or ""),
                    str(row.get("request_id") or ""),
                    str(row.get("reason") or ""),
                ]
            )
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
