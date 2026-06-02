"""fieldIndex content 인덱스 빌드/배포 — fieldIndex.py 분할 (룰 3 LoC).

`fieldIndex.py` 824 LoC 가 룰 3 임계 (>800) 위반. rebuildMain / rebuildDelta /
pushContentIndex / pullContentIndex / _clearDelta (~360 줄) 를 본 모듈로 분리.
caller compat — fieldIndex.py 가 re-export.
"""

from __future__ import annotations

import html
import json
import math
import re
import time
from pathlib import Path

import numpy as np
import polars as pl

import dartlab.config as _cfg
from dartlab.core.dataConfig import DATA_RELEASES
from dartlab.core.logger import getLogger

# content_raw(DART XML/HTML) → 검색용 평문. 색인 토큰화엔 정밀 파서(BeautifulSoup, XML당 ~100ms)가
# 불필요·과부하 — regex tag-strip 으로 222파일/수억 토큰 빌드시간을 시간→분 단위로 단축.
_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s+")


def _stripTags(raw: str, *, limit: int) -> str:
    """XML/HTML 태그 제거 + entity unescape + 공백 정규화 → 검색용 평문 (limit 자 캡)."""
    if not raw:
        return ""
    raw = raw[: limit * 6]  # 태그 제거 전 과대 입력 캡 (regex 비용 가드)
    return _WS_RE.sub(" ", _TAG_RE.sub(" ", html.unescape(raw))).strip()[:limit]


# fieldIndex ↔ fieldIndexRebuild 양방향 import 회피 — 함수 본문 lazy import.
# fieldIndex.py 가 본 모듈의 rebuildMain / rebuildDelta 외 7 항목을 re-export 하므로
# module-level `from fieldIndex import ...` 시 direct import 가 partially initialized
# 로 실패. fieldIndex 의 9 항목 (CONTENT_LIMIT · _contentIndexDir · _getSegments ·
# _IncrementalBuilder · buildContentSegment · clearCache · loadSegment · saveSegment ·
# searchContent) 사용은 모두 함수 본문 안 → 각 함수 시작 lazy import.

_log = getLogger(__name__)


