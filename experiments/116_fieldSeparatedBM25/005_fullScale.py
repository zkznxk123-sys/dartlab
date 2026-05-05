"""실험 116-005: 실제 규모 main 빌드 + 본문 검색 품질 측정

실험 ID: 116-005
실험명: docs 100종목 + allFilings 30일 → main 세그먼트 빌드

목적:
- 실제 docs 사업보고서 본문을 포함한 필드 분리 인덱스 품질 확인
- 빌드 시간 선형성 검증 (파일럿→실측)
- 본문형 쿼리에서 사업보고서 매칭 실전 측정

규모:
- docs 100종목 (시총 상위) × 평균 1154 section ≈ 115,000 section
- allFilings 30일 ≈ 150,000 section
- 총 약 265K 문서

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

DATA_DIR = Path("data/dart")

print("=" * 70)
print("실험 116-005: 실제 규모 main 빌드 + 본문 품질")
print("=" * 70)


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


# ═══════════════════════════════════════
# 증분 빌더 — 문서 하나씩 추가
# ═══════════════════════════════════════

class IncrementalFieldIndex:
    """stemDict + postings(dict)를 점진적으로 축적하는 빌더."""

    def __init__(self, tokenizer, name: str):
        self.tokenizer = tokenizer
        self.name = name
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
        # 메모리 해제
        self.postings.clear()
        self.docLengths = []
        return {
            "stemDict": self.stemToId,
            "offsets": offsets,
            "docIds": docIds,
            "termFreqs": tfs,
            "docLengths": docLengths,
            "avgDocLength": float(docLengths.mean()) if n > 0 else 0.0,
            "nDocs": n,
            "nStems": nStems,
            "nPostings": nP,
        }


# ═══════════════════════════════════════
# 데이터 로드 + 빌드
# ═══════════════════════════════════════

print("\n[데이터 스캔]")

# docs: 100종목만
docsFiles = sorted(Path("data/dart/docs").glob("*.parquet"))[:100]
print(f"  docs 파일: {len(docsFiles)}개 (100종목 샘플)")

# allFilings: 30일
allFilesDates = sorted(Path("data/dart/allFilings").glob("2026*.parquet"))[-30:]
print(f"  allFilings 파일: {len(allFilesDates)}개 ({allFilesDates[0].name} ~ {allFilesDates[-1].name})")


titleIdx = IncrementalFieldIndex(tokenizeNgram, "title")
sectionIdx = IncrementalFieldIndex(tokenizeNgram, "section")
contentIdx = IncrementalFieldIndex(tokenizeWord, "content")

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
            "rcept_no": row.get("rcept_no", ""),
            "section_order": row.get("section_order", 0),
            "corp_name": row.get("corp_name", ""),
            "stock_code": row.get("stock_code", ""),
            "report_nm": report,
            "section_title": sect,
            "source": source,
        })


print("\n[빌드 시작]")
t0 = time.perf_counter()

# docs
docT0 = time.perf_counter()
docCount = 0
for i, f in enumerate(docsFiles):
    try:
        df = pl.read_parquet(f).filter(pl.col("section_content").is_not_null())
        processBatch(df, "docs")
        docCount += df.height
    except Exception:
        continue
    if (i + 1) % 20 == 0:
        elapsed = time.perf_counter() - docT0
        print(f"  docs {i+1:>3}/{len(docsFiles)}: {docCount:,} sections, {elapsed:.0f}초")
docT = time.perf_counter() - docT0
print(f"  docs 완료: {docCount:,} sections, {docT:.1f}초")

# allFilings
afT0 = time.perf_counter()
afCount = 0
for i, f in enumerate(allFilesDates):
    try:
        df = pl.read_parquet(f).filter(pl.col("section_content").is_not_null())
        processBatch(df, "allFilings")
        afCount += df.height
    except Exception:
        continue
    if (i + 1) % 10 == 0:
        elapsed = time.perf_counter() - afT0
        print(f"  allFilings {i+1:>3}/{len(allFilesDates)}: {afCount:,} sections, {elapsed:.0f}초")
afT = time.perf_counter() - afT0
print(f"  allFilings 완료: {afCount:,} sections, {afT:.1f}초")

totalDocs = docCount + afCount
print(f"\n  전체: {totalDocs:,} sections, {time.perf_counter() - t0:.1f}초")

# finalize
print("\n[인덱스 finalize]")
fT0 = time.perf_counter()
titleFinal = titleIdx.finalize()
sectionFinal = sectionIdx.finalize()
contentFinal = contentIdx.finalize()
gc.collect()
print(f"  finalize: {time.perf_counter() - fT0:.1f}초")

totalT = time.perf_counter() - t0
print(f"\n[전체 빌드 시간]: {totalT:.1f}초 ({totalT/60:.1f}분)")
print(f"  title  : {titleFinal['nStems']:>7,} stems, {titleFinal['nPostings']:>12,} postings")
print(f"  section: {sectionFinal['nStems']:>7,} stems, {sectionFinal['nPostings']:>12,} postings")
print(f"  content: {contentFinal['nStems']:>7,} stems, {contentFinal['nPostings']:>12,} postings")

# 인덱스 크기
def idxBytes(idx):
    return idx["offsets"].nbytes + idx["docIds"].nbytes + idx["termFreqs"].nbytes + idx["docLengths"].nbytes
totalMb = (idxBytes(titleFinal) + idxBytes(sectionFinal) + idxBytes(contentFinal)) / 1024 / 1024
print(f"\n  3개 인덱스 총 크기: {totalMb:.1f}MB")

# 4M 문서 선형 확장
scale = 4_000_000 / totalDocs
print(f"  4M 문서 확장 추정: 빌드 {totalT*scale/60:.1f}분, 크기 {totalMb*scale/1024:.1f}GB")


# ═══════════════════════════════════════
# 검색 테스트
# ═══════════════════════════════════════

def scoreTf(fi: dict, tokens: list[str]) -> np.ndarray:
    scores = np.zeros(fi["nDocs"], dtype=np.float32)
    for t in tokens:
        sid = fi["stemDict"].get(t)
        if sid is None:
            continue
        s, e = fi["offsets"][sid], fi["offsets"][sid + 1]
        np.add.at(scores, fi["docIds"][s:e], fi["termFreqs"][s:e])
    return scores


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


def search(query: str, topK: int = 5):
    tn = tokenizeNgram(query)
    tw = tokenizeWord(query)
    tScore = scoreTf(titleFinal, tn)
    sScore = scoreTf(sectionFinal, tn)
    cScore = scoreBM25(contentFinal, tw)

    def norm(s):
        m = s.max()
        return s / m if m > 0 else s

    total = 5.0 * norm(tScore) + 2.0 * norm(sScore) + 1.0 * norm(cScore)
    topIds = np.argsort(-total)[:topK]
    return [(int(i), float(total[i])) for i in topIds if total[i] > 0]


print("\n" + "=" * 70)
print("본문형 쿼리 — docs(사업보고서) 포함 실전 검색")
print("=" * 70)

queries = [
    "반도체 업황 둔화",
    "원재료 가격 급등",
    "환율 변동 리스크",
    "해외 매출 비중 증가",
    "신규 수주 체결",
    "경쟁 심화로 인한 마진 압박",
    "연구개발 투자 확대",
    "공장 가동률 하락",
    "구조조정 계획",
    "품질 이슈",
]

for q in queries:
    t0 = time.perf_counter()
    hits = search(q, topK=3)
    ms = (time.perf_counter() - t0) * 1000
    print(f"\n── '{q}' ({ms:.1f}ms) ──")
    for i, (docId, score) in enumerate(hits):
        m = metaRows[docId]
        label = f"{m['source']:>10}"
        rpt = m['report_nm'][:40] if m['report_nm'] else m['section_title'][:40]
        print(f"  {i+1}. [{label}, {score:.2f}] {m['corp_name']} | {rpt}")
