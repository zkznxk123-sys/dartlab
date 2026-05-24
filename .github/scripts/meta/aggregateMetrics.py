"""T1-2 metrics aggregate — 30 일 rolling window 집계.

collectMetrics.py 의 daily JSON 들을 모아 시계열 + 평균/최대/최소 산출.
짝: metrics.yml workflow 가 매일 collect 후 호출.

실행::

    python -X utf8 .github/scripts/meta/aggregateMetrics.py \
        --input-dir landing/static/metrics/ \
        --window 30 \
        --output landing/static/metrics/rolling.json
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description="T1-2 metrics rolling 집계")
    parser.add_argument("--input-dir", required=True, help="daily JSON 폴더")
    parser.add_argument("--window", type=int, default=30, help="rolling window 일 수")
    parser.add_argument("--output", required=True, help="rolling 결과 JSON")
    args = parser.parse_args()

    inputDir = Path(args.input_dir)
    if not inputDir.is_dir():
        print(f"[aggregate] 입력 폴더 없음: {inputDir}")
        return 0

    cutoff = dt.datetime.now(dt.UTC) - dt.timedelta(days=args.window)
    daily: list[dict] = []
    for jsonFile in sorted(inputDir.glob("*.json")):
        if jsonFile.name == "rolling.json":
            continue
        try:
            data = json.loads(jsonFile.read_text(encoding="utf-8"))
            measured = dt.datetime.fromisoformat(data["measuredAt"].replace("Z", "+00:00"))
        except (json.JSONDecodeError, KeyError, ValueError, OSError):
            continue
        if measured < cutoff:
            continue
        daily.append(data)

    if not daily:
        rolling = {"window": args.window, "sampleN": 0, "signals": {}}
    else:
        # 신호별 시계열 + 통계
        signalNames = list(daily[0].get("signals", {}).keys())
        signals: dict[str, dict] = {}
        for name in signalNames:
            values = [d["signals"].get(name) for d in daily if d.get("signals", {}).get(name) is not None]
            numericValues = [v for v in values if isinstance(v, (int, float)) and v >= 0]
            if not numericValues:
                signals[name] = {"sampleN": 0}
                continue
            signals[name] = {
                "sampleN": len(numericValues),
                "latest": numericValues[-1],
                "min": min(numericValues),
                "max": max(numericValues),
                "avg": round(sum(numericValues) / len(numericValues), 2),
            }
        rolling = {
            "computedAt": dt.datetime.now(dt.UTC).isoformat(),
            "window": args.window,
            "sampleN": len(daily),
            "signals": signals,
        }

    outputPath = Path(args.output)
    outputPath.parent.mkdir(parents=True, exist_ok=True)
    outputPath.write_text(json.dumps(rolling, ensure_ascii=False, indent=2), encoding="utf-8")
    print(
        f"[aggregate] {args.window}일 rolling — sampleN={rolling.get('sampleN', 0)}, 신호 {len(rolling.get('signals', {}))}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
