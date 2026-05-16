"""DART openapi HTTP record-replay — Track 7 (VCR 인프라).

본 트랙 SSOT — [tests/POLICY.md](../../POLICY.md) §5 Track 7.
카세트 절차 — [tests/_cassettes/README.md](../../_cassettes/README.md).

본 파일은 vcrpy 인프라 골격이다. 카세트 부재 시 skip 되며 운영자가 한 번
record 후 commit 한다. record 절차는 README 참조.

회귀 가드 표면:
- DART API 응답 컬럼 추가/삭제 시 즉시 fail.
- API key 누락 + cached 카세트로 CI 가 네트워크 없이 검증.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from tests._helpers import buildVcr

pytestmark = [pytest.mark.unit, pytest.mark.vcr]

_CASSETTE_DIR = Path(__file__).resolve().parent.parent.parent / "_cassettes" / "dart"


def _cassette(name: str) -> Path:
    return _CASSETTE_DIR / name


def test_buildVcr_creates_instance_with_sanitize_defaults() -> None:
    """buildVcr 가 표준 sanitize 룰 (api_key/crtfc_key 제거) 로 인스턴스 생성."""
    vcrInstance = buildVcr(str(_CASSETTE_DIR))
    assert "crtfc_key" in vcrInstance.filter_query_parameters
    assert "api_key" in vcrInstance.filter_query_parameters
    assert "Authorization" in vcrInstance.filter_headers


def test_buildVcr_match_on_includes_path_and_query() -> None:
    """match 룰 — path · query 까지 비교 (host + method 만으로는 부족)."""
    vcrInstance = buildVcr(str(_CASSETTE_DIR))
    assert "path" in vcrInstance.match_on
    assert "query" in vcrInstance.match_on


@pytest.mark.network
def test_corpCode_replay_or_skip() -> None:
    """DART corpCode 조회 카세트 replay — 카세트 없으면 skip.

    record 절차 (운영자 트리거 1 회):
        $env:DART_API_KEY="..."
        uv run python -X utf8 -m pytest tests/providers/dart/test_openapi_vcr.py \
            -m "network" -v --vcr-record=once

    이후 CI 는 카세트만 replay (record_mode='none').
    """
    cassette = _cassette("corpCode.yaml")
    if not cassette.exists():
        pytest.skip(f"VCR 카세트 없음: {cassette}. 운영자 트리거로 record 필요 — tests/_cassettes/README.md 참조.")

    vcrInstance = buildVcr(str(_CASSETTE_DIR), record_mode="none")
    with vcrInstance.use_cassette(cassette.name):
        # 실제 dartlab API 호출 — 카세트로 replay
        from dartlab.providers.dart.openapi.corpCode import fetchCorpCode

        df = fetchCorpCode()
        assert df is not None
        assert df.height > 0
        # 컬럼 회귀 가드 — DART API 가 응답 컬럼 바꾸면 즉시 fail
        for required_col in ("corp_code", "corp_name", "stock_code"):
            assert required_col in df.columns, f"DART corpCode 응답에서 {required_col} 컬럼 누락"
