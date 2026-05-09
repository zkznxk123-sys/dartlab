"""Credit migration matrix + forward PD ladder unit 테스트.

순수 로직 — synthetic transition counts 로 검증. 실 dCR history 데이터 의존 X.
검증 항목:
- row-stochastic (각 row sum to 1)
- D absorbing (D row 는 self-loop only)
- 빈 row self-loop fallback
- PD monotonicity (horizon ↑ → PD ↑, rating 악화 → PD ↑)
"""

from __future__ import annotations

import pytest

pytestmark = [pytest.mark.unit]


# 합리적 dCR 분포 — 대부분 self-transition + 인접 등급 이동 + 등급 악화 시 D 비중 단조 증가
# (CreditMetrics 1997 표준 ladder 와 유사 — AAA 는 직접 D 0, CCC 는 25%+).
SAMPLE_COUNTS = {
    "AAA": {"AAA": 95, "AA+": 4, "AA": 1},
    "AA": {"AAA": 1, "AA+": 3, "AA": 89, "AA-": 5, "A+": 2},
    "A": {"AA-": 2, "A+": 5, "A": 80, "A-": 8, "BBB": 4, "D": 1},
    "BBB": {"A": 3, "BBB+": 5, "BBB": 73, "BBB-": 10, "BB": 5, "D": 4},
    "BB": {"BBB": 4, "BB+": 8, "BB": 56, "BB-": 18, "B": 6, "D": 8},
    "B": {"BB": 3, "B+": 10, "B": 45, "B-": 25, "CCC": 5, "D": 12},
    "CCC": {"B": 5, "CCC": 25, "CC": 20, "C": 25, "D": 25},
}


# ════════════════════════════════════════
# buildTransitionMatrix — row-stochastic 보장
# ════════════════════════════════════════


class TestBuildTransitionMatrix:
    def test_observed_row_sums_to_one(self):
        from dartlab.credit.migration import _DEFAULT_RATING_ORDER, buildTransitionMatrix

        df = buildTransitionMatrix(SAMPLE_COUNTS)
        # 각 row 의 to_rating 컬럼 합 = 1 (within float tolerance)
        for row in df.iter_rows(named=True):
            row_sum = sum(row[r] for r in _DEFAULT_RATING_ORDER)
            assert abs(row_sum - 1.0) < 1e-9, f"row {row['from_rating']} sums to {row_sum}, not 1"

    def test_empty_row_self_transition(self):
        """관측 0 인 등급은 self-loop (안정 가정)."""
        from dartlab.credit.migration import buildTransitionMatrix

        # AAA 만 관측 — AAA 외 등급은 모두 빈 row → self-loop 만
        sparse = {"AAA": {"AAA": 10, "AA+": 1}}
        df = buildTransitionMatrix(sparse)

        # AA 행 (관측 없음) → AA 컬럼만 1, 나머지 0
        aa_row = df.filter(df["from_rating"] == "AA").row(0, named=True)
        assert abs(aa_row["AA"] - 1.0) < 1e-9
        assert abs(aa_row["AAA"]) < 1e-9
        assert abs(aa_row["AA+"]) < 1e-9

    def test_D_is_absorbing(self):
        """D 행은 항상 self-loop only — 부도 흡수 상태."""
        from dartlab.credit.migration import _DEFAULT_RATING_ORDER, buildTransitionMatrix

        # D 에서 임의 전이 시도 (실제로는 발생 X 인 데이터, absorbing 강제 검증)
        with_d_transition = {**SAMPLE_COUNTS, "D": {"AAA": 5, "D": 95}}
        df = buildTransitionMatrix(with_d_transition)

        d_row = df.filter(df["from_rating"] == "D").row(0, named=True)
        assert abs(d_row["D"] - 1.0) < 1e-9
        # 다른 어떤 등급으로도 0
        for r in _DEFAULT_RATING_ORDER:
            if r == "D":
                continue
            assert abs(d_row[r]) < 1e-9, f"D → {r} should be 0 (absorbing)"

    def test_unknown_rating_in_counts_ignored(self):
        """ratings tuple 외 등급 키는 무시 (미정의 등급 안전 처리)."""
        from dartlab.credit.migration import buildTransitionMatrix

        with_unknown = {"AAA": {"AAA": 10, "ZZZ_UNKNOWN": 5}}
        df = buildTransitionMatrix(with_unknown)

        aaa_row = df.filter(df["from_rating"] == "AAA").row(0, named=True)
        # ZZZ 무시 → 10/10 = 1.0 self
        assert abs(aaa_row["AAA"] - 1.0) < 1e-9


