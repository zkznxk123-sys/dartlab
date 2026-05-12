"""dartlab.gather.mixins.context mirror 슬롯 — smoke import (G+ P-Q3).

룰 7 (src↔tests 1:1 mirror) 만족용 placeholder. 본격 단위 테스트는 후속.
"""

from __future__ import annotations

import importlib

import pytest

pytestmark = pytest.mark.unit


def test_smoke_import() -> None:
    """``dartlab.gather.mixins.context`` 모듈 import 가능 — 모듈 구조 회귀 차단."""
    importlib.import_module("dartlab.gather.mixins.context")


def test_protocol_attribute_names() -> None:
    """GatherMixinContext Protocol 의 명시 attribute 3 개 — runtime 노출 확인."""
    from dartlab.gather.mixins.context import GatherMixinContext

    annotations = getattr(GatherMixinContext, "__annotations__", {})
    assert "_client" in annotations, "GatherMixinContext._client 누락"
    assert "_cache" in annotations, "GatherMixinContext._cache 누락"
    assert "_owns_client" in annotations, "GatherMixinContext._owns_client 누락"


def test_5_mixins_inherit_protocol() -> None:
    """5 mixin 모두 GatherMixinContext 를 MRO 에 포함 — typing 분석 일관성."""
    from dartlab.gather.mixins.collect import _GatherCollectMixin
    from dartlab.gather.mixins.context import GatherMixinContext
    from dartlab.gather.mixins.info import _GatherInfoMixin
    from dartlab.gather.mixins.macro import _GatherMacroMixin
    from dartlab.gather.mixins.news import _GatherNewsMixin
    from dartlab.gather.mixins.price import _GatherPriceMixin

    for mixin in (
        _GatherPriceMixin,
        _GatherInfoMixin,
        _GatherNewsMixin,
        _GatherMacroMixin,
        _GatherCollectMixin,
    ):
        assert GatherMixinContext in mixin.__mro__, (
            f"{mixin.__name__} 가 GatherMixinContext 미상속 — Protocol 명시 회귀."
        )
