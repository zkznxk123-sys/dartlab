"""Stage C — 베이스 모델 dartlab audit 평가.

각 후보 모델(Gemma 4 / Qwen 3.5)로 financebench_kr 30질문 실행.
ops/ai.md 원칙: "벤치마크 숫자로 기본 모델을 정하지 않는다. dartlab AI audit으로 결정."

사전 준비:
    ollama pull gemma4:latest
    ollama pull qwen3.5:latest

실행:
    uv run python -X utf8 scripts/finslm/evalBaseline.py

출력:
    data/finslm/baseline_results.md
"""

from __future__ import annotations

import json
import os
import sys
import time

from dotenv import load_dotenv

load_dotenv()

# dartlab audit 질문 30개 (6막 × 5)
QUESTIONS = [
    # Act 1: 사업이해
    ("005930", "삼성전자 사업 구성과 매출 비중 알려줘"),
    ("005930", "삼성전자 성장 기여도 분해해줘"),
    ("000660", "SK하이닉스 매출 성장률과 CAGR은?"),
    ("005380", "현대차 매출 집중도(HHI) 분석"),
    ("035420", "NAVER 뭐 해서 돈 벌어?"),
    # Act 2: 수익성
    ("005930", "삼성전자 영업이익률 5년 추세"),
    ("000660", "SK하이닉스 ROE와 ROIC 추이"),
    ("005380", "현대차 DuPont 분해 결과"),
    ("005930", "삼성전자 비용구조 분해해줘"),
    ("000660", "SK하이닉스 마진은 사이클 어디에 있나?"),
    # Act 3: 현금흐름
    ("005930", "삼성전자 현금흐름 패턴은?"),
    ("005380", "현대차 이익품질 어때?"),
    ("000660", "SK하이닉스 OCF가 NI보다 큰가?"),
    ("005930", "삼성전자 FCF로 뭘 하고 있나?"),
    ("035420", "NAVER 발생액 비율 분석"),
    # Act 4: 안정성
    ("005930", "삼성전자 부채비율 안전한가?"),
    ("000660", "SK하이닉스 Z-Score 부실 위험"),
    ("005380", "현대차 이자보상배율 추이"),
    ("005930", "삼성전자 자금조달 구조"),
    ("035420", "NAVER 유동성 문제 있나?"),
    # Act 5: 자본배분
    ("005930", "삼성전자 배당정책 알려줘"),
    ("000660", "SK하이닉스 ROIC vs WACC"),
    ("005380", "현대차 자산구조 분석"),
    ("005930", "삼성전자 CAPEX 투자 추이"),
    ("035420", "NAVER 자본배분 효율성"),
    # Act 6: 전망
    ("005930", "삼성전자 적정 PER 얼마?"),
    ("000660", "SK하이닉스 DCF 가치평가"),
    ("005380", "현대차 종합 재무 등급은?"),
    ("005930", "삼성전자 왜 마진이 떨어졌나?"),
    ("000660", "SK하이닉스 이 회사 어때?"),
]


def run_question(stock_code: str, question: str, *, provider: str, model: str | None = None) -> dict:
    """단일 질문 실행 → {length, elapsed, error, has_code, has_table}."""
    import dartlab
    from dartlab.ai.runtime.core import analyze

    os.environ["DARTLAB_CONTEXT_V2"] = "1"

    try:
        c = dartlab.Company(stock_code)
    except (FileNotFoundError, OSError, RuntimeError) as e:
        return {"length": 0, "elapsed": 0, "error": str(e)[:200], "has_code": False, "has_table": False}

    full = ""
    error = None
    t0 = time.time()
    try:
        kwargs = {"provider": provider, "max_turns": 2}
        if model:
            kwargs["model"] = model
        for event in analyze(company=c, question=question, **kwargs):
            if event.kind == "chunk":
                full += event.data.get("text", "")
            elif event.kind == "error":
                error = str(event.data)[:200]
    except Exception as e:
        error = f"{type(e).__name__}: {e}"[:200]

    elapsed = time.time() - t0
    has_code = "```" in full
    has_table = "|" in full and "---" in full

    import gc
    del c
    gc.collect()

    return {
        "length": len(full),
        "elapsed": round(elapsed, 1),
        "error": error,
        "has_code": has_code,
        "has_table": has_table,
    }


