"""RI-VSA v10b — v10 의 두 bug 수정.

v10 fail 진단
-------------
1. **MAX_CODEPOINT 정규화 오류**: 한글 (U+AC00~U+D7A3) 이 전체 UTF 의 1% 만
   차지 → 256 bin 중 ~3 bin 에 몰림 → 신호 0.
   bin_freq nnz = 15/256 (60% 사용 안 됨).
2. **순서·빈도 손실**: 한 문장 내 unique bin set 만 cooc 누적 → 순서·연속성
   정보 다 잃음. 사용자 원래 "수평선 sequence" 의도와 어긋남.

v10b 수정
---------
1. **한글 전용 정규화**:
       bin = (ord(c) - 0xAC00) * K // 11172
   한글이 0~1 전체에 펼침. 한글 외 문자는 무시 (공백·숫자·영문은 별도 bin 또는 drop).
2. **Window-based 주변**: 한 글자의 좌우 ±W 글자 (W=5) 가 *주변*. 순서 보존.
   pair: bins[i:-d] vs bins[d:] → numpy vectorized np.add.at.
3. **PPMI 동일**, 단 가중 = window 내 가까울수록 강함 (optional, v10b 는 단순 1).

기대
----
한글 글자 11172 개 → 256 bin → 평균 43 글자/bin. 변별력 ↑.
"차입" 의 주변 glyph 들과 "돈" 의 주변 glyph 들이 *공유 영역* 에 vote 응집 시 매칭.

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
HANGUL_RANGE = HANGUL_END - HANGUL_START + 1  # 11172
WINDOW = 5
MAX_SECTION_CHARS = 30_000
MAX_SENTS_PER_SECTION = 200
MIN_SENTENCE_LEN = 8
MAX_CHARS_PER_SENTENCE = 200
N_SAMPLE_SENTENCES = 1_000_000

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
    """한글만 bin 으로. 한글 외 문자는 drop. 순서 보존."""
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
    print(f"RI-VSA v10b — 한글 전용 UTF 좌표 + window=±{WINDOW} 주변 분포 (K={K_BINS}, 1M 표본)")
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

    # ── 2. corpus 한 패스 — bins 추출 + window-based co-occurrence ──
    t0 = time.perf_counter()
    cooc = np.zeros((K_BINS, K_BINS), dtype=np.float64)
    bin_freq = np.zeros(K_BINS, dtype=np.float64)
    sentence_bins_list: list[np.ndarray] = [None] * n_sent  # type: ignore
    total_chars = 0
    for sid, sent in enumerate(sentences):
        bins = textToBins(sent)
        sentence_bins_list[sid] = bins
        n = bins.size
        total_chars += n
        if n < 2:
            continue
        # bin_freq (글자 단위)
        np.add.at(bin_freq, bins, 1)
        # window co-occurrence (대칭)
        for d in range(1, min(WINDOW, n - 1) + 1):
            a = bins[:-d]
            b = bins[d:]
            # forward
            np.add.at(cooc, (a, b), 1)
            # backward (대칭)
            np.add.at(cooc, (b, a), 1)
        if (sid + 1) % 100_000 == 0:
            print(f"  [cooc] {sid + 1:,}/{n_sent:,} | chars/sent avg {total_chars / (sid + 1):.1f}")
    print(
        f"[cooc] bin_freq nnz={int((bin_freq > 0).sum())}/{K_BINS} | "
        f"cooc nnz={int((cooc > 0).sum())}/{K_BINS * K_BINS} | "
        f"{time.perf_counter() - t0:.1f}s"
    )

    # ── 3. PPMI 가중 ──
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
    meaningProfile = ppmi / row_sum  # (K, K) — bin 의 주변 분포
    print(f"[ppmi] PPMI total nnz={int((ppmi > 0).sum()):,}/{K_BINS * K_BINS} | {time.perf_counter() - t0:.1f}s")

    # ── 4. 문장 시그니처 — 그 안 글자 bins 의 meaningProfile 평균 → sign-pack ──
    t0 = time.perf_counter()
    sentence_sigs_packed = np.zeros((n_sent, K_BINS // 8), dtype=np.uint8)
    # global threshold = corpus 평균 (모든 문장 동일 기준)
    # 한 문장 안에서 median 이면 모든 문장이 비슷한 패턴 → 변별력 X
    # → global mean of meaningProfile 행 평균을 threshold
    global_mean = meaningProfile.mean(axis=0)  # (K,)

    for sid in range(n_sent):
        bins = sentence_bins_list[sid]
        if bins.size == 0:
            continue
        sig = meaningProfile[bins].mean(axis=0)  # (K,)
        bits = (sig > global_mean).astype(np.uint8)
        sentence_sigs_packed[sid] = np.packbits(bits)
    print(f"[sig] sentence_sigs_packed {sentence_sigs_packed.nbytes / 1e6:.1f} MB | {time.perf_counter() - t0:.1f}s")

    # ── 5. 검색 함수 ──
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

    # ── 6. 평가 ──
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

    # ── 7. snippet 데모 ──
    print()
    print("─── snippet 검색 데모 (top 5) ───")
    SHOW = [
        "회사가 돈 빌렸나",
        "자사주 사들였나",
        "공장 짓는 회사",
        "유상증자한 회사",
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
