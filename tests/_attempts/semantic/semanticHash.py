"""Semantic Hash 시도 — 분포 의미를 polars + sparse matmul + SimHash 로.

목적
----
의미를 *학습된 임베딩* 없이, 코퍼스 *자체의 동료 분포* 에서 계산.

가설
----
Firth 1957: "단어 의미 = 그 단어와 함께 등장하는 동료".
- 섹션-단어 sparse matrix M
- 공기 행렬 = M.T @ M (≈ 분포)
- PPMI 가중 → 변별력 있는 동료만 강조
- SimHash 128 bit → 16 byte 의미 시그니처
- Hamming distance < N → 의미 이웃

기대 결과
--------
"유상" 의 의미 이웃 ⊇ {증자, 신주, 발행, 청약, 자본금, 운영자금, 결정} 같은
공시 도메인 공기어. 자연어 임베딩 모델 없이 분포만으로 의미가 잡히면 성공.

비고
----
- 회귀 가드 아님. 시도용 보관.
- 처음엔 trigram 만 (한글 trigram 이 bigram 보다 의미 단위에 가까움).
- 53 일치 본문 표본. scale up 검증 추후.

결과 (2026-05-20, 실패 — Python set OOM)
-----------------------------------------
첫 시도 모두 *Python set per section + all-pairs co-occurrence list* 가 메모리 폭발.
417K 섹션 × 평균 200 set 항목 × 100 byte/string = 8+ GB. all-pairs = 50M+ pair tuples.
시스템 메모리 31.3 GB 중 free 0.1 GB 까지 squeeze → MemoryError.

교훈
----
- Python set / dict / list 의 per-object overhead 가 수십 byte
- numpy / scipy.sparse 로 모든 누적 연산 옮겨야 안전
- Reservoir sampling 으로 *load 단계부터* 메모리 cap 필수

리팩토링 결과
-----------
이 파일 대신 [riVsaHash.py](riVsaHash.py) (v1) 가 numpy int16 counter 로
재구현 → OOM 0. 본 파일은 *실패 사례* 로 보존 (같은 실수 반복 방지).
"""

from __future__ import annotations

import hashlib
import time
from pathlib import Path

import numpy as np
import polars as pl
from scipy.sparse import csr_matrix

INPUT_DIR = Path("data/dart/allFilings")
HASH_BITS = 128
TOP_K_NEIGHBORS = 15
NGRAM_N = 3
MIN_NGRAM_DOC_FREQ = 10  # ngram 이 등장한 섹션 수 최소
MAX_NGRAMS_PER_SECTION = 800  # 긴 섹션 의 bigram 너무 많이 → cap
PROBE_TERMS = [
    "유상증자",
    "전환사",
    "차입금",
    "자기주",
    "대표이",
    "공시",
    "주주총",
    "합병",
    "특허",
    "소송",
    "최대주",
    "임원ㆍ",
]


def extractNgrams(text: str, *, n: int = NGRAM_N, cap: int = MAX_NGRAMS_PER_SECTION) -> set[str]:
    text = (text or "").strip()
    if len(text) < n:
        return set()
    s = {text[i : i + n] for i in range(len(text) - n + 1)}
    if len(s) > cap:
        # 너무 큰 섹션은 random sample
        s = set(list(s)[:cap])
    return s


