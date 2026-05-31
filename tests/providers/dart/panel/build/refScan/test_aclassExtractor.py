"""aclassExtractor mirror — 공개 심볼 import-smoke (데이터 0).

``gather/dart/panel/build/refScan/aclassExtractor.py`` 의 1:1 mirror. TABLE-GROUP ACLASS
추출 함수가 공개표면에 존재·callable 인지 확인 (실 추출은 zip XML 입력 → ref 생산 경로에서
검증). lxml import 회귀 가드.
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.unit


def test_aclass_extractor_symbols_callable() -> None:
    """extractAclassEntries / iterTableGroups 공개표면 존재 + callable."""
    from dartlab.providers.dart.panel.build.refScan import extractAclassEntries, iterTableGroups

    assert callable(extractAclassEntries)
    assert callable(iterTableGroups)
