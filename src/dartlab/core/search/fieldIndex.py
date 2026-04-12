"""필드 분리 BM25 검색 — scope="content" 전용 엔진.

실험 116 검증 결과 적용. title/section은 기존 ngramIndex 그대로 유지하고,
본문(content) 검색을 별도 엔진으로 분리.

설계:
- word 토크나이저 (공백+구두점) + BM25 + 필드 분리
- main + delta 세그먼트 구조 (월 1회 main 리빌드, 일 단위 delta 증분)
- scope="content": content 인덱스만 사용, title 매칭은 무관

저장 구조::

    data/dart/contentIndex/
    ├── main.npz        # content CSR (offsets, docIds, termFreqs, docLengths)
    ├── main_meta.parquet
    ├── main_stems.json
    ├── delta.npz       # 동일 구조, 최근 N일 증분
    ├── delta_meta.parquet
    └── delta_stems.json

병합 검색::

    mainScore = BM25(mainIndex, query)
    deltaScore = BM25(deltaIndex, query)
    rerank(union) by score desc — rcept_no 중복 시 delta 우선
"""

from __future__ import annotations

import json
import math
import re
import time
from collections import defaultdict
from pathlib import Path

import numpy as np
import polars as pl

# ── 상수 ──

CONTENT_LIMIT = 1500  # section_content 인덱싱 최대 글자 수

_WORD_RE = re.compile(r"[가-힣a-zA-Z0-9]+")


def _contentIndexDir() -> Path:
    from dartlab import config as _cfg

    base = Path(_cfg.dataDir) / "dart" / "contentIndex"
    base.mkdir(parents=True, exist_ok=True)
    return base


# ── 토크나이저 ──


def tokenizeWord(text: str) -> list[str]:
    """content 토크나이저 — 공백/구두점으로 분리된 단어 단위."""
    if not text:
        return []
    return _WORD_RE.findall(text)


# ── 빌더 ──


class _IncrementalBuilder:
    """문서 단위로 점진적 토큰 축적 후 CSR로 finalize."""

    def __init__(self):
        self.stemToId: dict[str, int] = {}
        self.postings: dict[int, list[tuple[int, int]]] = defaultdict(list)
        self.docLengths: list[int] = []

    def addDoc(self, text: str) -> None:
        docId = len(self.docLengths)
        if not text:
            self.docLengths.append(0)
            return
        toks = tokenizeWord(text)
        self.docLengths.append(len(toks))
        tf: dict[int, int] = defaultdict(int)
        for t in toks:
            sid = self.stemToId.get(t)
            if sid is None:
                sid = len(self.stemToId)
                self.stemToId[t] = sid
            tf[sid] += 1
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
        termFreqs = np.zeros(nP, dtype=np.int32)
        for sid in range(nStems):
            s = offsets[sid]
            for i, (d, c) in enumerate(self.postings[sid]):
                docIds[s + i] = d
                termFreqs[s + i] = c
        docLengths = np.array(self.docLengths, dtype=np.int32)
        # 메모리 해제
        self.postings.clear()
        self.docLengths = []
        return {
            "stemDict": self.stemToId,
            "offsets": offsets,
            "docIds": docIds,
            "termFreqs": termFreqs,
            "docLengths": docLengths,
            "avgDocLength": float(docLengths.mean()) if n > 0 else 0.0,
            "nDocs": n,
        }


def buildContentSegment(
    rows: list[dict],
    *,
    contentLimit: int = CONTENT_LIMIT,
    showProgress: bool = True,
) -> tuple[dict, pl.DataFrame]:
    """문서 리스트로부터 content 세그먼트 1개 빌드.

    Parameters
    ----------
    rows : list[dict]
        각 row는 rcept_no, section_order, corp_name, stock_code, rcept_dt,
        report_nm, section_title, section_content 포함.
    contentLimit : int
        section_content 인덱싱 최대 글자 수.

    Returns
    -------
    (index, meta)
        index : CSR dict. meta : polars DataFrame.
    """
    t0 = time.perf_counter()
    builder = _IncrementalBuilder()
    metaRecs = []

    for row in rows:
        content = (row.get("section_content") or "")[:contentLimit]
        builder.addDoc(content)
        metaRecs.append(
            {
                "rcept_no": row.get("rcept_no") or "",
                "section_order": int(row.get("section_order") or 0),
                "corp_code": row.get("corp_code") or "",
                "corp_name": row.get("corp_name") or "",
                "stock_code": row.get("stock_code") or "",
                "rcept_dt": str(row.get("rcept_dt") or ""),
                "report_nm": row.get("report_nm") or "",
                "section_title": row.get("section_title") or "",
                "text": content[:500],  # 스니펫용
                "source": row.get("source") or "",
            }
        )

    idx = builder.finalize()
    meta = pl.DataFrame(metaRecs)
    if showProgress:
        elapsed = time.perf_counter() - t0
        print(
            f"  [content] {idx['nDocs']:,}문서, {len(idx['stemDict']):,} stems, {idx['offsets'][-1]:,} postings, {elapsed:.1f}초"
        )
    return idx, meta


