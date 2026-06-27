"""brokerage.fetch 단위 테스트 — 디코드 + 스모크 (네트워크 0)."""

from __future__ import annotations

import importlib

import pytest

from dartlab.gather.sources.brokerage.fetch import _decode, _healthProblems

pytestmark = pytest.mark.unit

# 2개사 × 2카테고리 기대 — 헬스 판정 시나리오 공통 fixture.
_ENABLED = {"miraeasset": ["기업분석", "산업분석"], "nh": ["기업분석", "시황전략"]}
_FULL = {k: 1.0 for k in _ENABLED}


def test_smoke_import() -> None:
    importlib.import_module("dartlab.gather.sources.brokerage.fetch")
    importlib.import_module("dartlab.gather.sources.brokerage")


def test_decode_with_enc() -> None:
    raw = "리포트".encode("cp949")
    assert _decode(raw, "garbled", "cp949") == "리포트"


def test_decode_no_enc_uses_text() -> None:
    assert _decode(b"x", "이미디코드", None) == "이미디코드"


def test_health_all_healthy() -> None:
    counts = {"miraeasset": {"기업분석": 30, "산업분석": 5}, "nh": {"기업분석": 12, "시황전략": 4}}
    assert _healthProblems(counts, _FULL, _ENABLED) == []


def test_health_broker_fully_dead() -> None:
    # nh 가 enabled 인데 전 카테고리 0행 → 전체 깨짐 1건(카테고리별 중복 보고 안 함)
    counts = {"miraeasset": {"기업분석": 30, "산업분석": 5}}
    problems = _healthProblems(counts, _FULL, _ENABLED)
    assert len(problems) == 1
    assert problems[0].startswith("nh: 전체 0행")


def test_health_category_dead() -> None:
    # miraeasset 은 살아있으나 산업분석만 0행 → 카테고리 셀렉터 깨짐
    counts = {"miraeasset": {"기업분석": 30}, "nh": {"기업분석": 12, "시황전략": 4}}
    problems = _healthProblems(counts, _FULL, _ENABLED)
    assert problems == ["miraeasset/산업분석: 0행 — 보드 URL/셀렉터 깨짐 의심"]


def test_health_low_completeness() -> None:
    counts = {"miraeasset": {"기업분석": 30, "산업분석": 5}, "nh": {"기업분석": 12, "시황전략": 4}}
    comp = {"miraeasset": 1.0, "nh": 0.5}  # nh 필드 절반 누락
    problems = _healthProblems(counts, comp, _ENABLED)
    assert len(problems) == 1
    assert "파싱 완전성" in problems[0] and problems[0].startswith("nh")


def test_health_dynamic_label_no_false_positive() -> None:
    # NH 처럼 report_type 이 config 라벨과 다른 동적 브로커: cats=[] → 카테고리별 검사 생략, 총량만.
    counts = {"nh": {"ETF": 1, "기업": 6, "시황": 3, "전략": 2}}
    enabled = {"nh": []}
    assert _healthProblems(counts, {"nh": 1.0}, enabled) == []
