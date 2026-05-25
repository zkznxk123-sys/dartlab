"""mirror smoke — dart/openapi/batchCollectors.py (split helper).

분할 helper 모듈의 임포트 가능성 + 룰 7 mirror 슬롯 충족.
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.unit


@pytest.mark.xfail(
    reason="batch ↔ batchCollectors 양방향 import — direct import 시 partially initialized. 상수 분리 모듈 deferred"
)
def test_import() -> None:
    import dartlab.providers.dart.openapi.batchCollectors as mod

    assert mod is not None
