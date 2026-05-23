"""RI-VSA v10e — v10d + 자산 저장 + 12 쿼리 × top-10 풍부 snippet.

배경
----
v10d 자동 metric 은 평가셋 결함 때문에 신호 못 잡음. snippet 으로 보면 ~85%
정답. *수동 라벨링* 으로 진짜 recall@5 측정 필요.

이 파일:
1. v10c/v10d 의 빌드를 재현 (corpus → cooc → PPMI → sig)
2. 자산 저장 (data/_scratch_fm/v10e/) — 다음 평가에서 reload 가능
3. 12 쿼리 × top-10 풍부 snippet (section_title + body 첫 100 자) 출력
4. 그 출력을 보고 내가 (LLM) 직접 정답 판단 → 수동 라벨 평가

결과 (작성 후 채움)
------------------
"""

from __future__ import annotations

import json
import re
import time
from pathlib import Path

import numpy as np
import polars as pl
from evalSet import QUERIES

ALLFILINGS_DIR = Path("data/dart/allFilings")
ASSETS_DIR = Path("data/_scratch_fm/v10e")
ASSETS_DIR.mkdir(parents=True, exist_ok=True)

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
    print("RI-VSA v10e — full 20M + 자산 저장 + 12 쿼리 풍부 snippet")
    print("=" * 72)

    # 캐시 확인 — 이미 빌드돼 있으면 reload
    cache_files = [
        ASSETS_DIR / "sentence_sigs.npy",
        ASSETS_DIR / "meaningProfile.npy",
        ASSETS_DIR / "global_mean.npy",
        ASSETS_DIR / "meta.json",
    ]
    if all(p.exists() for p in cache_files):
        print("[cache] 캐시 발견 → reload")
        sentence_sigs_packed = np.load(ASSETS_DIR / "sentence_sigs.npy")
        meaningProfile = np.load(ASSETS_DIR / "meaningProfile.npy")
        global_mean = np.load(ASSETS_DIR / "global_mean.npy")
        with open(ASSETS_DIR / "meta.json", encoding="utf-8") as f:
            meta = json.load(f)
        sentences = meta["sentences"]
        sent_rcept = meta["rcept"]
        sent_report_nm = meta["report_nm"]
        sent_section_title = meta["section_title"]
        n_sent = len(sentences)
        print(f"[cache] 문장 {n_sent:,} | sigs {sentence_sigs_packed.nbytes / 1e6:.1f} MB")
    else:
        # ── 1. corpus + 문장 분리 + bins (한 패스) ──
        t0 = time.perf_counter()
        files = sorted(p for p in ALLFILINGS_DIR.glob("2026*.parquet") if "_meta" not in p.name)
        print(f"[files] {len(files)} 일치 parquet")

        cooc = np.zeros((K_BINS, K_BINS), dtype=np.float64)
        bin_freq = np.zeros(K_BINS, dtype=np.float64)
        sentences: list[str] = []
        sent_rcept: list[str] = []
        sent_report_nm: list[str] = []
        sent_section_title: list[str] = []
        sentence_bins_list: list[np.ndarray] = []
        for fi, f in enumerate(files):
            df = (
                pl.read_parquet(
                    f,
                    columns=[
                        "rcept_no",
                        "report_nm",
                        "section_title",
                        "section_content",
                    ],
                )
                .filter(pl.col("section_content").is_not_null())
                .with_columns(pl.col("section_content").str.slice(0, MAX_SECTION_CHARS))
            )
            for row in df.iter_rows():
                r, rn, stitle, txt = row
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
                    sent_report_nm.append(rn or "")
                    sent_section_title.append(stitle or "")
                    sentence_bins_list.append(bins)
            del df
            if (fi + 1) % 10 == 0:
                elapsed = time.perf_counter() - t0
                print(f"  [load] file {fi + 1}/{len(files)} | sentences {len(sentences):,} | elapsed {elapsed:.0f}s")
        n_sent = len(sentences)
        print(f"[corpus] 문장 {n_sent:,} | {time.perf_counter() - t0:.1f}s")

        # ── 2. PPMI ──
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
        global_mean = meaningProfile.mean(axis=0)
        print(f"[ppmi] nnz={int((ppmi > 0).sum()):,}")

        # ── 3. 문장 시그니처 ──
        t0 = time.perf_counter()
        sentence_sigs_packed = np.zeros((n_sent, K_BINS // 8), dtype=np.uint8)
        for sid in range(n_sent):
            bins = sentence_bins_list[sid]
            if bins.size == 0:
                continue
            sig = meaningProfile[bins].mean(axis=0)
            bits = (sig > global_mean).astype(np.uint8)
            sentence_sigs_packed[sid] = np.packbits(bits)
            if (sid + 1) % 5_000_000 == 0:
                print(f"  [sig] {sid + 1:,}/{n_sent:,}")
        print(f"[sig] {sentence_sigs_packed.nbytes / 1e6:.1f} MB | {time.perf_counter() - t0:.1f}s")

        # ── 4. 자산 저장 ──
        t0 = time.perf_counter()
        np.save(ASSETS_DIR / "sentence_sigs.npy", sentence_sigs_packed)
        np.save(ASSETS_DIR / "meaningProfile.npy", meaningProfile)
        np.save(ASSETS_DIR / "global_mean.npy", global_mean)
        meta = {
            "sentences": sentences,
            "rcept": sent_rcept,
            "report_nm": sent_report_nm,
            "section_title": sent_section_title,
        }
        with open(ASSETS_DIR / "meta.json", "w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False)
        print(f"[save] 자산 저장 {ASSETS_DIR} | {time.perf_counter() - t0:.1f}s")

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

    # ── 6. 12 쿼리 × top-10 풍부 snippet ──
    print()
    print("=" * 72)
    print("12 쿼리 × top-10 풍부 snippet (수동 라벨링 용)")
    print("=" * 72)

    for q in QUERIES:
        order, dist = search(q.text, top_k=50)
        seen = set()
        print(f"\n{'=' * 72}")
        print(f'❓ "{q.text}"  (정답 regex: {q.relevance.pattern})')
        print(f"{'=' * 72}")
        shown = 0
        for sid, d in zip(order, dist):
            r = sent_rcept[int(sid)]
            if r in seen:
                continue
            seen.add(r)
            snippet = sentences[int(sid)][:120].replace("\n", " ")
            rn = sent_report_nm[int(sid)] or ""
            stitle = sent_section_title[int(sid)] or ""
            print(
                f"  [{shown + 1:2d}] d={int(d):3d}  rcept={r}"
                f"\n        report_nm    : {rn[:60]}"
                f"\n        section_title: {stitle[:60]}"
                f"\n        snippet      : {snippet}"
            )
            shown += 1
            if shown >= 10:
                break


if __name__ == "__main__":
    main()
