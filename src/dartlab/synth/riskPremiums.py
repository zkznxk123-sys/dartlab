"""Damodaran 국가별 리스크 프리미엄 SSOT.

단일 진실의 원천. proforma.py::compute_company_wacc 가 country 파라미터로 분기.

데이터 경로:
1. 월별 갱신 parquet (`data/riskPremiums.parquet`) — scripts/dataSync/updateDamodaranERP.py 가 생성
2. 오프라인 fallback — `reference/data/damodaranDefaults.json` (패키지 내장 2024-07 스냅샷)

근거:
- Damodaran NYU Stern — Country Risk Premiums (ctryprem.html), 월 1회 갱신
- CAPM: Ke = Rf + beta × (matureMarketERP + countryRiskPremium)
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

_DEFAULTS_PATH = Path(__file__).resolve().parent.parent / "reference" / "data" / "damodaranDefaults.json"


@lru_cache(maxsize=1)
def _loadDefaults() -> dict[str, Any]:
    """패키지 내장 fallback 로드 (lru_cache — 세션당 1회)."""
    try:
        return json.loads(_DEFAULTS_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"countries": {}, "currencyToCountry": {}, "_meta": {}}


def resolveCountryCode(*, currency: str | None = None, country: str | None = None) -> str:
    """통화/국가 힌트 → ISO2 country code. 모호하면 'KR' (DART 기본).

    Parameters
    ----------
    currency : 통화 코드 (KRW/USD/JPY/...)
    country : 명시적 country code. 지정 시 currency 무시.
    """
    if country:
        code = country.strip().upper()
        if code in _loadDefaults().get("countries", {}):
            return code
    if currency:
        mapping = _loadDefaults().get("currencyToCountry", {})
        code = mapping.get(currency.strip().upper())
        if code:
            return code
    return "KR"


def loadDamodaranERP(
    countryCode: str | None = None,
    *,
    currency: str | None = None,
    asOfDate: str | None = None,
) -> dict[str, Any]:
    """Damodaran ERP (Equity Risk Premium) 국가별 룩업 + 자동 fallback.

    Capabilities:
        Aswath Damodaran (NYU Stern) 의 사실상 표준 ERP 데이터 — 국가별 성숙
        시장 ERP + 국가 리스크 프리미엄 + 무위험이자율 + 법인세율 + Moody's
        등급을 dict 로 반환. countryCode 누락 시 currency 에서 추론. DCF
        WACC 산출의 표준 입력.

    Args:
        countryCode: ISO 2-letter 코드 (예 ``"KR"``, ``"US"``, ``"JP"``).
            None 시 currency 에서 추론.
        currency: 통화 힌트 (KRW → KR, USD → US, JPY → JP). countryCode 없을 때만.
        asOfDate: ISO 8601 날짜. 현재 미사용 (월별 parquet 편입 시 활성).

    Returns:
        dict:
            - ``countryCode`` (str): ISO2 해결 결과
            - ``name`` (str): 국가명 (한국어)
            - ``matureMarketERP`` (float): 성숙시장 기준 프리미엄 (%)
            - ``countryRiskPremium`` (float): 국가 리스크 (%)
            - ``totalERP`` (float): 합계
            - ``riskFreeRate`` (float): 10Y 국채 (%)
            - ``marginalTaxRate`` (float): 법인세율 (%)
            - ``rating`` (str): Moody's 국가 등급
            - ``source`` (str): ``"damodaran_{YYYY-MM}"`` 또는 ``"fallback_default"``
            - ``asOfDate`` (str)

    Raises:
        없음 — 미지원 국가는 fallback_default 반환.

    Example:
        >>> erp = loadDamodaranERP("KR")
        >>> erp["totalERP"], erp["riskFreeRate"], erp["rating"]
        (6.8, 3.5, 'Aa2')

    Guide:
        Damodaran 의 ERP 는 매년 1 월/7 월 업데이트. 한국 totalERP ~ 6.8%
        (matureMarketERP 5.0% + countryRiskPremium 1.8%). 미국 ERP ~ 5.0%
        (mature, country risk 0). WACC 계산: Re = Rf + β × totalERP.

    SeeAlso:
        - ``loadAdamodaranBeta``: 업종별 unlevered beta
        - ``resolveCountryCode``: ISO2 코드 해결
        - ``analysis.financial.proforma.computeCompanyWacc``: WACC 본 데이터 사용
        - Damodaran, A. (2024) "Equity Risk Premiums" Working Paper

    Requires:
        ``data/synth/damodaranDefaults.json`` 로드 가능.

    AIContext:
        source="fallback_default" 결과는 정확도 낮음 — 호출자에게 명시.
        한국 회사의 WACC 산출에 미국 ERP (5.0%) 사용 금지 — KR ERP (6.8%)
        사용 필수.

    LLM Specifications:
        AntiPatterns:
            - countryCode + currency 동시 입력 — countryCode 우선, currency
              무시 (silently).
            - 미지원 국가 (EM 일부) 호출 시 fallback 그대로 인용 — 호출자가
              "근사값" 표기 필요.
        OutputSchema:
            상기 10 키 dict.
        Prerequisites:
            damodaranDefaults.json 보유 (Damodaran 데이터 추출 결과).
        Freshness:
            Damodaran 매년 1 월/7 월 업데이트. dartlab 패키지 버전 의존.
        Dataflow:
            countryCode/currency → resolveCountryCode → JSON 룩업 → fallback
            (한국 KR ~ 미국 US ~ 글로벌 평균).
        TargetMarkets: Global (90+ 국가 지원). KR/US/JP/CN/EU 주요 지원.
    """
    defaults = _loadDefaults()
    meta = defaults.get("_meta", {})
    countries: dict = defaults.get("countries", {})

    code = resolveCountryCode(currency=currency, country=countryCode)
    country = countries.get(code) or countries.get("KR") or {}

    mature = float(meta.get("matureMarketERP", 4.60))
    crp = float(country.get("countryRiskPremium", 0.60))
    total = float(country.get("totalERP", mature + crp))

    return {
        "countryCode": code,
        "name": country.get("name", code),
        "matureMarketERP": mature,
        "countryRiskPremium": crp,
        "totalERP": total,
        "riskFreeRate": float(country.get("riskFreeRate", 3.40)),
        "marginalTaxRate": float(country.get("taxRate", 24.20)),
        "rating": country.get("rating", "Aa2"),
        "source": "fallback_default",
        "asOfDate": meta.get("asOfDate", "2024-07-01"),
    }


def listSupportedCountries() -> list[str]:
    """지원 country code 목록 (audit/테스트용)."""
    return sorted(_loadDefaults().get("countries", {}).keys())