def main() -> None:
    print("=" * 72)
    print(f"Semantic Hash — {NGRAM_N}-gram + sparse matmul + SimHash")
    print("=" * 72)

    # ── 1. 코퍼스 로드 ──
    t0 = time.perf_counter()
    files = sorted(p for p in INPUT_DIR.glob("2026*.parquet") if "_meta" not in p.name)
    print(f"[load] {len(files)} 일치 parquet")
    df = pl.concat(
        [pl.read_parquet(f, columns=["section_content"]).filter(pl.col("section_content").is_not_null()) for f in files]
    )
    sections = df["section_content"].to_list()
    total_chars = sum(len(s) for s in sections)
    print(f"[load] 섹션 {len(sections):,} 개, 총 {total_chars / 1e6:.1f}M chars, {time.perf_counter() - t0:.1f}s")

    # ── 2. ngram 추출 + 빈도 컷 ──
    t0 = time.perf_counter()
    doc_freq: dict[str, int] = {}
    section_ngrams: list[set[str]] = []
    for s in sections:
        ns = extractNgrams(s)
        section_ngrams.append(ns)
        for g in ns:
            doc_freq[g] = doc_freq.get(g, 0) + 1
    keep = {g for g, c in doc_freq.items() if c >= MIN_NGRAM_DOC_FREQ}
    print(
        f"[ngram] 전체 {len(doc_freq):,} → doc_freq ≥{MIN_NGRAM_DOC_FREQ} {len(keep):,}, "
        f"{time.perf_counter() - t0:.1f}s"
    )

    g2id = {g: i for i, g in enumerate(sorted(keep))}
    id2g = {i: g for g, i in g2id.items()}
    n_grams = len(g2id)

    # ── 3. 섹션-ngram sparse matrix ──
    t0 = time.perf_counter()
    rows: list[int] = []
    cols: list[int] = []
    for sid, ns in enumerate(section_ngrams):
        for g in ns:
            gid = g2id.get(g)
            if gid is not None:
                rows.append(sid)
                cols.append(gid)
    n_sec = len(section_ngrams)
    M = csr_matrix(
        (np.ones(len(rows), dtype=np.int32), (rows, cols)),
        shape=(n_sec, n_grams),
    )
    print(f"[matrix] M = {n_sec:,} × {n_grams:,}, nnz={M.nnz:,}, {time.perf_counter() - t0:.1f}s")

    # ── 4. 공기 행렬 = M.T @ M ──
    t0 = time.perf_counter()
    CO = M.T @ M  # (n_grams, n_grams) sparse
    print(f"[co-occ] CO nnz={CO.nnz:,}, {time.perf_counter() - t0:.1f}s")

    # ── 5. PPMI ──
    t0 = time.perf_counter()
    # p_g = doc_freq / n_sec
    p_g = np.asarray(M.sum(axis=0)).flatten().astype(np.float32) / n_sec
    p_g = np.maximum(p_g, 1e-12)
    # PMI(a,b) = log( p_ab / (p_a * p_b) ),  p_ab = CO[a,b] / n_sec
    # 대각 = doc_freq → 자기 자신 (skip), PMI 음수 → 0
    CO = CO.tocoo()
    a = CO.row
    b = CO.col
    p_ab = CO.data.astype(np.float32) / n_sec
    pmi = np.log((p_ab + 1e-12) / (p_g[a] * p_g[b] + 1e-12))
    ppmi = np.maximum(pmi, 0.0)
    # 자기 자신 제거
    mask = (a != b) & (ppmi > 0)
    a = a[mask]
    b = b[mask]
    ppmi = ppmi[mask]
    print(f"[ppmi] positive pairs: {len(ppmi):,}, {time.perf_counter() - t0:.1f}s")

    # ── 6. ngram 별 동료 프로파일 → SimHash ──
    t0 = time.perf_counter()

    # neighbor_id → 128 bit ±1 sign vector (deterministic via blake2b hash)
    def signFor(nid: int, cache={}):
        v = cache.get(nid)
        if v is None:
            h = hashlib.blake2b(str(nid).encode(), digest_size=HASH_BITS // 8).digest()
            bits = np.unpackbits(np.frombuffer(h, dtype=np.uint8))
            v = bits.astype(np.int8) * 2 - 1  # 0→-1, 1→+1
            cache[nid] = v.astype(np.float32)
        return cache[nid]

    # SimHash 누적: acc[a] += sign(b) * ppmi
    acc = np.zeros((n_grams, HASH_BITS), dtype=np.float32)
    # 대칭이라 (a,b) 와 (b,a) 둘 다 누적
    for i in range(len(a)):
        ai, bi, w = int(a[i]), int(b[i]), float(ppmi[i])
        acc[ai] += signFor(bi) * w
        acc[bi] += signFor(ai) * w
    sig_bits = (acc > 0).astype(np.uint8)
    sig_packed = np.packbits(sig_bits, axis=1)  # (n_grams, 16)
    print(
        f"[simhash] {n_grams:,} ngram × {HASH_BITS // 8} byte = {sig_packed.nbytes / 1e6:.1f} MB, "
        f"{time.perf_counter() - t0:.1f}s"
    )

    # ── 7. probe 의미 이웃 검증 ──
    print()
    print(f"─── PROBE: 의미 이웃 (Hamming distance 가까운 {NGRAM_N}-gram) ───")
    for term in PROBE_TERMS:
        if term not in g2id:
            print(f'\n? "{term}" — 인덱스 없음 (doc_freq < {MIN_NGRAM_DOC_FREQ})')
            continue
        gid = g2id[term]
        sig = sig_packed[gid]
        xored = np.bitwise_xor(sig_packed, sig[None, :])
        dist = np.unpackbits(xored, axis=1).sum(axis=1)
        nearest = np.argpartition(dist, TOP_K_NEIGHBORS + 1)[: TOP_K_NEIGHBORS + 1]
        nearest = sorted(nearest, key=lambda i: dist[i])
        nearest = [i for i in nearest if i != gid][:TOP_K_NEIGHBORS]
        df_term = doc_freq.get(term, 0)
        print(f'\n? "{term}"  (doc_freq={df_term})')
        for i in nearest:
            print(f"    d={int(dist[i]):3d}  doc_freq={doc_freq[id2g[i]]:>6d}  {id2g[i]}")


if __name__ == "__main__":
    main()
