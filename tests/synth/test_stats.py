"""synth/stats.py 단위 테스트 — zscore · winsorize · percentileRank · rolling.

L1.5 통계 primitive SSOT 회귀 차단.
"""

from __future__ import annotations

import math

import numpy as np
import pytest

from dartlab.synth.stats import (
    normalize,
    percentileRank,
    rollingMean,
    rollingStd,
    rollingZScore,
    winsorize,
    zscore,
)


class TestZscore:
    def test_basic(self) -> None:
        out = zscore([1.0, 2.0, 3.0, 4.0, 5.0])
        # mean=3, std(ddof=1)≈1.5811 → (-1.265, -0.632, 0, 0.632, 1.265)
        assert abs(float(out[2])) < 1e-9
        assert abs(out[-1] - 1.2649110640673518) < 1e-9
        assert abs(out[0] + 1.2649110640673518) < 1e-9

    def test_empty(self) -> None:
        out = zscore([])
        assert out.size == 0

    def test_zero_std(self) -> None:
        out = zscore([5.0, 5.0, 5.0])
        assert np.all(out == 0.0)

    def test_with_nan(self) -> None:
        out = zscore([1.0, np.nan, 3.0])
        # mean(2), std≈1.414 → -0.707, NaN, 0.707
        assert math.isnan(float(out[1]))
        assert abs(out[0] + 0.7071067811865475) < 1e-9


class TestWinsorize:
    def test_basic(self) -> None:
        out = winsorize([1.0, 2.0, 3.0, 4.0, 100.0], lower=0.0, upper=0.8)
        # numpy linear interpolation: 0.8 분위 = 23.2 → 100 → 23.2 로 clip
        assert float(out[-1]) < 100.0
        assert float(out[-1]) == pytest.approx(23.2, abs=0.5)
        # 1.0 은 변경 없음
        assert float(out[0]) == 1.0

    def test_extreme_clip(self) -> None:
        # lower=0.2, upper=0.8 → 양 극단 모두 cap
        out = winsorize([1.0, 2.0, 3.0, 4.0, 5.0], lower=0.2, upper=0.8)
        # 0.2 분위=1.8, 0.8 분위=4.2 → 1 → 1.8, 5 → 4.2
        assert float(out[0]) == pytest.approx(1.8, abs=0.1)
        assert float(out[-1]) == pytest.approx(4.2, abs=0.1)

    def test_invalid_bounds(self) -> None:
        with pytest.raises(ValueError):
            winsorize([1.0, 2.0], lower=0.6, upper=0.4)

    def test_empty(self) -> None:
        out = winsorize([])
        assert out.size == 0


class TestPercentileRank:
    def test_target(self) -> None:
        assert percentileRank([10, 20, 30, 40, 50], target=25) == 0.4
        assert percentileRank([10, 20, 30, 40, 50], target=60) == 1.0
        assert percentileRank([10, 20, 30, 40, 50], target=5) == 0.0

    def test_array_mode(self) -> None:
        out = percentileRank([10, 20, 30, 40, 50])
        assert isinstance(out, np.ndarray)
        assert out.tolist() == [0.2, 0.4, 0.6, 0.8, 1.0]

    def test_empty(self) -> None:
        assert math.isnan(percentileRank([], target=1.0))


class TestRolling:
    def test_rolling_mean_basic(self) -> None:
        out = rollingMean([1.0, 2.0, 3.0, 4.0], period=2)
        # NaN, 1.5, 2.5, 3.5
        assert math.isnan(float(out[0]))
        assert out[1] == 1.5
        assert out[3] == 3.5

    def test_rolling_std_basic(self) -> None:
        out = rollingStd([1.0, 2.0, 3.0, 4.0, 5.0], period=3)
        # NaN, NaN, std(1,2,3)=1.0, std(2,3,4)=1.0, std(3,4,5)=1.0
        assert math.isnan(float(out[0]))
        assert math.isnan(float(out[1]))
        assert abs(out[2] - 1.0) < 1e-9

    def test_rolling_zscore_zero_std(self) -> None:
        out = rollingZScore([5.0, 5.0, 5.0, 5.0], period=2)
        # 모든 윈도우 std=0 → z=0
        assert math.isnan(float(out[0]))
        assert out[1] == 0.0
        assert out[3] == 0.0

    def test_invalid_period(self) -> None:
        with pytest.raises(ValueError):
            rollingMean([1.0, 2.0], period=0)
        with pytest.raises(ValueError):
            rollingStd([1.0, 2.0], period=1)


class TestNormalize:
    def test_zscore_method(self) -> None:
        out = normalize([1.0, 2.0, 3.0], method="zscore")
        assert abs(float(out[1])) < 1e-9

    def test_minmax_method(self) -> None:
        out = normalize([10.0, 20.0, 30.0], method="minmax")
        assert out.tolist() == [0.0, 0.5, 1.0]

    def test_rank_method(self) -> None:
        out = normalize([100, 200, 300], method="rank")
        assert out.tolist() == [pytest.approx(1.0 / 3), pytest.approx(2.0 / 3), pytest.approx(1.0)]

    def test_invalid_method(self) -> None:
        with pytest.raises(ValueError):
            normalize([1.0, 2.0], method="bogus")

    def test_minmax_constant(self) -> None:
        out = normalize([5.0, 5.0, 5.0], method="minmax")
        assert np.all(out == 0.0)