# ── 저장/로드 ──


def saveSegment(idx: dict, meta: pl.DataFrame, name: str, outDir: Path | None = None) -> None:
    """세그먼트를 디스크에 저장."""
    outDir = outDir or _contentIndexDir()
    outDir.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        outDir / f"{name}.npz",
        offsets=idx["offsets"],
        docIds=idx["docIds"],
        termFreqs=idx["termFreqs"],
        docLengths=idx["docLengths"],
    )
    (outDir / f"{name}_stems.json").write_text(
        json.dumps(idx["stemDict"], ensure_ascii=False),
        encoding="utf-8",
    )
    meta.write_parquet(outDir / f"{name}_meta.parquet")
    (outDir / f"{name}_info.json").write_text(
        json.dumps(
            {
                "nDocs": idx["nDocs"],
                "avgDocLength": idx["avgDocLength"],
                "builtAt": time.strftime("%Y-%m-%dT%H:%M:%S"),
            }
        ),
        encoding="utf-8",
    )


def loadSegment(name: str, inDir: Path | None = None) -> tuple[dict, pl.DataFrame] | None:
    """세그먼트를 디스크에서 로드. 파일이 없으면 None."""
    inDir = inDir or _contentIndexDir()
    npzPath = inDir / f"{name}.npz"
    if not npzPath.exists():
        return None
    arrs = np.load(npzPath)
    stemDict = json.loads((inDir / f"{name}_stems.json").read_text(encoding="utf-8"))
    info = json.loads((inDir / f"{name}_info.json").read_text(encoding="utf-8"))
    meta = pl.read_parquet(inDir / f"{name}_meta.parquet")
    idx = {
        "stemDict": stemDict,
        "offsets": arrs["offsets"],
        "docIds": arrs["docIds"],
        "termFreqs": arrs["termFreqs"],
        "docLengths": arrs["docLengths"],
        "avgDocLength": float(info["avgDocLength"]),
        "nDocs": int(info["nDocs"]),
    }
    return idx, meta


# ── 검색 ──


def _scoreBM25(idx: dict, queryTokens: list[str], k1: float = 1.5, b: float = 0.75) -> np.ndarray:
    """BM25 벡터화 스코어링."""
    scores = np.zeros(idx["nDocs"], dtype=np.float32)
    N = idx["nDocs"]
    if N == 0:
        return scores
    avgDl = max(idx["avgDocLength"], 1.0)
    for t in queryTokens:
        sid = idx["stemDict"].get(t)
        if sid is None:
            continue
        s, e = idx["offsets"][sid], idx["offsets"][sid + 1]
        ids = idx["docIds"][s:e]
        tfs = idx["termFreqs"][s:e].astype(np.float32)
        df_t = len(ids)
        idf = math.log((N - df_t + 0.5) / (df_t + 0.5) + 1.0)
        dl = idx["docLengths"][ids].astype(np.float32)
        normTf = tfs * (k1 + 1) / (tfs + k1 * (1 - b + b * dl / avgDl))
        np.add.at(scores, ids, idf * normTf)
    return scores


# 세션 캐시
_segments: dict[str, tuple[dict, pl.DataFrame]] | None = None


def _getSegments() -> dict[str, tuple[dict, pl.DataFrame]]:
    """main + delta 세그먼트 로드 (캐시)."""
    global _segments
    if _segments is not None:
        return _segments
    out = {}
    for name in ("main", "delta"):
        seg = loadSegment(name)
        if seg is not None:
            out[name] = seg
    _segments = out
    return out


def clearCache() -> None:
    """세션 캐시 해제 (인덱스 재빌드 후 호출)."""
    global _segments
    _segments = None


