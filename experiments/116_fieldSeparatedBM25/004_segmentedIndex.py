"""실험 116-004: 세그먼트 분할 인덱스 — 증분 업데이트 가능한 구조

실험 ID: 116-004
실험명: main + delta 세그먼트 구조로 증분 업데이트 설계 + 병합 비용 측정

배경:
- CSR 인덱스는 append 불가 (stemId 범위 고정) → 증분 필요 시 전체 리빌드
- 증분 무시하면 매일 220초 풀리빌드 = 비현실적
- docs 2,918종목 사업보고서는 분기 갱신 (연/반기/분기 공시)
- allFilings는 매일 수 천건 추가 (수시공시)

설계:
  main.npz     — 주기적 전체 리빌드 (월 1회, 모든 docs + 과거 allFilings)
  delta.npz    — 일 증분 빌드 (최근 N일 allFilings만)
  rcept_no 집합 — 중복 감지 (delta가 main을 포함할 때 main 우선)

  검색 = search(main) ∪ search(delta), 점수 병합 후 rerank

가설:
1. delta 빌드 시간 < 10초 (일치 4K문서 × 5필드)
2. 검색 병합 오버헤드 < 50ms
3. 월 1회 main 리빌드는 수용 가능 (배포 주기)

방법:
1. docs 중 10종목 샘플 + 최근 7일 allFilings → main 빌드
2. 최근 1일 allFilings → delta 빌드
3. main + delta 검색 병합, 품질/속도 측정

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

DATA_DIR = Path("data/dart")

print("=" * 60)
print("실험 116-004: 세그먼트 분할 + 증분 설계")
print("=" * 60)


_WORD_RE = re.compile(r"[가-힣a-zA-Z0-9]+")


def tokenizeWord(text: str) -> list[str]:
    return _WORD_RE.findall(text)


def tokenizeNgram(text: str, minLen: int = 2, maxLen: int = 3) -> list[str]:
    tokens = []
    text = text.strip()
    for n in range(minLen, maxLen + 1):
        if len(text) >= n:
            tokens.extend(text[i: i + n] for i in range(len(text) - n + 1))
    return tokens


# ═══════════════════════════════════════
# 세그먼트 인덱스 빌더
# ═══════════════════════════════════════

def buildSegment(
    titleTexts: list[str],
    sectionTexts: list[str],
    contentTexts: list[str],
    rceptNos: list[str],
    contentLimit: int = 1000,
) -> dict:
    """한 세그먼트 (main 또는 delta) 빌드."""
    t0 = time.perf_counter()
    n = len(titleTexts)

    def buildField(texts, tokenizer, label):
        stemToId: dict[str, int] = {}
        postings: dict[int, list[tuple[int, int]]] = defaultdict(list)
        docLengths = np.zeros(n, dtype=np.int32)
        for docId, text in enumerate(texts):
            if not text:
                continue
            toks = tokenizer(text)
            docLengths[docId] = len(toks)
            tf: dict[int, int] = defaultdict(int)
            for t in toks:
                if t not in stemToId:
                    stemToId[t] = len(stemToId)
                tf[stemToId[t]] += 1
            for sid, c in tf.items():
                postings[sid].append((docId, c))

        nStems = len(stemToId)
        offsets = np.zeros(nStems + 1, dtype=np.int64)
        for sid in range(nStems):
            offsets[sid + 1] = offsets[sid] + len(postings[sid])
        nP = int(offsets[-1])
        docIds = np.zeros(nP, dtype=np.int32)
        tfs = np.zeros(nP, dtype=np.int32)
        for sid in range(nStems):
            s = offsets[sid]
            for i, (d, c) in enumerate(postings[sid]):
                docIds[s + i] = d
                tfs[s + i] = c
        return {
            "stemDict": stemToId,
            "offsets": offsets,
            "docIds": docIds,
            "termFreqs": tfs,
            "docLengths": docLengths,
            "avgDocLength": float(docLengths.mean()) if n > 0 else 0.0,
            "nStems": nStems,
            "nPostings": nP,
        }

    truncContent = [(t or "")[:contentLimit] for t in contentTexts]

    title = buildField(titleTexts, tokenizeNgram, "title")
    section = buildField(sectionTexts, tokenizeNgram, "section")
    content = buildField(truncContent, tokenizeWord, "content")

    elapsed = time.perf_counter() - t0
    return {
        "title": title,
        "section": section,
        "content": content,
        "rceptNos": rceptNos,
        "nDocs": n,
        "buildTime": elapsed,
    }


# ═══════════════════════════════════════
# 세그먼트 검색
# ═══════════════════════════════════════

def scoreTf(fieldIdx: dict, queryTokens: list[str], nDocs: int) -> np.ndarray:
    scores = np.zeros(nDocs, dtype=np.float32)
    for t in queryTokens:
        sid = fieldIdx["stemDict"].get(t)
        if sid is None:
            continue
        s, e = fieldIdx["offsets"][sid], fieldIdx["offsets"][sid + 1]
        np.add.at(scores, fieldIdx["docIds"][s:e], fieldIdx["termFreqs"][s:e])
    return scores


def scoreBM25(fieldIdx: dict, queryTokens: list[str], nDocs: int, k1: float = 1.5, b: float = 0.75) -> np.ndarray:
    scores = np.zeros(nDocs, dtype=np.float32)
    N = nDocs
    avgDl = max(fieldIdx["avgDocLength"], 1.0)
    for t in queryTokens:
        sid = fieldIdx["stemDict"].get(t)
        if sid is None:
            continue
        s, e = fieldIdx["offsets"][sid], fieldIdx["offsets"][sid + 1]
        ids = fieldIdx["docIds"][s:e]
        tfs = fieldIdx["termFreqs"][s:e].astype(np.float32)
        df_t = len(ids)
        idf = math.log((N - df_t + 0.5) / (df_t + 0.5) + 1.0)
        dl = fieldIdx["docLengths"][ids].astype(np.float32)
        normTf = tfs * (k1 + 1) / (tfs + k1 * (1 - b + b * dl / avgDl))
        np.add.at(scores, ids, idf * normTf)
    return scores


def searchSegment(seg: dict, query: str) -> np.ndarray:
    """하나의 세그먼트 내 점수 배열 반환."""
    tn = tokenizeNgram(query)
    tw = tokenizeWord(query)
    n = seg["nDocs"]
    if n == 0:
        return np.array([], dtype=np.float32)

    tScore = scoreTf(seg["title"], tn, n)
    sScore = scoreTf(seg["section"], tn, n)
    cScore = scoreBM25(seg["content"], tw, n)

    def norm(s):
        m = s.max()
        return s / m if m > 0 else s

    return 5.0 * norm(tScore) + 2.0 * norm(sScore) + 1.0 * norm(cScore)


def searchMerged(main: dict, delta: dict, query: str, topK: int = 5) -> list[tuple[str, str, float]]:
    """main + delta 병합 검색. delta가 있으면 delta 우선."""
    mainScore = searchSegment(main, query)
    deltaScore = searchSegment(delta, query)

    # rcept_no 기준 중복 제거 (delta 우선)
    deltaRcepts = set(delta["rceptNos"])

    results = []
    # main에서 top-K 뽑기 (delta에 있는 건 제외)
    mainTop = np.argsort(-mainScore)[:topK * 3]
    for i in mainTop:
        if mainScore[i] <= 0:
            break
        rcept = main["rceptNos"][i]
        if rcept in deltaRcepts:
            continue
        results.append((rcept, "main", float(mainScore[i])))

    # delta에서 top-K
    if len(deltaScore) > 0:
        deltaTop = np.argsort(-deltaScore)[:topK * 3]
        for i in deltaTop:
            if deltaScore[i] <= 0:
                break
            results.append((delta["rceptNos"][i], "delta", float(deltaScore[i])))

    # 최종 정렬
    results.sort(key=lambda x: -x[2])
    return results[:topK]


# ═══════════════════════════════════════
# 1. 데이터 준비: main = 과거 6일, delta = 최근 1일
# ═══════════════════════════════════════

print("\n[데이터 로드]")
allFiles = sorted(Path("data/dart/allFilings").glob("2026*.parquet"))
mainFiles = allFiles[-7:-1]  # 과거 6일
deltaFiles = allFiles[-1:]   # 최근 1일

print(f"  main 파일: {len(mainFiles)}개 ({mainFiles[0].name} ~ {mainFiles[-1].name})")
print(f"  delta 파일: {len(deltaFiles)}개 ({deltaFiles[0].name})")


def loadFiles(files):
    dfs = []
    for f in files:
        try:
            df = pl.read_parquet(f).filter(pl.col("section_content").is_not_null())
            dfs.append(df)
        except Exception:
            pass
    if not dfs:
        return pl.DataFrame()
    return pl.concat(dfs)


mainDf = loadFiles(mainFiles)
deltaDf = loadFiles(deltaFiles)

print(f"  main 문서: {mainDf.height:,}")
print(f"  delta 문서: {deltaDf.height:,}")


# ═══════════════════════════════════════
# 2. 세그먼트 빌드
# ═══════════════════════════════════════

def buildFromDf(df: pl.DataFrame, label: str) -> dict:
    print(f"\n[빌드] {label} 세그먼트 ({df.height:,}문서)")
    rceptNos = [f"{r}_{o}" for r, o in zip(df["rcept_no"].to_list(), df["section_order"].to_list())]
    seg = buildSegment(
        df["report_nm"].fill_null("").to_list(),
        df["section_title"].fill_null("").to_list(),
        df["section_content"].fill_null("").to_list(),
        rceptNos,
    )
    print(f"  title   : {seg['title']['nStems']:>6,} stems, {seg['title']['nPostings']:>10,} postings")
    print(f"  section : {seg['section']['nStems']:>6,} stems, {seg['section']['nPostings']:>10,} postings")
    print(f"  content : {seg['content']['nStems']:>6,} stems, {seg['content']['nPostings']:>10,} postings")
    print(f"  빌드 시간: {seg['buildTime']:.2f}초")
    return seg


main = buildFromDf(mainDf, "main")
delta = buildFromDf(deltaDf, "delta")


# ═══════════════════════════════════════
# 3. 검색 테스트
# ═══════════════════════════════════════

queries = [
    "유상증자",
    "반도체 업황",
    "대표이사 변경",
    "배당",
    "공장 가동률",
]

# 메타 통합 (main + delta)
mainMeta = mainDf.select(["rcept_no", "section_order", "corp_name", "report_nm"]).with_columns(
    (pl.col("rcept_no") + "_" + pl.col("section_order").cast(str)).alias("_key")
)
deltaMeta = deltaDf.select(["rcept_no", "section_order", "corp_name", "report_nm"]).with_columns(
    (pl.col("rcept_no") + "_" + pl.col("section_order").cast(str)).alias("_key")
)
allMeta = pl.concat([mainMeta, deltaMeta]).unique(subset=["_key"])
metaMap = {row["_key"]: row for row in allMeta.iter_rows(named=True)}


print("\n" + "=" * 60)
print("병합 검색 테스트 (main + delta)")
print("=" * 60)

for q in queries:
    print(f"\n── '{q}' ──")
    t0 = time.perf_counter()
    hits = searchMerged(main, delta, q, topK=3)
    ms = (time.perf_counter() - t0) * 1000
    print(f"  검색 {ms:.1f}ms")
    for i, (key, src, score) in enumerate(hits):
        row = metaMap.get(key)
        if row:
            print(f"  {i+1}. [{src:>5}, {score:.2f}] {row['corp_name']} | {row['report_nm'][:45]}")


# ═══════════════════════════════════════
# 4. 증분 시뮬레이션 — 매일 delta 빌드 비용
# ═══════════════════════════════════════

print("\n" + "=" * 60)
print("증분 업데이트 비용 측정")
print("=" * 60)

# 1일치 delta 빌드
t0 = time.perf_counter()
newDelta = buildFromDf(deltaDf, "newDelta")
print(f"\n1일치({deltaDf.height:,}문서) 증분 빌드: {newDelta['buildTime']:.1f}초")

# main 리빌드 추정 (244일 전체)
totalDocs = 4_000_000  # 추정
scale = totalDocs / mainDf.height
estMainBuild = main["buildTime"] * scale
print(f"main 풀리빌드({totalDocs:,}문서) 추정: {estMainBuild/60:.1f}분")


# ═══════════════════════════════════════
# 5. 결론 요약
# ═══════════════════════════════════════

print("\n" + "=" * 60)
print("결론")
print("=" * 60)
print(f"""
- main 세그먼트: 정기 풀리빌드 (예상 {estMainBuild/60:.0f}분, 월 1회)
- delta 세그먼트: 매일 증분 빌드 ({newDelta['buildTime']:.1f}초)
- 병합 검색: {ms:.1f}ms 이내

다음 단계:
1. 전체 docs 2,918종목 포함한 main 빌드 시간 측정
2. delta 누적 후 임계점에서 자동 병합 (예: delta > 30일 → main에 합침)
3. 실제 ngramIndex.py에 SegmentedIndex 클래스 도입
""")
