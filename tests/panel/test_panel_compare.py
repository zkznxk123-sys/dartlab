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
from dartlab.providers.dart.panel.compare import compare, compareDiagnostics

_PANEL_DIR = Path(_cfg.dataDir) / "dart" / "panel"
_PAIR = ["005930", "000660"]  # 삼성·SK하이닉스 (동종)
_QUAD = ["005930", "000660", "035720", "000270"]  # +카카오·기아


def _has(code: str) -> bool:
    return (_PANEL_DIR / f"{code}.parquet").exists()


_requiresPairData = pytest.mark.skipif(not all(_has(c) for c in _PAIR), reason="panel artifact 없음 (삼성·SK)")


def requires_pair(fn):
    """실데이터 삼성·SK panel 이 필요한 테스트만 requires_data 로 분리한다."""
    return pytest.mark.requires_data(_requiresPairData(fn))


@pytest.fixture(scope="module")
def grid() -> pl.DataFrame:
    """삼성·SK 전체 격자 (2사 1회 로드, module 재사용)."""
    return compare(_PAIR)


@pytest.fixture(scope="module")
def propAlign() -> pl.DataFrame:
    """삼성·SK 유형자산 정렬 (label-drift 검증용)."""
    return compare(_PAIR, topic="유형자산")


# ── 계약 가드 (데이터 불요) ──


def test_compare_public_surface_callable() -> None:
    """공식 표면 dartlab.compare 는 provider compare 와 같은 함수다."""
    import dartlab
    from dartlab.providers.dart.panel import compare as panelCompare

    assert "compare" in dartlab.__all__
    assert dartlab.compare is panelCompare
    assert callable(dartlab.compare)


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


def test_compare_duplicate_codes_raises() -> None:
    """중복 code 는 조용히 dedup 하지 않는다 — 비교 대상 수를 사용자가 명시해야 한다."""
    with pytest.raises(ValueError, match="중복"):
        compare(["005930", "000660", "005930"])


def test_compare_invalid_scope_raises() -> None:
    """scope 오타 — 빈 표로 숨기지 않고 계약 오류."""
    with pytest.raises(ValueError, match="scope"):
        compare(["005930", "000660"], topic="bs", scope="merged")


def test_compare_invalid_freq_raises() -> None:
    """freq 오타 — 재무 셀모드 입도 오류."""
    with pytest.raises(ValueError, match="freq"):
        compare(["005930", "000660"], topic="bs", freq="monthly")


def test_compare_invalid_code_raises_and_diagnostics_payload() -> None:
    """compare 는 회사명이 아니라 KR 6자리 코드 또는 US ticker 만 받는다."""
    with pytest.raises(ValueError, match="6자리"):
        compare(["삼성전자", "000660"])

    diag = compareDiagnostics(["삼성전자", "000660"])
    assert diag["ok"] is False
    assert diag["reason"] == "invalidInput"
    assert diag["emptyReason"] == "invalidInput"
    assert "6자리" in str(diag["error"])


def test_compare_invalid_period_raises() -> None:
    """period 오타 — 빈 표로 숨기지 않고 계약 오류."""
    with pytest.raises(ValueError, match="period"):
        compare(["005930", "000660"], period="2025Q5")


def test_compare_empty_period_list_raises() -> None:
    """period=[] 는 '비교 시점 없음' 이라 빈 결과가 아니라 입력 오류다."""
    with pytest.raises(ValueError, match="period"):
        compare(["005930", "000660"], period=[])


def test_compare_us_finance_not_supported_yet() -> None:
    """US row compare 와 달리 finance cell compare 는 EDGAR adapter 확정 전 차단한다."""
    with pytest.raises(ValueError, match="US 재무 compare"):
        compare(["AAPL", "MSFT"], topic="bs")


def test_compare_us_ticker_normalized_before_market_guard() -> None:
    """US ticker 소문자 입력도 시장 판정 전 대문자 정규화."""
    from dartlab.providers.dart.panel.compare import _normCodes

    assert _normCodes(["aapl", "msft"]) == ["AAPL", "MSFT"]


