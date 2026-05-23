"""V10 — 카카오 None 29 (실제 운영 미커버) + V7 hash 결과 + 사람 검증 후보.

V9 finding: leave-out 의 mapper.map() 자동 흡수 오답이 정확도 폭락 원인.
운영 환경은 *사전 hit = 100% 정답*. 카카오 None 29 으로 진짜 측정.

V10 출력:
1. 카카오 None 29 각각의 hash 결과 (top-1 / top-3 + margin)
2. 사람 검증 시 정확도
3. Hybrid stack 시뮬레이션 — 사전 fallback + hash → overall acc

회귀 가드 아님.
"""

from __future__ import annotations

import hashlib
from collections import Counter, defaultdict

import polars as pl

from dartlab.core.utils.labels import _loadAccountMappings
from dartlab.providers.dart.finance.mapper import AccountMapper

_loadAccountMappings.cache_clear()
AccountMapper.release()
mapper = AccountMapper.get()

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

    print("hash 빌드...", flush=True)
    dictHashes = []
    for k, v in korMappings:
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

    # === 카카오 None unique 한글 ===
    df = pl.read_parquet("data/dart/finance/035720.parquet")
    unique = {}  # nm -> sj
    for r in df.select(["account_id", "account_nm", "sj_div"]).to_dicts():
        nm = r.get("account_nm")
        if not nm:
            continue
        if mapper.map(r.get("account_id") or "", nm) is None:
            if nm not in unique:
                unique[nm] = r["sj_div"]
    print(f"카카오 None unique = {len(unique)}", flush=True)

    def hashTopK(nm, sj, k=3, *, marginMin=10, overlapMin=0.5):
        inputH = characteristicRegions(nm)
        inputMh = minhash(nm)
        candidates = []
        for d in dictHashes:
            if sj and d["sj"] != sj:
                continue
            h = weightedDistance(inputH, d["hash"])
            m = mhSim(inputMh, d["mh"])
            s = h - m * 50 - min(d["cs"], 20) * 0.5
            candidates.append((s, d["snake"], d["kor"]))
        if not candidates:
            return None, []
        candidates.sort()
        # confidence: margin + overlap check
        marginOk = len(candidates) < 2 or (candidates[1][0] - candidates[0][0]) >= marginMin
        hitKor = candidates[0][2]
        overlapOk = bigramOverlap(nm, hitKor) >= overlapMin
        topK = candidates[:k]
        confidence = "✓" if (marginOk and overlapOk) else "?"
        return confidence, topK

    # 카카오 29 각각의 top-3 후보 출력 + 자동 매핑 여부
    print()
    print("=== 카카오 None 29 — V7 hash 자동 매칭 후보 (margin≥10, overlap≥0.5) ===")
    autoAccepted = []  # confidence ✓ 인 케이스
    for nm, sj in unique.items():
        conf, topK = hashTopK(nm, sj)
        if conf is None:
            print(f"  [no candidates] sj={sj} {nm!r}")
            continue
        if conf == "✓":
            autoAccepted.append((nm, sj, topK))
        top1 = topK[0]
        marker = "AUTO" if conf == "✓" else "후보"
        print(f"  [{marker}] sj={sj:4s} {nm!r:50s}")
        for s, snake, kor in topK:
            print(f"           {snake:50s}  ({kor!r}, score={s:.1f})")

    print()
    print(
        f"AUTO 매핑 (confidence ✓) = {len(autoAccepted)}/{len(unique)} ({len(autoAccepted) / len(unique) * 100:.1f}%)",
        flush=True,
    )


if __name__ == "__main__":
    main()
