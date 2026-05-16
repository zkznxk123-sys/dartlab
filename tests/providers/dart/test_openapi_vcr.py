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
def test_list_replay_or_record() -> None:
    """DART list.json 공시 목록 — 카세트 record (없을 때) 또는 replay (있을 때).

    카세트 부재 + DART_API_KEY 없음 → skip.
    카세트 부재 + DART_API_KEY 있음 → record 모드 (`once`, 첫 실 호출).
    카세트 존재 → replay 모드 (`none`, 네트워크 없이 검증).
    """
    import os

    import httpx

    cassette = _cassette("list.yaml")
    has_api_key = bool(os.environ.get("DART_API_KEY"))

    if not cassette.exists() and not has_api_key:
        pytest.skip(f"카세트 없음 ({cassette}) + DART_API_KEY 미설정 — 운영자 트리거 필요.")

    mode = "once" if not cassette.exists() else "none"
    vcrInstance = buildVcr(str(_CASSETTE_DIR), record_mode=mode)

    api_key = os.environ.get("DART_API_KEY", "REPLAY_NO_KEY_NEEDED")
    url = "https://opendart.fss.or.kr/api/list.json"
    params = {
        "crtfc_key": api_key,
        "corp_code": "00126380",  # 삼성전자
        "bgn_de": "20240101",
        "end_de": "20240131",
    }

    with vcrInstance.use_cassette(cassette.name):
        r = httpx.get(url, params=params, timeout=30)
        assert r.status_code == 200, f"HTTP {r.status_code}"

        # DART 응답 schema 회귀 가드
        body = r.json()
        assert "status" in body, "DART 응답에 status 누락"
        if body["status"] == "000":
            assert "list" in body, "DART 정상 응답에 list 누락"

    # sanitize 검증 — 카세트에 API key 노출 안 됨
    if cassette.exists() and api_key != "REPLAY_NO_KEY_NEEDED":
        content = cassette.read_text(encoding="utf-8")
        assert api_key not in content, "DART_API_KEY 가 카세트에 노출됨 — sanitize 실패"
