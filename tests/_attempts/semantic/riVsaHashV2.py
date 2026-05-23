"""RI-VSA v2 — scipy.sparse 행렬곱 + bigram·trigram 합집합.

목적
----
v1 의 한계 2 종 해결:
1. **속도**: 13 분 → 수십 초. Pass 2 의 Python loop 제거.
2. **동의어 갭**: bigram 추가로 sub-stem 공유 (자기주식 vs 자사주 둘 다 "주" 공유).

핵심 통찰
---------
v1 의 counter 누적은 사실 *희소 행렬 곱셈* 이다:
    counter = (M.T @ M) @ idxHashes
어디서 M = section × stem 이진 sparse.

(M.T @ M) 는 *공기 행렬* (CO[s,s'] = s 와 s' 가 같이 등장한 섹션 수).
이걸 idxHashes 와 곱하면 v1 의 counter 와 *수학적으로 동일*.

추가로 linear algebra 트릭:
    (M.T @ M) @ H = M.T @ (M @ H)
중간 (M.T @ M) 을 *재구성하지 않고* 두 번 곱하기만. 메모리 절약 + 속도 폭발.

다중 n-gram
----------
v1: trigram 만 → 자기주↔자사주 같은 다른 표면 형태 못 묶음.
v2: bigram + trigram 같은 hash 공간. "주" 같은 sub-stem 이 다리 놓는다.

위치 회전은 v3 에서 (지금은 bag-of-context).

방법
----
1. tokenize(section) → bigram + trigram 합집합
2. M = section × stem 이진 sparse (scipy.sparse.csr_matrix)
3. temp = M @ idxHashes  → (n_sec, 256) 섹션별 stem 합
4. weighted = M.T @ temp → (n_stems, 256) 각 stem 의 분포 누적
5. self 보정: weighted -= diag(M.T @ M) ⊙ idxHashes
6. contextHash = (weighted > 0).pack → 256-bit per stem

비고
----
- 시도 폴더 (회귀 가드 아님)
- v1 의 30K sample 동일 조건으로 빠른 비교
- 성공 → v3 (위치 회전) → v4 (allFilings + docs 전체) → 검색 인터페이스 → 언어 모델 흉내

결과 (2026-05-20, 65 일치 allFilings 30K 샘플)
------------------------------------------------
빌드: load 7.4s + stems 28.9s + M 26.8s + idxHash 0.8s + **matmul 12.9s** + pack 0.0s = **77 초**
v1 대비 **10× 빠름** (v1 = 13 분). matmul 만 비교 시 v1 의 Pass 2 = 762s → 12.9s = **60× 빠름**.

stems: 146,937 (bigram + trigram, v1 의 trigram-only 87,739 보다 60K 추가)
M: 30,000 × 146,937 nnz=32M, 129MB
최종 contextHash: 4.7 MB

PROBE A 의미 이웃 1순위 d (v1 vs v2):
- 유상증 → 상증자: v1=63, v2=4
- 전환사 → 환사채: v1=63, v2=5
- 자기주 → 기주식: v1=58, v2=11
- 차입금 → 장기차: v1=67, v2=10
- HBM → 반도체 family: v1=89~99 (random), v2=16~22 (의미 family)
→ **distance 폭격 작아짐** (v1 d=58~80 → v2 d=4~25)

PROBE B 쌍 distance:
- 자기 vs 자사 v2=27 (v1 d=130 = random mean → 100점 메움)
- 자기주 vs 자사 v2=39
- 취득 vs 처분 v2=15
- 대표 vs 임원 v2=27

PROBE C baseline: v2 mean=72.5 (v1=125.6). 1-bit 쪽으로 편향 (matmul 결과 부호 양수 쪽 우세).

결론
----
- ★ 10× 속도 향상 (Pass 2 의 Python loop 제거)
- ★ bigram + trigram 으로 부분문자열 인식 추가
- ★ 자기↔자사 d=130→27 동의어 갭 부분 메움
- × baseline mean=72.5 편향 (이론 128 의 56% 만) — 변별력 약화
- × "차입 vs 사채" d=45 ≈ "자기 vs 농업" d=43 — 분리 약함

다음 단계
--------
v3 — IDF 가중 + 풀 corpus. baseline 편향 회복 + 더 풍부한 분포.
"""

from __future__ import annotations

import hashlib
import time
from collections import Counter
from pathlib import Path

import numpy as np
import polars as pl
from scipy.sparse import csr_matrix