def test_compare_diagnostics_invalid_input_returns_payload() -> None:
    """진단 표면은 입력 오류도 payload 로 설명한다."""
    diag = compareDiagnostics(["005930"])
    assert diag["ok"] is False
    assert diag["reason"] == "invalidInput"
    assert diag["emptyReason"] == "invalidInput"
    assert "2개 이상" in str(diag["error"])


def test_compare_diagnostics_normalizes_codes_before_error() -> None:
    """진단도 compare 와 같은 code 정규화·시장 가드를 쓴다."""
    diag = compareDiagnostics(["005930", "aapl"])
    assert diag["ok"] is False
    assert diag["reason"] == "invalidInput"
    assert diag["codes"] == ["005930", "AAPL"]
    assert "혼합" in str(diag["error"])


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


def test_compare_row_scope_mismatch_stays_separate(monkeypatch: pytest.MonkeyPatch) -> None:
    """같은 disclosureKey·leafType 도 scope 가 다르면 같은 행에 병치하지 않는다."""
    import importlib

    cmp = importlib.import_module("dartlab.providers.dart.panel.compare")

    def fakeReadWide(code: str, *, marketNs: str, periods: list[str] | None, tag: bool) -> pl.DataFrame:
        scope = "consolidated" if code == "111111" else "standalone"
        return pl.DataFrame(
            {
                "chapter": ["III"],
                "sectionLeaf": ["2. 재무제표"],
                "blockLeaf": ["재무상태표"],
                "leafType": ["table"],
                "disclosureKey": ["BS"],
                "scope": [scope],
                "2025Q4": [f"{scope}-{code}"],
            }
        )

    monkeypatch.setattr(cmp, "readWide", fakeReadWide)
    df = cmp.compare(["111111", "222222"], topic="재무상태")
    assert df.height == 2
    assert set(df["scope"].to_list()) == {"consolidated", "standalone"}
    both = df.filter(pl.col("111111").is_not_null() & pl.col("222222").is_not_null())
    assert both.height == 0


def test_compare_row_uses_latest_common_period_without_topic(monkeypatch: pytest.MonkeyPatch) -> None:
    """topic=None 에서 period 미지정이면 전체 panel 최신 공통 시점을 고른다."""
    import importlib

    cmp = importlib.import_module("dartlab.providers.dart.panel.compare")

    def fakeReadWide(code: str, *, marketNs: str, periods: list[str] | None, tag: bool) -> pl.DataFrame:
        if code == "111111":
            values = {"2026Q1": "new-only-1", "2025Q4": "common-1"}
        else:
            values = {"2026Q1": None, "2025Q4": "common-2"}
        return pl.DataFrame(
            {
                "chapter": ["III"],
                "sectionLeaf": ["2. 재무제표"],
                "blockLeaf": ["공통항목"],
                "leafType": ["table"],
                "disclosureKey": ["BS"],
                "scope": ["consolidated"],
                **values,
            }
        )

    monkeypatch.setattr(cmp, "readWide", fakeReadWide)
    df = cmp.compare(["111111", "222222"])
    assert df.columns[-2:] == ["111111", "222222"]
    assert df[0, "111111"] == "common-1"
    assert df[0, "222222"] == "common-2"

    diag = cmp.compareDiagnostics(["111111", "222222"])
    assert diag["resolvedPeriods"] == ["2025Q4"]
    assert diag["sharedRows"] == 1


def test_compare_row_falls_back_to_latest_union_when_no_common_period(monkeypatch: pytest.MonkeyPatch) -> None:
    """공통 시점이 없으면 최신 union 시점으로 honest-gap 을 보존한다."""
    import importlib

    cmp = importlib.import_module("dartlab.providers.dart.panel.compare")

    def fakeReadWide(code: str, *, marketNs: str, periods: list[str] | None, tag: bool) -> pl.DataFrame:
        if code == "111111":
            values = {"2026Q1": "latest-1", "2025Q4": None}
        else:
            values = {"2026Q1": None, "2025Q4": "old-2"}
        return pl.DataFrame(
            {
                "chapter": ["III"],
                "sectionLeaf": ["2. 재무제표"],
                "blockLeaf": ["공통항목"],
                "leafType": ["table"],
                "disclosureKey": ["BS"],
                "scope": ["consolidated"],
                **values,
            }
        )

    monkeypatch.setattr(cmp, "readWide", fakeReadWide)
    df = cmp.compare(["111111", "222222"])
    assert df.columns[-2:] == ["111111", "222222"]
    assert df[0, "111111"] == "latest-1"
    assert df[0, "222222"] is None

    diag = cmp.compareDiagnostics(["111111", "222222"])
    assert diag["resolvedPeriods"] == ["2026Q1"]
    assert diag["soloRows"] == 1
    assert diag["missingCodes"] == ["222222"]


