"""RI-VSA v12 — 2D 평면 (X=UTF 수평선, Y=corpus 자연 끌어당김). 3 버전 동시.

배경 — 사용자 closed-form 발상
----------------------------
"stem 자체는 자연 위치 (X). 주변 stems 가 의미를 만든다. 자연적 밀어내기·연결·
끌어당김으로 의미에 연속성을 줘서 2D 완성":

    Y_i = Σ_j PPMI(i, j) × X_j  /  Σ_j PPMI(i, j)

= stem i 의 Y = 주변 stems 의 X 좌표 가중 평균. *force 평형의 closed form*,
학습·반복 X, 벡터 X. 같은 주변 (같은 의미) → 같은 Y → 자연 끌어당김.

3 버전 비교
----------
| 버전 | Y 정의 | 매칭 |
|---|---|---|
| v12  | Σ PPMI × X / Σ PPMI (closed form) | 2D histogram (32×16) Hamming |
| v12b | IDF × (1 − entropy(PPMI dist)) — specificity | 2D histogram Hamming |
| v12c | stem 의 1D 주변 X 분포 (smear, Y 없음) | distribution cosine |

공통 corpus 빌드:
- whitespace tokens
- stem-stem co-occurrence (window=5, IDF 가중 가능)
- df < MIN_DF 인 stem 제외 (noise 차단)

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
from scipy.sparse import csr_matrix, lil_matrix

ALLFILINGS_DIR = Path("data/dart/allFilings")
HANGUL_START = 0xAC00
HANGUL_END = 0xD7A3
HANGUL_RANGE = HANGUL_END - HANGUL_START + 1
WINDOW = 5  # in-sentence pair window (whitespace token 단위)
MIN_DF = 5  # stem df threshold (noise cut)
MAX_SECTION_CHARS = 30_000
MAX_SENTS_PER_SECTION = 200
MIN_SENTENCE_LEN = 8
MAX_TOKENS_PER_SENTENCE = 40
N_SAMPLE_SENTENCES = 1_000_000

# 2D histogram bins
X_BINS = 32
Y_BINS = 16
HIST_CELLS = X_BINS * Y_BINS  # 512
SIG_BYTES = HIST_CELLS // 8  # 64

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


def stemXCoord(stem: str) -> float | None:
    """stem 의 첫 한글 글자 → UTF / 한글범위 → 0~1. 비한글 시작이면 None."""
    if not stem:
        return None
    code = ord(stem[0])
    if HANGUL_START <= code <= HANGUL_END:
        return (code - HANGUL_START) / HANGUL_RANGE
    return None


def main() -> None:
    print("=" * 72)
    print("RI-VSA v12 — 2D 평면 (X=UTF, Y=closed-form 끌어당김) + 3 버전 비교")
    print("=" * 72)

    # ── 1. corpus load ──
    t0 = time.perf_counter()
    files = sorted(p for p in ALLFILINGS_DIR.glob("2026*.parquet") if "_meta" not in p.name)
    sentences: list[str] = []
    sent_rcept: list[str] = []
    sent_report_nm: list[str] = []
    sentence_tokens_list: list[list[str]] = []
    sample_full = False
    for f in files:
        df = (
            pl.read_parquet(
                f,
                columns=["rcept_no", "report_nm", "section_content"],
            )
            .filter(pl.col("section_content").is_not_null())
            .with_columns(pl.col("section_content").str.slice(0, MAX_SECTION_CHARS))
        )
        for row in df.iter_rows():
            r, rn, txt = row
            for sent in splitSentences(txt):
                sentences.append(sent)
                sent_rcept.append(r)
                sent_report_nm.append(rn)
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

    # ── 2. stem 사전 + df ──
    t0 = time.perf_counter()
    stem_df: dict[str, int] = defaultdict(int)
    for tokens in sentence_tokens_list:
        for tok in set(tokens):
            stem_df[tok] += 1
    print(f"[stems] unique whitespace tokens {len(stem_df):,} | {time.perf_counter() - t0:.1f}s")

    # df ≥ MIN_DF + X 좌표 (한글) 있는 stem 만 유지
    t0 = time.perf_counter()
    stem2id: dict[str, int] = {}
    stems_kept: list[str] = []
    stem_x_list: list[float] = []
    for s, df_count in stem_df.items():
        if df_count < MIN_DF:
            continue
        x = stemXCoord(s)
        if x is None:
            continue
        stem2id[s] = len(stems_kept)
        stems_kept.append(s)
        stem_x_list.append(x)
    n_stems = len(stems_kept)
    stem_X = np.asarray(stem_x_list, dtype=np.float32)
    stem_DF = np.asarray([stem_df[s] for s in stems_kept], dtype=np.float64)
    print(f"[filter] kept stems {n_stems:,} (df≥{MIN_DF}, 한글 시작) | {time.perf_counter() - t0:.1f}s")

    # ── 3. stem-stem co-occurrence (sparse) ──
    t0 = time.perf_counter()
    rows: list[int] = []
    cols: list[int] = []
    # 한 문장 안 window pair → cooc
    for tokens in sentence_tokens_list:
        ids = [stem2id[t] for t in tokens if t in stem2id]
        n = len(ids)
        for i in range(n):
            for j in range(i + 1, min(i + WINDOW + 1, n)):
                rows.append(ids[i])
                cols.append(ids[j])
    # 대칭
    rows_sym = rows + cols
    cols_sym = cols + rows
    data = np.ones(len(rows_sym), dtype=np.float32)
    cooc = csr_matrix((data, (rows_sym, cols_sym)), shape=(n_stems, n_stems))
    cooc.sum_duplicates()
    print(f"[cooc] nnz={cooc.nnz:,} | {cooc.data.nbytes / 1e6:.1f} MB | {time.perf_counter() - t0:.1f}s")

    # ── 4. PPMI (sparse) ──
    t0 = time.perf_counter()
    row_sum = np.asarray(cooc.sum(axis=1)).flatten().astype(np.float32) + 1e-9
    total = row_sum.sum()
    # PMI = log( cooc * total / (row_sum[i] * row_sum[j]) )
    cooc_coo = cooc.tocoo()
    pmi_data = np.log(
        np.maximum(
            cooc_coo.data * total / (row_sum[cooc_coo.row] * row_sum[cooc_coo.col]),
            1e-12,
        )
    )
    ppmi_mask = pmi_data > 0
    ppmi_data = pmi_data[ppmi_mask]
    ppmi_row = cooc_coo.row[ppmi_mask]
    ppmi_col = cooc_coo.col[ppmi_mask]
    ppmi = csr_matrix(
        (ppmi_data.astype(np.float32), (ppmi_row, ppmi_col)),
        shape=(n_stems, n_stems),
    )
    print(f"[ppmi] nnz={ppmi.nnz:,} | {ppmi.data.nbytes / 1e6:.1f} MB | {time.perf_counter() - t0:.1f}s")

    # ── 5. 3 버전 Y 좌표 계산 ──
    # v12: Y_i = Σ_j PPMI(i,j) × X_j / Σ_j PPMI(i,j)
    t0 = time.perf_counter()
    ppmi_row_sum = np.asarray(ppmi.sum(axis=1)).flatten() + 1e-9
    weighted_X = ppmi @ stem_X  # (n_stems,)
    Y_v12 = weighted_X / ppmi_row_sum  # closed-form 끌어당김
    Y_v12 = np.clip(Y_v12, 0, 1)
    print(f"[Y_v12] closed-form 끌어당김 | {time.perf_counter() - t0:.1f}s")

    # v12b: Y = IDF × (1 - entropy_norm)
    t0 = time.perf_counter()
    idf = np.log(n_sent / np.maximum(stem_DF, 1.0)).astype(np.float32)
    idf_norm = (idf - idf.min()) / max(idf.max() - idf.min(), 1e-9)
    # entropy of PPMI row distribution per stem
    entropy = np.zeros(n_stems, dtype=np.float32)
    ppmi_csr = ppmi
    for i in range(n_stems):
        start, end = ppmi_csr.indptr[i], ppmi_csr.indptr[i + 1]
        row_vals = ppmi_csr.data[start:end]
        if len(row_vals) < 2:
            entropy[i] = 0
            continue
        p = row_vals / max(row_vals.sum(), 1e-12)
        h = -(p * np.log(p + 1e-12)).sum()
        max_h = np.log(len(p))
        entropy[i] = h / max(max_h, 1e-9)
    Y_v12b = idf_norm * (1 - entropy)
    Y_v12b = np.clip(Y_v12b, 0, 1)
    print(f"[Y_v12b] IDF × specificity | {time.perf_counter() - t0:.1f}s")

    # v12c: stem 의 1D 주변 X 분포 (32-bin histogram)
    t0 = time.perf_counter()
    # 각 stem i 의 주변 분포: ppmi row 에서 cols 의 X 좌표 → 32 bin histogram
    smear_v12c = np.zeros((n_stems, X_BINS), dtype=np.float32)
    for i in range(n_stems):
        start, end = ppmi.indptr[i], ppmi.indptr[i + 1]
        if start == end:
            continue
        cols_i = ppmi.indices[start:end]
        vals_i = ppmi.data[start:end]
        x_neighbors = stem_X[cols_i]
        bins = (x_neighbors * X_BINS).clip(0, X_BINS - 1).astype(np.int32)
        np.add.at(smear_v12c[i], bins, vals_i)
        # 정규화 (확률 분포)
        s = smear_v12c[i].sum()
        if s > 0:
            smear_v12c[i] /= s
    print(f"[smear_v12c] {smear_v12c.nbytes / 1e6:.1f} MB | {time.perf_counter() - t0:.1f}s")

    # ── 6. 문장 시그니처 빌드 (3 버전) ──
    # v12, v12b: 2D histogram (X_BINS × Y_BINS) sign-pack 64 byte
    # v12c: smear sum → 32-dim float → sign-pack 4 byte (or cosine)
    def build_sentence_sigs_2d(Y: np.ndarray) -> np.ndarray:
        sigs_packed = np.zeros((n_sent, SIG_BYTES), dtype=np.uint8)
        # global threshold (median per cell) — 모든 문장 동일 기준
        # 일단 0 기준으로 (각 stem hot 한 cell 만 1)
        for sid, tokens in enumerate(sentence_tokens_list):
            ids = [stem2id[t] for t in tokens if t in stem2id]
            if not ids:
                continue
            ids = np.asarray(ids, dtype=np.int32)
            xb = (stem_X[ids] * X_BINS).clip(0, X_BINS - 1).astype(np.int32)
            yb = (Y[ids] * Y_BINS).clip(0, Y_BINS - 1).astype(np.int32)
            hist = np.zeros(HIST_CELLS, dtype=np.float32)
            np.add.at(hist, yb * X_BINS + xb, 1.0)
            # threshold = mean of hist
            thr = hist.mean()
            bits = (hist > thr).astype(np.uint8)
            sigs_packed[sid] = np.packbits(bits)
        return sigs_packed

    def build_sentence_smear_1d() -> np.ndarray:
        """v12c — 문장 = 그 안 stems 의 smear 합 (32-dim)."""
        sigs = np.zeros((n_sent, X_BINS), dtype=np.float32)
        for sid, tokens in enumerate(sentence_tokens_list):
            ids = [stem2id[t] for t in tokens if t in stem2id]
            if not ids:
                continue
            sigs[sid] = smear_v12c[ids].sum(axis=0)
            s = sigs[sid].sum()
            if s > 0:
                sigs[sid] /= s
        return sigs

    t0 = time.perf_counter()
    sigs_v12 = build_sentence_sigs_2d(Y_v12)
    print(f"[sigs_v12] {sigs_v12.nbytes / 1e6:.1f} MB | {time.perf_counter() - t0:.1f}s")

    t0 = time.perf_counter()
    sigs_v12b = build_sentence_sigs_2d(Y_v12b)
    print(f"[sigs_v12b] {sigs_v12b.nbytes / 1e6:.1f} MB | {time.perf_counter() - t0:.1f}s")

    t0 = time.perf_counter()
    sigs_v12c = build_sentence_smear_1d()
    print(f"[sigs_v12c] {sigs_v12c.nbytes / 1e6:.1f} MB | {time.perf_counter() - t0:.1f}s")

    # ── 7. 쿼리 함수 ──
    def query_sig_2d(q: str, Y: np.ndarray) -> np.ndarray:
        tokens = q.split()
        ids = [stem2id[t] for t in tokens if t in stem2id]
        if not ids:
            return np.zeros(SIG_BYTES, dtype=np.uint8)
        ids = np.asarray(ids, dtype=np.int32)
        xb = (stem_X[ids] * X_BINS).clip(0, X_BINS - 1).astype(np.int32)
        yb = (Y[ids] * Y_BINS).clip(0, Y_BINS - 1).astype(np.int32)
        hist = np.zeros(HIST_CELLS, dtype=np.float32)
        np.add.at(hist, yb * X_BINS + xb, 1.0)
        thr = hist.mean()
        bits = (hist > thr).astype(np.uint8)
        return np.packbits(bits)

    def query_sig_smear(q: str) -> np.ndarray:
        tokens = q.split()
        ids = [stem2id[t] for t in tokens if t in stem2id]
        if not ids:
            return np.zeros(X_BINS, dtype=np.float32)
        sig = smear_v12c[ids].sum(axis=0)
        s = sig.sum()
        if s > 0:
            sig /= s
        return sig

    def search_hamming(sigs: np.ndarray, qh: np.ndarray, top_k: int = 150) -> np.ndarray:
        xored = np.bitwise_xor(sigs, qh[None, :])
        dist = np.unpackbits(xored, axis=1).sum(axis=1)
        k = min(top_k, n_sent)
        part = np.argpartition(dist, k - 1)[:k]
        return part[np.argsort(dist[part])]

    def search_cosine(sigs: np.ndarray, qsig: np.ndarray, top_k: int = 150) -> np.ndarray:
        qn = np.linalg.norm(qsig) + 1e-12
        sn = np.linalg.norm(sigs, axis=1) + 1e-12
        cos = (sigs @ qsig) / (sn * qn)
        k = min(top_k, n_sent)
        part = np.argpartition(-cos, k - 1)[:k]
        return part[np.argsort(-cos[part])]

    # ── 8. 평가 (3 버전) ──
    def evaluate(name: str, get_order):
        print()
        print(f"─── {name} ───")
        print(f"{'쿼리':<22} {'#정답':>6} {'P@5':>6} {'P@10':>6} {'R@5':>6} {'R@10':>6} {'MRR':>6}")
        print("-" * 70)
        p5s, p10s, r5s, r10s, mrrs = [], [], [], [], []
        for q in QUERIES:
            pat = q.relevance
            rel_by_sent = np.fromiter(
                (bool(pat.search(r or "")) for r in sent_report_nm),
                dtype=bool,
                count=n_sent,
            )
            rcept_first: dict[str, int] = {}
            for i, r in enumerate(sent_rcept):
                rcept_first.setdefault(r, i)
            rcepts = list(rcept_first.keys())
            total_rel = sum(1 for r in rcepts if rel_by_sent[rcept_first[r]])
            if total_rel == 0:
                print(f"{q.text:<22} {0:>6d} {'nan':>6} {'nan':>6} {'nan':>6} {'nan':>6} {'nan':>6}")
                continue
            order = get_order(q.text)
            seen = set()
            hit_rel = []
            for sid in order:
                r = sent_rcept[int(sid)]
                if r in seen:
                    continue
                seen.add(r)
                hit_rel.append(bool(rel_by_sent[int(sid)]))
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
        return (
            np.mean(p5s) if p5s else 0,
            np.mean(mrrs) if mrrs else 0,
        )

    s_v12 = evaluate(
        "v12 (closed-form 끌어당김)",
        lambda q: search_hamming(sigs_v12, query_sig_2d(q, Y_v12)),
    )
    s_v12b = evaluate(
        "v12b (IDF × specificity)",
        lambda q: search_hamming(sigs_v12b, query_sig_2d(q, Y_v12b)),
    )
    s_v12c = evaluate(
        "v12c (1D stem smear cosine)",
        lambda q: search_cosine(sigs_v12c, query_sig_smear(q)),
    )

    # ── 9. 비교 표 ──
    print()
    print("=" * 72)
    print("  3 버전 비교 — 평균 점수")
    print("=" * 72)
    print(f"{'버전':<30} {'P@5':>6} {'MRR':>6}")
    print("-" * 50)
    for name, sc in [
        ("v12 (closed-form 끌어당김)", s_v12),
        ("v12b (IDF × specificity)", s_v12b),
        ("v12c (1D stem smear)", s_v12c),
    ]:
        print(f"{name:<30} {sc[0]:>6.2f} {sc[1]:>6.2f}")

    # ── 10. 최우수 버전의 snippet ──
    best_idx = int(np.argmax([s_v12[1], s_v12b[1], s_v12c[1]]))
    best_name = ["v12", "v12b", "v12c"][best_idx]
    print()
    print(f"─── snippet 데모 ({best_name} 최우수) ───")
    SHOW = [
        "회사가 돈 빌렸나",
        "자사주 사들였나",
        "공장 짓는 회사",
        "유상증자한 회사",
        "주주총회 결과",
    ]
    if best_idx == 0:
        get_order = lambda q: search_hamming(sigs_v12, query_sig_2d(q, Y_v12), top_k=30)  # noqa: E731
    elif best_idx == 1:
        get_order = lambda q: search_hamming(sigs_v12b, query_sig_2d(q, Y_v12b), top_k=30)  # noqa: E731
    else:
        get_order = lambda q: search_cosine(sigs_v12c, query_sig_smear(q), top_k=30)  # noqa: E731
    for q in SHOW:
        order = get_order(q)
        seen = set()
        print(f'\n❓ "{q}"')
        shown = 0
        for sid in order:
            r = sent_rcept[int(sid)]
            if r in seen:
                continue
            seen.add(r)
            snippet = sentences[int(sid)][:80].replace("\n", " ")
            print(f"    [{sent_report_nm[int(sid)][:24]:24s}]  {snippet}")
            shown += 1
            if shown >= 5:
                break


if __name__ == "__main__":
    main()