def searchContent(
    query: str,
    *,
    corpCode: str | None = None,
    stockCode: str | None = None,
    topK: int = 10,
) -> pl.DataFrame:
    """content 전용 BM25 검색. main + delta 병합.

    Parameters
    ----------
    query : 자연어 쿼리. 공백으로 단어 분리.
    corpCode, stockCode : 필터.
    topK : 반환 건수.
    """
    tokens = tokenizeWord(query)
    if not tokens:
        return pl.DataFrame()

    segments = _getSegments()
    if not segments:
        return pl.DataFrame(
            {"info": ["content 인덱스가 없습니다. dartlab.core.search.fieldIndex.rebuildContent() 실행 필요."]}
        )

    allHits: list[dict] = []
    deltaRcepts: set[tuple[str, int]] = set()

    # delta 먼저 — 중복 감지용 rcept_no 수집
    if "delta" in segments:
        dIdx, dMeta = segments["delta"]
        dScores = _scoreBM25(dIdx, tokens)
        top = np.argsort(-dScores)[: topK * 3]
        for i in top:
            if dScores[i] <= 0:
                break
            row = dMeta.row(int(i), named=True)
            deltaRcepts.add((row["rcept_no"], row["section_order"]))
            allHits.append({**row, "score": float(dScores[i]), "segment": "delta"})

    if "main" in segments:
        mIdx, mMeta = segments["main"]
        mScores = _scoreBM25(mIdx, tokens)
        top = np.argsort(-mScores)[: topK * 3]
        for i in top:
            if mScores[i] <= 0:
                break
            row = mMeta.row(int(i), named=True)
            key = (row["rcept_no"], row["section_order"])
            if key in deltaRcepts:
                continue
            allHits.append({**row, "score": float(mScores[i]), "segment": "main"})

    if not allHits:
        return pl.DataFrame()

    df = pl.DataFrame(allHits).sort("score", descending=True)

    # 필터
    if corpCode:
        df = df.filter(pl.col("corp_code") == corpCode)
    if stockCode:
        df = df.filter(pl.col("stock_code") == stockCode)

    # dartUrl 추가
    if df.height > 0:
        df = df.with_columns(
            ("https://dart.fss.or.kr/dsaf001/main.do?rcpNo=" + pl.col("rcept_no")).alias("dartUrl"),
        )

    return df.head(topK)


# ── 풀리빌드 + 증분 ──


def rebuildMain(
    *,
    includeAllFilings: bool = True,
    includeDocs: bool = True,
    contentLimit: int = CONTENT_LIMIT,
    showProgress: bool = True,
) -> int:
    """main 세그먼트 풀리빌드 — 전체 docs + 과거 allFilings.

    스트리밍 빌드: 파일 단위로 읽고 즉시 빌더에 feed 후 해제 (메모리 안전).
    시간 오래 걸림 (4M 문서 기준 약 18분). 월 1회 실행 권장.

    Returns
    -------
    int : 인덱싱된 문서 수.
    """
    import gc

    from dartlab.providers.dart.openapi.allFilingsCollector import _META_SUFFIX, _allFilingsDir

    builder = _IncrementalBuilder()
    metaRecs: list[dict] = []
    totalDocs = 0

    def feedDf(df: pl.DataFrame, source: str) -> int:
        added = 0
        for row in df.iter_rows(named=True):
            content = (row.get("section_content") or "")[:contentLimit]
            builder.addDoc(content)
            metaRecs.append(  # noqa: F821
                {
                    "rcept_no": row.get("rcept_no") or "",
                    "section_order": int(row.get("section_order") or 0),
                    "corp_code": row.get("corp_code") or "",
                    "corp_name": row.get("corp_name") or "",
                    "stock_code": row.get("stock_code") or "",
                    "rcept_dt": str(row.get("rcept_dt") or ""),
                    "report_nm": row.get("report_nm") or "",
                    "section_title": row.get("section_title") or "",
                    "text": content[:500],
                    "source": source,
                }
            )
            added += 1
        return added

    t0 = time.perf_counter()

    if includeAllFilings:
        outDir = _allFilingsDir()
        files = sorted(f for f in outDir.glob("*.parquet") if _META_SUFFIX not in f.stem)
        if showProgress:
            print(f"[main] allFilings 스트리밍: {len(files)}개 파일")
        for i, f in enumerate(files):
            try:
                df = pl.read_parquet(f).filter(pl.col("section_content").is_not_null())
            except (pl.exceptions.PolarsError, OSError):
                continue
            totalDocs += feedDf(df, "allFilings")
            del df
            if (i + 1) % 50 == 0:
                gc.collect()
                if showProgress:
                    elapsed = time.perf_counter() - t0
                    print(f"  allFilings {i + 1}/{len(files)}: {totalDocs:,} docs, {elapsed:.0f}초")

    if includeDocs:
        from dartlab import config as _cfg

        docsDir = Path(_cfg.dataDir) / "dart" / "docs"
        docsFiles = sorted(docsDir.glob("*.parquet"))
        if showProgress:
            print(f"[main] docs 스트리밍: {len(docsFiles)}개 파일")
        for i, f in enumerate(docsFiles):
            try:
                df = pl.read_parquet(f).filter(pl.col("section_content").is_not_null())
            except (pl.exceptions.PolarsError, OSError):
                continue
            totalDocs += feedDf(df, "docs")
            del df
            if (i + 1) % 200 == 0:
                gc.collect()
                if showProgress:
                    elapsed = time.perf_counter() - t0
                    print(f"  docs {i + 1}/{len(docsFiles)}: {totalDocs:,} docs, {elapsed:.0f}초")

    if showProgress:
        print(f"[main] 축적 완료: {totalDocs:,} 문서, finalize 시작")

    idx = builder.finalize()
    meta = pl.DataFrame(metaRecs)
    del metaRecs
    gc.collect()

    saveSegment(idx, meta, "main")
    clearCache()
    _clearDelta()

    if showProgress:
        elapsed = time.perf_counter() - t0
        print(f"[main] 저장 완료. 총 {elapsed / 60:.1f}분, {idx['nDocs']:,} 문서.")

    return idx["nDocs"]