def test_compare_diagnostics_counts_shared_partial_solo(monkeypatch: pytest.MonkeyPatch) -> None:
    """3사 diagnostics 는 shared/partial/solo row 를 구분한다."""
    import importlib

    cmp = importlib.import_module("dartlab.providers.dart.panel.compare")

    def fakeReadWide(code: str, *, marketNs: str, periods: list[str] | None, tag: bool) -> pl.DataFrame:
        valuesByCode = {
            "111111": ["shared-1", "partial-1", "solo-1"],
            "222222": ["shared-2", "partial-2", None],
            "333333": ["shared-3", None, None],
        }
        return pl.DataFrame(
            {
                "chapter": ["III", "III", "III"],
                "sectionLeaf": ["2. 재무제표", "3. 주석", "4. 기타"],
                "blockLeaf": ["공통", "부분", "단독"],
                "leafType": ["table", "table", "table"],
                "disclosureKey": ["ROW_SHARED", "ROW_PARTIAL", "ROW_SOLO"],
                "scope": ["consolidated", "consolidated", "consolidated"],
                "2025Q4": valuesByCode[code],
            }
        )

    monkeypatch.setattr(cmp, "readWide", fakeReadWide)
    diag = cmp.compareDiagnostics(["111111", "222222", "333333"], period="2025Q4")
    assert diag["rowCount"] == 3
    assert diag["sharedRows"] == 1
    assert diag["partialRows"] == 1
    assert diag["soloRows"] == 1
    assert diag["presentCodes"] == ["111111", "222222", "333333"]
    assert diag["missingCodes"] == []


def test_compare_topic_selects_period_after_topic_filter(monkeypatch: pytest.MonkeyPatch) -> None:
    """topic 지정 시 전체 최신분기가 아니라 topic 내부 최신분기를 고른다."""
    import importlib

    cmp = importlib.import_module("dartlab.providers.dart.panel.compare")

    def fakeReadWide(code: str, *, marketNs: str, periods: list[str] | None, tag: bool) -> pl.DataFrame:
        assert marketNs == "kr"
        assert periods is None
        assert tag is False
        suffix = code[-1]
        return pl.DataFrame(
            {
                "chapter": ["III", "III"],
                "sectionLeaf": ["2. 연결재무제표", "3. 주석"],
                "blockLeaf": ["최신항목", "재고자산"],
                "leafType": ["table", "table"],
                "disclosureKey": ["BS", "NT_INV"],
                "scope": ["consolidated", "consolidated"],
                "2026Q1": [f"latest-{suffix}", None],
                "2025Q4": [f"old-bs-{suffix}", f"inventory-{suffix}"],
            }
        )

    monkeypatch.setattr(cmp, "readWide", fakeReadWide)
    df = cmp.compare(["111111", "222222"], topic="재고")
    assert df.height == 1
    assert df[0, "disclosureKey"] == "NT_INV"
    assert df[0, "111111"] == "inventory-1"
    assert df[0, "222222"] == "inventory-2"

    diag = cmp.compareDiagnostics(["111111", "222222"], topic="재고")
    assert diag["resolvedPeriods"] == ["2025Q4"]


