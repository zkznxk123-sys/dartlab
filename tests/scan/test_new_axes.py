"""5부 비재무 심화 3축 (지배구조/공시변화/비교분석) 단위 테스트."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional
from unittest.mock import MagicMock, patch

import pytest

# ── Mock 데이터 구조 ──


@dataclass
class MockMajorHolderResult:
    years: list[int]
    totalShareRatio: list[Optional[float]]
    latestHolders: list[dict]
    df: None = None


@dataclass
class MockExecutiveResult:
    df: None = None
    totalCount: int = 10
    registeredCount: int = 5
    outsideCount: int = 4


@dataclass
class MockAuditResult:
    years: list[int] = None
    opinions: list[Optional[str]] = None
    auditors: list[Optional[str]] = None
    df: None = None

    def __post_init__(self):
        if self.years is None:
            self.years = [2021, 2022, 2023, 2024]
        if self.opinions is None:
            self.opinions = ["적정의견", "적정의견", "적정의견", "적정의견"]
        if self.auditors is None:
            self.auditors = ["삼일", "삼일", "삼정", "삼정"]


@dataclass
class MockDiffSummary:
    topic: str
    chapter: str | None
    totalPeriods: int
    changedCount: int
    stableCount: int

    @property
    def changeRate(self) -> float:
        if self.totalPeriods <= 1:
            return 0.0
        return self.changedCount / (self.totalPeriods - 1)


@dataclass
class MockDiffEntry:
    topic: str
    chapter: str | None
    fromPeriod: str
    toPeriod: str
    status: str
    fromLen: int
    toLen: int


@dataclass
class MockDiffResult:
    entries: list = None
    summaries: list = None

    def __post_init__(self):
        if self.entries is None:
            self.entries = []
        if self.summaries is None:
            self.summaries = []

    @property
    def totalChanges(self) -> int:
        return len(self.entries)

    def topChanged(self, n: int = 10) -> list:
        return sorted(self.summaries, key=lambda s: s.changeRate, reverse=True)[:n]


# ── Fixtures ──


def _mockCompanyWithReport():
    """report 데이터가 있는 mock company."""
    company = MagicMock()
    company.stockCode = "005930"

    company._report.majorHolder = MockMajorHolderResult(
        years=[2021, 2022, 2023, 2024],
        totalShareRatio=[20.5, 20.3, 19.8, 19.5],
        latestHolders=[
            {"name": "이재용", "relate": "본인", "ratio": 17.5, "shares": 1000000},
            {"name": "국민연금", "relate": "기관", "ratio": 9.2, "shares": 500000},
        ],
    )

    company._report.executive = MockExecutiveResult(totalCount=10, registeredCount=5, outsideCount=4)

    company._report.audit = MockAuditResult()

    return company


def _mockCompanyWithDocs():
    """docs 데이터가 있는 mock company."""
    company = MagicMock()
    company.stockCode = "005930"
    company.topics = ["businessOverview", "riskFactors", "accountingPolicy"]

    summaries = [
        MockDiffSummary("businessOverview", "사업", 5, 3, 1),
        MockDiffSummary("riskFactors", "위험", 5, 4, 0),
        MockDiffSummary("accountingPolicy", "회계", 5, 1, 3),
        MockDiffSummary("otherTopic", "기타", 5, 0, 4),
    ]
    entries = [
        MockDiffEntry("businessOverview", "사업", "2022", "2023", "CHANGED", 1000, 1200),
        MockDiffEntry("businessOverview", "사업", "2023", "2024", "CHANGED", 1200, 1500),
        MockDiffEntry("riskFactors", "위험", "2021", "2022", "CHANGED", 500, 800),
        MockDiffEntry("riskFactors", "위험", "2022", "2023", "CHANGED", 800, 600),
        MockDiffEntry("riskFactors", "위험", "2023", "2024", "CHANGED", 600, 900),
    ]
    mockDiffResult = MockDiffResult(entries=entries, summaries=summaries)

    return company, mockDiffResult


# ── 지배구조 테스트 ──

pytestmark = pytest.mark.unit


class TestGovernance:
    def test_calcOwnershipTrend(self):
        from dartlab.analysis.financial.governance import calcOwnershipTrend

        company = _mockCompanyWithReport()
        result = calcOwnershipTrend(company)
        assert result is not None
        assert "history" in result
        assert len(result["history"]) == 4
        assert result["history"][-1]["ratio"] == 19.5
        assert result["latestHolders"][0]["name"] == "이재용"

    def test_calcBoardComposition(self):
        from dartlab.analysis.financial.governance import calcBoardComposition

        company = _mockCompanyWithReport()
        result = calcBoardComposition(company)
        assert result is not None
        assert result["totalCount"] == 10
        assert result["outsideCount"] == 4
        assert result["outsideRatio"] == 40.0

    def test_calcAuditOpinionTrend(self):
        from dartlab.analysis.financial.governance import calcAuditOpinionTrend

        company = _mockCompanyWithReport()
        result = calcAuditOpinionTrend(company)
        assert result is not None
        history = result["history"]
        assert len(history) == 4
        assert history[0]["opinion"] == "적정의견"
        # 2023: 삼일->삼정 변경
        assert history[2]["auditorChanged"] is True

    def test_calcGovernanceFlags_lowOwnership(self):
        from dartlab.analysis.financial.governance import calcGovernanceFlags

        company = _mockCompanyWithReport()
        # 19.5% < 20% -> 경영권 방어 취약
        flags = calcGovernanceFlags(company)
        assert any("경영권 방어 취약" in f for f, k in flags)

    def test_calcGovernanceFlags_goodBoard(self):
        from dartlab.analysis.financial.governance import calcGovernanceFlags

        company = _mockCompanyWithReport()
        flags = calcGovernanceFlags(company)
        # 40% 사외이사 -> 아직 50% 미만이므로 기회 플래그 없음
        assert not any("이사회 독립성 양호" in f for f, k in flags)

    def test_none_when_no_report(self):
        from dartlab.analysis.financial.governance import calcOwnershipTrend

        company = MagicMock()
        company._report.majorHolder = None
        result = calcOwnershipTrend(company)
        assert result is None


# ── 오너 집중도 테스트 ──


def _buildMajorHolderDf(rows: list[dict]):
    import polars as pl

    schema = {
        "year": pl.Int64,
        "quarterNum": pl.Int64,
        "nm": pl.Utf8,
        "relate": pl.Utf8,
        "trmend_posesn_stock_qota_rt": pl.Float64,
    }
    for r in rows:
        for col in schema:
            r.setdefault(col, None)
    return pl.DataFrame(rows, schema=schema)


class TestOwnerConcentration:
    def test_separates_top1_and_special_related(self):
        from dartlab.analysis.financial.governance import calcOwnerConcentration

        df = _buildMajorHolderDf(
            [
                {"year": 2024, "quarterNum": 2, "nm": "김회장", "relate": "본인", "trmend_posesn_stock_qota_rt": 8.5},
                {
                    "year": 2024,
                    "quarterNum": 2,
                    "nm": "김사장",
                    "relate": "특수관계인",
                    "trmend_posesn_stock_qota_rt": 12.0,
                },
                {
                    "year": 2024,
                    "quarterNum": 2,
                    "nm": "홀딩스",
                    "relate": "특수관계인",
                    "trmend_posesn_stock_qota_rt": 30.0,
                },
                {"year": 2024, "quarterNum": 2, "nm": "계", "relate": "-", "trmend_posesn_stock_qota_rt": 50.5},
                {"year": 2023, "quarterNum": 2, "nm": "김회장", "relate": "본인", "trmend_posesn_stock_qota_rt": 8.0},
                {
                    "year": 2023,
                    "quarterNum": 2,
                    "nm": "김사장",
                    "relate": "특수관계인",
                    "trmend_posesn_stock_qota_rt": 12.0,
                },
            ]
        )
        result_obj = MockMajorHolderResult(
            years=[2023, 2024],
            totalShareRatio=[20.0, 50.5],
            latestHolders=[],
        )
        result_obj.df = df

        company = MagicMock()
        company._cache = {}
        company._report.majorHolder = result_obj
        out = calcOwnerConcentration(company)
        assert out is not None
        assert out["latest"]["year"] == 2024
        assert out["latest"]["top1Share"] == 8.5
        assert out["latest"]["specialRelatedSum"] == 42.0  # 12 + 30
        assert out["latest"]["topHolderRatio"] == 50.5
        assert out["latest"]["specialRelatedCount"] == 2

    def test_none_when_no_major_holder(self):
        from dartlab.analysis.financial.governance import calcOwnerConcentration

        company = MagicMock()
        company._cache = {}
        company._report.majorHolder = None
        assert calcOwnerConcentration(company) is None

    def test_governance_flags_include_dispersion(self):
        from dartlab.analysis.financial.governance import calcGovernanceFlags

        df = _buildMajorHolderDf(
            [
                {"year": 2024, "quarterNum": 2, "nm": "김회장", "relate": "본인", "trmend_posesn_stock_qota_rt": 5.0},
                {
                    "year": 2024,
                    "quarterNum": 2,
                    "nm": "홀딩스",
                    "relate": "특수관계인",
                    "trmend_posesn_stock_qota_rt": 40.0,
                },
            ]
        )
        mh = MockMajorHolderResult(
            years=[2024],
            totalShareRatio=[45.0],
            latestHolders=[{"name": "김회장", "relate": "본인", "ratio": 5.0, "shares": 100}],
        )
        mh.df = df

        company = MagicMock()
        company._cache = {}
        company._report.majorHolder = mh
        company._report.executive = MockExecutiveResult(totalCount=10, registeredCount=5, outsideCount=4)
        company._report.audit = MockAuditResult()
        with (
            patch("dartlab.analysis.financial.governance._loadSanction", return_value=None),
            patch("dartlab.analysis.financial.governance._loadContingentLiability", return_value=None),
            patch("dartlab.analysis.financial.governance._fetchLatestEquity", return_value=None),
        ):
            flags = calcGovernanceFlags(company)
        assert any("소유-지배 괴리" in msg for msg, _ in flags)


# ── 대표이사 교체 테스트 ──


@dataclass
class _MockExecutiveDocsResult:
    individualDf: object = None


def _buildIndividualDf(rows: list[dict]):
    import polars as pl

    schema = {
        "year": pl.Int64,
        "name": pl.Utf8,
        "gender": pl.Utf8,
        "position": pl.Utf8,
        "registrationType": pl.Utf8,
        "fullTime": pl.Utf8,
        "responsibility": pl.Utf8,
        "isCeo": pl.Boolean,
    }
    for r in rows:
        for col in schema:
            r.setdefault(col, None if col != "isCeo" else False)
    return pl.DataFrame(rows, schema=schema)


class TestCEOTurnover:
    def test_none_when_no_executive_docs(self):
        from dartlab.analysis.financial.governance import calcCEOTurnover

        company = MagicMock()
        company._cache = {}
        with patch(
            "dartlab.analysis.financial.governance._loadExecutiveDocs",
            return_value=None,
        ):
            assert calcCEOTurnover(company) is None

    def test_turnover_detection(self):
        from dartlab.analysis.financial.governance import calcCEOTurnover

        df = _buildIndividualDf(
            [
                {"year": 2021, "name": "김A", "isCeo": True},
                {"year": 2021, "name": "이B", "isCeo": True},
                {"year": 2022, "name": "김A", "isCeo": True},
                {"year": 2022, "name": "이B", "isCeo": True},
                {"year": 2023, "name": "김A", "isCeo": True},
                {"year": 2023, "name": "박C", "isCeo": True},  # 이B → 박C
                {"year": 2024, "name": "박C", "isCeo": True},  # 김A 퇴임
                {"year": 2025, "name": "박C", "isCeo": True},
                {"year": 2025, "name": "최D", "isCeo": True},  # 최D 합류
                # CEO 아닌 임원 섞어 — 무시되어야
                {"year": 2025, "name": "일반이사", "isCeo": False},
            ]
        )
        company = MagicMock()
        company._cache = {}
        with patch(
            "dartlab.analysis.financial.governance._loadExecutiveDocs",
            return_value=_MockExecutiveDocsResult(individualDf=df),
        ):
            r = calcCEOTurnover(company)

        assert r is not None
        assert r["windowYears"] == 5
        # 2022→2023: 1, 2023→2024: 1, 2024→2025: 1 → 총 3
        assert r["turnoverCount"] == 3
        assert r["lastChangeYear"] == 2025
        assert r["currentCeos"] == ["박C", "최D"]
        assert len(r["history"]) == 5
        assert r["avgTenureYears"] is not None

    def test_edgar_company_returns_none(self):
        from dartlab.analysis.financial.governance import calcCEOTurnover

        company = MagicMock()
        company._cache = {}
        company.currency = "USD"
        company.stockCode = "AAPL"
        assert calcCEOTurnover(company) is None

    def test_governance_flags_include_ceo_turnover(self):
        from dartlab.analysis.financial.governance import calcGovernanceFlags

        df = _buildIndividualDf(
            [
                {"year": 2023, "name": "A", "isCeo": True},
                {"year": 2024, "name": "B", "isCeo": True},
                {"year": 2025, "name": "C", "isCeo": True},
            ]
        )
        company = _mockCompanyWithReport()
        company._cache = {}
        with (
            patch(
                "dartlab.analysis.financial.governance._loadExecutiveDocs",
                return_value=_MockExecutiveDocsResult(individualDf=df),
            ),
            patch("dartlab.analysis.financial.governance._loadSanction", return_value=None),
            patch("dartlab.analysis.financial.governance._loadContingentLiability", return_value=None),
            patch("dartlab.analysis.financial.governance._loadRelatedPartyTx", return_value=None),
            patch("dartlab.analysis.financial.governance._fetchLatestEquity", return_value=None),
        ):
            flags = calcGovernanceFlags(company)
        assert any("대표이사 교체 2회" in msg for msg, _ in flags)


# ── 특수관계자 거래 집중도 테스트 ──


@dataclass
class _MockRelatedPartyResult:
    revenueTxDf: object = None
    guaranteeDf: object = None
    assetTxDf: object = None


def _buildRevenueTxDf(rows: list[dict]):
    import polars as pl

    schema = {
        "year": pl.Int64,
        "entity": pl.Utf8,
        "sales": pl.Int64,
        "purchases": pl.Int64,
    }
    for r in rows:
        for col in schema:
            r.setdefault(col, None)
    return pl.DataFrame(rows, schema=schema)


def _buildRptGuaranteeDf(rows: list[dict]):
    import polars as pl

    schema = {"year": pl.Int64, "entity": pl.Utf8, "amount": pl.Int64}
    for r in rows:
        for col in schema:
            r.setdefault(col, None)
    return pl.DataFrame(rows, schema=schema)


class TestRelatedPartyIntensity:
    def test_none_when_no_data(self):
        from dartlab.analysis.financial.governance import calcRelatedPartyIntensity

        company = MagicMock()
        company._cache = {}
        with patch(
            "dartlab.analysis.financial.governance._loadRelatedPartyTx",
            return_value=None,
        ):
            assert calcRelatedPartyIntensity(company) is None

    def test_ratios_and_trend(self):
        from dartlab.analysis.financial.governance import calcRelatedPartyIntensity

        # 백만원 단위: sales 100,000 = 1000억원. IS sales 1조원 → 10%
        revenueTx = _buildRevenueTxDf(
            [
                {"year": 2023, "entity": "자회사A", "sales": 100_000, "purchases": 10_000},
                {"year": 2024, "entity": "자회사A", "sales": 200_000, "purchases": 15_000},
                {"year": 2024, "entity": "자회사B", "sales": 50_000, "purchases": 5_000},
            ]
        )
        guaranteeDf = _buildRptGuaranteeDf([{"year": 2024, "entity": "자회사A", "amount": 200_000}])
        company = MagicMock()
        company._cache = {}
        # select/toDictBySnakeId mock — IS sales 시계열
        with (
            patch(
                "dartlab.analysis.financial.governance._loadRelatedPartyTx",
                return_value=_MockRelatedPartyResult(revenueTxDf=revenueTx, guaranteeDf=guaranteeDf),
            ),
            patch(
                "dartlab.analysis.financial.governance._fetchLatestEquity",
                return_value=500_000_000_000,  # 5000억원
            ),
            patch(
                "dartlab.analysis.financial.governance.toDictBySnakeId",
                return_value=(
                    {"sales": {"2023": 1_000_000_000_000, "2024": 2_500_000_000_000}},
                    ["2023", "2024"],
                ),
            ),
            patch(
                "dartlab.analysis.financial.governance.annualColsFromPeriods",
                return_value=["2023", "2024"],
            ),
        ):
            result = calcRelatedPartyIntensity(company)

        assert result is not None
        lt = result["latest"]
        assert lt["year"] == 2024
        assert lt["relatedSales"] == 250_000_000_000  # 250,000 백만 = 2500억
        assert lt["relatedPurchases"] == 20_000_000_000
        assert lt["relatedGuarantee"] == 200_000_000_000
        assert lt["totalRevenue"] == 2_500_000_000_000
        assert lt["relatedRevenueRatio"] == 10.0  # 2500억 / 2.5조 * 100
        assert lt["relatedGuaranteeRatio"] == 40.0  # 2000억 / 5000억
        # 추세: 2023년 1000억/1조 = 10%, 2024년 2500억/2.5조 = 10% → stable
        assert result["trend"] == "stable"

    def test_edgar_company_returns_none(self):
        from dartlab.analysis.financial.governance import calcRelatedPartyIntensity

        company = MagicMock()
        company._cache = {}
        company.currency = "USD"
        company.stockCode = "AAPL"
        assert calcRelatedPartyIntensity(company) is None

    def test_governance_flags_include_internal_sales(self):
        from dartlab.analysis.financial.governance import calcGovernanceFlags

        # relatedRevenueRatio 40% → warning
        revenueTx = _buildRevenueTxDf(
            [
                {"year": 2023, "entity": "자회사", "sales": 300_000, "purchases": 0},
                {"year": 2024, "entity": "자회사", "sales": 400_000, "purchases": 0},
            ]
        )
        company = _mockCompanyWithReport()
        company._cache = {}
        with (
            patch(
                "dartlab.analysis.financial.governance._loadRelatedPartyTx",
                return_value=_MockRelatedPartyResult(revenueTxDf=revenueTx, guaranteeDf=None),
            ),
            patch(
                "dartlab.analysis.financial.governance._fetchLatestEquity",
                return_value=None,
            ),
            patch(
                "dartlab.analysis.financial.governance.toDictBySnakeId",
                return_value=(
                    {"sales": {"2023": 1_000_000_000_000, "2024": 1_000_000_000_000}},
                    ["2023", "2024"],
                ),
            ),
            patch(
                "dartlab.analysis.financial.governance.annualColsFromPeriods",
                return_value=["2023", "2024"],
            ),
            patch("dartlab.analysis.financial.governance._loadSanction", return_value=None),
            patch("dartlab.analysis.financial.governance._loadContingentLiability", return_value=None),
        ):
            flags = calcGovernanceFlags(company)
        assert any("내부거래 의존" in msg for msg, _ in flags)


# ── 법적 이벤트 리스크 테스트 ──


@dataclass
class _MockSanctionResult:
    sanctionDf: object = None


@dataclass
class _MockContingentResult:
    guaranteeDf: object = None
    lawsuitDf: object = None


def _buildSanctionDf(rows: list[dict]):
    import polars as pl

    schema = {
        "year": pl.Int64,
        "date": pl.Utf8,
        "agency": pl.Utf8,
        "subject": pl.Utf8,
        "action": pl.Utf8,
        "amount": pl.Utf8,
        "amountValue": pl.Int64,
        "reason": pl.Utf8,
    }
    for r in rows:
        for col in schema:
            r.setdefault(col, None)
    return pl.DataFrame(rows, schema=schema)


def _buildGuaranteeDf(rows: list[dict]):
    import polars as pl

    schema = {"year": pl.Int64, "totalGuaranteeAmount": pl.Int64, "lineCount": pl.Int64}
    for r in rows:
        for col in schema:
            r.setdefault(col, None)
    return pl.DataFrame(rows, schema=schema)


def _buildLawsuitDf(rows: list[dict]):
    import polars as pl

    schema = {
        "year": pl.Int64,
        "filingDate": pl.Utf8,
        "parties": pl.Utf8,
        "description": pl.Utf8,
        "amount": pl.Utf8,
        "amountValue": pl.Int64,
        "status": pl.Utf8,
    }
    for r in rows:
        for col in schema:
            r.setdefault(col, None)
    return pl.DataFrame(rows, schema=schema)


class TestLegalEventRisk:
    def test_none_when_both_sources_missing(self):
        from dartlab.analysis.financial.governance import calcLegalEventRisk

        company = MagicMock()
        company._cache = {}
        with (
            patch("dartlab.analysis.financial.governance._loadSanction", return_value=None),
            patch(
                "dartlab.analysis.financial.governance._loadContingentLiability",
                return_value=None,
            ),
        ):
            assert calcLegalEventRisk(company) is None

    def test_counts_and_amounts(self):
        import datetime

        from dartlab.analysis.financial.governance import calcLegalEventRisk

        thisYear = datetime.datetime.now().year
        sanctionDf = _buildSanctionDf(
            [
                {
                    "year": thisYear - 1,
                    "date": f"{thisYear - 1}-03-15",
                    "agency": "공정위",
                    "action": "과징금 50억원",
                    "amountValue": 50_0000_0000,
                },
                {
                    "year": thisYear - 10,
                    "date": f"{thisYear - 10}-01-10",
                    "agency": "금융위",
                    "action": "과태료",
                    "amountValue": 1_0000_0000,
                },
            ]
        )
        lawsuitDf = _buildLawsuitDf(
            [
                {
                    "year": thisYear - 2,
                    "filingDate": f"{thisYear - 2}-05-20",
                    "parties": "A사 vs 당사",
                    "description": "손해배상",
                    "amountValue": 200_0000_0000,
                }
            ]
        )
        guaranteeDf = _buildGuaranteeDf([{"year": thisYear - 1, "totalGuaranteeAmount": 500_0000_0000, "lineCount": 3}])

        company = MagicMock()
        company._cache = {}
        with (
            patch(
                "dartlab.analysis.financial.governance._loadSanction",
                return_value=_MockSanctionResult(sanctionDf=sanctionDf),
            ),
            patch(
                "dartlab.analysis.financial.governance._loadContingentLiability",
                return_value=_MockContingentResult(guaranteeDf=guaranteeDf, lawsuitDf=lawsuitDf),
            ),
            patch(
                "dartlab.analysis.financial.governance._fetchLatestEquity",
                return_value=1000_0000_0000,
            ),
        ):
            result = calcLegalEventRisk(company)

        assert result is not None
        assert result["sanctionCount"] == 1
        assert result["sanctionAmount"] == 50_0000_0000
        assert result["lawsuitCount"] == 1
        assert result["lawsuitAmount"] == 200_0000_0000
        assert result["guaranteeAmount"] == 500_0000_0000
        assert result["totalEquity"] == 1000_0000_0000
        assert result["guaranteeToEquity"] == 50.0
        assert result["windowYears"] == 3
        assert len(result["recentEvents"]) == 2
        kinds = {e["kind"] for e in result["recentEvents"]}
        assert kinds == {"sanction", "lawsuit"}

    def test_edgar_company_returns_none(self):
        from dartlab.analysis.financial.governance import calcLegalEventRisk

        company = MagicMock()
        company._cache = {}
        company.currency = "USD"
        company.stockCode = "AAPL"
        assert calcLegalEventRisk(company) is None

    def test_governance_flags_include_sanction(self):
        import datetime

        from dartlab.analysis.financial.governance import calcGovernanceFlags

        thisYear = datetime.datetime.now().year
        sanctionDf = _buildSanctionDf(
            [
                {
                    "year": thisYear - 1,
                    "date": f"{thisYear - 1}-03-15",
                    "agency": "공정위",
                    "action": "과징금",
                    "amountValue": 30_0000_0000,
                }
            ]
        )
        company = _mockCompanyWithReport()
        company._cache = {}
        with (
            patch(
                "dartlab.analysis.financial.governance._loadSanction",
                return_value=_MockSanctionResult(sanctionDf=sanctionDf),
            ),
            patch(
                "dartlab.analysis.financial.governance._loadContingentLiability",
                return_value=None,
            ),
            patch(
                "dartlab.analysis.financial.governance._fetchLatestEquity",
                return_value=None,
            ),
        ):
            flags = calcGovernanceFlags(company)
        assert any("제재 1건" in msg for msg, _ in flags)


# ── 공시변화 테스트 ──


class TestDisclosureDelta:
    def test_calcDisclosureChangeSummary(self):
        from dartlab.analysis.financial.disclosureDelta import calcDisclosureChangeSummary

        company, diffResult = _mockCompanyWithDocs()
        with patch(
            "dartlab.analysis.financial.disclosureDelta._safeDiffResult",
            return_value=diffResult,
        ):
            result = calcDisclosureChangeSummary(company)
        assert result is not None
        assert result["totalChanges"] == 5
        assert result["changedTopics"] == 3
        assert result["unchangedTopics"] == 1
        assert len(result["topChanged"]) >= 1

    def test_calcKeyTopicChanges(self):
        from dartlab.analysis.financial.disclosureDelta import calcKeyTopicChanges

        company, diffResult = _mockCompanyWithDocs()
        with patch(
            "dartlab.analysis.financial.disclosureDelta._safeDiffResult",
            return_value=diffResult,
        ):
            result = calcKeyTopicChanges(company)
        assert result is not None
        topics = [kt["topic"] for kt in result["keyTopics"]]
        assert "businessOverview" in topics
        assert "riskFactors" in topics

    def test_calcChangeIntensity(self):
        from dartlab.analysis.financial.disclosureDelta import calcChangeIntensity

        company, diffResult = _mockCompanyWithDocs()
        with patch(
            "dartlab.analysis.financial.disclosureDelta._safeDiffResult",
            return_value=diffResult,
        ):
            result = calcChangeIntensity(company)
        assert result is not None
        assert result["totalDeltaBytes"] > 0
        assert len(result["topByDelta"]) >= 1

    def test_calcDisclosureDeltaFlags_riskFactors(self):
        from dartlab.analysis.financial.disclosureDelta import calcDisclosureDeltaFlags

        company, diffResult = _mockCompanyWithDocs()
        with patch(
            "dartlab.analysis.financial.disclosureDelta._safeDiffResult",
            return_value=diffResult,
        ):
            flags = calcDisclosureDeltaFlags(company)
        # riskFactors changeRate=1.0 -> 빈번한 변경
        assert any("riskFactors" in f for f, k in flags)

    def test_none_when_no_docs(self):
        from dartlab.analysis.financial.disclosureDelta import calcDisclosureChangeSummary

        company = MagicMock()
        with patch(
            "dartlab.analysis.financial.disclosureDelta._safeDiffResult",
            return_value=None,
        ):
            result = calcDisclosureChangeSummary(company)
        assert result is None


# ── 비교분석 테스트 ──


class TestPeerBenchmark:
    def test_calcPeerRanking_structure(self):
        from dartlab.analysis.financial.peerBenchmark import calcPeerRanking

        company = MagicMock()
        company.stockCode = "005930"

        with patch(
            "dartlab.analysis.financial.peerBenchmark._calcPercentile",
            side_effect=lambda sc, rn, lb: {
                "ratioName": rn,
                "label": lb,
                "value": 15.0,
                "percentile": 75.0,
                "rank": 250,
                "total": 1000,
                "period": "2024",
            },
        ):
            result = calcPeerRanking(company)
        assert result is not None
        assert len(result["rankings"]) == 8  # 8 benchmark ratios

    def test_calcRiskReturnPosition(self):
        from dartlab.analysis.financial.peerBenchmark import calcRiskReturnPosition

        company = MagicMock()
        company.stockCode = "005930"

        with (
            patch(
                "dartlab.analysis.financial.peerBenchmark.calcPeerRanking",
                return_value=None,
            ),
            patch(
                "dartlab.analysis.financial.peerBenchmark._getLatestValue",
                side_effect=lambda sc, rn: (15.0, 75.0) if rn == "roe" else (80.0, 30.0),
            ),
        ):
            result = calcRiskReturnPosition(company)
        assert result is not None
        assert result["quadrant"] == "고수익-저위험"
        assert result["assessment"] == "우량"

    def test_quadrant_lowReturn_highRisk(self):
        from dartlab.analysis.financial.peerBenchmark import calcRiskReturnPosition

        company = MagicMock()
        company.stockCode = "005930"

        with (
            patch(
                "dartlab.analysis.financial.peerBenchmark.calcPeerRanking",
                return_value=None,
            ),
            patch(
                "dartlab.analysis.financial.peerBenchmark._getLatestValue",
                side_effect=lambda sc, rn: (3.0, 20.0) if rn == "roe" else (300.0, 80.0),
            ),
        ):
            result = calcRiskReturnPosition(company)
        assert result is not None
        assert result["quadrant"] == "저수익-고위험"

    def test_calcPeerBenchmarkFlags(self):
        from dartlab.analysis.financial.peerBenchmark import calcPeerBenchmarkFlags

        company = MagicMock()
        company.stockCode = "005930"

        # ROE top 5%, 부채비율 top 5%
        def mockPercentile(sc, rn, lb):
            if rn == "roe":
                return {
                    "ratioName": rn,
                    "label": "ROE",
                    "value": 25.0,
                    "percentile": 95.0,
                    "rank": 50,
                    "total": 1000,
                    "period": "2024",
                }
            if rn == "debtRatio":
                return {
                    "ratioName": rn,
                    "label": "부채비율",
                    "value": 400.0,
                    "percentile": 95.0,
                    "rank": 50,
                    "total": 1000,
                    "period": "2024",
                }
            return {
                "ratioName": rn,
                "label": lb,
                "value": 10.0,
                "percentile": 50.0,
                "rank": 500,
                "total": 1000,
                "period": "2024",
            }

        with patch(
            "dartlab.analysis.financial.peerBenchmark._calcPercentile",
            side_effect=mockPercentile,
        ):
            with patch(
                "dartlab.analysis.financial.peerBenchmark.calcRiskReturnPosition",
                return_value={"quadrant": "고수익-고위험", "assessment": "레버리지 의존"},
            ):
                flags = calcPeerBenchmarkFlags(company)

        # ROE 상위 5% -> 기회, 부채비율 상위 5% -> 경고
        assert any("ROE 상위" in f and k == "opportunity" for f, k in flags)
        assert any("부채비율 상위" in f and k == "warning" for f, k in flags)


# ── Registry 통합 테스트 ──


class TestAxisRegistry:
    def test_registry_has_21_axes(self):
        from dartlab.analysis.financial import _AXIS_REGISTRY

        assert len(_AXIS_REGISTRY) >= 20  # 최소 20축 (새 축 추가 시 증가)

    def test_new_axes_in_registry(self):
        from dartlab.analysis.financial import _AXIS_REGISTRY

        assert "지배구조" in _AXIS_REGISTRY
        assert "공시변화" in _AXIS_REGISTRY
        assert "비교분석" in _AXIS_REGISTRY

    def test_aliases(self):
        from dartlab.analysis.financial import _ALIASES

        assert _ALIASES["governance"] == "지배구조"
        assert _ALIASES["disclosureDelta"] == "공시변화"
        assert _ALIASES["peerBenchmark"] == "비교분석"

    def test_resolve_axis(self):
        from dartlab.analysis.financial import _resolveAxis

        assert _resolveAxis("governance") == "지배구조"
        assert _resolveAxis("지배구조") == "지배구조"
        assert _resolveAxis("disclosureDelta") == "공시변화"
        assert _resolveAxis("peerBenchmark") == "비교분석"


class TestCatalog:
    def test_sections_count(self):
        from dartlab.story.catalog import SECTIONS

        assert len(SECTIONS) >= 20  # 섹션 추가 시 증가

    def test_new_sections_exist(self):
        from dartlab.story.catalog import SECTIONS

        keys = [s.key for s in SECTIONS]
        assert "지배구조" in keys
        assert "공시변화" in keys
        assert "비교분석" in keys

    def test_new_blocks_exist(self):
        from dartlab.story.catalog import listBlocks

        blocks = listBlocks()
        blockKeys = {b.key for b in blocks}
        expected = {
            "ownershipTrend",
            "boardComposition",
            "auditOpinionTrend",
            "governanceFlags",
            "disclosureChangeSummary",
            "keyTopicChanges",
            "changeIntensity",
            "disclosureDeltaFlags",
            "peerRanking",
            "riskReturnPosition",
            "peerBenchmarkFlags",
        }
        assert expected.issubset(blockKeys)
