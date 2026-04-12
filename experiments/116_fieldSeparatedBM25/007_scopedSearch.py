"""실험 116-007: scope 분리 — title 전용 vs content 전용 독립 검색

실험 ID: 116-007
실험명: 하나의 가중치 합산 대신, scope별 독립 엔진

문제 (실험 005-006):
- title ngram + content BM25 합산 시 정규화가 weak match 뻥튀기
- "원재료 가격 급등" 쿼리에 무관한 공시가 상위 차지
- 서로 다른 쿼리 유형을 한 엔진에 욱여넣으려다 품질 저하

재설계:
- scope="title"  — title ngram 전용 (현재 95% 방식 유지)
- scope="content" — content word BM25 전용
- scope="both"   — 두 결과를 별도로 반환

검증:
- 제목형 쿼리에서 scope="title" 품질 (기존 95% 유지 확인)
- 본문형 쿼리에서 scope="content" 품질 (실제 관련 문서 top-3에 오는가)

실험일: 2026-04-12
"""

from __future__ import annotations

import gc
import math
import re
import time
from collections import defaultdict
from pathlib import Path

import numpy as np
import polars as pl

print("실험 116-007: scope 분리 검색")
print("=" * 60)

_WORD_RE = re.compile(r"[가-힣a-zA-Z0-9]+")


def tokenizeWord(text: str) -> list[str]:
    return _WORD_RE.findall(text)


def tokenizeNgram(text: str) -> list[str]:
    tokens = []
    text = text.strip()
    if len(text) >= 2:
        tokens.extend(text[i: i + 2] for i in range(len(text) - 1))
    if len(text) >= 3:
        tokens.extend(text[i: i + 3] for i in range(len(text) - 2))
    return tokens


class IncrementalFieldIndex:
    def __init__(self, tokenizer):
        self.tokenizer = tokenizer
        self.stemToId: dict[str, int] = {}
        self.postings: dict[int, list[tuple[int, int]]] = defaultdict(list)
        self.docLengths: list[int] = []

    def addDoc(self, text: str):
        docId = len(self.docLengths)
        if not text:
            self.docLengths.append(0)
            return
        toks = self.tokenizer(text)
        self.docLengths.append(len(toks))
        tf: dict[int, int] = defaultdict(int)
        for t in toks:
            if t not in self.stemToId:
                self.stemToId[t] = len(self.stemToId)
            tf[self.stemToId[t]] += 1
        for sid, c in tf.items():
            self.postings[sid].append((docId, c))

    def finalize(self) -> dict:
        n = len(self.docLengths)
        nStems = len(self.stemToId)
        offsets = np.zeros(nStems + 1, dtype=np.int64)
        for sid in range(nStems):
            offsets[sid + 1] = offsets[sid] + len(self.postings[sid])
        nP = int(offsets[-1])
        docIds = np.zeros(nP, dtype=np.int32)
        tfs = np.zeros(nP, dtype=np.int32)
        for sid in range(nStems):
            s = offsets[sid]
            for i, (d, c) in enumerate(self.postings[sid]):
                docIds[s + i] = d
                tfs[s + i] = c
        docLengths = np.array(self.docLengths, dtype=np.int32)
        self.postings.clear()
        self.docLengths = []
        return {
            "stemDict": self.stemToId, "offsets": offsets, "docIds": docIds,
            "termFreqs": tfs, "docLengths": docLengths,
            "avgDocLength": float(docLengths.mean()) if n > 0 else 0.0,
            "nDocs": n,
        }


docsFiles = sorted(Path("data/dart/docs").glob("*.parquet"))[:100]
allFilesDates = sorted(Path("data/dart/allFilings").glob("2026*.parquet"))[-30:]

titleIdx = IncrementalFieldIndex(tokenizeNgram)
sectionIdx = IncrementalFieldIndex(tokenizeNgram)
contentIdx = IncrementalFieldIndex(tokenizeWord)
metaRows: list[dict] = []
contentTexts: list[str] = []  # content 저장 (품질 검증용)
CONTENT_LIMIT = 1500


def processBatch(df: pl.DataFrame, source: str):
    for row in df.iter_rows(named=True):
        report = row.get("report_nm") or ""
        sect = row.get("section_title") or ""
        content = (row.get("section_content") or "")[:CONTENT_LIMIT]
        titleIdx.addDoc(report)
        sectionIdx.addDoc(sect)
        contentIdx.addDoc(content)
        metaRows.append({
            "corp_name": row.get("corp_name", ""), "source": source,
            "report_nm": report, "section_title": sect,
        })
        contentTexts.append(content)


