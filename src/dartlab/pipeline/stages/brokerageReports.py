"""Brokerage research stage — 증권사 리서치 메타 sync 위임 (fetch+월별write+HF push).

별도빌드 금지: 스크랩·파싱·해소·적재는 ``gather.sources.brokerage`` 가 소유.
본 stage 는 ``.github/scripts/sync/syncBrokerageReports.py`` 를 호출만 한다.
"""

from __future__ import annotations

from dartlab.pipeline.stages._runner import runScript
from dartlab.pipeline.types import PipelineMode, StageResult


def runBrokerageReports(
    *, category: str = "brokerageReports", mode: PipelineMode = "recent", codes=None, upload: bool = True, token=None
) -> StageResult:
    """증권사 리서치 메타 — syncBrokerageReports.py 위임(수집+월별 parquet+HF push).

    Args:
        category: 카테고리 라벨.
        mode: 미사용.
        codes: 미사용.
        upload: False 면 ``--no-upload`` (로컬 빌드만, HF push 생략).
        token: 미사용(uploadCategoryToHf 가 env>.env 해석).

    Returns:
        StageResult (category='brokerageReports').

    Raises:
        없음 — sync 실패는 StageResult.report.err 로 표기.

    Example:
        >>> runBrokerageReports(upload=False)  # doctest: +SKIP
        StageResult(category='brokerageReports', ...)
    """
    script = ".github/scripts/sync/syncBrokerageReports.py"
    rc = runScript(script) if upload else runScript(script, "--no-upload")
    res = StageResult(category="brokerageReports")
    if rc != 0:
        res.report.err = 1
        res.report.failures.append(f"brokerageReports sync rc={rc}")
        return res
    res.report.ok = 1
    return res
