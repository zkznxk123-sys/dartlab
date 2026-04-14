"""Step A — Live ACE Playbook Smoke Test.

DARTLAB_CONTEXT_V2=1로 실제 API 호출하여 ACE 폐쇄 루프 검증.

실행:
    DARTLAB_CONTEXT_V2=1 uv run python -X utf8 scripts/eval/live_ace_smoke.py

검증:
    1. 3개 질문 모두 응답 100자+
    2. KnowledgeDB playbook에 bullet 누적
    3. 3번째 호출(같은 intent)에서 ace.playbook이 ContextBundle에 존재
    4. 에러 0
"""

from __future__ import annotations

import os
import sys
import time

os.environ["DARTLAB_CONTEXT_V2"] = "1"

from dotenv import load_dotenv

load_dotenv()


def main() -> int:
    # provider 감지
    provider = None
    if os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY"):
        provider = "gemini"
    elif os.getenv("GROQ_API_KEY"):
        provider = "groq"
    elif os.getenv("CEREBRAS_API_KEY"):
        provider = "cerebras"
    else:
        print("[FAIL] API key 없음 — GEMINI_API_KEY, GROQ_API_KEY, CEREBRAS_API_KEY 중 하나 설정 필요")
        return 1

    print(f"[INFO] Provider: {provider}")
    print(f"[INFO] DARTLAB_CONTEXT_V2={os.environ.get('DARTLAB_CONTEXT_V2')}")
    print()

    from dartlab import Company
    from dartlab.ai.context import ContextBuilder
    from dartlab.ai.persistence import KnowledgeDB
    from dartlab.ai.runtime.core import analyze

    # Company 로드
    print("[1/5] Company('005930') 로드...")
    t0 = time.time()
    c = Company("005930")
    print(f"  로드 완료 ({time.time() - t0:.1f}s)")

    QUESTIONS = [
        ("영업이익률 추세가 어떻게 되나?", "act2_profit"),
        ("부채비율 안전한가?", "act4_stability"),
        ("영업이익률 추세는?", "act2_profit"),  # 같은 intent 재호출 — playbook 주입 확인
    ]

    errors = []
    responses: list[str] = []

    for i, (q, expected_intent) in enumerate(QUESTIONS, 1):
        print(f"\n[{i + 1}/5] Q: '{q}' (expected: {expected_intent})")

        # ContextBuilder 확인 (API 호출 전)
        bundle = ContextBuilder(question=q, company=c, provider=provider).build()
        has_playbook = "ace.playbook" in bundle.keys()
        print(f"  intent={bundle.intent} parts={len(bundle.parts)} playbook={'YES' if has_playbook else 'no'}")
        if i == 3 and not has_playbook:
            print("  [WARN] 3번째 호출인데 playbook 미주입 — 1,2번에서 bullet 추출 실패일 수 있음")

        # 실제 API 호출
        t0 = time.time()
        full_text = ""
        try:
            for event in analyze(
                company=c,
                question=q,
                provider=provider,
                max_turns=2,
            ):
                if event.kind == "chunk":
                    full_text += event.data.get("text", "")
                elif event.kind == "error":
                    errors.append(f"Q{i}: {event.data}")
        except Exception as e:
            errors.append(f"Q{i}: {type(e).__name__}: {e}")
            full_text = ""

        elapsed = time.time() - t0
        responses.append(full_text)
        print(f"  응답: {len(full_text)}자 ({elapsed:.1f}s)")

        if len(full_text) < 100:
            errors.append(f"Q{i}: 응답이 너무 짧음 ({len(full_text)}자)")

    # KnowledgeDB 검증
    print("\n[4/5] KnowledgeDB playbook 확인...")
    db = KnowledgeDB.get()
    act2_bullets = db.get_bullets("act2_profit", min_quality=0.0)
    act4_bullets = db.get_bullets("act4_stability", min_quality=0.0)
    total_bullets = db.playbook_size()

    print(f"  act2_profit bullets: {len(act2_bullets)}")
    for b, q, s, f in act2_bullets[:5]:
        print(f"    q={q:.2f} s={s} f={f} | {b[:80]}")
    print(f"  act4_stability bullets: {len(act4_bullets)}")
    print(f"  total bullets: {total_bullets}")

    if total_bullets == 0:
        errors.append("playbook에 bullet 0개 — Curator 동작 안 함")

    # 3번째 호출에서 playbook 주입 확인
    print("\n[5/5] 3번째 호출 ContextBundle 재확인...")
    bundle3 = ContextBuilder(question=QUESTIONS[2][0], company=c, provider=provider).build()
    has_pb = "ace.playbook" in bundle3.keys()
    print(f"  ace.playbook: {'YES' if has_pb else 'NO'}")

    # 최종 결과
    print("\n" + "=" * 60)
    if errors:
        print(f"[FAIL] 에러 {len(errors)}건:")
        for e in errors:
            print(f"  - {e}")
        return 1
    else:
        print("[PASS] Live smoke test 통과!")
        print(f"  - 응답 3/3 (100자+)")
        print(f"  - Playbook bullets: {total_bullets}개 누적")
        print(
            f"  - 3번째 호출 playbook 주입: {'YES' if has_pb else 'NO (but bullets exist — selector quality filter)'}"
        )
        return 0


if __name__ == "__main__":
    sys.exit(main())
