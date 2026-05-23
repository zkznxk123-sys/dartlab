"""RI-VSA v8 — 평가 셋트 (A) 위에서 v3/v6/v7 3 자산 동시 벤치.

목적
----
지금까지 stem 응집 (자기↔자사 d=9) 만 봤지 *검색 품질* 은 측정 X.
[evalSet.py](evalSet.py) 의 12 자연어 쿼리 + 정답 룰로 v3/v6/v7 동시 비교.

핵심
----
v4 (riVsaSearch.py) 의 Python loop sectionHash 빌드는 16 분.
여기선 scipy.sparse matmul 1 회 로 모든 섹션 hash 동시 빌드 (3 variants 병렬):

    M = csr_matrix (n_sec, n_stems)   # token count (or binary) per section
    contextSigned = (n_stems, 256)    # ±1 hash bits, IDF 가중
    sectionAcc = M @ contextSigned    # (n_sec, 256) — 한 방
    sectionHashes = (sectionAcc > 0).pack

비교 변인
--------
- v3: 4 region 도입 전 (blake2b random only, IDF 가중)
- v6: 4 region 도입 (jamo + char Bloom + bigram + random) — baseline 응집 너무 큼
- v7: Tier 2 self-included identity (M.T @ M @ characteristic) — 현재 best stem 응집

기대
----
v7 의 stem 응집 (자기↔자사 d=9) 이 *섹션 검색* recall@k 로 옮겨가나?
v3 vs v7 의 정답 회수율 차이가 진짜 발전인지 아니면 stem 응집은 spurious 인지 판별.

결과 (2026-05-20, 417,201 섹션 × 169,142 stems)
------------------------------------------------
빌드: corpus load 54s + section matrix 868s + matmul/variant 83-95s.

평균 — 12 쿼리 (rcept dedup top-5/10, ground truth = report_nm regex):

| variant | P@5 | P@10 | R@5 | R@10 | MRR |
|---|---|---|---|---|---|
| V3 | 0.10 | 0.08 | 0.00 | 0.00 | 0.10 |
| V6 | 0.02 | 0.02 | 0.00 | 0.00 | 0.04 |
| **V7** | 0.05 | 0.05 | 0.00 | 0.00 | 0.08 |

쿼리별 MRR — 12 중 10 쿼리가 *완전 0*. 신호 있는 쿼리만:
- 배당 지급 (정답 1580): V3 MRR=1.00, V6=0.14, V7=1.00
- 합병 결정 (정답 199): V3=0.25, V6=0.33, V7=0.00

결론 (객관 평가 — v4 주관 평가 부정)
---------------------------------
- ★★★ v4 (riVsaSearch) 의 "75% 정확" 은 *주관 평가 거짓*. 실제 R@5 ≈ 0.
- × V7 의 stem 응집 (자기↔자사 d=9) → sectionHash 검색 정확도 옮겨지지 않음.
- × 오히려 V3 (응집 최저) 가 가장 좋음. V7 의 4 region 응집은 노이즈 흡수만 늘림.
- × 12 쿼리 중 10 개 완전 fail. 정답 셋트 sparse (78~2845 / 53K) 도 영향.

진단 — sectionHash 의 정보 손실
------------------------------
1. **섹션 단위가 너무 큼**. 한 섹션 = 수만 자 → 수천 stem 가중 합. 변별력 있는
   어휘 (차입·전환사채) 가 평균에 묻힘.
2. **쿼리 hash 의 도메인 토큰 부재**. "회사가 돈 빌렸나" 의 bigram (회사,사가,가 돈,...)
   → contextSigned 거쳐도 "차입" 의 의미 어휘 안 깨움.

다음 단계 (재설계)
-----------------
- C (sentenceHash) — 단위 축소 → 변별력 ↑ 검증
- 쿼리 확장 — RI-VSA 동료 stem 으로 "돈 빌렸나" → {차입, 사채, 운영자금} 자동 확장
- 또는 BM25 baseline 측정 — RI-VSA 가 BM25 보다 못하면 트랙 폐기
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import numpy as np
import polars as pl
from evalSet import QUERIES, evaluate, formatReport
from scipy.sparse import csr_matrix

ALLFILINGS_DIR = Path("data/dart/allFilings")
HASH_BYTES = 32
HASH_BITS = 256
NGRAM_NS = (2, 3)
MAX_TOKENS_PER_SECTION = 4000

VARIANTS = ("V3", "V6", "V7")


def tokenizeStems(s: str, cap: int = MAX_TOKENS_PER_SECTION) -> list[str]:
    if not s:
        return []
    out: list[str] = []
    for n in NGRAM_NS:
        if len(s) < n:
            continue
        upto = min(len(s) - n + 1, cap)
        out.extend(s[i : i + n] for i in range(upto))
    return out


def hashToSignedFloat(packed: np.ndarray, *, idf: np.ndarray | None = None) -> np.ndarray:
    """(N, 32) uint8 → (N, 256) ±1 float32, optionally IDF-scaled."""
    bits = np.unpackbits(packed, axis=1).astype(np.int8)  # 0/1
    signed = (bits * 2 - 1).astype(np.float32)
    if idf is not None:
        signed *= idf[:, None]
    return signed


def loadVariant(name: str) -> tuple[np.ndarray, np.ndarray, dict[str, int]]:
    """variant 자산 로드 → (contextSigned IDF-가중, df, g2id)."""
    d = Path(f"data/_scratch_fm/riVsa{name}")
    packed = np.load(d / "contextHash.npy")
    df = np.load(d / "df.npy")
    stems = json.loads((d / "stems.json").read_text(encoding="utf-8"))
    g2id = {s: i for i, s in enumerate(stems)}
    idf = np.log(df.max() / np.maximum(df, 1.0)).astype(np.float32)
    contextSigned = hashToSignedFloat(packed, idf=idf)
    return contextSigned, df, g2id


def buildSectionMatrix(contents: list[str], g2id: dict[str, int]) -> csr_matrix:
    """섹션 × stem CSR (binary — 토큰 등장 = 1). 같은 g2id 로 모든 variant 공통."""
    indptr = [0]
    indices: list[int] = []
    for s in contents:
        ids = set()
        for tok in tokenizeStems(s):
            gid = g2id.get(tok)
            if gid is not None:
                ids.add(gid)
        indices.extend(ids)
        indptr.append(len(indices))
    data = np.ones(len(indices), dtype=np.float32)
    n_sec = len(contents)
    n_stems = len(g2id)
    return csr_matrix((data, indices, indptr), shape=(n_sec, n_stems))


def buildSectionHashes(M: csr_matrix, contextSigned: np.ndarray) -> np.ndarray:
    """sparse matmul 1 회 — (n_sec, 256) → packed uint8 (n_sec, 32)."""
    acc = (M @ contextSigned).astype(np.float32)  # (n_sec, 256)
    bits = (acc > 0).astype(np.uint8)
    return np.packbits(bits, axis=1)


def buildQueryHashFn(g2id: dict[str, int], contextSigned: np.ndarray):
    def queryHash(q: str) -> np.ndarray:
        toks = tokenizeStems(q, cap=200)
        ids = [g2id[t] for t in toks if t in g2id]
        if not ids:
            return np.zeros(HASH_BYTES, dtype=np.uint8)
        ids = np.asarray(ids, dtype=np.int32)
        acc = contextSigned[ids].sum(axis=0)
        bits = (acc > 0).astype(np.uint8)
        return np.packbits(bits)

    return queryHash


def main() -> None:
    print("=" * 72)
    print("RI-VSA v8 — 평가 셋트 위 v3/v6/v7 3 자산 동시 벤치")
    print("=" * 72)

    # ── 1. corpus 로드 (한 번) ──
    t0 = time.perf_counter()
    files = sorted(p for p in ALLFILINGS_DIR.glob("2026*.parquet") if "_meta" not in p.name)
    parts = []
    for f in files:
        parts.append(
            pl.read_parquet(
                f,
                columns=["rcept_no", "report_nm", "section_content"],
            ).filter(pl.col("section_content").is_not_null())
        )
    sections_df = pl.concat(parts)
    n_sec = sections_df.height
    contents = sections_df["section_content"].to_list()
    report_nms = sections_df["report_nm"].to_list()
    rcept_nos = sections_df["rcept_no"].to_list()
    print(f"[corpus] {len(files)} 일치 → 섹션 {n_sec:,} | {time.perf_counter() - t0:.1f}s")

    # ── 2. 모든 variant 가 같은 stems.json 공유한다고 가정 (v3=v6=v7 모두 169142 동일 확인) ──
    # → section-matrix 는 한 번만 빌드. variant 별 contextSigned 만 교체.
    _, _, g2id0 = loadVariant("V3")
    t0 = time.perf_counter()
    M = buildSectionMatrix(contents, g2id0)
    print(f"[matrix] M = {n_sec:,} × {len(g2id0):,} | nnz={M.nnz:,} | {time.perf_counter() - t0:.1f}s")

    # ── 3. variant 별 sectionHash 빌드 + 평가 ──
    all_scores: dict[str, dict[str, dict[str, float]]] = {}
    for variant in VARIANTS:
        print()
        print(f"─── {variant} ───")
        t0 = time.perf_counter()
        contextSigned, _df, g2id_v = loadVariant(variant)
        # g2id 동일 가정. (체크)
        if list(g2id_v.items())[:3] != list(g2id0.items())[:3]:
            raise RuntimeError(f"{variant} g2id mismatch — re-build matrix needed")
        section_hashes = buildSectionHashes(M, contextSigned)
        build_t = time.perf_counter() - t0
        print(f"  [build] sectionHashes {section_hashes.nbytes / 1e6:.1f} MB | matmul {build_t:.1f}s")

        t0 = time.perf_counter()
        queryHash = buildQueryHashFn(g2id_v, contextSigned)
        scores = evaluate(section_hashes, queryHash, report_nms, rcept_nos)
        eval_t = time.perf_counter() - t0
        print(f"  [eval] 12 쿼리 | {eval_t:.1f}s")
        print()
        print(formatReport(scores))
        all_scores[variant] = scores

    # ── 4. variant 간 비교 표 ──
    print()
    print("=" * 72)
    print("  variant 비교 — 평균 점수")
    print("=" * 72)
    print(f"{'variant':<8} {'P@5':>6} {'P@10':>6} {'R@5':>6} {'R@10':>6} {'MRR':>6}")
    print("-" * 50)
    for variant, sc in all_scores.items():
        valid = [s for s in sc.values() if not np.isnan(s["precision@5"])]
        p5 = np.mean([s["precision@5"] for s in valid])
        p10 = np.mean([s["precision@10"] for s in valid])
        r5 = np.mean([s["recall@5"] for s in valid])
        r10 = np.mean([s["recall@10"] for s in valid])
        mrr = np.mean([s["mrr"] for s in valid])
        print(f"{variant:<8} {p5:>6.2f} {p10:>6.2f} {r5:>6.2f} {r10:>6.2f} {mrr:>6.2f}")

    # ── 5. 쿼리별 variant 비교 ──
    print()
    print("─── 쿼리별 MRR (variant 차이) ───")
    print(f"{'쿼리':<22} {'V3':>6} {'V6':>6} {'V7':>6}")
    print("-" * 48)
    for q in QUERIES:
        row = [all_scores[v][q.text]["mrr"] for v in VARIANTS]
        print(f"{q.text:<22} {row[0]:>6.2f} {row[1]:>6.2f} {row[2]:>6.2f}")


if __name__ == "__main__":
    main()
