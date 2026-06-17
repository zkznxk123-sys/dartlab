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


class TestProfitPoolDerived:
    """buildIndustrySummary 의 profit-pool 파생 컬럼 (영업이익률·coverageRatio) 단언.

    엔진 파생 = dual-source SSOT 캐논 (mainPlan/industry-analysis-lab/07 §구멍1).
    parquet 무의존 — ``_extractYearly`` monkeypatch + 합성 노드.
    """

    @staticmethod
    def _node(stockCode: str, industry: str, stage: str):
        from types import SimpleNamespace

        return SimpleNamespace(stockCode=stockCode, industry=industry, stage=stage)

    def _run(self, monkeypatch, fin: pl.DataFrame, nodes):
        from dartlab.industry.build import financials

        monkeypatch.setattr(financials, "_extractYearly", lambda year: fin)
        # getIndustry("synthIndustry") → None → stageLabels={} → 공정명 None (단언 무관)
        return financials.buildIndustrySummary(nodes, "synthIndustry", year="2024")

    def test_margin_is_revenue_weighted_not_simple_average(self, monkeypatch):
        """stage 영업이익률 = Σ영업이익/Σ매출 (revenue-weighted) — 단순평균(30%) 아님."""
        fin = pl.DataFrame(
            {
                "stockCode": ["big", "small"],
                "revenue": [100e12, 1e12],
                "opIncome": [10e12, 0.5e12],  # 마진 10% vs 50%
            }
        )
        nodes = [
            self._node("big", "synthIndustry", "fab"),
            self._node("small", "synthIndustry", "fab"),
        ]
        out = self._run(monkeypatch, fin, nodes)
        row = out.row(0, named=True)
        # revenue-weighted = (10+0.5)/(100+1)*100 = 10.396 → 10.4, NOT (10+50)/2 = 30
        assert row["영업이익률(%)"] == 10.4
        assert row["영업이익률(%)"] != 30.0
        assert row["coverageRatio"] == 1.0  # 둘 다 opIncome present

    def test_coverage_ratio_excludes_null_opincome(self, monkeypatch):
        """coverageRatio = opIncome 산출가능 / stage 회사수, 결손은 0 채움 아닌 제외."""
        fin = pl.DataFrame(
            {
                "stockCode": ["a", "b", "c"],
                "revenue": [100e12, 1e12, 5e12],
                "opIncome": [10e12, 0.5e12, None],  # c 결손
            }
        )
        nodes = [
            self._node("a", "synthIndustry", "fab"),
            self._node("b", "synthIndustry", "fab"),
            self._node("c", "synthIndustry", "fab"),
        ]
        out = self._run(monkeypatch, fin, nodes)
        row = out.row(0, named=True)
        assert row["기업수"] == 3
        assert row["coverageRatio"] == 0.667  # 2/3, round(3)
        # 마진은 결손 c 제외하고 a·b 만 revenue-weighted (0 채움 시 마진이 깎였을 것)
        assert row["영업이익률(%)"] == 10.4
        # opIncome 합은 c(null) skip → 10.5조
        assert row["영업이익(조)"] == 10.5

    def test_zero_revenue_margin_is_null_not_zero(self, monkeypatch):
        """매출 합 0 또는 opIncome 전무 stage → 영업이익률 null (0 채움/division 에러 금지)."""
        fin = pl.DataFrame(
            {
                "stockCode": ["x"],
                "revenue": [0.0],
                "opIncome": [None],
            }
        )
        nodes = [self._node("x", "synthIndustry", "fab")]
        out = self._run(monkeypatch, fin, nodes)
        row = out.row(0, named=True)
        assert row["영업이익률(%)"] is None
        assert row["coverageRatio"] == 0.0

    def test_schema_has_derived_columns(self, monkeypatch):
        """반환 스키마에 영업이익률(%)·coverageRatio 컬럼 존재 (소비자 계약)."""
        fin = pl.DataFrame({"stockCode": ["a"], "revenue": [10e12], "opIncome": [1e12]})
        nodes = [self._node("a", "synthIndustry", "fab")]
        out = self._run(monkeypatch, fin, nodes)
        assert "영업이익률(%)" in out.columns
        assert "coverageRatio" in out.columns
        assert out.columns == [
            "stage",
            "공정명",
            "매출(조)",
            "영업이익(조)",
            "기업수",
            "영업이익률(%)",
            "coverageRatio",
        ]


