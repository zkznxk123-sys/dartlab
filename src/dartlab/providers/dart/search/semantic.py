"""의미 검색 — type→본문 경험그래프 확장 + bm25-신뢰도 gated fusion.

`scope="auto"` 의 랭킹 코어. 실험 V233~V240(`tests/_attempts/horizonMeaning/`)에서 확정한 recipe 를 본진 이식:
keyword(bm25) 가 못 잡는 동의·관련 공시를 type(report_nm)→본문 경험확장으로 회복하되, bm25 신뢰도가
높은 질의는 키워드를 신뢰(gated). 임베딩·GPU 0.

artifact (build 시 fieldIndexRebuild.buildMeaningGraph/buildGateRef 생성):
- ``meaning.json`` : coreFeature(report_nm) → {bodyStem: SPPMI weight} top-K. 없으면 bm25 단독으로 graceful degrade.
- ``gateRef.json`` : {ref, gmin, gmax, gateX}. 없으면 균등(g=0.5).

설계 근거: V237(gated MRR 0.955, 사각 회복 80%, harm~0), V238(하이퍼 안전영역 GMIN 0.2/GMAX 0.85/GATE_X 1.5).
"""

from __future__ import annotations

import json
import math
import re
from collections import defaultdict
from pathlib import Path

import numpy as np
import polars as pl

from dartlab.core.logger import getLogger
from dartlab.providers.dart.search.fieldIndex import (
    _activeIndexDir,
    _contentIndexDir,
    _getSegments,
    _resolveResultUrl,
    _scoreBM25,
    tokenizeContent,
)

_log = getLogger(__name__)

# 의미확장/gate 하이퍼 (V238 안전영역 중앙값)
EXPAND_TOPN = 60
GMIN = 0.20
GMAX = 0.85
GATE_X = 1.5
RRF_K = 60

_GENERIC_STOP = frozenset(
    {
        "보고서",
        "공시",
        "제출",
        "정정",
        "기재",
        "첨부",
        "자료",
        "주요사항",
        "조회",
        "요구",
        "답변",
        "결과",
        "안내",
        "변경",
        "예고",
        "관련",
        "여부",
        "확인",
        "공고",
        "통지",
        "사업",
        "분기",
        "반기",
        "감사",
        "검토",
        "연결",
        "재무제표",
    }
)


_PAREN_RE = re.compile(r"[(\[]([^)\]]+)[)\]]")
_BRACKET_PREFIX_RE = re.compile(r"^\s*\[[^\]]*\]")
_TOKEN_RE = re.compile(r"[가-힣A-Za-z0-9]+")
_NUM_RE = re.compile(r"\d")
_HANGUL_RE = re.compile(r"[가-힣]+")


def reportNmCore(reportNm: str) -> set[str]:
    """report_nm → 의미 핵심 토큰 집합 (build 시 경험그래프 키 추출용). [...] 접두 제거 + 괄호 우선 + stopword.

    Args:
        reportNm: 공시 보고서명 (report_nm).

    Returns:
        set[str] — 2~14 자 한글 핵심 토큰 (generic stopword 제외).

    Raises:
        없음.

    Example:
        >>> "현금배당" in reportNmCore("[기재정정]주요사항보고서(현금배당)")
        True
    """
    raw = _BRACKET_PREFIX_RE.sub("", (reportNm or "").strip()).strip()
    parens = _PAREN_RE.findall(raw)
    pool = " ".join(parens) if parens else _PAREN_RE.sub(" ", raw)
    return {
        t
        for t in _TOKEN_RE.findall(pool)
        if 2 <= len(t) <= 14 and not _NUM_RE.search(t) and _HANGUL_RE.fullmatch(t) and t not in _GENERIC_STOP
    }


def coreFeatureWeights(tokens) -> dict[str, float]:
    """질의/제목 토큰 → char 특징(tok/prefix/suffix/ngram) 가중치 — 경험그래프 키. (V237 이식)

    Args:
        tokens: 토큰 iterable (한글 핵심어).

    Returns:
        dict[str, float] — feature 키(tok:/pre/suf/ng) → 가중치.

    Raises:
        없음.

    Example:
        >>> "tok:매출" in coreFeatureWeights(["매출"])
        True
    """
    feats: dict[str, float] = defaultdict(float)
    for token in tokens:
        if not token:
            continue
        feats[f"tok:{token}"] = 1.0
        n = len(token)
        for size, w in ((2, 0.18), (3, 0.34), (4, 0.42)):
            if n >= size:
                feats[f"pre{size}:{token[:size]}"] = max(feats[f"pre{size}:{token[:size]}"], w)
                feats[f"suf{size}:{token[-size:]}"] = max(feats[f"suf{size}:{token[-size:]}"], w)
        for size, w in ((2, 0.10), (3, 0.22), (4, 0.30)):
            if n >= size + 1:
                for s in range(n - size + 1):
                    g = token[s : s + size]
                    if g not in _GENERIC_STOP:
                        feats[f"ng{size}:{g}"] = max(feats[f"ng{size}:{g}"], w)
    return dict(feats)


