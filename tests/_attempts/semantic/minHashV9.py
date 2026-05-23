"""RI-VSA v9 — 사용자 원래 설계 정직 구현: 띄어쓰기 토큰 + MinHash + contextualized.

배경 — 깊은 실수 인정
-------------------
v1~v8 전체가 *글자 ngram (bigram + trigram) + SimHash* 로 박혀 있었다.
근본 잘못:
1. ngram 은 의미 단위가 아니다 ("회사가" 의 "사가" 같은 무의미 ngram 포함)
2. SimHash 의 signed sum 은 linear → 단순 합/XOR 시 collapse → bag-of-X
3. 사용자가 가르친 건 **띄어쓰기 토큰 + MinHash** 였는데 답습으로 ngram 갔다

사용자 설계
----------
1. **stem = 띄어쓰기 토큰** (no normalization, no morpheme split)
   - "회사가 돈 빌렸나" → ["회사가", "돈", "빌렸나"]
2. **K-dim MinHash signature per stem** (intrinsic, fixed)
   - h_1, …, h_K = K 개 독립 hash 함수
   - stemSig(token)[k] = h_k(token) ∈ uint32
3. **문장 내 stem 의 contextualized signature** (주변이 결정)
   - 단순 element-wise min 합성은 collapse (set MinHash 로 환원, 증명 v8 docstring)
   - non-linear pair-binding: `in_S(s_i)[k] = h_k(s_i) ⊕ min_{j≠i} h_k(s_j)`
   - 자기 hash 와 *주변 최소* 의 XOR — 비대칭 짝 합성
4. **문장 MinHash** = element-wise min over in_S(s_i)
5. **비교 = equality count** (Hamming X) — 표준 MinHash Jaccard 추정

구현 비고
--------
- K=128. stemSig = uint32[128] = 512 byte/stem.
- 한 stem 의 K hash: `blake2b(token, digest_size=512)` 1 회 → 128 uint32 slice.
  엄밀한 K 독립 perm 아니지만 cryptographic hash 의 slice 는 사실상 무상관.
- 문장 signature: uint32[128] = 512 byte/sentence.
- 검색: 쿼리 sig vs 문장 sig — 같은 dim 같은 값 갯수 / K = Jaccard.

평가
----
1M 문장 표본 → [evalSet.py](evalSet.py) 12 쿼리. 20M full 은 표본 신호 보고.

결과 (작성 후 채움)
------------------
"""

from __future__ import annotations

import hashlib
import re
import time
from pathlib import Path

import numpy as np
import polars as pl
from evalSet import QUERIES, evaluate, formatReport

ALLFILINGS_DIR = Path("data/dart/allFilings")
K = 64  # MinHash dimensions (uint32) — blake2b max 64 byte/call, 4 round 체인
N_BLAKE_ROUNDS = (K * 4 + 63) // 64
SIG_BYTES_PER_STEM = K * 4  # uint32
MAX_SECTION_CHARS = 30_000
MAX_SENTS_PER_SECTION = 200
MIN_SENTENCE_LEN = 8
MAX_STEMS_PER_SENTENCE = 40  # 띄어쓰기 토큰 — ngram 대비 1/10, cap 작게
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


def tokenizeStems(s: str) -> list[str]:
    """띄어쓰기 토큰. normalization 없음."""
    return s.split()


def stemSignature(token: str) -> np.ndarray:
    """token → uint32[K] MinHash signature (intrinsic, fixed).

    blake2b max 64 byte/call → person 태그로 N_BLAKE_ROUNDS 체인.
    K=64 → 256 byte = 4 round.
    """
    enc = token.encode("utf-8")
    parts = []
    for i in range(N_BLAKE_ROUNDS):
        h = hashlib.blake2b(
            enc,
            digest_size=64,
            person=f"v9{i:02d}".encode(),
        ).digest()
        parts.append(h)
    raw = b"".join(parts)[: K * 4]
    return np.frombuffer(raw, dtype=np.uint32).copy()


def sentenceMinHash(stem_sigs: np.ndarray) -> np.ndarray:
    """문장 (n stems × K) signature → 문장 MinHash (K,).

    contextualized:
        in_S(s_i)[k] = stem_sigs[i][k] XOR min_{j≠i} stem_sigs[j][k]
    sentence:
        sig[k] = min_i in_S(s_i)[k]

    edge case: n=1 → in_S(s_0) = stem_sigs[0] XOR stem_sigs[0] = 0 → sig=0.
       이 경우 그냥 stem_sigs[0] 반환 (단일 토큰 문장은 자기 signature).
    """
    n = stem_sigs.shape[0]
    if n == 0:
        return np.zeros(K, dtype=np.uint32)
    if n == 1:
        return stem_sigs[0].copy()

    # column-wise sort → 1st min + 2nd min
    sorted_sigs = np.sort(stem_sigs, axis=0)  # (n, K)
    min_val = sorted_sigs[0]  # (K,)
    second_min = sorted_sigs[1] if n > 1 else min_val  # (K,)

    # 주변 최소 (자기 제외)
    is_min = stem_sigs == min_val[None, :]  # (n, K)
    # 자기가 min 이면 second_min 으로, 아니면 min 으로
    min_excl = np.where(is_min, second_min[None, :], min_val[None, :])  # (n, K)

    in_S = stem_sigs ^ min_excl  # (n, K) — 비대칭 pair bind
    return in_S.min(axis=0)  # (K,)


