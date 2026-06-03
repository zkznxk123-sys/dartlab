"""News stage — 헤드라인 아카이브. syncNewsHeadlines(KR/US) + bulkUploadHf 동형.

워크플로 충실 재현: ``syncNewsHeadlines.py --market KR --once --max-queries <kr>`` +
``--market US --once --max-queries <us>`` + ``bulkUploadHf.py newsHeadlines --since 86400``.
max-queries 는 env NEWS_MAX_QUERIES_KR/US(기본 150/80, 워크플로 github.event.inputs).
"""

from __future__ import annotations

import os

from dartlab.pipeline.stages._runner import runScript
from dartlab.pipeline.types import PipelineMode, StageResult


def runNewsHeadlines(
    *, category: str = "news", mode: PipelineMode = "recent", codes=None, upload: bool = True, token=None
) -> StageResult:
    """뉴스 헤드라인 — KR/US fetch + bulk since-upload(newsHeadlines).

    Args:
        category: 카테고리 라벨.
        mode: 미사용.
        codes: 미사용.
        upload: bulkUploadHf 수행 여부.
        token: 미사용(bulkUploadHf 가 env>.env 해석).

    Returns:
        StageResult.

    Raises:
        없음.

    Example:
        >>> runNewsHeadlines(upload=False)  # doctest: +SKIP
        StageResult(category='newsHeadlines', ...)
    """
    krQ = os.environ.get("NEWS_MAX_QUERIES_KR", "150")
    usQ = os.environ.get("NEWS_MAX_QUERIES_US", "80")
    script = ".github/scripts/sync/syncNewsHeadlines.py"
    rc1 = runScript(script, "--market", "KR", "--once", "--max-queries", krQ)
    rc2 = runScript(script, "--market", "US", "--once", "--max-queries", usQ)
    res = StageResult(category="newsHeadlines")
    if rc1 != 0 or rc2 != 0:
        res.report.err = 1
        res.report.failures.append(f"news fetch rc=KR:{rc1}/US:{rc2}")
        return res
    res.report.ok = 1
    if upload:
        rc3 = runScript(".github/scripts/sync/bulkUploadHf.py", "newsHeadlines", "--since", "86400")
        if rc3 != 0:
            res.report.fail = 1
            res.report.failures.append(f"news upload rc={rc3}")
    return res
