"""industry/build/financials.py 의 단위 오류 sanity guard unit 테스트.

순수 로직 — synthetic DataFrame 으로 _applySanityGuard 검증. parquet 데이터 의존 X.
"""

from __future__ import annotations

import polars as pl
import pytest

pytestmark = [pytest.mark.unit]


class TestSanityGuard:
    def test_revenue_outlier_replaced_with_null(self):
        """매출 > 500조 (5e14) → None 으로 대체 (단위 오류 의심)."""
        from dartlab.industry.build.financials import _applySanityGuard

        df = pl.DataFrame(
            {
                "stockCode": ["005930", "000270", "032680"],  # 삼성·기아·소프트센(outlier)
                "revenue": [3.0e14, 1.0e14, 7.34e16],
                "opIncome": [4.0e13, 1.0e13, 1.63e16],
                "totalAssets": [4.0e14, 1.0e14, 1.22e17],
            }
        )
        out = _applySanityGuard(df, year="2022")

        rows = {row["stockCode"]: row for row in out.iter_rows(named=True)}
        # 정상 (삼성·기아) 보존
        assert rows["005930"]["revenue"] == 3.0e14
        assert rows["000270"]["revenue"] == 1.0e14
        # outlier (소프트센) None 대체
        assert rows["032680"]["revenue"] is None
        assert rows["032680"]["opIncome"] is None
        assert rows["032680"]["totalAssets"] is None

    def test_normal_korean_giants_preserved(self):
        """삼성전자 매출 300조 같은 정상 거대 기업 절대 hit 안 함."""
        from dartlab.industry.build.financials import _applySanityGuard

        df = pl.DataFrame(
            {
                "stockCode": ["005930"],
                "revenue": [3.0e14],  # 삼성전자 ~300조 (한국 최대 매출)
                "opIncome": [3.0e13],
                "totalAssets": [4.5e14],
            }
        )
        out = _applySanityGuard(df, year="2024")
        row = out.row(0, named=True)
        assert row["revenue"] == 3.0e14, "삼성전자 정상 매출이 outlier 로 오판되면 안 됨"

    def test_negative_outlier_also_caught(self):
        """absolute value 기준 — 음의 단위 오류 (-7e16 같은 값) 도 잡음."""
        from dartlab.industry.build.financials import _applySanityGuard

        df = pl.DataFrame(
            {
                "stockCode": ["X"],
                "revenue": [-7.34e16],
                "opIncome": [1.0e10],  # 정상 값
                "totalAssets": [1.0e12],
            }
        )
        out = _applySanityGuard(df, year="2022")
        row = out.row(0, named=True)
        assert row["revenue"] is None
        # 정상 컬럼은 보존
        assert row["opIncome"] == 1.0e10
        assert row["totalAssets"] == 1.0e12

    def test_all_null_column_safe(self):
        """전부 null 인 컬럼 (null dtype) 도 안전 — abs 연산 skip."""
        from dartlab.industry.build.financials import _applySanityGuard

        df = pl.DataFrame(
            {
                "stockCode": ["X"],
                "revenue": [7.34e16],
                "opIncome": [None],  # 전부 null → null dtype
                "totalAssets": [None],
            }
        )
        # 예외 없이 처리
        out = _applySanityGuard(df, year="2022")
        assert out.row(0, named=True)["revenue"] is None

    def test_empty_df_safe(self):
        """빈 DataFrame 안전 처리."""
        from dartlab.industry.build.financials import _applySanityGuard

        out = _applySanityGuard(pl.DataFrame(), year="2024")
        assert out.height == 0

    def test_partial_columns_ok(self):
        """totalAssets 컬럼 없어도 안전 (revenue 만 있어도 작동)."""
        from dartlab.industry.build.financials import _applySanityGuard

        df = pl.DataFrame(
            {
                "stockCode": ["X"],
                "revenue": [7.34e16],
            }
        )
        out = _applySanityGuard(df, year="2022")
        assert out.row(0, named=True)["revenue"] is None
