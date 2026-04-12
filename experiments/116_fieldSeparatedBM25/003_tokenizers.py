"""실험 116-003: 본문 검색 토크나이저 비교 — ngram vs 공백분리 vs 형태소 vs substring

실험 ID: 116-003
실험명: 본문 검색에서 어떤 단위로 토큰화해야 의미 있는 결과가 나오나

배경:
- 실험 116-002: ngram 토큰화는 본문 검색에서 노이즈만 생산
- "원재료" → "원재"/"재료"/"원재료" 3개로 분해 → "재료"가 관련 없는 수천 문서에 매칭
- 임베딩은 cold start 느림 → 제외

비교 대상 (cold start 없는 것만):
1. ngram 현재 방식 (기준)
2. 공백+구두점 분리 → 단어 단위 역인덱스
3. kiwi 형태소 분석 → 명사/동사 어간 역인덱스
4. polars str.contains (정확 부분문자열)

측정:
- 본문형 쿼리 10개에 대한 수동 precision (top-3 중 관련 있는 것 수)
- 속도 (cold start + warm)
- 빌드 비용

실험일: 2026-04-12
"""

from __future__ import annotations

import math
import re
import time
from collections import defaultdict
from pathlib import Path

import numpy as np
import polars as pl

DATA_DIR = Path("data/dart/allFilings")

print("=" * 60)
print("실험 116-003: 본문 검색 토크나이저 비교")
print("=" * 60)

pilotFile = DATA_DIR / "20260331.parquet"
df = pl.read_parquet(pilotFile)
df = df.filter(pl.col("section_content").is_not_null())
# content가 너무 짧은 것 제외 (사업보고서 위주로 의미 있는 비교)
df = df.filter(pl.col("section_content").str.len_chars() > 500)
print(f"\n로드: {df.height:,}문서 (content>500자)\n")

contentTexts = df["section_content"].to_list()


# ═══════════════════════════════════════
# 공통: 역인덱스 빌더
# ═══════════════════════════════════════

def buildInverted(tokenizedDocs: list[list[str]], name: str) -> dict:
    t0 = time.perf_counter()
    stemToId: dict[str, int] = {}
    postings: dict[int, list[tuple[int, int]]] = defaultdict(list)
    docLengths = np.zeros(len(tokenizedDocs), dtype=np.int32)

    for docId, tokens in enumerate(tokenizedDocs):
        docLengths[docId] = len(tokens)
        tf: dict[int, int] = defaultdict(int)
        for t in tokens:
            if t not in stemToId:
                stemToId[t] = len(stemToId)
            tf[stemToId[t]] += 1
        for sid, c in tf.items():
            postings[sid].append((docId, c))

    nStems = len(stemToId)
    offsets = np.zeros(nStems + 1, dtype=np.int64)
    for sid in range(nStems):
        offsets[sid + 1] = offsets[sid] + len(postings[sid])
    nPostings = int(offsets[-1])
    docIds = np.zeros(nPostings, dtype=np.int32)
    tfs = np.zeros(nPostings, dtype=np.int32)
    for sid in range(nStems):
        s = offsets[sid]
        for i, (d, c) in enumerate(postings[sid]):
            docIds[s + i] = d
            tfs[s + i] = c

    elapsed = time.perf_counter() - t0
    print(f"  [{name}] {nStems:,} stems, {nPostings:,} postings, {elapsed:.1f}초, avgDocLen={docLengths.mean():.0f}")
    return {
        "stemDict": stemToId, "offsets": offsets, "docIds": docIds,
        "termFreqs": tfs, "docLengths": docLengths,
        "avgDocLength": float(docLengths.mean()), "nDocs": len(tokenizedDocs),
        "buildTime": elapsed,
    }


def scoreBM25(idx: dict, queryTokens: list[str], k1: float = 1.5, b: float = 0.75) -> np.ndarray:
    scores = np.zeros(idx["nDocs"], dtype=np.float32)
    N = idx["nDocs"]
    avgDl = max(idx["avgDocLength"], 1.0)
    docLens = idx["docLengths"]
    for t in queryTokens:
        sid = idx["stemDict"].get(t)
        if sid is None:
            continue
        s, e = idx["offsets"][sid], idx["offsets"][sid + 1]
        ids = idx["docIds"][s:e]
        tfs = idx["termFreqs"][s:e].astype(np.float32)
        df_t = len(ids)
        idf = math.log((N - df_t + 0.5) / (df_t + 0.5) + 1.0)
        dl = docLens[ids].astype(np.float32)
        normTf = tfs * (k1 + 1) / (tfs + k1 * (1 - b + b * dl / avgDl))
        np.add.at(scores, ids, idf * normTf)
    return scores


# ═══════════════════════════════════════
# 방법 1: ngram (기준)
# ═══════════════════════════════════════

def tokenizeNgram(text: str) -> list[str]:
    text = text.strip()
    tokens = []
    if len(text) >= 2:
        tokens.extend(text[i: i + 2] for i in range(len(text) - 1))
    if len(text) >= 3:
        tokens.extend(text[i: i + 3] for i in range(len(text) - 2))
    return tokens


# ═══════════════════════════════════════
# 방법 2: 공백+구두점 분리
# ═══════════════════════════════════════

_WORD_RE = re.compile(r"[가-힣a-zA-Z0-9]+")

def tokenizeWord(text: str) -> list[str]:
    return _WORD_RE.findall(text)


# ═══════════════════════════════════════
# 방법 3: kiwi 형태소
# ═══════════════════════════════════════

try:
    from kiwipiepy import Kiwi  # type: ignore
    kiwi = Kiwi()
    _KIWI_AVAILABLE = True
