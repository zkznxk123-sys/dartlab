"""데이터-독립 baseline 스냅샷 — 얼린 기대 상수 가드 (적대적 검토 HIGH-1).

자매 ``test_ssot_equivalence_*`` 는 production 과 *같은 SSOT·복사 알고리즘* 을 oracle
로 써 co-drift(둘이 같은 방향으로 틀어지면 못 잡음) 약점이 있다. 본 가드는 그 보완 —
**production 알고리즘을 일절 참조하지 않고, 얼린 기대 출력 상수와 직접 비교**한다.

여기 값은 모두 리팩터 전 원본 코드(e6857503f)와 전체 코퍼스 145,873 byte-identical
이 증명된 시점의 출력이다 (옛=현재 격리실행 대조). 핵심 계정·12단계 대표 경로라
정상 매핑 추가에도 불변 — 출력이 바뀌면 그건 회귀 신호다. (혹 표준계정 자체를
의도적으로 바꾸면 그때만 본 상수 갱신.)
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.unit


@pytest.fixture(scope="module")
def _reset():
    from dartlab.core.accounts import release

    release()


# (account_id, account_nm) → 기대 snakeId. 12단계 경로 대표.
_DART_EXPECTED: dict[tuple[str, str], str | None] = {
    ("ifrs-full_Revenue", "매출액"): "sales",  # 사전 직접 hit (nm)
    ("", "자산총계"): "total_assets",  # 사전 직접 hit
    ("", "매출액"): "sales",
    ("", "부채총계"): "total_liabilities",
    ("", "당기순이익"): "net_profit",
    ("", "영업이익"): "operating_profit",
    ("ifrs-full_Assets", ""): "total_assets",  # id 경로
    ("dart_OperatingIncomeLoss", ""): "operating_profit",  # idSynonym
    ("", "현금의 기타유입"): "other_cash_inflows",  # noParen/noSpace 역인덱스
    ("", "현금의기타유입(유출)"): "other_cash_inflows_outflows",
    ("", "매출 액"): "sales",  # 공백 변형
    ("", "당기 순이익"): "net_profit",
    ("", "영업양도로 인한 현금유입액"): "cash_inflows_from_merger_and_acquisition",  # 액 suffix
    ("", "절대없는계정_xyz_999"): None,  # 미매핑
}

_LABEL_EXPECTED: dict[str, str] = {
    "total_assets": "자산총계",
    "sales": "매출액",
    "operating_profit": "영업이익",
    "net_profit": "당기순이익",
    "current_assets": "유동자산",
    "liabilities": "부채총계",
    "operating_cashflow": "영업활동현금흐름",
}

# (tag, stmt) → 기대 DART canonical snakeId (alias·stmtOverride 적용)
_EDGAR_EXPECTED: dict[tuple[str, str], str | None] = {
    ("Revenues", "IS"): "sales",
    ("Assets", "BS"): "assets",
    ("NetIncomeLoss", "IS"): "net_profit",  # stmtOverride IS
    ("NetIncomeLoss", "CF"): "net_income_cf",  # stmtOverride CF (같은 태그 다른 결과)
    ("CashAndCashEquivalentsAtCarryingValue", "BS"): "cash_and_cash_equivalents",
    ("CostOfGoodsSold", "IS"): "cost_of_sales",  # alias
}


def test_dart_baseline(_reset) -> None:
    """DART map() 이 얼린 기대 snakeId 와 정확히 일치 (12단계 경로 박제)."""
    from dartlab.providers.dart.finance.mapper import AccountMapper

    m = AccountMapper.get()
    diffs = {(i, n): (m.map(i, n), exp) for (i, n), exp in _DART_EXPECTED.items() if m.map(i, n) != exp}
    assert not diffs, f"DART baseline drift: {diffs}"


def test_label_baseline(_reset) -> None:
    """koreanLabels 가 얼린 기대 한글명과 일치 (라벨 cascade 박제)."""
    from dartlab.core.accounts import koreanLabels

    kr = koreanLabels()
    diffs = {s: (kr.get(s), exp) for s, exp in _LABEL_EXPECTED.items() if kr.get(s) != exp}
    assert not diffs, f"label baseline drift: {diffs}"


def test_edgar_baseline(_reset) -> None:
    """EdgarMapper.mapToDart 가 얼린 기대 snakeId 와 일치 (stmtOverride·alias 박제)."""
    from dartlab.providers.edgar.finance.mapper import EdgarMapper

    diffs = {
        (t, st): (EdgarMapper.mapToDart(t, st), exp)
        for (t, st), exp in _EDGAR_EXPECTED.items()
        if EdgarMapper.mapToDart(t, st) != exp
    }
    assert not diffs, f"EDGAR baseline drift: {diffs}"
