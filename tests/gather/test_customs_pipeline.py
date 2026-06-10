"""관세청 customs 풀파이프라인 배선 회귀 (네트워크 없음).

producer(buildCustoms)·소비(dataConfig/macroHf)·매핑(productIndicators) 연결이
조용히 끊기지 않도록 잠근다.
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.unit


def test_productIndicators_customs_mapping(monkeypatch: pytest.MonkeyPatch) -> None:
    import dartlab.gather.mapping.productIndicators as pi

    # 반도체 키워드 → customs HS 8542·8541
    assert pi.PRODUCT_INDICATOR_MAP["반도체"].get("customs") == ["8542", "8541"]
    assert pi.PRODUCT_INDICATOR_MAP["자동차"].get("customs") == ["8703", "8708"]

    monkeypatch.setattr(pi, "_getProductText", lambda code: "반도체 메모리 DRAM")
    inds = pi.getProductIndicators("005930")
    customs = [i["seriesId"] for i in inds if i["source"] == "customs"]
    assert "8542" in customs and "8541" in customs


def test_macroHf_customs_category() -> None:
    from dartlab.gather.bulkData.macroHf import _SOURCE_TO_CATEGORY, _category

    assert _category("customs") == "macroCustoms"
    assert _SOURCE_TO_CATEGORY["customs"] == "macroCustoms"


def test_dataConfig_macroCustoms_registered() -> None:
    import dartlab.core.dataConfig as dc

    cats = [v for v in vars(dc).values() if isinstance(v, dict) and "macroFred" in v]
    assert cats, "dataConfig 카테고리 dict 미발견"
    assert cats[0]["macroCustoms"]["dir"] == "macro/customs"
    assert cats[0]["macroCustoms"]["public"] is True
