"""RI-VSA v10 — 사용자 설계 정확 구현: UTF 자연 수평선 좌표 + 주변 stem 분포 (의미).

배경 — 사용자 핵심 통찰
---------------------
v1~v9 fail 의 공통 원인: 자연어 ↔ 도메인 어휘 클러스터 분리. 어떤 hash 합성도
*공유 토큰 없으면 매칭 X*.

사용자 v10 발상:
1. **수평선 = UTF 자연 좌표** — 모든 글자 → UTF / MAX → 0~1 점. 학습·룰·사전 0.
   "사람이/사람은/사람과" → 첫 2 점 동일 + 마지막 점 한글 코드 가까운 위치
   → 표면형 변형 자동 응집 (agipath rootDict 의 56 조사 룰이 자연 좌표로 자동)
2. **의미 = 주변 stem 의 수평선 분포** (Firth 1957 + 자연 좌표)
   한 stem 의 의미 = corpus 의 그 stem 등장 문장에서 *주변 글자들의 UTF 좌표 histogram*
   "차입금" 주변 = {증가, 단기, 운영자금, 사채, 갚, 결제} 의 좌표 분포
   "돈"     주변 = {빌, 갚, 자금, 운영, 결제, 지불} 의 좌표 분포
   공유 주변 (갚·자금·운영·결제) → 두 분포 *같은 bin 에 vote* → 자연 의미 유사

vs 이전 트랙
-----------
- v3 (M.T @ M + random hash): random hash 가 표면형 응집 X. char ngram noise.
- v7 (Tier2 self-included identity): 같음.
- v9 (whitespace + MinHash): 표면형 응집 X (코드값 인접해도 hash 무관).
- v10: UTF 좌표 = *자연 응집* + *주변 분포 distributional* 두 효과 합성.

알고리즘
--------
1. **글자 → 수평선 좌표**: c → ord(c) / MAX_CODEPOINT (0x110000) → float ∈ [0,1)
2. **수평선 bin**: K=256 bin. char → bin = int(coord * K).
3. **stem 표현**: stem (whitespace 토큰) → 글자들의 좌표 → bin 들 set/histogram.
4. **stem 의 주변 분포** (corpus 통계):
   각 stem s 에 대해, corpus 의 모든 등장 문장에서 *s 와 같은 문장 안의 다른 글자들의 bin*
   을 누적 → 256-dim float histogram = meaningProfile[s]
5. **문장 시그니처**:
   sig(sentence) = Σ over stem s in sentence of meaningProfile[s]
   → 256-dim float → sign-pack 또는 그대로 cosine.
6. **쿼리 시그니처**: 동일 함수.
7. **검색**: cosine similarity top-K (또는 SimHash sign-pack + Hamming).

비용
----
- meaningProfile 빌드 1 회: corpus 한 패스. 메모리 = K × n_unique_stems × 4 byte.
  1M 표본 → 500K stems × 256 × 4 = 500 MB. 부담.
  → stem 대신 *글자* 의 meaning profile 빌드. char-level → 11K unique chars × 256 = 11 MB.
    한 stem 의 의미 = 그 stem 글자들의 meaning profile 평균.
- 문장 시그니처 = 256-dim float. 20M sentences × 1KB = 20 GB. 너무 큼.
  → sign-pack 32 byte/sentence = 640 MB. OK.

구현 — 메모리 최적
------------------
- meaningProfile[char_bin][neighbor_bin] = corpus co-occurrence count (256 × 256 = 65K cells)
- 한 문장 시그니처: stem 의 글자 bin 들 → meaningProfile row 평균 → 256-dim
- 검색: query sig (256-dim float) vs sentence sigs (32 byte packed)
  → cosine 비교는 256-bit packed XOR 으로 근사

코드 단순화: 256-bit Bloom-like signature per sentence + SimHash 변형 sign-pack.

평가
----
[evalSet.py](evalSet.py) 12 쿼리. 1M 문장 표본 → 신호 보이면 full.

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
MAX_CODEPOINT = 0x110000  # Unicode max + 1
MAX_SECTION_CHARS = 30_000
MAX_SENTS_PER_SECTION = 200
MIN_SENTENCE_LEN = 8
MAX_CHARS_PER_SENTENCE = 200  # 시그니처 빌드 cap
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


def charToBin(ch: str) -> int:
    """글자 → UTF 좌표 → bin (0..K_BINS-1)."""
    return min(ord(ch) * K_BINS // MAX_CODEPOINT, K_BINS - 1)


def sentenceBins(s: str) -> np.ndarray:
    """문장 → 글자별 bin 배열 (공백 제외)."""
    if len(s) > MAX_CHARS_PER_SENTENCE:
        s = s[:MAX_CHARS_PER_SENTENCE]
    bins = [charToBin(ch) for ch in s if not ch.isspace()]
    return np.asarray(bins, dtype=np.int16)


def main() -> None:
    print("=" * 72)
    print(f"RI-VSA v10 — UTF 자연 수평선 + 주변 stem 분포 (K={K_BINS} bin, 1M 표본)")
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

    # ── 2. corpus 한 패스: bin-bin co-occurrence matrix (= 주변 분포 학습) ──
    # cooc[a][b] = corpus 의 모든 문장에서, bin a 와 bin b 가 같은 문장에 등장한 가중
    # 한 문장에서 (n_chars 개) bin 들 → 모든 pair (a, b) 에 +1 / n_chars  (normalize)
    # 메모리: K x K float32 = 256 KB. 가벼움.
    t0 = time.perf_counter()
    cooc = np.zeros((K_BINS, K_BINS), dtype=np.float32)
    bin_freq = np.zeros(K_BINS, dtype=np.float64)
    # sentence_bins_list 동시 저장 (다음 단계 재사용)
    sentence_bins_list: list[np.ndarray] = [None] * n_sent  # type: ignore
    for sid, sent in enumerate(sentences):
        bins = sentenceBins(sent)
        sentence_bins_list[sid] = bins
        if bins.size < 2:
            continue
        # unique bins (한 문장 내 중복 제거 — 같은 글자가 여러 번이어도 1 회만)
        ubins = np.unique(bins)
        u_n = ubins.size
        # 외적 — outer-product 누적 (a≠b 자기 제외)
        # 가중 = 1 / u_n (긴 문장 noise 회피)
        w = 1.0 / u_n
        # bin_freq 갱신
        bin_freq[ubins] += 1
        # cooc 갱신 — outer add (대칭)
        # 직접 outer: cooc[ubins, :][:, ubins] += w
        # 큰 문장에서 빠르게: indexing
        idx = ubins
        cooc[np.ix_(idx, idx)] += w
        # 자기 자신 빼기 (대각)
        cooc[idx, idx] -= w
        if (sid + 1) % 100_000 == 0:
            print(f"  [cooc] {sid + 1:,}/{n_sent:,}")
    print(
        f"[cooc] {cooc.nbytes / 1e3:.0f} KB | bin_freq nnz={int((bin_freq > 0).sum())}/{K_BINS} | "
        f"{time.perf_counter() - t0:.1f}s"
    )

    # ── 3. PMI / PPMI 가중 (변별력) ──
    # P(a,b) = cooc[a,b] / total
    # P(a) = bin_freq[a] / n_sent
    # PMI = log(P(a,b) / (P(a) * P(b)))
    # PPMI = max(PMI, 0)
    t0 = time.perf_counter()
    total_cooc = cooc.sum()
    pa = bin_freq / n_sent  # (K,)
    pa = np.maximum(pa, 1e-9)
    # 정규화 코어
    pab = cooc / max(total_cooc, 1.0)
    pa_pb = pa[:, None] * pa[None, :]
    with np.errstate(divide="ignore", invalid="ignore"):
        pmi = np.log((pab + 1e-12) / (pa_pb + 1e-12))
    ppmi = np.maximum(pmi, 0.0).astype(np.float32)  # (K, K)
    # 행별 정규화 — 한 bin 의 "주변 분포" = ppmi row normalized
    row_sum = ppmi.sum(axis=1, keepdims=True)
    row_sum = np.maximum(row_sum, 1e-9)
    meaningProfile = ppmi / row_sum  # (K, K) — bin → 주변 bin 분포
    print(f"[ppmi] PPMI total nnz={int((ppmi > 0).sum()):,} | {time.perf_counter() - t0:.1f}s")

    # ── 4. 문장 시그니처 — 그 안 모든 글자의 meaningProfile row 평균 ──
    t0 = time.perf_counter()
    # 한 문장: bins → meaningProfile[bins].mean(axis=0) → (K,) → sign-pack
    sentence_sigs_packed = np.zeros((n_sent, K_BINS // 8), dtype=np.uint8)
    sig_dense_threshold = np.zeros(n_sent, dtype=np.float32)  # debug
    for sid in range(n_sent):
        bins = sentence_bins_list[sid]
        if bins.size == 0:
            continue
        # 한 문장 의미 = 글자 bins 의 주변 분포 평균
        sig = meaningProfile[bins].mean(axis=0)  # (K,)
        # threshold = median (binary sign-pack)
        thr = np.median(sig)
        sig_dense_threshold[sid] = thr
        bits = (sig > thr).astype(np.uint8)
        sentence_sigs_packed[sid] = np.packbits(bits)
    print(f"[sig] sentence_sigs_packed {sentence_sigs_packed.nbytes / 1e6:.1f} MB | {time.perf_counter() - t0:.1f}s")

    # ── 5. 쿼리 함수 — 동일 함수 ──
    def queryHash(q: str) -> np.ndarray:
        bins = sentenceBins(q)
        if bins.size == 0:
            return np.zeros(K_BINS // 8, dtype=np.uint8)
        sig = meaningProfile[bins].mean(axis=0)
        thr = np.median(sig)
        bits = (sig > thr).astype(np.uint8)
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
