"""실험 116-006: 3개 필드 모두 BM25 + IDF로 랭킹 개선

실험 ID: 116-006
실험명: title/section/content 모두 BM25 적용 — 빈번한 ngram의 가중치 자동 감쇠

문제 (실험 005):
- title index에 IDF 없음 → "투자판단관련주요경영사항" 처럼 흔한 공시가 5x 가중치로 상위
- 관련 없는 쿼리("연구개발 투자 확대")에도 ngram "투자" 매치만으로 top-3 차지

해결:
- 3개 필드 전부 BM25 — IDF가 자동으로 흔한 stem 감쇠
- 실험 005 동일 데이터/쿼리로 재검증

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

print("실험 116-006: All-Field BM25")
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
            "nDocs": n, "nStems": nStems, "nPostings": nP,
        }


# 동일 데이터 로드 (005와 같음)
docsFiles = sorted(Path("data/dart/docs").glob("*.parquet"))[:100]
allFilesDates = sorted(Path("data/dart/allFilings").glob("2026*.parquet"))[-30:]

titleIdx = IncrementalFieldIndex(tokenizeNgram)
sectionIdx = IncrementalFieldIndex(tokenizeNgram)
contentIdx = IncrementalFieldIndex(tokenizeWord)
metaRows: list[dict] = []
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

print(f"  로드: {len(metaRows):,}문서, {time.perf_counter()-t0:.0f}초")

print("\n[finalize]")
title = titleIdx.finalize()
section = sectionIdx.finalize()
content = contentIdx.finalize()
gc.collect()
print(f"  title: {title['nStems']:,} stems, section: {section['nStems']:,} stems, content: {content['nStems']:,} stems")


# ═══════════════════════════════════════
# BM25 + 두 가지 검색 방식 비교
# ═══════════════════════════════════════

def scoreBM25(fi: dict, tokens: list[str], k1: float = 1.5, b: float = 0.75) -> np.ndarray:
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


def scoreTf(fi: dict, tokens: list[str]) -> np.ndarray:
    scores = np.zeros(fi["nDocs"], dtype=np.float32)
    for t in tokens:
        sid = fi["stemDict"].get(t)
        if sid is None:
            continue
        s, e = fi["offsets"][sid], fi["offsets"][sid + 1]
        np.add.at(scores, fi["docIds"][s:e], fi["termFreqs"][s:e])
    return scores


def search005(query: str, topK: int = 3):
    """실험 005 방식 — title/section TF, content BM25."""
    tn = tokenizeNgram(query)
    tw = tokenizeWord(query)
    t = scoreTf(title, tn)
    s = scoreTf(section, tn)
    c = scoreBM25(content, tw)

    def norm(s):
        m = s.max()
        return s / m if m > 0 else s
    total = 5.0 * norm(t) + 2.0 * norm(s) + 1.0 * norm(c)
    top = np.argsort(-total)[:topK]
    return [(int(i), float(total[i])) for i in top if total[i] > 0]


def search006(query: str, topK: int = 3):
    """실험 006 방식 — 3개 필드 모두 BM25."""
    tn = tokenizeNgram(query)
    tw = tokenizeWord(query)
    t = scoreBM25(title, tn)
    s = scoreBM25(section, tn)
    c = scoreBM25(content, tw)

    def norm(s):
        m = s.max()
        return s / m if m > 0 else s
    total = 5.0 * norm(t) + 2.0 * norm(s) + 1.0 * norm(c)
    top = np.argsort(-total)[:topK]
    return [(int(i), float(total[i])) for i in top if total[i] > 0]


queries = [
    "유상증자",              # 제목형 — 회귀 없어야 함
    "대표이사 변경",         # 제목형
    "반도체 업황 둔화",      # 본문형
    "원재료 가격 급등",      # 본문형
    "연구개발 투자 확대",    # 본문형 (005에서 실패)
    "공장 가동률 하락",      # 본문형 (005에서 실패)
    "경쟁 심화",             # 본문형
    "품질 이슈",             # 본문형
]

print("\n" + "=" * 70)
print("005 (title TF) vs 006 (title BM25) 비교")
print("=" * 70)

for q in queries:
    print(f"\n── '{q}' ──")
    r5 = search005(q, 3)
    r6 = search006(q, 3)
    print("  [005 방식 — title TF]")
    for i, (d, s) in enumerate(r5):
        m = metaRows[d]
        print(f"    {i+1}. [{m['source']:>10}, {s:.2f}] {m['corp_name']} | {m['report_nm'][:45]}")
    print("  [006 방식 — title BM25]")
    for i, (d, s) in enumerate(r6):
        m = metaRows[d]
        print(f"    {i+1}. [{m['source']:>10}, {s:.2f}] {m['corp_name']} | {m['report_nm'][:45]}")
