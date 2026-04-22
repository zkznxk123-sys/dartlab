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


def _ensureDefaultHandler() -> None:
    """root ``dartlab`` 로거에 기본 stderr 핸들러 부착 (최초 1회).

    사용자가 이미 핸들러를 붙였으면 아무것도 하지 않는다 (idempotent).
    propagate=False 로 root logger 로 흘러가지 않게 차단 — 다른 라이브러리 로거 설정과 충돌 방지.
    """
    global _DEFAULT_CONFIGURED
    if _DEFAULT_CONFIGURED:
        return
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
    root.propagate = False
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
