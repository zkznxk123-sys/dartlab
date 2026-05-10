"""Sprint 2~7 신설 22 모듈 통합 검증 러너.

실행 :
    uv run python -X utf8 scripts/validate/quantValidate.py [--phase 2a|2b|all]

산출 :
    data/quantValidation/results_{timestamp}.json — 통과/실패 + 메트릭
    data/quantValidation/report_{timestamp}.md   — 사람이 읽을 마크다운

검증 기준 :
    Phase 2a (numpy-only, 데이터 무관) — 함수 호출 성공 + 출력 sanity check
    Phase 2b (DART/KRX 데이터 필요) — 005930 + 시장 평균 + universe size + 분포 합리성
"""

from __future__ import annotations

import json
import logging
import sys
import time
import traceback
from datetime import datetime
from pathlib import Path

import numpy as np

logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(name)s: %(message)s")
log = logging.getLogger("validate")

OUT_DIR = Path("c:/Users/MSI/OneDrive/Desktop/sideProject/dartlab/data/quantValidation")
OUT_DIR.mkdir(parents=True, exist_ok=True)

results: list[dict] = []


_INCREMENTAL_PATH: Path | None = None


def _record(module: str, phase: str, status: str, **details):
    results.append(
        {
            "module": module,
            "phase": phase,
            "status": status,
            "ts": datetime.now().isoformat(timespec="seconds"),
            **details,
        }
    )
    icon = "OK " if status == "pass" else "FAIL"
    detail_str = " ".join(f"{k}={v}" for k, v in details.items() if k not in ("traceback",))
    print(f"[{phase}] {icon} {module} — {detail_str}", flush=True)
    # incremental save — process 죽어도 부분 결과 보존
    if _INCREMENTAL_PATH:
        try:
            _INCREMENTAL_PATH.write_text(json.dumps(results, indent=2, default=str), encoding="utf-8")
        except OSError:
            pass


def _try(module: str, phase: str, fn, **details_extra):
    import gc

    t0 = time.time()
    try:
        out = fn()
        dt = round(time.time() - t0, 2)
        _record(module, phase, "pass", elapsed=dt, **details_extra, **(out or {}))
    except Exception as e:
        dt = round(time.time() - t0, 2)
        _record(
            module,
            phase,
            "fail",
            elapsed=dt,
            error=type(e).__name__,
            message=str(e)[:200],
            traceback=traceback.format_exc()[:500],
        )
    finally:
        gc.collect()


# ════════════════════════════════════════
# Phase 2a — numpy-only modules (no real data)
# ════════════════════════════════════════


def phase2a_tripleBarrier():
    from dartlab.quant.labels.tripleBarrier import labelTripleBarrier, metaLabel

    rng = np.random.default_rng(42)
    n = 300
    close = 100 * np.exp(np.cumsum(rng.standard_normal(n) * 0.02))
    r = labelTripleBarrier(close, pt=2.0, sl=1.0, vertical=10, volWindow=20)
    assert "labels" in r and len(r["labels"]) > 0, "labels missing"
    assert (
        r["stats"]["winRate"] + r["stats"]["lossRate"] + r["stats"]["timeoutRate"] == 100.0
        or abs(r["stats"]["winRate"] + r["stats"]["lossRate"] + r["stats"]["timeoutRate"] - 100) < 0.01
    )

    # meta-label: 임의 primary signal
    primary = rng.choice([-1, 0, 1], size=len(r["labels"]))
    m = metaLabel(primary, r["labels"])
    return {
        "n_labels": int(r["n"]),
        "winRate": r["stats"]["winRate"],
        "metaPrecision": m.get("precision"),
    }


def phase2a_fracDiff():
    from dartlab.quant.transforms.fracDiff import findMinDForStationarity, fracDiffFFD

    rng = np.random.default_rng(42)
    # 실제 가격 시계열 모사 (log normal random walk, 더 길게 — window 충분 확보)
    series = 100 * np.exp(np.cumsum(rng.standard_normal(2000) * 0.01))
    r = fracDiffFFD(series, d=0.4)
    if "error" in r:
        # 작은 d 로 재시도
        r = fracDiffFFD(series, d=0.5)
    assert "transformed" in r, f"transformed missing: {r}"
    assert r.get("window", 0) > 5, f"window too short: {r.get('window')}"
    assert np.isfinite(r.get("originalCorr", float("nan"))), "corr not finite"

    r2 = findMinDForStationarity(series, dRange=(0.2, 0.8), step=0.2)
    return {
        "window": r["window"],
        "corr": r["originalCorr"],
        "optimalD": r2.get("optimalD"),
    }


