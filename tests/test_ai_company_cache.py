"""companyCache 단위 테스트 — Company() 는 mock 으로 대체해 외부 데이터 의존 없이."""

from __future__ import annotations

import threading
from unittest.mock import patch

import pytest

pytestmark = pytest.mark.unit


class _FakeCompany:
    """가짜 Company — 생성 횟수만 추적."""

    _count = 0

    def __init__(self, stockCode: str) -> None:
        self.stockCode = stockCode
        type(self)._count += 1
        self.seq = type(self)._count


@pytest.fixture(autouse=True)
def _resetFakeCount():
    _FakeCompany._count = 0
    yield


def _patchCompany():
    # dartlab.Company 를 _FakeCompany 로 대체
    import dartlab

    return patch.object(dartlab, "Company", _FakeCompany)


def test_noCtx_createsFreshInstanceEachCall():
    from dartlab.ai.runtime.companyCache import getOrCreateCompany, peekCache

    assert peekCache() is None
    with _patchCompany():
        a = getOrCreateCompany("005930")
        b = getOrCreateCompany("005930")
    # ctx 없으면 캐시 미사용 → 매번 새 인스턴스
    assert a is not b
    assert a.seq == 1
    assert b.seq == 2


def test_withCtx_sameStockCodeReturnsSameInstance():
    from dartlab.ai.runtime.companyCache import beginRequest, endRequest, getOrCreateCompany

    d = beginRequest()
    try:
        with _patchCompany():
            a = getOrCreateCompany("005930")
            b = getOrCreateCompany("005930")  # 같은 ctx, 같은 stockCode
            c = getOrCreateCompany("005930")
        assert a is b is c
        assert _FakeCompany._count == 1, "Company 는 한 번만 생성돼야 한다"
    finally:
        endRequest(d)


def test_withCtx_differentStockCodesCreateDifferentInstances():
    from dartlab.ai.runtime.companyCache import beginRequest, endRequest, getOrCreateCompany

    d = beginRequest()
    try:
        with _patchCompany():
            a = getOrCreateCompany("005930")
            b = getOrCreateCompany("000660")
        assert a is not b
        assert a.stockCode == "005930"
        assert b.stockCode == "000660"
        assert _FakeCompany._count == 2
    finally:
        endRequest(d)


def test_endRequestClearsCacheAndRemovesCtx():
    from dartlab.ai.runtime.companyCache import beginRequest, endRequest, getOrCreateCompany, peekCache

    d = beginRequest()
    with _patchCompany():
        getOrCreateCompany("005930")
    assert len(d) == 1
    endRequest(d)
    assert peekCache() is None, "endRequest 후 ctx 해제"
    assert len(d) == 0, "dict 비워짐"


def test_stockCodeNormalization():
    """공백 · 소문자 ticker · 숫자 패딩 모두 같은 key 로 정규화."""
    from dartlab.ai.runtime.companyCache import beginRequest, endRequest, getOrCreateCompany

    d = beginRequest()
    try:
        with _patchCompany():
            a = getOrCreateCompany("5930")  # 4자리 숫자 → 005930
            b = getOrCreateCompany(" 005930 ")  # 공백
            c = getOrCreateCompany("005930")
        assert a is b is c
        assert _FakeCompany._count == 1
    finally:
        endRequest(d)


def test_concurrentRequestsIsolated():
    """두 request 가 동시에 돌 때 각자의 cache 에만 접근 (ContextVar 격리)."""
    import contextvars

    from dartlab.ai.runtime.companyCache import beginRequest, endRequest, getOrCreateCompany

    results_a: list = []
    results_b: list = []
    barrier = threading.Barrier(2)

    def _worker(stockCode: str, bucket: list) -> None:
        d = beginRequest()
        try:
            with _patchCompany():
                barrier.wait(timeout=5.0)
                c1 = getOrCreateCompany(stockCode)
                c2 = getOrCreateCompany(stockCode)
            bucket.append((c1, c2))
        finally:
            endRequest(d)

    ctx_a = contextvars.copy_context()
    ctx_b = contextvars.copy_context()
    ta = threading.Thread(target=lambda: ctx_a.run(_worker, "005930", results_a))
    tb = threading.Thread(target=lambda: ctx_b.run(_worker, "000660", results_b))
    ta.start()
    tb.start()
    ta.join(timeout=10.0)
    tb.join(timeout=10.0)

    assert len(results_a) == 1 and len(results_b) == 1
    a_c1, a_c2 = results_a[0]
    b_c1, b_c2 = results_b[0]
    # 각자 ctx 안에서는 재사용
    assert a_c1 is a_c2
    assert b_c1 is b_c2
    # 서로 다른 ctx 간 인스턴스 격리
    assert a_c1 is not b_c1
    assert a_c1.stockCode == "005930"
    assert b_c1.stockCode == "000660"
