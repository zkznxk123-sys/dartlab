"""V8 — Hybrid stack: 수동 사전 (mapper.map() 12 단계) + hash 자동 매칭.

V7 결과: HH + cw + margin ≥ 10 = 92.9%, coverage 31.8%
V8 가설: 운영 환경 stack 시 정확도 + coverage 확장
  1. mapper.map() 12 단계 fallback → 사전 hit (정확도 100%)
  2. hash gate (group HH + margin ≥ 10) → 자동 매핑 (92.9%)
  3. fallback nonstd_

회귀 가드 아님.
"""

from __future__ import annotations

import hashlib
import random
from collections import Counter, defaultdict

from dartlab.core.utils.labels import _loadAccountMappings
from dartlab.providers.dart.finance.mapper import AccountMapper

_loadAccountMappings.cache_clear()
AccountMapper.release()

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
    fullClusterSize = Counter(v for _, v in korMappings)

    # === Leave-one-out: 사전에서 sample 제외 ===
    leftMappings = {k: v for k, v in korMappings if k not in sampleSet}

    # mapper.map() 가 leave-out 사전 사용하도록 mapper 패치
    AccountMapper._mappings = leftMappings.copy()
    AccountMapper._stdAccountsRaw = sa
    AccountMapper._noHyphenIndex = None
    AccountMapper._noSpaceIndex = None
    AccountMapper._noParenIndex = None
    mapper = AccountMapper.get() if AccountMapper._instance else AccountMapper()
    AccountMapper._instance = mapper
    # Direct attribute set (safer)
    mapper.__class__._mappings = leftMappings.copy()
    mapper.__class__._stdAccountsRaw = sa
    mapper.__class__._noHyphenIndex = None
    mapper.__class__._noSpaceIndex = None
    mapper.__class__._noParenIndex = None

    # === Hash dict 빌드 ===
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

    # === Step 1: mapper.map() 12 단계 fallback ===
    print("Step 1 — mapper.map() 12 단계 fallback ...", flush=True)
    dictCorrect = 0
    dictMiss = []  # mapper.map() None 인 sample
    dictWrong = 0
    for nm, expectedSnake in sample:
        sid = mapper.map("", nm)
        if sid is None:
            dictMiss.append((nm, expectedSnake))
        elif sid == expectedSnake:
            dictCorrect += 1
        else:
            dictWrong += 1
    print(f"  사전 hit (정답) = {dictCorrect}/{len(sample)} ({dictCorrect / len(sample) * 100:.1f}%)", flush=True)
    print(f"  사전 hit (오답) = {dictWrong}", flush=True)
    print(f"  사전 miss = {len(dictMiss)}", flush=True)

    # === Step 2: hash 자동 매칭 (mapper miss 만) ===
    def hashMatch(nm, expectedSnake, *, marginMin=10, overlapMin=0.7):
        inputH = characteristicRegions(nm)
        inputMh = minhash(nm)
        expectedSj = sa.get(expectedSnake, {}).get("sj", "")
        candidates = []
        for d in dictHashes:
            if expectedSj and d["sj"] != expectedSj:
                continue
            h = weightedDistance(inputH, d["hash"])
            m = mhSim(inputMh, d["mh"])
            s = h - m * 50 - min(d["cs"], 20) * 0.5
            candidates.append((s, d["snake"]))
        if not candidates:
            return None
        candidates.sort()
        chosen = candidates[0][1]
        if len(candidates) >= 2 and candidates[1][0] - candidates[0][0] < marginMin:
            return None
        return chosen

    print("Step 2 — hash 자동 매칭 (사전 miss 의 hash 시도) ...", flush=True)
    # 다양한 margin gate
    for margin in [5, 8, 10, 12, 15, 20]:
        hashCorrect = 0
        hashWrong = 0
        hashUnmapped = 0
        for nm, expectedSnake in dictMiss:
            cand = hashMatch(nm, expectedSnake, marginMin=margin)
            if cand is None:
                hashUnmapped += 1
            elif cand == expectedSnake:
                hashCorrect += 1
            else:
                hashWrong += 1
        # Hybrid 최종 결과
        totalCorrect = dictCorrect + hashCorrect
        totalWrong = dictWrong + hashWrong
        totalAttempted = totalCorrect + totalWrong
        totalUnmapped = hashUnmapped
        accuracy = totalCorrect / totalAttempted * 100 if totalAttempted else 0
        coverage = totalAttempted / len(sample) * 100
        print(
            f"  margin≥{margin:>2}: dict {dictCorrect}/{dictCorrect + dictWrong} + "
            f"hash {hashCorrect}/{hashCorrect + hashWrong} → "
            f"총 {totalCorrect}/{totalAttempted} ({accuracy:.1f}% acc, {coverage:.1f}% cov)",
            flush=True,
        )


if __name__ == "__main__":
    main()
