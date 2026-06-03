"""leaf text/table 분리 — 확실한 결정론 경계(<TABLE>)를 BUILD 가 별도 행으로 쪼갠다 (무손실).

수평화 정렬은 *같은 타입끼리* 해야 깨끗하다 (표↔표, 텍스트↔텍스트). 한 leaf 가 설명문(text)+표(table)를
섞어 담으면 정렬축이 흐려진다. <TABLE> 유무는 **결정론 경계**라 BUILD 가 나눈다 — BUILD = 확실한 것만 하는 단계.

각 행 contentRaw → 문서순서대로 [text-run, table, text-run, ...] 로 쪼개 행별 leafType 부여.
**무손실**: 쪼갠 part 들을 순서대로 이으면 원본 contentRaw (char-parity 0 보존). chapter/sectionLeaf/sectionPath/
blockLeaf/disclosureKey/xbrlClass 등은 상속, blockOrder 동일(part 순서로 안정 정렬).
"""

from __future__ import annotations

import re

import polars as pl

# TABLE 여는/닫는 태그 (대소문자·self-close 무관). 깊이 카운트로 **outermost** 표 경계만 잡는다 —
# regex .*? 는 nested(레이아웃 표 안 데이터 표)서 첫 </TABLE> 에 멈춰 표 꼬리를 text 로 흘리는 버그(silent).
_TBL_TAG = re.compile(r"<(/?)TABLE[\s/>]", re.IGNORECASE)
_PART_DTYPE = pl.List(pl.Struct({"leafType": pl.Utf8, "contentRaw": pl.Utf8}))


def _outermostTableSpans(cr: str) -> list[tuple[int, int]]:
    """contentRaw 에서 **최외곽** <TABLE>…</TABLE> char span 목록 (nested 표는 바깥 하나로). 깊이 카운트."""
    spans: list[tuple[int, int]] = []
    depth = 0
    start = -1
    for m in _TBL_TAG.finditer(cr):
        if m.group(1):  # '/' = 닫는 태그
            if depth > 0:
                depth -= 1
                if depth == 0:
                    spans.append((start, m.end()))
                    start = -1
        else:  # 여는 태그
            if depth == 0:
                start = m.start()
            depth += 1
    return spans


def splitOrdered(content_raw: str) -> list[dict]:
    """contentRaw → 문서순서 [(leafType, contentRaw)] (table 블록 + 실질 text). 무손실 + de-noise.

    **outermost 표 경계**(깊이 인식)로 분할 — nested 표는 바깥 하나로 묶어 경계 깨짐 없음. part 들을 순서대로
    이으면 byte-identical(span 들이 전체를 타일링). 공백-only 텍스트(표 사이)는 인접 표에 흡수(노이즈 행 0).
    실질 텍스트만 별도 text part. 표 0개/빈 입력은 text 1개.

    Args:
        content_raw: leaf 의 원본 XML 문자열 (None 허용 → "").

    Returns:
        문서순서 ``[{"leafType": "text"|"table", "contentRaw": str}]`` — part 이으면 원본 byte-identical.

    Raises:
        없음 — None/빈 입력은 빈 text 1개.

    Example:
        >>> [p["leafType"] for p in splitOrdered("pre<TABLE>a</TABLE>post")]
        ['text', 'table', 'text']
    """
    cr = content_raw or ""
    raw: list[tuple[str, str]] = []  # (leafType, contentRaw) — 흡수 전
    last = 0
    for s, e in _outermostTableSpans(cr):
        text = cr[last:s]
        tb = cr[s:e]
        if text.strip():
            raw.append(("text", text))  # 실질 텍스트는 별도 행
        elif text:
            tb = text + tb  # 공백-only → 표에 흡수 (무손실, 지문 불변)
        raw.append(("table", tb))
        last = e
    tail = cr[last:]
    if tail.strip() or not raw:
        raw.append(("text", tail))  # 실질 trailing text 또는 표 0개 행
    elif tail:
        raw[-1] = (raw[-1][0], raw[-1][1] + tail)  # trailing 공백 → 마지막 part 흡수
    return [{"leafType": t, "contentRaw": c} for t, c in raw]


def splitLeafTypes(df: pl.DataFrame) -> pl.DataFrame:
    """각 행 → text/table part 행으로 explode (leafType 부여, contentRaw 대체). 무손실.

    BUILD 의 마지막 단계 (horizontalize 병합 + dechunkNotes 분해 후). contentRaw 를 part 로 교체하고
    leafType 을 채운다. 나머지 컬럼 상속. 빈 df 는 그대로.

    Args:
        df: 분할 전 DataFrame (``contentRaw`` 컬럼 보유, leafType 미부여).

    Returns:
        각 leaf 가 text/table part 행으로 explode 된 DataFrame (+``leafType``, contentRaw 대체). 무손실.
        빈/``contentRaw`` 부재 df 는 그대로.

    Raises:
        없음.

    Example:
        >>> out = splitLeafTypes(df)  # doctest: +SKIP
        >>> set(out["leafType"].unique()) <= {"text", "table"}  # doctest: +SKIP
        True
    """
    if df.is_empty() or "contentRaw" not in df.columns:
        return df
    exploded = (
        df.with_columns(pl.col("contentRaw").map_elements(splitOrdered, return_dtype=_PART_DTYPE).alias("_parts"))
        .drop("contentRaw")
        .explode("_parts")
        .unnest("_parts")
    )
    return exploded
