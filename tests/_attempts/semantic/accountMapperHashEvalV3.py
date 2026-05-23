"""V3 — sample 분리 + Tier 2 identity + 모든 신호 결합 grid search.

V2 결과: best 77.6% (margin ≥ 10), 90% 미달.
V3 가설:
1. cluster ≥ 2 sample (정답 snakeId 가 사전에 변형으로 박혀 있는 경우) 만 분리
   → 진짜 매칭 가능 영역 측정. 90%+ 도달 가능?
2. Tier 2 identity hash (co-occurrence matrix) 추가
3. Top-3 voting + threshold + cluster weight 모든 결합

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


def main():
    data = _loadAccountMappings()
    mappings = data.get("mappings", {})
    sa = data.get("standardAccounts", {})
    korMappings = [(k, v) for k, v in mappings.items() if not any("a" <= c <= "z" or "A" <= c <= "Z" for c in k)]

    random.seed(42)
    sample = random.sample(korMappings, 500)
    sampleSet = set(k for k, _ in sample)

    # cluster size: snakeId 별 *전체* mapping 수 (leave-out 무관)
    fullClusterSize = Counter(v for _, v in korMappings)

    # sample 분리:
    # group A: cluster ≥ 2 (사전에 정답 snakeId 의 다른 변형 있음 = 매칭 가능 영역)
    # group B: cluster == 1 (sample 이 정답 snakeId 의 유일 변형 = 사전에 없는 영역)
    sampleA = [(k, v) for k, v in sample if fullClusterSize[v] >= 2]
    sampleB = [(k, v) for k, v in sample if fullClusterSize[v] == 1]
    print(f"sample total = {len(sample)}", flush=True)
    print(f"  group A (cluster ≥ 2, 매칭 가능 영역) = {len(sampleA)}", flush=True)
    print(f"  group B (cluster = 1, 매칭 불가 영역) = {len(sampleB)}", flush=True)

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
                "cs": fullClusterSize[v],
            }
        )
    print(f"dict = {len(dictHashes):,}", flush=True)

    def matchScore(inputH, inputMh, d, w=(1, 2, 2, 0), mhBoost=50):
        h = weightedDistance(inputH, d["hash"], w)
        m = mhSim(inputMh, d["mh"])
        return h - m * mhBoost

    def evaluate(testSample, score_fn=None, *, threshold=None, marginMin=None, topk=1, clusterWeight=False):
        if score_fn is None:
            score_fn = lambda h, m, d: matchScore(h, m, d)  # noqa: E731
        correct = 0
        matched = 0
        for nm, expectedSnake in testSample:
            inputH = characteristicRegions(nm)
            inputMh = minhash(nm)
            expectedSj = sa.get(expectedSnake, {}).get("sj", "")
            candidates = []
            for d in dictHashes:
                if expectedSj and d["sj"] != expectedSj:
                    continue
                s = score_fn(inputH, inputMh, d)
                if clusterWeight:
                    s -= min(d["cs"], 20) * 0.5  # cluster size bonus (큰 cluster 우선)
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
                # top-k cluster-weighted voting
                topSnakes = []
                for s, snk in candidates[:topk]:
                    topSnakes.append(snk)
                chosen = Counter(topSnakes).most_common(1)[0][0]
            matched += 1
            if chosen == expectedSnake:
                correct += 1
        return correct, matched

    scenarios = [
        # group A (cluster ≥ 2 — 매칭 가능 영역) 만 측정
        ("36. groupA — Hybrid + sj", sampleA, dict()),
        ("37. groupA — + cluster weight", sampleA, dict(clusterWeight=True)),
        ("38. groupA — + thr ≤ 20", sampleA, dict(threshold=20)),
        ("39. groupA — + thr ≤ 0", sampleA, dict(threshold=0)),
        ("40. groupA — + thr ≤ -20", sampleA, dict(threshold=-20)),
        ("41. groupA — + margin ≥ 5", sampleA, dict(marginMin=5)),
        ("42. groupA — + margin ≥ 10", sampleA, dict(marginMin=10)),
        ("43. groupA — + margin ≥ 20", sampleA, dict(marginMin=20)),
        ("44. groupA — cw + thr ≤ 0", sampleA, dict(clusterWeight=True, threshold=0)),
        ("45. groupA — cw + margin ≥ 10", sampleA, dict(clusterWeight=True, marginMin=10)),
        ("46. groupA — cw + margin ≥ 20", sampleA, dict(clusterWeight=True, marginMin=20)),
        ("47. groupA — top-3 + cw", sampleA, dict(topk=3, clusterWeight=True)),
        ("48. groupA — top-5 + cw", sampleA, dict(topk=5, clusterWeight=True)),
        ("49. groupA — top-3 + cw + margin≥10", sampleA, dict(topk=3, clusterWeight=True, marginMin=10)),
        ("50. groupA — cw + thr≤-10 + margin≥10", sampleA, dict(clusterWeight=True, threshold=-10, marginMin=10)),
        # group B 도 측정 — 본질적 한계 영역
        ("51. groupB — baseline (참고)", sampleB, dict()),
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
