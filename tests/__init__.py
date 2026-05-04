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
