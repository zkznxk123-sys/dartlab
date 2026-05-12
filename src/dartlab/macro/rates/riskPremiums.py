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

_DEFAULTS_PATH = Path(__file__).resolve().parent.parent.parent / "reference" / "data" / "damodaranDefaults.json"


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
    """Damodaran 국가별 리스크 프리미엄 조회.

    Parameters
    ----------
    countryCode : ISO2 국가코드 (KR/US/JP/...). None 이면 currency 에서 추론.
    currency : 통화 힌트 (countryCode 없을 때)
    asOfDate : ISO date. 현재는 미사용 (월별 parquet 편입 시 활성화).

    Returns
    -------
    dict
        countryCode : str — 해결된 ISO2
        name : str — 국가명
        matureMarketERP : float — 성숙시장 기준 프리미엄 (%)
        countryRiskPremium : float — 국가 리스크 프리미엄 (%)
        totalERP : float — matureMarketERP + countryRiskPremium (%)
        riskFreeRate : float — 해당 국가 10Y 국채 (%)
        marginalTaxRate : float — 법인세율 (%)
        rating : str — Moody's 국가 등급
        source : str — "damodaran_{YYYY-MM}" | "fallback_default"
        asOfDate : str — 스냅샷 기준일
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
