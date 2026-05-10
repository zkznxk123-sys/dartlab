"""Phase 2b alpha 별 isolated subprocess 검증 — 메모리 누적 방지.

각 alpha 별 독립 Python process 호출 → 8GB 로딩 후 process 종료 → 메모리 회수 후 다음.

실행 :
    uv run python -X utf8 scripts/validate/validatePhase2b.py [alpha_name]

알파 미지정 시 9 alpha 전체 sequential.
"""

from __future__ import annotations

import json
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

OUT_DIR = Path("c:/Users/MSI/OneDrive/Desktop/sideProject/dartlab/data/quantValidation")
OUT_DIR.mkdir(parents=True, exist_ok=True)

ALPHA_MODULES = [
    "altman",
    "piotroski",
    "beneish",
    "accruals",
    "qFactor",
    "qmj",
    "earningsSurprise",
    "bab",  # 가격 데이터 추가 로딩 — 무거움
    "fundamentalMomentum",  # 가격+펀더멘털 — 가장 무거움
]

EXTRA_MODULES = ["eventStudy", "textComposite"]


_SCRIPT_TEMPLATE = """\
import json, sys, traceback
sys.path.insert(0, 'c:/Users/MSI/OneDrive/Desktop/sideProject/dartlab/src')

ALPHA = {alpha!r}

def main():
    try:
        if ALPHA == "altman":
            from dartlab.quant.alphas.altman import calcAltmanFactor as fn
            r = fn(market="KR")
        elif ALPHA == "piotroski":
            from dartlab.quant.alphas.piotroski import calcPiotroskiFactor as fn
            r = fn(market="KR")
        elif ALPHA == "beneish":
            from dartlab.quant.alphas.beneish import calcBeneishFactor as fn
            r = fn(market="KR")
        elif ALPHA == "accruals":
            from dartlab.quant.alphas.accruals import calcAccrualsFactor as fn
            r = fn(market="KR")
        elif ALPHA == "qFactor":
            from dartlab.quant.alphas.qFactor import calcQFactor as fn
            r = fn(market="KR")
        elif ALPHA == "qmj":
            from dartlab.quant.alphas.qmj import calcQMJ as fn
            r = fn(market="KR")
        elif ALPHA == "earningsSurprise":
            from dartlab.quant.alphas.earningsSurprise import calcEarningsSurprise as fn
            r = fn(market="KR")
        elif ALPHA == "bab":
            from dartlab.quant.alphas.bab import calcBAB as fn
            r = fn(market="KR")
        elif ALPHA == "fundamentalMomentum":
            from dartlab.quant.alphas.fundamentalMomentum import calcFundamentalMomentum as fn
            r = fn(market="KR")
        elif ALPHA == "eventStudy":
            import numpy as np
            from dartlab.quant.signal.eventStudy import calcCAR
            rng = np.random.default_rng(42)
            n = 250
            s = rng.standard_normal(n) * 0.015
            m = rng.standard_normal(n) * 0.01
            s[150 + 1 : 150 + 6] += 0.01
            r = calcCAR(s, m, eventIdx=150)
        elif ALPHA == "textComposite":
            from dartlab.quant.textComposite import calcTextComposite
            r = calcTextComposite("005930", market="KR")
        else:
            print(json.dumps({{"error": "unknown alpha"}}))
            return

        if r is None:
            print(json.dumps({{"alpha": ALPHA, "result": None, "note": "None returned"}}))
            return

        # 핵심 메트릭만 추출 (full result 는 너무 큼)
        summary = {{"alpha": ALPHA, "universe": r.get("universe"), "year": r.get("year")}}
        if "scores" in r and isinstance(r["scores"], dict):
            summary["sample005930"] = r["scores"].get("005930")
            summary["scoresN"] = len(r["scores"])
        for k in ("zones", "grades", "flags", "groups", "interpretation",
                  "carPct", "isSignificant", "composite"):
            if k in r:
                v = r[k]
                if isinstance(v, str) and len(v) > 200:
                    v = v[:200]
                summary[k] = v
        print(json.dumps(summary, default=str))
    except Exception as e:
        print(json.dumps({{
            "alpha": ALPHA,
            "error": type(e).__name__,
            "message": str(e)[:200],
            "traceback": traceback.format_exc()[:500],
        }}))

main()
"""


def runOne(alpha: str) -> dict:
    """단일 alpha 를 isolated subprocess 에서 실행 → JSON dict."""
    script = _SCRIPT_TEMPLATE.format(alpha=alpha)
    t0 = time.time()
    try:
        res = subprocess.run(
            ["uv", "run", "python", "-X", "utf8", "-c", script],
            capture_output=True,
            text=True,
            timeout=300,
            encoding="utf-8",
            errors="replace",
        )
        dt = round(time.time() - t0, 2)
        # stdout 의 마지막 JSON 라인 파싱
        lines = [ln for ln in res.stdout.strip().split("\n") if ln.strip().startswith("{")]
        if not lines:
            return {
                "alpha": alpha,
                "elapsed": dt,
                "status": "fail",
                "error": "no JSON output",
                "stderr": res.stderr[-500:] if res.stderr else "",
            }
        data = json.loads(lines[-1])
        data["elapsed"] = dt
        data["status"] = "fail" if "error" in data else "pass"
        return data
    except subprocess.TimeoutExpired:
        return {"alpha": alpha, "elapsed": 300, "status": "fail", "error": "timeout"}
    except Exception as e:
        return {"alpha": alpha, "status": "fail", "error": type(e).__name__, "message": str(e)[:200]}


def main():
    args = sys.argv[1:]
    targets = args if args else (ALPHA_MODULES + EXTRA_MODULES)

    results = []
    started = datetime.now()
    ts = started.strftime("%Y%m%d_%H%M%S")
    out_path = OUT_DIR / f"phase2b_{ts}.json"

    print(f"\nPhase 2b isolated subprocess 검증 — {len(targets)} 모듈")
    print(f"incremental save: {out_path}\n")

    for alpha in targets:
        print(f"  → {alpha} ... ", end="", flush=True)
        r = runOne(alpha)
        results.append(r)
        out_path.write_text(json.dumps(results, indent=2, default=str), encoding="utf-8")
        icon = "OK" if r["status"] == "pass" else "FAIL"
        msg = r.get("error") or f"uni={r.get('universe')} sample={r.get('sample005930')}"
        print(f"{icon} {r.get('elapsed')}s — {msg}")

    n_pass = sum(1 for r in results if r["status"] == "pass")
    print(f"\n{n_pass}/{len(results)} pass")
    print(f"결과: {out_path}")
    return 0 if n_pass == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
