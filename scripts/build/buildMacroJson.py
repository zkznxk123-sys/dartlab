"""macro.cycle → landing/static/dashboards/macro.json

대시보드 v19 신규 Tier — 단일 파일 (회사 종속 X).
현재 경기 국면 + 섹터별 순풍/역풍 가중치.

출력 shape::

    {
      "version": "v19",
      "asOf": "2026-04-22",
      "kr": { phase, phaseLabel, confidence, indicators: {...}, signals: [...], sectorStrategy: "..." },
      "us": { 동일 },
      "sectorTailwind": {
        "semiconductor": { "kr": +0.4, "us": +0.2 },
        ...
      }
    }

실행::

    uv run python -X utf8 scripts/build/buildMacroJson.py
    # ~30초, <500MB
"""

from __future__ import annotations

import json
import sys
import time
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

OUT = ROOT / "landing" / "static" / "dashboards" / "macro.json"


# 섹터별 국면 민감도: ecosystem 의 industry 이름 → 국면별 tailwind/headwind (-1 ~ +1)
# 값이 +면 순풍 (좋음), -면 역풍 (나쁨)
SECTOR_SENSITIVITY = {
    "expansion": {
        "semiconductor": 0.6,
        "automotive": 0.5,
        "retail": 0.4,
        "it_software": 0.5,
        "construction": 0.3,
        "chemicals": 0.2,
        "shipbuilding": 0.4,
        "steel": 0.2,
        "display": 0.4,
        "biotech": 0.1,
        "finance": 0.3,
        "energy": 0.0,
    },
    "slowdown": {
        "semiconductor": -0.2,
        "automotive": -0.3,
        "retail": -0.2,
        "it_software": 0.1,
        "construction": -0.4,
        "chemicals": -0.2,
        "shipbuilding": -0.1,
        "steel": -0.3,
        "display": -0.2,
        "biotech": 0.2,
        "finance": -0.1,
        "energy": 0.1,
    },
    "contraction": {
        "semiconductor": -0.5,
        "automotive": -0.6,
        "retail": -0.4,
        "it_software": -0.2,
        "construction": -0.5,
        "chemicals": -0.4,
        "shipbuilding": -0.3,
        "steel": -0.5,
        "display": -0.5,
        "biotech": 0.3,
        "finance": -0.3,
        "energy": -0.2,
    },
    "recovery": {
        "semiconductor": 0.5,
        "automotive": 0.4,
        "retail": 0.3,
        "it_software": 0.4,
        "construction": 0.5,
        "chemicals": 0.3,
        "shipbuilding": 0.3,
        "steel": 0.4,
        "display": 0.3,
        "biotech": 0.0,
        "finance": 0.4,
        "energy": 0.3,
    },
}


def _analyze_market(market: str) -> dict:
    """classifyCycle for market. 실패 시 기본값."""
    try:
        from dartlab.macro.cycles.cycle import analyzeCycle

        result = analyzeCycle(market=market)
        # 시계열은 제거 (용량 축소)
        result.pop("timeseries", None)
        return result
    except Exception as e:
        print(f"  ⚠ {market}: {type(e).__name__}: {e}", flush=True)
        return {
            "market": market,
            "phase": "expansion",
            "phaseLabel": "확장",
            "confidence": "low",
            "signals": [],
            "sectorStrategy": "데이터 수집 중.",
        }


def main() -> int:
    t0 = time.time()
    print("[macro.json 빌드]", flush=True)

    print("  KR analyzing…", flush=True)
    kr = _analyze_market("KR")
    print(f"    phase: {kr.get('phase')} · {kr.get('phaseLabel')}", flush=True)

    print("  US analyzing…", flush=True)
    us = _analyze_market("US")
    print(f"    phase: {us.get('phase')} · {us.get('phaseLabel')}", flush=True)

    # 섹터 tailwind 계산 — 현재 KR/US 국면에 따라 값 look-up
    kr_phase = kr.get("phase", "expansion")
    us_phase = us.get("phase", "expansion")
    kr_map = SECTOR_SENSITIVITY.get(kr_phase, {})
    us_map = SECTOR_SENSITIVITY.get(us_phase, {})

    sectors = set(kr_map.keys()) | set(us_map.keys())
    sector_tailwind = {
        s: {
            "kr": round(kr_map.get(s, 0.0), 2),
            "us": round(us_map.get(s, 0.0), 2),
            "blended": round((kr_map.get(s, 0.0) * 0.6 + us_map.get(s, 0.0) * 0.4), 2),
        }
        for s in sorted(sectors)
    }

    output = {
        "version": "v19",
        "asOf": date.today().isoformat(),
        "kr": kr,
        "us": us,
        "sectorTailwind": sector_tailwind,
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(output, ensure_ascii=False, indent=0), encoding="utf-8")

    size_kb = OUT.stat().st_size / 1024
    elapsed = time.time() - t0
    print(f"완료: {size_kb:.1f}KB, {elapsed:.0f}초 → {OUT}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
