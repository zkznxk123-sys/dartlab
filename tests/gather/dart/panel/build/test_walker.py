"""panel walker mirror — 공개 심볼 + schema era 감지 (데이터 0).

``gather/dart/panel/build/walker.py`` 의 1:1 mirror. walkSections/detectSchemaEra 공개표면
존재 + 최소 lxml 문서에서 detectSchemaEra 가 예외 없이 동작하는지 검증 (손실0/dup0 전수
검증은 tests/panel/test_build_lossless.py 의 source 경로가 walkSections 를 직접 사용).
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.unit


def test_walker_public_symbols_callable() -> None:
    """walkSections / detectSchemaEra 공개표면 존재 + callable."""
    from dartlab.gather.dart.panel.build import detectSchemaEra, walkSections

    assert callable(walkSections)
    assert callable(detectSchemaEra)


def test_detect_schema_era_on_minimal_doc() -> None:
    """최소 lxml 문서에서 detectSchemaEra 가 예외 없이 era 값을 반환."""
    from lxml import etree

    from dartlab.gather.dart.panel.build import detectSchemaEra

    root = etree.fromstring(b"<DOCUMENT><BODY></BODY></DOCUMENT>")
    era = detectSchemaEra(root)
    assert era is not None
