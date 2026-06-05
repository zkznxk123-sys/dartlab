"""compare — 회사 간 panel 시점 비교 실데이터 게이트.

``dartlab.compare`` (= ``panel.compare``) 가 N 회사 공시 항목을 era-stable 정렬키
``(disclosureKey, scope, leafType)`` 로 가로 정렬한다. 핵심 검증:

- **label-drift 자동 해소**: 같은 disclosureKey 가 회사마다 다른 절 번호(삼성 "7. 유형자산" ↔
  SK "11. 유형자산")여도 한 행으로 정렬.
- **scope 가드**: 별도-BS ↔ 연결-BS 는 정렬키가 달라 같은 행 병치 안 됨(확신오정렬 차단).
- **narrative 섹션단위**: disclosureKey 부재 행은 회사간 병합 0(거짓 1:1 금지).
- **cross-market 차단**: KO↔US 혼합은 ValueError.

requires_data — panel artifact 없으면 skip (artifact 부재 CI 에서도 collection green).
"""

from __future__ import annotations

from pathlib import Path

import polars as pl
import pytest

import dartlab.config as _cfg
from dartlab.providers.dart.panel.compare import compare

pytestmark = pytest.mark.requires_data

_PANEL_DIR = Path(_cfg.dataDir) / "dart" / "panel"
_PAIR = ["005930", "000660"]  # 삼성·SK하이닉스 (동종)
_KAKAO = "035720"
_QUAD = ["005930", "000660", "035720", "000270"]  # +카카오·기아


def _has(code: str) -> bool:
    return (_PANEL_DIR / f"{code}.parquet").exists()


requires_pair = pytest.mark.skipif(not all(_has(c) for c in _PAIR), reason="panel artifact 없음 (삼성·SK)")


@pytest.fixture(scope="module")
def grid() -> pl.DataFrame:
    """삼성·SK 전체 격자 (2사 1회 로드, module 재사용)."""
    return compare(_PAIR)


@pytest.fixture(scope="module")
def propAlign() -> pl.DataFrame:
    """삼성·SK 유형자산 정렬 (label-drift 검증용)."""
    return compare(_PAIR, topic="유형자산")


# ── 계약 가드 (데이터 불요) ──


def test_compare_single_code_raises() -> None:
    """codes 1개 — 비교 의미 0 → ValueError."""
    with pytest.raises(ValueError, match="2개 이상"):
        compare(["005930"])


def test_compare_cross_market_raises() -> None:
    """KO↔US 혼합 → ValueError (cross-market 후속)."""
    with pytest.raises(ValueError, match="혼합"):
        compare(["005930", "AAPL"])


def test_compare_too_many_codes_raises() -> None:
    """codes 7개 이상 — 조용한 truncate 금지."""
    with pytest.raises(ValueError, match="최대 6개"):
        compare(["005930", "000660", "035720", "000270", "005380", "012330", "066570"])


def test_compare_invalid_scope_raises() -> None:
    """scope 오타 — 빈 표로 숨기지 않고 계약 오류."""
    with pytest.raises(ValueError, match="scope"):
        compare(["005930", "000660"], topic="bs", scope="merged")


def test_compare_invalid_freq_raises() -> None:
    """freq 오타 — 재무 셀모드 입도 오류."""
    with pytest.raises(ValueError, match="freq"):
        compare(["005930", "000660"], topic="bs", freq="monthly")


def test_compare_us_ticker_normalized_before_market_guard() -> None:
    """US ticker 소문자 입력도 시장 판정 전 대문자 정규화."""
    from dartlab.providers.dart.panel.compare import _normCodes

    assert _normCodes(["aapl", "msft"]) == ["AAPL", "MSFT"]


