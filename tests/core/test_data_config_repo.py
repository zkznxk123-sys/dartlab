"""dataConfig.repoFor — 카테고리별 HF repo 라우팅 단위 테스트.

전용 repo 분리(panel/news 파일수 벽 회피) 인프라. 데이터 이전 전까지는 모든 카테고리가 기본
repo 를 공유(동작 무변경) — repo 필드가 있을 때만 그쪽으로 라우팅하는지 검증.
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.unit


def test_repofor_default_is_hf_repo():
    """repo 필드 미지정 카테고리 → 기본 HF_REPO (이전 전 동작 무변경 보장)."""
    from dartlab.core.dataConfig import HF_REPO, repoFor

    assert repoFor("panel") == HF_REPO
    assert repoFor("contentIndex") == HF_REPO
    assert repoFor("newsGdelt") == HF_REPO


def test_repofor_unknown_category_graceful():
    """미등록 카테고리도 KeyError 없이 기본 repo (bulkUploadHf krxPricesV2 등)."""
    from dartlab.core.dataConfig import HF_REPO, repoFor

    assert repoFor("krxPricesV2") == HF_REPO
    assert repoFor("zzz-nonexistent") == HF_REPO


def test_repofor_respects_repo_field(monkeypatch):
    """카테고리에 repo 필드가 있으면 그 전용 repo 로 라우팅 (이전 완료 후 시나리오)."""
    from dartlab.core import dataConfig

    monkeypatch.setitem(dataConfig.DATA_RELEASES["panel"], "repo", "eddmpython/dartlab-data-panel")
    assert dataConfig.repoFor("panel") == "eddmpython/dartlab-data-panel"
    # 다른 카테고리는 영향 없음
    assert dataConfig.repoFor("contentIndex") == dataConfig.HF_REPO


def test_hfbaseurl_uses_repofor(monkeypatch):
    """hfBaseUrl 도 repoFor 로 repo 를 해석 — 전용 repo 면 URL 도 그쪽."""
    from dartlab.core import dataConfig

    monkeypatch.setitem(dataConfig.DATA_RELEASES["panel"], "repo", "eddmpython/dartlab-data-panel")
    url = dataConfig.hfBaseUrl("panel")
    assert "dartlab-data-panel" in url
    assert url.endswith("/dart/panel")
