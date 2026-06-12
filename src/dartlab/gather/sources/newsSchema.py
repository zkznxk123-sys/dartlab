"""뉴스 archive canonical 단일 스키마 — 전 소스(rss·gdelt·naver) 공유 SSOT.

옛 구조는 `news.py`(7컬럼)·`gdelt.py`(16컬럼)·`newsHeadlines.py`(7컬럼)가 *같은
이름 `_ARCHIVE_SCHEMA`* 를 제각각 정의해 `loadNewsArchive` 가 `diagonal_relaxed`
concat 으로 봉합했다. 본 모듈이 **17컬럼 superset 1개**로 통일한다.

설계: base 8(date·title·source·url·market·query·captured_at·description) +
enrichment 9(sentiment_score·sentiment_label·model_version·topic_id·topic_label·
topic_prob·themes·language·tone_raw). 모든 소스 archive 진입점은 마지막에
`coerceToCanonical` 1회로 누락 컬럼을 null 채움 → 출력 데이터 계약 통일.

- `description` (신규): naver 스니펫. rss/gdelt 는 null.
- enrichment 9: gdelt 가 built-in 으로 채우고, rss/naver 는 enrich 단계(Phase B)가 채움.
"""

from __future__ import annotations

import polars as pl

# 뉴스 archive canonical 스키마 (17컬럼 superset). 컬럼 순서 = 출력 계약.
NEWS_ARCHIVE_SCHEMA: dict[str, pl.DataType] = {
    # ── base 8 ──
    "date": pl.Date,
    "title": pl.Utf8,
    "source": pl.Utf8,
    "url": pl.Utf8,
    "market": pl.Utf8,
    "query": pl.Utf8,
    "captured_at": pl.Datetime("us", time_zone="UTC"),
    "description": pl.Utf8,  # naver 스니펫 (rss/gdelt=null)
    # ── enrichment 9 (gdelt built-in / Phase B 채움) ──
    "sentiment_score": pl.Float64,
    "sentiment_label": pl.Utf8,
    "model_version": pl.Utf8,
    "topic_id": pl.Int32,
    "topic_label": pl.Utf8,
    "topic_prob": pl.Float64,
    "themes": pl.List(pl.Utf8),
    "language": pl.Utf8,
    "tone_raw": pl.Float64,
}

# 라이브 verb / 최소 표면이 쓰는 base 컬럼 (enrichment 제외).
NEWS_BASE_COLS: tuple[str, ...] = (
    "date",
    "title",
    "source",
    "url",
    "market",
    "query",
    "captured_at",
    "description",
)


def coerceToCanonical(df: pl.DataFrame | None) -> pl.DataFrame:
    """임의 뉴스 DataFrame 을 canonical 17컬럼으로 정렬·보강.

    Sig: ``coerceToCanonical(df) -> pl.DataFrame``

    Capabilities:
        - 누락 컬럼을 해당 dtype 의 null 로 채움
        - 컬럼 순서·dtype 를 NEWS_ARCHIVE_SCHEMA 로 강제 (cast strict=False)
        - None/빈 입력은 동일 schema 빈 DataFrame

    AIContext:
        각 소스 archive 진입점(`fetchHeadlinesForArchive`·`fetchGdeltGkg`)이 마지막에
        1회 호출 → 세 소스 출력 컬럼셋을 byte 단위 동일하게 만든다 (대칭의 실질).

    Guide:
        입력은 일부 컬럼만 있어도 된다 — 누락은 null, cast 불가 값도 null
        (strict=False). 스키마 외 컬럼은 drop.

    When:
        소스 archive 진입점 마지막 + writeDailyParquet 저장 직전 (이중 안전).

    How:
        NEWS_ARCHIVE_SCHEMA 순회 select — 보유 컬럼 cast, 미보유 pl.lit(None) cast.

    Requires:
        없음.

    Args:
        df: 임의 뉴스 DataFrame (일부 컬럼만 보유 가능). None/빈 허용.

    Returns:
        pl.DataFrame — NEWS_ARCHIVE_SCHEMA 17컬럼·순서·dtype. 입력이 비면 빈 DataFrame.

    Raises:
        없음 — cast 는 strict=False (불가 값은 null).

    Example:
        >>> import polars as pl
        >>> coerceToCanonical(pl.DataFrame({"url": ["u"], "title": ["t"]})).columns[:2]
        ['date', 'title']

    See Also:
        ``NEWS_ARCHIVE_SCHEMA``: canonical 17컬럼 SSOT.
        ``gather.sources.newsIo.writeDailyParquet``: 저장 직전 호출자.
    """
    if df is None or df.is_empty():
        return pl.DataFrame(schema=NEWS_ARCHIVE_SCHEMA)
    exprs = []
    for col, dtype in NEWS_ARCHIVE_SCHEMA.items():
        if col in df.columns:
            exprs.append(pl.col(col).cast(dtype, strict=False).alias(col))
        else:
            # pl.lit(None).cast(dtype) — List(Utf8) 등 nested dtype 에도 안전한 null 리터럴.
            exprs.append(pl.lit(None).cast(dtype).alias(col))
    return df.select(exprs)
