"""dartlab 중앙 로거.

라이브러리 내부 진행/진단 메시지는 전부 ``logging`` 경유 — 사용자가 log 레벨·핸들러
를 자유롭게 제어. CLI 전용 사용자 출력 (cli/commands/*) 은 여전히 ``print`` 유지.

기본 동작::

    import dartlab  # stderr 에 INFO 레벨 dartlab 메시지 자동 출력

Silence (자동화/CI 에서)::

    import logging
    logging.getLogger("dartlab").setLevel(logging.WARNING)

Verbose::

    logging.getLogger("dartlab").setLevel(logging.DEBUG)

사용 (라이브러리 내부 코드)::

    from dartlab.core.logger import getLogger
    log = getLogger(__name__)
    log.info("다운로드 시작: %s", label)
    log.warning("재시도 %d/%d", attempt, maxRetries)
"""

from __future__ import annotations

import logging
import sys

_ROOT_NAME = "dartlab"
_DEFAULT_CONFIGURED = False


def _ensureUtf8Stream() -> None:
    """Windows 기본 stdout/stderr cp949 인코딩을 UTF-8 로 재구성 (가능한 경우).

    한글·이모지가 포함된 로그·가이드 출력이 Windows 터미널에서 ``UnicodeEncodeError``
    없이 표시되도록 한다. TextIOWrapper.reconfigure 를 지원하지 않는 환경
    (Python 3.6 이하, 이미 다른 wrapper) 에서는 조용히 스킵.
    """
    if sys.platform != "win32":
        return
    for stream in (sys.stdout, sys.stderr):
        try:
            enc = (getattr(stream, "encoding", "") or "").lower()
            if enc and enc not in {"utf-8", "utf8"}:
                stream.reconfigure(encoding="utf-8", errors="backslashreplace")
        except (AttributeError, OSError, ValueError):
            # 리다이렉트된 스트림·서브프로세스 파이프 등 reconfigure 불가 — 무시.
            pass


def _ensureDefaultHandler() -> None:
    """root ``dartlab`` 로거에 기본 stderr 핸들러 부착 (최초 1회).

    사용자가 이미 핸들러를 붙였으면 아무것도 하지 않는다 (idempotent).
    propagate=True 유지 — pytest caplog / 사용자 root logger 훅 이 dartlab
    레코드를 볼 수 있도록. 중복 출력은 root 가 별도 핸들러 설정했을 때만
    발생하며, 그 경우 사용자가 ``dartlab`` 핸들러를 따로 관리해야 한다.
    """
    global _DEFAULT_CONFIGURED
    if _DEFAULT_CONFIGURED:
        return
    _ensureUtf8Stream()
    root = logging.getLogger(_ROOT_NAME)
    if root.handlers:
        _DEFAULT_CONFIGURED = True
        return

    handler = logging.StreamHandler(sys.stderr)
    # 간결한 포맷 — 메시지 본문에 [dartlab] 프리픽스·레벨 이미 녹아있음
    handler.setFormatter(logging.Formatter("%(message)s"))
    root.addHandler(handler)
    # 사용자가 이미 setLevel 호출했으면 (NOTSET=0 아님) 존중. 아니면 INFO.
    if root.level == logging.NOTSET:
        root.setLevel(logging.INFO)
    # propagate=True (default) 유지 — caplog 가 dartlab.* 레코드를 캡처 가능.
    _DEFAULT_CONFIGURED = True


def getLogger(name: str | None = None) -> logging.Logger:
    """dartlab 네임스페이스 로거.

    Parameters
    ----------
    name : str | None
        모듈명 (보통 ``__name__``). None 이면 root ``dartlab`` 로거.

    Returns
    -------
    logging.Logger
        ``dartlab`` 또는 ``dartlab.<name>`` 로거. 기본 핸들러 부착됨.
    """
    _ensureDefaultHandler()
    if name is None or name == _ROOT_NAME:
        return logging.getLogger(_ROOT_NAME)
    if name.startswith(_ROOT_NAME + "."):
        return logging.getLogger(name)
    # __name__ 이 "dartlab.providers.dart.company" 같이 완전 경로인 경우
    if name.startswith(_ROOT_NAME):
        return logging.getLogger(name)
    return logging.getLogger(f"{_ROOT_NAME}.{name}")