def test_compare_topic_keeps_missing_company_as_null(monkeypatch: pytest.MonkeyPatch) -> None:
    """topic 이 한 회사에만 있어도 비교 대상 회사 컬럼은 null 로 남긴다."""
    import importlib

    cmp = importlib.import_module("dartlab.providers.dart.panel.compare")

    def fakeReadWide(code: str, *, marketNs: str, periods: list[str] | None, tag: bool) -> pl.DataFrame:
        if code == "111111":
            rows = {
                "blockLeaf": ["재고자산", "최신항목"],
                "disclosureKey": ["NT_INV", "BS"],
                "2026Q1": [None, "latest-1"],
                "2025Q4": ["inventory-1", "old-bs-1"],
            }
        else:
            rows = {
                "blockLeaf": ["매출채권", "최신항목"],
                "disclosureKey": ["NT_AR", "BS"],
                "2026Q1": [None, "latest-2"],
                "2025Q4": ["receivable-2", "old-bs-2"],
            }
        return pl.DataFrame(
            {
                "chapter": ["III", "III"],
                "sectionLeaf": ["3. 주석", "2. 연결재무제표"],
                "leafType": ["table", "table"],
                "scope": ["consolidated", "consolidated"],
                **rows,
            }
        )

    monkeypatch.setattr(cmp, "readWide", fakeReadWide)
    df = cmp.compare(["111111", "222222"], topic="재고")
    assert df.columns[-2:] == ["111111", "222222"]
    assert df.height == 1
    assert df[0, "111111"] == "inventory-1"
    assert df[0, "222222"] is None

    diag = cmp.compareDiagnostics(["111111", "222222"], topic="재고")
    assert diag["resolvedPeriods"] == ["2025Q4"]
    assert diag["presentCodes"] == ["111111"]
    assert diag["missingCodes"] == ["222222"]
    assert diag["soloRows"] == 1


def test_compare_row_keeps_missing_panel_company_as_null(monkeypatch: pytest.MonkeyPatch) -> None:
    """한 회사 panel 이 없어도 읽힌 회사 row 와 누락 회사 null 컬럼을 보존한다."""
    import importlib

    cmp = importlib.import_module("dartlab.providers.dart.panel.compare")

    def fakeReadWide(code: str, *, marketNs: str, periods: list[str] | None, tag: bool) -> pl.DataFrame | None:
        if code == "222222":
            return None
        return pl.DataFrame(
            {
                "chapter": ["III"],
                "sectionLeaf": ["3. 주석"],
                "blockLeaf": ["재고자산"],
                "leafType": ["table"],
                "disclosureKey": ["NT_INV"],
                "scope": ["consolidated"],
                "2025Q4": ["inventory-1"],
            }
        )

    monkeypatch.setattr(cmp, "readWide", fakeReadWide)
    df = cmp.compare(["111111", "222222"], topic="재고")
    assert df.columns[-2:] == ["111111", "222222"]
    assert df.height == 1
    assert df[0, "111111"] == "inventory-1"
    assert df[0, "222222"] is None

    diag = cmp.compareDiagnostics(["111111", "222222"], topic="재고")
    assert diag["resolvedPeriods"] == ["2025Q4"]
    assert diag["presentCodes"] == ["111111"]
    assert diag["missingCodes"] == ["222222"]
    assert diag["soloRows"] == 1


def test_compare_finance_uses_latest_common_period(monkeypatch: pytest.MonkeyPatch) -> None:
    """재무 셀모드 period=None 은 회사별 최신값이 아니라 최신 공통 시점으로 맞춘다."""
    import importlib

    cmp = importlib.import_module("dartlab.providers.dart.panel.compare")

    def fakeCompanyCellsByPeriod(
        code: str,
        statement: str,
        freq: str,
        scope: str,
        marketNs: str,
        *,
        targetLabels: list[str] | None = None,
        panelPeriods: list[str] | None = None,
    ) -> dict[str, dict[str, tuple[str, float]]]:
        assert statement == "bs"
        assert freq == "quarter"
        assert scope == "consolidated"
        assert marketNs == "kr"
        assert targetLabels is None
        assert panelPeriods is None
        if code == "111111":
            return {
                "2026Q1": {"ifrs-full_Assets": ("자산총계", 260.0)},
                "2025Q4": {"ifrs-full_Assets": ("자산총계", 150.0)},
            }
        return {"2025Q4": {"ifrs-full_Assets": ("자산총계", 250.0)}}

    monkeypatch.setattr(cmp, "_companyCellsByPeriod", fakeCompanyCellsByPeriod)
    df = cmp.compare(["111111", "222222"], topic="bs")
    assert df.height == 1
    assert df[0, "111111"] == 150.0
    assert df[0, "222222"] == 250.0

    diag = cmp.compareDiagnostics(["111111", "222222"], topic="bs")
    assert diag["resolvedPeriods"] == ["2025Q4"]
    assert diag["scope"] == "consolidated"


