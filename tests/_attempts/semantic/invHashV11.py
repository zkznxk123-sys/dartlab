"""RI-VSA v11 — 역인덱스 stem + 수평선 + char-bin PPMI 결합 (Step 1: 1M 표본).

배경 — 사용자 결정적 통찰
----------------------
v10b 가 첫 신호 (P@5=0.15, MRR=0.17) 봤지만 *글자 공유 없는 자연어 쿼리* 는 fail.
사용자 발상:
1. **역인덱스 stem + 수평선 구조물** = agipath core 의 정공법
   - stem 단위 invIndex (stem → [(sid, pos)])
   - stem 수평선 좌표 (UTF) — 응집 만들기
2. **공시 + docs 다** = corpus 30 배 확대 (PPMI 안정성 + 어휘 합류)

v11 = v10b 의 char-bin PPMI (의미 layer) + invIndex direct hit (정확 매칭) 결합.

알고리즘
--------
구조물 (한 패스 corpus 빌드):
1. tokenize whitespace: text.split()
2. invIndex[stem] = [(sid, pos_in_sentence)]
3. stemCoord[stem] = first 한글 글자 UTF / 한글범위 → 0~1 (수평선 좌표)
4. char-bin PPMI (v10b 동일): bin_freq, cooc, meaningProfile

검색 (2-layer 가중 합):
- Layer A (직접 매칭): 쿼리 stem 각각의 invIndex hit → sid 점수 += K
- Layer B (의미 확장): 쿼리 char-bin sig vs corpus sentence sig Hamming → sid 점수 += (K - dist)
- 두 점수 합산 → top-K

가중: A = invIndex hit 수. B = K - Hamming dist (0~K_BITS). 초기 1:1.

기대
----
- 도메인 어휘 쿼리 ("주주총회 결과", "최대주주 변경") — invIndex direct hit + PPMI 둘 다 신호 ↑↑
- 자연어 쿼리 ("회사가 돈 빌렸나") — invIndex 의 일부 stem ("회사가") direct hit + 약한 PPMI

step
----
Step 1 (지금): allFilings 1M 표본
Step 2: allFilings 20M full
Step 3: + docs 표본
Step 4: + docs full

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

ALLFILINGS_DIR = Path("data/dart/allFilings")
K_BINS = 256
HANGUL_START = 0xAC00
HANGUL_END = 0xD7A3
HANGUL_RANGE = HANGUL_END - HANGUL_START + 1
WINDOW = 5
MAX_SECTION_CHARS = 30_000
MAX_SENTS_PER_SECTION = 200
MIN_SENTENCE_LEN = 8
MAX_CHARS_PER_SENTENCE = 200
MAX_TOKENS_PER_SENTENCE = 40
N_SAMPLE_SENTENCES = 1_000_000

# Layer 가중치 (초기)
W_DIRECT = 10.0  # invIndex hit 당
W_PPMI = 1.0  # PPMI Hamming 당 (K - dist)

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


def textToBins(text: str) -> np.ndarray:
    """한글 글자 → bin. 비한글 drop."""
    if len(text) > MAX_CHARS_PER_SENTENCE:
        text = text[:MAX_CHARS_PER_SENTENCE]
    bins = []
    for ch in text:
        code = ord(ch)
        if HANGUL_START <= code <= HANGUL_END:
            bins.append((code - HANGUL_START) * K_BINS // HANGUL_RANGE)
    return np.asarray(bins, dtype=np.int32)


def main() -> None:
    print("=" * 72)
    print(f"RI-VSA v11 — invIndex + 수평선 + char-bin PPMI (Step 1, 1M 표본, K={K_BINS})")
    print("=" * 72)

    # ── 1. corpus + 문장 분리 ──
    t0 = time.perf_counter()
    files = sorted(p for p in ALLFILINGS_DIR.glob("2026*.parquet") if "_meta" not in p.name)
    sentences: list[str] = []
    sent_rcept: list[str] = []
    sent_report_nm: list[str] = []
    n_sec_total = 0
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
        n_sec_total += df.height
        for row in df.iter_rows():
            r, rn, txt = row
            for sent in splitSentences(txt):
                sentences.append(sent)
                sent_rcept.append(r)
                sent_report_nm.append(rn)
                if len(sentences) >= N_SAMPLE_SENTENCES:
                    sample_full = True
                    break
            if sample_full:
                break
        del df
        if sample_full:
            break
    n_sent = len(sentences)
    print(f"[corpus+split] 섹션 {n_sec_total:,} → 문장 {n_sent:,} (sample) | {time.perf_counter() - t0:.1f}s")

    # ── 2. 한 패스: bins + invIndex + char-bin cooc ──
    t0 = time.perf_counter()
    cooc = np.zeros((K_BINS, K_BINS), dtype=np.float64)
    bin_freq = np.zeros(K_BINS, dtype=np.float64)
    sentence_bins_list: list[np.ndarray] = [None] * n_sent  # type: ignore
    # invIndex: stem → list of (sid, pos)
    invIndex: dict[str, list[tuple[int, int]]] = defaultdict(list)

    for sid, sent in enumerate(sentences):
        # bins (char-bin PPMI 용)
        bins = textToBins(sent)
        sentence_bins_list[sid] = bins
        if bins.size >= 2:
            np.add.at(bin_freq, bins, 1)
            for d in range(1, min(WINDOW, bins.size - 1) + 1):
                a = bins[:-d]
                b = bins[d:]
                np.add.at(cooc, (a, b), 1)
                np.add.at(cooc, (b, a), 1)
        # whitespace tokens → invIndex
        tokens = sent.split()[:MAX_TOKENS_PER_SENTENCE]
        for pos, tok in enumerate(tokens):
            invIndex[tok].append((sid, pos))
        if (sid + 1) % 100_000 == 0:
            print(f"  [build] {sid + 1:,}/{n_sent:,} | unique stems {len(invIndex):,}")
    print(
        f"[build] invIndex unique stems {len(invIndex):,} | "
        f"avg postings {sum(len(v) for v in invIndex.values()) / max(len(invIndex), 1):.1f} | "
        f"bin_freq nnz={int((bin_freq > 0).sum())}/{K_BINS} | "
        f"cooc nnz={int((cooc > 0).sum())}/{K_BINS * K_BINS} | "
        f"{time.perf_counter() - t0:.1f}s"
    )

    # ── 3. PPMI ──
    t0 = time.perf_counter()
    total_cooc = cooc.sum()
    pa = bin_freq / max(bin_freq.sum(), 1.0)
    pa = np.maximum(pa, 1e-12)
    pab = cooc / max(total_cooc, 1.0)
    pa_pb = pa[:, None] * pa[None, :]
    with np.errstate(divide="ignore", invalid="ignore"):
        pmi = np.log((pab + 1e-12) / (pa_pb + 1e-12))
    ppmi = np.maximum(pmi, 0.0).astype(np.float32)
    row_sum = ppmi.sum(axis=1, keepdims=True)
    row_sum = np.maximum(row_sum, 1e-9)
    meaningProfile = ppmi / row_sum
    print(f"[ppmi] nnz={int((ppmi > 0).sum()):,}/{K_BINS * K_BINS} | {time.perf_counter() - t0:.1f}s")

    # ── 4. 문장 시그니처 (char-bin sig) ──
    t0 = time.perf_counter()
    sentence_sigs_packed = np.zeros((n_sent, K_BINS // 8), dtype=np.uint8)
    global_mean = meaningProfile.mean(axis=0)
    for sid in range(n_sent):
        bins = sentence_bins_list[sid]
        if bins.size == 0:
            continue
        sig = meaningProfile[bins].mean(axis=0)
        bits = (sig > global_mean).astype(np.uint8)
        sentence_sigs_packed[sid] = np.packbits(bits)
    print(f"[sig] {sentence_sigs_packed.nbytes / 1e6:.1f} MB | {time.perf_counter() - t0:.1f}s")

    # ── 5. 검색 함수 — 2 layer 가중 합 ──
    def queryHash(q: str) -> np.ndarray:
        bins = textToBins(q)
        if bins.size == 0:
            return np.zeros(K_BINS // 8, dtype=np.uint8)
        sig = meaningProfile[bins].mean(axis=0)
        bits = (sig > global_mean).astype(np.uint8)
        return np.packbits(bits)

    def search(q: str, top_k: int = 30) -> tuple[np.ndarray, np.ndarray]:
        # Layer A — invIndex direct hit
        direct_scores = np.zeros(n_sent, dtype=np.float32)
        for tok in q.split():
            postings = invIndex.get(tok)
            if postings:
                for sid, _pos in postings:
                    direct_scores[sid] += W_DIRECT
        # Layer B — char-bin PPMI Hamming
        qh = queryHash(q)
        xored = np.bitwise_xor(sentence_sigs_packed, qh[None, :])
        dist = np.unpackbits(xored, axis=1).sum(axis=1).astype(np.float32)
        ppmi_scores = (K_BINS - dist) * W_PPMI
        total_scores = direct_scores + ppmi_scores
        # top-K — *높을수록 좋음*
        k = min(top_k, n_sent)
        part = np.argpartition(-total_scores, k - 1)[:k]
        order = part[np.argsort(-total_scores[part])]
        return order, total_scores[order]

    # ── 6. 평가 ──
    print()
    print("─── 평가 셋트 (12 쿼리, A+B 가중 합) ───")
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
        order, _ = search(q.text, top_k=150)
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

    # ── 7. snippet 데모 ──
    print()
    print("─── snippet 검색 데모 (top 5) ───")
    SHOW = [
        "회사가 돈 빌렸나",
        "자사주 사들였나",
        "공장 짓는 회사",
        "유상증자한 회사",
        "주주총회 결과",
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
            snippet = sentences[int(sid)][:80].replace("\n", " ")
            print(f"    score={sc:7.1f}  [{sent_report_nm[int(sid)][:24]:24s}]  {snippet}")
            shown += 1
            if shown >= 5:
                break


if __name__ == "__main__":
    main()
