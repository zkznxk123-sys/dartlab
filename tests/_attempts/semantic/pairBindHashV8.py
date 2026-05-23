"""RI-VSA v8 — pairwise bind contextualized sentence hash.

목적 — 사용자 원래 설계 정직 구현
-------------------------------
v1~v7 모두 *bag-of-characteristics* (모든 stem 의 hash 단순 합) 으로 collapse
한 게 실제 fail 의 한 원인.

사용자 설계: **한 문장 안에서 주체 stem 의 정체성 = 주변 stem 의 hash 조합**.
v7 까지 corpus-wide 평균 (M.T @ M) 으로 구현했지만 정작 사용자가 말한 건
*문장 내 동적 합성*.

수학적으로 합성이 *non-linear binding* 이어야 collapse 안 함:
- 단순 Σ_{j≠i} char[s_j] = S_total − char[s_i] → sentenceHash 가 (n−1)*S_total
  로 collapse (= v7 와 동일 형태)
- XOR 도 같은 collapse
- pairwise bind 필요 — `bind(c_i, c_j) = blake2b(sorted(c_i, c_j))` 같은
  *짝 해시*. 짝 해시들의 합은 단일 해시 합과 다른 공간.

알고리즘
--------
1. characteristic[stem] = blake2b(stem) → 256 bit (169K × 32B = 5.4 MB lookup)
2. 한 문장 S 의 stems = [s_1, …, s_n]:
   - 각 짝 (i, j), i < j:
       pair_key = sorted([char[s_i], char[s_j]]) 의 byte concat
       pair_hash = blake2b(pair_key)  → 256 bit
   - acc = Σ over pairs of unpack(pair_hash) (signed ±1)
   - sentence_sig = (acc > 0).pack  → 256 bit
3. 쿼리도 같은 함수.

복잡도
------
- 평균 문장 80 stems → C(80,2) = 3160 pair → 3160 × 1 µs = 3 ms / sentence
- 20M sentences × 3ms = 60K sec = **17 hours** (full).
- → **표본 100K 먼저** (3 분) 평가, 신호 있으면 full.

표본 평가 셋트
------------
[evalSet.py](evalSet.py) 의 12 쿼리. 100K 문장 subset 에 대한 rcept_no
relevance label.

결과 (작성 후 채움)
------------------
"""

from __future__ import annotations

import hashlib
import time
from pathlib import Path

import numpy as np
import polars as pl
from evalSet import QUERIES, evaluate, formatReport

ALLFILINGS_DIR = Path("data/dart/allFilings")
HASH_BYTES = 32
HASH_BITS = 256
NGRAM_NS = (2, 3)
MAX_STEMS_PER_SENTENCE = 60  # pairwise n² 폭발 차단
MAX_SECTION_CHARS = 30_000
MAX_SENTS_PER_SECTION = 200
MIN_SENTENCE_LEN = 8
N_SAMPLE_SENTENCES = 100_000

import re

SENT_SPLIT = re.compile(r"(?<=[다음음니다요죠임함])[\.\?!]\s+|[\.\?!]\s+|\n+|;\s+")


def splitSentences(text: str) -> list[str]:
    if not text:
        return []
    if len(text) > MAX_SECTION_CHARS:
        text = text[:MAX_SECTION_CHARS]
    parts = SENT_SPLIT.split(text)
    out = []
    for p in parts:
        p = p.strip()
        if len(p) >= MIN_SENTENCE_LEN:
            out.append(p)
            if len(out) >= MAX_SENTS_PER_SECTION:
                break
    return out


def tokenizeStems(s: str) -> list[str]:
    if not s:
        return []
    out: list[str] = []
    for n in NGRAM_NS:
        if len(s) < n:
            continue
        out.extend(s[i : i + n] for i in range(len(s) - n + 1))
    return out


def characteristic(stem: str) -> bytes:
    return hashlib.blake2b(stem.encode("utf-8"), digest_size=HASH_BYTES).digest()


def computeSentenceHash(stem_chars: list[bytes]) -> np.ndarray:
    """문장의 stem characteristic 리스트 → pair-bind sentence hash (32 byte).

    Non-linear binding: blake2b(sorted(c_i, c_j)) per pair.
    Accumulate signed votes across all pairs → sign pack.
    """
    n = len(stem_chars)
    if n < 2:
        # 단일 stem 문장 — 자기 자신만 (collapse 위험 없음 자체로 작음)
        if n == 1:
            bits = np.unpackbits(np.frombuffer(stem_chars[0], dtype=np.uint8))
            return np.packbits(bits)
        return np.zeros(HASH_BYTES, dtype=np.uint8)

    acc = np.zeros(HASH_BITS, dtype=np.int32)
    # 짝 합성
    for i in range(n):
        ci = stem_chars[i]
        for j in range(i + 1, n):
            cj = stem_chars[j]
            if ci <= cj:
                pair_key = ci + cj
            else:
                pair_key = cj + ci
            pair_hash = hashlib.blake2b(pair_key, digest_size=HASH_BYTES).digest()
            bits = np.frombuffer(pair_hash, dtype=np.uint8)
            unpacked = np.unpackbits(bits).astype(np.int32)
            acc += unpacked * 2 - 1  # 0/1 → -1/+1
    return np.packbits((acc > 0).astype(np.uint8))