# ════════════════════════════════════════
# forwardPdLadder — Cohort matrix power
# ════════════════════════════════════════


class TestForwardPdLadder:
    def test_horizon_monotonicity(self):
        """동일 등급에서 horizon ↑ → PD ↑ (누적)."""
        from dartlab.credit.migration import forwardPdLadder

        df = forwardPdLadder(SAMPLE_COUNTS, horizons=(1, 3, 5))
        for row in df.iter_rows(named=True):
            assert row["1yPD"] <= row["3yPD"] + 1e-9, f"{row['rating']}: 1y {row['1yPD']} > 3y {row['3yPD']}"
            assert row["3yPD"] <= row["5yPD"] + 1e-9, f"{row['rating']}: 3y {row['3yPD']} > 5y {row['5yPD']}"

    def test_rating_quality_monotonicity_at_5y(self):
        """등급 악화 → PD 단조 증가 (5 년)."""
        from dartlab.credit.migration import forwardPdLadder

        df = forwardPdLadder(SAMPLE_COUNTS, horizons=(5,))
        # AAA → CCC 순으로 5yPD 가 단조 증가해야 정상 (학술 표준)
        check_order = ["AAA", "AA", "A", "BBB", "BB", "B", "CCC"]
        prev = -1.0
        for r in check_order:
            row = df.filter(df["rating"] == r).row(0, named=True)
            assert row["5yPD"] >= prev - 1e-9, f"{r} 5yPD {row['5yPD']} < 이전 등급 {prev} (단조성 위반)"
            prev = row["5yPD"]

    def test_AAA_pd_lower_than_CCC(self):
        """AAA 5yPD ≪ CCC 5yPD (강한 차이)."""
        from dartlab.credit.migration import forwardPdLadder

        df = forwardPdLadder(SAMPLE_COUNTS, horizons=(5,))
        aaa_pd = df.filter(df["rating"] == "AAA").row(0, named=True)["5yPD"]
        ccc_pd = df.filter(df["rating"] == "CCC").row(0, named=True)["5yPD"]
        assert ccc_pd > aaa_pd, f"CCC 5yPD {ccc_pd} not > AAA {aaa_pd}"
        assert ccc_pd > 10 * aaa_pd, "CCC PD 가 AAA 의 10 배 이상이어야 정상"

    def test_D_pd_is_one(self):
        """D 등급은 이미 부도 — 모든 horizon 에서 PD = 1.0."""
        from dartlab.credit.migration import forwardPdLadder

        df = forwardPdLadder(SAMPLE_COUNTS, horizons=(1, 3, 5))
        d_row = df.filter(df["rating"] == "D").row(0, named=True)
        assert abs(d_row["1yPD"] - 1.0) < 1e-9
        assert abs(d_row["3yPD"] - 1.0) < 1e-9
        assert abs(d_row["5yPD"] - 1.0) < 1e-9

    def test_empty_counts_returns_zero_pd(self):
        """관측 0 → 모두 self-loop → D 도달 0 → 모든 PD 0."""
        from dartlab.credit.migration import forwardPdLadder

        df = forwardPdLadder({}, horizons=(1, 3, 5))
        for row in df.iter_rows(named=True):
            if row["rating"] == "D":
                continue  # D 자체는 PD=1
            assert row["1yPD"] == 0.0
            assert row["5yPD"] == 0.0

    def test_zero_horizon_returns_zero(self):
        """horizon 0 → PD 0 (현재 시점은 부도 상태가 아니면 PD=0)."""
        from dartlab.credit.migration import forwardPdLadder

        df = forwardPdLadder(SAMPLE_COUNTS, horizons=(0,))
        for row in df.iter_rows(named=True):
            assert row["0yPD"] == 0.0
