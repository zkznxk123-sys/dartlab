"""RI-VSA C — 문장 단위 정체성 해시 (search 단위 와 일치).

목적
----
사용자 목표: "search 로 입력되면 그것도 해시해서 바로 매칭 가능하는 것 까지".
v2 (riVsaSearchV2) 는 *섹션 단위* hash. 너무 큼 (수만~수십만 자) — 한 섹션이
다양한 의미 섞임.

C 는 *문장 단위*:
- 한 섹션 → 문장 분리 → 각 문장 hash
- 쿼리 → 같은 hash 함수 → 문장 단위 NN 매칭
- 정답 회수 보다 *snippet 회수* 가 user-facing 가까움 (RAG 같은 사용감)

핵심 알고리즘
------------
문장 분리: section_content → splitlines() + 줄바꿈 후 . ! ? 분할.
문장 hash = Σ over stem∈문장 of (contextSigned[stem] · idf[stem]) → sign-pack.
정확히 V2 와 동일한 hash 함수 — 단위만 문장으로.

이게 V2 와 다른 이유:
- 섹션 1 개 = 수십 문장 → 의미 mixed
- 문장 1 개 = 한 명제 → 의미 응집 → hash 변별력 ↑
- 또한 user-facing 결과가 "관련 문장 1 줄" 로 정확함

설계
----
- variant 선택: B (riVsaSearchV2) 결과 우승 자산. 일단 V7.
- 문장 분리는 정규식 — 한국어 마침표 ⊆ "." + "다.\n" + "다.  " 등.
- 메모리 — 53K 섹션 → 추정 ~300-500K 문장. 32B 해시 → ~16 MB. 부담 없음.

결과 (2026-05-20, V7 자산 + 417,201 섹션 → 20,338,065 문장)
-----------------------------------------------------------
- 빌드: corpus+split 84.8s, hash chunk 1770s (29 분), sentence_hashes 650.8 MB
- 섹션 길이 cap 30K, 섹션당 문장 cap 200, chunk 50K (Polars Rust 힙 누수 회피)

평가 (12 쿼리, rcept dedup top-5/10, report_nm regex ground truth):

| 메트릭 | V2 섹션 단위 (V7) | C 문장 단위 (V7) |
|---|---|---|
| 평균 P@5 | 0.05 | **0.05** |
| 평균 R@5 | 0.00 | 0.00 |
| 평균 MRR | 0.08 | **0.04** |
| 빌드 시간 | ~17 분 | ~30 분 |

쿼리별 — 12 중 11 개 *완전 0*. 신호:
- 최대주주 변경 (정답 303): P@5=0.60 P@10=0.70 MRR=0.50 ← 유일한 정상 신호

snippet 데모가 *근본 원인* 노출 (d=0 매칭이 boilerplate):
- "회사가 돈 빌렸나" → d=0: `| 대산항만운영㈜ | 2011.08.22 |...` (표 셀)
- "자사주 사들였나" → d=0: `※ 기타 자세한 사항은...` (사업보고서 boilerplate)
- "공장 짓는 회사" → d=8: `세포막 단백질 또는 분비 단백질을 표적함` (생물학)

결론 — RI-VSA 의 근본 가설 fail
-----------------------------
"주변 stem 들의 의미가 합쳐져서 문장 의미가 된다" 는 Firth 1957 분포 가설의
자연스러운 확장처럼 보였지만, 실제로는 작동하지 않음.

이유:
1. **쿼리 어휘 vs 도메인 어휘의 다른 클러스터**.
   "돈 빌렸나" 의 ngram (회사, 사가, 가 돈) 은 corpus 의 흔한 어휘 → contextHash
   가중 합산 시 거의 zero vector → boilerplate 문장이 d=0 매칭 (boilerplate 도
   무작위 분포 가까움).
2. **단위 축소 (섹션→문장) 가 신호 안 강화**. P@5 동일 (0.05).
3. **stem 응집 ≠ 검색 정확도**. V7 자기↔자사 d=9 가 자연어 쿼리 검색으로 옮겨지지
   않음. 응집은 어휘 동의어 측정, 검색은 *문장-쿼리 다리* 필요.

다음 단계 (재설계)
-----------------
- D-1. BM25 baseline 측정 (5 분) — RI-VSA 가 정말 BM25 보다 못한지 확정
- D-2. RI-VSA 트랙 폐기 — substring (FM-index) + 도메인 사전 (자사주 → 자기주식취득)
  으로 회귀. 사용자 원래 search 트랙 강화.
- D-3. *또는* 쿼리 자체 변환 — "돈 빌렸나" → "차입" 으로 인간 사전 매핑 후 RI-VSA
  적용. 자연어 추상화는 인간 사전이 담당, RI-VSA 는 동의어 확장만.
"""

