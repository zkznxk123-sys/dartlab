"""Tool 실행 중 stdout / stderr / dartlab logger 라인을 SSE 로 실시간 스트림하기 위한 캡처 장치.

설계 SSOT — `runToolWithProgress`, `_progressCtx`, `DispatchingStream`,
`ProgressLoggingHandler`, `installProgressCapture`. toolLoop.py 가 이 한 파일만
import 해서 쓴다.

흐름:
    1. 서버 부팅 시 `installProgressCapture()` 1회 호출.
       - `sys.stdout / sys.stderr` 를 `DispatchingStream` 으로 감싼다.
       - `logging.getLogger("dartlab")` 에 `ProgressLoggingHandler` 를 붙인다.
       - idempotent — 여러 번 호출해도 중복 래핑·핸들러 부착 방지.
    2. tool 실행 시 `runToolWithProgress(fn, *args, **kwargs)` 제너레이터를 소비.
       - worker thread 에서 `contextvars.copy_context().run` 으로 caller ctx 복사.
       - worker 안에서 `_progressCtx.set(queue)` → 그 ctx 의 `DispatchingStream` /
         `ProgressLoggingHandler` 가 `_progressCtx.get()` 으로 queue 획득, 라인 enqueue.
       - 메인 스레드는 queue 를 폴링하며 `("progress", line)` yield.
       - 완료 시 `("done", raw)` 또는 `("err", exc)` 로 마감.
    3. 여러 요청이 동시에 오면 각자 `copy_context()` 로 ContextVar 가 격리되어
       다른 요청의 queue 와 섞이지 않는다.

제약:
    - `print("x", end="")` 처럼 newline 없는 출력은 즉시 enqueue 되지 않는다
      (`\\n` 만날 때까지 DispatchingStream 내부 buffer 에 축적).
    - `queue.Queue(maxsize=500)` 초과 시 put_nowait 가 drop — 진행 라인은 소실되어도
      tool 결과 자체는 정상 반환. UI 측에서 드롭 허용.
"""

from __future__ import annotations

import contextvars
import logging
import queue
import sys
import threading
from typing import Any, Callable, Generator, Optional

_LINE_Q_MAXSIZE = 500
_POLL_TIMEOUT_S = 0.2

_progressCtx: contextvars.ContextVar[Optional["queue.Queue[str]"]] = contextvars.ContextVar(
    "dartlab_progressCtx", default=None
)


def _enqueue(line: str) -> None:
    """현재 ctx 의 queue 에 한 줄 enqueue. 없거나 Full 이면 무시."""
    q = _progressCtx.get()
    if q is None:
        return
    line = line.rstrip()
    if not line:
        return
    try:
        q.put_nowait(line)
    except queue.Full:
        pass


class DispatchingStream:
    """원본 stream 에 그대로 쓰면서 `_progressCtx` queue 에도 라인 단위로 복사.

    - write: 원본 stream 에 항상 flush → 서버 콘솔 출력 보존.
    - newline 이 포함된 경우에만 queue 에 라인 단위 enqueue.
    - 래핑 대상 속성 (encoding, isatty, buffer, fileno, reconfigure 등) delegate.
    """

    def __init__(self, orig: Any) -> None:
        self._orig = orig
        self._bufLock = threading.Lock()
        self._buf = ""

    @property
    def orig(self) -> Any:
        return self._orig

    def write(self, s: Any) -> int:
        if s is None:
            return 0
        try:
            written = self._orig.write(s)
        except Exception:  # noqa: BLE001 — broken stream (ex: closed fd)
            written = 0
        if not isinstance(s, str):
            try:
                s = s.decode("utf-8", errors="replace") if isinstance(s, (bytes, bytearray)) else str(s)
            except Exception:  # noqa: BLE001
                return written if isinstance(written, int) else 0
        with self._bufLock:
            self._buf += s
            lines: list[str] = []
            while "\n" in self._buf:
                line, self._buf = self._buf.split("\n", 1)
                lines.append(line)
        for line in lines:
            _enqueue(line)
        return written if isinstance(written, int) else 0

    def flush(self) -> None:
        try:
            self._orig.flush()
        except Exception:  # noqa: BLE001
            pass

    def isatty(self) -> bool:
        fn = getattr(self._orig, "isatty", None)
        return bool(fn()) if callable(fn) else False

    def __getattr__(self, name: str) -> Any:
        # encoding · buffer · fileno · reconfigure · errors 등 모든 나머지 속성은 원본 위임.
        return getattr(self._orig, name)


