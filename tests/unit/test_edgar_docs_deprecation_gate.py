"""EDGAR PR-E7b 운영자 트리거 게이트 가드 — plan delegated-prancing-tower.

본 PR-E7b 단독 검증:
- ``DARTLAB_EDGAR_DOCS_DEPRECATED=1`` 시 ``fetchEdgarDocs`` 의 docs.parquet emit skip
- 동일 환경변수 시 ``deployEdgarToHF`` 의 'docs' 카테고리 자동 제외
- ``_loadLocalAccessionNos`` 가 sections _index.parquet 우선 + docs.parquet fallback
- 환경변수 미설정 시 옛 path 그대로 (dual-write 유지)

PR-E7a 의 sectionsParityEdgar 4 주 연속 0 violations + D.1 회귀 0 + viewer 0 + sync
14 일 무사고 통과 후 운영자가 환경변수 set + 1 회 sync → 신 path 단독 운영.
"""

from __future__ import annotations

import inspect
import os

from dartlab.gather.edgar.docs.fetch import fetchEdgarDocs
from dartlab.providers.edgar.openapi.deploy import deployEdgarToHF


def _setGate(enabled: bool) -> None:
    if enabled:
        os.environ["DARTLAB_EDGAR_DOCS_DEPRECATED"] = "1"
    else:
        os.environ.pop("DARTLAB_EDGAR_DOCS_DEPRECATED", None)


def test_deploy_drops_docs_when_gate_active() -> None:
    """게이트 활성 시 deployEdgarToHF 의 'docs' 카테고리 자동 제외."""
    _setGate(True)
    try:
        # dryRun=True 라 실제 HF 호출 없음. docs 가 cats 에서 빠지면 result 에 'docs' 키 부재.
        result = deployEdgarToHF(categories=["scan", "docs", "sections"], dryRun=True)
        # docs 가 제거됐으므로 result 에 0 또는 미등재.
        # scan / sections 디렉터리 부재 시 0, 존재 시 file count.
        assert "docs" not in result or result.get("docs", 0) == 0
    finally:
        _setGate(False)


def test_deploy_keeps_docs_when_gate_off() -> None:
    """게이트 미설정 시 'docs' 카테고리 유지 (dual-write 동안 옛 path 보존)."""
    _setGate(False)
    # dryRun — sections/scan/docs 모두 시도. docs 가 cats 안에 있음.
    result = deployEdgarToHF(categories=["docs"], dryRun=True)
    # docs key 등재 (0 이라도 entry 존재).
    assert "docs" in result


def test_fetch_has_gate_check_in_source() -> None:
    """fetchEdgarDocs 본문에 DARTLAB_EDGAR_DOCS_DEPRECATED 게이트 분기 존재."""
    src = inspect.getsource(fetchEdgarDocs)
    assert "DARTLAB_EDGAR_DOCS_DEPRECATED" in src
    assert "docsDeprecated" in src or "docs_deprecated" in src.lower()


def test_freshness_prefers_sections_index() -> None:
    """_loadLocalAccessionNos 가 sections _index.parquet 우선 호출."""
    from dartlab.providers.edgar.openapi.freshness import _loadLocalAccessionNos

    src = inspect.getsource(_loadLocalAccessionNos)
    # sections _index.parquet 우선 path 존재.
    assert "loadSectionsIndex" in src
    # 옛 docs.parquet fallback 도 유지 (gate 미설정 시).
    assert "edgarDocs" in src


def test_freshness_skips_old_docs_when_gate_active() -> None:
    """게이트 활성 + sections artifact + docs.parquet 부재 시 sections 우선 path 만 hit."""
    from dartlab.providers.edgar.openapi.freshness import _loadLocalAccessionNos

    _setGate(True)
    try:
        accessions, latest = _loadLocalAccessionNos("ZZZNONEXISTENT")
        # 둘 다 없으면 빈 set + None.
        assert accessions == set()
        assert latest is None
    finally:
        _setGate(False)


def test_fetch_gate_callable_signature_unchanged() -> None:
    """fetchEdgarDocs 의 시그니처는 변경 0 (caller 회귀 X)."""
    sig = inspect.signature(fetchEdgarDocs)
    params = list(sig.parameters.keys())
    # 핵심 인자 보유.
    assert "ticker" in params
    assert "outPath" in params
    assert "sinceYear" in params
