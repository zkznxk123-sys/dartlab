"""검증 결과 종합 — 가장 최근 results_*.json → 진단 리포트 (마크다운).

Phase 3 (진단) 자동화. 실행 :
    uv run python -X utf8 scripts/validate/summarizeValidation.py
"""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

OUT_DIR = Path("c:/Users/MSI/OneDrive/Desktop/sideProject/dartlab/data/quantValidation")


def main():
    files = sorted(OUT_DIR.glob("results_*.json"))
    if not files:
        print("검증 결과 없음 — quantValidate.py 먼저 실행")
        return
    latest = files[-1]
    print(f"latest: {latest.name}")

    data = json.loads(latest.read_text(encoding="utf-8"))
    n_pass = sum(1 for r in data if r["status"] == "pass")
    n_fail = len(data) - n_pass

    by_phase = defaultdict(lambda: [0, 0])
    for r in data:
        by_phase[r["phase"]][0 if r["status"] == "pass" else 1] += 1

    fails = [r for r in data if r["status"] == "fail"]
    perfs = sorted(
        [(r["module"], r.get("elapsed", 0)) for r in data if r["status"] == "pass"],
        key=lambda x: -x[1],
    )

    lines = [
        f"# Quant 검증 종합 — {latest.stem}",
        "",
        f"**총 {len(data)} 모듈 — pass {n_pass}, fail {n_fail}, 통과률 {round(100 * n_pass / len(data), 1)}%**",
        "",
        "## Phase 별",
        "",
    ]
    for phase, (p, f) in sorted(by_phase.items()):
        lines.append(f"- **{phase}**: pass {p} / fail {f}")

    if fails:
        lines += ["", "## ❌ 실패 모듈"]
        for r in fails:
            lines.append(f"- **{r['module']}** ({r['phase']}) — `{r.get('error', '?')}`: {r.get('message', '')}")
            tb = r.get("traceback", "")
            if tb:
                lines.append(f"  ```\n  {tb[:300]}\n  ```")

    lines += ["", "## 성능 — 가장 느린 5", ""]
    for m, e in perfs[:5]:
        lines.append(f"- {m}: {e}s")

    lines += ["", "## ✅ 통과 모듈 — 핵심 메트릭", ""]
    for r in data:
        if r["status"] != "pass":
            continue
        details = {k: v for k, v in r.items() if k not in ("module", "phase", "status", "ts", "elapsed", "traceback")}
        if details:
            kv = ", ".join(f"`{k}={v}`" for k, v in list(details.items())[:5])
            lines.append(f"- **{r['module']}** — {kv}")

    out_path = OUT_DIR / f"{latest.stem.replace('results_', 'summary_')}.md"
    out_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"종합 리포트: {out_path}")


if __name__ == "__main__":
    main()
