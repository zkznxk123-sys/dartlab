"""V4 — action region 격리 + char-only/bigram-only strict + 다중 신호 결합.

V3 결과: group A 최대 87.1% (cluster weight + margin ≥ 10).
V4 가설: 90%+ 도달 위해
- 5번째 region 으로 action keyword bloom (액션 어휘 격리)
- char-only / bigram-only strict score (jamo·random 제외)
- region distance 가 *모든 region 0* 인 경우만 hit (perfect)

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


def decomposeJamo(c):
    if not ("가" <= c <= "힣"):
        return ()
    i = ord(c) - JAMO_BASE
    cho = i // 588
    jung = (i % 588) // 28
    jong = i % 28
    return (cho, jung, jong) if jong else (cho, jung)


def characteristic5(s: str):
    """5 region: jamo / char / bigram / random / action."""
    s = s.replace(" ", "")
    r0 = r1 = r2 = r3 = r4 = 0
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
    # Region 5: action bloom (액션 어휘 64 bit dedicated)
    for a in ACTIONS:
        if a in s:
            r4 |= 1 << (int(hashlib.md5(f"act{a}".encode()).hexdigest()[:8], 16) % 64)
    return (r0, r1, r2, r3, r4)


def popcount(x):
    return bin(x).count("1")


def hammingRegions(a, b):
    return [popcount(a[i] ^ b[i]) for i in range(5)]


def weightedDistance(a, b, weights=(1, 2, 2, 0, 5)):
    r = hammingRegions(a, b)
    return sum(r[i] * weights[i] for i in range(5))


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
    random.seed(42)
    sample = random.sample(korMappings, 500)
    sampleSet = set(k for k, _ in sample)

    fullClusterSize = Counter(v for _, v in korMappings)
    sampleA = [(k, v) for k, v in sample if fullClusterSize[v] >= 2]
    print(f"group A = {len(sampleA)}", flush=True)

    print("hash 빌드...", flush=True)
    dictHashes = []
    for k, v in korMappings:
        if k in sampleSet:
            continue
        dictHashes.append(
            {
                "kor": k,
                "snake": v,
                "hash": characteristic5(k),
                "mh": minhash(k),
                "sj": sa.get(v, {}).get("sj", ""),
                "cs": fullClusterSize[v],
            }
        )
    print(f"dict = {len(dictHashes):,}", flush=True)

    def evaluate(
        testSample,
        weights=(1, 2, 2, 0, 5),
        *,
        threshold=None,
        marginMin=None,
        mhBoost=50,
        clusterWeight=False,
        topk=1,
        requireActionMatch=False,
        charOnly=False,
    ):
        correct = 0
        matched = 0
        for nm, expectedSnake in testSample:
            inputH = characteristic5(nm)
            inputMh = minhash(nm)
            expectedSj = sa.get(expectedSnake, {}).get("sj", "")
            candidates = []
            for d in dictHashes:
                if expectedSj and d["sj"] != expectedSj:
                    continue
                if requireActionMatch:
                    # action region distance 0 강제
                    if popcount(inputH[4] ^ d["hash"][4]) > 0:
                        continue
                if charOnly:
                    h = weightedDistance(inputH, d["hash"], (0, 3, 0, 0, 0))
                else:
                    h = weightedDistance(inputH, d["hash"], weights)
                m = mhSim(inputMh, d["mh"])
                s = h - m * mhBoost
                if clusterWeight:
                    s -= min(d["cs"], 20) * 0.5
                candidates.append((s, d["snake"]))
            if not candidates:
                continue
            candidates.sort()
            chosen = candidates[0][1]
            chosenScore = candidates[0][0]
            if threshold is not None and chosenScore > threshold:
                continue
            if marginMin is not None and len(candidates) >= 2:
                if candidates[1][0] - candidates[0][0] < marginMin:
                    continue
            if topk > 1:
                topSnakes = [s for _, s in candidates[:topk]]
                chosen = Counter(topSnakes).most_common(1)[0][0]
            matched += 1
            if chosen == expectedSnake:
                correct += 1
        return correct, matched

    scenarios = [
        # 5-region 시도
        ("52. 5-reg (action w=5)", sampleA, dict()),
        ("53. 5-reg + action match strict", sampleA, dict(requireActionMatch=True)),
        ("54. 5-reg + cw + action strict", sampleA, dict(requireActionMatch=True, clusterWeight=True)),
        ("55. 5-reg action w=10", sampleA, dict(weights=(1, 2, 2, 0, 10))),
        ("56. 5-reg action w=20", sampleA, dict(weights=(1, 2, 2, 0, 20))),
        ("57. 5-reg + cw + thr≤0", sampleA, dict(clusterWeight=True, threshold=0)),
        ("58. 5-reg + cw + margin≥10", sampleA, dict(clusterWeight=True, marginMin=10)),
        ("59. 5-reg + cw + action + margin≥5", sampleA, dict(clusterWeight=True, requireActionMatch=True, marginMin=5)),
        (
            "60. 5-reg + cw + action + margin≥10",
            sampleA,
            dict(clusterWeight=True, requireActionMatch=True, marginMin=10),
        ),
        ("61. 5-reg + cw + action + thr≤0", sampleA, dict(clusterWeight=True, requireActionMatch=True, threshold=0)),
        (
            "62. 5-reg + cw + action + thr≤-10",
            sampleA,
            dict(clusterWeight=True, requireActionMatch=True, threshold=-10),
        ),
        ("63. char-only + cw", sampleA, dict(charOnly=True, clusterWeight=True)),
        ("64. char-only + cw + thr≤0", sampleA, dict(charOnly=True, clusterWeight=True, threshold=0)),
        ("65. char-only + cw + margin≥10", sampleA, dict(charOnly=True, clusterWeight=True, marginMin=10)),
        (
            "66. char-only + cw + action + margin≥10",
            sampleA,
            dict(charOnly=True, clusterWeight=True, requireActionMatch=True, marginMin=10),
        ),
        ("67. 5-reg act20 + cw + margin≥10", sampleA, dict(weights=(1, 2, 2, 0, 20), clusterWeight=True, marginMin=10)),
        (
            "68. 5-reg act20 + cw + action strict + margin≥5",
            sampleA,
            dict(weights=(1, 2, 2, 0, 20), clusterWeight=True, requireActionMatch=True, marginMin=5),
        ),
        (
            "69. 5-reg act20 + cw + action + margin≥15",
            sampleA,
            dict(weights=(1, 2, 2, 0, 20), clusterWeight=True, requireActionMatch=True, marginMin=15),
        ),
        (
            "70. 5-reg act20 + cw + action + thr≤-10",
            sampleA,
            dict(weights=(1, 2, 2, 0, 20), clusterWeight=True, requireActionMatch=True, threshold=-10),
        ),
        (
            "71. 5-reg act20 + cw + action + thr≤-20",
            sampleA,
            dict(weights=(1, 2, 2, 0, 20), clusterWeight=True, requireActionMatch=True, threshold=-20),
        ),
    ]

    print()
    print(f"{'scenario':52s} {'correct':>8s} {'matched':>8s} {'accuracy':>10s} {'coverage':>10s}")
    print("-" * 100, flush=True)
    for name, smpl, kw in scenarios:
        c, m = evaluate(smpl, **kw)
        acc = c / m * 100 if m else 0
        cov = m / len(smpl) * 100 if smpl else 0
        flag = "  ★★★ ≥ 95%" if acc >= 95 else ("  ★★ ≥ 90%" if acc >= 90 else ("  ★ ≥ 85%" if acc >= 85 else ""))
        print(f"{name:52s} {c:>8d} {m:>8d} {acc:>9.1f}% {cov:>9.1f}%{flag}", flush=True)


if __name__ == "__main__":
    main()
