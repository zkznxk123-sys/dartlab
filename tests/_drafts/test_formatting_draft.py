"""Hypothesis ghostwriter draft — dartlab.core.formatting (시범).

본 SSOT 통합 PR (Phase 2c) — Hypothesis 의 `ghostwriter` 기능 시범 도입.
함수 시그니처 → 자동 fuzz test draft 생성. 사용자가 review 후 정식 위치
(tests/core/) 로 이동.

본 draft 의 weak property: "함수가 임의 입력에 raise 하지 않는다" 만 검증.
*결과 정확성* 검증은 별도 oracle test (수작업) 필요.

생성 명령:
    uv run hypothesis write dartlab.core.formatting > tests/_drafts/test_formatting_draft.py

이동 절차:
    1. 본 draft 를 함수별 oracle test 로 보강 (예: formatComma(1234, 0) == "1,234")
    2. 검증된 case 들을 tests/core/test_formatting.py 신규 생성에 통합
    3. 본 draft 삭제

마커 `pytest.mark.draft` 부착 — CI 의 default unit collection 에서 제외.
한 번 시범 실행: `pytest tests/_drafts/ -m draft`.
"""

import typing

import pytest
from hypothesis import given
from hypothesis import strategies as st

import dartlab.core.formatting

pytestmark = pytest.mark.draft


@given(val=st.from_type(typing.Any), decimals=st.integers(), nullStr=st.text())
def test_fuzz_formatComma(val: typing.Any, decimals: int, nullStr: str) -> None:
    """formatComma 가 임의 입력에 raise 하지 않음 — ghostwriter 자동 생성."""
    dartlab.core.formatting.formatComma(val=val, decimals=decimals, nullStr=nullStr)


@given(
    val=st.from_type(typing.Any),
    decimals=st.integers(),
    suffix=st.text(),
    nullStr=st.text(),
)
def test_fuzz_formatDecimal(val: typing.Any, decimals: int, suffix: str, nullStr: str) -> None:
    """formatDecimal 가 임의 입력에 raise 하지 않음 — ghostwriter 자동 생성."""
    dartlab.core.formatting.formatDecimal(val=val, decimals=decimals, suffix=suffix, nullStr=nullStr)


@given(val=st.from_type(typing.Any), withWon=st.booleans(), nullStr=st.text())
def test_fuzz_formatKr(val: typing.Any, withWon: bool, nullStr: str) -> None:
    """formatKr 가 임의 입력에 raise 하지 않음 — ghostwriter 자동 생성."""
    dartlab.core.formatting.formatKr(val=val, withWon=withWon, nullStr=nullStr)
