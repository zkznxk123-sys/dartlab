"""V7 — 90% 돌파 fine-tuning. 미세 조정 + group H/HH 분리.

V6 결과: group H best = 89.7% (cw + margin ≥ 10).
V7 목표: 90% + 95% 도달 전수 시도.

신규:
- group HH (overlap ≥ 0.7) — 더 엄격 영역
- margin grid 8, 12, 15
- threshold + margin 조합 grid
- top-k voting + cw + margin

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


def bigramOverlap(a, b):
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

    groupH, groupHH = [], []
    for nm, expectedSnake in sample:
        if fullClusterSize[expectedSnake] < 2:
            continue
        others = [k for k in snakeToKors[expectedSnake] if k != nm]
        if not others:
            continue
        maxOverlap = max(bigramOverlap(nm, o) for o in others)
        if maxOverlap >= 0.7:
            groupHH.append((nm, expectedSnake))
        if maxOverlap >= 0.5:
            groupH.append((nm, expectedSnake))

    print(f"group H (overlap ≥ 0.5) = {len(groupH)}", flush=True)
    print(f"group HH (overlap ≥ 0.7) = {len(groupHH)}", flush=True)

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

    def evaluate(
        testSample,
        *,
        threshold=None,
        marginMin=None,
        mhBoost=50,
        weights=(1, 2, 2, 0),
        clusterWeight=False,
        topk=1,
        csBonus=0.5,
    ):
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
                    s -= min(d["cs"], 20) * csBonus
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
            if topk > 1:
                topSnakes = [s for _, s in candidates[:topk]]
                chosen = Counter(topSnakes).most_common(1)[0][0]
            matched += 1
            if chosen == expectedSnake:
                correct += 1
        return correct, matched

    scenarios = [
        # group H fine grid
        ("97. H + cw + margin≥8", groupH, dict(clusterWeight=True, marginMin=8)),
        ("98. H + cw + margin≥10", groupH, dict(clusterWeight=True, marginMin=10)),
        ("99. H + cw + margin≥12", groupH, dict(clusterWeight=True, marginMin=12)),
        ("100. H + cw + margin≥15", groupH, dict(clusterWeight=True, marginMin=15)),
        ("101. H + cw csB=1.0 + margin≥10", groupH, dict(clusterWeight=True, csBonus=1.0, marginMin=10)),
        ("102. H + cw csB=2.0 + margin≥10", groupH, dict(clusterWeight=True, csBonus=2.0, marginMin=10)),
        ("103. H + cw + thr≤-10 + margin≥10", groupH, dict(clusterWeight=True, threshold=-10, marginMin=10)),
        ("104. H + cw + thr≤-15 + margin≥10", groupH, dict(clusterWeight=True, threshold=-15, marginMin=10)),
        ("105. H + cw + thr≤-15 + margin≥15", groupH, dict(clusterWeight=True, threshold=-15, marginMin=15)),
        ("106. H + cw + thr≤-25 + margin≥5", groupH, dict(clusterWeight=True, threshold=-25, marginMin=5)),
        ("107. H + top-3 + cw + margin≥10", groupH, dict(clusterWeight=True, marginMin=10, topk=3)),
        ("108. H + top-5 + cw + margin≥10", groupH, dict(clusterWeight=True, marginMin=10, topk=5)),
        (
            "109. H + char-heavy (w=0,3,3,0) + cw + margin≥10",
            groupH,
            dict(weights=(0, 3, 3, 0), clusterWeight=True, marginMin=10),
        ),
        (
            "110. H + bigram-heavy (w=0,1,5,0) + cw + margin≥10",
            groupH,
            dict(weights=(0, 1, 5, 0), clusterWeight=True, marginMin=10),
        ),
        ("111. H + mhBoost=100 + cw + margin≥10", groupH, dict(mhBoost=100, clusterWeight=True, marginMin=10)),
        ("112. H + mhBoost=20 + cw + margin≥10", groupH, dict(mhBoost=20, clusterWeight=True, marginMin=10)),
        # group HH (더 엄격 영역)
        ("113. HH + cw + margin≥10", groupHH, dict(clusterWeight=True, marginMin=10)),
        ("114. HH + cw + margin≥5", groupHH, dict(clusterWeight=True, marginMin=5)),
        ("115. HH + cw + thr≤0", groupHH, dict(clusterWeight=True, threshold=0)),
        ("116. HH + cw + thr≤-20", groupHH, dict(clusterWeight=True, threshold=-20)),
        ("117. HH baseline", groupHH, dict()),
    ]

    print()
    print(f"{'scenario':55s} {'correct':>8s} {'matched':>8s} {'accuracy':>10s} {'coverage':>10s}")
    print("-" * 100, flush=True)
    for name, smpl, kw in scenarios:
        c, m = evaluate(smpl, **kw)
        acc = c / m * 100 if m else 0
        cov = m / len(smpl) * 100 if smpl else 0
        flag = "  ★★★ ≥ 95%" if acc >= 95 else ("  ★★ ≥ 90%" if acc >= 90 else ("  ★ ≥ 85%" if acc >= 85 else ""))
        print(f"{name:55s} {c:>8d} {m:>8d} {acc:>9.1f}% {cov:>9.1f}%{flag}", flush=True)


if __name__ == "__main__":
    main()