class ProgressLoggingHandler(logging.Handler):
    """dartlab 로거 record → `_progressCtx` queue. ctx 없으면 no-op."""

    def emit(self, record: logging.LogRecord) -> None:
        q = _progressCtx.get()
        if q is None:
            return
        try:
            msg = self.format(record)
        except Exception:  # noqa: BLE001
            try:
                msg = record.getMessage()
            except Exception:  # noqa: BLE001
                return
        for line in msg.splitlines():
            line = line.rstrip()
            if not line:
                continue
            try:
                q.put_nowait(line)
            except queue.Full:
                return


_installed = False
_installLock = threading.Lock()
_progressHandler: Optional[ProgressLoggingHandler] = None


def installProgressCapture() -> None:
    """프로세스 생애 1회 호출. sys.stdout/stderr 래핑 + dartlab logger handler 부착.

    idempotent — 여러 번 호출해도 안전. import 시점에 자동 부팅하지 않는다 (서버 환경
    전용). 테스트나 CLI 에서 원치 않는 stdout 래핑을 피하기 위해 명시적 호출 필요.
    """
    global _installed, _progressHandler
    with _installLock:
        if _installed:
            return
        # sys.stdout / sys.stderr wrap — 이미 DispatchingStream 이면 스킵.
        if not isinstance(sys.stdout, DispatchingStream):
            sys.stdout = DispatchingStream(sys.stdout)  # type: ignore[assignment]
        if not isinstance(sys.stderr, DispatchingStream):
            sys.stderr = DispatchingStream(sys.stderr)  # type: ignore[assignment]

        # dartlab logger 에 handler attach — 기존 StreamHandler 는 그대로 유지.
        root = logging.getLogger("dartlab")
        already = any(isinstance(h, ProgressLoggingHandler) for h in root.handlers)
        if not already:
            handler = ProgressLoggingHandler()
            handler.setFormatter(logging.Formatter("%(message)s"))
            root.addHandler(handler)
            _progressHandler = handler

        _installed = True


def runToolWithProgress(
    fn: Callable[..., Any],
    *args: Any,
    **kwargs: Any,
) -> Generator[tuple[str, Any], None, None]:
    """`fn(*args, **kwargs)` 를 worker thread 에서 실행. 진행 라인 yield.

    yields:
        ("progress", line: str)
        ("done", result: Any)
        ("err", exc: BaseException)

    caller 는 ("done" / "err") 중 정확히 하나를 마지막으로 받는다.
    """
    q: "queue.Queue[str]" = queue.Queue(maxsize=_LINE_Q_MAXSIZE)
    sentinel = object()
    box: dict[str, Any] = {}

    def _worker() -> None:
        token = _progressCtx.set(q)
        try:
            box["raw"] = fn(*args, **kwargs)
        except BaseException as exc:  # noqa: BLE001 — tool 예외는 caller 에 전달
            box["err"] = exc
        finally:
            _progressCtx.reset(token)
            try:
                q.put_nowait(sentinel)  # type: ignore[arg-type]
            except queue.Full:
                # sentinel 은 반드시 들어가야 하므로 blocking put 으로 폴백
                q.put(sentinel)  # type: ignore[arg-type]

    ctx = contextvars.copy_context()
    t = threading.Thread(target=lambda: ctx.run(_worker), name="dartlab-tool-progress", daemon=True)
    t.start()

    try:
        while True:
            try:
                item = q.get(timeout=_POLL_TIMEOUT_S)
            except queue.Empty:
                if not t.is_alive():
                    break
                continue
            if item is sentinel:
                break
            if isinstance(item, str):
                yield ("progress", item)
    finally:
        t.join(timeout=5.0)

    if "err" in box:
        yield ("err", box["err"])
    else:
        yield ("done", box.get("raw"))


__all__ = [
    "DispatchingStream",
    "ProgressLoggingHandler",
    "installProgressCapture",
    "runToolWithProgress",
]
