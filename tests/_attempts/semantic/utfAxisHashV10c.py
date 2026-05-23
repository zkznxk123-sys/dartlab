"""RI-VSA v10c — v10b 구조 그대로 + allFilings full 20M corpus (Step 2).

배경
----
v10b 가 1M 표본에서 P@5=0.15 첫 신호. corpus 확대로 PPMI 안정성 → 신호 변화 측정.
사용자 의도 "공시 + docs 다" 의 1 차 단계.

v10b 와 차이
-----------
- N_SAMPLE 제거 — allFilings 의 모든 *.parquet (2026* 65 일치) full
- 메모리 효율: sentence_bins_list 는 그대로 보관 (~2GB 추정, OK)
- 그 외 동일: 한글 정규화 (0xAC00~0xD7A3), K=256 bin, window=±5, PPMI

기대
----
- 1M → 20M = 20× corpus → PPMI matrix 안정성 향상
- 흔한 글자 (이·은·는) 의 noise 약해지고 도메인 글자 (차·금·증) signal 강화
- 약한 신호 자연어 쿼리 ("회사가 돈 빌렸나") 가 신호 등장하나 핵심

결과 (작성 후 채움)
------------------
"""

from __future__ import annotations

import re
import time
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
    print(f"RI-VSA v10c — v10b full 20M (allFilings, K={K_BINS}, window=±{WINDOW})")
    print("=" * 72)

    # ── 1. corpus + 문장 분리 + bins 추출 (한 패스) ──
    t0 = time.perf_counter()
    files = sorted(p for p in ALLFILINGS_DIR.glob("2026*.parquet") if "_meta" not in p.name)
    print(f"[files] {len(files)} 일치 parquet")

    # cooc 즉시 누적 (sentence_bins 도 보관)
    cooc = np.zeros((K_BINS, K_BINS), dtype=np.float64)
    bin_freq = np.zeros(K_BINS, dtype=np.float64)
    sentences: list[str] = []
    sent_rcept: list[str] = []
    sent_report_nm: list[str] = []
    sentence_bins_list: list[np.ndarray] = []
    total_chars = 0
    for fi, f in enumerate(files):
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
                bins = textToBins(sent)
                if bins.size >= 2:
                    np.add.at(bin_freq, bins, 1)
                    for d in range(1, min(WINDOW, bins.size - 1) + 1):
                        a = bins[:-d]
                        b = bins[d:]
                        np.add.at(cooc, (a, b), 1)
                        np.add.at(cooc, (b, a), 1)
                sentences.append(sent)
                sent_rcept.append(r)
                sent_report_nm.append(rn)
                sentence_bins_list.append(bins)
                total_chars += bins.size
        del df
        if (fi + 1) % 10 == 0:
            elapsed = time.perf_counter() - t0
            print(
                f"  [load+cooc] file {fi + 1}/{len(files)} | "
                f"sentences {len(sentences):,} | "
                f"avg chars/sent {total_chars / max(len(sentences), 1):.1f} | "
                f"elapsed {elapsed:.0f}s"
            )
    n_sent = len(sentences)
    print(
        f"[corpus+cooc] 문장 {n_sent:,} | "
        f"bin_freq nnz={int((bin_freq > 0).sum())}/{K_BINS} | "
        f"cooc nnz={int((cooc > 0).sum())}/{K_BINS * K_BINS} | "
        f"{time.perf_counter() - t0:.1f}s"
    )

    # ── 2. PPMI ──
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

    # ── 3. 문장 시그니처 ──
    t0 = time.perf_counter()
    sentence_sigs_packed = np.zeros((n_sent, K_BINS // 8), dtype=np.uint8)
    global_mean = meaningProfile.mean(axis=0)
    last_log = time.perf_counter()
    for sid in range(n_sent):
        bins = sentence_bins_list[sid]
        if bins.size == 0:
            continue
        sig = meaningProfile[bins].mean(axis=0)
        bits = (sig > global_mean).astype(np.uint8)
        sentence_sigs_packed[sid] = np.packbits(bits)
        if (sid + 1) % 2_000_000 == 0:
            elapsed = time.perf_counter() - last_log
            rate = 2_000_000 / elapsed
            eta = (n_sent - sid - 1) / rate
            print(f"  [sig] {sid + 1:,}/{n_sent:,} | {rate:.0f} sent/s | eta {eta:.0f}s")
            last_log = time.perf_counter()
    print(f"[sig] {sentence_sigs_packed.nbytes / 1e6:.1f} MB | {time.perf_counter() - t0:.1f}s")

    # ── 4. 검색 함수 ──
    def queryHash(q: str) -> np.ndarray:
        bins = textToBins(q)
        if bins.size == 0:
            return np.zeros(K_BINS // 8, dtype=np.uint8)
        sig = meaningProfile[bins].mean(axis=0)
        bits = (sig > global_mean).astype(np.uint8)
        return np.packbits(bits)

    def search(q: str, top_k: int = 30) -> tuple[np.ndarray, np.ndarray]:
        qh = queryHash(q)
        xored = np.bitwise_xor(sentence_sigs_packed, qh[None, :])
        dist = np.unpackbits(xored, axis=1).sum(axis=1)
        k = min(top_k, n_sent)
        part = np.argpartition(dist, k - 1)[:k]
        order = part[np.argsort(dist[part])]
        return order, dist[order]

    # ── 5. 평가 ──
    print()
    print("─── 평가 셋트 (12 쿼리, Hamming) ───")
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
        order, dist = search(q.text, top_k=150)
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

    # ── 6. snippet 데모 ──
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
        order, dist = search(q, top_k=30)
        seen = set()
        print(f'\n❓ "{q}"')
        shown = 0
        for sid, d in zip(order, dist):
            r = sent_rcept[int(sid)]
            if r in seen:
                continue
            seen.add(r)
            snippet = sentences[int(sid)][:80].replace("\n", " ")
            print(f"    d={int(d):3d}  [{sent_report_nm[int(sid)][:24]:24s}]  {snippet}")
            shown += 1
            if shown >= 5:
                break


if __name__ == "__main__":
    main()
