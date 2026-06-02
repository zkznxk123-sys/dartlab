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

import array
import json
import math
import re
import time
from pathlib import Path

from dartlab.core.logger import getLogger

_log = getLogger(__name__)


import numpy as np
import polars as pl

# ── 상수 ──

CONTENT_LIMIT = 1500  # section_content 인덱싱 최대 글자 수

_WORD_RE = re.compile(r"[가-힣a-zA-Z0-9]+")


def _contentIndexDir() -> Path:
    from dartlab.core.dataLoader import _getDataRoot

    base = _getDataRoot() / "dart" / "contentIndex"
    base.mkdir(parents=True, exist_ok=True)
    return base


# ── 토크나이저 ──


def tokenizeWord(text: str) -> list[str]:
    """content 토크나이저 — 공백/구두점으로 분리된 단어 단위.

    Args:
        text: 인자.

    Raises:
        없음.

    Example:
        >>> tokenizeWord(...)

    Returns:
        list[str] — 토큰 또는 stems 리스트.
    """
    if not text:
        return []
    return _WORD_RE.findall(text)


# ── 빌더 ──


class _IncrementalBuilder:
    """문서 단위로 점진적 토큰 축적 후 CSR로 finalize.

    posting 누적을 ``array.array('i')`` 3열(stemId/docId/tf, 각 4 byte)로 — dict-of-list-of-tuple
    (posting 당 ~56 byte) 대비 ~7x 메모리 절감. 풀 색인(수억 posting) OOM 회피. finalize 에서
    stemId 기준 stable argsort → bincount cumsum 으로 CSR offsets 구성.
    """

    def __init__(self):
        self.stemToId: dict[str, int] = {}
        self._pSid = array.array("i")  # posting별 stem id
        self._pDid = array.array("i")  # posting별 doc id
        self._pTf = array.array("i")  # posting별 term freq
        self._docLengths = array.array("i")

    def addDoc(self, text: str) -> None:
        """document 1 개 추가 — 토크나이즈 + stem→id 매핑 + posting 3열 누적.

        Args:
            text: document 본문 (빈 문자열 = 길이 0 doc 으로 기록).

        Returns:
            None.

        Raises:
            없음.

        Example:
            >>> builder.addDoc("배당에 관한 사항")  # doctest: +SKIP
        """
        docId = len(self._docLengths)
        if not text:
            self._docLengths.append(0)
            return
        toks = tokenizeWord(text)
        self._docLengths.append(len(toks))
        tf: dict[int, int] = {}
        getSid = self.stemToId.get
        for t in toks:
            sid = getSid(t)
            if sid is None:
                sid = len(self.stemToId)
                self.stemToId[t] = sid
            tf[sid] = tf.get(sid, 0) + 1
        apS, apD, apT = self._pSid.append, self._pDid.append, self._pTf.append
        for sid, c in tf.items():
            apS(sid)
            apD(docId)
            apT(c)

    def finalize(self) -> dict:
        """누적된 posting 3열/docLengths → CSR 인덱스 dict — BM25 검색 준비 완료 상태.

        Returns:
            ``{"stemDict": dict, "offsets": np.ndarray, "docIds": np.ndarray,
            "termFreqs": np.ndarray, "docLengths": np.ndarray, "avgDocLength": float, "nDocs": int}``.

        Raises:
            없음.

        Example:
            >>> idx = builder.finalize()  # doctest: +SKIP
        """
        nDocs = len(self._docLengths)
        nStems = len(self.stemToId)
        sids = np.frombuffer(self._pSid, dtype=np.int32)
        dids = np.frombuffer(self._pDid, dtype=np.int32)
        tfs = np.frombuffer(self._pTf, dtype=np.int32)
        offsets = np.zeros(nStems + 1, dtype=np.int64)
        if sids.size:
            order = np.argsort(sids, kind="stable")  # stemId 기준 그룹화
            docIds = np.ascontiguousarray(dids[order])
            termFreqs = np.ascontiguousarray(tfs[order])
            counts = np.bincount(sids, minlength=nStems)
            np.cumsum(counts, out=offsets[1:])
            del order, counts
        else:
            docIds = np.zeros(0, dtype=np.int32)
            termFreqs = np.zeros(0, dtype=np.int32)
        docLengths = np.frombuffer(self._docLengths, dtype=np.int32).copy()
        # 메모리 해제 (array.array 버퍼 + frombuffer view 참조 해제)
        del sids, dids, tfs
        self._pSid = self._pDid = self._pTf = array.array("i")
        self._docLengths = array.array("i")
        return {
            "stemDict": self.stemToId,
            "offsets": offsets,
            "docIds": docIds,
            "termFreqs": termFreqs,
            "docLengths": docLengths,
            "avgDocLength": float(docLengths.mean()) if nDocs > 0 else 0.0,
            "nDocs": nDocs,
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

    Raises:
        없음.

    Example:
        >>> buildContentSegment(...)

    Args:
        rows: 문서 row dict 리스트.
        contentLimit: 본문 최대 문자 수.
        showProgress: True 면 progress 로그.

    Returns:
        tuple[dict, pl.DataFrame] — (인덱스, meta).
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
                "url": row.get("url") or "",  # 뉴스 기사 url (비뉴스는 "")
            }
        )

    idx = builder.finalize()
    meta = pl.DataFrame(metaRecs)
    if showProgress:
        elapsed = time.perf_counter() - t0
        _log.info(
            "  [content] %s문서, %s stems, %s postings, %.1f초",
            f"{idx['nDocs']:,}",
            f"{len(idx['stemDict']):,}",
            f"{idx['offsets'][-1]:,}",
            elapsed,
        )
    return idx, meta