HASH_BITS = 256
HASH_BYTES = 32
NGRAM_NS = (2, 3)  # bigram + trigram
MIN_DOC_FREQ = 10
MAX_TOKENS_PER_SECTION = 4000  # bigram + trigram 합쳐 cap
SAMPLE_SECTIONS = 30000
TOP_K = 15
SEED = 42

INPUT_DIR = Path("data/dart/allFilings")

PROBE_TERMS = [
    # trigram
    "유상증",
    "전환사",
    "차입금",
    "자기주",
    "대표이",
    "주주총",
    "최대주",
    # bigram
    "유상",
    "사채",
    "차입",
    "자사",
    "자기",
    "대표",
    "총회",
    "변경",
    "취득",
    "처분",
    "합병",
    "소송",
    "특허",
    "HBM",
]

PROBE_PAIRS_NEAR = [
    ("자기", "자사"),  # bigram synonym test
    ("자기주", "자사"),  # cross-gram synonym test
    ("유상", "증자"),
    ("차입", "사채"),
    ("취득", "처분"),
    ("대표", "임원"),
]
PROBE_PAIRS_FAR = [
    ("자기", "농업"),
    ("배당", "특허"),
    ("HBM", "농업"),
]


def indexHashSigned(stem: str) -> np.ndarray:
    """blake2b → 256 dim ±1 signed (int8)."""
    h = hashlib.blake2b(stem.encode(), digest_size=HASH_BYTES).digest()
    bits = np.unpackbits(np.frombuffer(h, dtype=np.uint8))
    return bits.astype(np.int8) * 2 - 1


def tokenize(s: str, *, max_count: int = MAX_TOKENS_PER_SECTION) -> list[str]:
    """bigram + trigram 합집합 (순서 보존)."""
    tokens: list[str] = []
    for n in NGRAM_NS:
        if len(s) < n:
            continue
        upto = min(len(s) - n + 1, max_count)
        for i in range(upto):
            tokens.append(s[i : i + n])
    return tokens


