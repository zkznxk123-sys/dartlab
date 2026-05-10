"""Stage B-3 — graph causesNarrative/timelineNarrative 추출.

auditAnalysis에 있는 170종목에 대해 buildGraph → traversal → QA 변환.
publishBatch 없이도 실행 가능 (Company 로드만 필요).

메모리 안전: 1종목씩 순차, gc.collect().

실행:
    uv run python -X utf8 scripts/finslm/extractGraph.py

출력:
    data/finslm/raw/graph_pairs.jsonl
"""

from __future__ import annotations

import gc
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
AUDIT_DIR = ROOT / "data" / "dart" / "auditAnalysis"
OUT = ROOT / "data" / "finslm" / "raw" / "graph_pairs.jsonl"

SYSTEM_PROMPT = (
    "당신은 dartlab 한국/미국 공시 분석 전문가입니다. "
    "재무제표 데이터를 기반으로 기업을 분석합니다. "
    "숫자는 원본 그대로 인용하고, 근거 없는 주장은 하지 않습니다. "
    "인과 관계를 추적하여 '왜'에 대한 답을 데이터로 뒷받침합니다."
)

METRICS = ["영업이익률", "순이익률", "FCF", "부채비율", "ROIC", "매출액"]

QUESTIONS = {
    "영업이익률": "왜 영업이익률이 변동했나? 원인을 추적해줘.",
    "순이익률": "순이익률 변동의 근본 원인은?",
    "FCF": "FCF가 줄었다면 원인이 뭐야?",
    "부채비율": "부채비율 변동 원인을 분석해줘.",
    "ROIC": "ROIC가 WACC보다 높은/낮은 이유는?",
    "매출액": "매출 변동의 원인 구조를 분해해줘.",
}


def _sharegpt(system: str, human: str, gpt: str, meta: dict) -> dict:
    return {
        "conversations": [
            {"from": "system", "value": system},
            {"from": "human", "value": human},
            {"from": "gpt", "value": gpt},
        ],
        "metadata": meta,
    }


def main() -> int:
    codes = sorted([f.stem for f in AUDIT_DIR.glob("*.md")])
    print(f"[graph] {len(codes)}종목 × {len(METRICS)} 지표 = 최대 {len(codes) * len(METRICS)} 페어")

    pairs: list[dict] = []
    success = 0
    fail = 0

    for i, code in enumerate(codes):
        try:
            import dartlab

            c = dartlab.Company(code)
            corpName = getattr(c, "corpName", code)
        except (FileNotFoundError, OSError, RuntimeError, KeyError, ValueError):
            fail += 1
            continue

        try:
            from dartlab.core.graph import buildGraph
            from dartlab.core.graph.traverse import causesNarrative, timelineNarrative

            g = buildGraph(c)
        except (ImportError, FileNotFoundError, OSError, RuntimeError, KeyError, TypeError, ValueError):
            fail += 1
            del c
            gc.collect()
            continue

        for metric in METRICS:
            cn = causesNarrative(g, metric)
            tn = timelineNarrative(g, metric)

            # causes 가 비어있으면 skip
            if "찾을 수 없습니다" in cn and "데이터 없음" in tn:
                continue

            answer_parts = []
            if "찾을 수 없습니다" not in cn:
                answer_parts.append(cn)
            if "데이터 없음" not in tn:
                answer_parts.append(tn)

            if not answer_parts:
                continue

            q = QUESTIONS[metric].replace("해줘", f"해줘. 회사: {corpName}({code})")
            pairs.append(
                _sharegpt(
                    SYSTEM_PROMPT,
                    q,
                    "\n\n".join(answer_parts),
                    {"stock_code": code, "intent": "graph_causes", "source": "graph", "metric": metric},
                )
            )

        success += 1
        del c, g  # noqa: F821  # 두 try 모두 통과한 경로에서만 도달 — 둘 다 정의 보장
        gc.collect()

        if (i + 1) % 20 == 0:
            print(f"  [{i + 1}/{len(codes)}] pairs={len(pairs)} ok={success} fail={fail}")

    # 저장
    with open(OUT, "w", encoding="utf-8") as f:
        for p in pairs:
            f.write(json.dumps(p, ensure_ascii=False) + "\n")

    print(f"\n[graph] {len(pairs)}개 페어 (ok={success} fail={fail}) → {OUT.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