# ── 저장/로드 ──


def saveSegment(idx: dict, meta: pl.DataFrame, name: str, outDir: Path | None = None) -> None:
    """세그먼트를 디스크에 저장.

    Args:
        idx: 인자.
        meta: 인자.
        name: 인자.
        outDir: 인자.

    Raises:
        없음.

    Example:
        >>> saveSegment(...)
    """
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
    """세그먼트를 디스크에서 로드. 파일이 없으면 None.

    Args:
        name: 인자.
        inDir: 인자.

    Raises:
        없음.

    Example:
        >>> loadSegment(...)

    Returns:
        tuple[dict, pl.DataFrame] 또는 None — (인덱스, meta).
    """
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
    """세션 캐시 해제 (인덱스 재빌드 후 호출).

    Raises:
        없음.

    Example:
        >>> clearCache(...)
    """
    global _segments
    _segments = None


def _resolveResultUrl(df: pl.DataFrame) -> pl.DataFrame:
    """결과 DataFrame 에 dartUrl 컬럼 부여 — source 분기.

    뉴스(source="news")는 기사 url 그대로, 그 외(공시)는 DART 뷰어 URL(rcpNo) 조합.

    Args:
        df: 검색 결과 DataFrame (rcept_no/source/url 컬럼 보유).

    Returns:
        pl.DataFrame — dartUrl 컬럼 추가본. 빈 df 면 그대로.

    Raises:
        없음.

    Example:
        >>> _resolveResultUrl(pl.DataFrame())  # doctest: +SKIP
    """
    if df.height == 0:
        return df
    hasUrl = "url" in df.columns
    dartBase = "https://dart.fss.or.kr/dsaf001/main.do?rcpNo=" + pl.col("rcept_no")
    if hasUrl and "source" in df.columns:
        return df.with_columns(
            pl.when(pl.col("source") == "news").then(pl.col("url")).otherwise(dartBase).alias("dartUrl")
        )
    return df.with_columns(dartBase.alias("dartUrl"))


def searchContent(
    query: str,
    *,
    corpCode: str | None = None,
    stockCode: str | None = None,
    limit: int = 10,
) -> pl.DataFrame:
    """content 전용 BM25 검색. main + delta 병합.

    Parameters
    ----------
    query : 자연어 쿼리. 공백으로 단어 분리.
    corpCode, stockCode : 필터.
    limit : 반환 건수.

    Raises:
        없음.

    Example:
        >>> searchContent(...)

    Args:
        query: 검색어 (자연어).
        corpCode: 회사 식별자 corp_code. None 이면 전체.
        stockCode: 종목코드 (6 자리). None 이면 전체.
        limit: 최대 결과 행 수.

    Returns:
        pl.DataFrame — 검색 결과 (rcept_no/score/snippet 등).
    """
    tokens = tokenizeWord(query)
    if not tokens:
        return pl.DataFrame()

    segments = _getSegments()
    if not segments:
        return pl.DataFrame(
            {
                "info": [
                    "content 인덱스가 없습니다. dartlab.providers.dart.search.fieldIndex.rebuildContent() 실행 필요."
                ]
            }
        )

    allHits: list[dict] = []
    deltaRcepts: set[tuple[str, int]] = set()

    # delta 먼저 — 중복 감지용 rcept_no 수집
    if "delta" in segments:
        dIdx, dMeta = segments["delta"]
        dScores = _scoreBM25(dIdx, tokens)
        top = np.argsort(-dScores)[: limit * 3]
        for i in top:
            if dScores[i] <= 0:
                break
            row = dMeta.row(int(i), named=True)
            deltaRcepts.add((row["rcept_no"], row["section_order"]))
            allHits.append({**row, "score": float(dScores[i]), "segment": "delta"})

    if "main" in segments:
        mIdx, mMeta = segments["main"]
        mScores = _scoreBM25(mIdx, tokens)
        top = np.argsort(-mScores)[: limit * 3]
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

    df = _resolveResultUrl(df)
    return df.head(limit)


# ── 풀리빌드 + 증분 ──


# ── rebuildMain / rebuildDelta / push/pull 등 빌드 helper 는 fieldIndexRebuild.py 로 분리 (룰 3 LoC).
from dartlab.providers.dart.search.fieldIndexRebuild import (  # noqa: E402, F401
    _clearDelta,
    contentStats,
    iterContent,
    pullContentIndex,
    pushContentIndex,
    rebuildDelta,
    rebuildMain,
)
