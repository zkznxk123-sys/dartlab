"""panel cross (회사간/세계마켓간) mirror — guard 경로 + index 부재 (데이터 0).

``providers/dart/panel/cross.py`` 의 1:1 mirror. disclosureKey 빈 값/빈 입력 guard 와
_index 부재 시 None 을 검증 (providers ↛ gather: 경로는 config 직접 read). 실규모 cross
정렬은 tests/panel/test_cross_index.py (requires_data) 담당.
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.unit


def test_cross_company_empty_key_returns_none() -> None:
    """disclosureKey 빈 값 → None (guard)."""
    from dartlab.providers.dart.panel import crossCompany

    assert crossCompany(disclosureKey="") is None


def test_cross_market_empty_input_returns_none() -> None:
    """빈 codesByMarket → None."""
    from dartlab.providers.dart.panel import crossMarket

    assert crossMarket({}, "inventoryDisclosure") is None


def test_index_codes_for_none_when_index_absent() -> None:
    """_index 부재(가짜 disclosureKey) → _indexCodesFor None (caller fallback)."""
    from dartlab.providers.dart.panel.cross import _indexCodesFor

    # 실제 _index 가 있어도 이 키는 없을 것 → None 또는 빈 list 가 아닌 정상 동작.
    out = _indexCodesFor("__nonexistent_disclosure_key__", "kr")
    assert out is None or out == []
