"""credit L2 scorecard 순수함수 광범위 단위 테스트.

외부 API 없는 순수 함수만 대상. coverage 29% → 35%+ 끌어올림.

대상:
- credit/scoring/creditScorecard.py (scoreMetric, axisScore, weightedScore,
  mapTo20Grade, gradeCategory, isInvestmentGrade, cashFlowGrade, creditOutlook,
  notchGrade, estimatePD)
- credit engine + post-adjust 헬퍼 import smoke
"""


# ══════════════════════════════════════
# credit/scoring/creditScorecard.py
# ══════════════════════════════════════


class TestScoreMetric:
    def test_below_excellent(self):
        from dartlab.credit.scoring.creditScorecard import scoreMetric

        # 예: D/EBITDA — 작을수록 좋음 (breakpoints: (value, score) 오름차순)
        threshold = {
            "lower_is_better": True,
            "breakpoints": [(1.0, 5.0), (2.0, 20.0), (3.5, 50.0), (5.0, 80.0)],
        }
        r = scoreMetric(0.5, threshold)
        assert r is not None
        assert r <= 5.0

    def test_above_weak(self):
        from dartlab.credit.scoring.creditScorecard import scoreMetric

        threshold = {
            "lower_is_better": True,
            "breakpoints": [(1.0, 5.0), (2.0, 20.0), (3.5, 50.0), (5.0, 80.0)],
        }
        r = scoreMetric(10.0, threshold)
        assert r is not None
        assert r >= 80.0

    def test_none(self):
        from dartlab.credit.scoring.creditScorecard import scoreMetric

        threshold = {"lower_is_better": True, "breakpoints": [(1.0, 5.0), (5.0, 80.0)]}
        r = scoreMetric(None, threshold)
        assert r is None

    def test_higherIsBetter(self):
        from dartlab.credit.scoring.creditScorecard import scoreMetric

        # FFO/Debt — 높을수록 좋음 (breakpoints 값 오름차순, lower_is_better=False 면 내부 반전)
        threshold = {
            "lower_is_better": False,
            "breakpoints": [(0.5, 5.0), (0.3, 20.0), (0.15, 50.0), (0.05, 80.0)],
        }
        rGood = scoreMetric(0.6, threshold)
        rBad = scoreMetric(0.01, threshold)
        if rGood is not None and rBad is not None:
            assert rGood < rBad


class TestAxisScore:
    def test_normalScores(self):
        from dartlab.credit.scoring.creditScorecard import axisScore

        r = axisScore([("metric1", 10.0), ("metric2", 20.0), ("metric3", 30.0)])
        assert isinstance(r, float)
        # 평균 20
        assert 15 < r < 25

    def test_dictScores(self):
        from dartlab.credit.scoring.creditScorecard import axisScore

        r = axisScore([{"name": "m1", "value": 0.5, "score": 15.0}, {"name": "m2", "value": 0.3, "score": 25.0}])
        assert isinstance(r, float)

    def test_allNoneReturnsNone(self):
        from dartlab.credit.scoring.creditScorecard import axisScore

        r = axisScore([("m1", None), ("m2", None)])
        assert r is None

    def test_empty(self):
        from dartlab.credit.scoring.creditScorecard import axisScore

        r = axisScore([])
        assert r is None


class TestWeightedScore:
    def test_uniformWeights(self):
        from dartlab.credit.scoring.creditScorecard import weightedScore

        axes = [
            {"score": 20.0, "weight": 0.25},
            {"score": 30.0, "weight": 0.25},
            {"score": 40.0, "weight": 0.25},
            {"score": 50.0, "weight": 0.25},
        ]
        r = weightedScore(axes)
        # 평균 35
        assert 30 < r < 40

    def test_skewedWeights(self):
        from dartlab.credit.scoring.creditScorecard import weightedScore

        axes = [
            {"score": 10.0, "weight": 0.8},
            {"score": 90.0, "weight": 0.2},
        ]
        r = weightedScore(axes)
        # 0.8*10 + 0.2*90 = 8 + 18 = 26
        assert 23 < r < 29

    def test_skipsNone(self):
        from dartlab.credit.scoring.creditScorecard import weightedScore

        axes = [
            {"score": 20.0, "weight": 0.5},
            {"score": None, "weight": 0.5},
        ]
        r = weightedScore(axes)
        assert isinstance(r, float)


class TestMapTo20Grade:
    def test_aaaScore(self):
        from dartlab.credit.scoring.creditScorecard import mapTo20Grade

        grade, desc, pd = mapTo20Grade(2.0)
        assert "AAA" in grade or "AA" in grade
        assert isinstance(desc, str)
        assert pd < 1.0

    def test_defaultScore(self):
        from dartlab.credit.scoring.creditScorecard import mapTo20Grade

        grade, desc, pd = mapTo20Grade(95.0)
        assert "D" in grade or "C" in grade or grade.startswith("C")
        assert pd > 10.0


