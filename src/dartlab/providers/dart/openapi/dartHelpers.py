"""dart/openapi dart 헬퍼 — dart.py 분할 (규칙 3 LoC).

_dataPath / _buildPeriods / _periodLabel / _maybeValidateFinance / _fetchSeries.
"""

from __future__ import annotations

from pathlib import Path

import polars as pl

from dartlab import config as _dartlabConfig
from dartlab.core.dartClient import DartClient
from dartlab.core.dataConfig import DATA_RELEASES
from dartlab.providers.dart.openapi.constants import (
    CODE_TO_LABEL as _CODE_TO_LABEL,
)
from dartlab.providers.dart.openapi.constants import (
    QUARTER_TO_CODE as _QUARTER_TO_CODE,
)


def _dataPath(category: str, stockCode: str) -> Path:
    """dartlab 데이터 디렉토리 내 저장 경로.

    {dataDir}/dart/{category}/{stockCode}.parquet
    """
    subDir = DATA_RELEASES.get(category, {}).get("dir", f"dart/{category}")
    dest = Path(_dartlabConfig.dataDir) / subDir / f"{stockCode}.parquet"
    dest.parent.mkdir(parents=True, exist_ok=True)
    return dest


# ── 내부 유틸 ──────────────────────────────────────────────


def _buildPeriods(
    start: int,
    end: int | None,
    quarterly: bool,
    quarter: str,
) -> list[tuple[str, str]]:
    """(bsnsYear, reprtCode) 리스트 생성."""
    endYear = end if end is not None else start
    if endYear < start:
        raise ValueError(f"start({start}) > end({endYear}): 시작 연도가 종료 연도보다 큽니다")
    if start < 2015:
        raise ValueError(f"start={start}: OpenDART는 2015년 이후 데이터만 제공합니다")

    years = range(start, endYear + 1)
    quarters = ["Q1", "Q2", "Q3", "Q4"] if quarterly else [quarter]

    periods = []
    for y in years:
        for q in quarters:
            code = _QUARTER_TO_CODE.get(q, "11011")
            periods.append((str(y), code))
    return periods


def _periodLabel(bsnsYear: str, reprtCode: str) -> str:
    label = _CODE_TO_LABEL.get(reprtCode, reprtCode)
    return f"{bsnsYear} {label}"


def _maybeValidateFinance(df: pl.DataFrame) -> None:
    """opt-in finance schema 검증 — DARTLAB_VALIDATE_SCHEMA=1 일 때만 동작.

    Capabilities:
        production path 의 데이터 drift 차단 — DART API 응답 schema 가 silent
        하게 바뀌면 즉시 warning 로그. 환경변수 OFF (기본) 면 0 비용.
    Args:
        df: Dart.finance 결과 frame.
    Returns:
        None. validate 실패 시 logger.warning, raise 안 함 (production 무중단).
    Example:
        >>> _maybeValidateFinance(df)  # env OFF → no-op
        >>> import os; os.environ['DARTLAB_VALIDATE_SCHEMA'] = '1'
        >>> _maybeValidateFinance(df)  # schema 위반 시 logger.warning
    Guide:
        CI / dev 에서 ON (catch drift), production wheel 사용자는 default OFF.
    SeeAlso:
        dartlab.core.schemas.FinanceSchema.
    Requires:
        dev 환경 — pandera[polars] 설치. production wheel 은 default OFF 라 무영향.    Raises:
        없음. validate 실패는 warning 으로만 보고.
    """
    import os

    if not os.environ.get("DARTLAB_VALIDATE_SCHEMA"):
        return
    if df is None or df.is_empty():
        return
    try:
        from dartlab.core.logger import getLogger
        from dartlab.core.schemas import FinanceSchema

        FinanceSchema.validate(df, lazy=True)
    except ImportError:
        return
    except Exception as exc:  # noqa: BLE001 — schema validation drift는 모든 예외 흡수
        from dartlab.core.logger import getLogger

        getLogger(__name__).warning("FinanceSchema drift: %s", str(exc)[:200])


def _fetchSeries(
    client: DartClient,
    endpoint: str,
    corpCode: str,
    corpName: str,
    periods: list[tuple[str, str]],
    title: str,
    extraParams: dict | None = None,
) -> pl.DataFrame:
    """여러 기간 연속 조회 → concat + rich.progress."""
    from rich.progress import BarColumn, MofNCompleteColumn, Progress, SpinnerColumn, TextColumn

    from dartlab.core.logger import getConsole

    frames: list[pl.DataFrame] = []

    progress = Progress(
        SpinnerColumn(),
        TextColumn("[bold blue]{task.description}"),
        BarColumn(),
        MofNCompleteColumn(),
        console=getConsole(),
    )
    _task = progress.add_task(f"{title} | {corpName}", total=len(periods))
    with progress:
        for bsnsYear, reprtCode in periods:
            progress.update(_task, description=f"{title} | {corpName} | {_periodLabel(bsnsYear, reprtCode)}")

            params: dict[str, str] = {
                "corp_code": corpCode,
                "bsns_year": bsnsYear,
                "reprt_code": reprtCode,
            }
            if extraParams:
                params.update(extraParams)

            df = client.getDf(f"{endpoint}.json", params)
            if df.height > 0:
                frames.append(df)
            progress.advance(_task)

    if not frames:
        return pl.DataFrame()
    return pl.concat(frames, how="diagonal_relaxed")