def rebuildMain(
    *,
    includeAllFilings: bool = True,
    includeDocs: bool = True,
    includePanel: bool = False,
    contentLimit: int | None = None,
    panelLimit: int = 4000,
    showProgress: bool = True,
) -> int:
    """main 세그먼트 풀리빌드 — docs + allFilings (+ panel filing 롤업).

    스트리밍 빌드: 파일 단위로 읽고 즉시 빌더에 feed 후 해제 (메모리 안전).
    시간 오래 걸림 (4M 문서 기준 약 18분). 월 1회 실행 권장.

    includePanel=True 면 "완전한 DART 문서" 색인: panel 정규화 본문을 filing(rceptNo) 단위로 롤업해
    1 문서로 추가하고, 같은 rceptNo 의 allFilings 원문은 skip (panel 본문 우선). 표시 메타(corp_name/
    report_nm/rcept_dt)는 allFilings 메타 dict 에서 채운다.

    Args:
        includeAllFilings: True 면 전체 공시 (수시 포함).
        includeDocs: True 면 docs sections 포함.
        includePanel: True 면 panel 정규화 본문을 filing 롤업으로 추가.
        contentLimit: allFilings/docs 본문 최대 문자 수.
        panelLimit: panel filing 롤업 본문 최대 문자 수.
        showProgress: True 면 progress 로그.

    Returns:
        int — 인덱스 빌드 건수.

    Raises:
        없음 (파일별 read 오류는 skip).

    Example:
        >>> rebuildMain(includePanel=True)  # doctest: +SKIP
    """
    import gc

    from dartlab.providers.dart.openapi.allFilingsCollector import _META_SUFFIX, _allFilingsDir
    from dartlab.providers.dart.search.fieldIndex import (
        CONTENT_LIMIT,
        _IncrementalBuilder,
        clearCache,
        saveSegment,
    )

    if contentLimit is None:
        contentLimit = CONTENT_LIMIT
    builder = _IncrementalBuilder()
    metaRecs: list[dict] = []
    totalDocs = 0

    # panel 통합 시 allFilings 메타(content_raw 제외 경량)를 먼저 dict 로 — panel 롤업 문서의 표시 메타 보강용.
    afMeta: dict[str, dict] = {}
    panelRcepts: set[str] = set()
    if includePanel and includeAllFilings:
        afMeta = _buildAfMeta(showProgress=showProgress)

    # allFilings 는 content_raw (DART XML/HTML 태그 보존) — regex tag-strip 으로 평문화 (빌드시간 가드).
    # docs/ 는 옛 section_content (이미 평문) 그대로 사용.
    def feedDf(df: pl.DataFrame, source: str, *, contentColumn: str, skipRcepts: set[str] | None = None) -> int:
        """parquet DataFrame 의 각 row 를 builder 에 추가 + meta record 동행 — 빌드 건수 반환.

        Args:
            df: parquet DataFrame.
            source: 인덱스 라벨 (예 ``"main"`` / ``"delta"``).
            contentColumn: 본문 컬럼명. ``"content_raw"`` 이면 regex tag-strip 평문화,
                ``"section_content"`` 이면 그대로 사용.

        Returns:
            추가된 doc 수.

        Raises:
            없음.

        Example:
            >>> feedDf(df, "allFilings", contentColumn="content_raw")  # doctest: +SKIP
        """
        added = 0
        for row in df.iter_rows(named=True):
            if skipRcepts and (row.get("rcept_no") or "") in skipRcepts:
                continue
            raw = row.get(contentColumn) or ""
            if contentColumn == "content_raw":
                content = _stripTags(raw, limit=contentLimit)
            else:
                content = raw[:contentLimit]
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

    if includePanel:
        totalDocs += _feedPanelRollup(builder, metaRecs, afMeta, panelRcepts, panelLimit, showProgress)
        if showProgress:
            _log.info(f"[main] panel 롤업 완료: {len(panelRcepts):,} filing, {time.perf_counter() - t0:.0f}초")

    if includeAllFilings:
        import os

        outDir = _allFilingsDir()
        files = sorted(f for f in outDir.glob("*.parquet") if _META_SUFFIX not in f.stem)
        _afl = int(os.environ.get("DARTLAB_SEARCH_AF_FILES", "0"))  # 테스트용 제한(0=무제한)
        if _afl > 0:
            files = files[-_afl:]
        if showProgress:
            _log.info(f"[main] allFilings 스트리밍: {len(files)}개 파일 (panel skip {len(panelRcepts):,})")
        for i, f in enumerate(files):
            try:
                df = pl.read_parquet(f).filter(pl.col("fetch_status") == "ok")
            except (pl.exceptions.PolarsError, OSError):
                continue
            totalDocs += feedDf(df, "allFilings", contentColumn="content_raw", skipRcepts=panelRcepts)
            del df
            if (i + 1) % 50 == 0:
                gc.collect()
                if showProgress:
                    elapsed = time.perf_counter() - t0
                    _log.info(f"  allFilings {i + 1}/{len(files)}: {totalDocs:,} docs, {elapsed:.0f}초")

    if includeDocs:
        from dartlab.core.dataLoader import _getDataRoot

        docsDir = _getDataRoot() / "dart" / "docs"
        docsFiles = sorted(docsDir.glob("*.parquet"))
        if showProgress:
            _log.info(f"[main] docs 스트리밍: {len(docsFiles)}개 파일")
        for i, f in enumerate(docsFiles):
            try:
                df = pl.read_parquet(f).filter(pl.col("section_content").is_not_null())
            except (pl.exceptions.PolarsError, OSError):
                continue
            totalDocs += feedDf(df, "docs", contentColumn="section_content")
            del df
            if (i + 1) % 200 == 0:
                gc.collect()
                if showProgress:
                    elapsed = time.perf_counter() - t0
                    _log.info(f"  docs {i + 1}/{len(docsFiles)}: {totalDocs:,} docs, {elapsed:.0f}초")

    if showProgress:
        _log.info(f"[main] 축적 완료: {totalDocs:,} 문서, finalize 시작")

    idx = builder.finalize()
    meta = pl.DataFrame(metaRecs)
    del metaRecs
    gc.collect()

    saveSegment(idx, meta, "main")
    clearCache()
    _clearDelta()

    if showProgress:
        elapsed = time.perf_counter() - t0
        _log.info(f"[main] 저장 완료. 총 {elapsed / 60:.1f}분, {idx['nDocs']:,} 문서.")

    return idx["nDocs"]