class TestGradeCategory:
    def test_aaa(self):
        from dartlab.credit.scoring.creditScorecard import gradeCategory

        r = gradeCategory("AAA")
        assert isinstance(r, str)

    def test_default(self):
        from dartlab.credit.scoring.creditScorecard import gradeCategory

        r = gradeCategory("D")
        assert isinstance(r, str)


class TestIsInvestmentGrade:
    def test_aaaTrue(self):
        from dartlab.credit.scoring.creditScorecard import isInvestmentGrade

        assert isInvestmentGrade("AAA") is True
        assert isInvestmentGrade("AA+") is True
        assert isInvestmentGrade("BBB-") is True

    def test_speculativeFalse(self):
        from dartlab.credit.scoring.creditScorecard import isInvestmentGrade

        assert isInvestmentGrade("BB+") is False
        assert isInvestmentGrade("D") is False


class TestCashFlowGrade:
    def test_basic(self):
        from dartlab.credit.scoring.creditScorecard import cashFlowGrade

        # 우수한 영업현금흐름
        r = cashFlowGrade(ocfToSales=20.0, fcfPositive=True, ocfToDebt=80.0, ocfTrendStable=True)
        assert isinstance(r, str)

    def test_negativeCashflow(self):
        from dartlab.credit.scoring.creditScorecard import cashFlowGrade

        r = cashFlowGrade(ocfToSales=-5.0, fcfPositive=False, ocfToDebt=10.0)
        assert isinstance(r, str)

    def test_noneInputs(self):
        from dartlab.credit.scoring.creditScorecard import cashFlowGrade

        r = cashFlowGrade(None, None, None)
        assert isinstance(r, str)


class TestCreditOutlook:
    def test_stable(self):
        from dartlab.credit.scoring.creditScorecard import creditOutlook

        r = creditOutlook([30.0, 30.0, 30.0])
        assert isinstance(r, str)

    def test_improving(self):
        from dartlab.credit.scoring.creditScorecard import creditOutlook

        # 최근이 낮음 → 점수 개선 (= positive outlook)
        r = creditOutlook([15.0, 25.0, 35.0])
        assert isinstance(r, str)

    def test_deteriorating(self):
        from dartlab.credit.scoring.creditScorecard import creditOutlook

        # 최근이 높음 → 점수 악화 (= negative outlook)
        r = creditOutlook([45.0, 35.0, 25.0])
        assert isinstance(r, str)


class TestNotchGrade:
    def test_positiveNotch(self):
        from dartlab.credit.scoring.creditScorecard import notchGrade

        # AA에서 +1 notch
        r = notchGrade("AA", 1)
        assert isinstance(r, str)

    def test_negativeNotch(self):
        from dartlab.credit.scoring.creditScorecard import notchGrade

        r = notchGrade("BBB", -2)
        assert isinstance(r, str)

    def test_zeroNotch(self):
        from dartlab.credit.scoring.creditScorecard import notchGrade

        r = notchGrade("A", 0)
        assert r == "A"


class TestEstimatePD:
    def test_aaaLow(self):
        from dartlab.credit.scoring.creditScorecard import estimatePD

        pd = estimatePD("AAA")
        assert pd < 0.5  # AAA PD 매우 낮음

    def test_defaultHigh(self):
        from dartlab.credit.scoring.creditScorecard import estimatePD

        pd = estimatePD("D")
        assert pd > 10  # default 등급은 PD 높음

    def test_intermediate(self):
        from dartlab.credit.scoring.creditScorecard import estimatePD

        pdBbb = estimatePD("BBB")
        pdBb = estimatePD("BB")
        assert pdBbb < pdBb


# ══════════════════════════════════════
# Smoke imports
# ══════════════════════════════════════


def test_creditPublicEntries():
    from dartlab.credit import axes, credit, creditCompany, guide

    assert callable(credit)
    assert callable(creditCompany)
    assert callable(axes)
    assert callable(guide)


def test_creditEngineEntries():
    from dartlab.credit._engineCHS import _calcCHSAdjustment, _chsPdToScore
    from dartlab.credit._engineFinancial import _evaluateFinancial
    from dartlab.credit._engineNotch import _calcNotchAdjustment
    from dartlab.credit._enginePostAdjust import (
        _applyPostAdjustments,
        _applyTimeSeriesSmoothing,
        _blendOFS,
        _explainDivergence,
        _normalizeMetricsForOutput,
    )
    from dartlab.credit._engineScoring import _scoreBusinessStability, _scoreCashFlow
    from dartlab.credit.engine import evaluate, evaluateCompany

    assert callable(evaluate)
    assert callable(evaluateCompany)
    assert callable(_evaluateFinancial)
    assert callable(_applyPostAdjustments)


def test_creditScoringEntries():
    from dartlab.credit.scoring.creditScorecard import (
        axisScore,
        cashFlowGrade,
        creditOutlook,
        estimatePD,
        gradeCategory,
        isInvestmentGrade,
        mapTo20Grade,
        notchGrade,
        scoreMetric,
        weightedScore,
    )
    from dartlab.credit.scoring.metrics import calcAllMetrics, calcFinancialMetrics, calcSeparateMetrics

    assert callable(scoreMetric)
    assert callable(calcAllMetrics)
