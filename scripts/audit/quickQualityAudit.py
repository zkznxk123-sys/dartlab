"""빠른 품질 audit — tool 다양성 + override 재호출 + pastInsight 활용 체크.

4개 시나리오를 돌려 각 질문에서 AI 가 어떤 tool 을 몇 번 호출했는지,
override 를 재호출했는지, 경험(pastInsight/sectorInsights)을 썼는지 기록.
"""

from __future__ import annotations

import json
import sys
import time
from collections import Counter
from pathlib import Path

from dartlab.ai.runtime.core import runAsk

SCENARIOS = [
    {
        "id": "Q1_valuation_samsung",
        "question": "삼성전자 가치평가 — DCF 결과를 직접 보고, WACC 가정이 비현실적이면 overrides 로 재계산해서 두 결과를 비교해라.",
        "stockCode": "005930",
        "expect": {"assumption_aware": True, "override_retry": True},
    },
    {
        "id": "Q2_credit_daewoo",
        "question": "대우건설 신용/부실 위험 진단 해줘. 레버리지 악화 시나리오로 스트레스 테스트도 해봐.",
        "stockCode": "047040",
        "expect": {"credit_used": True, "override_retry": True},
    },
    {
        "id": "Q3_growth_samyang",
        "question": "삼양식품 성장 분석 — 과거에 이 회사나 식품 업종 본 적 있나? 있으면 참고해서 얘기해줘.",
        "stockCode": "003230",
        "expect": {"experience_used": True},
    },
    {
        "id": "Q4_cycle_semiconductor",
        "question": "반도체 업황 사이클 지금 어디야? 삼성전자 매출 방향과 macro 결과 맞물려서 보여줘.",
        "stockCode": "005930",
        "expect": {"macro_used": True, "diversified": True},
    },
    {
        "id": "Q5_macro_topdown",
        "question": "최근 한국 경제 어떤가",
        "stockCode": None,
        "expect": {"macro_used": True, "gather_news": True},
    },
    {
        "id": "Q6_out_of_scope",
        "question": "오늘 서울 날씨 어때",
        "stockCode": None,
        "expect": {"tool_count": 0, "refusal": True},
    },
    {
        "id": "Q7_sector_compare",
        "question": "삼양식품 vs 농심 식품업종 비교 — 과거 분석 참고해서",
        "stockCode": "003230",
        "expect": {"experience_used": True, "compare_tool": True},
    },
]


def runOne(scenario: dict) -> dict:
    t0 = time.time()
    chunks: list[str] = []
    tool_calls: list[tuple[str, dict]] = []

    for ev in runAsk(scenario["question"], stockCode=scenario.get("stockCode")):
        if ev.kind == "chunk":
            chunks.append(ev.data["text"])
        elif ev.kind == "tool_call":
            tc = ev.data
            tool_calls.append((tc.get("name", ""), tc.get("arguments", {})))

    elapsed = time.time() - t0
    answer = "".join(chunks)

    names = [n for n, _ in tool_calls]
    counter = Counter(names)

    # override 재호출 — 같은 tool 이 두 번 이상 + 한 번은 overrides 인자
    override_retry = False
    for name in set(names):
        calls = [a for n, a in tool_calls if n == name]
        if len(calls) >= 2:
            with_ov = sum(1 for a in calls if a.get("overrides"))
            if with_ov >= 1:
                override_retry = True
                break

    experience_used = bool(counter.get("pastInsight", 0) or counter.get("sectorInsights", 0))
    macro_used = bool(counter.get("macro", 0))
    credit_used = bool(counter.get("credit", 0))
    diversified = len(set(names)) >= 4

    return {
        "id": scenario["id"],
        "question": scenario["question"],
        "elapsed_sec": round(elapsed, 1),
        "answer_chars": len(answer),
        "tool_total": len(tool_calls),
        "unique_tools": sorted(set(names)),
        "tool_counts": dict(counter),
        "override_retry": override_retry,
        "experience_used": experience_used,
        "macro_used": macro_used,
        "credit_used": credit_used,
        "diversified": diversified,
        "expect": scenario["expect"],
        "answer_head": answer[:500],
        "answer_tail": answer[-500:] if len(answer) > 500 else "",
        "tool_trace": [{"name": n, "args": {k: v for k, v in a.items() if k != "code"}} for n, a in tool_calls],
    }


def main() -> None:
    idx = int(sys.argv[1]) if len(sys.argv) > 1 else -1
    out_dir = Path("data/audit/quick")
    out_dir.mkdir(parents=True, exist_ok=True)

    results = []
    targets = SCENARIOS if idx < 0 else [SCENARIOS[idx]]
    for sc in targets:
        print(f"\n===== {sc['id']} =====", flush=True)
        r = runOne(sc)
        results.append(r)
        print(
            f"  elapsed={r['elapsed_sec']}s | tools={r['tool_total']} | "
            f"unique={len(r['unique_tools'])} | override_retry={r['override_retry']} | "
            f"experience={r['experience_used']}",
            flush=True,
        )
        print(f"  tools: {r['tool_counts']}", flush=True)

    out = out_dir / f"audit_{int(time.time())}.json"
    out.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nsaved: {out}")


if __name__ == "__main__":
    main()
