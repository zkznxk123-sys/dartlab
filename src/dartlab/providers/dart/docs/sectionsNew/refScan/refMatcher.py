"""옛 양식 TABLE-GROUP TITLE → ref table fuzzy match (Layer 1 lookup).

P-S2 검증 게이트: precision ≥ 0.85, recall ≥ 0.70 @ Jaccard threshold.
Ground truth = 같은 회사의 인접 신 양식 분기에서 발견된 동일 ACLASS.

LLM Specifications:
    AntiPatterns:
        - 옛 양식 TITLE 직접 정규식 매칭 금지 — mapper.py 의 260 regex 복귀
          위험. matchToRef 는 token Jaccard 만 사용.
        - threshold hardcode 금지 — caller 파라미터, P-S2 sweep 검증 후 확정.
        - ref table 매번 read 금지 — caller 가 한 번 load 후 dataframe 전달.
    OutputSchema:
        - ``matchToRef(title, refDf, threshold) -> (rawId or None, score)``
    Prerequisites:
        - ref table DataFrame (sectionsXbrlRef.parquet load 결과).
        - titleNormalizer.tokenize.
    Freshness:
        - threshold 변경 시 5 baseline P-S2 재측정.
    Dataflow:
        - 옛 양식 TITLE → normalizeTitle → tokenize → ref entry token Jaccard
          → best match rawId (Jaccard ≥ threshold).
    TargetMarkets:
        - KR (DART). EDGAR 는 별도 (TextBlock concept ID 직접 매칭 가능).

마스터 플랜: v5 §5.3 + P-S2 검증 게이트.
"""

from __future__ import annotations

from functools import lru_cache

import polars as pl

from dartlab.providers.dart.docs.sectionsNew.refScan.titleNormalizer import (
    jaccardSimilarity,
    normalizeTitle,
    tokenize,
)

# Worker init 에서 ref 의 token set 을 한 번 pre-compute → row iter 회피.
# (rawId, frozenset(tokens)) tuple list. corpCount ≥ 3 만.
_REF_TOKENS: list[tuple[str, frozenset]] | None = None


def precomputeRefTokens(
    refDf: pl.DataFrame,
    *,
    onlyCorpCountAtLeast: int = 3,
) -> list[tuple[str, frozenset]]:
    """ref token set pre-compute — worker init 에서 한 번 호출.

    Returns ``[(rawId, frozenset(tokens))]`` list, corpCount 필터 후.
    """
    out: list[tuple[str, frozenset]] = []
    candidates = refDf.filter(
        (pl.col("corpCount") >= onlyCorpCountAtLeast)
        & (pl.col("rawTitleCanonical").is_not_null())
        & (pl.col("rawTitleCanonical").str.len_chars() > 0)
    )
    for row in candidates.iter_rows(named=True):
        toks = frozenset(tokenize(row["rawTitleCanonical"]))
        if toks:
            out.append((row["rawId"], toks))
    return out


def setGlobalRefTokens(refTokens: list[tuple[str, frozenset]]) -> None:
    """worker 의 module-global _REF_TOKENS set."""
    global _REF_TOKENS
    _REF_TOKENS = refTokens
    # cache invalidate (새 ref 시)
    _matchCached.cache_clear()


@lru_cache(maxsize=8192)
def _matchCached(
    queryTokens: frozenset,
    threshold: float,
) -> tuple[str | None, float]:
    """동일 token set 결과 cache — 같은 heading 분기 간 반복 회피."""
    if _REF_TOKENS is None:
        return (None, 0.0)
    bestId: str | None = None
    bestScore = 0.0
    for rawId, refTokens in _REF_TOKENS:
        inter = len(queryTokens & refTokens)
        if inter == 0:
            continue
        union = len(queryTokens | refTokens)
        score = inter / union if union else 0.0
        if score > bestScore:
            bestScore = score
            bestId = rawId
    if bestScore < threshold:
        return (None, bestScore)
    return (bestId, bestScore)


