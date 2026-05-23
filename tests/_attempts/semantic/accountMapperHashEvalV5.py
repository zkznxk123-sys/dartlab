"""V5 — Tier 2 identity hash (co-occurrence) 적용.

V7 riVsa 의 정확한 패러다임:
identity[s] = M.T @ M @ characteristic
M = co-occurrence matrix (account_nm 사이)

co-occurrence 정의:
- 같은 snakeId 의 한글 변형 = 강한 co-occurrence (cluster)
- 같은 sj 안 한글 = 약한 co-occurrence

V4 최대 87% → Tier 2 추가 시 90%+ 도달 가능?

회귀 가드 아님.
"""

from __future__ import annotations

import hashlib
import random
from collections import Counter, defaultdict

import numpy as np
from scipy import sparse

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


def characteristic256(s: str) -> np.ndarray:
    """4 region 256-bit → uint8 array of length 32."""
    s = s.replace(" ", "")
    bits = np.zeros(256, dtype=np.float32)
    for c in s:
        for j in decomposeJamo(c):
            bits[int(hashlib.md5(f"jamo{j}".encode()).hexdigest()[:8], 16) % 64] = 1
    for c in s:
        bits[64 + int(hashlib.md5(f"char{c}".encode()).hexdigest()[:8], 16) % 64] = 1
    for i in range(len(s) - 1):
        bits[128 + int(hashlib.md5(f"bg{s[i : i + 2]}".encode()).hexdigest()[:8], 16) % 64] = 1
    h = int(hashlib.md5(s.encode()).hexdigest()[:16], 16)
    for i in range(8):
        bits[192 + ((h >> (i * 4)) & 63)] = 1
    return bits


def cosineDist(a: np.ndarray, b: np.ndarray) -> float:
    na = np.linalg.norm(a)
    nb = np.linalg.norm(b)
    if na == 0 or nb == 0:
        return 1.0
    return 1.0 - float(a @ b) / (na * nb)


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

    # === Characteristic matrix C: N × 256 ===
    dict_items = [(k, v) for k, v in korMappings if k not in sampleSet]
    N = len(dict_items)
    print(f"N = {N}, building characteristic matrix...", flush=True)

    korToIdx = {k: i for i, (k, _) in enumerate(dict_items)}
    snakeArr = [v for _, v in dict_items]
    sjArr = [sa.get(v, {}).get("sj", "") for v in snakeArr]

    C = np.zeros((N, 256), dtype=np.float32)
    for i, (k, _) in enumerate(dict_items):
        C[i] = characteristic256(k)

    # === Co-occurrence matrix M: N × N (sparse) ===
    # i ↔ j 가 같은 snakeId → strong (weight 1.0)
    # i ↔ j 가 같은 sj 만 → weak (weight 0.0 — skip, sparse 폭발 차단)
    print("building co-occurrence M...", flush=True)
    snakeToIndices = defaultdict(list)
    for i, snake in enumerate(snakeArr):
        snakeToIndices[snake].append(i)

    rows, cols, vals = [], [], []
    for snake, idxs in snakeToIndices.items():
        if len(idxs) < 2:
            continue
        for i in idxs:
            for j in idxs:
                if i == j:
                    continue
                rows.append(i)
                cols.append(j)
                vals.append(1.0)
    M = sparse.csr_matrix((vals, (rows, cols)), shape=(N, N), dtype=np.float32)
    print(f"M nnz = {M.nnz:,}", flush=True)

    # === Identity = M.T @ M @ C (self 포함 — V7 idea) ===
    print("identity = M.T @ M @ C ...", flush=True)
    # M.T @ M = sparse symmetric. Result N × 256
    MTM = M.T @ M  # sparse
    identity = MTM @ C + C  # self 포함
    # L2 norm for cosine
    norms = np.linalg.norm(identity, axis=1, keepdims=True)
    norms[norms == 0] = 1
    identityNorm = identity / norms
    print(f"identity shape = {identity.shape}", flush=True)

    sjA = np.array(sjArr)

    def evaluate(testSample, *, threshold=None, marginMin=None, identityMode=True, clusterWeight=False):
        correct = 0
        matched = 0
        for nm, expectedSnake in testSample:
            inputC = characteristic256(nm)
            # input identity — input 한글이 사전에 없으니 자기 characteristic 만 (no neighbor)
            inputId = inputC
            inputIdNorm = inputId / (np.linalg.norm(inputId) or 1)
            expectedSj = sa.get(expectedSnake, {}).get("sj", "")
            # sj filter
            sjMask = (sjA == expectedSj) if expectedSj else np.ones(N, dtype=bool)
            if identityMode:
                # cosine distance to all dict identities
                sims = identityNorm[sjMask] @ inputIdNorm
                scores = 1 - sims
            else:
                # Hamming to characteristic only
                scores = np.sum(np.abs(C[sjMask] - inputC), axis=1)
            if clusterWeight:
                csA = np.array([fullClusterSize[s] for s in (np.array(snakeArr)[sjMask])])
                scores = scores - np.minimum(csA, 20) * 0.005
            order = np.argsort(scores)
            if len(order) == 0:
                continue
            # map back
            sjIndices = np.where(sjMask)[0]
            sortedIdx = sjIndices[order]
            chosenSnake = snakeArr[sortedIdx[0]]
            chosenScore = scores[order[0]]
            if threshold is not None and chosenScore > threshold:
                continue
            if marginMin is not None and len(order) >= 2:
                if scores[order[1]] - scores[order[0]] < marginMin:
                    continue
            matched += 1
            if chosenSnake == expectedSnake:
                correct += 1
        return correct, matched

    scenarios = [
        ("72. identity baseline", dict()),
        ("73. identity + cw", dict(clusterWeight=True)),
        ("74. identity + threshold ≤ 0.5", dict(threshold=0.5)),
        ("75. identity + threshold ≤ 0.3", dict(threshold=0.3)),
        ("76. identity + threshold ≤ 0.1", dict(threshold=0.1)),
        ("77. identity + margin ≥ 0.05", dict(marginMin=0.05)),
        ("78. identity + margin ≥ 0.1", dict(marginMin=0.1)),
        ("79. identity + cw + margin ≥ 0.05", dict(clusterWeight=True, marginMin=0.05)),
        ("80. identity + cw + margin ≥ 0.1", dict(clusterWeight=True, marginMin=0.1)),
        ("81. identity + cw + thr ≤ 0.3 + margin ≥ 0.05", dict(clusterWeight=True, threshold=0.3, marginMin=0.05)),
        ("82. identity + cw + thr ≤ 0.2 + margin ≥ 0.1", dict(clusterWeight=True, threshold=0.2, marginMin=0.1)),
        ("83. Tier 1 only baseline (참고)", dict(identityMode=False)),
    ]

    print()
    print(f"{'scenario':55s} {'correct':>8s} {'matched':>8s} {'accuracy':>10s} {'coverage':>10s}")
    print("-" * 100, flush=True)
    for name, kw in scenarios:
        c, m = evaluate(sampleA, **kw)
        acc = c / m * 100 if m else 0
        cov = m / len(sampleA) * 100 if sampleA else 0
        flag = "  ★★★ ≥ 95%" if acc >= 95 else ("  ★★ ≥ 90%" if acc >= 90 else ("  ★ ≥ 85%" if acc >= 85 else ""))
        print(f"{name:55s} {c:>8d} {m:>8d} {acc:>9.1f}% {cov:>9.1f}%{flag}", flush=True)


if __name__ == "__main__":
    main()
