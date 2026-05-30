"""panel BUILD 수평화 — element-granular 행 → section-granular (무손실 concat).

walker 가 emit 한 element 단위 행을 canonical 키(XBRL 표=xbrlClass / narrative=
sectionLeaf·blockLeaf)별로 묶어 ``contentRaw`` 를 ``blockOrder`` 순서대로 join →
한 row = 한 canonical 단위. 런타임 pivot 이 이 row 를 period 축으로 정렬(회사내 수평화).

무손실: contentRaw join 은 모든 element 의 raw XML 을 순서대로 보존 (태그 가공 0, R4).
중복 0: 각 element 는 정확히 한 그룹에 속해 한 번만 concat.

LLM Specifications:
    AntiPatterns:
        - contentRaw concat 시 separator 삽입 금지 — 원본 char 보존(태그 무손실 char 합 검증).
        - group 키에 period 포함 금지 — builder 가 이미 period 별 분리 호출.
        - content_plain 등 파생 컬럼 생성 금지 (단일 contentRaw, R4).
    OutputSchema:
        - ``horizontalize(df) -> pl.DataFrame`` (동일 14-col, section-granular).
    Prerequisites:
        - polars. walker 출력 element-granular DataFrame (단일 period).
    Freshness:
        - walker 출력 schema 변경 시 group 키 재검증.
    Dataflow:
        - element 행 → (chapter, gkey) group → blockOrder 순 contentRaw join → section 행.
    TargetMarkets:
        - KR (DART). US 동일 알고리즘 (us-gaap walker 출력에도 적용).
"""

from __future__ import annotations

import polars as pl


def horizontalize(df: pl.DataFrame) -> pl.DataFrame:
    """element-granular walker 출력 → section-granular (canonical 키별 무손실 concat).

    Args:
        df: walker 출력 element-granular DataFrame (단일 period). 14-col schema.

    Returns:
        section-granular DataFrame (동일 14-col, blockOrder 순 정렬). 빈 입력은 그대로.

    Raises:
        없음 — 빈 DataFrame 은 그대로 반환.

    Example:
        >>> import polars as pl
        >>> out = horizontalize(walkerDf)  # doctest: +SKIP
        >>> out.height <= walkerDf.height  # doctest: +SKIP
        True

    SeeAlso:
        - ``walker.walkSections`` — element-granular 입력 생산.
        - ``builder.buildPanel`` — 본 함수 호출 후 disclosureKey 부착·write.

    Requires:
        - polars.

    Capabilities:
        - 회사내 수평화의 BUILD 단계 — element 를 canonical 단위로 묶어 런타임 pivot 가능 형태로.

    Guide:
        - builder 가 period 별로 호출 — 직접 호출 X.

    AIContext:
        - 순수 변환 — contentRaw 순서 concat, 태그·char 무손실.

    LLM Specifications:
        AntiPatterns:
            - group_by maintain_order=False 금지 — blockOrder 순서 보존 필수(무손실 순서).
            - aggregate 시 contentRaw first() 금지 — join("") 로 전 element 보존.
        OutputSchema:
            - ``pl.DataFrame`` (14-col, section-granular).
        Prerequisites:
            - walker 출력 14-col (xbrlClass/sectionLeaf/blockLeaf/contentRaw/blockOrder 등).
        Freshness:
            - walker schema 변경 시 재검증.
        Dataflow:
            - (chapter, gkey) group → sort(blockOrder) → contentRaw join → min(blockOrder).
        TargetMarkets:
            - KR + US 공통.
    """
    if df.is_empty():
        return df
    gkey = pl.coalesce(
        [
            pl.col("xbrlClass"),
            pl.when(pl.col("sectionLeaf").str.len_chars() > 0).then(pl.col("sectionLeaf")).otherwise(None),
            pl.when(pl.col("blockLeaf").str.len_chars() > 0).then(pl.col("blockLeaf")).otherwise(None),
            pl.lit("__root__"),
        ]
    )
    grouped = (
        df.with_columns(gkey.alias("_gkey"))
        .sort("blockOrder")
        .group_by(["chapter", "_gkey"], maintain_order=True)
        .agg(
            pl.col("sectionLeaf").first(),
            pl.col("blockLeaf").first(),
            pl.col("xbrlClass").first(),
            pl.col("xbrlMatched").first(),
            pl.col("xbrlMatchScore").first(),
            pl.col("atocId").first(),
            pl.col("aassocnote").first(),
            pl.col("blockOrder").min().alias("blockOrder"),
            pl.col("contentRaw").str.join("").alias("contentRaw"),  # 태그 무손실 순서 concat
            pl.col("period").first(),
            pl.col("corp").first(),
            pl.col("rceptNo").first(),
            pl.col("disclosureKey").first(),
        )
        .drop("_gkey")
        .sort("blockOrder")
    )
    return grouped
