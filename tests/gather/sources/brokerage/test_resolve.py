"""brokerage.resolve 단위 테스트 — 명시코드 추출 (네트워크/corpCode 0)."""

from __future__ import annotations

import pytest

from dartlab.gather.sources.brokerage.resolve import _resolveTicker

pytestmark = pytest.mark.unit


def test_resolve_explicit_code() -> None:
    assert _resolveTicker("삼성전자 (005930/매수) 좋다") == "005930"
    assert _resolveTicker("SK하이닉스 (000660/Not Rated) ...") == "000660"


def test_resolve_none_for_market() -> None:
    # 회사 없는 시황 → None (이름매칭 끔 = corpCode 회피)
    assert _resolveTicker("◆ Daily 시황 6/26 ◆", useNameMatch=False) is None
    assert _resolveTicker("", useNameMatch=False) is None


def test_resolve_foreign_none() -> None:
    # 외국주식(6자리 코드 없음) + 이름매칭 끔 → None
    assert _resolveTicker("릴라이언스 인더스트리 (RELIANCE IN/매수)", useNameMatch=False) is None
