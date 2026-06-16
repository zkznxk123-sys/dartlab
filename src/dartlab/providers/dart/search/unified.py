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
    _scopeMask,
    _scoreBM25,
    tokenizeContent,
)
from dartlab.providers.dart.search.router import loadRouterModel, routeCanon

_log = getLogger(__name__)

RRF_K = 60  # reciprocal-rank 융합 상수 (landing·recipe parity)
EXPAND_BOOST = 0.5  # 확장토큰 가중 (질의 원토큰 1.0 대비)
EVENT_TITLE_CANDIDATE_FLOOR = 5000
EVENT_TITLE_CANDIDATE_MULTIPLIER = 500
_EVENT_TITLE_TERMS: tuple[str, ...] = (
    "공시",
    "원문",
    "결정",
    "변경",
    "제출",
    "체결",
    "발행",
    "취득",
    "처분",
    "소집",
    "결과",
    "합병",
    "분할",
    "양수",
    "양도",
    "소송",
    "횡령",
    "배임",
    "영업정지",
    "배당",
)
_BODY_SEMANTIC_TERMS: tuple[str, ...] = (
    "본문",
    "주석",
    "사업의 내용",
    "위험",
    "리스크",
    "risk",
    "md&a",
    "유동성",
    "손상",
    "정책",
    "비중",
    "만기",
)
_NON_DECISION_TERMS: tuple[str, ...] = ("결과", "제출", "보고서", "기사", "뉴스")
_DECISION_RESULT_TERMS: tuple[str, ...] = ("발행결과", "청약결과", "증권발행실적")


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
    sourceKind: str | None = None,
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
    eventTitleRerank = _prefersEventTitleRerank(query)
    candidateLimit = _candidateLimit(query, limit) if eventTitleRerank else limit * 3

    allHits: list[dict] = []
    deltaKeys: set[tuple] = set()
    for name in ("delta", "main"):
        if name not in segments:
            continue
        idx, meta = segments[name]
        # corp/stock 스코프는 RRF *전* lane 점수에 적용 — "회사 안에서 검색" 의미론.
        # 사후 필터는 전역 top-N 에 못 들면 0건이 되는 결함 (흔한 질의 + 회사 지정).
        mask = _scopeMask(meta, corpCode, stockCode, sourceKind)
        plain = _scoreBM25(idx, tokens)
        if mask is not None:
            plain = np.where(mask, plain, 0.0)
        if hasExpansion:
            boosted = _scoreBM25(idx, list(weights), weights=weights)
            if mask is not None:
                boosted = np.where(mask, boosted, 0.0)
            fused = _rrfFuse(plain, boosted)
        else:
            fused = plain
        top = np.argsort(-fused)[:candidateLimit]
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

    if eventTitleRerank:
        allHits = _rerankEventTitleHits(query, allHits, routerModel)

    # corp/stock 스코프는 _scopeMask 로 랭킹 전 적용 완료 — 사후 필터 불필요.
    df = pl.DataFrame(allHits).sort("score", descending=True)
    return _resolveResultUrl(df).head(limit)


def _candidateLimit(query: str, limit: int) -> int:
    """Return a wider candidate pool for generic event-title filing queries."""
    del query
    return max(limit * EVENT_TITLE_CANDIDATE_MULTIPLIER, EVENT_TITLE_CANDIDATE_FLOOR)


def _prefersEventTitleRerank(query: str) -> bool:
    """Whether the query asks for a disclosure event/title rather than body evidence."""
    text = " ".join(str(query or "").strip().lower().split())
    if not text:
        return False
    if any(term in text for term in _BODY_SEMANTIC_TERMS) and "제출" not in text:
        return False
    return any(term in text for term in _EVENT_TITLE_TERMS)


def _rerankEventTitleHits(query: str, hits: list[dict], routerModel: dict | None) -> list[dict]:
    """Rerank broad BM25 candidates with report title, event canon, and freshness signals."""
    if not hits:
        return hits
    weights = _eventTitleWeights(query, routerModel)
    dates = [_dateOrdinal(row.get("rcept_dt")) for row in hits]
    maxDate = max(dates or [0])
    minDate = min([value for value in dates if value] or [maxDate])
    dateSpan = max(1, maxDate - minDate)
    genericDecision = _genericDecisionQuery(query)
    ranked: list[dict] = []
    total = max(1, len(hits))
    for index, row in enumerate(hits):
        title = " ".join(str(row.get(key) or "") for key in ("report_nm", "section_title"))
        titleScore = _weightedTokenOverlap(title, weights)
        decisionScore = _decisionTitleScore(title, genericDecision=genericDecision, query=query)
        sourceScore = 1.0 if str(row.get("source") or "") == "allFilings" else 0.0
        dateValue = _dateOrdinal(row.get("rcept_dt"))
        freshness = (dateValue - minDate) / dateSpan if dateValue else 0.0
        originalRank = 1.0 - (index / total)
        finalScore = (
            float(row.get("score") or 0.0)
            + 8.0 * titleScore
            + 7.0 * decisionScore
            + 1.5 * sourceScore
            + 1.5 * freshness
            + 2.0 * originalRank
        )
        ranked.append({**row, "score": finalScore})
    return sorted(ranked, key=lambda row: float(row.get("score") or 0.0), reverse=True)


def _eventTitleWeights(query: str, routerModel: dict | None) -> dict[str, float]:
    weights = _expansionWeights(query, routerModel)
    if _genericDecisionQuery(query):
        for token in tokenizeContent("결정 주요사항보고서"):
            weights[token] = max(weights.get(token, 0.0), 0.7)
    return weights


def _genericDecisionQuery(query: str) -> bool:
    text = str(query or "")
    return ("공시" in text or "원문" in text) and not any(term in text for term in _NON_DECISION_TERMS)


def _weightedTokenOverlap(text: str, weights: dict[str, float]) -> float:
    tokens = set(tokenizeContent(text))
    if not tokens:
        return 0.0
    return sum(float(weight) for token, weight in weights.items() if token in tokens)


def _decisionTitleScore(title: str, *, genericDecision: bool, query: str) -> float:
    if "결정" not in query and not genericDecision:
        return 0.0
    score = 1.0 if "결정" in title else 0.0
    if genericDecision and any(term in title for term in _DECISION_RESULT_TERMS):
        score -= 1.0
    return score


def _dateOrdinal(value: object) -> int:
    digits = "".join(ch for ch in str(value or "") if ch.isdigit())[:8]
    if len(digits) != 8:
        return 0
    try:
        year = int(digits[:4])
        month = int(digits[4:6])
        day = int(digits[6:8])
    except ValueError:
        return 0
    return year * 372 + month * 31 + day
