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
    n_full = FIR.rebuildMain(includePanel=False, tier="full", showProgress=False)
    FI.clearCache()
    n_lite = FIR.rebuildMain(includePanel=False, tier="lite", sinceDate="20240601", showProgress=False)
    assert n_full == 2
    assert n_lite == 1  # 20240101 제외, 20241201 포함
    assert (FI._contentIndexDir() / "main.npz").exists()
    assert (FI._contentIndexDir("lite") / "main.npz").exists()


def test_index_info_schema_version(synthRoot):
    """빌드된 인덱스 info 에 schemaVersion 기록 + indexInfo 노출."""
    from dartlab.providers.dart.search import fieldIndex as FI
    from dartlab.providers.dart.search import fieldIndexRebuild as FIR

    _mkAllFilings(synthRoot)
    FIR.rebuildMain(includePanel=False, tier="full", showProgress=False)
    info = FIR.indexInfo()
    assert info["available"] is True
    assert info["schemaVersion"] == FI.INDEX_SCHEMA_VERSION
    assert info["compatible"] is True
    assert info["nDocs"] == 2


def _mkPanel(root):
    """flat panel parquet 합성 — 운영 스키마(data/dart/panel/{code}.parquet)."""
    import polars as pl

    panelDir = root / "dart" / "panel"
    panelDir.mkdir(parents=True, exist_ok=True)
    pl.DataFrame(
        [
            {
                "rceptNo": "20240115000001",
                "period": "2023Q4",
                "sectionLeaf": "사업의 개요",
                "contentRaw": "<P>반도체 메모리 사업 매출 성장</P>",
            }
        ]
    ).write_parquet(panelDir / "005930.parquet")
    pl.DataFrame(
        [
            {
                "rceptNo": "20250320000002",
                "period": "2025Q1",
                "sectionLeaf": "재무제표",
                "contentRaw": "<P>영업이익 흑자전환 HBM 수요</P>",
            },
        ]
    ).write_parquet(panelDir / "000660.parquet")


def test_panel_meta_from_flat_artifact(synthRoot):
    """flat panel artifact 에서 rcept_dt/report_nm 메타가 채워진다(공백 아님)."""
    import polars as pl

    from dartlab.providers.dart.search import fieldIndex as FI
    from dartlab.providers.dart.search import fieldIndexRebuild as FIR

    _mkPanel(synthRoot)
    n = FIR.rebuildMain(includeAllFilings=False, includePanel=True, tier="full", showProgress=False)
    assert n == 2
    meta = pl.read_parquet(FI._contentIndexDir() / "main_meta.parquet")
    assert set(meta["rcept_dt"].to_list()) == {"20240115", "20250320"}
    assert "사업보고서" in meta["report_nm"].to_list()
    assert set(meta["source"].to_list()) == {"panel"}


def test_lite_sincedate_keeps_recent_panel(synthRoot):
    """lite sinceDate 가 panel 을 전량 탈락시키지 않고 최근 filing 만 보존."""
    from dartlab.providers.dart.search import fieldIndex as FI
    from dartlab.providers.dart.search import fieldIndexRebuild as FIR

    _mkPanel(synthRoot)
    n = FIR.rebuildMain(
        includeAllFilings=False, includePanel=True, tier="lite", sinceDate="20250101", showProgress=False
    )
    # 20240115 제외, 20250320 보존 = 1
    assert n == 1
    assert (FI._contentIndexDir("lite") / "main.npz").exists()


def test_index_info_hasmeaning_nonempty(synthRoot):
    """meaning.json={} (degraded) 면 hasMeaning=False — 파일 존재만으로 healthy 거짓보고 금지."""
    from dartlab.providers.dart.search import fieldIndex as FI
    from dartlab.providers.dart.search import fieldIndexRebuild as FIR

    base = FI._contentIndexDir()
    (base / "main_info.json").write_text(
        '{"nDocs": 10, "avgDocLength": 5.0, "builtAt": "2026-06-02", "schemaVersion": 1}', encoding="utf-8"
    )
    (base / "meaning.json").write_text("{}", encoding="utf-8")  # degraded — 0 노드
    assert FIR.indexInfo()["hasMeaning"] is False
    (base / "meaning.json").write_text('{"유상증자결정": {"신주": 1.2}}', encoding="utf-8")
    assert FIR.indexInfo()["hasMeaning"] is True
