"""macro.cycle → landing/static/dashboards/macro.json

대시보드 v19 신규 Tier — 단일 파일 (회사 종속 X).
현재 경기 국면 + 섹터별 순풍/역풍 가중치.

출력 shape::

    {
      "version": "v19",
      "asOf": "2026-04-22",
      "kr": { phase, phaseLabel, confidence, indicators: {...}, signals: [...], sectorStrategy: "..." },
      "us": { 동일 },
      "transmission": { drivers, edges, sourceRefs, missing },
      "sectorTailwind": {
        "semiconductor": { "kr": +0.4, "us": +0.2 },
        ...
      }
    }

실행::

    uv run python -X utf8 .github/scripts/prebuild/buildMacroJson.py
    # ~30초, <500MB
"""

from __future__ import annotations

import json
import sys
import time
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
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


def _fallback(market: str) -> dict:
    return {
        "market": market,
        "phase": "expansion",
        "phaseLabel": "확장",
        "confidence": "low",
        "signals": [],
        "sectorStrategy": "데이터 수집 중.",
    }


def _analyze_market(market: str) -> dict:
    """sync 단계 (buildMacroCycle.py) 가 미리 산출한 cycle JSON 을 읽는다.

    HF dataset ``macro/cycle/{market}.json`` 우선, 없으면 로컬 cache, 모두 없으면
    기본값. 본 함수는 외부 API 호출 0 — prebuild offline 가드 통과.
    """
    lower = market.lower()

    # 1. 로컬 cache (sync 단계가 같은 머신에서 돌았다면 존재)
    localPath = ROOT / "data" / "macro" / "cycle" / f"{lower}.json"
    if localPath.exists():
        try:
            return json.loads(localPath.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as e:
            print(f"  ⚠ {market} local cache load 실패: {e}", flush=True)

    # 2. HF dataset 다운로드 (offline 가드는 HF 호스트 default allow)
    try:
        from huggingface_hub import hf_hub_download

        path = hf_hub_download(
            repo_id="eddmpython/dartlab-data",
            repo_type="dataset",
            filename=f"macro/cycle/{lower}.json",
        )
        result = json.loads(Path(path).read_text(encoding="utf-8"))
        # 로컬 cache 도 저장 — 다음 실행 빠르게.
        localPath.parent.mkdir(parents=True, exist_ok=True)
        localPath.write_text(json.dumps(result, ensure_ascii=False, indent=0), encoding="utf-8")
        return result
    except Exception as e:
        print(f"  ⚠ {market} HF cycle JSON 미가용 ({type(e).__name__}): fallback", flush=True)
        return _fallback(market)


def _build_transmission() -> dict:
    """Macro Lens용 시장·섹터 전파 payload 를 macro.json 에 싣는다.

    ``analyzeTransmission`` 은 회사 객체를 읽지 않고, macro observation 이 없으면 missing
    lineage 로 닫힌다. prebuild offline 환경에서는 외부 API 호출 없이 HF/local cache 또는
    missing payload 만 만든다.
    """
    try:
        from dartlab.macro.transmission import analyzeTransmission

        payload = analyzeTransmission("KR", includeCrossMarket=True)
        payload["version"] = "v1"
        return payload
    except Exception as e:
        print(f"  ⚠ macro transmission 미가용 ({type(e).__name__}): missing payload", flush=True)
        return {
            "version": "v1",
            "market": "KR",
            "sectorKey": None,
            "asOf": None,
            "drivers": [],
            "edges": [],
            "regimeEvidence": [],
            "aliases": {},
            "sourceRefs": ["dartlab://macro/transmission"],
            "missing": [
                {
                    "id": "macro.transmission",
                    "status": "missing",
                    "reason": f"macro transmission unavailable: {type(e).__name__}",
                    "sourceRef": "dartlab://macro/transmission",
                }
            ],
        }


def main() -> int:
    # prebuild = offline only. analyzeCycle (외부 API) 호출은 sync 단계로 이전,
    # 여기서는 HF dataset 의 macro/cycle/{kr,us}.json 만 다운로드해서 사용.
    from dartlab.core.offlineGuard import enforceOffline

    enforceOffline()

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
    transmission = _build_transmission()

    output = {
        "version": "v19",
        "asOf": date.today().isoformat(),
        "kr": kr,
        "us": us,
        "transmission": transmission,
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
