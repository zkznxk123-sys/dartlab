"""V6 — *자동화 가능 영역* 분리 + 90% 도달 가능 영역 추출.

V1~V5 종합: best 87.1% (group A, margin ≥ 10).
V6 가설: 90% 미달은 *모든 sample* 검증 때문. 진짜 자동화 가능 sample 만
분리하면 90%+ 도달 가능.

자동화 가능 sample 정의:
- 정답 snakeId 의 cluster 한글 중 *입력과 char N-gram overlap ≥ 50%* 있음
- 즉 사전에 *충분히 가까운 변형* 보유

회귀 가드 아님.
"""

from __future__ import annotations

import hashlib
import random
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


def bigramOverlap(a: str, b: str) -> float:
    a = a.replace(" ", "")
    b = b.replace(" ", "")
    ga = {a[i : i + 2] for i in range(len(a) - 1)} or {a}
    gb = {b[i : i + 2] for i in range(len(b) - 1)} or {b}
    inter = ga & gb
    return len(inter) / min(len(ga), len(gb)) if min(len(ga), len(gb)) else 0


def main():
    data = _loadAccountMappings()
    mappings = data.get("mappings", {})
    sa = data.get("standardAccounts", {})
    korMappings = [(k, v) for k, v in mappings.items() if not any("a" <= c <= "z" or "A" <= c <= "Z" for c in k)]
    random.seed(42)
    sample = random.sample(korMappings, 500)
    sampleSet = set(k for k, _ in sample)

    fullClusterSize = Counter(v for _, v in korMappings)
    snakeToKors = defaultdict(list)
    for k, v in korMappings:
        snakeToKors[v].append(k)

    # group H (high overlap, 자동화 가능): cluster ≥ 2 + 정답 snakeId 의 다른 변형 중 bigram overlap ≥ 0.5
    # group M (medium): overlap 0.2~0.5
    # group L (low): overlap < 0.2 또는 cluster = 1
    groupH, groupM, groupL = [], [], []
    for nm, expectedSnake in sample:
        if fullClusterSize[expectedSnake] < 2:
            groupL.append((nm, expectedSnake))
            continue
        others = [k for k in snakeToKors[expectedSnake] if k != nm]
        if not others:
            groupL.append((nm, expectedSnake))
            continue
        maxOverlap = max(bigramOverlap(nm, o) for o in others)
        if maxOverlap >= 0.5:
            groupH.append((nm, expectedSnake))
        elif maxOverlap >= 0.2:
            groupM.append((nm, expectedSnake))
        else:
            groupL.append((nm, expectedSnake))

    print(f"sample total = {len(sample)}", flush=True)
    print(
        f"  group H (overlap ≥ 0.5, 자동화 가능) = {len(groupH)} ({len(groupH) / len(sample) * 100:.1f}%)", flush=True
    )
    print(f"  group M (overlap 0.2~0.5) = {len(groupM)} ({len(groupM) / len(sample) * 100:.1f}%)", flush=True)
    print(
        f"  group L (overlap < 0.2 or cluster=1) = {len(groupL)} ({len(groupL) / len(sample) * 100:.1f}%)", flush=True
    )

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

    def evaluate(testSample, *, threshold=None, marginMin=None, clusterWeight=False, mhBoost=50, weights=(1, 2, 2, 0)):
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
            if threshold is not None and candidates[0][0] > threshold:
                continue
            if marginMin is not None and len(candidates) >= 2:
                if candidates[1][0] - candidates[0][0] < marginMin:
                    continue
            matched += 1
            if chosen == expectedSnake:
                correct += 1
        return correct, matched

    bestKw = dict(clusterWeight=True, marginMin=10)  # V3 best
    bestKw5 = dict(clusterWeight=True, marginMin=5)
    bestKw0 = dict(clusterWeight=True, threshold=0)
    bestKwHigh = dict(clusterWeight=True, marginMin=20)

    scenarios = [
        # group H — 자동화 가능 영역
        ("84. group H baseline", groupH, dict()),
        ("85. group H + cw", groupH, dict(clusterWeight=True)),
        ("86. group H + cw + margin≥5", groupH, bestKw5),
        ("87. group H + cw + margin≥10", groupH, bestKw),
        ("88. group H + cw + margin≥20", groupH, bestKwHigh),
        ("89. group H + cw + thr≤0", groupH, bestKw0),
        ("90. group H + cw + thr≤-20", groupH, dict(clusterWeight=True, threshold=-20)),
        ("91. group H + cw + thr≤0 + margin≥5", groupH, dict(clusterWeight=True, threshold=0, marginMin=5)),
        ("92. group H + cw + thr≤-20 + margin≥10", groupH, dict(clusterWeight=True, threshold=-20, marginMin=10)),
        # group M
        ("93. group M baseline", groupM, dict()),
        ("94. group M + cw + margin≥10", groupM, bestKw),
        # group L
        ("95. group L baseline", groupL, dict()),
        # all sample (참고)
        ("96. ALL + cw + margin≥10 (참고)", sample, bestKw),
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
