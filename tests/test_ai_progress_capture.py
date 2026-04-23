"""progressCapture 모듈 단위 테스트."""

from __future__ import annotations

import io
import logging
import queue
import threading

import pytest

pytestmark = pytest.mark.unit


def test_dispatching_stream_routes_to_queue_and_original():
    from dartlab.ai.runtime.progressCapture import DispatchingStream, _progressCtx

    orig = io.StringIO()
    ds = DispatchingStream(orig)
    q1: queue.Queue = queue.Queue(maxsize=100)
    token = _progressCtx.set(q1)
    try:
        ds.write("line 1\nline 2\npartial")
    finally:
        _progressCtx.reset(token)

    # 원본 stream 에는 전체 그대로 흐름
    assert orig.getvalue() == "line 1\nline 2\npartial"
    # queue 에는 newline 으로 끊긴 2줄만 (partial 은 내부 buffer 에 남음)
    assert q1.get_nowait() == "line 1"
    assert q1.get_nowait() == "line 2"
    with pytest.raises(queue.Empty):
        q1.get_nowait()


def test_dispatching_stream_noop_without_ctx():
    from dartlab.ai.runtime.progressCapture import DispatchingStream, _progressCtx

    # caller 에 ctx 없음
    assert _progressCtx.get() is None
    orig = io.StringIO()
    ds = DispatchingStream(orig)
    ds.write("hello\nworld\n")
    # 원본엔 흐르고, queue 에 enqueue 할 대상 없음 → 조용히 통과
    assert orig.getvalue() == "hello\nworld\n"


def test_dispatching_stream_delegates_attributes():
    from dartlab.ai.runtime.progressCapture import DispatchingStream

    orig = io.StringIO()
    orig.custom_attr = "sentinel"  # type: ignore[attr-defined]
    ds = DispatchingStream(orig)
    assert ds.custom_attr == "sentinel"  # __getattr__ delegation
    # isatty: StringIO 는 isatty=False
    assert ds.isatty() is False


def test_logging_handler_routes_to_queue_in_ctx():
    from dartlab.ai.runtime.progressCapture import ProgressLoggingHandler, _progressCtx

    h = ProgressLoggingHandler()
    h.setFormatter(logging.Formatter("%(message)s"))
    log = logging.getLogger("dartlab.test_progress_handler")
    log.setLevel(logging.INFO)
    log.addHandler(h)
    # 부모 "dartlab" 로거에 installProgressCapture 가 이미 붙어 있으면
    # 레코드가 이중 enqueue 되므로 propagate 차단.
    prev_propagate = log.propagate
    log.propagate = False
    try:
        q1: queue.Queue = queue.Queue(maxsize=100)
        token = _progressCtx.set(q1)
        try:
            log.info("hello")
            log.info("multi\nline\nmessage")
        finally:
            _progressCtx.reset(token)
        assert q1.get_nowait() == "hello"
        assert q1.get_nowait() == "multi"
        assert q1.get_nowait() == "line"
        assert q1.get_nowait() == "message"
    finally:
        log.removeHandler(h)
        log.propagate = prev_propagate


def test_logging_handler_noop_without_ctx():
    from dartlab.ai.runtime.progressCapture import ProgressLoggingHandler, _progressCtx

    assert _progressCtx.get() is None
    h = ProgressLoggingHandler()
    h.setFormatter(logging.Formatter("%(message)s"))
    log = logging.getLogger("dartlab.test_progress_handler_noop")
    log.setLevel(logging.INFO)
    log.addHandler(h)
    try:
        log.info("floating message")  # 조용히 drop — assert 는 예외 없음
    finally:
        log.removeHandler(h)


def test_runToolWithProgress_success_flow():
    from dartlab.ai.runtime.progressCapture import ProgressLoggingHandler, runToolWithProgress

    h = ProgressLoggingHandler()
    h.setFormatter(logging.Formatter("%(message)s"))
    log = logging.getLogger("dartlab.progress_test_success")
    log.setLevel(logging.INFO)
    log.addHandler(h)

    def fn_ok():
        log.info("step 1")
        log.info("step 2")
        return {"ok": True, "value": 42}

    try:
        events = list(runToolWithProgress(fn_ok))
    finally:
        log.removeHandler(h)

    # 최종은 ("done", ...) 이고 progress 라인이 중간에 2개 들어있다
    assert events[-1][0] == "done"
    assert events[-1][1] == {"ok": True, "value": 42}
    lines = [payload for kind, payload in events if kind == "progress"]
    assert "step 1" in lines
    assert "step 2" in lines


def test_runToolWithProgress_error_flow():
    from dartlab.ai.runtime.progressCapture import ProgressLoggingHandler, runToolWithProgress

    h = ProgressLoggingHandler()
    h.setFormatter(logging.Formatter("%(message)s"))
    log = logging.getLogger("dartlab.progress_test_error")
    log.setLevel(logging.INFO)
    log.addHandler(h)

    def fn_err():
        log.info("before error")
        raise ValueError("boom")

    try:
        events = list(runToolWithProgress(fn_err))
    finally:
        log.removeHandler(h)

    kind, payload = events[-1]
    assert kind == "err"
    assert isinstance(payload, ValueError)
    assert str(payload) == "boom"
    progress_lines = [p for k, p in events if k == "progress"]
    assert "before error" in progress_lines


def test_progress_ctx_isolated_across_concurrent_tools():
    """두 tool 이 동시에 돌 때 각자의 queue 에만 enqueue 되는지."""
    from dartlab.ai.runtime.progressCapture import ProgressLoggingHandler, runToolWithProgress

    h = ProgressLoggingHandler()
    h.setFormatter(logging.Formatter("%(message)s"))
    log_a = logging.getLogger("dartlab.progress_test_iso_a")
    log_b = logging.getLogger("dartlab.progress_test_iso_b")
    for log in (log_a, log_b):
        log.setLevel(logging.INFO)
        log.addHandler(h)

    barrier = threading.Barrier(2)

    def fn_a():
        barrier.wait(timeout=5.0)
        log_a.info("A1")
        log_a.info("A2")
        return "A-done"

    def fn_b():
        barrier.wait(timeout=5.0)
        log_b.info("B1")
        log_b.info("B2")
        return "B-done"

    result_a: list = []
    result_b: list = []

    def drain_a():
        result_a.extend(runToolWithProgress(fn_a))

    def drain_b():
        result_b.extend(runToolWithProgress(fn_b))

    ta = threading.Thread(target=drain_a)
    tb = threading.Thread(target=drain_b)
    try:
        ta.start()
        tb.start()
        ta.join(timeout=10.0)
        tb.join(timeout=10.0)
    finally:
        for log in (log_a, log_b):
            log.removeHandler(h)

    lines_a = [p for k, p in result_a if k == "progress"]
    lines_b = [p for k, p in result_b if k == "progress"]

    # A 의 queue 엔 A 라인만, B 의 queue 엔 B 라인만
    assert "A1" in lines_a and "A2" in lines_a
    assert "B1" not in lines_a and "B2" not in lines_a
    assert "B1" in lines_b and "B2" in lines_b
    assert "A1" not in lines_b and "A2" not in lines_b
    assert result_a[-1] == ("done", "A-done")
    assert result_b[-1] == ("done", "B-done")
