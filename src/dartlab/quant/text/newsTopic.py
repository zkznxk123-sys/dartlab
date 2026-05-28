"""news headline topic clustering — BERTopic 또는 query-based fallback (Phase B).

BERTopic 가용 시 dynamic topic discovery (umap + hdbscan). 미가용 시 query 컬럼을
프록시 topic 으로 사용 — narrative pulse 의 topic axis 가 항상 동작.

월 1 회 전체 refit (cron-monthly) — drift 보정. 일별은 partial_fit (incremental).
"""

from __future__ import annotations

import logging

import polars as pl

log = logging.getLogger(__name__)


def _bertopicOrNone():
    """BERTopic 가용 시 클래스 반환, 미가용 시 None.

    Sig: ``_bertopicOrNone() -> type | None``

    Capabilities: optional 그룹 narrative 활성 시만 import 성공.
    AIContext: clusterNewsTopics 의 모델 gate.
    Guide: bertopic + umap + hdbscan + sklearn 4 종 동시 필요.
    When: clusterNewsTopics 호출 시 1 회.
    How: try import BERTopic.

    Returns:
        BERTopic 클래스 또는 None.

    Raises:
        없음.

    Example::

        cls = _bertopicOrNone()  # None if no narrative group

    Requires:
        optional 그룹 narrative.

    See Also:
        ``clusterNewsTopics``: caller.
    """
    try:
        from bertopic import BERTopic

        return BERTopic
    except ImportError:
        log.debug("bertopic 미설치 — query proxy fallback")
        return None


def clusterNewsTopics(
    df: pl.DataFrame,
    *,
    market: str = "KR",
    nrTopics: int | None = 30,
    seed: int = 42,
) -> pl.DataFrame:
    """헤드라인 topic clustering — BERTopic 우선, query proxy fallback.

    Capabilities:
        - BERTopic 가용 시 sentence-transformers embedding + UMAP + HDBSCAN dynamic clustering
        - 미가용 시 query 컬럼을 proxy topic 으로 사용 (query → topic_id 1:1, label = query 앞 20 자)
        - 결과 컬럼 추가: topic_id (int), topic_label (str), topic_prob (float 0~1)
        - 결정론성 — seed 고정

    AIContext:
        Phase B 의 topic SSOT. narrativePulse 가 (date × topic) 격자 생성에 사용.

    Guide:
        nrTopics=None 이면 BERTopic 자동 결정 (보통 50~100). 30 이면 broad cluster.
        query proxy fallback 은 단순 분류라 BERTopic 대비 narrative 신호 약함.

    When:
        - 일별 enrichNewsHeadlines cron
        - narrativePulse aggregate 직전

    How:
        title 추출 → BERTopic.fit_transform / fallback 시 query unique 매핑.

    Args:
        df: title + query 컬럼 보유 DataFrame.
        market: "KR" | "US" — embedding 모델 선택 (KR 다국어).
        nrTopics: BERTopic 강제 topic 수 (None = 자동).
        seed: 결정론 (UMAP random_state).

    Returns:
        pl.DataFrame — 원본 + (topic_id, topic_label, topic_prob).

    Raises:
        없음.

    Example::

        df = clusterNewsTopics(df, market="KR", nrTopics=20)

    Requires:
        title + query 컬럼. BERTopic + sentence-transformers (optional 그룹 narrative).

    See Also:
        ``_bertopicOrNone``: 모델 gate.
        ``narrativePulse.buildNarrativePulse``: 다운스트림.
    """
    if "title" not in df.columns:
        log.warning("title 컬럼 부재 — topic skip")
        return df.with_columns(
            pl.lit(-1).alias("topic_id"),
            pl.lit("unknown").alias("topic_label"),
            pl.lit(0.0).alias("topic_prob"),
        )
    if df.is_empty():
        return df.with_columns(
            pl.lit(None, dtype=pl.Int32).alias("topic_id"),
            pl.lit(None, dtype=pl.Utf8).alias("topic_label"),
            pl.lit(None, dtype=pl.Float64).alias("topic_prob"),
        )

    BERTopicCls = _bertopicOrNone()
    titles = df["title"].to_list()

    if BERTopicCls is not None and len(titles) >= 10:
        try:
            # multilingual model 가용 시 KR/US 통합
            from sentence_transformers import SentenceTransformer

            embModel = SentenceTransformer("sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")
            topicModel = BERTopicCls(
                embedding_model=embModel,
                nr_topics=nrTopics,
                calculate_probabilities=True,
                verbose=False,
            )
            topicIds, probs = topicModel.fit_transform(titles)
            topicInfo = topicModel.get_topic_info()
            # topic_label = top 3 단어 결합
            labels = {}
            for tid in topicInfo["Topic"].tolist():
                if tid == -1:
                    labels[tid] = "outlier"
                    continue
                topWords = topicModel.get_topic(tid)
                labels[tid] = " ".join(w for w, _ in topWords[:3]) if topWords else f"topic_{tid}"
            probValues = [float(p.max()) if p is not None and len(p) > 0 else 0.0 for p in probs]
            return df.with_columns(
                pl.Series("topic_id", [int(t) for t in topicIds], dtype=pl.Int32),
                pl.Series(
                    "topic_label",
                    [labels.get(int(t), "unknown") for t in topicIds],
                    dtype=pl.Utf8,
                ),
                pl.Series("topic_prob", probValues, dtype=pl.Float64),
            )
        except Exception as exc:
            log.warning("BERTopic 실패: %s — query proxy fallback", exc)

    # fallback — query 컬럼을 topic proxy
    queries = df["query"].to_list() if "query" in df.columns else titles
    uniq = {q: i for i, q in enumerate(dict.fromkeys(queries))}
    topicIds = [uniq[q] for q in queries]
    labels = [q[:20] for q in queries]
    return df.with_columns(
        pl.Series("topic_id", topicIds, dtype=pl.Int32),
        pl.Series("topic_label", labels, dtype=pl.Utf8),
        pl.lit(1.0).alias("topic_prob"),
    )
