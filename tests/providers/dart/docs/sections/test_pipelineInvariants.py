"""sections() 결과 invariant 회귀 가드 — pipeline 4 fix 의 직접 assertion.

본 commit 4 fix 의 *동작 invariant* 를 baseline 비교가 아닌 직접 assertion 으로
검증. parity test (test_sectionsPolarsParity.py) 는 baseline parquet 과의 일치만
보장 — baseline 을 새 buggy 결과로 regen 하면 회귀가 통과해버린다. 본 test 는
fix 가 *왜* 필요했는지의 invariant 를 코드에 박아 baseline 우회 회귀 차단.

가드 4 종:
    1. companyOverview 2026Q1 placeholder 의 textPath 가 '회사의 개요' 인지
       (commit 260f82657 — chapter row catch-all 등록 시 placeholder 가 다른
       sub-section textPath 로 alias 되던 회귀).
    2. chapter-only unique line ('회사채 미상환 잔액', 'AA-&cr;',
       '사외이사 선임의 건(후보:최종원)') 이 sections cell 에 등장하는지
       (commit dd2c6c0a8 — chapter row 폐기 시 chapter-only 본문 손실 회귀).
    3. table block 의 textPath 가 null 인 row 의 비율
       (commit 0f719c442 — 표가 어떤 heading 아래인지 미부여 회귀).
    4. 모든 topic 의 blockOrder 가 0-based contiguous
       (commit 7d6df7327 — dedup 후 blockOrder gap 회귀).

대상: 000660 (SK하이닉스) — 옛 보고서 (XI. 그 밖에..., III. 재무에 관한 사항)
에 chapter-only 표 다수 존재, 2026Q1 분기보고서 placeholder, consolidatedNotes
표 풍부 — 4 fix 모두 같은 회사로 검증 가능한 최적 fixture.

baseline parquet 부재 시 skip. realData + slow.
"""

from __future__ import annotations

from pathlib import Path

import polars as pl
import pytest

pytestmark = [pytest.mark.realData, pytest.mark.slow]

_STOCK = "000660"
_DATA_PATH = Path(__file__).resolve().parents[5] / "data" / "dart" / "docs" / f"{_STOCK}.parquet"


def _hasData() -> bool:
    return _DATA_PATH.exists()


@pytest.fixture(scope="module")
def sectionsFrame() -> pl.DataFrame:
    """000660 sections frame — module scope cache."""
    if not _hasData():
        pytest.skip(f"data 부재: {_DATA_PATH}")
    from dartlab.core import dataLoader

    dataLoader._shouldRefreshDart = lambda *a, **k: False  # noqa: SLF001
    from dartlab.providers.dart.docs.sectionsLegacy.pipeline import _preparedCache, sections

    _preparedCache.clear()
    df = sections(_STOCK, topics=None)
    assert df is not None, f"{_STOCK}: sections() returned None"
    return df


def test_placeholder_textpath_not_aliased(sectionsFrame: pl.DataFrame) -> None:
    """2026Q1 분기보고서 의 '1. 회사의 개요' placeholder ('기재하지 아니하였습니다')
    가 companyOverview 의 첫 row 에 위치하고 textPath 가 '회사의 개요' 인지.

    회귀 시나리오: chapter row 등록 + sub-section title 미 prepend → heading state
    가 다른 sub-section (예 '정관 > 사업목적추가현황') 로 박혀 placeholder 가 그
    row 에 잘못 채워짐. fix (commit 260f82657) 는 chapter row 폐기 + title prepend.
    """
    if "2026Q1" not in sectionsFrame.columns:
        pytest.skip("2026Q1 분기보고서 부재")
    co = sectionsFrame.filter(pl.col("topic").cast(pl.Utf8) == "companyOverview").sort("blockOrder")
    q1 = co.filter(pl.col("2026Q1").is_not_null())
    assert q1.height > 0, "companyOverview 의 2026Q1 cell 이 모두 null"
    # 첫 2 row 에 자기 sub-section heading + placeholder
    first2 = q1.head(2)
    paths = first2["textPath"].cast(pl.Utf8).to_list()
    cells = first2["2026Q1"].cast(pl.Utf8).to_list()
    assert all("회사의 개요" in (p or "") for p in paths), (
        f"2026Q1 placeholder textPath 가 '회사의 개요' 아님 (alias 회귀 가능): paths={paths}"
    )
    # textPath 에 '정관' / '사업목적' 포함되면 직전 회귀 재현 — 명시 차단
    for p in paths:
        assert "정관" not in (p or "") and "사업목적" not in (p or ""), (
            f"2026Q1 placeholder 가 정관/사업목적 textPath 로 alias — 회귀 재현: path={p}"
        )
    # 적어도 한 cell 은 placeholder '기재하지 아니하였' 포함
    assert any("기재하지 아니하" in (c or "") for c in cells), (
        f"2026Q1 placeholder 본문 누락 — cells={[c[:40] for c in cells]}"
    )


