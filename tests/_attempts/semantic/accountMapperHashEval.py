"""account 매퍼 hash 매칭 정확도 평가 — leave-one-out 검증.

목적
----
V7 Tier 1 characteristic hash + 다양한 가드/scoring 조합의 정확도 측정.
사전 매핑 500 sample 을 leave-one-out 으로 빼고, 나머지 사전으로 매칭 시도.
정답 snakeId 와 비교해 매칭률·정확도 계산.

목표 — 정확도 90%+ 도달 가능한 조합 찾기.

회귀 가드 아님. 시도 폴더.
"""

from __future__ import annotations

import hashlib
import random
import sys
from collections import Counter, defaultdict

from dartlab.core.utils.labels import _loadAccountMappings

_loadAccountMappings.cache_clear()

# === V7 Tier 1 4-region characteristic ===
JAMO_BASE = ord("가")


def decomposeJamo(c):
    if not ("가" <= c <= "힣"):
        return ()
    i = ord(c) - JAMO_BASE
    cho = i // 588
    jung = (i % 588) // 28
    jong = i % 28
    return (cho, jung, jong) if jong else (cho, jung)


def characteristicRegions(s: str):
    """4 region 별 분리 hash."""
    s = s.replace(" ", "")
    r0 = r1 = r2 = r3 = 0
    for c in s:
        for j in decomposeJamo(c):
            r0 |= 1 << (int(hashlib.md5(f"jamo{j}".encode()).hexdigest()[:8], 16) % 64)
    for c in s:
        r1 |= 1 << (int(hashlib.md5(f"char{c}".encode()).hexdigest()[:8], 16) % 64)
    for i in range(len(s) - 1):
        r2 |= 1 << (int(hashlib.md5(f"bg{s[i : i + 2]}".encode()).hexdigest()[:8], 16) % 64)
    h = int(hashlib.md5(s.encode()).hexdigest()[:16], 16)
    for i in range(8):
        r3 |= 1 << ((h >> (i * 4)) & 63)
    return (r0, r1, r2, r3)


def popcount(x):
    return bin(x).count("1")


def hammingRegions(a, b):
    return [popcount(a[i] ^ b[i]) for i in range(4)]


def weightedDistance(a, b, weights=(1, 1, 1, 1)):
    r = hammingRegions(a, b)
    return sum(r[i] * weights[i] for i in range(4))


ACTIONS = [
    "증가",
    "감소",
    "취득",
    "처분",
    "유입",
    "유출",
    "발행",
    "상환",
    "회수",
    "지급",
    "평가",
    "재측정",
    "재분류",
    "전환",
]
ACTION_OPPOSITES = {
    "증가": "감소",
    "감소": "증가",
    "취득": "처분",
    "처분": "취득",
    "유입": "유출",
    "유출": "유입",
    "발행": "상환",
    "상환": "발행",
}
QUALS = [
    "유동성",
    "비유동",
    "유동",
    "단기",
    "장기",
    "외화",
    "소수",
    "지배기업",
    "지배",
    "연결",
    "별도",
    "기타",
    "주임종",
    "관계기업",
    "공동기업",
    "종속기업",
]


def extractAction(s):
    for a in ACTIONS:
        if a in s:
            return a
    return None


def extractQuals(s):
    return frozenset(q for q in QUALS if q in s)


# === MinHash for hybrid ===
NUM_MH = 64


def minhash(s):
    s = s.replace(" ", "")
    g = {s[i : i + 2] for i in range(len(s) - 1)} or {s}
    hs = [2**32 - 1] * NUM_MH
    for ng in g:
        for i in range(NUM_MH):
            h = int(hashlib.md5((str(i) + ng).encode()).hexdigest()[:8], 16)
            if h < hs[i]:
                hs[i] = h
    return tuple(hs)


def mhSim(a, b):
    return sum(1 for x, y in zip(a, b) if x == y) / len(a)


