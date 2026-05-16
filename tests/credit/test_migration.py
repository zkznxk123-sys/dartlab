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
# (CreditMetrics 1997 표준 ladder 와 유사 — dCR-AAA 는 직접 D 0, dCR-CCC 는 25%+).
# 실 transition.json 는 result['grade'] (full prefix "dCR-XXX") 로 누적되므로 동일 형식.
SAMPLE_COUNTS = {
    "dCR-AAA": {"dCR-AAA": 95, "dCR-AA+": 4, "dCR-AA": 1},
    "dCR-AA": {"dCR-AAA": 1, "dCR-AA+": 3, "dCR-AA": 89, "dCR-AA-": 5, "dCR-A+": 2},
    "dCR-A": {"dCR-AA-": 2, "dCR-A+": 5, "dCR-A": 80, "dCR-A-": 8, "dCR-BBB": 4, "dCR-D": 1},
    "dCR-BBB": {"dCR-A": 3, "dCR-BBB+": 5, "dCR-BBB": 73, "dCR-BBB-": 10, "dCR-BB": 5, "dCR-D": 4},
    "dCR-BB": {"dCR-BBB": 4, "dCR-BB+": 8, "dCR-BB": 56, "dCR-BB-": 18, "dCR-B": 6, "dCR-D": 8},
    "dCR-B": {"dCR-BB": 3, "dCR-B+": 10, "dCR-B": 45, "dCR-B-": 25, "dCR-CCC": 5, "dCR-D": 12},
    "dCR-CCC": {"dCR-B": 5, "dCR-CCC": 25, "dCR-CC": 20, "dCR-C": 25, "dCR-D": 25},
}


# ════════════════════════════════════════
# buildTransitionMatrix — row-stochastic 보장
# ════════════════════════════════════════


class TestBuildTransitionMatrix:
    def test_observed_row_sums_to_one(self):
        from dartlab.credit.scoring.migration import _DEFAULT_RATING_ORDER, buildTransitionMatrix

        df = buildTransitionMatrix(SAMPLE_COUNTS)
        # 각 row 의 to_rating 컬럼 합 = 1 (within float tolerance)
        for row in df.iter_rows(named=True):
            row_sum = sum(row[r] for r in _DEFAULT_RATING_ORDER)
            assert abs(row_sum - 1.0) < 1e-9, f"row {row['from_rating']} sums to {row_sum}, not 1"

    def test_empty_row_self_transition(self):
        """관측 0 인 등급은 self-loop (안정 가정)."""
        from dartlab.credit.scoring.migration import buildTransitionMatrix

        # dCR-AAA 만 관측 — 그 외 등급은 모두 빈 row → self-loop 만
        sparse = {"dCR-AAA": {"dCR-AAA": 10, "dCR-AA+": 1}}
        df = buildTransitionMatrix(sparse)

        # dCR-AA 행 (관측 없음) → dCR-AA 컬럼만 1, 나머지 0
        aa_row = df.filter(df["from_rating"] == "dCR-AA").row(0, named=True)
        assert abs(aa_row["dCR-AA"] - 1.0) < 1e-9
        assert abs(aa_row["dCR-AAA"]) < 1e-9
        assert abs(aa_row["dCR-AA+"]) < 1e-9

    def test_D_is_absorbing(self):
        """D 행은 항상 self-loop only — 부도 흡수 상태."""
        from dartlab.credit.scoring.migration import _DEFAULT_RATING_ORDER, buildTransitionMatrix

        # D 에서 임의 전이 시도 (실제로는 발생 X 인 데이터, absorbing 강제 검증)
        with_d_transition = {**SAMPLE_COUNTS, "dCR-D": {"dCR-AAA": 5, "dCR-D": 95}}
        df = buildTransitionMatrix(with_d_transition)

        d_row = df.filter(df["from_rating"] == "dCR-D").row(0, named=True)
        assert abs(d_row["dCR-D"] - 1.0) < 1e-9
        # 다른 어떤 등급으로도 0
        for r in _DEFAULT_RATING_ORDER:
            if r == "dCR-D":
                continue
            assert abs(d_row[r]) < 1e-9, f"dCR-D → {r} should be 0 (absorbing)"

    def test_unknown_rating_in_counts_ignored(self):
        """ratings tuple 외 등급 키는 무시 (미정의 등급 안전 처리)."""
        from dartlab.credit.scoring.migration import buildTransitionMatrix

        with_unknown = {"dCR-AAA": {"dCR-AAA": 10, "ZZZ_UNKNOWN": 5}}
        df = buildTransitionMatrix(with_unknown)

        aaa_row = df.filter(df["from_rating"] == "dCR-AAA").row(0, named=True)
        # ZZZ 무시 → 10/10 = 1.0 self
        assert abs(aaa_row["dCR-AAA"] - 1.0) < 1e-9


# ════════════════════════════════════════
# forwardPdLadder — Cohort matrix power
# ════════════════════════════════════════