_CHAPTER_ONLY_SAMPLE_LINES = (
    # 20210817001301 'III. 재무에 관한 사항' chapter row 에만 있던 표 cell
    "회사채 미상환 잔액",
    # 20210330000776 회사채 신용등급 표 cell
    "AA-&cr;",
    # 20170331004537 'XI. 그 밖에 투자자 보호…' chapter-only 표 row
    "사외이사 선임의 건(후보:최종원)",
)


def test_chapter_only_lines_recovered(sectionsFrame: pl.DataFrame) -> None:
    """chapter row 가 sub-section 으로 분할 안 된 *고유* 표 row 가 sections cell
    에 살아있는지.

    회귀 시나리오: chapter row 를 sub-section 있으면 통째로 폐기 → 위 3 종 line
    이 누락. fix (commit dd2c6c0a8) 는 chapter content 의 block 중 sub-section
    line set 에 없는 의미있는 line 보유 block 만 lonely 등록.

    SK하이닉스 옛 분기/사업 보고서 (2017~2021) 에 chapter-only 표 다수 — 본
    sample 3 종 모두 hits ≥ 1 보장. hits=0 이면 chapter-only 손실 회귀.
    """
    periodCols = [c for c in sectionsFrame.columns if c[:4].isdigit()]
    assert periodCols, "period 컬럼이 없음 — pipeline 출력 비정상"
    for line in _CHAPTER_ONLY_SAMPLE_LINES:
        hits = 0
        for col in periodCols:
            hits += sectionsFrame.filter(pl.col(col).cast(pl.Utf8).str.contains(line, literal=True)).height
        assert hits > 0, (
            f"chapter-only line {line!r} 가 모든 period cell 에서 사라짐 — "
            f"chapter row 폐기 회귀 (commit dd2c6c0a8 의 unique-block 로직 망가짐)"
        )


def test_table_textpath_propagated(sectionsFrame: pl.DataFrame) -> None:
    """모든 table block row 가 직전 heading 의 textPath 를 상속하는지.

    회귀 시나리오: _expandStructuredRows 의 blockType != 'text' 분기에서 textPath
    를 None 으로 설정 → 표가 어떤 heading 아래인지 식별 불가, viewer 가 표를
    무관한 leaf 에 박음. fix (commit 0f719c442) 는 현재 heading state 의 textPath
    propagation.

    임계: null textPath table row 비율 ≤ 5% (heading 등장 전 표 등 예외 허용).
    """
    tables = sectionsFrame.filter(pl.col("blockType").cast(pl.Utf8) == "table")
    if tables.height == 0:
        pytest.skip("table row 0 — 검증 skip")
    nullCount = tables.filter(pl.col("textPath").is_null()).height
    nullRatio = nullCount / tables.height
    assert nullRatio <= 0.05, (
        f"table row 중 textPath null 비율 {nullRatio:.2%} — "
        f"5% 임계 초과 (propagation 회귀). null={nullCount} / total={tables.height}"
    )


def test_block_order_contiguous_per_topic(sectionsFrame: pl.DataFrame) -> None:
    """모든 topic 의 blockOrder 가 0-based contiguous (gap 0).

    회귀 시나리오: dedup 후 blockOrder 가 듬성듬성 (예 29, 32, 44...) — viewer
    에서 row 누락된 것처럼 보임. fix (commit 7d6df7327) 는 topic 별 cum_count
    재부여.
    """
    for topic in sectionsFrame["topic"].unique().to_list():
        sub = sectionsFrame.filter(pl.col("topic") == topic).sort("blockOrder")
        bos = sub["blockOrder"].to_list()
        expected = list(range(len(bos)))
        assert bos == expected, (
            f"topic={topic} blockOrder gap: first 5 = {bos[:5]}, len={len(bos)}, expected first 5 = {expected[:5]}"
        )
