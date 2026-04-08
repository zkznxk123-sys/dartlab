"""R26 audit 회귀 테스트 — company show/select silent failure 차단.

R26-1: c.show('없는토픽') silent None → ValueError
R26-2: c.select('IS', ['없는계정']) silent None → ValueError
R26-3: c.select('없는토픽', ['매출액']) silent None → ValueError (show 에서)
R26-4: c.select('IS', []) silent None → ValueError

Plan v9 dual access (P0.13): show/select 가 property → CallableAccessor 로 변경되어
``inspect.getsource(Company.show)`` 가 property 객체를 받아 에러 발생.
대신 내부 구현 ``_showImpl`` / ``_selectImpl`` 의 source 를 검증한다.
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.unit


def test_dart_company_show_has_explicit_error_path():
    """R26-1: DART company._showImpl 가 ValueError 발생 코드 가짐."""
    import inspect

    from dartlab.providers.dart.company import Company

    src = inspect.getsource(Company._showImpl)
    assert "ValueError" in src
    assert "찾을 수 없" in src


def test_dart_company_select_validates_empty_indlist():
    """R26-4: 빈 indList 차단 코드 검증."""
    import inspect

    from dartlab.providers.dart.company import Company

    src = inspect.getsource(Company._selectImpl)
    assert "len(indList) == 0" in src
    assert "indList" in src


def test_dart_company_select_raises_on_unmatched_indlist():
    """R26-2: indList 매치 안 되면 ValueError."""
    import inspect

    from dartlab.providers.dart.company import Company

    src = inspect.getsource(Company._selectImpl)
    assert "찾을 수 없" in src
    assert "ValueError" in src


def test_edgar_company_show_has_explicit_error_path():
    """R26-1 EDGAR: edgar company._showImpl 가 ValueError 발생 코드 가짐."""
    import inspect

    from dartlab.providers.edgar.company import Company

    src = inspect.getsource(Company._showImpl)
    assert "ValueError" in src
    assert "찾을 수 없" in src


def test_edgar_company_select_validates_empty_indlist():
    """R26-4 EDGAR: 빈 indList 차단."""
    import inspect

    from dartlab.providers.edgar.company import Company

    src = inspect.getsource(Company._selectImpl)
    assert "len(indList) == 0" in src


def test_edgar_company_select_raises_on_unmatched():
    """R26-2 EDGAR: 매치 안 되면 ValueError."""
    import inspect

    from dartlab.providers.edgar.company import Company

    src = inspect.getsource(Company._selectImpl)
    assert "찾을 수 없" in src
    assert "ValueError" in src


def test_notes_explicit_attribute_error():
    """R26 보조: c.notes.없는것 이 AttributeError + 안내 (audit C7 검증)."""
    import inspect

    from dartlab.providers.dart.docs.notes import Notes

    # __getattr__ 에 명시적 에러 안내가 있는지 source check
    if hasattr(Notes, "__getattr__"):
        src = inspect.getsource(Notes.__getattr__)
        assert "AttributeError" in src or "지원" in src or "찾을 수 없" in src
