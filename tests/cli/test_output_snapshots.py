"""CLI 출력 시각 회귀 차단 — syrupy snapshot.

본 SSOT 통합 PR (commit ad520727b) 의 acceptance test. dartlab.core.logger
의 공용 Console + Progress + RichHandler 가 한 frame buffer 위에서 일관된
화면을 그리는지를 *함수 contract* 가 아니라 *사용자가 보는 출력* 으로 동결.

미래 PR 이 CLI 출력 통일성을 깨면 즉시 fail.
"""

from __future__ import annotations

import pytest

from tests._helpers import captureRichOutput

pytestmark = pytest.mark.unit


def _emitHfDownloadMarker() -> None:
    """HF 다운로드 1 사이클의 logger 마커 시뮬레이션."""
    from dartlab.core.logger import getLogger

    log = getLogger(__name__)
    log.info("[cyan]⬇ HF[/] metadata/dartList.parquet")
    log.info("[green]✓[/] dartList.parquet (4.2 MB)")


def _emitProgressBar() -> None:
    """공용 Progress singleton 1 사이클 — bar + counter.

    `progress.refresh()` 는 snapshot 결정성을 위한 강제 redraw — production
    사용자는 `auto_refresh=True` 의 background thread tick (~0.1s) 으로 자연스
    럽게 보지만, 동기 테스트는 thread tick 보장 없이 끝나 Linux CI 에서 빈
    출력. refresh 명시 호출로 thread 의존성 제거.
    """
    from dartlab.core.logger import getProgress

    progress = getProgress()
    with progress:
        task = progress.add_task("종목 스캔", total=3)
        for _ in range(3):
            progress.advance(task)
        progress.refresh()


def _emitConsoleStdout() -> None:
    """getConsole().print 직접 호출 (CLI 명령이 자주 쓰는 패턴)."""
    from dartlab.core.logger import getConsole

    console = getConsole()
    console.print("[bold]자동 수집 시작[/]: 3개 종목 docs")
    console.print("  1. 삼성전자 (005930)")
    console.print("  2. SK하이닉스 (000660)")
    console.print("  3. 카카오 (035720)")
    console.print("\n[bold green]완료[/]: 성공 3 / 총 3")


def _emitMixedLoggerAndConsole() -> None:
    """logger.info + getConsole().print 혼합 — 한 Console 공유 검증."""
    from dartlab.core.logger import getConsole, getLogger

    log = getLogger(__name__)
    console = getConsole()

    log.info("[cyan]⬇ HF[/] dartList.parquet")
    console.print("[bold]수집 대상[/]: 1047 종목")
    log.info("[green]✓[/] dartList.parquet (4.2 MB)")
    console.print("[bold green]완료[/]: 1047 종목 처리")


def _emitErrorAndWarning() -> None:
    """logger.warning / error 가 같은 Console 로 라우팅 — handler 일관성."""
    from dartlab.core.logger import getLogger

    log = getLogger(__name__)
    log.warning("DART API 키 미설정 — 부분 수집 모드")
    log.error("종목 005930 수집 실패: connection timeout")


def test_hfDownloadMarker_noTqdmChars(snapshot) -> None:
    """HF 다운로드 마커 출력에 tqdm 시그니처 부재 + ⬇/✓ 마커 존재."""
    out = captureRichOutput(_emitHfDownloadMarker)
    # tqdm 시그니처 (▓ bar / "it/s" / "%|") 가 새지 않아야 한다.
    assert "▓" not in out, "tqdm bar 문자 잔존"
    assert "it/s" not in out, "tqdm 속도 표기 잔존"
    # SSOT 마커
    assert "⬇" in out and "HF" in out
    assert "✓" in out
    # 텍스트 형태 동결
    assert out == snapshot


def test_progressBar_oneCycle(snapshot) -> None:
    """공용 Progress singleton 의 폭/컬럼 텍스트 동결."""
    out = captureRichOutput(_emitProgressBar)
    assert "종목 스캔" in out
    assert out == snapshot


def test_consoleStdout_collectAutoOutput(snapshot) -> None:
    """dartlab collect --auto 의 헤더/종목 목록/완료 라인 동결."""
    out = captureRichOutput(_emitConsoleStdout)
    assert "자동 수집 시작" in out
    assert "삼성전자" in out
    assert out == snapshot


def test_mixedLoggerAndConsole_shareSameBuffer(snapshot) -> None:
    """logger.info 와 console.print 가 한 buffer 안에서 순서대로 섞임."""
    out = captureRichOutput(_emitMixedLoggerAndConsole)
    # logger 메시지가 console.print 메시지 *사이* 에 들어와야 한다.
    posDownload = out.index("⬇")
    posTarget = out.index("수집 대상")
    posDone = out.index("✓")
    posComplete = out.index("완료")
    assert posDownload < posTarget < posDone < posComplete, "Live frame buffer 순서 깨짐"
    assert out == snapshot


def test_errorAndWarning_routedToSameConsole(snapshot) -> None:
    """logger.warning + error 가 같은 RichHandler/Console 로 라우팅됨."""
    out = captureRichOutput(_emitErrorAndWarning)
    assert "WARNING" in out or "warning" in out.lower()
    assert "ERROR" in out or "error" in out.lower()
    assert out == snapshot