class TestConcentrationVerb:
    """Industry()(id, concentration=True) 어댑터 — calcs.concentration dict → DataFrame.

    묻어둔 calcIndustryConcentration(테스트만 호출)을 런타임 verb 모드로 노출
    (mainPlan/industry-analysis-lab/07 §구멍 — 집중도 함수 런타임 노출 thesis).
    parquet 무의존 — loadNodes monkeypatch + 합성 노드. **상장사 매출 기준** 상대 집중도.
    """

    @staticmethod
    def _node(stockCode: str, corpName: str, stage: str, revenue, industry="synthIndustry"):
        from types import SimpleNamespace

        return SimpleNamespace(stockCode=stockCode, corpName=corpName, industry=industry, stage=stage, revenue=revenue)

    def _run(self, monkeypatch, nodes):
        from dartlab.industry import Industry
        from dartlab.industry.build import pipeline

        monkeypatch.setattr(pipeline, "loadNodes", lambda: nodes)
        return Industry()("synthIndustry", concentration=True)

    def test_revenue_share_and_hhi_columns(self, monkeypatch):
        """상위사 행 + 매출비중(%) + 산업 집계(HHI·CR3·기업수) 동반."""
        nodes = [
            self._node("a", "A사", "fab", 60e12),
            self._node("b", "B사", "fab", 30e12),
            self._node("c", "C사", "fab", 10e12),
        ]
        out = self._run(monkeypatch, nodes)
        rows = out.to_dicts()
        assert [r["종목명"] for r in rows] == ["A사", "B사", "C사"]  # 매출 내림차순
        # 매출비중 = 상장사 내 상대 — 60/100, 30/100, 10/100
        assert rows[0]["매출비중(%)"] == 60.0
        assert rows[2]["매출비중(%)"] == 10.0
        # HHI = 60^2+30^2+10^2 = 4600 (모든 행에 반복 첨부)
        assert rows[0]["HHI"] == 4600.0
        assert rows[0]["HHI라벨"] == "집중"
        assert rows[0]["상위3비중(%)"] == 100.0
        assert rows[0]["기업수"] == 3
        assert rows[0]["총매출(조)"] == 100.0

    def test_only_top5_rows(self, monkeypatch):
        """7사여도 상위 5사만 행으로 반환 (calcIndustryConcentration topN=5)."""
        nodes = [self._node(f"s{i}", f"{i}사", "fab", (10 - i) * 1e12) for i in range(7)]
        out = self._run(monkeypatch, nodes)
        assert out.height == 5

    def test_empty_industry_returns_typed_empty(self, monkeypatch):
        """매출 양수 회사 없으면 빈 DataFrame(스키마 보존) — 0 채움/예외 금지."""
        nodes = [self._node("z", "Z사", "fab", None)]
        out = self._run(monkeypatch, nodes)
        assert out.height == 0
        assert "매출비중(%)" in out.columns
        assert "HHI" in out.columns


class TestProfitPoolDynamics:
    """calcProfitPoolDynamics — argmax 리더 교체로 집중형/이동형 판정 (산업 동학).

    measure-first 실측(2차전지 이동·반도체 집중)이 독립 oracle. parquet 무의존 —
    buildTimelineSummary monkeypatch + 합성 stage×연도 영업이익. share 금지·levels·적자전환·생존편향.
    """

    def _timeline(self, recs):
        """recs = [(연도, stage, 공정명, 영업이익조, 기업수)] → buildTimelineSummary 형태 DataFrame."""
        return pl.DataFrame(
            [
                {"연도": y, "stage": st, "공정명": nm, "매출(조)": 0.0, "영업이익(조)": op, "기업수": n}
                for (y, st, nm, op, n) in recs
            ]
        )

    def _run(self, monkeypatch, df):
        from dartlab.industry.build import financials, pipeline
        from dartlab.industry.calcs.profitPoolDynamics import calcProfitPoolDynamics

        monkeypatch.setattr(pipeline, "loadNodes", lambda: [])
        monkeypatch.setattr(financials, "buildTimelineSummary", lambda nodes, ind, years=None: df)
        return calcProfitPoolDynamics("synth")

    def test_migration_when_leader_changes(self, monkeypatch):
        """2차전지형 — 양극재(첫해 1위, 적자전환) → 셀(끝해 1위) = 이동형."""
        df = self._timeline(
            [
                ("2021", "cathode", "양극재", 0.3, 5),
                ("2021", "cell", "셀", 0.2, 3),
                ("2024", "cathode", "양극재", -0.5, 5),
                ("2024", "cell", "셀", 0.7, 3),
            ]
        )
        r = self._run(monkeypatch, df)
        assert r["판정"] == "이동형"
        assert r["리더_첫해"][1] == "양극재"
        assert r["리더_끝해"][1] == "셀"
        assert "양극재" in r["적자전환"]  # 0.3 > 0, -0.5 < 0
        assert r["윈도"] == "2021~2024"

    def test_concentration_when_leader_fixed(self, monkeypatch):
        """반도체형 — FAB이 모든 해 1위 = 집중형. 적자전환 없음."""
        df = self._timeline(
            [
                ("2021", "fab", "전공정", 64.0, 20),
                ("2021", "design", "설계", 0.4, 13),
                ("2024", "fab", "전공정", 56.0, 20),
                ("2024", "design", "설계", 0.1, 13),
            ]
        )
        r = self._run(monkeypatch, df)
        assert r["판정"] == "집중형"
        assert r["리더_첫해"][1] == r["리더_끝해"][1] == "전공정"
        assert r["적자전환"] == []

    def test_under_two_valid_years_returns_none(self, monkeypatch):
        """유효 연도(Σ영업이익>0) < 2 면 판정 None (zero-crossing/단년 가드)."""
        df = self._timeline(
            [
                ("2021", "fab", "전공정", -1.0, 5),  # Σ<0 → 무효
                ("2024", "fab", "전공정", 5.0, 5),  # 유효 1개뿐
            ]
        )
        r = self._run(monkeypatch, df)
        assert r["판정"] is None
        assert r["생존편향주의"]  # 고정 필드는 항상 존재
