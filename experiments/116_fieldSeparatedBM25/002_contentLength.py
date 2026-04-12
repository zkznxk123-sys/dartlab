"""실험 116-002: content 길이 제한별 — posting 수, 인덱스 크기, precision 측정

실험 ID: 116-002
실험명: content를 몇 글자까지 인덱싱할 때 품질/크기 트레이드오프가 최적인가

배경:
- 실험 001에서 content 전문 인덱싱 시 6,190문서에서 13.8M postings
- 4M 문서 선형 확장 시 89억 postings, ~71GB
- content 길이를 자르면 posting 수가 비례 감소
- 문제: 너무 짧게 자르면 본문 검색 품질 하락

가설:
1. [:500]이면 posting 수 4~5x 감소, 품질은 대부분 유지
2. [:200]이면 도입부만 → 본문형 쿼리 놓치기 시작
3. 전문 대비 [:2000]은 큰 차이 없을 것 (실제 중요한 정보는 앞쪽에 집중)

방법:
1. content 길이 limits = [None, 5000, 2000, 1000, 500, 200, 100]
2. 각 limit으로 contentIndex 빌드 → posting 수, 크기 기록
3. 동일 쿼리 세트로 검색 → precision 비교

측정:
- posting 수와 인덱스 크기
- 제목형 쿼리 10개 (회귀 확인)
- 본문형 쿼리 10개 (품질 유지 확인)
- top-5 결과 중 각 쿼리와 관련 있는 문서 수 (간이 precision)

실험일: 2026-04-12
"""

from __future__ import annotations

import math
import time
from collections import defaultdict
from pathlib import Path

import numpy as np
import polars as pl

DATA_DIR = Path("data/dart/allFilings")

print("=" * 60)
print("실험 116-002: content 길이 제한 트레이드오프")
print("=" * 60)

pilotFile = DATA_DIR / "20260331.parquet"
df = pl.read_parquet(pilotFile)
df = df.filter(pl.col("section_content").is_not_null())
print(f"\n로드: {df.height:,}문서\n")


def tokenize(text: str) -> list[str]:
    text = text.strip()
    tokens = set()
    if len(text) >= 2:
        tokens.update(text[i: i + 2] for i in range(len(text) - 1))
    if len(text) >= 3:
        tokens.update(text[i: i + 3] for i in range(len(text) - 2))
    return list(tokens)


def buildFieldIndex(texts: list[str], maxChars: int | None = None) -> dict:
    if maxChars is not None:
        texts = [(t or "")[:maxChars] for t in texts]

    t0 = time.perf_counter()
    stemToId: dict[str, int] = {}
    postings: dict[int, list[tuple[int, int]]] = defaultdict(list)
    docLengths = np.zeros(len(texts), dtype=np.int32)

    for docId, text in enumerate(texts):
        if not text:
            continue
        tokens = tokenize(text)
        docLengths[docId] = len(tokens)
        stemTf: dict[int, int] = defaultdict(int)
        for t in tokens:
            if t not in stemToId:
                stemToId[t] = len(stemToId)
            stemTf[stemToId[t]] += 1
        for sid, tf in stemTf.items():
            postings[sid].append((docId, tf))

    nStems = len(stemToId)
    offsets = np.zeros(nStems + 1, dtype=np.int64)
    for sid in range(nStems):
        offsets[sid + 1] = offsets[sid] + len(postings[sid])

    nPostings = int(offsets[-1])
    docIds = np.zeros(nPostings, dtype=np.int32)
    termFreqs = np.zeros(nPostings, dtype=np.int32)
    for sid in range(nStems):
        start = offsets[sid]
        for i, (docId, tf) in enumerate(postings[sid]):
            docIds[start + i] = docId
            termFreqs[start + i] = tf

    elapsed = time.perf_counter() - t0
    return {
        "stemDict": stemToId,
        "offsets": offsets,
        "docIds": docIds,
        "termFreqs": termFreqs,
        "docLengths": docLengths,
        "avgDocLength": float(docLengths.mean()),
        "nDocs": len(texts),
        "nStems": nStems,
        "nPostings": nPostings,
        "buildTime": elapsed,
    }


def scoreTf(idx: dict, queryTokens: list[str]) -> np.ndarray:
    scores = np.zeros(idx["nDocs"], dtype=np.float32)
    for t in queryTokens:
        sid = idx["stemDict"].get(t)
        if sid is None:
            continue
        s, e = idx["offsets"][sid], idx["offsets"][sid + 1]
        np.add.at(scores, idx["docIds"][s:e], idx["termFreqs"][s:e])
    return scores


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
        docIdsForStem = idx["docIds"][s:e]
        tfs = idx["termFreqs"][s:e].astype(np.float32)
        df = len(docIdsForStem)
        idf = math.log((N - df + 0.5) / (df + 0.5) + 1.0)
        dl = docLens[docIdsForStem].astype(np.float32)
        normTf = tfs * (k1 + 1) / (tfs + k1 * (1 - b + b * dl / avgDl))
        np.add.at(scores, docIdsForStem, idf * normTf)
    return scores


