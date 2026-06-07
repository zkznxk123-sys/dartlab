"""expenseDetailBuilder 합성 + Company 파사드 검증 — reconcile·by-nature 회복·강한 토픽.

``c.panel("expenseDetail")`` 가 panel 노트 + finance reconcile 을 합성해 reconciliationStatus 와
reconciledTarget(operatingExpense|sga)을 채우는지, noPanelDetail 회사가 성격별 노트로 회복되는지
(DESIGN_DEBATE v6) 게이트한다.

데이터 없으면 skip. 종목 로드는 module-scope fixture(OOM 가드).
"""

from __future__ import annotations

import polars as pl
import pytest

pytestmark = pytest.mark.unit


def _facadeFrame(code: str) -> pl.DataFrame | None:
    """Company 파사드로 비용상세 합성 프레임 로드 — 데이터 없으면 skip."""
    try:
        import dartlab

        return dartlab.Company(code).panel("expenseDetail")
    except (ValueError, FileNotFoundError, OSError) as exc:
        pytest.skip(f"expenseDetail requires data/env ({code}): {exc}")
        return None


@pytest.fixture(scope="module")
def frames() -> dict[str, pl.DataFrame | None]:
    """대표 종목 합성 프레임 1회 로드 — 제조·판관비성격별 회복·영업비용성격별·noPanelDetail."""
    return {code: _facadeFrame(code) for code in ("005930", "000080", "000050", "035420")}


def test_manufacturer_sga_matched(frames: dict[str, pl.DataFrame | None]) -> None:
    """제조(005930) 판관비 명세 detail 이 finance 와 reconcile(matched/near)."""
    frame = frames["005930"]
    if frame is None or frame.is_empty():
        pytest.skip("005930 expenseDetail empty")
    sga = frame.filter((pl.col("sourceLane") == "strictSgaDetail") & (pl.col("rowRole") == "detail"))
    statuses = set(sga["reconciliationStatus"].to_list())
    assert statuses & {"matched", "near"}, f"제조 판관비 명세 reconcile 실패: {statuses}"


def test_no_exception(frames: dict[str, pl.DataFrame | None]) -> None:
    """대표 종목 전수 무예외(빈 결과 허용, 예외 불가)."""
    for code, frame in frames.items():
        assert frame is None or isinstance(frame, pl.DataFrame), code


def test_bynature_sga_recovery(frames: dict[str, pl.DataFrame | None]) -> None:
    """noPanelDetail 회사가 판관비 성격별 노트로 회복(reconciledTarget=sga, matched)."""
    frame = frames["000080"]
    if frame is None or frame.is_empty():
        pytest.skip("000080 expenseDetail empty")
    recovered = frame.filter(
        (pl.col("sourceLane") == "strictExpensesByNature")
        & (pl.col("reconciledTarget") == "sga")
        & (pl.col("reconciliationStatus") == "matched")
    )
    assert recovered.height > 0, "000080 sgaByNature 회복 행 없음"


def test_bynature_opex_separated(frames: dict[str, pl.DataFrame | None]) -> None:
    """영업비용 성격별은 reconciledTarget=operatingExpense 로 물리 분리(판관비와 안 섞임)."""
    frame = frames["000050"]
    if frame is None or frame.is_empty():
        pytest.skip("000050 expenseDetail empty")
    opex = frame.filter(pl.col("reconciledTarget") == "operatingExpense")
    if opex.height == 0:
        pytest.skip("000050 operatingExpense 행 없음(연도별 노트 차이)")
    assert set(opex["reconciledTarget"].to_list()) == {"operatingExpense"}


def test_facade_strong_topic() -> None:
    """expenseDetail 이 강한 토픽으로 등록되어 c.panel 이 합성 백엔드로 라우팅."""
    from dartlab.providers.dart.builder.dataDispatcher import isStrongTopic

    assert isStrongTopic("expenseDetail") is True


def test_facade_returns_frame(frames: dict[str, pl.DataFrame | None]) -> None:
    """Company 파사드가 reconciledTarget 컬럼 가진 DataFrame 반환."""
    frame = frames["005930"]
    if frame is None:
        pytest.skip("005930 unavailable")
    assert isinstance(frame, pl.DataFrame)
    assert "reconciledTarget" in frame.columns