def main():
    data = _loadAccountMappings()
    mappings = data.get("mappings", {})
    sa = data.get("standardAccounts", {})
    korMappings = [(k, v) for k, v in mappings.items() if not any("a" <= c <= "z" or "A" <= c <= "Z" for c in k)]
    print(f"한글 매핑 = {len(korMappings):,}", flush=True)

    random.seed(42)
    sample = random.sample(korMappings, 500)
    sampleSet = set(k for k, _ in sample)

    print("hash 빌드...", flush=True)
    dictHashes = []
    for k, v in korMappings:
        if k in sampleSet:
            continue
        dictHashes.append(
            {
                "kor": k,
                "snake": v,
                "hash": characteristicRegions(k),
                "mh": minhash(k),
                "action": extractAction(k),
                "quals": extractQuals(k),
                "sj": sa.get(v, {}).get("sj", ""),
            }
        )
    print(f"baseline dict = {len(dictHashes):,}", flush=True)

    def evaluate(score_fn, gate_fn, topk=1):
        correct = 0
        matched = 0
        for nm, expectedSnake in sample:
            inputH = characteristicRegions(nm)
            inputMh = minhash(nm)
            inputAct = extractAction(nm)
            inputQuals = extractQuals(nm)
            expectedSj = sa.get(expectedSnake, {}).get("sj", "")
            candidates = []
            for d in dictHashes:
                if not gate_fn(d, inputAct, inputQuals, expectedSj):
                    continue
                s = score_fn(inputH, inputMh, d)
                candidates.append((s, d["snake"]))
            if not candidates:
                continue
            matched += 1
            candidates.sort()
            if topk == 1:
                if candidates[0][1] == expectedSnake:
                    correct += 1
            else:
                topSnakes = [s for _, s in candidates[:topk]]
                voted = Counter(topSnakes).most_common(1)[0][0]
                if voted == expectedSnake:
                    correct += 1
        return correct, matched

    # === gates ===
    def gate_none(d, inputAct, inputQuals, expectedSj):
        return True

    def gate_sj(d, inputAct, inputQuals, expectedSj):
        return not expectedSj or d["sj"] == expectedSj

    def gate_action(d, inputAct, inputQuals, expectedSj):
        return d["action"] == inputAct

    def gate_aq(d, inputAct, inputQuals, expectedSj):
        return d["action"] == inputAct and d["quals"] == inputQuals

    def gate_a_sj(d, inputAct, inputQuals, expectedSj):
        return d["action"] == inputAct and (not expectedSj or d["sj"] == expectedSj)

    def gate_aq_sj(d, inputAct, inputQuals, expectedSj):
        return d["action"] == inputAct and d["quals"] == inputQuals and (not expectedSj or d["sj"] == expectedSj)

    def gate_strict_opposite(d, inputAct, inputQuals, expectedSj):
        # action 일치 + 반대어 차단 + sj 일치
        if d["action"] != inputAct:
            return False
        opp = ACTION_OPPOSITES.get(inputAct)
        if opp and d["action"] == opp:
            return False
        if expectedSj and d["sj"] != expectedSj:
            return False
        return True

    # === scoring ===
    def score_hamming(inputH, inputMh, d):
        return weightedDistance(inputH, d["hash"])

    def score_weighted(inputH, inputMh, d):
        return weightedDistance(inputH, d["hash"], (1, 2, 2, 0))

    def score_semantic_only(inputH, inputMh, d):
        return weightedDistance(inputH, d["hash"], (1, 1, 2, 0))

    def score_minhash(inputH, inputMh, d):
        return -mhSim(inputMh, d["mh"])

    def score_hybrid(inputH, inputMh, d):
        h = weightedDistance(inputH, d["hash"], (1, 2, 2, 0))
        m = mhSim(inputMh, d["mh"])
        return h - m * 50

    def score_hybrid_strict(inputH, inputMh, d):
        h = weightedDistance(inputH, d["hash"], (0, 2, 3, 0))  # char + bigram strict
        m = mhSim(inputMh, d["mh"])
        return h - m * 80

    scenarios = [
        # baseline
        ("1. V7 Tier 1 단독", score_hamming, gate_none, 1),
        ("2. V7 + sj gate", score_hamming, gate_sj, 1),
        ("3. V7 + action gate", score_hamming, gate_action, 1),
        ("4. V7 + action + qual gate", score_hamming, gate_aq, 1),
        ("5. V7 + action + sj gate", score_hamming, gate_a_sj, 1),
        ("6. V7 + action + qual + sj gate", score_hamming, gate_aq_sj, 1),
        # weighted scoring
        ("7. weighted + sj gate", score_weighted, gate_sj, 1),
        ("8. weighted + action + sj gate", score_weighted, gate_a_sj, 1),
        ("9. weighted + action + qual + sj", score_weighted, gate_aq_sj, 1),
        # MinHash
        ("10. MinHash + sj gate", score_minhash, gate_sj, 1),
        ("11. MinHash + action + sj gate", score_minhash, gate_a_sj, 1),
        ("12. MinHash + a + q + sj gate", score_minhash, gate_aq_sj, 1),
        # Hybrid
        ("13. Hybrid + sj gate", score_hybrid, gate_sj, 1),
        ("14. Hybrid + action + sj gate", score_hybrid, gate_a_sj, 1),
        ("15. Hybrid + a + q + sj gate", score_hybrid, gate_aq_sj, 1),
        ("16. Hybrid strict + a + q + sj", score_hybrid_strict, gate_aq_sj, 1),
        # top-k voting
        ("17. Hybrid + a + q + sj + top-3 vote", score_hybrid, gate_aq_sj, 3),
        ("18. Hybrid strict + a + q + sj + top-3", score_hybrid_strict, gate_aq_sj, 3),
        # semantic only
        ("19. semantic only + a + q + sj", score_semantic_only, gate_aq_sj, 1),
        ("20. semantic only + opposite gate", score_semantic_only, gate_strict_opposite, 1),
    ]

    print()
    print(f"{'scenario':50s} {'correct':>8s} {'matched':>8s} {'accuracy':>10s} {'coverage':>10s}")
    print("-" * 100, flush=True)
    for name, sf, gf, tk in scenarios:
        c, m = evaluate(sf, gf, tk)
        acc = c / m * 100 if m else 0
        cov = m / len(sample) * 100
        flag = "  ★ ≥ 90%" if acc >= 90 else ("  ✓ ≥ 80%" if acc >= 80 else "")
        print(f"{name:50s} {c:>8d} {m:>8d} {acc:>9.1f}% {cov:>9.1f}%{flag}", flush=True)


if __name__ == "__main__":
    main()