def test_compare_diagnostics_finance_reads_cells_once_per_code(monkeypatch: pytest.MonkeyPatch) -> None:
    """finance diagnostics 는 표와 resolved period 계산 때문에 셀을 중복 로드하지 않는다."""
    import importlib

    cmp = importlib.import_module("dartlab.providers.dart.panel.compare")
    calls: list[str] = []

    def fakeCompanyCellsByPeriod(
        code: str,
        statement: str,
        freq: str,
        scope: str,
        marketNs: str,
        *,
        targetLabels: list[str] | None = None,
        panelPeriods: list[str] | None = None,
    ) -> dict[str, dict[str, tuple[str, float]]]:
        calls.append(code)
        return {"2025Q4": {"ifrs-full_Assets": ("자산총계", 10.0 if code == "111111" else 20.0)}}

    monkeypatch.setattr(cmp, "_companyCellsByPeriod", fakeCompanyCellsByPeriod)
    diag = cmp.compareDiagnostics(["111111", "222222"], topic="bs")
    assert diag["ok"] is True
    assert diag["resolvedPeriods"] == ["2025Q4"]
    assert calls == ["111111", "222222"]


def test_compare_finance_respects_explicit_period_and_multiperiod(monkeypatch: pytest.MonkeyPatch) -> None:
    """재무 셀모드도 명시 period/list period 계약을 따른다."""
    import importlib

    cmp = importlib.import_module("dartlab.providers.dart.panel.compare")
    seen: list[tuple[list[str] | None, list[str] | None]] = []

    def fakeCompanyCellsByPeriod(
        code: str,
        statement: str,
        freq: str,
        scope: str,
        marketNs: str,
        *,
        targetLabels: list[str] | None = None,
        panelPeriods: list[str] | None = None,
    ) -> dict[str, dict[str, tuple[str, float]]]:
        seen.append((targetLabels, panelPeriods))
        if code == "111111":
            return {
                "2026Q1": {"ifrs-full_Assets": ("자산총계", 260.0)},
                "2025Q4": {"ifrs-full_Assets": ("자산총계", 150.0)},
            }
        return {"2025Q4": {"ifrs-full_Assets": ("자산총계", 250.0)}}

    monkeypatch.setattr(cmp, "_companyCellsByPeriod", fakeCompanyCellsByPeriod)

    one = cmp.compare(["111111", "222222"], topic="bs", period="2025Q4")
    assert seen[-2:] == [(["2025Q4"], ["2025Q4"]), (["2025Q4"], ["2025Q4"])]
    assert one.columns[-2:] == ["111111", "222222"]
    assert one[0, "111111"] == 150.0
    assert one[0, "222222"] == 250.0

    many = cmp.compare(["111111", "222222"], topic="bs", period=["2025Q4", "2026Q1"])
    assert seen[-2:] == [(["2026Q1", "2025Q4"], ["2026Q1", "2025Q4"])] * 2
    assert many.columns[-4:] == ["111111␟2026Q1", "111111␟2025Q4", "222222␟2026Q1", "222222␟2025Q4"]
    assert many[0, "111111␟2026Q1"] == 260.0
    assert many[0, "111111␟2025Q4"] == 150.0
    assert many[0, "222222␟2026Q1"] is None
    assert many[0, "222222␟2025Q4"] == 250.0

    diag = cmp.compareDiagnostics(["111111", "222222"], topic="bs", period=["2025Q4", "2026Q1"])
    assert diag["resolvedPeriods"] == ["2026Q1", "2025Q4"]


