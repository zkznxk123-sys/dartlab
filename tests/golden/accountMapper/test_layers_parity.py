"""Parity 가드 — SSOT JSON ``layers``/``edgar`` == in-code dict/EDGAR 소스.

통합 마이그레이션 중간 단계(S1~S3)에서 단일 SSOT JSON 과 아직 살아있는 in-code
dict 가 *동일* 함을 강제. 둘이 어긋나면 (한쪽만 수정) 즉시 fail → drift 차단.

S4 에서 in-code dict 가 제거되면 본 테스트는 "SSOT layers 존재 + 형태" 검증으로
축소된다 (그 시점 비교 대상이 사라지므로). 그때까지 byte-동일 강제.
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.unit


def _ssot() -> dict:
    from dartlab.core.utils.labels import _loadAccountMappings

    _loadAccountMappings.cache_clear()
    return _loadAccountMappings()


def test_layers_present() -> None:
    """SSOT 에 layers/edgar 키 존재 (통합 1단계 완료 신호)."""
    data = _ssot()
    assert set(data["layers"]) == {"idSynonym", "nameSynonym", "snakeAlias", "labelEn", "korSynonym"}
    assert set(data["edgar"]) == {"accounts", "learnedTags", "stmtOverrides"}


def test_dart_layers_match_incode() -> None:
    """layers.idSynonym/nameSynonym == mapper.py in-code dict (S4 전까지)."""
    try:
        from dartlab.providers.dart.finance.mapper import ACCOUNT_NAME_SYNONYMS, ID_SYNONYMS
    except ImportError:
        pytest.skip("in-code dict 제거됨 (S4+) — parity 비교 대상 없음")
    layers = _ssot()["layers"]
    assert layers["idSynonym"] == dict(ID_SYNONYMS)
    assert layers["nameSynonym"] == dict(ACCOUNT_NAME_SYNONYMS)


def test_labels_layers_match_incode() -> None:
    """layers.snakeAlias/labelEn/korSynonym == labels.py in-code dict (S4 전까지)."""
    from dartlab.core.utils.labels import _EDGAR_LABELS, _KR_SYNONYMS, SNAKEID_ALIASES

    if not isinstance(SNAKEID_ALIASES, dict):  # 방어
        pytest.skip("SNAKEID_ALIASES 비정상")
    layers = _ssot()["layers"]
    # S4 후 in-code dict 가 SSOT 에서 로드되면 동일성은 자명 — 그 전엔 진짜 비교
    assert layers["snakeAlias"] == dict(SNAKEID_ALIASES)
    assert layers["labelEn"] == dict(_EDGAR_LABELS)
    assert layers["korSynonym"] == dict(_KR_SYNONYMS)


def test_edgar_sources_match_files() -> None:
    """edgar.accounts/learnedTags == EDGAR mapperData 파일 (S4 파일 삭제 전까지)."""
    import json
    from pathlib import Path

    import dartlab

    base = Path(dartlab.__file__).parent / "providers" / "edgar" / "finance" / "mapperData"
    saPath = base / "standardAccounts.json"
    lsPath = base / "learnedSynonyms.json"
    if not saPath.exists() or not lsPath.exists():
        pytest.skip("EDGAR mapperData 파일 제거됨 (S4+) — SSOT 단일 소유")
    edgar = _ssot()["edgar"]
    assert edgar["accounts"] == json.loads(saPath.read_text(encoding="utf-8"))["accounts"]
    assert edgar["learnedTags"] == json.loads(lsPath.read_text(encoding="utf-8")).get("tagMappings", {})


def test_edgar_stmt_overrides_roundtrip() -> None:
    """edgar.stmtOverrides ("tag|stmt") == STMT_OVERRIDES tuple 라운드트립."""
    try:
        from dartlab.providers.edgar.finance.mapper import STMT_OVERRIDES
    except ImportError:
        pytest.skip("STMT_OVERRIDES 제거됨 (S4+)")
    enc = _ssot()["edgar"]["stmtOverrides"]
    expected = {f"{tag}|{stmt}": sid for (tag, stmt), sid in STMT_OVERRIDES.items()}
    assert enc == expected