def _buildAfMeta(*, showProgress: bool = True) -> dict[str, dict]:
    """allFilings 메타(content_raw 제외 경량) → {rcept_no: {corp_code,corp_name,stock_code,rcept_dt,report_nm}}.

    panel 롤업 문서의 표시 메타 보강용. content_raw 미로드라 빠르다.
    """
    from dartlab.providers.dart.openapi.allFilingsCollector import _META_SUFFIX, _allFilingsDir

    cols = ["rcept_no", "corp_code", "corp_name", "stock_code", "rcept_dt", "report_nm"]
    out: dict[str, dict] = {}
    files = sorted(f for f in _allFilingsDir().glob("*.parquet") if _META_SUFFIX not in f.stem)
    for f in files:
        try:
            df = pl.read_parquet(f, columns=cols)
        except (pl.exceptions.PolarsError, OSError):
            continue
        for row in df.iter_rows(named=True):
            rn = row.get("rcept_no") or ""
            if rn and rn not in out:
                out[rn] = {
                    "corp_code": row.get("corp_code") or "",
                    "corp_name": row.get("corp_name") or "",
                    "stock_code": row.get("stock_code") or "",
                    "rcept_dt": str(row.get("rcept_dt") or ""),
                    "report_nm": row.get("report_nm") or "",
                }
        del df
    if showProgress:
        _log.info(f"[main] allFilings 메타 dict: {len(out):,} filing")
    return out


def _panelDir():
    from dartlab.core.dataLoader import _getDataRoot

    return _getDataRoot() / "dart" / "panel"


def _feedPanelRollup(builder, metaRecs, afMeta, panelRcepts, panelLimit, showProgress) -> int:
    """panel 정규화 본문을 filing(rceptNo) 단위 롤업해 빌더에 추가 — "완전한 DART 문서" 색인.

    종목별 parquet 스트리밍(read+del+gc) → rceptNo 별 contentRaw concat → get_text → addDoc 1 문서.
    표시 메타는 afMeta(allFilings) 에서 보강. 추가한 rceptNo 를 panelRcepts 에 기록(allFilings 패스 skip 용).
    """
    import gc
    import os
    import re

    base = _panelDir()
    if not base.exists():
        if showProgress:
            _log.info("[main] panel 디렉토리 없음 — 롤업 skip")
        return 0
    codeDirs = sorted(d for d in base.iterdir() if d.is_dir())
    _codeLimit = int(os.environ.get("DARTLAB_SEARCH_PANEL_CODES", "0"))  # 테스트용 제한(0=무제한)
    if _codeLimit > 0:
        codeDirs = codeDirs[:_codeLimit]

    tag = re.compile(r"<[^>]+>")
    sp = re.compile(r"\s+")
    perSection = 2000  # 섹션당 raw 캡 (메모리·시간 가드)
    rawCap = panelLimit * 4
    added = 0
    for ci, cd in enumerate(codeDirs):
        files = [f for f in cd.glob("*.parquet") if not f.name.startswith("_")]
        if not files:
            continue
        try:
            df = pl.read_parquet(files, columns=["rceptNo", "contentRaw", "sectionLeaf"])
        except (pl.exceptions.PolarsError, OSError):
            continue
        if df.height == 0:
            del df
            continue
        # 벡터 group_by — 섹션 raw 캡 후 rceptNo 별 list 수집. Python 섹션 루프 회피(8.7M row 직접순회 금지).
        try:
            rolled = (
                df.with_columns(pl.col("contentRaw").cast(pl.Utf8).str.slice(0, perSection))
                .group_by("rceptNo", maintain_order=True)
                .agg(
                    pl.col("contentRaw").alias("parts"),
                    pl.col("sectionLeaf").first().alias("leaf"),
                )
            )
        except (pl.exceptions.PolarsError, OSError):
            continue
        del df
        for row in rolled.iter_rows(named=True):
            rn = row["rceptNo"]
            if not rn:
                continue
            parts = row["parts"] or []
            raw = " ".join(p for p in parts if p)[:rawCap]
            text = sp.sub(" ", tag.sub(" ", raw)).strip()[:panelLimit]
            if not text:
                continue
            builder.addDoc(text)
            m = afMeta.get(rn, {})
            metaRecs.append(
                {
                    "rcept_no": rn,
                    "section_order": 0,
                    "corp_code": m.get("corp_code", ""),
                    "corp_name": m.get("corp_name", ""),
                    "stock_code": m.get("stock_code", "") or cd.name,
                    "rcept_dt": m.get("rcept_dt", ""),
                    "report_nm": m.get("report_nm", ""),
                    "section_title": row.get("leaf") or "",
                    "text": text[:500],
                    "source": "panel",
                }
            )
            panelRcepts.add(rn)
            added += 1
        del rolled
        if (ci + 1) % 200 == 0:
            gc.collect()
            if showProgress:
                _log.info(f"  panel {ci + 1}/{len(codeDirs)}: {added:,} filing")
    return added