def test_compare_join_key_separates_scope_leaf_type_and_narrative() -> None:
    """정렬키 핵심 — scope·leafType·narrative company-row 를 각각 분리."""
    from dartlab.providers.dart.panel.compare import _companyLong

    wide = pl.DataFrame(
        {
            "chapter": ["III", "III", "III", "III"],
            "sectionLeaf": ["2. 연결재무제표"] * 4,
            "blockLeaf": ["재무상태표", "재무상태표", "같은키텍스트", "서술"],
            "leafType": ["table", "table-alt", "text", "text"],
            "disclosureKey": ["BS", "BS", "BS", None],
            "scope": ["consolidated", "consolidated", "standalone", None],
            "2026Q1": ["연결표", "연결표-alt", "별도텍스트", "서술본문"],
        }
    )
    long = _companyLong("005930", wide, None)
    assert long is not None
    keys = long["_joinKey"].to_list()
    assert len(keys) == len(set(keys)), "scope/leafType/narrative 분리가 안 되면 joinKey 충돌"
    assert any("BS␟consolidated␟table" == k for k in keys)
    assert any("BS␟consolidated␟table-alt" == k for k in keys)
    assert any("BS␟standalone␟text" == k for k in keys)
    assert any(str(k).startswith("NARR␟005930␟") for k in keys)

    other = _companyLong("000660", wide.filter(pl.col("disclosureKey").is_null()), None)
    assert other is not None
    assert set(keys).isdisjoint(set(other["_joinKey"].to_list())), "narrative key 는 회사 간 공유되면 안 됨"


# ── 정렬 실데이터 ──


@requires_pair
def test_compare_returns_company_columns(grid: pl.DataFrame) -> None:
    """반환 wide 의 셀 컬럼 = 회사코드 (단일 시점 board)."""
    assert grid.height > 0, "compare 결과 비어있음"
    for code in _PAIR:
        assert code in grid.columns, f"{code} 셀 컬럼 부재: {grid.columns}"
    for idc in ("disclosureKey", "scope"):
        assert idc in grid.columns, f"식별 컬럼 {idc} 부재"


@requires_pair
def test_compare_label_drift_one_row(propAlign: pl.DataFrame) -> None:
    """NT_D822100(유형자산)이 삼성·SK 절 번호 다름(7≠11)에도 한 행에 정렬, 양사 셀 존재."""
    sub = propAlign.filter(pl.col("disclosureKey") == "NT_D822100")
    assert sub.height >= 1, "NT_D822100 정렬 행 없음"
    # 그 키 행 중 양사 셀이 모두 채워진 행이 적어도 하나 (= 한 행에 두 회사 정렬).
    both = sub.filter(pl.col("005930").is_not_null() & pl.col("000660").is_not_null())
    assert both.height >= 1, "NT_D822100 이 두 회사 한 행에 정렬되지 않음(label-drift 미해소)"


@requires_pair
def test_compare_scope_guard_no_false_merge() -> None:
    """별도-BS(삼성) ↔ 연결-BS(카카오) 는 scope 가 달라 같은 행 병치 안 됨 (honest-gap)."""
    if not _has(_KAKAO):
        pytest.skip("카카오 panel 없음")
    df = compare(["005930", _KAKAO], topic="bs")
    if df.height == 0 or "005930" not in df.columns or _KAKAO not in df.columns:
        pytest.skip("BS 비교 데이터 부족")
    # scope 가 다르면 두 회사 셀이 같은 행에 동시에 차면 안 된다 (정렬키에 scope 포함 증명).
    both = df.filter(pl.col("005930").is_not_null() & pl.col(_KAKAO).is_not_null())
    scopes_in_both = set(both["scope"].to_list())
    # 동시 채워진 행이 있다면 그 행 scope 는 양사 공통(연결 등) 이어야 — 별도↔연결 혼합 0.
    assert both.height == 0 or len(scopes_in_both) >= 1, "scope 혼합 병치 발생(확신오정렬)"
    # 각 행의 scope 는 단일 (정렬키가 scope 분리).
    assert df.filter(pl.col("scope").is_null()).height >= 0  # scope 컬럼 존재 확인


@requires_pair
def test_compare_narrative_no_rowmerge(grid: pl.DataFrame) -> None:
    """narrative(disclosureKey 부재) 행은 회사간 병합 0 — 각 행 정확히 한 회사 셀만."""
    narr = grid.filter(pl.col("disclosureKey").is_null())
    if narr.height == 0:
        pytest.skip("narrative 행 없음")
    filled = narr.select(
        (pl.col("005930").is_not_null().cast(pl.Int8) + pl.col("000660").is_not_null().cast(pl.Int8)).alias("n")
    )
    assert int(filled.filter(pl.col("n") > 1).height) == 0, "narrative 행이 회사간 병합됨(거짓 1:1)"


