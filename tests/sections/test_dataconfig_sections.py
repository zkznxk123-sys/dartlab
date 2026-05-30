"""dataConfig DATA_RELEASES['sections'] 항목 회귀 가드.

plan snazzy-wibbling-origami PR-1d. sectionsStorage / sectionsBuilder 가 영속화하는
``data/dart/sections/{code}/{period}.parquet`` artifact 의 HF push 메타 일관성 검증.
"""

from __future__ import annotations

import pytest

from dartlab.core.dataConfig import DATA_RELEASES, hfBaseUrl

pytestmark = [pytest.mark.unit]


def test_sections_entry_present():
    assert "sections" in DATA_RELEASES


def test_sections_dir_matches_storage_module():
    # sectionsStorage._SECTIONS_REL 와 DATA_RELEASES["sections"]["dir"] 일치.
    # 둘이 분리되면 build path 와 HF push path 가 어긋남 → 사용자 측 다운로드 0.
    from dartlab.providers.dart.docs.sections.sectionsStorage import _SECTIONS_REL

    assert DATA_RELEASES["sections"]["dir"] == _SECTIONS_REL


def test_sections_marked_nested():
    # uploadData.py 가 isNested 플래그로 rglob + path_in_repo relative_to 처리.
    # nested 플래그 누락 시 종목 디렉터리 안 파일이 HF root 에 평탄 업로드 → 사고.
    assert DATA_RELEASES["sections"].get("nested") is True


def test_sections_marked_public():
    assert DATA_RELEASES["sections"].get("public") is True


def test_sections_hf_url_resolves():
    url = hfBaseUrl("sections")
    assert url.endswith("/dart/sections")
