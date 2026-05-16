"""테스트 공통 도우미 — logger/stdout 캡처 패턴 + fixture-based Company.

Phase 3 Act4 — 구현 세부 (logger propagate, stdout clean, mockcompany 구조)
를 추상화해 refactor 시 연쇄 깨짐 완화.

사용 예::

    from tests._helpers import assertLogged, assertStdoutClean

    def test_download_message_goes_to_logger(capsys, caplog):
        import logging
        with caplog.at_level(logging.INFO, logger="dartlab.core.messaging"):
            from dartlab.core.messaging import emit
            emit("download:start", stockCode="005930", label="finance")
        assertStdoutClean(capsys)
        assertLogged(caplog, pattern="005930", logger="dartlab.core.messaging")
"""

from __future__ import annotations

import re
from typing import Any


def assertLogged(
    caplog: Any,
    pattern: str,
    *,
    logger: str | None = None,
    level: str | None = None,
) -> None:
    """caplog 에 특정 패턴의 레코드가 있는지 assert.

    Parameters
    ----------
    caplog : pytest.LogCaptureFixture
        ``caplog`` fixture.
    pattern : str
        레코드 메시지에 포함되어야 할 문자열 (regex 미사용, plain substring).
        정규식이 필요하면 ``pattern_re`` 변형을 만들어 사용.
    logger : str | None
        특정 logger 이름 필터 (예: "dartlab.viz"). None 이면 전체 검사.
    level : str | None
        최소 레벨 필터 ("INFO"/"WARNING"/"ERROR"). None 이면 전체.

    Raises
    ------
    AssertionError
        매칭 레코드 없을 때. 실제 캡처된 레코드 요약 포함.
    """
    records = caplog.records
    if logger is not None:
        records = [r for r in records if r.name == logger or r.name.startswith(logger + ".")]
    if level is not None:
        import logging as _logging

        min_level = getattr(_logging, level.upper())
        records = [r for r in records if r.levelno >= min_level]

    for r in records:
        if pattern in r.getMessage():
            return

    # 실패 — 디버그 정보 제공
    summary = [f"  {r.levelname} {r.name}: {r.getMessage()[:120]}" for r in records]
    raise AssertionError(
        f"패턴 '{pattern}' 를 포함하는 레코드 없음 (logger={logger!r}, level={level!r}).\n"
        f"  캡처된 {len(records)}건:\n" + "\n".join(summary[:10])
    )


def assertStdoutClean(capsys: Any) -> None:
    """capsys 의 stdout 이 비어 있음을 assert. 라이브러리 pollution 방어.

    라이브러리 내부 코드는 stdout 에 직접 쓰면 안 되며 logger 를 경유해야
    한다. 본 helper 는 그 계약을 테스트에서 검증.

    Raises
    ------
    AssertionError
        stdout 에 출력이 있을 때. 앞 300자 포함.
    """
    captured = capsys.readouterr()
    if captured.out:
        raise AssertionError(
            f"stdout 오염 감지 (라이브러리는 logger 사용, stdout 쓰기 금지):\n  {captured.out[:300]!r}"
        )


def assertStdoutContains(capsys: Any, pattern: str) -> None:
    """capsys 의 stdout 에 특정 패턴이 있는지 assert. print 기반 출력 검증용.

    사용 케이스: CLI 명령, viz marker (``<!--DARTLAB_VIZ:``), 사용자
    interactive (setup/ask) 등 **의도적** stdout 출력.

    Raises
    ------
    AssertionError
        매칭 실패 시 실제 stdout 앞 300자 포함.
    """
    captured = capsys.readouterr()
    if pattern not in captured.out:
        raise AssertionError(f"stdout 에 '{pattern}' 없음.\n  실제 stdout:\n  {captured.out[:300]!r}")


_VIZ_MARKER_RE = re.compile(r"<!--DARTLAB_VIZ:(.+?):VIZ_END-->", re.DOTALL)


def extractVizMarkers(stdout: str) -> list[dict]:
    """stdout 에서 DARTLAB_VIZ marker JSON 전수 추출.

    Parameters
    ----------
    stdout : str
        ``capsys.readouterr().out`` 원본.

    Returns
    -------
    list[dict]
        각 marker 의 JSON payload (chartType / title / series 등). marker
        없으면 빈 리스트.
    """
    import json

    out: list[dict] = []
    for m in _VIZ_MARKER_RE.finditer(stdout):
        try:
            out.append(json.loads(m.group(1)))
        except json.JSONDecodeError:
            pass
    return out


def captureRichOutput(fn, *, width: int = 120, color: bool = False) -> str:
    """fn 호출 동안 dartlab Console 출력을 텍스트로 캡처 — syrupy snapshot 호환.

    Capabilities:
        dartlab.core.logger 의 공용 Console 을 임시 record-mode 로 교체해 rich
        Progress · Live · Console.print · RichHandler 로그를 한 문자열로 모은다.
        snapshot 동결로 CLI 시각 회귀를 자동 차단한다.
    Args:
        fn: 인자 없는 callable. 본 함수 안에서 호출되며 그 동안의 출력만 캡처.
        width: 터미널 폭 고정 (환경 독립성 — Windows / Linux ANSI 차이 제거).
        color: True 면 ANSI escape 포함, False 면 plain text.
    Returns:
        str. console.export_text(clear=False, styles=color) 결과.
    Example:
        >>> from tests._helpers import captureRichOutput
        >>> def emit_hf_marker():
        ...     from dartlab.core.logger import getLogger
        ...     getLogger(__name__).info("[cyan]⬇ HF[/] dartList.parquet")
        >>> text = captureRichOutput(emit_hf_marker)
        >>> "⬇ HF" in text
        True
    Guide:
        installRichHandler 가 호출됐을 때만 logger → Console 라우팅 동작.
        본 헬퍼가 자동으로 idempotent 호출.
    SeeAlso:
        dartlab.core.logger.installRichHandler · getConsole.
    Requires:
        rich Console.record=True 지원 (rich >= 12).
    AIContext:
        본 SSOT 통합 PR (commit ad520727b) 의 화면 일관성 acceptance test.
    Raises:
        없음. fn 내부 예외는 그대로 전파.
    """
    import io

    from rich.console import Console

    from dartlab.core import logger as _loggerMod

    _loggerMod.installRichHandler()
    buf = io.StringIO()
    newConsole = Console(file=buf, record=True, force_terminal=True, width=width, color_system="truecolor")
    savedConsole = _loggerMod._console
    _loggerMod._console = newConsole
    try:
        savedRichHandler = None
        for h in _loggerMod.logging.getLogger(_loggerMod._ROOT_NAME).handlers:
            if hasattr(h, "console"):
                savedRichHandler = h
                h.console = newConsole
        fn()
        return newConsole.export_text(clear=False, styles=color)
    finally:
        _loggerMod._console = savedConsole
        if savedRichHandler is not None:
            savedRichHandler.console = savedConsole