def loadMeaningGraph(inDir: Path | None = None) -> dict[str, dict[str, float]] | None:
    """meaning.json (coreFeature→{bodyStem:weight}) 로드. 없으면 None (bm25 단독 degrade).

    Args:
        inDir: 인덱스 디렉토리. None 이면 기본 contentIndex 경로.

    Returns:
        dict[str, dict[str, float]] 또는 None — 경험그래프 (부재·파손 시 None).

    Raises:
        없음 (OSError/JSONDecodeError 는 None 으로 흡수).

    Example:
        >>> g = loadMeaningGraph()  # doctest: +SKIP
    """
    path = (inDir or _contentIndexDir()) / "meaning.json"
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def loadGateRef(inDir: Path | None = None) -> dict[str, float]:
    """gateRef.json 로드. 없으면 균등(ref<=0 → g=0.5).

    Args:
        inDir: 인덱스 디렉토리. None 이면 기본 contentIndex 경로.

    Returns:
        dict[str, float] — {ref, gmin, gmax, gateX}. 부재 시 ref=0(균등).

    Raises:
        없음 (예외는 기본값으로 흡수).

    Example:
        >>> loadGateRef().keys() >= {"ref"}  # doctest: +SKIP
        True
    """
    path = (inDir or _contentIndexDir()) / "gateRef.json"
    if not path.exists():
        return {"ref": 0.0, "gmin": GMIN, "gmax": GMAX, "gateX": GATE_X}
    try:
        d = json.loads(path.read_text(encoding="utf-8"))
        return {
            "ref": float(d.get("ref", 0.0)),
            "gmin": float(d.get("gmin", GMIN)),
            "gmax": float(d.get("gmax", GMAX)),
            "gateX": float(d.get("gateX", GATE_X)),
        }
    except (OSError, json.JSONDecodeError, ValueError):
        return {"ref": 0.0, "gmin": GMIN, "gmax": GMAX, "gateX": GATE_X}


def expandMeaning(queryTokens: list[str], graph: dict, *, topN: int = EXPAND_TOPN) -> dict[str, float]:
    """질의 토큰 → 경험그래프 확장 → 의미 프로필 {bodyStem: weight}. (V237 expandTitle 이식)

    Args:
        queryTokens: 질의 핵심 토큰 리스트.
        graph: 경험그래프(loadMeaningGraph 반환). falsy 면 빈 dict.
        topN: 프로필 상위 N 본문 stem.

    Returns:
        dict[str, float] — bodyStem → 누적 가중치 (상위 topN).

    Raises:
        없음.

    Example:
        >>> expandMeaning(["매출"], {"tok:매출": {"채권": 1.0}})
        {'채권': 1.0}
    """
    if not graph:
        return {}
    prof: dict[str, float] = defaultdict(float)
    for f, sw in coreFeatureWeights(queryTokens).items():
        for b, ew in graph.get(f, {}).items():
            prof[b] += sw * ew
    return dict(sorted(prof.items(), key=lambda kv: kv[1], reverse=True)[:topN])


def gateWeight(top1: float, gref: dict) -> float:
    """bm25 top1 신뢰도 → 의미가중 g. bm25 약할수록(top1 낮을수록) g↑. (V237 gateW 이식)

    Args:
        top1: 질의의 bm25 최고 점수 (신뢰도 신호).
        gref: gateRef dict ({ref, gmin, gmax, gateX}).

    Returns:
        float — 의미가중 g ∈ [gmin, gmax]. ref<=0 이면 (gmin+gmax)/2.

    Raises:
        없음.

    Example:
        >>> 0.2 <= gateWeight(0.0, {"ref": 0}) <= 0.85
        True
    """
    ref = gref.get("ref", 0.0)
    gmin, gmax, gx = gref.get("gmin", GMIN), gref.get("gmax", GMAX), gref.get("gateX", GATE_X)
    if ref <= 0:
        return (gmin + gmax) / 2.0
    x = min(top1 / ref, gx)
    return max(gmin, min(gmax, gmax - (gmax - gmin) * (x / gx)))


