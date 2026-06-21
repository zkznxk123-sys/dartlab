"""Prebuild stage — offline only(``enforceOffline()`` 강제) derived JSON 합성.

``.github/scripts/prebuild/*.py`` 의 offline 오케스트레이션을 stage 함수로 흡수. 첫 증명
인스턴스 = ``runMacroJson`` (``buildMacroJson.py`` 흡수). prebuild 는 외부 API 호출 0 —
sync 단계가 HF 에 publish 한 산출(``macro/cycle|regime/{kr,us}.json``)을 download 해
derived asset(``landing/static/dashboards/macro.json`` v20)으로 조립한다.

⛔ offline 불변: 각 ``run*`` 함수의 첫 비-docstring statement 는 반드시
``enforceOffline()`` (AST 게이트 ``test_inlibrary_prebuild_offline``). 모듈은
``_FORBIDDEN_IMPORTS`` 7종(``dartlab.gather.fred``·``dartlab.macro.cycles.cycle``·
``seriesFetch``·``forecast``·``rates`` 등)을 import 하지 않는다 — fetch-independent
``analyzeTransmission`` 만 허용. HF download(``hf_hub_download``)는 offlineGuard allow-list.
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from dartlab.pipeline.types import PipelineMode, StageResult

_ROOT = Path(__file__).resolve().parents[4]
_MACRO_JSON_OUT = _ROOT / "landing" / "static" / "dashboards" / "macro.json"
_REPO_ID = "eddmpython/dartlab-data"


# 섹터별 국면 민감도: ecosystem 의 industry 이름 → 국면별 tailwind/headwind (-1 ~ +1).
# 값이 +면 순풍(좋음), -면 역풍(나쁨). buildMacroJson.py 정적 dict 이전.
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


def _fallbackCycle(market: str) -> dict:
    return {
        "market": market,
        "phase": "expansion",
        "phaseLabel": "확장",
        "confidence": "low",
        "signals": [],
        "sectorStrategy": "데이터 수집 중.",
    }


def _analyzeMarket(market: str) -> dict:
    """sync 단계(runMacroCycle)가 미리 산출한 cycle JSON 을 읽는다.

    로컬 cache → HF dataset ``macro/cycle/{market}.json`` download → 기본값. 외부 API 0 —
    prebuild offline 가드 통과(HF host 는 default allow).
    """
    lower = market.lower()

    localPath = _ROOT / "data" / "macro" / "cycle" / f"{lower}.json"
    if localPath.exists():
        try:
            return json.loads(localPath.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as e:
            print(f"  ⚠ {market} local cache load 실패: {e}", flush=True)

    try:
        from huggingface_hub import hf_hub_download

        path = hf_hub_download(
            repo_id=_REPO_ID,
            repo_type="dataset",
            filename=f"macro/cycle/{lower}.json",
        )
        result = json.loads(Path(path).read_text(encoding="utf-8"))
        localPath.parent.mkdir(parents=True, exist_ok=True)
        localPath.write_text(json.dumps(result, ensure_ascii=False, indent=0), encoding="utf-8")
        return result
    except Exception as e:  # noqa: BLE001 — HF 미가용은 fallback(missing 명시·crash 0)
        print(f"  ⚠ {market} HF cycle JSON 미가용 ({type(e).__name__}): fallback", flush=True)
        return _fallbackCycle(market)


def _loadRegime(market: str) -> dict:
    """sync(runMacroRegime)가 산출한 regime payload 를 읽는다 — offline.

    로컬 cache → HF download → missing payload 순(외부 API 0). freshness 재계산 0 —
    sync 시점 asOf 동결 전달(거짓 신선도 방지).
    """
    lower = market.lower()

    localPath = _ROOT / "data" / "macro" / "regime" / f"{lower}.json"
    if localPath.exists():
        try:
            return json.loads(localPath.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as e:
            print(f"  ⚠ {market} regime local cache load 실패: {e}", flush=True)

    try:
        from huggingface_hub import hf_hub_download

        path = hf_hub_download(
            repo_id=_REPO_ID,
            repo_type="dataset",
            filename=f"macro/regime/{lower}.json",
        )
        result = json.loads(Path(path).read_text(encoding="utf-8"))
        localPath.parent.mkdir(parents=True, exist_ok=True)
        localPath.write_text(json.dumps(result, ensure_ascii=False, indent=0), encoding="utf-8")
        return result
    except Exception as e:  # noqa: BLE001 — HF 미가용은 missing payload(crash 0)
        print(f"  ⚠ {market} HF regime JSON 미가용 ({type(e).__name__}): missing payload", flush=True)
        return {
            "market": market.upper(),
            "forecast": {
                "models": {},
                "missing": [
                    {
                        "id": "regime",
                        "status": "missing",
                        "reason": f"regime payload unavailable: {type(e).__name__}",
                    }
                ],
            },
            "rates": {"missing": [{"id": "yieldCurve", "status": "missing", "reason": "regime payload unavailable"}]},
        }


def _buildTransmission() -> dict:
    """Macro Lens용 시장·섹터 전파 payload — ``analyzeTransmission`` (fetch-independent).

    회사 객체를 읽지 않고, macro observation 이 없으면 missing lineage 로 닫힌다. prebuild
    offline 환경에서는 외부 API 호출 없이 HF/local cache 또는 missing payload 만 만든다.
    """
    try:
        from dartlab.macro.transmission import analyzeTransmission

        payload = analyzeTransmission("KR", includeCrossMarket=True)
        payload["version"] = "v1"
        return payload
    except Exception as e:  # noqa: BLE001 — transmission 미가용은 missing payload(crash 0)
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


def runMacroJson(
    *, category: str = "macroJson", mode: PipelineMode = "offline", codes=None, upload: bool = False, token=None
) -> StageResult:
    """macro.cycle/regime → ``landing/static/dashboards/macro.json`` (v20, offline).

    ``buildMacroJson.py`` 흡수 — 첫 stmt 가 ``enforceOffline()``(offline 불변). sync 가
    publish 한 cycle/regime JSON 을 download 해 SECTOR_SENSITIVITY 매핑 + transmission
    조립 → macro.json v20 write. HF push 없음(landing 정적 asset).

    Args:
        category: 카테고리 라벨.
        mode: 미사용(offline 고정).
        codes: 미사용.
        upload: 미사용(landing 정적 asset — HF push 없음).
        token: 미사용.

    Returns:
        StageResult (report.ok=macro.json 작성, report.err=실패 격리).

    Raises:
        없음 (예외는 StageResult 로 격리).

    Example:
        >>> runMacroJson()  # doctest: +SKIP
        StageResult(category='macroJson', ...)
    """
    from dartlab.core.offlineGuard import enforceOffline

    enforceOffline()

    res = StageResult(category="macroJson")
    try:
        print("[macro.json 빌드]", flush=True)
        print("  KR analyzing…", flush=True)
        kr = _analyzeMarket("KR")
        print(f"    phase: {kr.get('phase')} · {kr.get('phaseLabel')}", flush=True)
        print("  US analyzing…", flush=True)
        us = _analyzeMarket("US")
        print(f"    phase: {us.get('phase')} · {us.get('phaseLabel')}", flush=True)

        krPhase = kr.get("phase", "expansion")
        usPhase = us.get("phase", "expansion")
        krMap = SECTOR_SENSITIVITY.get(krPhase, {})
        usMap = SECTOR_SENSITIVITY.get(usPhase, {})

        sectors = set(krMap.keys()) | set(usMap.keys())
        sectorTailwind = {
            s: {
                "kr": round(krMap.get(s, 0.0), 2),
                "us": round(usMap.get(s, 0.0), 2),
                "blended": round((krMap.get(s, 0.0) * 0.6 + usMap.get(s, 0.0) * 0.4), 2),
            }
            for s in sorted(sectors)
        }
        transmission = _buildTransmission()
        krRegime = _loadRegime("KR")
        usRegime = _loadRegime("US")

        output = {
            "version": "v20",
            "asOf": date.today().isoformat(),
            "kr": kr,
            "us": us,
            "transmission": transmission,
            "sectorTailwind": sectorTailwind,
            "regime": {"kr": krRegime, "us": usRegime},
        }

        _MACRO_JSON_OUT.parent.mkdir(parents=True, exist_ok=True)
        _MACRO_JSON_OUT.write_text(json.dumps(output, ensure_ascii=False, indent=0), encoding="utf-8")
        sizeKb = _MACRO_JSON_OUT.stat().st_size / 1024
        print(f"완료: {sizeKb:.1f}KB → {_MACRO_JSON_OUT}", flush=True)
        res.report.ok = 1
    except Exception as exc:  # noqa: BLE001 — macro.json 합성 실패 격리
        res.report.err = 1
        res.report.failures.append(f"macroJson: {type(exc).__name__}: {exc}")
        print(f"[pipeline] macroJson 빌드 실패(격리): {exc}", flush=True)
    return res
