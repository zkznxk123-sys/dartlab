"""RI-VSA v14 — Spectral Graph Laplacian Eigenmap (학습 0, 수학 기반).

배경 — 사용자 요구
----------------
v1~v13 통계 기반 (단봉 정규분포, PPMI) 모두 *변별력 약함*. 사용자가
*언어 모델 흉내낼 수학적 기반* 요구.

해답: **Spectral Graph Theory + Laplacian Eigenmap**
- 학습 0 (eigendecomposition deterministic)
- 의미 cluster 자동 분리 (Cheeger inequality 수학 보장)
- 합성성, 분포 의미, 유추 모두 매핑
- 메모리 cheap (k=32 dim per stem)

알고리즘
--------
1. corpus → stem-stem co-occurrence sparse graph G
   nodes = stems (df ≥ 5 한글 시작)
   edges = (s, t) with weight = PPMI(s, t)

2. Normalized Laplacian:
   D = diag(degree)
   L_sym = I − D^(-1/2) A D^(-1/2)

3. Eigendecomposition (Lanczos, sparse):
   L_sym v_k = λ_k v_k, λ_1=0 ≤ λ_2 ≤ ... ≤ λ_n
   top k=32 smallest non-zero eigenvalues → eigenvectors

4. stem 좌표:
   stem s_i → (v_2[i], v_3[i], ..., v_33[i]) ∈ R^32

5. 문장 sig:
   sentence = Σ over stems s in sentence of stem_coord[s]
   (또는 IDF 가중)

6. 매칭 = cosine similarity (32-dim)

수학적 보장
----------
- Cheeger inequality: λ_2 작음 → 그래프 cluster 분리 명확
- Spectral gap: λ_{k+1} − λ_k 큰 곳 = 자연 cluster 개수
- Eigenvectors = best k-dim embedding (preserve graph distance)

결과 (작성 후 채움)
------------------
"""

from __future__ import annotations

import re
import time
from collections import defaultdict
from pathlib import Path

import numpy as np
import polars as pl
from evalSet import QUERIES
from scipy.sparse import csr_matrix, diags, identity
from scipy.sparse.linalg import eigsh

ALLFILINGS_DIR = Path("data/dart/allFilings")
K_EMBED = 32  # spectral embedding 차원
WINDOW = 5
MIN_DF = 5
HANGUL_START = 0xAC00
HANGUL_END = 0xD7A3
MAX_SECTION_CHARS = 30_000
MAX_SENTS_PER_SECTION = 200
MIN_SENTENCE_LEN = 8
MAX_TOKENS_PER_SENTENCE = 40
N_SAMPLE_SENTENCES = 200_000

SENT_SPLIT = re.compile(r"(?<=[다음음니다요죠임함])[\.\?!]\s+|[\.\?!]\s+|\n+|;\s+")


def splitSentences(text: str) -> list[str]:
    if not text:
        return []
    if len(text) > MAX_SECTION_CHARS:
        text = text[:MAX_SECTION_CHARS]
    parts = SENT_SPLIT.split(text)
    out: list[str] = []
    for p in parts:
        p = p.strip()
        if len(p) >= MIN_SENTENCE_LEN:
            out.append(p)
            if len(out) >= MAX_SENTS_PER_SECTION:
                break
    return out


def hangulStart(token: str) -> bool:
    if not token:
        return False
    code = ord(token[0])
    return HANGUL_START <= code <= HANGUL_END