def buildMeaningGraph(*, contentLimit: int | None = None, showProgress: bool = True) -> int:
    """type(report_nm)→본문 경험그래프 build → meaning.json 저장. allFilings 스트리밍 (SPPMI top-K).

    의미검색(scope=auto) 확장 엔진의 artifact. 키워드가 못 잡는 동의·관련 공시 회복용.

    Args:
        contentLimit: 본문 토큰화 최대 문자 수. None 이면 CONTENT_LIMIT.
        showProgress: True 면 progress 로그.

    Returns:
        int — 그래프 feature 노드 수.

    Raises:
        없음 (파일별 read 오류는 skip).

    Example:
        >>> buildMeaningGraph()  # doctest: +SKIP
    """
    import gc
    import os
    import re
    from collections import Counter

    from dartlab.providers.dart.openapi.allFilingsCollector import _META_SUFFIX, _allFilingsDir
    from dartlab.providers.dart.search.fieldIndex import CONTENT_LIMIT, _contentIndexDir, tokenizeWord
    from dartlab.providers.dart.search.semantic import coreFeatureWeights, reportNmCore

    if contentLimit is None:
        contentLimit = CONTENT_LIMIT
    # 그래프는 토큰 분포만 필요 — 정밀 파서(BeautifulSoup) 대신 regex tag-strip (5~10x 빠름, 222파일 timeout 회피).
    tag = re.compile(r"<[^>]+>")
    sp = re.compile(r"\s+")
    shift, branch, minCo, bodyCap = 0.7, 24, 3, 150
    co: dict[str, Counter] = {}
    titleDf: Counter = Counter()
    bodyDf: Counter = Counter()
    nDocs = 0

    files = sorted(f for f in _allFilingsDir().glob("*.parquet") if _META_SUFFIX not in f.stem)
    _afl = int(os.environ.get("DARTLAB_SEARCH_AF_FILES", "0"))  # 테스트용 제한(0=무제한)
    if _afl > 0:
        files = files[-_afl:]
    for i, f in enumerate(files):
        try:
            df = pl.read_parquet(f, columns=["report_nm", "content_raw", "fetch_status"]).filter(
                pl.col("fetch_status") == "ok"
            )
        except (pl.exceptions.PolarsError, OSError):
            continue
        for row in df.iter_rows(named=True):
            core = reportNmCore(row.get("report_nm") or "")
            if not core:
                continue
            raw = row.get("content_raw") or ""
            if not raw:
                continue
            text = sp.sub(" ", tag.sub(" ", raw[: contentLimit * 6])).strip()[:contentLimit]
            tf: Counter = Counter(t for t in tokenizeWord(text) if t not in core)
            body = [t for t, _ in tf.most_common(bodyCap)]
            if not body:
                continue
            nDocs += 1
            for b in body:
                bodyDf[b] += 1
            for fkey in set(coreFeatureWeights(core)):
                titleDf[fkey] += 1
                co.setdefault(fkey, Counter()).update(body)
        del df
        if (i + 1) % 50 == 0:
            gc.collect()
    n = max(1, nDocs)
    graph: dict[str, dict[str, float]] = {}
    for fkey, counts in co.items():
        fDf = titleDf[fkey]
        w: dict[str, float] = {}
        for b, c in counts.items():
            if c < minCo:
                continue
            bDf = bodyDf.get(b, 0)
            if bDf <= 0:
                continue
            pmi = math.log((c * n) / (fDf * bDf)) - shift
            if pmi > 0:
                w[b] = round(pmi * math.log(1.0 + n / bDf), 5)
        if w:
            graph[fkey] = dict(sorted(w.items(), key=lambda kv: kv[1], reverse=True)[:branch])
    (_contentIndexDir() / "meaning.json").write_text(json.dumps(graph, ensure_ascii=False), encoding="utf-8")
    if showProgress:
        _log.info(f"[meaning] {nDocs:,} 문서 → feature {len(graph):,} 노드 meaning.json 저장")
    return len(graph)