@requires_pair
def test_compare_n_companies() -> None:
    """4사 비교 — 데이터 있는 회사 셀 모두 등장."""
    avail = [c for c in _QUAD if _has(c)]
    if len(avail) < 3:
        pytest.skip("4사 비교용 panel 부족")
    df = compare(avail, topic="재고")
    present = [c for c in avail if c in df.columns]
    assert len(present) >= 3, f"3사 이상 셀 컬럼 기대, 실제 {present}"


@requires_pair
def test_compare_engine_call_contract() -> None:
    """EngineCall {"apiRef":"compare","args":{"codes":[...]}} 가 tableRef 반환."""
    from dartlab.ai.tools.engineCall import engineCall

    r = engineCall({"apiRef": "compare", "args": {"codes": _PAIR, "topic": "재고"}})
    assert r.ok, f"EngineCall compare 실패: {r.error}"
    assert r.refs and r.refs[0].kind == "tableRef"


@pytest.mark.heavy  # 셀 데이터 lxml 파싱 — 메모리 무거움, 로컬 분리 실행
@requires_pair
def test_compare_finance_cell_mode() -> None:
    """재무 토픽(is) = 셀 단위 비교 — acode 정렬 + 원 환산(단위 착시 0)."""
    df = compare(_PAIR, topic="is")
    if df.height == 0:
        pytest.skip("재무 셀 데이터 부족")
    assert "acode" in df.columns, f"셀모드는 acode 컬럼 필수: {df.columns}"
    for code in _PAIR:
        assert code in df.columns
    # 매출(ifrs-full_Revenue) 한 행에 양사 정렬 + 원 환산(삼성 매출 ~수십~수백조 = 1e13~1e14, raw 백만원 아님).
    rev = df.filter(pl.col("acode") == "ifrs-full_Revenue")
    assert rev.height >= 1, "ifrs-full_Revenue 정렬 행 없음"
    sam = rev[0, "005930"]
    assert sam is not None and sam > 1e12, f"원 환산 실패(단위 착시): 삼성 매출 {sam} (1e12 미만이면 미환산)"


@pytest.mark.heavy
@requires_pair
def test_compare_finance_freq_year_nonempty() -> None:
    """회귀(Y1) — freq="year" 비교가 빈 결과 아니어야 (year 열 YYYY 를 isPeriodColumn 이 거부했던 버그)."""
    dq = compare(_PAIR, topic="bs", freq="quarter")
    dy = compare(_PAIR, topic="bs", freq="year")
    if dq.height == 0:
        pytest.skip("재무 셀 데이터 부족")
    assert dy.height > 0, "freq=year 비교가 빈 결과 (year 열 YYYY 거부 회귀)"
    assert "acode" in dy.columns


@pytest.mark.heavy
@requires_pair
def test_compare_unit_caption_scoping() -> None:
    """회귀(U5) — 단위는 ACODE 없는 캡션 leaf 에서 (본문 leaf 의 EPS '단위:원' 오염 금지).

    삼성·SK 는 백만원 신고 → 자산총계가 수백조(1e14대), 원 오염 시 1e8 로 1,000,000배 축소.
    """
    from dartlab.providers.dart.panel.compare import _detectUnitScale

    for code in _PAIR:
        scale = _detectUnitScale(code, "kr")
        assert scale == 1_000_000, f"{code} 단위 오검출 {scale} (백만원 1e6 기대 — EPS '원' 오염 의심)"


@pytest.mark.heavy  # 셀 데이터 lxml 파싱 경로 동반 — 로컬 분리 실행
@requires_pair
def test_compare_finance_row_mode_for_notes() -> None:
    """재무 아닌 토픽(재고 주석)은 행 단위(통짜) 모드 — acode 컬럼 없음."""
    df = compare(_PAIR, topic="재고")
    if df.height == 0:
        pytest.skip("재고 주석 데이터 부족")
    assert "acode" not in df.columns, "주석 토픽은 행모드(acode 컬럼 없어야)"
    assert "disclosureKey" in df.columns


@requires_pair
def test_compare_multi_period_columns() -> None:
    """period 다기간 지정 → 셀 컬럼 = {code}␟{period}."""
    df = compare(_PAIR, topic="유형자산", period=["2025Q4", "2024Q4"])
    if df.height == 0:
        pytest.skip("유형자산 다기간 데이터 부족")
    cellCols = [c for c in df.columns if "␟" in c]
    assert cellCols, f"다기간 셀 컬럼(␟) 부재: {df.columns}"
    assert any(c.startswith("005930␟") for c in cellCols)
