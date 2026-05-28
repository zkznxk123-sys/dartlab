"""EDGAR sections HF 배포 게이트 가드 — PR-E3 plan delegated-prancing-tower.

본 PR-E3 단독 검증:
- ``deploy._CATEGORY_MAP`` 에 ``"sections" → "edgarSections"`` 매핑 등록
- ``DATA_RELEASES["edgarSections"]`` 의 ``nested=True`` (period-shard rglob 자동)
- ``deployEdgarToHF`` 의 default categories 가 ``["scan", "docs", "sections"]`` 3 종
- ``deployEdgarToHF(dryRun=True)`` 시 sections 디렉터리 부재 빠른 skip

workflow 파일 (``.github/workflows/edgarSync.yml``) 변경은 정적 grep 으로 cache step
+ deploy step 의 sections 등장 확인.
"""

from __future__ import annotations

import inspect
import re
from pathlib import Path

from dartlab.core.dataConfig import DATA_RELEASES
from dartlab.providers.edgar.openapi.deploy import _CATEGORY_MAP, deployEdgarToHF


def test_category_map_has_sections() -> None:
    """deploy 의 카테고리 매핑에 sections 등록."""
    assert "sections" in _CATEGORY_MAP
    assert _CATEGORY_MAP["sections"] == "edgarSections"


def test_data_releases_edgar_sections_nested() -> None:
    """edgarSections 가 nested=True — period-shard rglob 자동 처리 필수."""
    entry = DATA_RELEASES["edgarSections"]
    assert entry.get("nested") is True


def test_deploy_default_includes_sections() -> None:
    """deployEdgarToHF 의 default ``cats`` 에 sections 포함."""
    src = inspect.getsource(deployEdgarToHF)
    assert "sections" in src
    # 기본 cats 리터럴 안에 sections.
    assert re.search(r"cats\s*=\s*categories\s*or\s*\[[^\]]*sections", src)


def test_deploy_dryrun_handles_missing_sections_dir() -> None:
    """sections 디렉터리 부재 시 dryRun 이 0 반환 (예외 없음)."""
    result = deployEdgarToHF(categories=["sections"], dryRun=True)
    # localDir 없으면 result[cat] = 0 + 다음 카테고리로 계속.
    assert isinstance(result, dict)
    # sections 부재 시 0 또는 미등재.
    assert result.get("sections", 0) >= 0


def test_workflow_yaml_has_sections_cache_and_deploy() -> None:
    """``.github/workflows/edgarSync.yml`` 에 sections cache + deploy step."""
    wf = Path("c:/Users/MSI/OneDrive/Desktop/sideProject/dartlab/.github/workflows/edgarSync.yml")
    if not wf.exists():
        wf = Path(".github/workflows/edgarSync.yml")
    assert wf.exists(), f"workflow 파일 부재: {wf}"
    text = wf.read_text(encoding="utf-8")
    # cache restore + save 둘 다 sections path.
    assert "data/edgar/sections" in text
    # deploy step 에 'sections' append.
    assert "cats.append('sections')" in text or 'cats.append("sections")' in text
