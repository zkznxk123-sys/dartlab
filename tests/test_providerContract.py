"""providers Protocol contract 검증 — P-트랙 룰 1 게이트 + P-PR0 isinstance runtime.

dart/edgar/edinet 3 provider 가 동일 Protocol 표면 (DocsProvider · FinanceProvider ·
FilingsProvider · MemorySafeProvider · CompanyProtocol) 만족하는지 검증.

P0.5 baseline: Protocol 일부는 아직 P1.5 에서 신설 — 미존재 시 xfail.
P1.5 이후 strict: 모든 Protocol isinstance + 메서드 시그니처 introspection 일치.
P-PR0 (2026-05-12): 실 Company 인스턴스 isinstance runtime 검증 2 함수 추가 —
    baseline 모드 (현 위반 등록 + new violation 만 fail). P-PR8 strict 전환.

게이트 활성화 단계:
    P0.5 — Protocol import 시도, ImportError 면 xfail (회귀 가드만) — 완료
    P1.5 — Protocol 신설 직후 isinstance 검증 활성 — 완료 (5 Protocol 실재)
    P-PR0 — Company 인스턴스 + namespace isinstance baseline 모드 — 본 PR
    P-PR8 — 전 contract strict (isinstanceRuntimeViolations / namespaceIsinstanceViolations 0)
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


# ── P-PR0 추가: 실 인스턴스 isinstance runtime 검증 (baseline 모드) ──

_PROVIDER_PROBES: tuple[tuple[str, str], ...] = (
    ("dart", "005930"),
    ("edgar", "AAPL"),
    ("edinet", "7203"),
)


def test_company_isinstance_runtime() -> None:
    """3 provider Company 인스턴스가 CompanyProtocol isinstance 만족 (baseline 모드).

    Protocol 5 종은 `core/protocols.py` 에 실재. 본 테스트는 *실 Company 인스턴스* 가
    Protocol 의 `__instancecheck__` 를 통과하는지 검증.

    인스턴스 생성 실패 (외부 의존 / 초기화 비용) 도 violation 으로 기록 — baseline 등록.
    P-PR8 strict 전환 시 `isinstanceRuntimeViolations` 카운트 0 강제.
    """
    from dartlab.core.protocols import CompanyProtocol

    violations: list[str] = []
    for providerName, stockCode in _PROVIDER_PROBES:
        try:
            mod = importlib.import_module(f"dartlab.providers.{providerName}.company")
            company = mod.Company(stockCode)
        except Exception as exc:  # noqa: BLE001 — 인스턴스 생성 실패 자체가 violation
            violations.append(f"{providerName}: 인스턴스 생성 실패 — {type(exc).__name__}: {exc}")
            continue

        try:
            if not isinstance(company, CompanyProtocol):
                violations.append(f"{providerName}: isinstance(co, CompanyProtocol) == False")
        finally:
            if hasattr(company, "__exit__"):
                try:
                    company.__exit__(None, None, None)
                except Exception:  # noqa: BLE001 — cleanup silent
                    pass

    baseline = _loadBaseline()
    allowed = set(baseline.get("isinstanceRuntimeViolations", []))
    new_violations = set(violations) - allowed
    assert not new_violations, (
        f"CompanyProtocol isinstance runtime 회귀 {len(new_violations)} 건: {new_violations}. "
        "P-PR0 baseline 에 등록하거나 Company 구현 보강 필요."
    )


def test_provider_namespaces_isinstance() -> None:
    """co.docs / co.finance namespace 가 각 Provider Protocol 만족 (baseline 모드).

    DocsProvider · FinanceProvider 의 메서드 시그니처 (fetchFiling/fetchStatements/...) 가
    3 provider namespace 에 매핑되는지 검증.

    namespace 부재 또는 isinstance 미통과 = violation. P-PR8 strict 전환.
    """
    from dartlab.core.protocols import DocsProvider, FinanceProvider

    violations: list[str] = []
    for providerName, stockCode in _PROVIDER_PROBES:
        try:
            mod = importlib.import_module(f"dartlab.providers.{providerName}.company")
            company = mod.Company(stockCode)
        except Exception as exc:  # noqa: BLE001
            violations.append(f"{providerName}: 인스턴스 생성 실패 — {type(exc).__name__}: {exc}")
            continue

        try:
            for nsName, protocolCls in (("docs", DocsProvider), ("finance", FinanceProvider)):
                namespace = getattr(company, nsName, None)
                if namespace is None:
                    violations.append(f"{providerName}.{nsName}: namespace 부재")
                    continue
                if not isinstance(namespace, protocolCls):
                    violations.append(f"{providerName}.{nsName}: isinstance({protocolCls.__name__}) == False")
        finally:
            if hasattr(company, "__exit__"):
                try:
                    company.__exit__(None, None, None)
                except Exception:  # noqa: BLE001
                    pass

    baseline = _loadBaseline()
    allowed = set(baseline.get("namespaceIsinstanceViolations", []))
    new_violations = set(violations) - allowed
    assert not new_violations, (
        f"Namespace Protocol isinstance 회귀 {len(new_violations)} 건: {new_violations}. "
        "P-PR0 baseline 에 등록하거나 namespace 구현 보강 필요."
    )
