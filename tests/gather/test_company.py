"""Company 클래스 기본 테스트."""

import polars as pl
import pytest

from tests.conftest import SAMSUNG, requires_samsung

pytestmark = pytest.mark.integration


class TestCompany:
    @classmethod
    def setup_class(cls):
        from dartlab import Company

        cls.c = Company(SAMSUNG)

    def test_init_by_code(self):
        c = self.c
        assert c.stockCode == SAMSUNG
        assert c.corpName == "삼성전자"

    def test_repr(self):
        import dartlab

        dartlab.verbose = False
        c = self.c
        assert "005930" in repr(c)
        assert "삼성전자" in repr(c)
        dartlab.verbose = True

    def test_filings(self):
        c = self.c
        filings = c.filings()
        assert isinstance(filings, pl.DataFrame)
        assert len(filings) > 0
        assert "dartUrl" in filings.columns

    def test_invalid_name_raises(self):
        from dartlab import Company

        with pytest.raises(ValueError):
            Company("존재하지않는회사명zzz")

    def test_sections_hide_raw_source_topics(self):
        c = self.c
        sections = c.sections
        assert sections is not None
        topics = set(sections["topic"].to_list())
        assert "주요제품및원재료등" not in topics
        assert "파생상품등에관한사항" not in topics
        assert "I.회사의개황" not in topics

    def test_profile_trace_for_finance_and_report_topics(self):
        c = self.c
        assert c.trace("dividend")["primarySource"] == "report"
        assert c.trace("BS")["primarySource"] == "finance"
        assert c.trace("CIS")["primarySource"] == "finance"
        ratioTrace = c.trace("ratios")
        assert ratioTrace["primarySource"] == "finance"
        assert ratioTrace["template"] == "general"
        assert ratioTrace["coverage"] in {"full", "partial"}
        assert ratioTrace["rowCount"] is not None
        assert ratioTrace["yearCount"] is not None

    def test_index_and_profile_accessor(self):
        c = self.c
        assert c.index.height > 0
        assert set(["chapter", "topic", "kind", "source", "periods", "shape", "preview"]).issubset(set(c.index.columns))
        assert c.sections is not None
        assert isinstance(c.sections, pl.DataFrame)
        assert c.facts is not None
        assert isinstance(c.facts, pl.DataFrame)

    def test_report_available_api_types_matches_extract_without_extract_caches(self):
        from dartlab.providers.dart.company import Company as DartCompany
        from dartlab.providers.dart.report.types import API_TYPES

        fastCompany = DartCompany(SAMSUNG)
        available = fastCompany.report.availableApiTypes

        reportCacheKeys = set(fastCompany.report._cache._store.keys())
        assert "_availableApiTypes" in reportCacheKeys
        assert not any(key.startswith("_extract_") for key in reportCacheKeys)

        baselineCompany = DartCompany(SAMSUNG)
        expected = [name for name in API_TYPES if baselineCompany.report.extract(name) is not None]
        assert available == expected

    def test_report_result_surface_is_unified(self):
        from dartlab.providers.dart.report.types import ReportResult

        c = self.c
        dividend = c._report.result("dividend")
        treasury = c._report.result("treasuryStock")

        assert dividend is not None
        assert hasattr(dividend, "df")
        assert isinstance(dividend.df, pl.DataFrame)

        assert treasury is None or isinstance(treasury, ReportResult)
        if treasury is not None:
            assert isinstance(treasury.df, pl.DataFrame)

    def test_index_includes_finance_ratio_series(self):
        c = self.c
        ratios = c.index.filter(pl.col("topic") == "ratios")
        assert ratios.height == 1
        assert ratios.item(0, "chapter") == "III. 재무에 관한 사항"
        assert ratios.item(0, "source") == "finance"
        assert ratios.item(0, "label") == "재무비율"
