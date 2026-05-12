"""Gather axis registry contract — registry 메타데이터 vs 실제 dispatch 일관성.

가까운 사고 (2026-04-26): test_gatherAxes.py 가 모든 axis 에 stockCode 일괄 dispatch
하다가 krx axis (column 명 기대) 에서 mismatch. registry 가 axis-별 target 의미를
명시하지 않아 발생.

본 테스트는 axis 추가/변경 시 다음을 강제:

    1. `AXIS_REGISTRY` 모든 entry 의 ``targetType`` 이 유효 enum 값
    2. `API_KEY_INFO` 가 registry 모든 axis 를 커버 (누락 시 _guide 가 "불필요" 로
       잘못 표시)
    3. ``_guide()`` 가 ``hidden=True`` axis 를 노출하지 않음
    4. ``AXIS_ALIASES`` 매핑이 모두 registry 의 정규 키를 가리킴
    5. 모든 entry 의 ``example`` 이 빈 문자열이 아님 + axis 이름 포함

unit marker — 네트워크 호출 없음. ci-fast 에서 검증.
"""

from __future__ import annotations

import inspect
from typing import get_args

import pytest

from dartlab.gather.entry import (
    API_KEY_INFO,
    AXIS_ALIASES,
    AXIS_REGISTRY,
    GatherEntry,
    TargetType,
)

pytestmark = pytest.mark.unit


_VALID_TARGET_TYPES = set(get_args(TargetType))


def test_registryNotEmpty():
    """registry 에 axis 가 최소 1개 이상."""
    assert AXIS_REGISTRY, "AXIS_REGISTRY 가 비어있음 — gather() 진입 불가"


@pytest.mark.parametrize("axis", sorted(AXIS_REGISTRY))
def test_eachAxisTargetTypeIsValid(axis: str):
    """모든 axis 의 targetType 이 TargetType enum 에 속함."""
    entry = AXIS_REGISTRY[axis]
    assert entry.targetType in _VALID_TARGET_TYPES, (
        f"axis '{axis}' 의 targetType='{entry.targetType}' 이 유효하지 않음. 허용: {sorted(_VALID_TARGET_TYPES)}"
    )


@pytest.mark.parametrize("axis", sorted(AXIS_REGISTRY))
def test_eachAxisHasApiKeyInfo(axis: str):
    """`API_KEY_INFO` 가 모든 registry axis 를 커버.

    누락 시 ``_guide()`` 가 기본값 '불필요' 로 잘못 표시 → 사용자가 키 필요한 axis 를
    키 없이 호출했다가 런타임에 발견하는 사고 발생.
    """
    assert axis in API_KEY_INFO, (
        f"axis '{axis}' 가 API_KEY_INFO 에 없음. 키 불필요면 '불필요' 명시, 필요하면 환경변수 이름 + 안내 문자열 등록."
    )


def test_apiKeyInfoNoExtraEntries():
    """`API_KEY_INFO` 에 registry 에 없는 키가 들어있지 않음 — 옛 axis 잔존 차단."""
    extra = set(API_KEY_INFO) - set(AXIS_REGISTRY)
    assert not extra, f"API_KEY_INFO 에 registry 에 없는 axis 잔존: {sorted(extra)}"


@pytest.mark.parametrize("axis", sorted(AXIS_REGISTRY))
def test_eachAxisFieldsNonEmpty(axis: str):
    """label/description/example 가 비어있지 않음."""
    entry = AXIS_REGISTRY[axis]
    assert entry.label.strip(), f"axis '{axis}' 의 label 이 비어있음"
    assert entry.description.strip(), f"axis '{axis}' 의 description 이 비어있음"
    assert entry.example.strip(), f"axis '{axis}' 의 example 이 비어있음"


@pytest.mark.parametrize("axis", sorted(AXIS_REGISTRY))
def test_eachAxisExampleMentionsAxisName(axis: str):
    """example 문자열이 자기 axis 이름과 strict 일치 — 복사붙여넣기 실수 + alias 차단.

    consistency_no_alias 원칙: registry key 와 example 의 axis 이름이 대소문자
    포함 100% 일치해야 한다. ``krxindex`` registry 인데 example 이 ``krxIndex`` 면
    같은 것을 두 이름으로 부르는 alias — 사용자가 어느 것이 정식인지 헷갈린다.
    """
    entry = AXIS_REGISTRY[axis]
    assert axis in entry.example, (
        f"axis '{axis}' 의 example 이 정식 이름과 strict 일치 안 됨 (대소문자 포함): {entry.example!r}"
    )


def test_aliasesPointToValidAxes():
    """`AXIS_ALIASES` 의 모든 값이 registry 정규 키."""
    invalid = {alias: target for alias, target in AXIS_ALIASES.items() if target not in AXIS_REGISTRY}
    assert not invalid, f"AXIS_ALIASES 가 미등록 axis 를 가리킴: {invalid}"


def test_guideExcludesHiddenAxes():
    """`_guide()` 출력이 ``hidden=True`` axis 를 노출하지 않음."""
    g = GatherEntry()
    df = g._guide()
    visible = set(df["axis"].to_list())
    hidden = {key for key, entry in AXIS_REGISTRY.items() if entry.hidden}
    leaked = visible & hidden
    assert not leaked, f"_guide() 가 hidden axis 를 노출: {leaked}"


def test_guideHasAllVisibleAxes():
    """`_guide()` 가 모든 ``hidden=False`` axis 를 포함."""
    g = GatherEntry()
    df = g._guide()
    visible_in_guide = set(df["axis"].to_list())
    visible_in_registry = {key for key, entry in AXIS_REGISTRY.items() if not entry.hidden}
    missing = visible_in_registry - visible_in_guide
    assert not missing, f"_guide() 가 visible axis 누락: {missing}"


def test_targetRequiredFalseAxesHaveOptionalTargetType():
    """``targetRequired=False`` axis 의 targetType 이 'stockCode' 가 아님 — 모순 차단.

    targetRequired=False 인데 targetType='stockCode' 이면 "선택" 의미가 모호해진다
    (종목코드는 본질적으로 필수). macro/krx/krxindex 처럼 indicator/columnName/none
    등이어야 한다.
    """
    contradictions = []
    for axis, entry in AXIS_REGISTRY.items():
        if not entry.targetRequired and entry.targetType == "stockCode":
            contradictions.append(axis)
    assert not contradictions, (
        f"targetRequired=False 인데 targetType='stockCode' 인 axis: {contradictions}. "
        f"종목코드 선택 axis 는 의미가 모호 — indicator/columnName/none 중 하나로 변경."
    )


def test_callableAcceptsKnownAxes():
    """``__call__`` signature 검증 — axis/target/**kwargs 패턴."""
    sig = inspect.signature(GatherEntry.__call__)
    params = list(sig.parameters)
    # self, axis, target, **kwargs
    assert "axis" in params
    assert "target" in params