from __future__ import annotations

import json
import re
import time
from pathlib import Path

import numpy as np
import polars as pl
from evalSet import QUERIES, evaluate, formatReport

ALLFILINGS_DIR = Path("data/dart/allFilings")
HASH_BYTES = 32
HASH_BITS = 256
NGRAM_NS = (2, 3)
MAX_TOKENS_PER_SENTENCE = 400
MIN_SENTENCE_LEN = 8
MAX_SECTION_CHARS = 30_000  # 그 이상은 표 outlier — 의미 무의미
MAX_SENTS_PER_SECTION = 200  # 한 섹션 max 200 문장 (긴 표 잘라냄)
CHUNK_SIZE = 50_000  # 문장 hash chunk

DEFAULT_VARIANT = "V7"

# 한국어 + 영어 문장 종결.
# "...다.\n", "...니다.", "...했음.", 줄바꿈, ; 등.
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


def tokenizeStems(s: str, cap: int = MAX_TOKENS_PER_SENTENCE) -> list[str]:
    if not s:
        return []
    out: list[str] = []
    for n in NGRAM_NS:
        if len(s) < n:
            continue
        upto = min(len(s) - n + 1, cap)
        out.extend(s[i : i + n] for i in range(upto))
    return out


def hashToSignedFloat(packed: np.ndarray, *, idf: np.ndarray) -> np.ndarray:
    bits = np.unpackbits(packed, axis=1).astype(np.int8)
    signed = (bits * 2 - 1).astype(np.float32)
    signed *= idf[:, None]
    return signed


def loadVariant(name: str) -> tuple[np.ndarray, dict[str, int]]:
    d = Path(f"data/_scratch_fm/riVsa{name}")
    packed = np.load(d / "contextHash.npy")
    df = np.load(d / "df.npy")
    stems = json.loads((d / "stems.json").read_text(encoding="utf-8"))
    g2id = {s: i for i, s in enumerate(stems)}
    idf = np.log(df.max() / np.maximum(df, 1.0)).astype(np.float32)
    contextSigned = hashToSignedFloat(packed, idf=idf)
    return contextSigned, g2id


