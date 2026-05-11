"""providers Protocol contract 검증 — P-트랙 룰 1 게이트.

dart/edgar/edinet 3 provider 가 동일 Protocol 표면 (DocsProvider · FinanceProvider ·
FilingsProvider · MemorySafeProvider · CompanyProtocol) 만족하는지 검증.

P0.5 baseline: Protocol 일부는 아직 P1.5 에서 신설 — 미존재 시 xfail.
P1.5 이후 strict: 모든 Protocol isinstance + 메서드 시그니처 introspection 일치.

게이트 활성화 단계:
    P0.5 (현재) — Protocol import 시도, ImportError 면 xfail (회귀 가드만)
    P1.5 — Protocol 신설 직후 isinstance 검증 활성
    P8 — EDINET 갭 메운 뒤 전 contract strict
"""

from __future__ import annotations

import importlib
import json
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

_REPO = Path(__file__).resolve().parent.parent
_BASELINE = _REPO / "scripts" / "audit" / "_baselines" / "providerContract.json"


def _loadBaseline() -> dict:
    """baseline JSON 로드. 없으면 빈 dict — 첫 실행은 회귀 가드 noop."""
    if _BASELINE.exists():
        return json.loads(_BASELINE.read_text(encoding="utf-8"))
    return {"missingProtocols": [], "missingProviderImpls": [], "_note": "P0.5 baseline"}


def test_protocol_module_importable() -> None:
    """dartlab.core.protocols 가 import 가능해야 한다."""
    mod = importlib.import_module("dartlab.core.protocols")
    assert hasattr(mod, "CompanyProtocol"), "CompanyProtocol 부재 — core/protocols.py 손상"


def test_provider_protocols_present() -> None:
    """P1.5 후 strict: DocsProvider · FinanceProvider · FilingsProvider · MemorySafeProvider 모두 존재.

    P0.5 baseline: 미존재 항목은 _baselines/providerContract.json 의 missingProtocols 에 기록.
    """
    mod = importlib.import_module("dartlab.core.protocols")
    expected = {"DocsProvider", "FinanceProvider", "FilingsProvider", "MemorySafeProvider"}
    actual = {name for name in expected if hasattr(mod, name)}
    missing = expected - actual

    baseline = _loadBaseline()
    allowed_missing = set(baseline.get("missingProtocols", []))

    new_missing = missing - allowed_missing
    assert not new_missing, (
        f"Protocol 누락 회귀: {new_missing} (baseline 외 신규). P1.5 에서 신설하거나 baseline 갱신 필요."
    )


def test_provider_company_isinstance_baseline() -> None:
    """3 provider Company 가 CompanyProtocol isinstance 만족.

    P0.5 baseline: 미만족 provider 는 _baselines/providerContract.json 의 missingProviderImpls 에 기록.
    P8 strict: 모두 만족 필수.
    """
    from dartlab.core.protocols import CompanyProtocol

    violations: list[str] = []
    for providerName in ("dart", "edgar", "edinet"):
        try:
            mod = importlib.import_module(f"dartlab.providers.{providerName}.company")
            if not hasattr(mod, "Company"):
                violations.append(f"{providerName}: Company class 부재")
                continue
            # isinstance 호출 가능성만 검증 (실 인스턴스 생성은 무거움 — 회귀 가드는 클래스 검증만)
            CompanyCls = mod.Company
            requiredAttrs = {"show", "select", "trace", "filings"}
            missingAttrs = requiredAttrs - set(dir(CompanyCls))
            if missingAttrs:
                violations.append(f"{providerName}: {missingAttrs} 메서드 부재")
        except ImportError as exc:
            violations.append(f"{providerName}: import 실패 — {exc}")

    baseline = _loadBaseline()
    allowed = set(baseline.get("missingProviderImpls", []))
    new_violations = set(violations) - allowed
    assert not new_violations, f"Provider Company contract 회귀: {new_violations} (baseline 외 신규)."
