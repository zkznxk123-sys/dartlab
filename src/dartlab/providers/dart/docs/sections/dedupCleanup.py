"""chapter-level catch-all 중복 row drop + blockOrder contiguous 재부여.

Phase 4 cleanup. Phase 1 의 unique-block fix 가 대부분 차단하지만 defensive
layer 로 남아있음. operation.sectionsRefactor §4-2 부채 — Phase 1 단일화
대상이지만 본 PR 에선 분리만, 폐기는 트랙 D 에서.

본 모듈은 ``pipeline.py`` 에서 분리됨 (operation.sectionsRefactor §5 부채 1).
caller API 0 변경 — pipeline.py 가 본 함수를 re-import.
"""

from __future__ import annotations

import re

import polars as pl

_CHAPTER_CATCH_ALL_RE = re.compile(r"^(?:I{1,3}|IV|V|VI{0,3}|IX|X|XI|XII)\.\s")


def _dropChapterCatchAllDuplicates(df: pl.DataFrame) -> pl.DataFrame:
    """chapter-level catch-all 중복 row drop.

    문제: ``sectionMappings.json`` 의 ``"I. 회사의 개요"`` 류 룰이 chapter heading
    자체일 때 모든 sub-block 을 chapter-level topic 으로 일괄 매핑. 동시에
    sub-heading block 은 specific topic 으로 매핑 — 같은 ``sourceBlockOrder`` 가
    두 topic 으로 중복.

    해결: ``sourceTopic`` 이 chapter title catch-all 이고 같은
    ``(chapter, sourceBlockOrder)`` 가 non-catch-all sourceTopic row 로 존재하면
    catch-all row drop. specific 단독 sourceBlockOrder 는 KEEP.

    Args:
        df: ``sections()`` 의 raw 결과.

    Returns:
        catch-all 중복 row 제거된 frame.
    """
    if df is None or df.height == 0:
        return df
    needed = {"sourceTopic", "sourceBlockOrder", "chapter"}
    if not needed.issubset(df.columns):
        return df

    is_catch_all = pl.col("sourceTopic").cast(pl.Utf8).str.contains(_CHAPTER_CATCH_ALL_RE.pattern)
    specific_keys = (
        df.lazy()
        .filter(pl.col("sourceTopic").is_not_null() & ~is_catch_all)
        .select(["chapter", "sourceBlockOrder"])
        .unique()
        .with_columns(pl.lit(True).alias("_hasSpecific"))
        .collect()
    )
    if specific_keys.is_empty():
        return df

    joined = df.join(specific_keys, on=["chapter", "sourceBlockOrder"], how="left")
    keep = ~(is_catch_all & pl.col("_hasSpecific").fill_null(False))
    dedup = joined.filter(keep).drop("_hasSpecific")

    # dedup 후 blockOrder 가 듬성듬성 — topic 별 0-based contiguous 재부여.
    # sourceBlockOrder 는 보존 (원본 DART HTML block 인덱스).
    if "blockOrder" in dedup.columns and "topic" in dedup.columns and dedup.height > 0:
        dedup = dedup.sort(["topic", "blockOrder"]).with_columns(
            (pl.cum_count("blockOrder").over("topic", mapping_strategy="group_to_rows") - 1)
            .cast(pl.Int64)
            .alias("blockOrder")
        )
    return dedup