def matchToRef(
    title: str,
    refDf: pl.DataFrame,
    *,
    threshold: float = 0.70,
    onlyCorpCountAtLeast: int = 3,
) -> tuple[str | None, float]:
    """옛 양식 TABLE-GROUP TITLE → ref table best match rawId.

    Args:
        title: 옛 양식 의 TABLE-GROUP TITLE 텍스트 원본.
        refDf: Layer 1 ``sectionsXbrlRef.parquet`` DataFrame.
        threshold: Jaccard cutoff. 기본 0.70 (P-S2 검증 게이트 후 확정 예상).
        onlyCorpCountAtLeast: SSOT 입성 minimum corpCount. 기본 3.

    Returns:
        ``(rawId or None, score)`` — threshold 미달 시 ``(None, best_score)``.

    Examples:
        >>> import polars as pl
        >>> ref = pl.DataFrame({
        ...     "rawId": ["NT_C_D826380", "NT_C_D822100"],
        ...     "rawTitleCanonical": ["재고자산", "유형자산"],
        ...     "corpCount": [5, 5],
        ... })
        >>> matchToRef("재고자산의 구성", ref, threshold=0.5)
        ('NT_C_D826380', 1.0)

    LLM Specifications:
        AntiPatterns:
            - normalize 결과 빈 string 시 ref 와 매칭 시도 금지 — (None, 0.0)
              즉시 반환.
            - score 동률 시 rawId 알파벳 순서 의존 금지 — 첫 hit 반환 (caller
              가 후처리로 corpCount tiebreak 가능).
        OutputSchema:
            - ``tuple[str | None, float]``.
    """
    if not title:
        return (None, 0.0)
    norm = normalizeTitle(title)
    if not norm:
        return (None, 0.0)
    queryTokens = frozenset(tokenize(norm))
    if not queryTokens:
        return (None, 0.0)

    # Pre-compute fast path — worker init 시 setGlobalRefTokens 호출됐으면 사용.
    if _REF_TOKENS is not None:
        return _matchCached(queryTokens, threshold)

    # Fallback — refDf 직접 iter (test / 임시 호출 시)
    if refDf is None or refDf.is_empty():
        return (None, 0.0)
    bestId: str | None = None
    bestScore = 0.0
    candidates = refDf.filter(
        (pl.col("corpCount") >= onlyCorpCountAtLeast)
        & (pl.col("rawTitleCanonical").is_not_null())
        & (pl.col("rawTitleCanonical").str.len_chars() > 0)
    )
    for row in candidates.iter_rows(named=True):
        refTokens = tokenize(row["rawTitleCanonical"])
        if not refTokens:
            continue
        score = jaccardSimilarity(queryTokens, refTokens)
        if score > bestScore:
            bestScore = score
            bestId = row["rawId"]

    if bestScore < threshold:
        return (None, bestScore)
    return (bestId, bestScore)


def evaluateThreshold(
    labeledRows: list[dict],
    refDf: pl.DataFrame,
    *,
    thresholds: list[float] | None = None,
) -> pl.DataFrame:
    """threshold sweep — precision / recall / F1 측정.

    Args:
        labeledRows: 각 row 가 ``{"title": str, "trueRawId": str | None}`` —
            None = ref 에 매칭되어선 안 되는 negative sample.
        refDf: Layer 1 ref DataFrame.
        thresholds: sweep 할 Jaccard cutoff list. 기본 0.4 ~ 0.95 step 0.05.

    Returns:
        DataFrame with cols: threshold / precision / recall / f1 / tp / fp / fn.

    LLM Specifications:
        AntiPatterns:
            - true label 이 None 인 row 무시 금지 — negative sample 도 precision
              계산에 essential.
            - F1 = 0/0 case 0.0 반환 (zero-division 회피).
        OutputSchema:
            - polars DataFrame, 7 col, threshold 별 정렬.
    """
    if thresholds is None:
        thresholds = [0.40, 0.50, 0.60, 0.65, 0.70, 0.75, 0.80, 0.85, 0.90, 0.95]
    rows: list[dict] = []
    for t in thresholds:
        tp = 0
        fp = 0
        fn = 0
        for sample in labeledRows:
            predId, _score = matchToRef(sample["title"], refDf, threshold=t)
            trueId = sample.get("trueRawId")
            if predId is not None and trueId is not None and predId == trueId:
                tp += 1
            elif predId is not None and (trueId is None or predId != trueId):
                fp += 1
            elif predId is None and trueId is not None:
                fn += 1
            # else (None, None) = true negative (precision/recall 에 영향 없음)
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0
        rows.append(
            {
                "threshold": t,
                "precision": precision,
                "recall": recall,
                "f1": f1,
                "tp": tp,
                "fp": fp,
                "fn": fn,
            }
        )
    return pl.DataFrame(rows).sort("threshold")