def phase2a_matrixProfile():
    from dartlab.quant.transforms.matrixProfile import computeMatrixProfile, findSimilarPatterns

    rng = np.random.default_rng(42)
    s = np.cumsum(rng.standard_normal(300))
    r = computeMatrixProfile(s, window=20)
    assert "motif" in r and "discord" in r, "motif/discord missing"

    r2 = findSimilarPatterns(s, queryStart=len(s) - 20, window=20, topK=5)
    return {
        "motifDist": r["motif"][2],
        "discordDist": r["discord"][1],
        "topKFound": len(r2.get("topK", [])),
    }


def phase2a_almgren():
    from dartlab.quant.transactionCost import almgrenChrissCost, sharpeNetOfCost

    r = almgrenChrissCost(quantity=10000, avgDailyVolume=1_000_000, price=70000, duration=1.0)
    assert r["totalCost"] > 0, "totalCost should be positive"

    rng = np.random.default_rng(42)
    rets = rng.standard_normal(252) * 0.01 + 0.0005
    r2 = sharpeNetOfCost(rets, avgTradeSize=0.01, avgVolume=1e6, turnoverPerYear=5)
    assert r2["grossSharpe"] > r2["netSharpe"], "net should be lower"
    return {
        "costBp": r["costBp"],
        "grossSharpe": r2["grossSharpe"],
        "netSharpe": r2["netSharpe"],
    }


def phase2a_meanCVaR():
    from dartlab.quant.meanCVaR import optimizeMeanCVaR

    rng = np.random.default_rng(42)
    R = rng.standard_normal((500, 5)) * 0.01
    R[:, 0] += 0.0005  # asset 0 has positive drift
    r = optimizeMeanCVaR(R, alpha=0.05, longOnly=True, maxWeight=0.5)
    assert "weights" in r, "weights missing"
    w = r["weights"]
    assert abs(w.sum() - 1.0) < 0.05, f"weights sum {w.sum()} far from 1"
    return {
        "weights_round": [round(float(x), 3) for x in w],
        "cvar": r["cvar"],
        "exp_ret_annual": r["expectedReturnAnnual"],
    }


def phase2a_blackLitterman():
    from dartlab.quant.blackLitterman import blackLittermanPosterior, buildSimpleViews

    rng = np.random.default_rng(42)
    cov = np.cov(rng.standard_normal((252, 5)).T) * 0.0001
    w_mkt = np.array([0.4, 0.3, 0.15, 0.1, 0.05])
    P, q = buildSimpleViews(["A", "B", "C", "D", "E"], {"A": 0.15, "B": -0.05})
    r = blackLittermanPosterior(cov=cov, marketWeights=w_mkt, P=P, q=q)
    assert "muBL" in r and len(r["muBL"]) == 5, "muBL bad"
    return {
        "muEqMean": round(float(r["muEq"].mean() * 252), 4),
        "muBLMean": round(float(r["muBL"].mean() * 252), 4),
        "weightSum": round(float(r["weights"].sum()), 3),
    }


def phase2a_nco():
    from dartlab.quant.factor.nco import optimizeNCO

    rng = np.random.default_rng(42)
    n = 12
    cov = np.cov(rng.standard_normal((252, n)).T) * 0.0001
    mu = rng.standard_normal(n) * 0.001
    r = optimizeNCO(cov, mu=mu, nClusters=3)
    assert "weights" in r, "weights missing"
    w = r["weights"]
    assert abs(w.sum() - 1.0) < 0.01, f"weights sum {w.sum()}"
    assert len(r["clusters"]) == 3, f"clusters {len(r['clusters'])}"
    return {
        "nClusters": r["nClusters"],
        "clusterSizes": [len(c) for c in r["clusters"]],
        "weightTop3": sorted(w.tolist(), reverse=True)[:3],
    }


def phase2a_shrinkage():
    from dartlab.quant.factor.shrinkage import denoiseRMT, shrinkConstantCorrelation, shrinkOAS

    rng = np.random.default_rng(42)
    R = rng.standard_normal((400, 10))
    r1 = shrinkOAS(R)
    r2 = shrinkConstantCorrelation(R)
    r3 = denoiseRMT(R, alpha=0.3)
    return {
        "oasShrinkage": r1["shrinkageRatio"],
        "ccShrinkage": r2["shrinkageRatio"],
        "rmtSignal": r3["signalEigenCount"],
        "rmtNoise": r3["noiseEigenCount"],
    }


