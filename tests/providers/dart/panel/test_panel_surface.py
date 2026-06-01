"""panel 표면 닫기 mirror — raw 기본 + key optional + search + freq 시그니처 (데이터 0).

``panel.py`` 의 Phase 2 표면: ``__init__`` tag 기본 raw, ``__call__`` key optional + freq, ``search``
메서드. 실데이터 raw/plain 셀 내용은 tests/panel(requires_data) 담당 — 여기선 시그니처·무데이터 동작.
"""

from __future__ import annotations

import inspect

import polars as pl
import pytest

pytestmark = pytest.mark.unit


def test_default_tag_is_raw() -> None:
    """Panel.__init__ tag 기본 = True(raw, 정부 native 태그 보존)."""
    from dartlab.providers.dart.panel import Panel

    assert inspect.signature(Panel.__init__).parameters["tag"].default is True


def test_call_key_optional_and_freq_param() -> None:
    """__call__ key optional(None 기본) + freq 인자 존재."""
    from dartlab.providers.dart.panel import Panel

    params = inspect.signature(Panel.__call__).parameters
    assert params["key"].default is None  # key 없이 전체 격자 호출 가능
    assert "freq" in params


def test_call_no_key_no_override_returns_self() -> None:
    """key 없음 + override 없음 → self (이미 격자). 빈 종목은 빈 self."""
    from dartlab.providers.dart.panel import Panel

    p = Panel("000000nonexistent")
    out = p()
    assert isinstance(out, pl.DataFrame)
    assert out.is_empty()  # artifact 없으니 빈 self


def test_search_method_exists_and_empty_term_none() -> None:
    """search 메서드 존재 + 빈 term → None."""
    from dartlab.providers.dart.panel import Panel

    p = Panel("000000nonexistent")
    assert callable(p.search)
    assert p.search("") is None


def test_search_separate_from_call() -> None:
    """search(본문)와 __call__(이름표)은 별 표면 — 빈 artifact 둘 다 None/빈."""
    from dartlab.providers.dart.panel import Panel

    p = Panel("000000nonexistent")
    assert p.search("anything") is None  # 본문 검색
    assert p("anything") is None  # 이름표 검색


def test_freq_five_statement_mapping() -> None:
    """5표 topic → statement 매핑 (SCE=EF, CIS=IS3)."""
    from dartlab.providers.dart.panel.panel import _FIVE_STMT

    assert _FIVE_STMT == {"IS": "IS2", "CIS": "IS3", "CF": "CF", "BS": "BS", "SCE": "EF"}


def test_freq_no_artifact_returns_none() -> None:
    """freq + 5표 topic 인데 셀 artifact 없으면 None (예외 없음)."""
    from dartlab.providers.dart.panel import Panel

    p = Panel("000000nonexistent")
    assert p("IS", freq="year") is None
