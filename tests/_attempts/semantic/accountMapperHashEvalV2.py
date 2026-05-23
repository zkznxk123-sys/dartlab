"""V2 — strict threshold + margin + cluster weighting + identity hash.

V1 결과: best = Hybrid + sj gate = 69%. action/qualifier 가드 역효과.
V2 목표: 정확도 90%+ 도달 가능한 추가 트릭 검증.

신규 신호:
- threshold strict (distance ≤ K, low coverage trade)
- top-1 vs top-2 margin (confidence)
- cluster size weighting (큰 cluster 우선)
- V7 Tier 2 identity (co-occurrence matrix)
- 사전 grammar (한글 base ↔ snakeId base) 강제

회귀 가드 아님.
"""

from __future__ import annotations

import hashlib
import random
import re
from collections import Counter, defaultdict

from dartlab.core.utils.labels import _loadAccountMappings

_loadAccountMappings.cache_clear()

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


def weightedDistance(a, b, weights=(1, 2, 2, 0)):
    r = hammingRegions(a, b)
    return sum(r[i] * weights[i] for i in range(4))


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


# === grammar (Idea 15) ===
ACTIONS_KOR = [
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


def stripActionKor(s: str):
    for a in ACTIONS_KOR:
        if a in s:
            return re.sub(r"[\s()\[\]/.,_\-의은는을를이가과와에도및]", "", s.replace(a, ""))
    return re.sub(r"[\s()\[\]/.,_\-의은는을를이가과와에도및]", "", s)


def main():
    data = _loadAccountMappings()
    mappings = data.get("mappings", {})
    sa = data.get("standardAccounts", {})
    korMappings = [(k, v) for k, v in mappings.items() if not any("a" <= c <= "z" or "A" <= c <= "Z" for c in k)]
    print(f"한글 매핑 = {len(korMappings):,}", flush=True)

    random.seed(42)
    sample = random.sample(korMappings, 500)
    sampleSet = set(k for k, _ in sample)

    # 사전 한글 → 통계
    clusterSize = Counter()  # snakeId → 매핑 수
    korBaseToSnake = defaultdict(Counter)  # base → snakeId 분포
    for k, v in korMappings:
        if k in sampleSet:
            continue
        clusterSize[v] += 1
        kb = stripActionKor(k)
        if kb:
            korBaseToSnake[kb][v] += 1

    # 1:1 결정적 base → snakeId
    deterministicBase = {b: c.most_common(1)[0][0] for b, c in korBaseToSnake.items() if len(c) == 1}
    print(f"deterministic base = {len(deterministicBase):,}", flush=True)

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
                "sj": sa.get(v, {}).get("sj", ""),
                "clusterSize": clusterSize[v],
            }
        )
    print(f"dict = {len(dictHashes):,}", flush=True)

    def matchScore(inputH, inputMh, d, w=(1, 2, 2, 0), mhBoost=50):
        h = weightedDistance(inputH, d["hash"], w)
        m = mhSim(inputMh, d["mh"])
        return h - m * mhBoost

    def evaluate(score_fn, gate_fn, *, threshold=None, marginMin=None, useGrammar=False):
        correct = 0
        matched = 0
        for nm, expectedSnake in sample:
            inputH = characteristicRegions(nm)
            inputMh = minhash(nm)
            expectedSj = sa.get(expectedSnake, {}).get("sj", "")
            inputBase = stripActionKor(nm)
            candidates = []
            for d in dictHashes:
                if not gate_fn(d, expectedSj):
                    continue
                s = score_fn(inputH, inputMh, d)
                candidates.append((s, d["snake"]))
            if not candidates:
                continue
            candidates.sort()
            chosen = candidates[0][1]
            chosenScore = candidates[0][0]
            # threshold
            if threshold is not None and chosenScore > threshold:
                continue
            # margin
            if marginMin is not None and len(candidates) >= 2:
                if candidates[1][0] - candidates[0][0] < marginMin:
                    continue
            # grammar override
            if useGrammar and inputBase in deterministicBase:
                chosen = deterministicBase[inputBase]
            matched += 1
            if chosen == expectedSnake:
                correct += 1
        return correct, matched

    def gate_sj(d, expectedSj):
        return not expectedSj or d["sj"] == expectedSj

    def gate_sj_big_cluster(d, expectedSj):
        return (not expectedSj or d["sj"] == expectedSj) and d["clusterSize"] >= 3

    scenarios = [
        # threshold (낮은 cov, 높은 acc 시도)
        ("21. Hybrid sj, thr ≤ 60", lambda h, m, d: matchScore(h, m, d), gate_sj, dict(threshold=60)),
        ("22. Hybrid sj, thr ≤ 40", lambda h, m, d: matchScore(h, m, d), gate_sj, dict(threshold=40)),
        ("23. Hybrid sj, thr ≤ 20", lambda h, m, d: matchScore(h, m, d), gate_sj, dict(threshold=20)),
        ("24. Hybrid sj, thr ≤ 0", lambda h, m, d: matchScore(h, m, d), gate_sj, dict(threshold=0)),
        ("25. Hybrid sj, thr ≤ -20", lambda h, m, d: matchScore(h, m, d), gate_sj, dict(threshold=-20)),
        # margin
        ("26. Hybrid sj + margin ≥ 5", lambda h, m, d: matchScore(h, m, d), gate_sj, dict(marginMin=5)),
        ("27. Hybrid sj + margin ≥ 10", lambda h, m, d: matchScore(h, m, d), gate_sj, dict(marginMin=10)),
        ("28. Hybrid sj + margin ≥ 20", lambda h, m, d: matchScore(h, m, d), gate_sj, dict(marginMin=20)),
        # cluster size
        ("29. Hybrid sj + cluster ≥ 3", lambda h, m, d: matchScore(h, m, d), gate_sj_big_cluster, {}),
        # grammar override
        ("30. Hybrid sj + grammar override", lambda h, m, d: matchScore(h, m, d), gate_sj, dict(useGrammar=True)),
        (
            "31. Hybrid sj + grammar + thr ≤ 0",
            lambda h, m, d: matchScore(h, m, d),
            gate_sj,
            dict(useGrammar=True, threshold=0),
        ),
        (
            "32. Hybrid sj + grammar + thr ≤ -20",
            lambda h, m, d: matchScore(h, m, d),
            gate_sj,
            dict(useGrammar=True, threshold=-20),
        ),
        # 최강 결합
        (
            "33. Hybrid+grammar+thr≤0+margin≥10",
            lambda h, m, d: matchScore(h, m, d),
            gate_sj,
            dict(useGrammar=True, threshold=0, marginMin=10),
        ),
        (
            "34. Hybrid+grammar+thr≤-10+margin≥10",
            lambda h, m, d: matchScore(h, m, d),
            gate_sj,
            dict(useGrammar=True, threshold=-10, marginMin=10),
        ),
        (
            "35. Hybrid+grammar+thr≤-20+margin≥20",
            lambda h, m, d: matchScore(h, m, d),
            gate_sj,
            dict(useGrammar=True, threshold=-20, marginMin=20),
        ),
    ]

    print()
    print(f"{'scenario':50s} {'correct':>8s} {'matched':>8s} {'accuracy':>10s} {'coverage':>10s}")
    print("-" * 100, flush=True)
    for name, sf, gf, kw in scenarios:
        c, m = evaluate(sf, gf, **kw)
        acc = c / m * 100 if m else 0
        cov = m / len(sample) * 100
        flag = "  ★★ ≥ 95%" if acc >= 95 else ("  ★ ≥ 90%" if acc >= 90 else ("  ✓ ≥ 80%" if acc >= 80 else ""))
        print(f"{name:50s} {c:>8d} {m:>8d} {acc:>9.1f}% {cov:>9.1f}%{flag}", flush=True)


if __name__ == "__main__":
    main()
