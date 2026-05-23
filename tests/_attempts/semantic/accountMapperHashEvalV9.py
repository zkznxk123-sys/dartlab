"""V9 — 진짜 운영 시뮬레이션 + 카카오 None 일반화.

V8 finding: leave-one-out 에서 mapper.map() 가 *다른 변형* 으로 자동 흡수
하면 leave-out sample 의 *정답 추적 정확도 낮음*. leave-out 자체가
*진짜 미커버 시뮬레이션 불완전*.

V9 가설:
1. *진짜 운영* = 미커버 한글 sample → mapper.map() 시도 (사전 hit) →
   None 면 hash 시도 (자동 매핑) → None 면 nonstd_
2. 운영 환경에선 mapper.map() 의 *오답 흡수* 가 0 (None 또는 정답만)
3. hash 단독 정확도 (V7 = 92.9%) + 사전 fallback 정답률 (운영 환경 90%+) = overall 92~95%

검증:
- 카카오 None 29 개 (실제 미커버) → mapper + hash 조합 결과 + 사람 검증
- 사전 sample leave-cluster (정답 snakeId 의 모든 한글 제외) → hash 단독 정확도

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
    fullClusterSize = Counter(v for _, v in korMappings)
    snakeToKors = defaultdict(list)
    for k, v in korMappings:
        snakeToKors[v].append(k)

    # === Sample 1: leave-cluster (정답 snakeId 의 cluster 전체 사전 제외) ===
    # 진짜 운영 환경 — 미커버 한글이 사전에 *완전 없음*
    random.seed(42)
    sample = random.sample(korMappings, 500)
    # group H sample (overlap ≥ 0.5) 만 — 자동화 가능 영역
    groupH = []
    for nm, expectedSnake in sample:
        if fullClusterSize[expectedSnake] < 2:
            continue
        others = [k for k in snakeToKors[expectedSnake] if k != nm]
        if not others:
            continue
        if max(bigramOverlap(nm, o) for o in others) >= 0.5:
            groupH.append((nm, expectedSnake))
    print(f"group H sample = {len(groupH)}", flush=True)

    # === Hash dict (leave-cluster 방식: sample 의 snakeId cluster 전체 제외) ===
    # 단 group H 의 정답 snakeId 의 *다른* 변형 1 개는 남김 (자동화 가능 영역 보존)
    print("hash 빌드 (leave-cluster)...", flush=True)

    # === Approach 1: 정상 사전 (모든 한글 포함) + hash 매칭 — 운영 시 *미커버* 시뮬레이션 ===
    # 운영 환경: 미커버 한글 = 사전에 없는 *진짜 새* 한글. 사전 cluster 는 그대로.
    # 그래서 dict 에 *모든 사전 한글 포함* — 단 sample 자기 자신만 제외 (입력 한글).
    sampleSet = set(k for k, _ in groupH)
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

    # mapper 도 leave-out (sample 자기 자신만 제외)
    leftMappings = {k: v for k, v in korMappings if k not in sampleSet}
    AccountMapper._mappings = leftMappings
    AccountMapper._stdAccountsRaw = sa
    AccountMapper._noHyphenIndex = None
    AccountMapper._noSpaceIndex = None
    AccountMapper._noParenIndex = None
    mapper = AccountMapper()
    AccountMapper._instance = mapper
    mapper.__class__._mappings = leftMappings
    mapper.__class__._stdAccountsRaw = sa
    mapper.__class__._noHyphenIndex = None
    mapper.__class__._noSpaceIndex = None
    mapper.__class__._noParenIndex = None

    # === Approach: dict + hash 조합 정확도 (운영 환경 — group H sample) ===
    def hashMatch(nm, expectedSj, *, marginMin=10, overlapMin=0.7):
        inputH = characteristicRegions(nm)
        inputMh = minhash(nm)
        candidates = []
        for d in dictHashes:
            if expectedSj and d["sj"] != expectedSj:
                continue
            h = weightedDistance(inputH, d["hash"])
            m = mhSim(inputMh, d["mh"])
            s = h - m * 50 - min(d["cs"], 20) * 0.5
            candidates.append((s, d["snake"], d["kor"]))
        if not candidates:
            return None
        candidates.sort()
        # margin check
        if len(candidates) >= 2 and candidates[1][0] - candidates[0][0] < marginMin:
            return None
        # overlap check (input 과 hash hit 한글의 bigram overlap)
        hitKor = candidates[0][2]
        if bigramOverlap(nm, hitKor) < overlapMin:
            return None
        return candidates[0][1]

    print()
    print("=== Hybrid stack 정확도 (group H, 운영 환경) ===", flush=True)
    print(f"{'config':50s} {'dict_acc':>10s} {'hash_acc':>10s} {'total':>10s} {'cov':>8s}", flush=True)
    print("-" * 100, flush=True)
    for margin in [5, 8, 10, 12, 15, 20]:
        for overlap in [0.5, 0.7]:
            dictCorrect = dictWrong = 0
            hashCorrect = hashWrong = hashSkip = 0
            for nm, expectedSnake in groupH:
                expectedSj = sa.get(expectedSnake, {}).get("sj", "")
                # Step 1: mapper.map()
                sid = mapper.map("", nm)
                if sid is not None:
                    if sid == expectedSnake:
                        dictCorrect += 1
                    else:
                        dictWrong += 1
                    continue
                # Step 2: hash
                cand = hashMatch(nm, expectedSj, marginMin=margin, overlapMin=overlap)
                if cand is None:
                    hashSkip += 1
                elif cand == expectedSnake:
                    hashCorrect += 1
                else:
                    hashWrong += 1
            totalAttempt = dictCorrect + dictWrong + hashCorrect + hashWrong
            totalCorrect = dictCorrect + hashCorrect
            acc = totalCorrect / totalAttempt * 100 if totalAttempt else 0
            cov = totalAttempt / len(groupH) * 100
            flag = "  ★★★ ≥ 95%" if acc >= 95 else ("  ★★ ≥ 90%" if acc >= 90 else ("  ★ ≥ 85%" if acc >= 85 else ""))
            print(
                f"margin≥{margin:>2}, overlap≥{overlap:.1f}: "
                f"d={dictCorrect}/{dictCorrect + dictWrong} h={hashCorrect}/{hashCorrect + hashWrong} "
                f"= {totalCorrect}/{totalAttempt} acc={acc:.1f}% cov={cov:.1f}%{flag}",
                flush=True,
            )


if __name__ == "__main__":
    main()