class TestForwardPdLadder:
    def test_horizon_monotonicity(self):
        """동일 등급에서 horizon ↑ → PD ↑ (누적)."""
        from dartlab.credit.scoring.migration import forwardPdLadder

        df = forwardPdLadder(SAMPLE_COUNTS, horizons=(1, 3, 5))
        for row in df.iter_rows(named=True):
            assert row["1yPD"] <= row["3yPD"] + 1e-9, f"{row['rating']}: 1y {row['1yPD']} > 3y {row['3yPD']}"
            assert row["3yPD"] <= row["5yPD"] + 1e-9, f"{row['rating']}: 3y {row['3yPD']} > 5y {row['5yPD']}"

    def test_rating_quality_monotonicity_at_5y(self):
        """등급 악화 → PD 단조 증가 (5 년)."""
        from dartlab.credit.scoring.migration import forwardPdLadder

        df = forwardPdLadder(SAMPLE_COUNTS, horizons=(5,))
        # dCR-AAA → dCR-CCC 순으로 5yPD 가 단조 증가해야 정상 (학술 표준)
        check_order = ["dCR-AAA", "dCR-AA", "dCR-A", "dCR-BBB", "dCR-BB", "dCR-B", "dCR-CCC"]
        prev = -1.0
        for r in check_order:
            row = df.filter(df["rating"] == r).row(0, named=True)
            assert row["5yPD"] >= prev - 1e-9, f"{r} 5yPD {row['5yPD']} < 이전 등급 {prev} (단조성 위반)"
            prev = row["5yPD"]

    def test_AAA_pd_lower_than_CCC(self):
        """dCR-AAA 5yPD ≪ dCR-CCC 5yPD (강한 차이)."""
        from dartlab.credit.scoring.migration import forwardPdLadder

        df = forwardPdLadder(SAMPLE_COUNTS, horizons=(5,))
        aaa_pd = df.filter(df["rating"] == "dCR-AAA").row(0, named=True)["5yPD"]
        ccc_pd = df.filter(df["rating"] == "dCR-CCC").row(0, named=True)["5yPD"]
        assert ccc_pd > aaa_pd, f"dCR-CCC 5yPD {ccc_pd} not > dCR-AAA {aaa_pd}"
        assert ccc_pd > 10 * aaa_pd, "dCR-CCC PD 가 dCR-AAA 의 10 배 이상이어야 정상"

    def test_D_pd_is_one(self):
        """dCR-D 등급은 이미 부도 — 모든 horizon 에서 PD = 1.0."""
        from dartlab.credit.scoring.migration import forwardPdLadder

        df = forwardPdLadder(SAMPLE_COUNTS, horizons=(1, 3, 5))
        d_row = df.filter(df["rating"] == "dCR-D").row(0, named=True)
        assert abs(d_row["1yPD"] - 1.0) < 1e-9
        assert abs(d_row["3yPD"] - 1.0) < 1e-9
        assert abs(d_row["5yPD"] - 1.0) < 1e-9

    def test_empty_counts_returns_zero_pd(self):
        """관측 0 → 모두 self-loop → D 도달 0 → 모든 PD 0."""
        from dartlab.credit.scoring.migration import forwardPdLadder

        df = forwardPdLadder({}, horizons=(1, 3, 5))
        for row in df.iter_rows(named=True):
            if row["rating"] == "dCR-D":
                continue  # D 자체는 PD=1
            assert row["1yPD"] == 0.0
            assert row["5yPD"] == 0.0

    def test_zero_horizon_returns_zero(self):
        """horizon 0 → PD 0 (현재 시점은 부도 상태가 아니면 PD=0)."""
        from dartlab.credit.scoring.migration import forwardPdLadder

        df = forwardPdLadder(SAMPLE_COUNTS, horizons=(0,))
        for row in df.iter_rows(named=True):
            assert row["0yPD"] == 0.0


# ════════════════════════════════════════
# 실 데이터 호환성 회귀 가드
# ════════════════════════════════════════


class TestRealDataCompatibility:
    """credit.history._updateTransition 가 'dCR-XXX' full prefix 형식으로 누적하므로
    migration 모듈의 default ordering 도 동일 형식이어야 한다 (회귀 가드)."""

    def test_default_ordering_matches_history_format(self):
        from dartlab.credit.scoring.migration import _DEFAULT_RATING_ORDER

        for label in _DEFAULT_RATING_ORDER:
            assert label.startswith("dCR-"), (
                f"'{label}' 가 dCR- prefix 누락. credit.history transition.json 와 mismatch."
            )

    def test_real_grade_format_matched(self):
        """실 dartlab.credit() 가 emit 하는 grade 키와 default ordering 매칭."""
        from dartlab.credit.scoring.migration import buildTransitionMatrix

        # dartlab.credit('005930') 가 실제로 emit 하는 형식
        real_format = {"dCR-AA": {"dCR-AA+": 2, "dCR-AA": 8}}
        df = buildTransitionMatrix(real_format)

        # dCR-AA 행이 정상 매칭됐는지 — 빈 row 가 아니어야
        aa_row = df.filter(df["from_rating"] == "dCR-AA").row(0, named=True)
        assert abs(aa_row["dCR-AA+"] - 0.2) < 1e-9, "dCR-AA → dCR-AA+ 확률 0.2 매칭 실패"
        assert abs(aa_row["dCR-AA"] - 0.8) < 1e-9, "dCR-AA → dCR-AA 확률 0.8 매칭 실패"
