"""panel horizontalize mirror — element→section 무손실 concat 단위 (데이터 0).

``gather/dart/panel/build/horizontalize.py`` 의 1:1 mirror. 합성 14-col element 행을
group concat 해 (1) 같은 (chapter, xbrlClass) 가 한 행으로 묶이고 (2) contentRaw 글자 합이
정확히 보존(태그 무손실, R4·G1)되는지 검증.
"""

from __future__ import annotations

import polars as pl
import pytest

pytestmark = pytest.mark.unit


def _row(blockOrder: int, contentRaw: str, *, xbrlClass: str = "BS_C", chapter: str = "A") -> dict:
    """합성 14-col element 행 (모호한 dtype 은 None)."""
    return {
        "chapter": chapter,
        "sectionLeaf": "s",
        "blockLeaf": "",
        "xbrlClass": xbrlClass,
        "xbrlMatched": None,
        "xbrlMatchScore": None,
        "atocId": None,
        "aassocnote": None,
        "blockOrder": blockOrder,
        "contentRaw": contentRaw,
        "period": "2024Q4",
        "corp": "005930",
        "rceptNo": "20250101000001",
        "disclosureKey": None,
    }


def test_horizontalize_groups_and_is_char_lossless() -> None:
    """같은 (chapter, xbrlClass) element 2개 → 1 section 행, contentRaw 글자 합 보존."""
    from dartlab.providers.dart.panel.schema import PANEL_SCHEMA
    from dartlab.providers.dart.panel.build import horizontalize

    rows = [_row(1, "<P>aaa</P>"), _row(2, "<TABLE><TR>b</TR></TABLE>")]
    df = pl.DataFrame(rows, schema=PANEL_SCHEMA)
    srcChars = sum(len(r["contentRaw"]) for r in rows)
    srcTags = sum(r["contentRaw"].count("<") for r in rows)

    out = horizontalize(df)
    assert out.height == 1, "같은 canonical 키 element 는 한 section 으로 묶여야 함"
    outChars = out.select(pl.col("contentRaw").str.len_chars().sum()).item()
    outTags = out.select(pl.col("contentRaw").str.count_matches("<", literal=True).sum()).item()
    assert outChars == srcChars, f"글자 손실/중복: {srcChars} → {outChars}"
    assert outTags == srcTags, f"태그 손실/가공: {srcTags} → {outTags} (R4 위반)"


def test_horizontalize_empty_passthrough() -> None:
    """빈 입력은 그대로 반환."""
    from dartlab.providers.dart.panel.schema import PANEL_SCHEMA
    from dartlab.providers.dart.panel.build import horizontalize

    empty = pl.DataFrame(schema=PANEL_SCHEMA)
    assert horizontalize(empty).height == 0