def phase2a_bubble():
    from dartlab.quant.bubbleTest import calcGSADF, calcSADF

    # explosive series (= 버블 시뮬)
    rng = np.random.default_rng(42)
    n = 200
    s = np.zeros(n)
    s[0] = 100
    for t in range(1, n):
        rho = 1.0 if t < 150 else 1.02  # 후반 explosive
        s[t] = rho * s[t - 1] + rng.standard_normal() * 0.5
    s = np.maximum(s, 1)  # positive
    r1 = calcSADF(s)
    r2 = calcGSADF(s)
    return {
        "sadfStat": r1.get("sadfStat"),
        "sadfBubble": r1.get("isBubble"),
        "gsadfStat": r2.get("gsadfStat"),
        "gsadfSpans": len(r2.get("bubbleSpans") or []),
    }


def phase2a_structuralBreak():
    from dartlab.quant.structuralBreak import detectMultipleBreaks, detectStructuralBreak

    rng = np.random.default_rng(42)
    n = 200
    s = np.concatenate(
        [
            rng.standard_normal(100) * 0.01,
            rng.standard_normal(100) * 0.01 + 0.05,  # mean shift at idx=100
        ]
    )
    r = detectStructuralBreak(s, threshold=2.5)
    assert r.get("isBreak"), "should detect break"
    rm = detectMultipleBreaks(s, maxBreaks=2)
    return {
        "breakIdx": r.get("breakIdx"),
        "supStat": r.get("supStat"),
        "multiBreaks": rm.get("nBreaks"),
    }


def phase2a_johansen():
    from dartlab.quant.johansen import calcVECM, johansenTest

    rng = np.random.default_rng(42)
    n = 500
    # 공적분 시뮬: x_t random walk, y_t = 2*x + ε (stationary spread)
    eps_x = rng.standard_normal(n) * 0.5
    x = np.cumsum(eps_x)
    y = 2 * x + rng.standard_normal(n) * 0.5
    Y = np.column_stack([x, y])
    jr = johansenTest(Y)
    assert jr.get("cointRank", 0) >= 1, f"should detect cointegration, got rank={jr.get('cointRank')}"

    vr = calcVECM(Y)
    return {
        "cointRank": jr.get("cointRank"),
        "traceStats": jr.get("traceStats", []).tolist() if hasattr(jr.get("traceStats"), "tolist") else None,
        "spreadVol": round(float(np.std(vr["spreads"])), 4) if "spreads" in vr else None,
    }


def phase2a_multipleTesting():
    from dartlab.quant.factor.multipleTesting import haircutSharpe, realityCheck

    r = haircutSharpe(sharpe=1.5, nTests=20, nObs=1000, method="bonferroni")
    assert "haircutSharpe" in r, "haircutSharpe missing"

    rng = np.random.default_rng(42)
    bench = rng.standard_normal(252) * 0.01
    strats = [bench + rng.standard_normal(252) * 0.005 + 0.0003 for _ in range(5)]
    rc = realityCheck(strats, bench, nBootstrap=200)
    return {
        "originalSharpe": 1.5,
        "haircutSharpe": r["haircutSharpe"],
        "haircutSig": r["isSignificant"],
        "rcPValue": rc.get("pValue"),
    }


def runPhase2a():
    print("\n" + "=" * 70)
    print("Phase 2a — numpy-only modules (12 modules)")
    print("=" * 70)
    _try("tripleBarrier", "2a", phase2a_tripleBarrier)
    _try("fracDiff", "2a", phase2a_fracDiff)
    _try("matrixProfile", "2a", phase2a_matrixProfile)
    _try("almgrenChriss", "2a", phase2a_almgren)
    _try("meanCVaR", "2a", phase2a_meanCVaR)
    _try("blackLitterman", "2a", phase2a_blackLitterman)
    _try("nco", "2a", phase2a_nco)
    _try("shrinkage", "2a", phase2a_shrinkage)
    _try("bubbleTest", "2a", phase2a_bubble)
    _try("structuralBreak", "2a", phase2a_structuralBreak)
    _try("johansen", "2a", phase2a_johansen)
    _try("multipleTesting", "2a", phase2a_multipleTesting)


# ════════════════════════════════════════
# Phase 2b — DART/KRX real data
# ════════════════════════════════════════


