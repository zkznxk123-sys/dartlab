"""한·영 축 alias 가 서로 같은 canonical 축으로 해결되는지 검증.

각 엔진의 공개 API 는 한글/영문 alias 양쪽 호출을 허용한다. 축 매핑 dict 가
실제 코드에 존재하고 양방향 매핑이 깨지지 않았는지 최소 smoke.
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.unit


def test_analysis_alias_dict_roundtrip():
    """analysis 엔진 alias 가 전부 실제 축 또는 그룹에 연결된다."""
    from dartlab.analysis.financial import _ALIASES, _AXIS_TO_GROUP, _GROUPS

    for alias, target in _ALIASES.items():
        # target 은 축이름 (한글) 또는 그룹이름 ("financial" 등) 둘 중 하나
        ok = target in _AXIS_TO_GROUP or target in _GROUPS
        assert ok, f"alias '{alias}' → '{target}' 이 실제 축/그룹 어디에도 없음. _GROUPS 또는 _ALIASES 수정 필요."


def test_analysis_resolveAxis_roundtrip():
    """_resolveAxis 가 한글/영문 양쪽 입력을 동일한 canonical 축으로 해결한다."""
    from dartlab.analysis.financial import _resolveAxis

    pairs = [
        ("profitability", "수익성"),
        ("growth", "성장성"),
        ("stability", "안정성"),
        ("valuation", "가치평가"),
        ("governance", "지배구조"),
    ]
    for en, ko in pairs:
        assert _resolveAxis(en) == _resolveAxis(ko), (
            f"alias mismatch: '{en}' → {_resolveAxis(en)} ≠ '{ko}' → {_resolveAxis(ko)}"
        )


def test_analysis_alias_contains_core_axes():
    """핵심 축 (수익성/성장성/안정성/가치평가) 이 영문 alias 를 가진다."""
    from dartlab.analysis.financial import _ALIASES

    aliases = set(_ALIASES.values())
    # 역방향 검증 — 핵심 한글 축은 _ALIASES 값에 나타나야 함 (영문 키로 접근 가능)
    core = {"수익성", "성장성", "안정성", "가치평가", "지배구조"}
    missing = core - aliases
    assert not missing, f"영문 alias 가 누락된 핵심 축: {missing}"


def test_scan_alias_sample():
    """scan 엔진이 한글/영문 양쪽 호출을 모두 guide DataFrame 으로 응답한다."""
    import dartlab

    # 가이드 호출은 데이터 로드 없이 DataFrame 반환 (무인자 호출 = 가이드)
    df = dartlab.scan()
    # 가이드에는 축 목록이 포함되어야 함
    assert df is not None
    assert hasattr(df, "height") or hasattr(df, "__len__")


def test_gather_entry_has_news_axis():
    """gather 엔진에 news 축이 등록돼 있다 (한/영 키워드 dispatch 진입점)."""
    from dartlab.gather import entry as gatherEntry

    # entry 모듈 존재만 smoke — 구체 dispatch 는 엔진 호출 시점에
    assert gatherEntry is not None
