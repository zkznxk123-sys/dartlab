"""통합 검색 R* — plain BM25 ⊕ (큐레이션 동의어 + 결정론 라우팅 canon) 확장 BM25 RRF.

``scope="auto"`` 의 랭킹 코어. unifiedSearchRecipe honest-gold 실측으로 확정한 레시피의
본진 이식 — hard(자유구어·paraphrase) nDCG@10 0.237(word·무확장) → 0.502, 정식어 0.618 → 0.943
(tests/_attempts/unifiedSearchRecipe/ARCHITECTURE.md). 임베딩·GPU·학습 0.

융합은 always-safe: 확장이 발화하지 않거나 라우팅이 틀려도 plain BM25 lane 이 RRF 로 보존돼
최악이 plain 과 동급이다. 같은 실험의 기각 카탈로그 — meaning graph(+0.010, 동어반복 인공물)·
fasttext(dominated)·DuckDB FTS(한국어 이점 0) — 는 본진에 들이지 않는다.

artifact: ``router.json`` (인덱스와 동거 배포, 부재 시 라우팅 lane 생략). 큐레이션 동의어는
코드 내장(curatedSyn). title-ngram lane ⊕ content RRF 통합은 후속(type-name 질의 극대화,
ARCHITECTURE §7.5) — 본 모듈은 실측 완료된 content lane 만 담는다.
"""

from __future__ import annotations

import numpy as np
import polars as pl

from dartlab.core.logger import getLogger
from dartlab.providers.dart.search.curatedSyn import expandQuery
from dartlab.providers.dart.search.fieldIndex import (
    _activeIndexDir,
    _getSegments,
    _resolveResultUrl,
    _scoreBM25,
    tokenizeContent,
)
from dartlab.providers.dart.search.router import loadRouterModel, routeCanon

_log = getLogger(__name__)

RRF_K = 60  # reciprocal-rank 융합 상수 (landing·recipe parity)
EXPAND_BOOST = 0.5  # 확장토큰 가중 (질의 원토큰 1.0 대비)


def _expansionWeights(query: str, routerModel: dict | None) -> dict[str, float]:
    """질의 → bigram 가중치 dict. 원토큰 1.0 + 큐레이션·라우팅 canon 확장 0.5(max 병합)."""
    weights: dict[str, float] = {t: 1.0 for t in tokenizeContent(query)}

    def boost(term: str) -> None:
        """확장 용어의 bigram 들을 EXPAND_BOOST 가중으로 병합 (기존 가중과 max — 원토큰 1.0 보존).

        Args:
            term: 확장 용어 (동의어 또는 라우팅 canon 본문어).

        Raises:
            없음.

        Example:
            >>> boost("자기주식")  # doctest: +SKIP

        Returns:
            None — 클로저의 weights dict 를 제자리 갱신.
        """
        for t in tokenizeContent(term):
            weights[t] = max(weights.get(t, 0.0), EXPAND_BOOST)

    for term in expandQuery(query):
        boost(term)
    for term in routeCanon(routerModel, query):
        boost(term)
    return weights


def _rrfFuse(plain: np.ndarray, boosted: np.ndarray, *, k: int = RRF_K) -> np.ndarray:
    """두 점수 배열을 reciprocal-rank 로 등가 융합 — 순위 기반이라 lane 간 스케일 무관."""
    fused = np.zeros(len(plain), dtype=np.float32)
    for arr in (plain, boosted):
        nz = np.nonzero(arr)[0]
        for r, d in enumerate(nz[np.argsort(-arr[nz])], start=1):
            fused[int(d)] += np.float32(1.0 / (k + r))
    return fused


def searchUnified(
    query: str,
    *,
    corpCode: str | None = None,
    stockCode: str | None = None,
    limit: int = 10,
) -> pl.DataFrame:
    """통합 검색 — plain BM25 ⊕ 확장 BM25 RRF. main+delta 병합 (delta 우선).

    확장(동의어·canon)이 발화하지 않으면 plain BM25 단독 — searchContent 와 동일 동작으로
    graceful degrade. router.json 부재 시 라우팅 lane 만 생략(큐레이션은 코드 내장이라 동작).

    Args:
        query: 검색어 (자연어 — 구어·약어 허용).
        corpCode: 회사 식별자 corp_code. None 이면 전체.
        stockCode: 종목코드 (6 자리). None 이면 전체.
        limit: 최대 결과 행 수.

    Raises:
        없음.

    Example:
        >>> searchUnified("자사주 샀어?", limit=5)  # doctest: +SKIP

    Returns:
        pl.DataFrame — searchContent 와 동일 스키마 + score/segment/dartUrl. 인덱스 부재 시 info 컬럼.
    """
    tokens = tokenizeContent(query)
    if not tokens:
        return pl.DataFrame()

    segments = _getSegments()
    if not segments:
        return pl.DataFrame(
            {"info": ["content 인덱스가 없습니다. dartlab.providers.dart.search.rebuildContent() 실행 필요."]}
        )

    routerModel = loadRouterModel(_activeIndexDir())  # 세그먼트와 동거 — 부재 시 None
    weights = _expansionWeights(query, routerModel)
    hasExpansion = len(weights) > len(set(tokens))

    allHits: list[dict] = []
    deltaKeys: set[tuple] = set()
    for name in ("delta", "main"):
        if name not in segments:
            continue
        idx, meta = segments[name]
        plain = _scoreBM25(idx, tokens)
        if hasExpansion:
            boosted = _scoreBM25(idx, list(weights), weights=weights)
            fused = _rrfFuse(plain, boosted)
        else:
            fused = plain
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
