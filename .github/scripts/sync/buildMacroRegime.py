"""macro forecast 4모델 + 수익률곡선 + GaR 분포 + Hamilton regime band
→ HF macro/regime/{kr,us}.json (sync 단계).

``analyzeForecast`` (Cleveland Fed probit · Sahm rule · Conference Board LEI ·
Hamilton 수축확률) + ``analyzeRates`` (Nelson-Siegel 수익률곡선) + ``growthAtRisk``
(FCI 조건부 GDP 성장률 분위) 는 FRED/ECOS fetch 의존이라 **sync 단계** 책임이다.
Hamilton regime band(smoothedProbs)는 ``analyzeForecast`` 결과에 없으므로
(contractionProb 스칼라만 노출·smoothedProbs 배열 드롭) ``cycles.regimeSwitching.
hamiltonRegime`` 을 직접 호출해 ``HamiltonResult.smoothedProbs`` 에서 추출한다.

prebuild ``buildMacroJson.py`` 가 본 JSON 을 다운로드해 ``regime`` 키로 조립(offline,
외부 API 0). ``buildMacroCycle.py`` 와 동형 — 같은 cron(macroData.yml)·같은 머신.

산출은 회고/확률/분포를 *단일 점수로 붕괴시키지 않고* 정직하게 분리한다 —
합산 필드·composite 없음(verdict 부활 구조적 차단). 각 모델은 자기 호라이즌·시간성·
freshness·신뢰성 게이트를 독립 표기한다.

런타임 예산(fetch vs CPU 분리):
  - fetch: analyzeForecast(~12 LEI 시리즈 + UNRATE + GDP) + analyzeRates(DGS 8만기)
    + GaR(GDP + NFCI) ≈ buildMacroCycle 대비 ~30 FRED fetch 증분. HF bulk parquet
    cache(data/macro) hit 시 online fetch 최소.
  - CPU: Hamilton EM(maxIter=50·2-regime AR(1)) + GaR IRLS 분위회귀 = 순수 numpy.
    분기 시계열(수십~수백 관측)이라 초 단위. macroData.yml timeout-minutes:120 충분.
시리즈/축 단위 try/except — 실패는 missing payload(전체 중단 0).

asOf 는 각 시리즈 최종 관측일(`_lastObsDate`)로 모델별 분리 표기한다 — 단일 asOf
뭉치기 금지(probit 일간·LEI/Sahm 월간·Hamilton/GaR 분기 vintage 상이).

실행::

    uv run python -X utf8 .github/scripts/sync/buildMacroRegime.py
    uv run python -X utf8 .github/scripts/sync/buildMacroRegime.py --push

환경변수:
    HF_TOKEN: --push 시 필수.
    FRED_API_KEY / ECOS_API_KEY: 시리즈 fetch (HF bulk cache 우선).
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# 모델별 vintage(staleAfterDays) — 시리즈 cadence 반영(단일 asOf 뭉치기 금지·§7).
_STALE_PROBIT = 7  # T10Y3M 일간
_STALE_SAHM = 45  # UNRATE 월간
_STALE_LEI = 75  # CB-LEI 월간
_STALE_QUARTER = 120  # Hamilton/GaR/regimeBand 분기 GDP(revision 잦음)

# Nelson-Siegel interpretation enum → 한국어 라벨(prose 파싱 0·SSOT 매핑).
_CURVE_LABEL = {"steep_normal": "가파른정상", "normal": "정상", "flat": "평탄", "inverted": "역전"}

# Hamilton regime 분리도 임계 — Cohen's d 중간효과(두 regime 평균차 ≥ 큰쪽 σ의 절반).
_SEPARATION_MIN = 0.5
# LEI 사용가능 구성요소 개수 게이트(전체 10 중 ~6 이상).
_LEI_COMPONENT_RATIO_MIN = 0.6


def _miss(axis: str, e: Exception) -> dict:
    return {"id": axis, "status": "error", "reason": f"{type(e).__name__}: {e}"}


def _lastObsDate(g, seriesId: str) -> str | None:
    """시리즈 최종 관측일(YYYY-MM-DD). gather macro df 의 date 컬럼 max."""
    try:
        df = g.macro(seriesId)
        if df is None or len(df) == 0:
            return None
        dates = df.get_column("date").to_list()
        return str(max(dates))[:10] if dates else None
    except Exception:
        return None


def _round5pct(p: float | None) -> float | None:
    """확률 5%p 반올림(probit 점추정 가짜 정밀 가드)."""
    if p is None:
        return None
    return round(round(p * 20) / 20, 2)


def _separation(params: dict) -> float | None:
    """Hamilton regime 분리도 = (mu_exp − mu_con) / max(σ). mu-swap 으로 mu_exp ≥ mu_con."""
    try:
        muExp = params.get("mu_expansion")
        muCon = params.get("mu_contraction")
        sigMax = max(params.get("sigma_expansion", 0.0), params.get("sigma_contraction", 0.0))
        if muExp is None or muCon is None or sigMax <= 0:
            return None
        return round((muExp - muCon) / sigMax, 3)
    except (TypeError, ValueError):
        return None


def _extractForecast(forecast: dict, market: str, g) -> dict:
    """forecast 4모델 추출 + §3.4 신뢰성 게이트. 합산 필드 없음(verdict 차단)."""
    models: dict = {}
    missing: list = []
    isUs = market.upper() == "US"
    runDate = datetime.now(timezone.utc).date().isoformat()

    # probit (US 전용) — 항상 산출(스칼라 입력), zone 주역·확률 5%p 보조.
    if isUs:
        rp = forecast.get("recessionProb")
        if rp:
            models["probit"] = {
                "probability": rp.get("probability"),
                "probabilityRounded": _round5pct(rp.get("probability")),
                "zone": rp.get("zone"),
                "zoneLabel": rp.get("zoneLabel"),
                "spread": rp.get("spread"),
                "horizon": "12M",
                "timeKind": "leading",
                "precisionNote": "Estrella-Mishkin 고정계수·표준오차 미산출(점추정)",
                "asOf": _lastObsDate(g, "T10Y3M") or runDate,
                "seriesId": "T10Y3M",
                "staleAfterDays": _STALE_PROBIT,
            }
        else:
            models["probit"] = {"status": "데이터부족·표시 보류"}
    else:
        missing.append({"id": "probit", "status": "notApplicable", "reason": "US 전용"})

    # Sahm (US 전용) — result None(데이터부족) vs 정상계산 둘뿐(dead path 이중게이트 금지).
    if isUs:
        sr = forecast.get("sahmRule")
        if sr is None:
            models["sahm"] = {"status": "데이터부족·표시 보류"}
        else:
            models["sahm"] = {
                "value": sr.get("value"),
                "triggered": sr.get("triggered"),
                "zone": sr.get("zone"),
                "zoneLabel": sr.get("zoneLabel"),
                "horizon": "realtime",
                "timeKind": "trigger(동행)",
                "asOf": _lastObsDate(g, "UNRATE") or runDate,
                "seriesId": "UNRATE",
                "staleAfterDays": _STALE_SAHM,
            }
    else:
        missing.append({"id": "sahm", "status": "notApplicable", "reason": "US 전용"})

    # LEI — US=CB-LEI(개수 게이트), KR=CLI composite(shape 다름).
    lei = forecast.get("lei")
    if isUs:
        if lei:
            avail = lei.get("availableComponents") or 0
            total = lei.get("totalComponents") or 0
            ratio = (avail / total) if total else 0.0
            if ratio >= _LEI_COMPONENT_RATIO_MIN and lei.get("signalLabel") != "데이터부족":
                models["lei"] = {
                    "level": lei.get("level"),
                    "mom6m": lei.get("mom6m"),
                    "signal": lei.get("signal"),
                    "signalLabel": lei.get("signalLabel"),
                    "availableComponents": avail,
                    "totalComponents": total,
                    "overlapNote": "term-spread·initial-claims 내포(probit/Sahm 부분 상관)",
                    "horizon": "6-9M",
                    "timeKind": "leading",
                    "asOf": _lastObsDate(g, "PERMIT") or runDate,
                    "staleAfterDays": _STALE_LEI,
                }
            else:
                models["lei"] = {
                    "status": "구성요소 부족·표시 보류",
                    "availableComponents": avail,
                    "totalComponents": total,
                }
        else:
            models["lei"] = {"status": "구성요소 부족·표시 보류", "availableComponents": 0, "totalComponents": 10}
    else:
        if lei:
            models["lei"] = {
                "cliMomentum": lei.get("cliMomentum"),
                "cliLevel": lei.get("cliLevel"),
                "growthApprox": lei.get("growthApprox"),
                "growthLabel": lei.get("growthLabel"),
                "asOf": _lastObsDate(g, "CLI") or runDate,
                "staleAfterDays": _STALE_LEI,
            }
        else:
            missing.append({"id": "lei", "status": "데이터부족·표시 보류", "reason": "CLI composite 미산출"})

    # Hamilton — US: converged + 분리도 게이트. KR: 단위 parity 미확정·표면화 보류.
    if isUs:
        hr = forecast.get("hamiltonRegime")
        if hr:
            sep = _separation(hr.get("params", {}))
            base = {
                "timeKind": "retrospective",
                "horizon": "동행",
                "staleAfterDays": _STALE_QUARTER,
                "revisionLabel": "분기 GDP·수정 대상",
                "asOf": _lastObsDate(g, "A191RL1Q225SBEA") or runDate,
                "seriesId": "A191RL1Q225SBEA",
                "seriesSource": "FRED",
                "separation": sep,
            }
            if not hr.get("converged"):
                models["hamilton"] = {**base, "contractionProb": None, "converged": False, "status": "EM 미수렴"}
            elif sep is None or sep < _SEPARATION_MIN:
                models["hamilton"] = {**base, "contractionProb": None, "converged": True, "status": "레짐 분리 약함"}
            else:
                models["hamilton"] = {
                    **base,
                    "contractionProb": hr.get("contractionProb"),
                    "converged": True,
                    "iterations": hr.get("iterations"),
                }
        else:
            models["hamilton"] = {"status": "표본 부족·표시 보류"}
    else:
        missing.append(
            {
                "id": "hamilton",
                "status": "단위 parity 미확정·표시 보류",
                "reason": "GROWTH↔A191RL1Q225SBEA 단위 동일성 미확정",
            }
        )

    return {"models": models, "missing": missing}


def _extractRates(r: dict, forecast: dict | None, market: str, g) -> dict:
    """수익률곡선 1줄 — spread=probit.spread 재사용(yieldCurve에 spread 필드 없음),
    curveShape=interpretation enum 한국어 매핑(beta1 부호 직역 금지)."""
    if market.upper() != "US":
        return {"missing": [{"id": "yieldCurve", "status": "notApplicable", "reason": "US 전용"}]}
    yc = r.get("yieldCurve")
    rp = forecast.get("recessionProb") if forecast else None
    spread = rp.get("spread") if rp else None
    if yc is None or spread is None:
        return {"missing": [{"id": "yieldCurve", "status": "missing", "reason": "yieldCurve 또는 spread 부재"}]}
    shape = yc.get("interpretation")
    return {
        "spread10y3m": round(spread, 2),
        "sign": "+" if spread > 0 else "-" if spread < 0 else "",
        "curveShape": shape,
        "curveShapeLabel": _CURVE_LABEL.get(shape, shape),
        "curveSource": "NelsonSiegel.interpretation",
        "asOf": _lastObsDate(g, "T10Y3M") or datetime.now(timezone.utc).date().isoformat(),
        "seriesId": "T10Y3M",
        "staleAfterDays": _STALE_PROBIT,
        "missing": [],
    }


def _extractGaR(g, market: str) -> dict:
    """GaR 4Q 전향 조건부 분포 — growthAtRisk(FCI, GDP YoY%, horizon=4) 직접 호출
    (summary._addGrowthAtRisk 패턴). FCI=NFCI(National Financial Conditions Index)."""
    from dartlab.macro.crisis.growthAtRisk import growthAtRisk
    from dartlab.macro.seriesFetch import fetchSeriesList

    gdpSeries = fetchSeriesList(g, "GDP")
    if not (gdpSeries and len(gdpSeries) >= 20):
        return {"status": "표본 부족·표시 보류"}
    gdpGrowth = [
        ((gdpSeries[i] / gdpSeries[i - 4]) - 1) * 100
        for i in range(4, len(gdpSeries))
        if gdpSeries[i - 4] and gdpSeries[i - 4] > 0
    ]
    fci = fetchSeriesList(g, "NFCI")
    if not (fci and len(fci) >= 20) or not gdpGrowth:
        return {"status": "표본 부족·표시 보류"}
    gar = growthAtRisk(fci, gdpGrowth, horizon=4)
    if not gar:
        return {"status": "표본 부족·표시 보류"}
    return {
        "gar5": gar["currentGaR5"],
        "gar25": gar["currentGaR25"],
        "median": gar["median"],
        "gar75": gar["currentGaR75"],
        "gar95": gar["currentGaR95"],
        "skewness": gar["skewness"],
        "tailRisk": gar["tailRisk"],
        "tailRiskLabel": gar["tailRiskLabel"],
        "currentFCI": gar["currentFCI"],
        "observations": gar["observations"],
        "horizon": 4,
        "timeKind": "forward",
        "seriesNote": "FCI(NFCI 대용) 조건부 GDP 성장률 분위(점추정 아닌 조건부 분포)",
        "asOf": _lastObsDate(g, "GDP") or datetime.now(timezone.utc).date().isoformat(),
        "staleAfterDays": _STALE_QUARTER,
        "revisionLabel": "분기 GDP·수정 대상",
    }


def _extractRegimeBand(g, market: str) -> dict:
    """Hamilton regime band — analyzeForecast가 contractionProb 스칼라만 노출하고
    smoothedProbs 배열을 드롭하므로, cycles.regimeSwitching.hamiltonRegime 을 직접
    호출해 최근 ~24분기 수축확률 열(smoothedProbs[-24:, 1])을 추출한다."""
    from dartlab.macro.cycles.regimeSwitching import hamiltonRegime
    from dartlab.macro.seriesFetch import fetchSeriesList

    gdpVals = fetchSeriesList(g, "A191RL1Q225SBEA")
    if not (gdpVals and len(gdpVals) >= 20):
        return {"status": "표본 부족·표시 보류"}
    hr = hamiltonRegime(gdpVals, maxIter=50)
    sep = _separation(hr.params)
    asOf = _lastObsDate(g, "A191RL1Q225SBEA") or datetime.now(timezone.utc).date().isoformat()
    if not hr.converged:
        return {"status": "EM 미수렴", "converged": False, "separation": sep}
    if sep is None or sep < _SEPARATION_MIN:
        return {"status": "레짐 분리 약함", "converged": True, "separation": sep}
    band = [round(float(x), 4) for x in hr.smoothedProbs[-24:, 1]]
    return {
        "band": band,
        "converged": True,
        "separation": sep,
        "timeKind": "retrospective",
        "horizon": "동행",
        "asOf": asOf,
        "staleAfterDays": _STALE_QUARTER,
    }


def _analyzeRegime(market: str) -> dict:
    """단일 시장 regime payload — forecast 4모델 + rates 곡선 + GaR + regime band.
    축별 try/except(전체 중단 0·실패는 missing payload)."""
    from dartlab.macro.forecast.forecast import analyzeForecast
    from dartlab.macro.rates.rates import analyzeRates
    from dartlab.macro.seriesFetch import getGather

    g = getGather(None)
    out: dict = {"market": market.upper(), "computedAt": datetime.now(timezone.utc).isoformat()}

    forecast = None
    try:
        forecast = analyzeForecast(market=market)
        out["forecast"] = _extractForecast(forecast, market, g)
    except Exception as e:
        out["forecast"] = {"models": {}, "missing": [_miss("forecast", e)]}

    try:
        r = analyzeRates(market=market)
        out["rates"] = _extractRates(r, forecast, market, g)
    except Exception as e:
        out["rates"] = {"missing": [_miss("rates", e)]}

    if market.upper() == "US":
        try:
            out["gar"] = _extractGaR(g, market)
        except Exception as e:
            out["gar"] = {"status": "표본 부족·표시 보류", "missing": [_miss("gar", e)]}
        try:
            out["regimeBand"] = _extractRegimeBand(g, market)
        except Exception as e:
            out["regimeBand"] = {"missing": [_miss("regimeBand", e)]}

    return out


def buildRegime(outDir: Path) -> dict[str, Path]:
    """KR + US regime payload JSON 빌드."""
    outDir.mkdir(parents=True, exist_ok=True)
    written: dict[str, Path] = {}

    for market in ("KR", "US"):
        t0 = time.time()
        print(f"[macroRegime] {market} analyzing …", flush=True)
        try:
            result = _analyzeRegime(market)
        except Exception as e:
            print(f"[macroRegime] {market} 실패: {type(e).__name__}: {e}", flush=True)
            continue
        path = outDir / f"{market.lower()}.json"
        path.write_text(json.dumps(result, ensure_ascii=False, indent=0), encoding="utf-8")
        kb = path.stat().st_size / 1024
        nModels = len(result.get("forecast", {}).get("models", {}))
        print(
            f"[macroRegime] {market}: models={nModels} → {path} ({kb:.1f}KB, {time.time() - t0:.0f}s)",
            flush=True,
        )
        written[market.lower()] = path

    return written


def deploy(written: dict[str, Path], *, repoId: str) -> None:
    """HF dataset macro/regime/ 에 publish."""
    import os

    from huggingface_hub import HfApi

    token = os.environ.get("HF_TOKEN", "")
    if not token:
        print("[macroRegime] HF_TOKEN 없음 — publish 스킵")
        return

    api = HfApi(token=token)
    for market, path in written.items():
        commit = api.upload_file(
            path_or_fileobj=str(path),
            path_in_repo=f"macro/regime/{market}.json",
            repo_id=repoId,
            repo_type="dataset",
            commit_message=f"build: macro regime {market}.json",
        )
        print(f"[hf] macro/regime/{market}.json: {getattr(commit, 'commit_url', None)}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", default="data/macro/regime", help="출력 디렉토리 (기본 data/macro/regime)")
    parser.add_argument("--repo-id", default="eddmpython/dartlab-data")
    parser.add_argument("--push", action="store_true", help="HF dataset publish 활성화")
    args = parser.parse_args()

    written = buildRegime(Path(args.out))
    if not written:
        print("[macroRegime] 결과 0 건 — exit 1")
        return 1
    if args.push:
        deploy(written, repoId=args.repo_id)
    return 0


if __name__ == "__main__":
    sys.exit(main())
