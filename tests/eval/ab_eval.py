"""Step C — A/B 평가: legacy(v1) vs context v2.

삼성전자 1종목 × 10질문으로 축소 실행 (메모리 안전).
각 질문을 v1/v2 순서로 호출 → 응답 길이 + 에러율 비교.

실행:
    uv run python -X utf8 tests/eval/ab_eval.py

결과:
    tests/eval/ab_results.md 에 마크다운 테이블 저장
"""

from __future__ import annotations

import gc
import os
import sys
import time

from dotenv import load_dotenv

load_dotenv()

# provider 감지
provider = None
if os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY"):
    provider = "gemini"
elif os.getenv("GROQ_API_KEY"):
    provider = "groq"
elif os.getenv("CEREBRAS_API_KEY"):
    provider = "cerebras"
else:
    print("[FAIL] API key 없음")
    sys.exit(1)

QUESTIONS = [
    ("삼성전자 사업 구성 알려줘", "act1"),
    ("영업이익률 추세", "act2"),
    ("비용구조 분해", "act2"),
    ("현금흐름 패턴은?", "act3"),
    ("이익품질 어때", "act3"),
    ("부채비율 안전한가", "act4"),
    ("배당정책", "act5"),
    ("ROIC 추이", "act5"),
    ("적정 PER", "act6"),
    ("이 회사 어때", "all"),
]


def run_one(company, question: str, *, use_v2: bool) -> dict:
    """단일 질문 실행 → {length, elapsed, error}."""
    os.environ["DARTLAB_CONTEXT_V2"] = "1" if use_v2 else "0"

    from dartlab.ai.runtime.core import runAsk

    full = ""
    error = None
    t0 = time.time()
    try:
        for event in runAsk(company=company, question=question, provider=provider, max_turns=2):
            if event.kind == "chunk":
                full += event.data.get("text", "")
            elif event.kind == "error":
                error = str(event.data)[:200]
    except Exception as e:
        error = f"{type(e).__name__}: {e}"[:200]
    elapsed = time.time() - t0
    return {"length": len(full), "elapsed": round(elapsed, 1), "error": error}


def main() -> int:
    print(f"[INFO] Provider: {provider}")
    print(f"[INFO] Questions: {len(QUESTIONS)}")
    print()

    from dartlab import Company

    print("Loading Company('005930')...")
    c = Company("005930")
    print("Loaded.")
    print()

    results: list[dict] = []

    for i, (q, cat) in enumerate(QUESTIONS, 1):
        print(f"[{i}/{len(QUESTIONS)}] {q}")

        # v1 (legacy)
        r1 = run_one(c, q, use_v2=False)
        print(f"  v1: {r1['length']:5d}자 {r1['elapsed']:5.1f}s {'ERROR:' + r1['error'][:50] if r1['error'] else 'OK'}")

        # v2 (context engineering)
        r2 = run_one(c, q, use_v2=True)
        print(f"  v2: {r2['length']:5d}자 {r2['elapsed']:5.1f}s {'ERROR:' + r2['error'][:50] if r2['error'] else 'OK'}")

        results.append(
            {
                "question": q,
                "category": cat,
                "v1_len": r1["length"],
                "v1_time": r1["elapsed"],
                "v1_error": r1["error"],
                "v2_len": r2["length"],
                "v2_time": r2["elapsed"],
                "v2_error": r2["error"],
            }
        )

    # 집계
    v1_total = sum(r["v1_len"] for r in results)
    v2_total = sum(r["v2_len"] for r in results)
    v1_errors = sum(1 for r in results if r["v1_error"])
    v2_errors = sum(1 for r in results if r["v2_error"])
    v1_time = sum(r["v1_time"] for r in results)
    v2_time = sum(r["v2_time"] for r in results)
    v1_ok = sum(1 for r in results if r["v1_len"] > 100 and not r["v1_error"])
    v2_ok = sum(1 for r in results if r["v2_len"] > 100 and not r["v2_error"])

    print()
    print("=" * 60)
    print("A/B 평가 결과 요약")
    print("=" * 60)
    print(f"{'':20s} {'v1 (legacy)':>15s} {'v2 (context)':>15s}")
    print(f"{'성공 (100자+)':20s} {v1_ok:>15d} {v2_ok:>15d}")
    print(f"{'에러':20s} {v1_errors:>15d} {v2_errors:>15d}")
    print(f"{'총 응답 길이':20s} {v1_total:>15,d} {v2_total:>15,d}")
    print(f"{'총 시간':20s} {v1_time:>14.1f}s {v2_time:>14.1f}s")
    print()

    # 마크다운 결과 파일
    out_path = "tests/eval/ab_results.md"
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("# A/B 평가 결과\n\n")
        f.write(f"- 날짜: {time.strftime('%Y-%m-%d')}\n")
        f.write(f"- Provider: {provider}\n")
        f.write("- 종목: 005930 삼성전자\n\n")
        f.write("| # | 질문 | Cat | v1 길이 | v1 시간 | v2 길이 | v2 시간 | v2-v1 |\n")
        f.write("|---|------|-----|---------|---------|---------|---------|-------|\n")
        for i, r in enumerate(results, 1):
            diff = r["v2_len"] - r["v1_len"]
            sign = "+" if diff > 0 else ""
            f.write(
                f"| {i} | {r['question'][:20]} | {r['category']} | "
                f"{r['v1_len']:,} | {r['v1_time']}s | "
                f"{r['v2_len']:,} | {r['v2_time']}s | {sign}{diff:,} |\n"
            )
        f.write(f"\n**합계**: v1={v1_total:,}자 / v2={v2_total:,}자 / diff={v2_total - v1_total:+,}\n")
        f.write(f"\n**성공률**: v1={v1_ok}/{len(QUESTIONS)} / v2={v2_ok}/{len(QUESTIONS)}\n")

    print(f"결과 저장: {out_path}")

    # GC
    del c
    gc.collect()

    return 0 if v2_errors <= v1_errors else 1


if __name__ == "__main__":
    sys.exit(main())
