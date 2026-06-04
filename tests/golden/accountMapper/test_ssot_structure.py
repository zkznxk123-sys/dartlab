"""SSOT 구조 sanity + stale 재발 가드 — accountMappings.json 단일 소유.

통합 완료(S4) 후: in-code dict 가 사라지고 accountMappings.json 이 전 계정 매핑의
단일 소유. 본 가드는 그 구조 무결성과, 과거 stale _metadata 버그(파생 카운트가
실데이터와 어긋남)의 재발을 차단한다. 동등성(byte-identical 보존)은 자매 golden
``test_ssot_equivalence_*`` 가 독립 reference 구현으로 검증한다.
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.unit


def _ssot() -> dict:
    from dartlab.core.accounts.data import loadAccounts

    loadAccounts.cache_clear()
    return loadAccounts()


def test_top_level_keys() -> None:
    """SSOT top-level 키 = 단일 소유 5 구획."""
    assert set(_ssot()) == {"_metadata", "mappings", "standardAccounts", "layers", "edgar"}


def test_layers_shape() -> None:
    """layers = stage 별 5 dict (평면화 금지 — 의미 보존)."""
    layers = _ssot()["layers"]
    assert set(layers) == {"idSynonym", "nameSynonym", "snakeAlias", "labelEn", "korSynonym"}
    for name, d in layers.items():
        assert isinstance(d, dict) and d, f"layers.{name} 비정상"
        assert all(isinstance(k, str) and isinstance(v, str) for k, v in d.items())


def test_edgar_shape() -> None:
    """edgar = EDGAR tag 매핑 소스 (accounts/learnedTags/stmtOverrides)."""
    edgar = _ssot()["edgar"]
    assert set(edgar) == {"accounts", "learnedTags", "stmtOverrides"}
    assert edgar["accounts"] and all("snakeId" in a and "stmt" in a for a in edgar["accounts"])
    assert edgar["learnedTags"] and all(isinstance(v, str) for v in edgar["learnedTags"].values())
    assert all("|" in k for k in edgar["stmtOverrides"]), "stmtOverrides 키는 'tag|stmt' 인코딩"


def test_metadata_no_stale_derived_counts() -> None:
    """_metadata 에 drift 하는 파생 카운트 금지 (옛 stale 버그 재발 가드).

    옛 _metadata 는 standardAccounts/learnedSynonyms/merged 같은 *파생 카운트*를
    박아뒀고 실데이터와 어긋났다(learnedSynonyms:31489 인데 키 자체 부재). 파생
    카운트는 loader/test 가 실측해야지 메타에 박으면 drift 한다.
    """
    meta = _ssot()["_metadata"]
    forbidden = {"standardAccounts", "learnedSynonyms", "merged", "standardAccountsCount"}
    leaked = forbidden & set(meta)
    assert not leaked, f"_metadata 에 drift 파생 카운트 재유입: {leaked}"
    # 운영자 카운터는 보존
    assert "lastUpdate" in meta and "addedCount" in meta


def test_edgar_files_retired() -> None:
    """EDGAR finance mapperData 파일이 SSOT 로 흡수돼 제거됨 (단일 소유 가드).

    중복 소스(파일 + SSOT)가 다시 생기면 drift. SSOT 단일 소유 강제.
    """
    from pathlib import Path

    import dartlab

    base = Path(dartlab.__file__).parent / "providers" / "edgar" / "finance" / "mapperData"
    assert not (base / "standardAccounts.json").exists(), "EDGAR standardAccounts.json 재유입 (SSOT 중복)"
    assert not (base / "learnedSynonyms.json").exists(), "EDGAR learnedSynonyms.json 재유입 (SSOT 중복)"
