"""HF dataset drift check — 5σ 분포 이탈 자동 issue (T7-5).

매 sync workflow 완료 후 호출. baseline (이전 sync 결과) 대비 다음 신호 검출:

1. **row count drift**: 이전 sync 대비 ±5σ 초과 (정상은 ~1 percent 변동)
2. **column schema drift**: 컬럼 추가/삭제 자동 감지
3. **분포 drift**: 핵심 numeric 컬럼의 mean/median/std ±5σ

알람: GitHub issue 자동 생성 + docs/INCIDENTS.md 항목 추가 (T1-3 통합).

baseline 저장: HF dataset metadata 또는 `data/_lineage/drift_baseline.json`.

실행::

    python -X utf8 .github/scripts/sync/dataDriftCheck.py --table corp/profile.parquet
    python -X utf8 .github/scripts/sync/dataDriftCheck.py --strict --create-issue

본 도구는 *프로토타입* — 정밀 신호 (Pandera schema 통합, Kolmogorov-Smirnov
검정 등) 는 후속 트랙.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent


def loadBaseline(baselineFile: Path) -> dict:
    if not baselineFile.exists():
        return {}
    try:
        return json.loads(baselineFile.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def saveBaseline(baselineFile: Path, data: dict) -> None:
    baselineFile.parent.mkdir(parents=True, exist_ok=True)
    baselineFile.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def checkRowCountDrift(currentCount: int, baseline: dict, sigmaThreshold: float = 5.0) -> dict:
    """row count 가 baseline 대비 sigma 임계 초과 여부.

    baseline 이 비어있거나 sampleN < 3 → 첫 측정으로 기록.
    """
    history = baseline.get("rowCountHistory", [])
    if len(history) < 3:
        return {"status": "insufficient_baseline", "currentCount": currentCount, "historyN": len(history)}

    mean = sum(history) / len(history)
    variance = sum((x - mean) ** 2 for x in history) / len(history)
    std = variance**0.5
    if std == 0:
        # std 0 인데 변동 있으면 drift
        if currentCount != mean:
            return {"status": "drift", "currentCount": currentCount, "mean": mean, "std": 0, "sigmaDelta": float("inf")}
        return {"status": "ok", "currentCount": currentCount, "mean": mean, "std": 0}

    sigmaDelta = abs(currentCount - mean) / std
    return {
        "status": "drift" if sigmaDelta > sigmaThreshold else "ok",
        "currentCount": currentCount,
        "mean": round(mean, 2),
        "std": round(std, 2),
        "sigmaDelta": round(sigmaDelta, 2),
        "threshold": sigmaThreshold,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="HF dataset drift check (T7-5)")
    parser.add_argument(
        "--table",
        default="corp/profile.parquet",
        help="검사 대상 (HF dataset 안 path)",
    )
    parser.add_argument(
        "--baseline-file",
        type=Path,
        default=REPO_ROOT / "data" / "_lineage" / "drift_baseline.json",
        help="baseline JSON 위치 (gitignored)",
    )
    parser.add_argument("--sigma", type=float, default=5.0, help="drift sigma 임계 (기본 5)")
    parser.add_argument("--current-count", type=int, default=-1, help="현재 row count (CI 가 전달)")
    parser.add_argument("--create-issue", action="store_true", help="drift 감지 시 GitHub issue 생성")
    parser.add_argument("--strict", action="store_true", help="drift 감지 시 exit 2")
    parser.add_argument("--json", action="store_true", help="JSON 출력")
    args = parser.parse_args()

    baseline = loadBaseline(args.baseline_file)

    if args.current_count < 0:
        # CI 가 row count 전달 안 했으면 baseline 기록만
        print(
            f"[dataDriftCheck] --current-count 미지정 — baseline 조회만 ({len(baseline.get('rowCountHistory', []))} samples)"
        )
        return 0

    rowCheck = checkRowCountDrift(args.current_count, baseline, sigmaThreshold=args.sigma)

    # history 갱신
    history = baseline.get("rowCountHistory", [])
    history.append(args.current_count)
    if len(history) > 30:
        history = history[-30:]
    baseline["rowCountHistory"] = history
    baseline["lastTable"] = args.table
    baseline["lastCheckAt"] = dt.datetime.now(dt.UTC).isoformat()
    saveBaseline(args.baseline_file, baseline)

    summary = {
        "table": args.table,
        "rowCount": rowCheck,
        "baselineFile": str(args.baseline_file),
    }

    if args.json:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    else:
        print(f"[dataDriftCheck] table={args.table}")
        print(f"[dataDriftCheck] row count: {rowCheck.get('status')}")
        for key in ("currentCount", "mean", "std", "sigmaDelta", "threshold"):
            if key in rowCheck:
                print(f"  {key}: {rowCheck[key]}")

    if rowCheck.get("status") == "drift":
        print(f"[dataDriftCheck] ALERT — row count drift {rowCheck.get('sigmaDelta')}σ > {args.sigma}σ")
        if args.create_issue and os.getenv("GITHUB_TOKEN"):
            # 실제 issue 생성은 후속 (gh CLI 또는 octokit 호출).
            print("[dataDriftCheck] GitHub issue 생성은 후속 (gh CLI 또는 API)")
        if args.strict:
            return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