def buildGateRef(*, sampleN: int = 2000, showProgress: bool = True) -> float:
    """gate 기준값(코퍼스 median bm25 top1) → gateRef.json. 색인 규모 적응(V238 보강).

    main 세그먼트의 self-query(report_nm core) bm25 top1 분포 중앙값.

    Args:
        sampleN: top1 분포 샘플 질의 수.
        showProgress: True 면 progress 로그.

    Returns:
        float — ref (median bm25 top1). main 세그먼트 부재 시 0.0(균등).

    Raises:
        없음.

    Example:
        >>> buildGateRef()  # doctest: +SKIP
    """
    from dartlab.providers.dart.search import semantic as _sem
    from dartlab.providers.dart.search.fieldIndex import _contentIndexDir, _scoreBM25, loadSegment, tokenizeWord
    from dartlab.providers.dart.search.semantic import reportNmCore

    seg = loadSegment("main")
    out = {"ref": 0.0, "gmin": _sem.GMIN, "gmax": _sem.GMAX, "gateX": _sem.GATE_X}
    if seg is None:
        (_contentIndexDir() / "gateRef.json").write_text(json.dumps(out), encoding="utf-8")
        return 0.0
    idx, meta = seg
    top1s: list[float] = []
    step = max(1, meta.height // sampleN)
    for i in range(0, meta.height, step):
        row = meta.row(i, named=True)
        core = reportNmCore(row.get("report_nm") or "")
        toks = list(core) if core else tokenizeWord(row.get("text") or "")
        if not toks:
            continue
        scores = _scoreBM25(idx, toks)
        if scores.size and scores.max() > 0:
            top1s.append(float(scores.max()))
    if top1s:
        top1s.sort()
        out["ref"] = top1s[len(top1s) // 2]
    (_contentIndexDir() / "gateRef.json").write_text(json.dumps(out), encoding="utf-8")
    if showProgress:
        _log.info(f"[gateRef] n={len(top1s)} ref(median bm25 top1)={out['ref']:.2f}")
    return out["ref"]


def rebuildDelta(sinceDate: str | None = None, daysBack: int = 30, showProgress: bool = True) -> int:
    """delta 세그먼트 빌드 — 최근 N일 allFilings.

    main 이후 추가된 allFilings만 포함.

    Parameters
    ----------
    sinceDate : YYYYMMDD. 이 날짜 이후만. None이면 daysBack 사용.
    daysBack : sinceDate 미지정 시 N일 전부터.

    Raises:
        없음.

    Example:
        >>> rebuildDelta(...)

    Args:
        sinceDate: 시작일 YYYYMMDD. None 이면 daysBack 사용.
        daysBack: 과거 N 일 (sinceDate 없을 때).
        showProgress: True 면 progress 로그.

    Returns:
        int — 인덱스 빌드 건수.
    """
    from datetime import datetime, timedelta

    from dartlab.providers.dart.openapi.allFilingsCollector import _META_SUFFIX, _allFilingsDir
    from dartlab.providers.dart.search.fieldIndex import (
        CONTENT_LIMIT,
        buildContentSegment,
        clearCache,
        saveSegment,
    )

    if sinceDate is None:
        sinceDate = (datetime.now() - timedelta(days=daysBack)).strftime("%Y%m%d")

    outDir = _allFilingsDir()
    files = sorted(f for f in outDir.glob("*.parquet") if _META_SUFFIX not in f.stem and f.stem >= sinceDate)

    if showProgress:
        _log.info(f"[delta] {sinceDate} 이후: {len(files)}개 파일")

    rows: list[dict] = []
    for f in files:
        try:
            df = pl.read_parquet(f).filter(pl.col("fetch_status") == "ok")
        except (pl.exceptions.PolarsError, OSError):
            continue
        for row in df.iter_rows(named=True):
            raw = row.get("content_raw") or ""
            # buildContentSegment 는 section_content 컬럼을 본문으로 읽으므로 평문 결과를 동일 키로 채운다.
            row["section_content"] = _stripTags(raw, limit=CONTENT_LIMIT)
            row.setdefault("section_order", 0)
            row.setdefault("section_title", "")
            row["source"] = "allFilings"
            rows.append(row)

    if showProgress:
        _log.info(f"[delta] 총 {len(rows):,} 문서")

    if not rows:
        _clearDelta()
        return 0

    idx, meta = buildContentSegment(rows, showProgress=showProgress)
    saveSegment(idx, meta, "delta")
    clearCache()
    return idx["nDocs"]


def _clearDelta() -> None:
    """delta 세그먼트 파일 제거."""
    from dartlab.providers.dart.search.fieldIndex import _contentIndexDir

    outDir = _contentIndexDir()
    for name in ("delta.npz", "delta_stems.json", "delta_meta.parquet", "delta_info.json"):
        p = outDir / name
        if p.exists():
            p.unlink()


# ── HF 동기화 ──


def pushContentIndex(token: str | None = None) -> None:
    """content 인덱스 (main + delta) 를 HF에 업로드.

    Args:
        token: 인자.

    Raises:
        없음.

    Example:
        >>> pushContentIndex(...)
    """
    from huggingface_hub import HfApi

    from dartlab.providers.dart.search.fieldIndex import _contentIndexDir

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
        "meaning.json",
        "gateRef.json",
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

    Raises:
        없음.

    Example:
        >>> pullContentIndex(...)

    Returns:
        int — 인덱스 빌드 건수.
    """
    from huggingface_hub import hf_hub_download

    from dartlab.core.dataLoader import _getDataRoot
    from dartlab.providers.dart.search.fieldIndex import _contentIndexDir, clearCache

    outDir = _contentIndexDir()
    outDir.mkdir(parents=True, exist_ok=True)
    dataDir = _getDataRoot()  # dart/contentIndex/ 앞의 루트

    names = [
        "main.npz",
        "main_stems.json",
        "main_meta.parquet",
        "main_info.json",
        "delta.npz",
        "delta_stems.json",
        "delta_meta.parquet",
        "delta_info.json",
        "meaning.json",
        "gateRef.json",
    ]
    ok = 0
    _log.info("[cyan]⬇ HF[/] contentIndex (%d 파일)", len(names))
    for name in names:
        try:
            hf_hub_download(
                repo_id="eddmpython/dartlab-data",
                repo_type="dataset",
                filename=f"dart/contentIndex/{name}",
                local_dir=str(dataDir),
            )
            ok += 1
        except (OSError, ConnectionError, ValueError):
            # HF Hub 다운로드 실패 (네트워크 / 인증 / 파일 부재) — 다음 파일 진행.
            continue
    clearCache()
    _log.info("[green]✓[/] contentIndex (%d/%d 파일)", ok, len(names))
    return ok


# ── 통계 ──


def contentStats() -> dict:
    """content 인덱스 통계.

    Args:
        (인자 자동 생성).

    Raises:
        없음.

    Example:
        >>> contentStats(...)

    Returns:
        dict — 결과 통계.
    """
    from dartlab.providers.dart.search.fieldIndex import _getSegments

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


def iterContent(
    query: str,
    *,
    corpCode: str | None = None,
    stockCode: str | None = None,
    limit: int = 10,
):
    """``searchContent`` 의 iterator pair (룰 10).

    Args:
        query: 자연어 쿼리.
        corpCode: corp_code 필터.
        stockCode: 종목코드 필터.
        limit: 반환 건수.

    Yields:
        검색 결과 row dict.

    Example:
        >>> for row in iterContent("매출", limit=5):
        ...     print(row.get("rcept_no"))

    Raises:
        없음.
    """
    from dartlab.providers.dart.search.fieldIndex import searchContent

    df = searchContent(query, corpCode=corpCode, stockCode=stockCode, limit=limit)
    if df is None or df.is_empty():
        return
    yield from df.iter_rows(named=True)