print("\n[데이터 로드]")
t0 = time.perf_counter()
for f in docsFiles:
    try:
        df = pl.read_parquet(f).filter(pl.col("section_content").is_not_null())
        processBatch(df, "docs")
    except Exception:
        continue
for f in allFilesDates:
    try:
        df = pl.read_parquet(f).filter(pl.col("section_content").is_not_null())
        processBatch(df, "allFilings")
    except Exception:
        continue

print(f"  {len(metaRows):,}문서, {time.perf_counter()-t0:.0f}초")

title = titleIdx.finalize()
section = sectionIdx.finalize()
content = contentIdx.finalize()
gc.collect()


# ═══════════════════════════════════════
# 스코어 함수
# ═══════════════════════════════════════

def scoreBM25(fi, tokens, k1=1.5, b=0.75):
    scores = np.zeros(fi["nDocs"], dtype=np.float32)
    N = fi["nDocs"]
    avgDl = max(fi["avgDocLength"], 1.0)
    for t in tokens:
        sid = fi["stemDict"].get(t)
        if sid is None:
            continue
        s, e = fi["offsets"][sid], fi["offsets"][sid + 1]
        ids = fi["docIds"][s:e]
        tfs = fi["termFreqs"][s:e].astype(np.float32)
        df_t = len(ids)
        idf = math.log((N - df_t + 0.5) / (df_t + 0.5) + 1.0)
        dl = fi["docLengths"][ids].astype(np.float32)
        normTf = tfs * (k1 + 1) / (tfs + k1 * (1 - b + b * dl / avgDl))
        np.add.at(scores, ids, idf * normTf)
    return scores


def searchTitle(query: str, topK: int = 5):
    tn = tokenizeNgram(query)
    t = scoreBM25(title, tn)
    s = scoreBM25(section, tn)
    total = 5.0 * t + 2.0 * s
    top = np.argsort(-total)[:topK]
    return [(int(i), float(total[i])) for i in top if total[i] > 0]


def searchContent(query: str, topK: int = 5, minTokensMatch: int = 0):
    """content 전용 BM25. minTokensMatch: 쿼리 단어 중 최소 몇 개가 문서에 있어야 하나."""
    tw = tokenizeWord(query)
    if not tw:
        return []

    scores = scoreBM25(content, tw)

    # 쿼리 단어 매칭 수 계산 (false positive 필터)
    if minTokensMatch > 0:
        matchCount = np.zeros(content["nDocs"], dtype=np.int32)
        for t in tw:
            sid = content["stemDict"].get(t)
            if sid is None:
                continue
            s, e = content["offsets"][sid], content["offsets"][sid + 1]
            ids = content["docIds"][s:e]
            np.add.at(matchCount, ids, 1)
        scores[matchCount < minTokensMatch] = 0

    top = np.argsort(-scores)[:topK]
    return [(int(i), float(scores[i])) for i in top if scores[i] > 0]


# ═══════════════════════════════════════
# 품질 측정
# ═══════════════════════════════════════

def fmt(hits, label, showContent=False):
    print(f"  [{label}]")
    for i, (d, s) in enumerate(hits):
        m = metaRows[d]
        print(f"    {i+1}. [{m['source']:>10}, {s:.2f}] {m['corp_name']} | {m['report_nm'][:45]}")
        if showContent and contentTexts[d]:
            snippet = contentTexts[d].replace("\n", " ")[:180]
            print(f"         content: {snippet}")


titleQueries = [
    "유상증자",
    "대표이사 변경",
    "전환사채",
    "배당",
    "자기주식 취득",
]

contentQueries = [
    "반도체 HBM 투자",
    "원재료 가격 급등",
    "환율 변동 리스크",
    "해외 매출 비중",
    "신규 수주 공급 계약",
    "경쟁 심화 마진 압박",
    "공장 가동률 하락",
    "구조조정 계획",
]

print("\n" + "=" * 70)
print("제목형 쿼리 — scope='title' 검증")
print("=" * 70)

for q in titleQueries:
    print(f"\n── '{q}' ──")
    fmt(searchTitle(q, 3), "title")


print("\n" + "=" * 70)
print("본문형 쿼리 — scope='content' 검증 (content snippet 포함)")
print("=" * 70)

for q in contentQueries:
    print(f"\n── '{q}' ──")
    # minTokensMatch=0 (all), 2 (엄격)
    fmt(searchContent(q, 3), "content (loose)", showContent=True)
    fmt(searchContent(q, 3, minTokensMatch=2), "content (≥2 매치)", showContent=True)