def main() -> None:
    print("=" * 72)
    print("RI-VSA v2 — scipy.sparse + bigram·trigram")
    print(f"  NGRAM_NS={NGRAM_NS}  MIN_DF={MIN_DOC_FREQ}  SAMPLE={SAMPLE_SECTIONS}")
    print("=" * 72)

    # ── 1. 로드 ──
    t0 = time.perf_counter()
    files = sorted(p for p in INPUT_DIR.glob("2026*.parquet") if "_meta" not in p.name)
    df = pl.concat(
        [pl.read_parquet(f, columns=["section_content"]).filter(pl.col("section_content").is_not_null()) for f in files]
    )
    if df.height > SAMPLE_SECTIONS:
        df = df.sample(SAMPLE_SECTIONS, seed=SEED)
    sections = df["section_content"].to_list()
    total_chars = sum(len(s) for s in sections)
    print(
        f"[load] {len(files)} 일치 → 섹션 {len(sections):,} 샘플 "
        f"({total_chars / 1e6:.1f}M chars) — {time.perf_counter() - t0:.1f}s"
    )

    # ── 2. Pass 1: doc_freq ──
    t0 = time.perf_counter()
    doc_freq: Counter[str] = Counter()
    section_tokens: list[list[str]] = []
    for s in sections:
        toks = tokenize(s)
        section_tokens.append(toks)
        doc_freq.update(set(toks))
    keep = sorted(t for t, c in doc_freq.items() if c >= MIN_DOC_FREQ)
    g2id = {t: i for i, t in enumerate(keep)}
    id2g = keep
    n_stems = len(g2id)
    print(
        f"[stems] {len(doc_freq):,} 전체 → df≥{MIN_DOC_FREQ} {n_stems:,} "
        f"(bigram + trigram) — {time.perf_counter() - t0:.1f}s"
    )

    # ── 3. sparse M = section × stem ──
    t0 = time.perf_counter()
    rows: list[int] = []
    cols: list[int] = []
    for sid, toks in enumerate(section_tokens):
        seen_ids = set()
        for t in toks:
            gid = g2id.get(t)
            if gid is not None and gid not in seen_ids:
                seen_ids.add(gid)
                rows.append(sid)
                cols.append(gid)
    n_sec = len(sections)
    M = csr_matrix(
        (np.ones(len(rows), dtype=np.int32), (rows, cols)),
        shape=(n_sec, n_stems),
    )
    print(
        f"[M] {n_sec:,} × {n_stems:,}  nnz={M.nnz:,}  "
        f"({M.data.nbytes / 1e6:.1f} MB data)  — {time.perf_counter() - t0:.1f}s"
    )
    # free section_tokens — 더 이상 필요 없음
    del section_tokens, rows, cols

    # ── 4. idxHashes ──
    t0 = time.perf_counter()
    idxHashes = np.zeros((n_stems, HASH_BITS), dtype=np.int32)
    for stem, sid in g2id.items():
        idxHashes[sid] = indexHashSigned(stem).astype(np.int32)
    print(f"[idxHash] {idxHashes.nbytes / 1e6:.1f} MB — {time.perf_counter() - t0:.1f}s")

    # ── 5. weighted = M.T @ (M @ idxHashes) ──
    # 핵심: linear algebra 트릭으로 CO 행렬 재구성 X
    t0 = time.perf_counter()
    temp = M @ idxHashes  # (n_sec, 256)
    weighted = (M.T @ temp).astype(np.int64)  # (n_stems, 256)
    print(
        f"[matmul] M @ ix → (M.T @ that) = (n_sec={n_sec}, 256) → (n_stems={n_stems}, 256) "
        f"— {time.perf_counter() - t0:.1f}s"
    )

    # ── 6. self 보정 ──
    t0 = time.perf_counter()
    # diag(M.T @ M)[s] = doc_freq[s] (M 이 binary 라면 정확히 doc_freq)
    df_arr = np.asarray([doc_freq[id2g[i]] for i in range(n_stems)], dtype=np.int64)
    self_contrib = df_arr[:, None] * idxHashes  # (n_stems, 256)
    weighted -= self_contrib
    print(f"[self-correct] |max|={np.abs(weighted).max()} — {time.perf_counter() - t0:.1f}s")

    # ── 7. pack to 256-bit ──
    t0 = time.perf_counter()
    contextBits = (weighted > 0).astype(np.uint8)
    contextPacked = np.packbits(contextBits, axis=1)
    print(f"[pack] {contextPacked.nbytes / 1e6:.1f} MB — {time.perf_counter() - t0:.1f}s")

    # ── 8. PROBE A — 의미 이웃 ──
    print()
    print(f"─── PROBE A: 의미 이웃 (top {TOP_K}) ───")
    for term in PROBE_TERMS:
        if term not in g2id:
            print(f'\n? "{term}" — 인덱스 없음 (df < {MIN_DOC_FREQ})')
            continue
        sid = g2id[term]
        xored = np.bitwise_xor(contextPacked, contextPacked[sid : sid + 1])
        dist = np.unpackbits(xored, axis=1).sum(axis=1)
        nearest = np.argpartition(dist, TOP_K + 1)[: TOP_K + 1]
        nearest = sorted(nearest, key=lambda i: dist[i])
        nearest = [i for i in nearest if i != sid][:TOP_K]
        print(f'\n? "{term}"  (df={df_arr[sid]:,})')
        for i in nearest:
            print(f"    d={int(dist[i]):3d}  df={int(df_arr[i]):>6d}  {id2g[i]!r}")

    # ── 9. PROBE B — 쌍 ──
    print()
    print("─── PROBE B: 쌍 distance ───")
    for label, pairs in [("가까워야", PROBE_PAIRS_NEAR), ("멀어야", PROBE_PAIRS_FAR)]:
        print(f"\n[{label}]")
        for a, b in pairs:
            if a not in g2id or b not in g2id:
                print(f"  {a:8s} vs {b:8s} — 누락")
                continue
            ai, bi = g2id[a], g2id[b]
            d = int(np.unpackbits(np.bitwise_xor(contextPacked[ai], contextPacked[bi])).sum())
            print(f"  {a:8s} vs {b:8s}  d={d}")

    # ── 10. PROBE C — baseline ──
    print()
    print("─── PROBE C: 무작위 baseline ───")
    rng = np.random.default_rng(SEED)
    idxs = rng.choice(n_stems, size=2000, replace=False)
    xored = np.bitwise_xor(contextPacked[idxs[:1000]], contextPacked[idxs[1000:]])
    dists = np.unpackbits(xored, axis=1).sum(axis=1)
    print(
        f"  1000 random pairs: mean={dists.mean():.1f}  median={np.median(dists):.1f}  "
        f"std={dists.std():.1f}  min={dists.min()}  max={dists.max()}"
    )


if __name__ == "__main__":
    main()
