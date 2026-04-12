"""실험 116-001: 필드 분리 BM25 — 본문 검색 파일럿

실험 ID: 116-001
실험명: report_nm / section_title / section_content 3개 독립 역인덱스 구축 후 가중치 합산

목적:
- 현재 dartlab.search()는 제목(report_nm + section_title)만 인덱싱 → 본문 검색 불가
- 실험 014에서 content[:50] 혼합 인덱싱이 precision 95→35%로 실패 → 한 인덱스에 섞어서
- 필드 분리 시 각 인덱스가 독립이므로 content 어휘 폭발이 title 인덱스를 오염시키지 않음

가설:
1. titleIndex: 어휘 작음(~5K) → TF + 필드 가중치 (현재 방식 유지)
2. contentIndex: 어휘 큼(수십K~수백K) → BM25(TF + IDF + length norm) 필수
3. 제목형 쿼리("유상증자") → titleIndex에서 강하게 hit → 현재 95% 유지
4. 본문형 쿼리("반도체 업황 둔화") → contentIndex에서 hit → 새로 커버

방법:
1. 파일럿 규모: 2026-03-31 하루치 allFilings (~6200문서)
2. 3개 인덱스 독립 빌드 (CSR)
3. 본문형 쿼리 10개 + 제목형 쿼리 10개로 측정
4. 가중치 조합: title×5 + section×2 + content×1

측정:
- 제목형 쿼리: 현재 방식 vs 필드분리 — precision 유지 확인
- 본문형 쿼리: 현재 방식 0% → 필드분리 몇 % ?
- 인덱스 크기 증가율
- 검색 속도

규모 확정 후 전체 400만 문서로 확장.

실험일: 2026-04-12
"""

from __future__ import annotations

import json
import math
import time
from collections import defaultdict
from pathlib import Path

import numpy as np
import polars as pl

DATA_DIR = Path("data/dart/allFilings")

# ═══════════════════════════════════════
# 1. 데이터 로드 (파일럿: 1일치)
# ═══════════════════════════════════════

print("=" * 60)
print("실험 116-001: 필드 분리 BM25 파일럿")
print("=" * 60)

pilotFile = DATA_DIR / "20260331.parquet"
df = pl.read_parquet(pilotFile)
df = df.filter(pl.col("section_content").is_not_null())
print(f"\n로드: {df.height:,}문서")


# ═══════════════════════════════════════
# 2. 토크나이저 (기존 ngramIndex와 동일)
# ═══════════════════════════════════════

def tokenize(text: str) -> list[str]:
    text = text.strip()
    tokens = set()
    if len(text) >= 2:
        tokens.update(text[i: i + 2] for i in range(len(text) - 1))
    if len(text) >= 3:
        tokens.update(text[i: i + 3] for i in range(len(text) - 2))
    return list(tokens)


# ═══════════════════════════════════════
# 3. 필드별 역인덱스 빌드
# ═══════════════════════════════════════

def buildFieldIndex(texts: list[str], name: str) -> dict:
    """필드 하나의 역인덱스 빌드.

    Returns
    -------
    dict
        stemDict : dict — stem → stemId
        offsets : np.ndarray — CSR offsets
        docIds : np.ndarray — CSR docIds
        termFreqs : np.ndarray — 각 posting의 TF (content용)
        docLengths : np.ndarray — 문서별 토큰 수 (BM25 length norm)
    """
    t0 = time.perf_counter()

    stemToId: dict[str, int] = {}
    postings: dict[int, list[tuple[int, int]]] = defaultdict(list)  # stemId → [(docId, tf)]
    docLengths = np.zeros(len(texts), dtype=np.int32)

    for docId, text in enumerate(texts):
        if not text:
            continue
        tokens = tokenize(text)
        docLengths[docId] = len(tokens)

        # TF 집계
        stemTf: dict[int, int] = defaultdict(int)
        for t in tokens:
            if t not in stemToId:
                stemToId[t] = len(stemToId)
            stemTf[stemToId[t]] += 1

        for sid, tf in stemTf.items():
            postings[sid].append((docId, tf))

    # CSR 구조로 변환
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
    avgDocLen = docLengths.mean()
    print(f"  [{name}] {nStems:,} stems, {nPostings:,} postings, avgDocLen={avgDocLen:.0f}, {elapsed:.2f}초")

    return {
        "stemDict": stemToId,
        "offsets": offsets,
        "docIds": docIds,
        "termFreqs": termFreqs,
        "docLengths": docLengths,
        "avgDocLength": float(avgDocLen),
        "nDocs": len(texts),
    }


print("\n[빌드] 3개 필드 인덱스")
titleTexts = df["report_nm"].fill_null("").to_list()
sectionTexts = df["section_title"].fill_null("").to_list()
contentTexts = df["section_content"].fill_null("").to_list()

titleIdx = buildFieldIndex(titleTexts, "title")
sectionIdx = buildFieldIndex(sectionTexts, "section")
contentIdx = buildFieldIndex(contentTexts, "content")


# ═══════════════════════════════════════
# 4. 필드별 스코어 함수
# ═══════════════════════════════════════