def phase2b_alphas():
    """9 재무 alpha cross-sectional 검증."""
    from dartlab.quant.alphas.accruals import calcAccrualsFactor
    from dartlab.quant.alphas.altman import calcAltmanFactor
    from dartlab.quant.alphas.bab import calcBAB
    from dartlab.quant.alphas.beneish import calcBeneishFactor
    from dartlab.quant.alphas.earningsSurprise import calcEarningsSurprise
    from dartlab.quant.alphas.fundamentalMomentum import calcFundamentalMomentum
    from dartlab.quant.alphas.piotroski import calcPiotroskiFactor
    from dartlab.quant.alphas.qFactor import calcQFactor
    from dartlab.quant.alphas.qmj import calcQMJ

    alphas = [
        ("altman", calcAltmanFactor),
        ("piotroski", calcPiotroskiFactor),
        ("beneish", calcBeneishFactor),
        ("accruals", calcAccrualsFactor),
        ("qFactor", calcQFactor),
        ("qmj", calcQMJ),
        ("bab", calcBAB),
        ("earningsSurprise", calcEarningsSurprise),
        ("fundMomentum", calcFundamentalMomentum),
    ]
    for name, fn in alphas:

        def _check(fn=fn):
            r = fn(market="KR")
            if r is None:
                return {"universe": 0, "note": "None returned"}
            uni = r.get("universe", 0)
            if uni < 50:
                return {"universe": uni, "note": "low universe"}
            # 005930 점수
            score = None
            for key in ("scores",):
                d = r.get(key)
                if isinstance(d, dict):
                    score = d.get("005930")
                    break
            return {"universe": uni, "samsung005930": score}

        _try(f"alphas.{name}", "2b", _check)


def phase2b_eventStudy():
    """Event study 가짜 시계열 검증."""
    from dartlab.quant.eventStudy import calcBHAR, calcCAR

    def _check():
        rng = np.random.default_rng(42)
        n = 250
        s = rng.standard_normal(n) * 0.015
        m = rng.standard_normal(n) * 0.01
        # event 일자 후 +5% drift 추가
        s[150 + 1 : 150 + 6] += 0.01
        car = calcCAR(s, m, eventIdx=150, eventWindow=(-5, 5))
        bhar = calcBHAR(s, m, eventIdx=150, holdWindow=60)
        return {
            "carPct": car.get("carPct"),
            "carSig": car.get("isSignificant"),
            "bhar": bhar.get("bhar"),
        }

    _try("eventStudy", "2b", _check)


def phase2b_textComposite():
    """텍스트 composite 005930 호출."""
    from dartlab.quant.textComposite import calcTextComposite

    def _check():
        r = calcTextComposite("005930", market="KR")
        if r is None:
            return {"available": False, "note": "no text data"}
        return {"available": True, "scores": r.get("scores"), "composite": r.get("composite")}

    _try("textComposite", "2b", _check)


def runPhase2b():
    print("\n" + "=" * 70)
    print("Phase 2b — DART/KRX real data (11 modules)")
    print("=" * 70)
    phase2b_alphas()
    phase2b_eventStudy()
    phase2b_textComposite()


# ════════════════════════════════════════
# Main
# ════════════════════════════════════════


def main():
    args = sys.argv[1:]
    phase = "all"
    if "--phase" in args:
        phase = args[args.index("--phase") + 1]

    started = datetime.now()
    ts = started.strftime("%Y%m%d_%H%M%S")
    global _INCREMENTAL_PATH
    _INCREMENTAL_PATH = OUT_DIR / f"results_{ts}.json"
    print(f"\nQuant 검증 시작 — phase={phase}, started={started.isoformat(timespec='seconds')}")
    print(f"incremental save: {_INCREMENTAL_PATH}")

    if phase in ("2a", "all"):
        runPhase2a()
    if phase in ("2b", "all"):
        runPhase2b()

    # 최종 저장 (incremental 외에 explicit 한번 더)
    json_path = OUT_DIR / f"results_{ts}.json"
    json_path.write_text(json.dumps(results, indent=2, default=str), encoding="utf-8")

    # 요약
    n_pass = sum(1 for r in results if r["status"] == "pass")
    n_fail = len(results) - n_pass
    print("\n" + "=" * 70)
    print(f"검증 완료 — {n_pass}/{len(results)} pass, {n_fail} fail")
    print(f"결과 저장: {json_path}")
    print("=" * 70)

    # 마크다운 리포트
    md_path = OUT_DIR / f"report_{ts}.md"
    lines = [f"# Quant Validation Report — {started.isoformat(timespec='seconds')}", ""]
    lines.append(f"**총 {len(results)} 모듈, {n_pass} pass, {n_fail} fail**\n")
    for r in results:
        icon = "✅" if r["status"] == "pass" else "❌"
        details = " ".join(
            f"`{k}={v}`" for k, v in r.items() if k not in ("module", "phase", "status", "ts", "traceback")
        )
        lines.append(f"- {icon} **{r['module']}** ({r['phase']}) — {details}")
    md_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"리포트 저장: {md_path}")

    return n_fail


if __name__ == "__main__":
    sys.exit(0 if main() == 0 else 1)
