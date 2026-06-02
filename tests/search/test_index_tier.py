"""검색 인덱스 tier(lite/full) 배포 단위 테스트 — 경로 분기 + 축소 빌드 + 활성 디렉터리 fallback.

배포면 핵심: pip 사용자는 경량 lite tier 를 받아 즉시 검색. flat(기존 배포/full) 우선, 없으면
tier(기본 lite) 로 fallback — 기존 인덱스 무효화 0. 네트워크 미사용(로컬 합성 데이터만).
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.unit


@pytest.fixture
def synthRoot(tmp_path, monkeypatch):
    """합성 데이터 루트 — cfg.dataDir 격리 + 검색 캐시/세션 가드 리셋."""
    import dartlab.config as cfg
    from dartlab.providers.dart.search import fieldIndex, fieldIndexRebuild

    monkeypatch.setattr(cfg, "dataDir", str(tmp_path))
    monkeypatch.setattr(fieldIndexRebuild, "_HF_CONTENTINDEX_ATTEMPTED", True, raising=False)  # 네트워크 차단
    monkeypatch.setenv("DARTLAB_NO_HF_DOWNLOAD", "1")
    fieldIndex.clearCache()
    yield tmp_path
    fieldIndex.clearCache()


def test_content_index_dir_tier_path(synthRoot):
    """_contentIndexDir(None)=flat, ('lite')=서브디렉터리."""
    from dartlab.providers.dart.search.fieldIndex import _contentIndexDir

    flat = _contentIndexDir()
    lite = _contentIndexDir("lite")
    assert flat.name == "contentIndex"
    assert lite.parent.name == "contentIndex" and lite.name == "lite"


def test_active_index_dir_flat_first(synthRoot):
    """flat main.npz 존재 → 활성 디렉터리 = flat (기존 배포 보존)."""
    from dartlab.providers.dart.search.fieldIndex import _activeIndexDir, _contentIndexDir

    (_contentIndexDir() / "main.npz").write_bytes(b"\x00")
    assert _activeIndexDir() == _contentIndexDir()


def test_active_index_dir_tier_fallback(synthRoot, monkeypatch):
    """flat 부재 + lite/main.npz 존재 + env tier=lite → 활성 디렉터리 = lite."""
    from dartlab.providers.dart.search.fieldIndex import _activeIndexDir, _contentIndexDir

    monkeypatch.setenv("DARTLAB_SEARCH_TIER", "lite")
    (_contentIndexDir("lite") / "main.npz").write_bytes(b"\x00")
    assert _activeIndexDir() == _contentIndexDir("lite")


def _mkAllFilings(root):
    import polars as pl

    afdir = root / "dart" / "allFilings"
    afdir.mkdir(parents=True, exist_ok=True)
    base = dict(section_order=0, corp_code="", corp_name="삼성", section_title="", fetch_status="ok")
    pl.DataFrame(
        [
            {
                **base,
                "rcept_no": "20240101000001",
                "stock_code": "005930",
                "rcept_dt": "20240101",
                "report_nm": "유상증자결정",
                "content_raw": "<p>유상증자 신주 발행 자금조달</p>",
            }
        ]
    ).write_parquet(afdir / "20240101.parquet")
    pl.DataFrame(
        [
            {
                **base,
                "rcept_no": "20241201000002",
                "stock_code": "000660",
                "rcept_dt": "20241201",
                "report_nm": "주요사항보고",
                "content_raw": "<p>합병 결정 흡수합병 비율</p>",
            }
        ]
    ).write_parquet(afdir / "20241201.parquet")


def test_rebuild_main_lite_sincedate_reduces(synthRoot):
    """lite tier + sinceDate → 하한 이전 공시 제외(축소 색인). full 은 flat 전량."""
    from dartlab.providers.dart.search import fieldIndex as FI
    from dartlab.providers.dart.search import fieldIndexRebuild as FIR

    _mkAllFilings(synthRoot)
    n_full = FIR.rebuildMain(includeDocs=False, tier="full", showProgress=False)
    FI.clearCache()
    n_lite = FIR.rebuildMain(includeDocs=False, tier="lite", sinceDate="20240601", showProgress=False)
    assert n_full == 2
    assert n_lite == 1  # 20240101 제외, 20241201 포함
    assert (FI._contentIndexDir() / "main.npz").exists()
    assert (FI._contentIndexDir("lite") / "main.npz").exists()


def test_index_info_schema_version(synthRoot):
    """빌드된 인덱스 info 에 schemaVersion 기록 + indexInfo 노출."""
    from dartlab.providers.dart.search import fieldIndex as FI
    from dartlab.providers.dart.search import fieldIndexRebuild as FIR

    _mkAllFilings(synthRoot)
    FIR.rebuildMain(includeDocs=False, tier="full", showProgress=False)
    info = FIR.indexInfo()
    assert info["available"] is True
    assert info["schemaVersion"] == FI.INDEX_SCHEMA_VERSION
    assert info["compatible"] is True
    assert info["nDocs"] == 2