def _scoreMeaning(idx: dict, profile: dict[str, float]) -> np.ndarray:
    """의미 프로필을 CSR 역인덱스에 투영 — posting presence 가중합. (V237 scoreProf 이식)"""
    scores = np.zeros(idx["nDocs"], dtype=np.float32)
    if not profile or idx["nDocs"] == 0:
        return scores
    for stem, w in profile.items():
        sid = idx["stemDict"].get(stem)
        if sid is None:
            continue
        s, e = idx["offsets"][sid], idx["offsets"][sid + 1]
        ids = idx["docIds"][s:e]
        np.add.at(scores, ids, np.float32(w))
    return scores


def _gatedFuse(bm: np.ndarray, mn: np.ndarray, g: float, *, k: int = RRF_K) -> np.ndarray:
    """bm25·의미 점수를 reciprocal-rank 로 gated 융합. (V237 gatedFuse 이식, naive sum 아님)"""
    fused: dict[int, float] = defaultdict(float)
    nz = np.nonzero(bm)[0]
    for r, d in enumerate(nz[np.argsort(-bm[nz])], start=1):
        fused[int(d)] += (1.0 - g) * 1.0 / (k + r)
    nz2 = np.nonzero(mn)[0]
    for r, d in enumerate(nz2[np.argsort(-mn[nz2])], start=1):
        fused[int(d)] += g * 1.0 / (k + r)
    arr = np.zeros(len(bm), dtype=np.float32)
    for d, v in fused.items():
        arr[d] = v
    return arr


def searchSemantic(
    query: str,
    *,
    corpCode: str | None = None,
    stockCode: str | None = None,
    limit: int = 10,
) -> pl.DataFrame:
    """의미 검색 — bm25 + type→본문 경험확장 gated fusion. main+delta 병합 (delta 우선).

    meaning.json 부재 시 bm25 단독으로 graceful degrade (기존 content 검색과 동일 동작).

    Args:
        query: 검색어 (자연어).
        corpCode: 회사 식별자 corp_code. None 이면 전체.
        stockCode: 종목코드 (6 자리). None 이면 전체.
        limit: 최대 결과 행 수.

    Returns:
        pl.DataFrame — searchContent 와 동일 스키마 + score/segment/dartUrl. 인덱스 부재 시 info 컬럼.

    Raises:
        없음.

    Example:
        >>> searchSemantic("유상증자", limit=5)  # doctest: +SKIP
    """
    tokens = tokenizeContent(query)
    if not tokens:
        return pl.DataFrame()

    segments = _getSegments()
    if not segments:
        return pl.DataFrame(
            {"info": ["content 인덱스가 없습니다. dartlab.providers.dart.search.rebuildContent() 실행 필요."]}
        )

    activeDir = _activeIndexDir()  # flat(legacy/full) 또는 tier(lite) — 세그먼트와 동일 위치에서 meaning/gateRef
    graph = loadMeaningGraph(activeDir)
    gref = loadGateRef(activeDir)
    profile = expandMeaning(tokens, graph) if graph else {}

    # 1) 세그먼트별 bm25/의미 점수 + gate top1(전 세그먼트 bm25 최대)
    segScores: dict[str, tuple] = {}
    top1 = 0.0
    for name, (idx, meta) in segments.items():
        bm = _scoreBM25(idx, tokens)
        if bm.size:
            top1 = max(top1, float(bm.max()))
        mn = _scoreMeaning(idx, profile)
        segScores[name] = (idx, meta, bm, mn)
    g = gateWeight(top1, gref)

    # 2) 세그먼트별 gated 융합 → 병합 (delta 우선)
    allHits: list[dict] = []
    deltaKeys: set[tuple] = set()
    for name in ("delta", "main"):
        if name not in segScores:
            continue
        _idx, meta, bm, mn = segScores[name]
        fused = _gatedFuse(bm, mn, g)
        top = np.argsort(-fused)[: limit * 3]
        for i in top:
            if fused[i] <= 0:
                break
            row = meta.row(int(i), named=True)
            key = (row["rcept_no"], row["section_order"])
            if name == "main" and key in deltaKeys:
                continue
            if name == "delta":
                deltaKeys.add(key)
            allHits.append({**row, "score": float(fused[i]), "segment": name})

    if not allHits:
        return pl.DataFrame()

    df = pl.DataFrame(allHits).sort("score", descending=True)
    if corpCode:
        df = df.filter(pl.col("corp_code") == corpCode)
    if stockCode:
        df = df.filter(pl.col("stock_code") == stockCode)
    return _resolveResultUrl(df).head(limit)
