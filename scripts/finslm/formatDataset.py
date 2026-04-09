"""Stage A-2 — ShareGPT 포맷 통합 + train/val/test 분리.

data/finslm/raw/*.jsonl → data/finslm/{train,val,test}.jsonl

실행:
    uv run python -X utf8 scripts/finslm/formatDataset.py
"""

from __future__ import annotations

import hashlib
import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
RAW_DIR = ROOT / "data" / "finslm" / "raw"
OUT_DIR = ROOT / "data" / "finslm"


def _dedupe(pairs: list[dict]) -> list[dict]:
    """질문 기준 중복 제거 (같은 질문 → 가장 긴 답변)."""
    best: dict[str, dict] = {}
    for p in pairs:
        q = p["conversations"][1]["value"]
        key = hashlib.md5(q.encode()).hexdigest()
        existing = best.get(key)
        if existing is None or len(p["conversations"][2]["value"]) > len(existing["conversations"][2]["value"]):
            best[key] = p
    return list(best.values())


def _validate(pair: dict) -> bool:
    """최소 품질 필터."""
    convs = pair.get("conversations", [])
    if len(convs) < 3:
        return False
    human = convs[1].get("value", "")
    gpt = convs[2].get("value", "")
    if len(human) < 5 or len(gpt) < 30:
        return False
    return True


def main() -> int:
    # raw 파일 전부 로드
    all_pairs: list[dict] = []
    for f in sorted(RAW_DIR.glob("*.jsonl")):
        with open(f, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line:
                    try:
                        all_pairs.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
        print(f"  {f.name}: {sum(1 for _ in open(f, encoding='utf-8'))}줄")

    print(f"\n로드: {len(all_pairs)}개")

    # 품질 필터
    valid = [p for p in all_pairs if _validate(p)]
    print(f"필터 후: {valid.__len__()}개 (제거 {len(all_pairs) - len(valid)})")

    # 중복 제거
    deduped = _dedupe(valid)
    print(f"중복 제거 후: {len(deduped)}개")

    # 셔플 + 분리 (80/10/10)
    random.seed(42)
    random.shuffle(deduped)

    n = len(deduped)
    n_train = int(n * 0.8)
    n_val = int(n * 0.1)
    train = deduped[:n_train]
    val = deduped[n_train : n_train + n_val]
    test = deduped[n_train + n_val :]

    # 저장
    for name, data in [("train", train), ("val", val), ("test", test)]:
        path = OUT_DIR / f"{name}.jsonl"
        with open(path, "w", encoding="utf-8") as f:
            for p in data:
                f.write(json.dumps(p, ensure_ascii=False) + "\n")
        print(f"  {name}.jsonl: {len(data)}개")

    # 통계
    print(f"\n총: train={len(train)} val={len(val)} test={len(test)}")
    avg_q = sum(len(p["conversations"][1]["value"]) for p in deduped) / max(len(deduped), 1)
    avg_a = sum(len(p["conversations"][2]["value"]) for p in deduped) / max(len(deduped), 1)
    print(f"평균 질문: {avg_q:.0f}자, 평균 답변: {avg_a:.0f}자")

    return 0


if __name__ == "__main__":
    sys.exit(main())
