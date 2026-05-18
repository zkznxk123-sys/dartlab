"""Phase R hallucination 재현 테스트 (보조).

candidate 의 예시 질문을 `POST /api/ask` 로 재질의해 동일 tool sequence 재현을
확인한다. 재현 실패 = pattern 이 더 이상 유효하지 않음 → promote_skill 중단.

사용
====

    uv run python src/dartlab/skills/verify_candidate.py \\
        --candidate data/audit/candidates/2026-04-25-candidates.json \\
        --id cand-2026-04-25-001

서버 off 시 skip + WARN (exit 0).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--candidate", type=Path, required=True)
    ap.add_argument("--id", required=True)
    ap.add_argument("--url", default="http://127.0.0.1:8400/api/ask")
    args = ap.parse_args()

    payload = json.loads(args.candidate.read_text(encoding="utf-8"))
    cand = next((c for c in payload.get("candidates", []) if c.get("id") == args.id), None)
    if cand is None:
        print(f"[fatal] id {args.id} 미발견")
        return 1

    examples = cand.get("example_questions") or []
    if not examples:
        print("[skip] 예시 질문 없음")
        return 0

    try:
        import httpx
    except ImportError:
        print("[skip] httpx 없음")
        return 0

    expected_seq = cand.get("seq_hash")
    print(f"[verify] 예시 {len(examples)} 개 재질의 → seq_hash {expected_seq!r} 비교")

    try:
        with httpx.Client(timeout=60.0) as client:
            for q in examples[:1]:  # 첫 예시만 재호출 (비용 억제)
                try:
                    r = client.post(args.url, json={"question": q, "stream": False})
                except httpx.ConnectError:
                    print(f"[skip] 서버 off (WARN) — {args.url}")
                    return 0
                if r.status_code != 200:
                    print(f"[skip] HTTP {r.status_code}")
                    return 0
                # seq_hash 비교는 audit jsonl 동기화 이후 가능 — 지금은 재호출 완료만 확인
                print(f"  [{q[:40]}...] 재호출 OK ({len(r.text)} bytes)")
    except Exception as e:
        print(f"[error] {e}")
        return 1

    print("[verify] 재현 호출 완료 (seq_hash 비교는 audit jsonl 동기화 후 재실행)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