def selectTopStems(stems: list[str], cap: int) -> list[str]:
    """cap 초과 시 *unique* stem 유지 + 빈도 추정 없이 첫 cap 개. 정밀도 위해
    추후 IDF 정렬 가능."""
    seen = set()
    out = []
    for s in stems:
        if s in seen:
            continue
        seen.add(s)
        out.append(s)
        if len(out) >= cap:
            break
    return out


def main() -> None:
    print("=" * 72)
    print("RI-VSA v8 — pairwise bind contextualized sentence hash (표본 100K)")
    print("=" * 72)

    # ── 1. corpus load + 문장 분리 (truncate 후) ──
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

    # ── 2. characteristic table (unique stems 추출 + blake2b) ──
    t0 = time.perf_counter()
    char_cache: dict[str, bytes] = {}
    # 미리 한 패스 — 모든 unique stem 의 characteristic
    sentence_stem_chars: list[list[bytes]] = []
    for sent in sentences:
        toks = tokenizeStems(sent)
        toks_top = selectTopStems(toks, MAX_STEMS_PER_SENTENCE)
        chars: list[bytes] = []
        for tok in toks_top:
            c = char_cache.get(tok)
            if c is None:
                c = characteristic(tok)
                char_cache[tok] = c
            chars.append(c)
        sentence_stem_chars.append(chars)
    print(f"[chars] unique stems {len(char_cache):,} | {time.perf_counter() - t0:.1f}s")

    # ── 3. sentence hash 빌드 (pairwise bind) ──
    t0 = time.perf_counter()
    sentence_hashes = np.zeros((n_sent, HASH_BYTES), dtype=np.uint8)
    last_log = time.perf_counter()
    for sid, chars in enumerate(sentence_stem_chars):
        sentence_hashes[sid] = computeSentenceHash(chars)
        if (sid + 1) % 10_000 == 0:
            elapsed = time.perf_counter() - last_log
            rate = 10_000 / elapsed
            eta = (n_sent - sid - 1) / rate
            print(f"  [hash] {sid + 1:,}/{n_sent:,} | {rate:.0f} sent/s | eta {eta:.0f}s")
            last_log = time.perf_counter()
    print(f"[hash] sentence_hashes {sentence_hashes.nbytes / 1e6:.1f} MB | {time.perf_counter() - t0:.1f}s")

    # ── 4. query hash 함수 ──
    def queryHash(q: str) -> np.ndarray:
        toks = tokenizeStems(q)
        toks_top = selectTopStems(toks, MAX_STEMS_PER_SENTENCE)
        if not toks_top:
            return np.zeros(HASH_BYTES, dtype=np.uint8)
        chars = []
        for tok in toks_top:
            c = char_cache.get(tok)
            if c is None:
                c = characteristic(tok)
            chars.append(c)
        return computeSentenceHash(chars)

    # ── 5. 평가 ──
    print()
    print("─── 평가 셋트 (12 쿼리) ───")
    scores = evaluate(sentence_hashes, queryHash, sent_report_nm, sent_rcept)
    print(formatReport(scores))

    valid = [s for s in scores.values() if not np.isnan(s["precision@5"])]
    if valid:
        avg_p5 = np.mean([s["precision@5"] for s in valid])
        avg_r5 = np.mean([s["recall@5"] for s in valid])
        avg_mrr = np.mean([s["mrr"] for s in valid])
        print()
        print(f"평균 — P@5={avg_p5:.2f}  R@5={avg_r5:.2f}  MRR={avg_mrr:.2f}")

    # ── 6. snippet 데모 (signal 보이는지 직접 확인) ──
    print()
    print("─── snippet 검색 데모 (top 5) ───")
    SHOW = [
        "회사가 돈 빌렸나",
        "자사주 사들였나",
        "공장 짓는 회사",
        "유상증자한 회사",
    ]
    for q in SHOW:
        qh = queryHash(q)
        xored = np.bitwise_xor(sentence_hashes, qh[None, :])
        dist = np.unpackbits(xored, axis=1).sum(axis=1)
        order = np.argpartition(dist, 30)[:30]
        order = order[np.argsort(dist[order])]
        seen = set()
        print(f'\n❓ "{q}"')
        shown = 0
        for sid in order:
            r = sent_rcept[int(sid)]
            if r in seen:
                continue
            seen.add(r)
            snippet = sentences[int(sid)][:80].replace("\n", " ")
            print(f"    d={int(dist[sid]):3d}  [{sent_report_nm[int(sid)][:24]:24s}]  {snippet}")
            shown += 1
            if shown >= 5:
                break


if __name__ == "__main__":
    main()
