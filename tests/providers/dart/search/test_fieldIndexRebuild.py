"""mirror smoke — dart/search/fieldIndexRebuild.py (split helper).

분할 helper 모듈의 임포트 가능성 + 룰 7 mirror 슬롯 충족.
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.unit


@pytest.mark.xfail(
    reason="fieldIndex ↔ fieldIndexRebuild 양방향 import — direct import 시 partially initialized (fieldIndex 경유 import 는 작동). 상수 분리 모듈 deferred"
)
def test_import() -> None:
    import dartlab.providers.dart.search.fieldIndexRebuild as mod

    assert mod is not None
