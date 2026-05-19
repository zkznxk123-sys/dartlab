"""재무제표 주석 sub-topic 수평화 — financialNotes/consolidatedNotes 분할.

DART 사업보고서의 "5. 재무제표 주석" / "3. 연결재무제표 주석" 은 31~32 개의
N. 헤딩 (`1. 일반적 사항`, `2. 중요한 회계처리방침`, ... `32. 보고기간후사건`)
으로 구성된다. 전체가 한 topic 이라 길고 느림 — 본 모듈이 sections frame 의
notes row 들을 N. 패턴으로 sub-topic 분할한다.

알고리즘:
1. notes row 의 본문 (모든 period 컬럼 중 첫 non-empty) 첫 줄에서 ``N.`` 추출.
2. ``cumsum`` 으로 연속 row 그룹 만들기 — 다음 ``M.`` 헤딩 만날 때까지 같은 그룹.
3. 각 그룹의 topic 을 ``{parent}_{NN}_{slug}`` 로 rewrite, sourceTopic 보존.

NOTES_SUB_SECTIONS (reference SSOT) 의 (번호, slug, 한글) 매핑 사용.
"""

from __future__ import annotations

import re

import polars as pl

from dartlab.reference.docs.topicStandard import NOTES_SUB_SECTIONS, notesSubTopicKey

# DART 표준 31 주석 번호 → (slug, 한글 label) — O(1) lookup
_NOTES_BY_NUMBER: dict[int, tuple[str, str]] = {num: (slug, korean) for num, slug, korean in NOTES_SUB_SECTIONS}

# 주석 분할 대상 parent topic.
_NOTES_PARENT_TOPICS: tuple[str, ...] = ("financialNotes", "consolidatedNotes")

# ``N.`` 헤딩 매처 — "1. 일반적 사항", "12. 차입금" 등.
# &cr; (DART HTML escape) + 줄바꿈 분기 동시 수용.
_NOTES_HEADING_RE = re.compile(r"^\s*(\d{1,2})\.\s+([^\n\r]{2,80})")


def _extractNoteNumber(body: str | None) -> int | None:
    """body 첫 줄에서 ``N.`` 헤딩 추출 → 표준 1~32 안의 N 반환. 매칭 없으면 None."""
    if not isinstance(body, str) or not body:
        return None
    match = _NOTES_HEADING_RE.match(body)
    if not match:
        return None
    try:
        number = int(match.group(1))
    except ValueError:
        return None
    return number if number in _NOTES_BY_NUMBER else None


def splitNotesSections(df: pl.DataFrame) -> pl.DataFrame:
    """sections frame 의 notes row 들을 sub-topic 으로 분할.

    Args:
        df: sections frame (``c.sections`` 의 raw — chapter/topic/blockOrder/period... 컬럼).

    Returns:
        분할 후 sections frame. notes 외 topic 은 변경 0. parent topic key (예
        ``financialNotes``) 은 row 별로 sub-topic key (``financialNotes_05_xyz``) 로
        rewrite, ``sourceTopic`` 에 원래 parent 보존.

    Example:
        >>> splitNotesSections(c.sections)  # financialNotes 113 rows → 31 sub-topic 으로 분할

    동작 보장:
        - 분할 대상 topic 에서 ``N.`` 헤딩 추출 실패 (예 옛 보고서 형식) row 는
          그대로 parent topic 유지.
        - 분할 후 sub-topic 의 blockOrder 는 그 sub-topic 안에서 0-based 재할당.
    """
    if df is None or df.height == 0 or "topic" not in df.columns:
        return df
    if "sourceTopic" not in df.columns:
        df = df.with_columns(pl.col("topic").alias("sourceTopic"))
    notes_mask = pl.col("topic").is_in(_NOTES_PARENT_TOPICS)
    if not df.filter(notes_mask).height:
        return df

    # 본문 추출용 period 컬럼 — annual (사업보고서, `2024` 등) 만 사용.
    # 이유: 분기보고서와 사업보고서가 동일 주석에도 *다른* N 번호를 매김 (분기엔
    # 일부 sub-section 생략). NOTES_SUB_SECTIONS SSOT 는 사업보고서 표준 번호 기준
    # 이므로 분기 본문으로 N 추출하면 잘못된 sub-topic key 생성. annual 우선.
    annual_cols = [c for c in df.columns if re.fullmatch(r"\d{4}", c)]
    quarter_cols = [c for c in df.columns if re.fullmatch(r"\d{4}Q[1-4]", c)]
    # annual 최신부터 (예 2025 > 2024 > 2023), 없으면 quarter Q4 (사업보고서 동치) → 그 외 quarter.
    annual_cols_sorted = sorted(annual_cols, reverse=True)
    q4_cols_sorted = sorted([c for c in quarter_cols if c.endswith("Q4")], reverse=True)
    other_q_cols_sorted = sorted([c for c in quarter_cols if not c.endswith("Q4")], reverse=True)
    period_cols_sorted = annual_cols_sorted + q4_cols_sorted + other_q_cols_sorted

    # (topic, blockOrder) 정렬 — cumsum 그룹화의 정확성을 위해 보고서 흐름 순서 강제.
    # docsSec frame 의 default 순서는 입력 데이터 순서이지 보고서 흐름이 아닐 수 있다.
    notes_df = df.filter(notes_mask).sort(["topic", "blockOrder"])
    other_df = df.filter(~notes_mask)

    # 본문 추출 — period 컬럼 중 첫 non-empty 가 대표 본문.
    def _firstNonEmptyBody(row: dict) -> str | None:
        for p in period_cols_sorted:
            v = row.get(p)
            if isinstance(v, str) and v.strip():
                return v
        return None

    # to_dicts 로 row iteration — note number 추출 + cumsum 그룹화.
    rows = notes_df.to_dicts()
    # parent topic 별로 cumsum (마지막으로 본 노트 번호 유지 — 같은 노트 안 row 동일 번호).
    last_number: dict[str, int | None] = {p: None for p in _NOTES_PARENT_TOPICS}
    note_numbers: list[int | None] = []
    for row in rows:
        parent = row.get("topic")
        body = _firstNonEmptyBody(row)
        n = _extractNoteNumber(body)
        if n is not None:
            last_number[parent] = n
        note_numbers.append(last_number.get(parent))

    # 새 topic key 계산 — None 이면 그대로 parent (매칭 못한 옛 row).
    new_topics: list[str] = []
    for row, n in zip(rows, note_numbers, strict=False):
        parent = row["topic"]
        if n is None:
            new_topics.append(parent)
            continue
        slug, _korean = _NOTES_BY_NUMBER[n]
        new_topics.append(notesSubTopicKey(parent, n, slug))

    # notes_df 의 topic 컬럼 rewrite. blockOrder 재할당은 보조 처리.
    notes_df = notes_df.with_columns(pl.Series("topic", new_topics, dtype=notes_df.schema["topic"]))

    # blockOrder 재할당 — sub-topic 안에서 0-based.
    notes_df = notes_df.sort("blockOrder").with_columns(
        (pl.cum_count("blockOrder").over("topic", mapping_strategy="group_to_rows") - 1)
        .cast(pl.Int64)
        .alias("blockOrder")
    )

    return pl.concat([other_df, notes_df], how="vertical_relaxed").sort(["topic", "blockOrder"])