def test_compare_finance_year_period_normalizes_label(monkeypatch: pytest.MonkeyPatch) -> None:
    """freq=year 에서 명시 분기 period 는 출력 label=YYYY, panel prune=YYYYQn 으로 분리한다."""
    import importlib

    cmp = importlib.import_module("dartlab.providers.dart.panel.compare")
    seen: list[tuple[list[str] | None, list[str] | None, str]] = []

    def fakeCompanyCellsByPeriod(
        code: str,
        statement: str,
        freq: str,
        scope: str,
        marketNs: str,
        *,
        targetLabels: list[str] | None = None,
        panelPeriods: list[str] | None = None,
    ) -> dict[str, dict[str, tuple[str, float]]]:
        seen.append((targetLabels, panelPeriods, scope))
        return {"2025": {"ifrs-full_Assets": ("자산총계", 10.0 if code == "111111" else 20.0)}}

    monkeypatch.setattr(cmp, "_companyCellsByPeriod", fakeCompanyCellsByPeriod)
    df = cmp.compare(["111111", "222222"], topic="bs", period="2025Q4", freq="year")
    assert seen[-2:] == [(["2025"], ["2025Q4"], "consolidated")] * 2
    assert df.columns[-2:] == ["111111", "222222"]
    assert df[0, "111111"] == 10.0
    assert df[0, "222222"] == 20.0

    diag = cmp.compareDiagnostics(["111111", "222222"], topic="bs", period="2025Q4", freq="year")
    assert diag["period"] == ["2025Q4"]
    assert diag["resolvedPeriods"] == ["2025"]
    assert diag["scope"] == "consolidated"


def test_compare_finance_keeps_missing_company_as_null(monkeypatch: pytest.MonkeyPatch) -> None:
    """재무 셀모드도 한 회사 결손을 표 전멸로 만들지 않고 null 회사 컬럼으로 보존한다."""
    import importlib

    cmp = importlib.import_module("dartlab.providers.dart.panel.compare")

    def fakeCompanyCellsByPeriod(
        code: str,
        statement: str,
        freq: str,
        scope: str,
        marketNs: str,
        *,
        targetLabels: list[str] | None = None,
        panelPeriods: list[str] | None = None,
    ) -> dict[str, dict[str, tuple[str, float]]]:
        if code == "111111":
            return {"2025Q4": {"ifrs-full_Assets": ("자산총계", 150.0)}}
        return {}

    monkeypatch.setattr(cmp, "_companyCellsByPeriod", fakeCompanyCellsByPeriod)
    df = cmp.compare(["111111", "222222"], topic="bs", period="2025Q4")
    assert df.columns[-2:] == ["111111", "222222"]
    assert df[0, "111111"] == 150.0
    assert df[0, "222222"] is None

    diag = cmp.compareDiagnostics(["111111", "222222"], topic="bs", period="2025Q4")
    assert diag["resolvedPeriods"] == ["2025Q4"]
    assert diag["presentCodes"] == ["111111"]
    assert diag["missingCodes"] == ["222222"]
    assert diag["soloRows"] == 1


def test_compare_finance_scales_each_period_independently(monkeypatch: pytest.MonkeyPatch) -> None:
    """재무 셀모드는 최신 단위 하나가 아니라 각 period 캡션 단위로 원 환산한다."""
    import importlib

    cmp = importlib.import_module("dartlab.providers.dart.panel.compare")
    cell = importlib.import_module("dartlab.providers.dart.panel.cell")

    monkeypatch.setattr(cmp, "_detectUnitScales", lambda code, marketNs: {"2026Q1": 1_000, "2025Q4": 1})
    monkeypatch.setattr(cell, "_cellsFromPanel", lambda code, marketNs, periods: pl.DataFrame({"dummy": [1]}))
    monkeypatch.setattr(
        cell,
        "_cellWideFromCells",
        lambda cells, *, statement, freq, scope: pl.DataFrame(
            {
                "axisPath": [""],
                "acode": ["ifrs-full_Assets"],
                "label": ["자산총계"],
                "2026Q1": ["2"],
                "2025Q4": ["3"],
            }
        ),
    )

    per = cmp._companyCellsByPeriod("111111", "bs", "quarter", "consolidated", "kr")
    assert per["2026Q1"]["ifrs-full_Assets"][1] == 2_000
    assert per["2025Q4"]["ifrs-full_Assets"][1] == 3


