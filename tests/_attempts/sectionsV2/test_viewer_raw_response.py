"""viewer API 응답 raw XML 회귀 가드 — plan v4 PR-3.4 (backend 분).

plan snazzy-wibbling-origami v4 의 frontend visual baseline 게이트 중 *backend
contract* 부분. Playwright UI 검증 전 사전 가드:

    1. `_buildRowsForTopic` 응답의 cells 가 raw XML 양식 (P/SPAN/USERMARK/TABLE) 포함.
    2. DOMPurify allowlist attr (align/colspan/rowspan/usermark/border) 1 개 이상.
    3. 5 baseline 종목 × 3 핵심 topic (productService/financialNotes/consolidatedNotes).
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

import dartlab.config as _cfg

os.environ.setdefault("DARTLAB_NO_HF_DOWNLOAD", "1")

_BASELINE = ("005380", "005930", "035720", "207940", "000660")
_CORE_TOPICS = ("productService", "financialNotes", "consolidatedNotes")


def _sectionsDir(code: str) -> Path:
    return Path(_cfg.dataDir) / "dart" / "sections" / code


@pytest.mark.unit
@pytest.mark.parametrize("code", _BASELINE)
def testViewerRowsRawXml(code: str) -> None:
    """viewer rows 응답의 cells 가 raw XML 양식 (P/SPAN/TABLE 보존)."""
    if not _sectionsDir(code).exists():
        pytest.skip(f"{code} sections artifact 부재")
    from dartlab import Company
    from dartlab.server.services.companyApi import _buildRowsForTopic

    c = Company(code)
    foundAny = False
    for topic in _CORE_TOPICS:
        rows = _buildRowsForTopic(c, topic, windowPeriods=None)
        if not rows:
            continue
        foundAny = True
        # cell 양식 검사 — raw XML 양식 1 개 이상 (P 또는 TABLE).
        rawCells = []
        for r in rows[:10]:
            for cellValue in r.get("cells", {}).values():
                if isinstance(cellValue, str) and cellValue:
                    rawCells.append(cellValue)
        if rawCells:
            hasRawXml = any(("<P" in c or "<TABLE" in c or "<SPAN" in c) for c in rawCells)
            assert hasRawXml, f"{code}/{topic} cells 에 raw XML (<P/<SPAN/<TABLE) 0 — xmlChunkToMixed 회귀 의심"
            break
    assert foundAny, f"{code} 모든 핵심 topic 의 rows 가 빈 결과"


@pytest.mark.unit
@pytest.mark.parametrize("code", _BASELINE)
def testViewerRowsAttrPreserved(code: str) -> None:
    """viewer rows 응답에 DOMPurify allowlist attr 1 개 이상 보존."""
    if not _sectionsDir(code).exists():
        pytest.skip(f"{code} sections artifact 부재")
    from dartlab import Company
    from dartlab.server.services.companyApi import _buildRowsForTopic

    c = Company(code)
    for topic in _CORE_TOPICS:
        rows = _buildRowsForTopic(c, topic, windowPeriods=None)
        if not rows:
            continue
        # cells 중 attr 1 개 이상.
        for r in rows:
            for cellValue in r.get("cells", {}).values():
                if isinstance(cellValue, str) and cellValue:
                    # DART 비표준 attr 또는 표준 attr 1 개 이상.
                    if any(
                        attr in cellValue
                        for attr in ("ALIGN=", "COLSPAN=", "ROWSPAN=", "USERMARK=", "BORDER=", "WIDTH=", "VALIGN=")
                    ):
                        return  # 검증 통과
        # topic 1 개라도 attr 발견 시 OK. 모든 topic 0 면 fail.
    pytest.fail(
        f"{code} 모든 cells 에 DOMPurify allowlist attr (ALIGN/COLSPAN/USERMARK 등) 0 — _tableToHtml lossy 회귀 의심"
    )