def scoreTf(idx: dict, queryTokens: list[str]) -> np.ndarray:
    """TF 단순 합산 — 어휘가 작은 title/section 용."""
    scores = np.zeros(idx["nDocs"], dtype=np.float32)
    for t in queryTokens:
        sid = idx["stemDict"].get(t)
        if sid is None:
            continue
        s, e = idx["offsets"][sid], idx["offsets"][sid + 1]
        np.add.at(scores, idx["docIds"][s:e], idx["termFreqs"][s:e])
    return scores


def scoreBM25(idx: dict, queryTokens: list[str], k1: float = 1.5, b: float = 0.75) -> np.ndarray:
    """BM25 스코어 — 어휘가 큰 content 용."""
    scores = np.zeros(idx["nDocs"], dtype=np.float32)
    N = idx["nDocs"]
    avgDl = idx["avgDocLength"]
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
# 5. 필드 분리 통합 검색
# ═══════════════════════════════════════

def searchFieldSeparated(
    query: str,
    topK: int = 10,
    wTitle: float = 5.0,
    wSection: float = 2.0,
    wContent: float = 1.0,
) -> list[int]:
    tokens = tokenize(query)
    titleScore = scoreTf(titleIdx, tokens)
    sectionScore = scoreTf(sectionIdx, tokens)
    contentScore = scoreBM25(contentIdx, tokens)

    # 스코어별 정규화 (max로 나눠서 스케일 맞춤)
    def norm(s):
        m = s.max()
        return s / m if m > 0 else s

    total = (
        wTitle * norm(titleScore)
        + wSection * norm(sectionScore)
        + wContent * norm(contentScore)
    )
    topIds = np.argsort(-total)[:topK]
    return [int(i) for i in topIds if total[i] > 0]


def searchCurrentMethod(query: str, topK: int = 10) -> list[int]:
    """현재 dartlab.search() 방식 재현 — title + section만, content 없음."""
    tokens = tokenize(query)
    titleScore = scoreTf(titleIdx, tokens)
    sectionScore = scoreTf(sectionIdx, tokens)

    def norm(s):
        m = s.max()
        return s / m if m > 0 else s

    total = 5.0 * norm(titleScore) + 2.0 * norm(sectionScore)
    topIds = np.argsort(-total)[:topK]
    return [int(i) for i in topIds if total[i] > 0]


# ═══════════════════════════════════════
# 6. 벤치마크 쿼리
# ═══════════════════════════════════════

titleQueries = [
    "유상증자",
    "전환사채",
    "대표이사 변경",
    "배당",
    "자기주식 취득",
    "합병",
    "감자",
    "주주총회",
    "사업보고서",
    "신주인수권",
]

contentQueries = [
    "반도체 업황",
    "원재료 가격 상승",
    "환율 변동 리스크",
    "연구개발 투자 확대",
    "해외 매출 비중",
    "공장 가동률",
    "신규 수주",
    "경쟁 심화",
    "구조조정 계획",
    "품질 문제",
]


# ═══════════════════════════════════════
# 7. 측정
# ═══════════════════════════════════════

def measure(queries: list[str], label: str):
    print(f"\n── {label} ──")
    currentHits = 0
    newHits = 0
    t0 = time.perf_counter()
    for q in queries:
        curr = searchCurrentMethod(q, topK=5)
        new = searchFieldSeparated(q, topK=5)
        cc = len(curr)
        nn = len(new)
        currentHits += (cc > 0)
        newHits += (nn > 0)
        print(f"  '{q}': 현재={cc:>2}건, 필드분리={nn:>2}건")
        if nn > 0 and cc == 0:
            # 본문형 쿼리가 새로 잡힌 경우 샘플 출력
            topDoc = new[0]
            row = df.row(topDoc, named=True)
            print(f"      → [new] {row['corp_name']} | {row['report_nm'][:40]}")
    avgMs = (time.perf_counter() - t0) / len(queries) / 2 * 1000
    print(f"\n  {label} 결과: 현재 {currentHits}/{len(queries)}건 매치, 필드분리 {newHits}/{len(queries)}건 매치")
    print(f"  평균 검색 속도: {avgMs:.1f}ms")


measure(titleQueries, "제목형 쿼리")
measure(contentQueries, "본문형 쿼리 (현재 엔진이 못 찾는 것)")


# ═══════════════════════════════════════
# 8. 인덱스 크기 비교
# ═══════════════════════════════════════

def idxSizeBytes(idx: dict) -> int:
    return (
        idx["offsets"].nbytes
        + idx["docIds"].nbytes
        + idx["termFreqs"].nbytes
        + idx["docLengths"].nbytes
        + len(json.dumps(idx["stemDict"]).encode("utf-8"))
    )


print("\n── 인덱스 크기 ──")
tSize = idxSizeBytes(titleIdx)
sSize = idxSizeBytes(sectionIdx)
cSize = idxSizeBytes(contentIdx)
print(f"  titleIndex   : {tSize / 1024 / 1024:.1f} MB ({titleIdx['stemDict'].__len__()} stems)")
print(f"  sectionIndex : {sSize / 1024 / 1024:.1f} MB ({sectionIdx['stemDict'].__len__()} stems)")
print(f"  contentIndex : {cSize / 1024 / 1024:.1f} MB ({contentIdx['stemDict'].__len__()} stems)")
print(f"  합계         : {(tSize + sSize + cSize) / 1024 / 1024:.1f} MB")
print(f"  증가 배수    : {(tSize + sSize + cSize) / tSize:.1f}x vs title만")