# ═══════════════════════════════════════
# 1. 고정 인덱스 (title/section)
# ═══════════════════════════════════════

print("[빌드] title / section (고정)")
titleIdx = buildFieldIndex(df["report_nm"].fill_null("").to_list())
print(f"  title   : {titleIdx['nStems']:>6} stems, {titleIdx['nPostings']:>10,} postings, {titleIdx['buildTime']:.1f}초")
sectionIdx = buildFieldIndex(df["section_title"].fill_null("").to_list())
print(f"  section : {sectionIdx['nStems']:>6} stems, {sectionIdx['nPostings']:>10,} postings, {sectionIdx['buildTime']:.1f}초")


# ═══════════════════════════════════════
# 2. content 길이별 빌드
# ═══════════════════════════════════════

contentTexts = df["section_content"].fill_null("").to_list()
lengthLimits = [None, 5000, 2000, 1000, 500, 200, 100]
contentIndexes = {}

print("\n[빌드] content (길이별)")
print(f"{'limit':>10} | {'stems':>8} | {'postings':>12} | {'avg토큰':>7} | {'빌드':>6} | {'크기':>8}")
print("-" * 72)

for limit in lengthLimits:
    idx = buildFieldIndex(contentTexts, maxChars=limit)
    contentIndexes[limit] = idx
    sizeMb = (idx["offsets"].nbytes + idx["docIds"].nbytes + idx["termFreqs"].nbytes) / 1024 / 1024
    label = "full" if limit is None else f"[:{limit}]"
    print(f"{label:>10} | {idx['nStems']:>8,} | {idx['nPostings']:>12,} | {idx['avgDocLength']:>7.0f} | {idx['buildTime']:>5.1f}s | {sizeMb:>6.1f}MB")


# ═══════════════════════════════════════
# 3. 검색 함수
# ═══════════════════════════════════════

def normVec(s):
    m = s.max()
    return s / m if m > 0 else s


def searchFieldSeparated(query: str, contentIdx: dict, topK: int = 5) -> list[tuple[int, float]]:
    tokens = tokenize(query)
    t = normVec(scoreTf(titleIdx, tokens))
    s = normVec(scoreTf(sectionIdx, tokens))
    c = normVec(scoreBM25(contentIdx, tokens))
    total = 5.0 * t + 2.0 * s + 1.0 * c
    topIds = np.argsort(-total)[:topK]
    return [(int(i), float(total[i])) for i in topIds if total[i] > 0]


# ═══════════════════════════════════════
# 4. 벤치마크
# ═══════════════════════════════════════

titleQueries = [
    "유상증자", "전환사채", "대표이사 변경", "배당", "자기주식 취득",
    "합병", "감자", "주주총회", "사업보고서", "신주인수권",
]

contentQueries = [
    "반도체 업황", "원재료 가격 상승", "환율 변동 리스크", "연구개발 투자 확대",
    "해외 매출 비중", "공장 가동률", "신규 수주", "경쟁 심화",
    "구조조정 계획", "품질 문제",
]


def measureHits(queries: list[str], label: str):
    print(f"\n── {label} — content limit별 hit 수 ──")
    header = f"{'쿼리':>16} |"
    for limit in lengthLimits:
        label2 = "full" if limit is None else f"{limit}"
        header += f" {label2:>6} |"
    print(header)
    print("-" * len(header))

    for q in queries:
        row = f"{q:>16} |"
        for limit in lengthLimits:
            hits = searchFieldSeparated(q, contentIndexes[limit], topK=5)
            row += f" {len(hits):>6} |"
        print(row)


measureHits(titleQueries, "제목형 쿼리 (현재 방식도 잘 되던 것)")
measureHits(contentQueries, "본문형 쿼리 (현재 방식으로 찾기 힘든 것)")


# ═══════════════════════════════════════
# 5. 4M 문서 확장 추정
# ═══════════════════════════════════════

print("\n── 4M 문서 선형 확장 추정 ──")
scale = 4_000_000 / df.height
print(f"{'limit':>10} | {'postings 추정':>18} | {'크기 추정':>12}")
print("-" * 50)
for limit in lengthLimits:
    idx = contentIndexes[limit]
    estPostings = int(idx["nPostings"] * scale)
    estGb = estPostings * 8 / 1024**3
    label = "full" if limit is None else f"[:{limit}]"
    print(f"{label:>10} | {estPostings:>18,} | {estGb:>10.1f}GB")


# ═══════════════════════════════════════
# 6. 본문형 쿼리 상세 (limit=500 기준으로)
# ═══════════════════════════════════════

print("\n── 본문형 쿼리 상세 (content [:500]) ──")
for q in contentQueries:
    hits = searchFieldSeparated(q, contentIndexes[500], topK=3)
    print(f"\n쿼리: '{q}'")
    for i, (docId, score) in enumerate(hits):
        row = df.row(docId, named=True)
        print(f"  {i+1}. [score={score:.2f}] {row['corp_name']} | {row['report_nm'][:50]}")