def test_compare_unit_scale_ignores_older_period_caption(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """최신 재무표에 단위 캡션이 없으면 과거 period 의 '단위:원' 으로 오염되지 않는다."""
    import importlib

    cmp = importlib.import_module("dartlab.providers.dart.panel.compare")
    read = importlib.import_module("dartlab.providers.dart.panel.read")
    flat = tmp_path / "111111.parquet"
    flat.write_bytes(b"")

    monkeypatch.setattr(read, "ensurePanelFromHf", lambda code, marketNs: None)
    monkeypatch.setattr(read, "_panelDir", lambda code, marketNs: tmp_path / "periods")
    monkeypatch.setattr(
        cmp.pl,
        "read_parquet",
        lambda path, columns: pl.DataFrame(
            {
                "disclosureKey": ["BS", "BS"],
                "contentRaw": ["<TABLE><TR><TD>재무상태표</TD></TR></TABLE>", "<TABLE>단위 : 원</TABLE>"],
                "period": ["2026Q1", "2018Q4"],
            }
        ),
    )

    assert cmp._detectUnitScale("111111", "kr") == 1_000_000


def test_compare_unit_scale_can_scope_to_requested_period(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """단위 검출은 요청 period 를 주면 그 period 의 캡션만 사용한다."""
    import importlib

    cmp = importlib.import_module("dartlab.providers.dart.panel.compare")
    read = importlib.import_module("dartlab.providers.dart.panel.read")
    flat = tmp_path / "111111.parquet"
    flat.write_bytes(b"")

    monkeypatch.setattr(read, "ensurePanelFromHf", lambda code, marketNs: None)
    monkeypatch.setattr(read, "_panelDir", lambda code, marketNs: tmp_path / "periods")
    monkeypatch.setattr(
        cmp.pl,
        "read_parquet",
        lambda path, columns: pl.DataFrame(
            {
                "disclosureKey": ["BS", "BS"],
                "contentRaw": ["<TABLE>단위 : 천원</TABLE>", "<TABLE>단위 : 원</TABLE>"],
                "period": ["2026Q1", "2025Q4"],
            }
        ),
    )

    assert cmp._detectUnitScale("111111", "kr") == 1_000
    assert cmp._detectUnitScale("111111", "kr", period="2025Q4") == 1
    assert cmp._detectUnitScale("111111", "kr", period="2025") == 1


def test_compare_unit_scale_uses_latest_period_caption(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """최신 period 의 캡션은 그대로 신뢰한다."""
    import importlib

    cmp = importlib.import_module("dartlab.providers.dart.panel.compare")
    read = importlib.import_module("dartlab.providers.dart.panel.read")
    flat = tmp_path / "111111.parquet"
    flat.write_bytes(b"")

    monkeypatch.setattr(read, "ensurePanelFromHf", lambda code, marketNs: None)
    monkeypatch.setattr(read, "_panelDir", lambda code, marketNs: tmp_path / "periods")
    monkeypatch.setattr(
        cmp.pl,
        "read_parquet",
        lambda path, columns: pl.DataFrame(
            {
                "disclosureKey": ["BS", "BS"],
                "contentRaw": ["<TABLE>단위 : 천원</TABLE>", "<TABLE>단위 : 원</TABLE>"],
                "period": ["2026Q1", "2018Q4"],
            }
        ),
    )

    assert cmp._detectUnitScale("111111", "kr") == 1_000


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


@requires_pair
def test_compare_diagnostics_row_contract_matches_frame() -> None:
    """진단 payload 는 compare row 출력의 모드·행수·열·회사 존재를 설명한다."""
    df = compare(_PAIR, topic="재고")
    diag = compareDiagnostics(_PAIR, topic="재고")
    assert diag["mode"] == "row"
    assert diag["marketNs"] == "kr"
    assert diag["rowCount"] == df.height
    assert diag["columns"] == df.columns
    assert diag["cellColumns"] == [c for c in df.columns if c in _PAIR]
    if df.height == 0:
        assert diag["ok"] is False
        assert diag["emptyReason"] == "topicFilteredEmpty"
    else:
        assert diag["ok"] is True
        assert diag["reason"] == "ready"
        assert set(diag["presentCodes"]).issubset(set(_PAIR))
        assert diag["sharedRows"] + diag["partialRows"] + diag["soloRows"] <= df.height


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