def main() -> int:
    # 사용 가능한 provider/model 결정
    # ollama 모델 확인
    models_to_test: list[tuple[str, str | None]] = []

    # gemini는 항상 테스트 (무료)
    if os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY"):
        models_to_test.append(("gemini", None))

    # ollama 모델
    try:
        import subprocess
        result = subprocess.run(["ollama", "list"], capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            for line in result.stdout.split("\n"):
                if "gemma4" in line.lower():
                    models_to_test.append(("ollama", "gemma4"))
                if "qwen3" in line.lower():
                    model_name = line.split()[0] if line.split() else ""
                    if model_name:
                        models_to_test.append(("ollama", model_name))
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass

    if not models_to_test:
        print("[FAIL] 사용 가능한 모델 없음. GEMINI_API_KEY 설정 또는 ollama 모델 설치 필요.")
        return 1

    print(f"테스트 모델: {models_to_test}")
    print(f"질문: {len(QUESTIONS)}개")
    print()

    all_results: dict[str, list[dict]] = {}

    for provider, model in models_to_test:
        label = f"{provider}:{model}" if model else provider
        print(f"\n{'='*60}")
        print(f"모델: {label}")
        print(f"{'='*60}")

        results = []
        for i, (code, q) in enumerate(QUESTIONS, 1):
            print(f"  [{i}/{len(QUESTIONS)}] {q[:40]}...", end=" ", flush=True)
            r = run_question(code, q, provider=provider, model=model)
            status = "OK" if r["length"] > 100 and not r["error"] else "FAIL"
            print(f"{status} {r['length']}자 {r['elapsed']}s")
            r["question"] = q
            r["stock_code"] = code
            results.append(r)

        all_results[label] = results

    # 결과 요약
    print(f"\n{'='*60}")
    print("결과 요약")
    print(f"{'='*60}")

    out_path = "data/finslm/baseline_results.md"
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("# FinSLM 베이스라인 평가 결과\n\n")
        f.write(f"날짜: {time.strftime('%Y-%m-%d')}\n\n")

        for label, results in all_results.items():
            ok = sum(1 for r in results if r["length"] > 100 and not r["error"])
            errors = sum(1 for r in results if r["error"])
            total_len = sum(r["length"] for r in results)
            total_time = sum(r["elapsed"] for r in results)
            code_count = sum(1 for r in results if r["has_code"])
            table_count = sum(1 for r in results if r["has_table"])

            summary = (
                f"## {label}\n\n"
                f"- 성공: {ok}/{len(results)}\n"
                f"- 에러: {errors}\n"
                f"- 총 응답: {total_len:,}자\n"
                f"- 총 시간: {total_time:.0f}s\n"
                f"- 코드 포함: {code_count}/{len(results)}\n"
                f"- 테이블 포함: {table_count}/{len(results)}\n\n"
            )
            print(summary)
            f.write(summary)

            f.write("| # | 종목 | 질문 | 길이 | 시간 | 코드 | 테이블 | 상태 |\n")
            f.write("|---|------|------|------|------|------|--------|------|\n")
            for i, r in enumerate(results, 1):
                status = "OK" if r["length"] > 100 and not r["error"] else "FAIL"
                f.write(
                    f"| {i} | {r['stock_code']} | {r['question'][:25]} | "
                    f"{r['length']:,} | {r['elapsed']}s | "
                    f"{'Y' if r['has_code'] else '-'} | "
                    f"{'Y' if r['has_table'] else '-'} | {status} |\n"
                )
            f.write("\n")

    print(f"결과 저장: {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
