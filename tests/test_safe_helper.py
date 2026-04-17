"""Phase 16 B4 — safe.py SSOT 회귀 가드."""

from __future__ import annotations

import pytest


@pytest.mark.unit
def test_get_value():
    from dartlab.core.finance.safe import get

    assert get({"2024": 100}, "2024") == 100


@pytest.mark.unit
def test_get_none():
    from dartlab.core.finance.safe import get

    assert get({"2024": None}, "2024") == 0
    assert get({"2024": None}, "2024", default=-1) == -1


@pytest.mark.unit
def test_get_missing_key():
    from dartlab.core.finance.safe import get

    assert get({}, "missing") == 0


@pytest.mark.unit
def test_get_none_row():
    from dartlab.core.finance.safe import get

    assert get(None, "key") == 0


@pytest.mark.unit
def test_get_first():
    from dartlab.core.finance.safe import getFirst

    data = {"매출액": {"2024": 1000}, "매출": {"2024": None}}
    assert getFirst(data, ["매출", "매출액"], "2024") == 1000


@pytest.mark.unit
def test_get_first_all_empty():
    from dartlab.core.finance.safe import getFirst

    assert getFirst({}, ["a", "b"], "2024") == 0
    assert getFirst({"a": None}, ["a"], "2024") == 0


@pytest.mark.unit
def test_yoy_positive():
    from dartlab.core.finance.safe import yoy

    assert yoy(110, 100) == 10.0
    assert yoy(200, 100) == 100.0


@pytest.mark.unit
def test_yoy_negative():
    from dartlab.core.finance.safe import yoy

    assert yoy(90, 100) == -10.0


@pytest.mark.unit
def test_yoy_none_or_zero():
    from dartlab.core.finance.safe import yoy

    assert yoy(100, 0) is None
    assert yoy(None, 100) is None
    assert yoy(100, None) is None


@pytest.mark.unit
def test_no_duplicate_get_in_analysis():
    """B2 sentinel: analysis/financial 에서 _get/_getF* 정의 0건."""
    import os
    import subprocess

    os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    # grep "def _get" or "def _getF[0-9]*" in analysis/financial 루트 .py 만
    result = subprocess.run(
        ["grep", "-rE", r"^def _get(\b|F[0-9]*\b)", "src/dartlab/analysis/financial/"],
        capture_output=True,
        text=True,
    )
    # 통합 완료 후 0건 — B2 끝나면 activate
    # 현재는 informational (assert 없음). B2 완료 후 assert 추가.
    print(f"_get/_getF* 정의 수: {len(result.stdout.splitlines())}")
