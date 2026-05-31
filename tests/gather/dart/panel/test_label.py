"""panel buildLabel — canonicalKey → 한글 표시라벨 (P4, synthetic ref 경량).

panelXbrlRef 의 (rawId→canonicalKey, rawTitleCanonical, corpCount) 에서 canonicalKey 별
corpCount 최빈 제목을 대표 라벨로. 손 큐레이션 0. synthetic ref 로 검증 — 실데이터 불요.
"""

from __future__ import annotations

import polars as pl
import pytest

from dartlab.gather.dart.panel import buildLabel

pytestmark = pytest.mark.unit


def test_build_label_from_ref(tmp_path) -> None:
    """ref → canonicalKey 별 최빈 제목 (rawId scope-strip + corpCount tiebreak)."""
    ref = pl.DataFrame(
        {
            "rawId": ["NT_C_D826380", "NT_S_D826385", "BS_C", "BS_S"],
            "rawTitleCanonical": ["재고자산", "재고자산", "재무상태표", "재무상태표"],
            "corpCount": [10, 8, 20, 18],
            "marketNs": ["kr", "kr", "kr", "kr"],
        }
    )
    refP = tmp_path / "ref.parquet"
    ref.write_parquet(str(refP))
    outP = tmp_path / "_label.parquet"

    res = buildLabel(marketNs="kr", refPath=refP, outPath=outP, verbose=False)
    assert res["rowCount"] == 3  # NT_D826380, NT_D826385, BS (BS_C·BS_S 병합)

    label = pl.read_parquet(str(outP))
    d = dict(zip(label["canonicalKey"].to_list(), label["labelKr"].to_list(), strict=False))
    assert d["NT_D826380"] == "재고자산"
    assert d["NT_D826385"] == "재고자산"
    assert d["BS"] == "재무상태표"


def test_build_label_missing_ref(tmp_path) -> None:
    """ref 부재 → rowCount 0 (raise 0)."""
    res = buildLabel(marketNs="kr", refPath=tmp_path / "nope.parquet", outPath=tmp_path / "out.parquet", verbose=False)
    assert res["rowCount"] == 0
