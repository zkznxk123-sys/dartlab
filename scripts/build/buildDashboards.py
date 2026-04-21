"""회사별 대시보드 JSON 사전 빌드.

`c.review(type='dashboard')` → `landing/static/dashboards/{stockCode}.json`.

사용법::

    # 전 종목 (기본)
    uv run python -X utf8 scripts/build/buildDashboards.py

    # 상위 N개만 (개발용 빠른 빌드)
    uv run python -X utf8 scripts/build/buildDashboards.py --companies 100

    # 특정 종목만
    uv run python -X utf8 scripts/build/buildDashboards.py --codes 005930,000660
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

import dartlab  # noqa: E402
from dartlab.industry.build.pipeline import loadNodes  # noqa: E402

OUT_DIR = ROOT / "landing" / "static" / "dashboards"


def buildOne(stockCode: str) -> dict | None:
    """한 종목에 대해 review(type='dashboard') → dict."""
    try:
        c = dartlab.Company(stockCode)
        r = c.review(type="dashboard")
        js = r.toJson() if hasattr(r, "toJson") else None
        if isinstance(js, str):
            return json.loads(js)
        if isinstance(js, dict):
            return js
        return None
    except Exception as e:
        print(f"  ⚠ {stockCode}: {e}", flush=True)
        return None


def main() -> int:
    parser = argparse.ArgumentParser(description="대시보드 JSON 사전 빌드")
    parser.add_argument("--companies", type=int, default=0, help="상위 N개만 (0=전체)")
    parser.add_argument("--codes", type=str, default="", help="종목코드 CSV (우선)")
    args = parser.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    # 대상 종목 선정
    if args.codes:
        targets = [c.strip() for c in args.codes.split(",") if c.strip()]
    else:
        nodes = loadNodes()
        ranked = sorted(nodes, key=lambda n: n.revenue or 0, reverse=True)
        if args.companies > 0:
            ranked = ranked[: args.companies]
        targets = [n.stockCode for n in ranked]

    total = len(targets)
    print(f"[대시보드 빌드] {total}개 종목 → {OUT_DIR}")

    t0 = time.time()
    built = 0
    failed = 0
    for i, code in enumerate(targets, 1):
        data = buildOne(code)
        if data is None:
            failed += 1
            continue
        (OUT_DIR / f"{code}.json").write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        built += 1
        if i % 50 == 0 or i == total:
            rate = i / (time.time() - t0) if time.time() > t0 else 0
            print(f"  [{i}/{total}] built={built} failed={failed} ({rate:.1f}/s)", flush=True)

    elapsed = time.time() - t0
    print(f"완료: {built}사 생성, {failed}사 실패 ({elapsed:.0f}초)")
    return 0 if failed < total else 1


if __name__ == "__main__":
    sys.exit(main())