def hashSentencesChunked(
    sentences: list[str],
    g2id: dict[str, int],
    contextSigned: np.ndarray,
    chunk_size: int = CHUNK_SIZE,
    log_every: int = 500_000,
) -> np.ndarray:
    """chunk 단위 문장 해시 — sparse matrix 없이 직접 누적.

    한 chunk:
      ids_per_sentence = [tokenize → g2id 매핑]
      acc_chunk = sum over sentences in chunk of contextSigned[ids].sum(0)  per row
      pack bits → uint8 (chunk_n, 32)

    메모리 — chunk_size × HASH_BITS float32 = 50K × 256 × 4 = 51 MB / chunk.
    """
    n = len(sentences)
    out = np.zeros((n, HASH_BYTES), dtype=np.uint8)
    t_last = time.perf_counter()

    for c0 in range(0, n, chunk_size):
        c1 = min(c0 + chunk_size, n)
        chunk_n = c1 - c0
        acc = np.zeros((chunk_n, HASH_BITS), dtype=np.float32)
        for i, s in enumerate(sentences[c0:c1]):
            ids = set()
            for tok in tokenizeStems(s):
                gid = g2id.get(tok)
                if gid is not None:
                    ids.add(gid)
            if ids:
                ids_arr = np.fromiter(ids, dtype=np.int32, count=len(ids))
                acc[i] = contextSigned[ids_arr].sum(axis=0)
        bits = (acc > 0).astype(np.uint8)
        out[c0:c1] = np.packbits(bits, axis=1)
        if (c1 // log_every) > (c0 // log_every):
            elapsed = time.perf_counter() - t_last
            print(f"  [chunk] {c1:,}/{n:,} | {elapsed:.0f}s")
            t_last = time.perf_counter()
    return out


def main() -> None:
    print("=" * 72)
    print(f"RI-VSA C — 문장 단위 정체성 해시 (variant={DEFAULT_VARIANT})")
    print("=" * 72)

    # ── 1. corpus + 문장 분리 (polars-side truncate 후 split) ──
    t0 = time.perf_counter()
    files = sorted(p for p in ALLFILINGS_DIR.glob("2026*.parquet") if "_meta" not in p.name)
    sentences: list[str] = []
    sent_rcept: list[str] = []
    sent_report_nm: list[str] = []
    n_sec_total = 0
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
        # 파일 단위로 iter — 메모리 누수 회피
        for row in df.iter_rows():
            r, rn, txt = row
            for sent in splitSentences(txt):
                sentences.append(sent)
                sent_rcept.append(r)
                sent_report_nm.append(rn)
        del df
    n_sent = len(sentences)
    print(
        f"[corpus+split] 섹션 {n_sec_total:,} → 문장 {n_sent:,} | "
        f"avg {n_sent / max(n_sec_total, 1):.1f} sent/sec | "
        f"{time.perf_counter() - t0:.1f}s"
    )

    # ── 2. variant 자산 + chunked sentence hash (sparse matrix 우회) ──
    t0 = time.perf_counter()
    contextSigned, g2id = loadVariant(DEFAULT_VARIANT)
    print(f"[load] {DEFAULT_VARIANT} | {time.perf_counter() - t0:.1f}s")

    t0 = time.perf_counter()
    sentence_hashes = hashSentencesChunked(sentences, g2id, contextSigned)
    print(f"[hash] sentenceHashes {sentence_hashes.nbytes / 1e6:.1f} MB | {time.perf_counter() - t0:.1f}s")

    # ── 3. 평가 (rcept 단위 평가 — 문장 → rcept 매핑) ──
    def queryHash(q: str) -> np.ndarray:
        toks = tokenizeStems(q, cap=200)
        ids = [g2id[t] for t in toks if t in g2id]
        if not ids:
            return np.zeros(HASH_BYTES, dtype=np.uint8)
        ids = np.asarray(ids, dtype=np.int32)
        acc = contextSigned[ids].sum(axis=0)
        return np.packbits((acc > 0).astype(np.uint8))

    print()
    print("─── 평가 셋트 (12 쿼리) ───")
    scores = evaluate(sentence_hashes, queryHash, sent_report_nm, sent_rcept)
    print(formatReport(scores))

    valid = [s for s in scores.values() if not np.isnan(s["precision@5"])]
    if valid:
        avg = {
            "P@5": np.mean([s["precision@5"] for s in valid]),
            "P@10": np.mean([s["precision@10"] for s in valid]),
            "R@5": np.mean([s["recall@5"] for s in valid]),
            "R@10": np.mean([s["recall@10"] for s in valid]),
            "MRR": np.mean([s["mrr"] for s in valid]),
        }
        print()
        print(f"평균 — P@5={avg['P@5']:.2f}  R@5={avg['R@5']:.2f}  MRR={avg['MRR']:.2f}")

    # ── 4. 사용자 눈 — top 5 문장 직접 출력 ──
    print()
    print("─── snippet 검색 데모 (top 5 문장) ───")
    SHOW = ["회사가 돈 빌렸나", "자사주 사들였나", "공장 짓는 회사"]
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