def rebuildDelta(sinceDate: str | None = None, daysBack: int = 30, showProgress: bool = True) -> int:
    """delta 세그먼트 빌드 — 최근 N일 allFilings.

    main 이후 추가된 allFilings만 포함.

    Parameters
    ----------
    sinceDate : YYYYMMDD. 이 날짜 이후만. None이면 daysBack 사용.
    daysBack : sinceDate 미지정 시 N일 전부터.
    """
    from datetime import datetime, timedelta

    from dartlab.providers.dart.openapi.allFilingsCollector import _META_SUFFIX, _allFilingsDir

    if sinceDate is None:
        sinceDate = (datetime.now() - timedelta(days=daysBack)).strftime("%Y%m%d")

    outDir = _allFilingsDir()
    files = sorted(f for f in outDir.glob("*.parquet") if _META_SUFFIX not in f.stem and f.stem >= sinceDate)

    if showProgress:
        print(f"[delta] {sinceDate} 이후: {len(files)}개 파일")

    rows: list[dict] = []
    for f in files:
        try:
            df = pl.read_parquet(f).filter(pl.col("section_content").is_not_null())
        except (pl.exceptions.PolarsError, OSError):
            continue
        for row in df.iter_rows(named=True):
            row["source"] = "allFilings"
            rows.append(row)

    if showProgress:
        print(f"[delta] 총 {len(rows):,} 문서")

    if not rows:
        _clearDelta()
        return 0

    idx, meta = buildContentSegment(rows, showProgress=showProgress)
    saveSegment(idx, meta, "delta")
    clearCache()
    return idx["nDocs"]


def _clearDelta() -> None:
    """delta 세그먼트 파일 제거."""
    outDir = _contentIndexDir()
    for name in ("delta.npz", "delta_stems.json", "delta_meta.parquet", "delta_info.json"):
        p = outDir / name
        if p.exists():
            p.unlink()


# ── HF 동기화 ──


def pushContentIndex(token: str | None = None) -> None:
    """content 인덱스 (main + delta) 를 HF에 업로드."""
    from huggingface_hub import HfApi

    outDir = _contentIndexDir()
    api = HfApi(token=token)
    names = [
        "main.npz",
        "main_stems.json",
        "main_meta.parquet",
        "main_info.json",
        "delta.npz",
        "delta_stems.json",
        "delta_meta.parquet",
        "delta_info.json",
    ]
    for name in names:
        src = outDir / name
        if not src.exists():
            continue
        api.upload_file(
            path_or_fileobj=str(src),
            path_in_repo=f"dart/contentIndex/{name}",
            repo_id="eddmpython/dartlab-data",
            repo_type="dataset",
        )


def pullContentIndex() -> int:
    """HF에서 content 인덱스 다운로드 (main + delta).

    Returns
    -------
    int : 다운로드 성공한 파일 수.
    """
    from huggingface_hub import hf_hub_download

    from dartlab import config as _cfg

    outDir = _contentIndexDir()
    outDir.mkdir(parents=True, exist_ok=True)
    dataDir = Path(_cfg.dataDir)  # dart/contentIndex/ 앞의 루트

    names = [
        "main.npz",
        "main_stems.json",
        "main_meta.parquet",
        "main_info.json",
        "delta.npz",
        "delta_stems.json",
        "delta_meta.parquet",
        "delta_info.json",
    ]
    ok = 0
    for name in names:
        try:
            hf_hub_download(
                repo_id="eddmpython/dartlab-data",
                repo_type="dataset",
                filename=f"dart/contentIndex/{name}",
                local_dir=str(dataDir),
            )
            ok += 1
        except Exception:
            continue
    clearCache()
    return ok


# ── 통계 ──


def contentStats() -> dict:
    """content 인덱스 통계."""
    segments = _getSegments()
    out: dict = {}
    for name, (idx, meta) in segments.items():
        out[name] = {
            "nDocs": idx["nDocs"],
            "nStems": len(idx["stemDict"]),
            "nPostings": int(idx["offsets"][-1]),
            "avgDocLength": idx["avgDocLength"],
        }
    return out