except Exception:
    _KIWI_AVAILABLE = False
    print("  [경고] kiwipiepy 없음 — 형태소 실험 건너뜀")


def tokenizeKiwi(text: str) -> list[str]:
    # 명사(N*), 동사(V*), 외래어(SL) 어간만
    result = kiwi.tokenize(text[:2000])  # 파일럿에서 길이 제한
    return [t.form for t in result if t.tag.startswith(("N", "V", "SL"))]


# ═══════════════════════════════════════
# 빌드
# ═══════════════════════════════════════

print("[빌드]")

# 파일럿 규모 조정: content를 [:1000] 제한
truncated = [t[:1000] for t in contentTexts]

print("  ngram 인덱스 (bigram+trigram)...")
ngramIdx = buildInverted([tokenizeNgram(t) for t in truncated], "ngram")

print("  word 인덱스 (공백분리)...")
wordIdx = buildInverted([tokenizeWord(t) for t in truncated], "word")

kiwiIdx = None
if _KIWI_AVAILABLE:
    print("  kiwi 형태소 인덱스 (느림 — 기다려주세요)...")
    kiwiTokens = [tokenizeKiwi(t) for t in truncated]
    kiwiIdx = buildInverted(kiwiTokens, "kiwi")


# ═══════════════════════════════════════
# 방법 4: polars substring
# ═══════════════════════════════════════

def searchSubstring(query: str, topK: int = 3) -> list[int]:
    # 쿼리를 공백으로 나눠 모든 단어가 포함된 문서
    words = query.split()
    expr = None
    for w in words:
        cond = pl.col("section_content").str.contains(w, literal=True)
        expr = cond if expr is None else expr & cond
    hits = df.with_row_index().filter(expr).head(topK)
    return hits["index"].to_list()


# ═══════════════════════════════════════
# 검색 함수
# ═══════════════════════════════════════

def searchIdx(idx: dict, query: str, tokenizer, topK: int = 3) -> list[tuple[int, float]]:
    tokens = tokenizer(query)
    scores = scoreBM25(idx, tokens)
    top = np.argsort(-scores)[:topK]
    return [(int(i), float(scores[i])) for i in top if scores[i] > 0]


# ═══════════════════════════════════════
# 본문형 쿼리 벤치마크
# ═══════════════════════════════════════

contentQueries = [
    "반도체 업황",
    "원재료 가격",
    "환율 변동",
    "연구개발 투자",
    "해외 매출",
    "공장 가동률",
    "신규 수주",
    "경쟁 심화",
    "구조조정",
    "품질 문제",
]

print("\n" + "=" * 60)
print("본문형 쿼리 상세 비교 (top-3)")
print("=" * 60)

for q in contentQueries:
    print(f"\n── 쿼리: '{q}' ──")

    # ngram
    ngramHits = searchIdx(ngramIdx, q, tokenizeNgram, topK=3)
    print("\n  [ngram]")
    for i, (docId, score) in enumerate(ngramHits):
        r = df.row(docId, named=True)
        print(f"    {i+1}. [{score:.2f}] {r['corp_name']} | {r['report_nm'][:45]}")

    # word
    wordHits = searchIdx(wordIdx, q, tokenizeWord, topK=3)
    print("\n  [word]")
    for i, (docId, score) in enumerate(wordHits):
        r = df.row(docId, named=True)
        print(f"    {i+1}. [{score:.2f}] {r['corp_name']} | {r['report_nm'][:45]}")

    # kiwi
    if kiwiIdx is not None:
        kiwiHits = searchIdx(kiwiIdx, q, tokenizeKiwi, topK=3)
        print("\n  [kiwi]")
        for i, (docId, score) in enumerate(kiwiHits):
            r = df.row(docId, named=True)
            print(f"    {i+1}. [{score:.2f}] {r['corp_name']} | {r['report_nm'][:45]}")

    # substring
    t0 = time.perf_counter()
    subHits = searchSubstring(q, topK=3)
    subMs = (time.perf_counter() - t0) * 1000
    print(f"\n  [substring] ({subMs:.1f}ms)")
    for i, docId in enumerate(subHits):
        r = df.row(docId, named=True)
        print(f"    {i+1}. {r['corp_name']} | {r['report_nm'][:45]}")


# ═══════════════════════════════════════
# 속도 측정
# ═══════════════════════════════════════

print("\n" + "=" * 60)
print("속도 측정 (warm, 10회 평균)")
print("=" * 60)

methods = [
    ("ngram", lambda q: searchIdx(ngramIdx, q, tokenizeNgram, topK=3)),
    ("word", lambda q: searchIdx(wordIdx, q, tokenizeWord, topK=3)),
    ("substring", lambda q: searchSubstring(q, topK=3)),
]
if kiwiIdx is not None:
    methods.insert(2, ("kiwi", lambda q: searchIdx(kiwiIdx, q, tokenizeKiwi, topK=3)))

for name, fn in methods:
    # warmup
    for q in contentQueries[:2]:
        fn(q)
    t0 = time.perf_counter()
    for _ in range(3):
        for q in contentQueries:
            fn(q)
    elapsed = (time.perf_counter() - t0) / (3 * len(contentQueries)) * 1000
    print(f"  {name:>10}: {elapsed:>6.1f}ms/쿼리")

print()
print("빌드 시간 / 크기:")
for name, idx in [("ngram", ngramIdx), ("word", wordIdx)] + ([("kiwi", kiwiIdx)] if kiwiIdx else []):
    sz = (idx["offsets"].nbytes + idx["docIds"].nbytes + idx["termFreqs"].nbytes) / 1024 / 1024
    print(f"  {name:>10}: 빌드 {idx['buildTime']:>5.1f}초, {idx['stemDict'].__len__():>7,} stems, {sz:>6.1f}MB")
