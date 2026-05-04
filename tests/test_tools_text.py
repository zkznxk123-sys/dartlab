"""text helper 레거시는 read/search/verify canonical tools로 대체된다."""

from __future__ import annotations

import importlib.util

import pytest

pytestmark = pytest.mark.unit


def test_legacy_text_helper_module_is_removed():
    assert importlib.util.find_spec("dartlab.ai.tools.text") is None


def test_verify_answer_is_the_text_claim_gate():
    from dartlab.ai.tools.verifyAnswer import verifyAnswer

    result = verifyAnswer("가능한 기능을 확인했습니다.", refs=[])

    assert result.ok is True
    assert result.refs[0].kind == "verifyRef"