def main() -> None:
    print("=" * 72)
    print(f"RI-VSA v9 — whitespace token + MinHash + contextualized (K={K}, blake2b rounds={N_BLAKE_ROUNDS})")
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

    # ── 2. stem signature cache (unique whitespace tokens) ──
    t0 = time.perf_counter()
    sig_cache: dict[str, np.ndarray] = {}
    sentence_tokens: list[list[str]] = []
    for sent in sentences:
        toks = tokenizeStems(sent)
        if len(toks) > MAX_STEMS_PER_SENTENCE:
            toks = toks[:MAX_STEMS_PER_SENTENCE]
        sentence_tokens.append(toks)
        for tok in toks:
            if tok not in sig_cache:
                sig_cache[tok] = stemSignature(tok)
    print(f"[stems] unique whitespace tokens {len(sig_cache):,} | {time.perf_counter() - t0:.1f}s")

    # ── 3. sentence MinHash 빌드 ──
    t0 = time.perf_counter()
    sentence_sigs = np.zeros((n_sent, K), dtype=np.uint32)
    last_log = time.perf_counter()
    for sid, toks in enumerate(sentence_tokens):
        if not toks:
            continue
        stem_sigs = np.stack([sig_cache[t] for t in toks], axis=0)  # (n, K)
        sentence_sigs[sid] = sentenceMinHash(stem_sigs)
        if (sid + 1) % 50_000 == 0:
            elapsed = time.perf_counter() - last_log
            rate = 50_000 / elapsed
            eta = (n_sent - sid - 1) / rate
            print(f"  [hash] {sid + 1:,}/{n_sent:,} | {rate:.0f} sent/s | eta {eta:.0f}s")
            last_log = time.perf_counter()
    print(f"[hash] sentence_sigs {sentence_sigs.nbytes / 1e6:.1f} MB | {time.perf_counter() - t0:.1f}s")

    # ── 4. query function — 같은 함수 ──
    def queryMinHash(q: str) -> np.ndarray:
        toks = tokenizeStems(q)
        if not toks:
            return np.zeros(K, dtype=np.uint32)
        stem_sigs = np.stack(
            [sig_cache.get(t) if t in sig_cache else stemSignature(t) for t in toks],
            axis=0,
        )
        return sentenceMinHash(stem_sigs)

    # ── 5. 검색 함수 (equality count) ──
    def searchTopK(qsig: np.ndarray, k: int = 30) -> tuple[np.ndarray, np.ndarray]:
        eq = (sentence_sigs == qsig[None, :]).sum(axis=1)  # (n_sent,) int
        # 큰 게 좋음 (more equal dimensions = higher Jaccard)
        order = np.argpartition(-eq, min(k, n_sent - 1))[:k]
        order = order[np.argsort(-eq[order])]
        return order, eq[order]

    # evalSet 의 evaluate 는 Hamming 기반 → MinHash 용으로 직접 평가 작성
    print()
    print("─── 평가 셋트 (12 쿼리, equality-count) ───")
    print(f"{'쿼리':<22} {'#정답':>6} {'P@5':>6} {'P@10':>6} {'R@5':>6} {'R@10':>6} {'MRR':>6}")
    print("-" * 70)
    p5s, p10s, r5s, r10s, mrrs = [], [], [], [], []
    for q in QUERIES:
        # ground truth
        import re as _re

        pat = q.relevance
        rel_by_sent = np.fromiter(
            (bool(pat.search(r or "")) for r in sent_report_nm),
            dtype=bool,
            count=n_sent,
        )
        rcept_first = {}
        for i, r in enumerate(sent_rcept):
            rcept_first.setdefault(r, i)
        rcepts = list(rcept_first.keys())
        total_rel = sum(1 for r in rcepts if rel_by_sent[rcept_first[r]])
        if total_rel == 0:
            print(f"{q.text:<22} {0:>6d} {'nan':>6} {'nan':>6} {'nan':>6} {'nan':>6} {'nan':>6}")
            continue

        qsig = queryMinHash(q.text)
        order, eq = searchTopK(qsig, k=150)
        # rcept dedup → top-10
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
    print("─── snippet 검색 데모 (top 5, equality count) ───")
    SHOW = [
        "회사가 돈 빌렸나",
        "자사주 사들였나",
        "공장 짓는 회사",
        "유상증자한 회사",
    ]
    for q in SHOW:
        qsig = queryMinHash(q)
        order, eq = searchTopK(qsig, k=30)
        seen = set()
        print(f'\n❓ "{q}"')
        shown = 0
        for sid, e in zip(order, eq):
            r = sent_rcept[int(sid)]
            if r in seen:
                continue
            seen.add(r)
            snippet = sentences[int(sid)][:80].replace("\n", " ")
            print(f"    eq={int(e):3d}/{K}  [{sent_report_nm[int(sid)][:24]:24s}]  {snippet}")
            shown += 1
            if shown >= 5:
                break


if __name__ == "__main__":
    main()
