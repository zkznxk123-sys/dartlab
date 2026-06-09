"""EngineCall 자동경로 도달성 lock — 공개 데이터 verb 가 손코딩 없이 호출 가능한지.

verb 를 추가/개선하면 EngineCall 일반 디스패치(`_genericPublicCall`) + 라이브 capability
카탈로그가 자동 노출한다 (손코딩 도구 불필요). 본 가드는 핵심 verb 가 그 자동경로에서
조용히 빠지는 회귀를 차단한다 — `dartlab.compare`/`scan`/`gather` 가 capability 에서 사라지거나
top-level callable 이 아니게 되면 fail. (runtime.mcp "도구 설계 원칙" SSOT.)
"""

from __future__ import annotations

import pytest

import dartlab
from dartlab.ai.tools.engineCall import _capabilityExists

pytestmark = pytest.mark.unit

# LLM 이 EngineCall(apiRef=...) 로 부르는 top-level 데이터 verb.
_TOPLEVEL_VERBS = ["compare", "scan", "gather"]


@pytest.mark.parametrize("verb", _TOPLEVEL_VERBS)
def test_toplevel_verb_engine_call_reachable(verb: str) -> None:
    """capability 등재(unknown_api_ref 거부 안 함) + top-level callable 존재."""
    assert _capabilityExists(verb) or _capabilityExists(f"dartlab.{verb}"), (
        f"{verb} 가 capability 카탈로그에 없음 — EngineCall 자동경로에서 빠짐"
    )
    func = getattr(dartlab, verb, None)
    assert callable(func), f"dartlab.{verb} 가 top-level callable 아님 — generic dispatch 불가"


def test_company_panel_engine_call_reachable() -> None:
    """Company.panel 도 EngineCall 전용 핸들러 + capability 로 도달 가능.

    target 없이 호출하면 'company_not_resolved'(핸들러 도달) — 'unknown_api_ref'(미도달)가 아님.
    (`dartlab.Company` 는 팩토리 함수라 클래스 속성 검사 대신 디스패치 도달로 확인.)
    """
    from dartlab.ai.tools.engineCall import engineCall

    assert _capabilityExists("Company.panel"), "Company.panel capability 누락"
    result = engineCall({"apiRef": "Company.panel", "args": {"topic": "IS"}})
    assert result.error == "company_not_resolved", (
        f"Company.panel 핸들러 미도달 (기대 company_not_resolved, 실제 {result.error})"
    )


def test_compare_dispatches_via_engine_call() -> None:
    """compare 가 실제 EngineCall 로 디스패치됨 — unknown_api_ref 가 아님(데이터 무관).

    단일 종목(계약 위반)으로 호출하면 compare 가 *실행단 ValueError* 를 낸다 = verb 가
    자동경로에서 인식·디스패치·실행됐다는 증거. 미등록이면 'unknown_api_ref' ToolResult 만 나온다.
    """
    from dartlab.ai.tools.engineCall import engineCall

    try:
        result = engineCall({"apiRef": "dartlab.compare", "args": {"codes": ["005930"]}})
    except ValueError:
        return  # verb 가 실행되어 도메인 검증 ValueError → 도달·디스패치 증명.
    assert result.error not in {"unknown_api_ref", "private_api_blocked"}, (
        f"compare 가 EngineCall 자동경로에서 거부됨: {result.error}"
    )