def main() -> None:
    print("=" * 72)
    print(f"RI-VSA v14 — Spectral Graph Laplacian Eigenmap (k={K_EMBED} dim)")
    print("=" * 72)

    # ── 1. corpus load ──
    t0 = time.perf_counter()
    files = sorted(p for p in ALLFILINGS_DIR.glob("2026*.parquet") if "_meta" not in p.name)
    sentences: list[str] = []
    sent_rcept: list[str] = []
    sent_report_nm: list[str] = []
    sent_section_title: list[str] = []
    sentence_tokens_list: list[list[str]] = []
    sample_full = False
    for f in files:
        df = (
            pl.read_parquet(
                f,
                columns=["rcept_no", "report_nm", "section_title", "section_content"],
            )
            .filter(pl.col("section_content").is_not_null())
            .with_columns(pl.col("section_content").str.slice(0, MAX_SECTION_CHARS))
        )
        for row in df.iter_rows():
            r, rn, stitle, txt = row
            for sent in splitSentences(txt):
                sentences.append(sent)
                sent_rcept.append(r)
                sent_report_nm.append(rn or "")
                sent_section_title.append(stitle or "")
                tokens = sent.split()[:MAX_TOKENS_PER_SENTENCE]
                sentence_tokens_list.append(tokens)
                if len(sentences) >= N_SAMPLE_SENTENCES:
                    sample_full = True
                    break
            if sample_full:
                break
        del df
        if sample_full:
            break
    n_sent = len(sentences)
    print(f"[corpus] 문장 {n_sent:,} | {time.perf_counter() - t0:.1f}s")

    # ── 2. df + filter ──
    t0 = time.perf_counter()
    stem_df: dict[str, int] = defaultdict(int)
    for tokens in sentence_tokens_list:
        for tok in set(tokens):
            stem_df[tok] += 1
    stem2id: dict[str, int] = {}
    stems_kept: list[str] = []
    for s, c in stem_df.items():
        if c < MIN_DF or not hangulStart(s):
            continue
        stem2id[s] = len(stems_kept)
        stems_kept.append(s)
    n_stems = len(stems_kept)
    stem_df_arr = np.asarray([stem_df[s] for s in stems_kept], dtype=np.float64)
    idf = np.log(n_sent / np.maximum(stem_df_arr, 1.0)).astype(np.float32)
    print(f"[filter] kept stems {n_stems:,} (df≥{MIN_DF}, 한글) | {time.perf_counter() - t0:.1f}s")

    # ── 3. stem-stem cooc (sparse window) ──
    t0 = time.perf_counter()
    rows: list[int] = []
    cols: list[int] = []
    for tokens in sentence_tokens_list:
        ids = [stem2id[t] for t in tokens if t in stem2id]
        n = len(ids)
        for i in range(n):
            for j in range(i + 1, min(i + WINDOW + 1, n)):
                rows.append(ids[i])
                cols.append(ids[j])
    # symmetric
    rows_sym = rows + cols
    cols_sym = cols + rows
    data = np.ones(len(rows_sym), dtype=np.float32)
    cooc = csr_matrix((data, (rows_sym, cols_sym)), shape=(n_stems, n_stems))
    cooc.sum_duplicates()
    print(f"[cooc] nnz={cooc.nnz:,} ({cooc.data.nbytes / 1e6:.1f} MB) | {time.perf_counter() - t0:.1f}s")

    # ── 4. PPMI 가중 (sparse) ──
    t0 = time.perf_counter()
    row_sum = np.asarray(cooc.sum(axis=1)).flatten().astype(np.float32) + 1e-9
    total = row_sum.sum()
    cooc_coo = cooc.tocoo()
    pmi_vals = np.log(
        np.maximum(
            cooc_coo.data * total / (row_sum[cooc_coo.row] * row_sum[cooc_coo.col]),
            1e-12,
        )
    )
    ppmi_mask = pmi_vals > 0
    ppmi_data = pmi_vals[ppmi_mask].astype(np.float32)
    A = csr_matrix(
        (
            ppmi_data,
            (cooc_coo.row[ppmi_mask], cooc_coo.col[ppmi_mask]),
        ),
        shape=(n_stems, n_stems),
    )
    print(f"[ppmi] nnz={A.nnz:,} ({A.data.nbytes / 1e6:.1f} MB) | {time.perf_counter() - t0:.1f}s")

    # ── 5. Normalized Laplacian L_sym = I − D^(-1/2) A D^(-1/2) ──
    t0 = time.perf_counter()
    degrees = np.asarray(A.sum(axis=1)).flatten()
    degrees = np.maximum(degrees, 1e-9)
    D_inv_sqrt = diags(1.0 / np.sqrt(degrees))
    L_sym = identity(n_stems) - D_inv_sqrt @ A @ D_inv_sqrt
    print(f"[laplacian] L_sym shape {L_sym.shape}, nnz {L_sym.nnz:,} | {time.perf_counter() - t0:.1f}s")

    # ── 6. Top-k smallest eigenvalues (Lanczos) ──
    t0 = time.perf_counter()
    # eigsh smallest 는 's M' 또는 shift-invert (sigma=0) 둘 다 가능
    # k+1 — eigenvalue 0 (trivial) 포함 후 v_2..v_{k+1} 사용
    # which='SM' 은 느림 → shift-invert 더 빠름
    try:
        eigenvalues, eigenvectors = eigsh(L_sym, k=K_EMBED + 1, sigma=0, which="LM", tol=1e-4)
    except Exception as e:
        print(f"  shift-invert fail ({e}), falling back to which='SM'")
        eigenvalues, eigenvectors = eigsh(L_sym, k=K_EMBED + 1, which="SM", tol=1e-4)
    # 오름차순 정렬
    order = np.argsort(eigenvalues)
    eigenvalues = eigenvalues[order]
    eigenvectors = eigenvectors[:, order]
    # v_1 (trivial constant) drop → v_2..v_{k+1}
    stem_coords = eigenvectors[:, 1 : K_EMBED + 1].astype(np.float32)  # (n_stems, K)
    print(
        f"[eigen] eigenvalues[0:5]={eigenvalues[:5]} | "
        f"stem_coords {stem_coords.nbytes / 1e6:.1f} MB | "
        f"{time.perf_counter() - t0:.1f}s"
    )

    # ── 7. 문장 시그니처 (stems 좌표 IDF-가중 평균) ──
    t0 = time.perf_counter()
    sentence_coords = np.zeros((n_sent, K_EMBED), dtype=np.float32)
    for sid, tokens in enumerate(sentence_tokens_list):
        ids = [stem2id[t] for t in tokens if t in stem2id]
        if not ids:
            continue
        ids_arr = np.asarray(ids, dtype=np.int32)
        ws = idf[ids_arr]
        if ws.sum() < 1e-9:
            continue
        sentence_coords[sid] = (stem_coords[ids_arr] * ws[:, None]).sum(axis=0) / ws.sum()
    # L2 정규화
    norms = np.linalg.norm(sentence_coords, axis=1, keepdims=True) + 1e-9
    sentence_coords_n = sentence_coords / norms
    print(f"[sent] sentence_coords {sentence_coords.nbytes / 1e6:.1f} MB | {time.perf_counter() - t0:.1f}s")

    # ── 8. 검색 함수 ──
    def queryCoord(q: str) -> np.ndarray:
        tokens = q.split()
        ids = [stem2id[t] for t in tokens if t in stem2id]
        if not ids:
            return np.zeros(K_EMBED, dtype=np.float32)
        ids_arr = np.asarray(ids, dtype=np.int32)
        ws = idf[ids_arr]
        if ws.sum() < 1e-9:
            return np.zeros(K_EMBED, dtype=np.float32)
        q_coord = (stem_coords[ids_arr] * ws[:, None]).sum(axis=0) / ws.sum()
        n = np.linalg.norm(q_coord) + 1e-9
        return q_coord / n

    def search(q: str, top_k: int = 30) -> tuple[np.ndarray, np.ndarray]:
        qc = queryCoord(q)
        cos = sentence_coords_n @ qc  # (n_sent,)
        k = min(top_k, n_sent)
        part = np.argpartition(-cos, k - 1)[:k]
        order = part[np.argsort(-cos[part])]
        return order, cos[order]

    # ── 9. 평가 (report_nm OR section_title) ──
    print()
    print("─── 평가 셋트 (12 쿼리, cosine, rcept dedup) ───")
    print(f"{'쿼리':<22} {'#정답':>6} {'P@5':>6} {'P@10':>6} {'R@5':>6} {'R@10':>6} {'MRR':>6}")
    print("-" * 70)
    p5s, p10s, r5s, r10s, mrrs = [], [], [], [], []
    for q in QUERIES:
        pat = q.relevance
        rel_by_sent = np.fromiter(
            (bool(pat.search(sent_report_nm[i])) or bool(pat.search(sent_section_title[i])) for i in range(n_sent)),
            dtype=bool,
            count=n_sent,
        )
        rcept_first: dict[str, int] = {}
        for i, r in enumerate(sent_rcept):
            rcept_first.setdefault(r, i)
        rcept_rel: dict[str, bool] = {}
        for i, r in enumerate(sent_rcept):
            if rel_by_sent[i]:
                rcept_rel[r] = True
        rcepts = list(rcept_first.keys())
        total_rel = sum(1 for r in rcepts if rcept_rel.get(r, False))
        if total_rel == 0:
            print(f"{q.text:<22} {0:>6d} {'nan':>6} {'nan':>6} {'nan':>6} {'nan':>6} {'nan':>6}")
            continue
        order, _ = search(q.text, top_k=150)
        seen = set()
        hit_rel = []
        for sid in order:
            r = sent_rcept[int(sid)]
            if r in seen:
                continue
            seen.add(r)
            hit_rel.append(rcept_rel.get(r, False))
            if len(hit_rel) >= 10:
                break
        p5 = sum(hit_rel[:5]) / 5
        p10 = sum(hit_rel[:10]) / 10
        r5 = sum(hit_rel[:5]) / total_rel
        r10 = sum(hit_rel[:10]) / total_rel
        rr = 0.0
        for rank, h in enumerate(hit_rel, 1):
            if h:
                rr = 1.0 / rank
                break
        p5s.append(p5)
        p10s.append(p10)
        r5s.append(r5)
        r10s.append(r10)
        mrrs.append(rr)
        print(f"{q.text:<22} {total_rel:>6d} {p5:>6.2f} {p10:>6.2f} {r5:>6.2f} {r10:>6.2f} {rr:>6.2f}")
    print("-" * 70)
    if p5s:
        print(
            f"{'평균':<22} {'':>6} {np.mean(p5s):>6.2f} {np.mean(p10s):>6.2f} "
            f"{np.mean(r5s):>6.2f} {np.mean(r10s):>6.2f} {np.mean(mrrs):>6.2f}"
        )

    # ── 10. snippet ──
    print()
    print("─── snippet (top 5) ───")
    SHOW = [
        "회사가 돈 빌렸나",
        "자사주 사들였나",
        "공장 짓는 회사",
        "유상증자한 회사",
        "주주총회 결과",
        "전환사채 발행",
        "대표이사 누가 바뀌었나",
    ]
    for q in SHOW:
        order, scores = search(q, top_k=30)
        seen = set()
        print(f'\n❓ "{q}"')
        shown = 0
        for sid, sc in zip(order, scores):
            r = sent_rcept[int(sid)]
            if r in seen:
                continue
            seen.add(r)
            snippet = sentences[int(sid)][:100].replace("\n", " ")
            stitle = sent_section_title[int(sid)][:20] if sent_section_title[int(sid)] else ""
            print(f"    cos={sc:.3f}  [{sent_report_nm[int(sid)][:22]:22s}][{stitle:<20s}]  {snippet}")
            shown += 1
            if shown >= 5:
                break


if __name__ == "__main__":
    main()
