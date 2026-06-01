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


def test_native_stmt_mapping_lowercase() -> None:
    """소문자 5표 → native statement 매핑 (sce=EF, cis=IS3). 소스 = 대소문자."""
    from dartlab.providers.dart.panel.panel import _NATIVE_STMT

    assert _NATIVE_STMT == {"is": "IS2", "cis": "IS3", "cf": "CF", "bs": "BS", "sce": "EF"}


def test_case_dispatch_native_vs_finance() -> None:
    """소문자=native(자급), 대문자=finance(파사드 주입). artifact/주입 없으면 둘 다 None."""
    from dartlab.providers.dart.panel import Panel

    p = Panel("000000nonexistent")
    assert p("is", freq="year") is None  # native — 셀 artifact 없음
    assert p("IS", freq="year") is None  # finance — standalone 주입 없음


def test_freq_not_source_switch() -> None:
    """freq 는 입도일 뿐 — 대문자 IS 는 freq 와 무관히 native 안 부름(소스=대소문자)."""
    import inspect

    from dartlab.providers.dart.panel.panel import Panel

    # __call__ 에 freq 인자는 있지만 native 분기는 _NATIVE_STMT(소문자)로만
    src = inspect.getsource(Panel.__call__)
    assert "_NATIVE_STMT" in src
    assert "readStatement" in src  # native 는 readStatement, freq→readCellWide 버그 제거


# ── native 재무비율 (소문자 ratios) vs finance 비율 (대문자 RATIOS) 디스패치 ──


def test_ratios_lowercase_native(monkeypatch) -> None:
    """소문자 'ratios' → cell.readRatios(native 자급), showFn 미경유 (is/IS 대칭)."""
    import dartlab.providers.dart.panel.cell as C
    from dartlab.providers.dart.panel import Panel

    sentinel = pl.DataFrame({"ratio": ["roe"], "label": ["x"], "2024": [1.0]})
    seen: dict = {}
    monkeypatch.setattr(C, "readRatios", lambda code, **k: (seen.update(code=code), sentinel)[1])

    p = Panel("005930fake")
    p._showFn = lambda *a, **k: pytest.fail("native ratios 는 finance showFn 경유 금지")
    p._strongFn = lambda key: True
    out = p("ratios")
    assert out is sentinel
    assert seen["code"] == "005930fake"


def test_ratios_uppercase_finance() -> None:
    """대문자 'RATIOS' → key='ratios' 치환 후 finance showFn 위임 (기존 동작 보존)."""
    from dartlab.providers.dart.panel import Panel

    p = Panel("005930fake")
    seen: dict = {}

    def _show(key, **k):
        seen["key"] = key
        return pl.DataFrame({"x": [1]})

    p._showFn = _show
    p._strongFn = lambda key: key == "ratios"
    out = p("RATIOS")
    assert seen.get("key") == "ratios"  # 대문자 → 소문자 finance topic
    assert out is not None
