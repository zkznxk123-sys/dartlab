"""WICS 섹터 분류 — industry/compat.py에 위임.

이 모듈은 하위 호환용 shim이다. 실제 구현은 dartlab.industry.compat.
기존 소비자가 `from dartlab.core.sector.classifier import classify` 등을
그대로 사용할 수 있도록 인터페이스를 유지한다.
"""

from dartlab.industry import (
    IndustryGroup,
    Sector,
    _byValue,
    _loadSectorData,
    _matchProductKeywords,
    classify,
)

# 하위 호환: 일부 소비자가 이 dict를 직접 참조
_data = _loadSectorData()

KSIC_TO_SECTOR: dict[str, tuple] = {}
for _ksic, _m in _data.get("ksicMapping", {}).items():
    _s = _byValue(Sector, _m["sector"], Sector.UNKNOWN)
    _ig = _byValue(IndustryGroup, _m["industryGroup"], IndustryGroup.UNKNOWN)
    KSIC_TO_SECTOR[_ksic] = (_s, _ig)

MANUAL_OVERRIDES: dict[str, tuple] = {}
for _name, _m in _data.get("manualOverrides", {}).items():
    _s = _byValue(Sector, _m["sector"], Sector.UNKNOWN)
    _ig = _byValue(IndustryGroup, _m["industryGroup"], IndustryGroup.UNKNOWN)
    MANUAL_OVERRIDES[_name] = (_s, _ig)

PRODUCT_KEYWORDS: dict[tuple, list[str]] = {}
for _key, _kws in _data.get("productKeywords", {}).items():
    _parts = _key.split("|")
    if len(_parts) == 2:
        _s = _byValue(Sector, _parts[0], Sector.UNKNOWN)
        _ig = _byValue(IndustryGroup, _parts[1], IndustryGroup.UNKNOWN)
        PRODUCT_KEYWORDS[(_s, _ig)] = _kws


def _matchKeywords(products: str) -> tuple | None:
    """주요제품 키워드 매칭 — 하위 호환."""
    result = _matchProductKeywords(products, _data.get("productKeywords", {}))
    if result is None:
        return None
    sector_str, ig_str, score = result
    return (
        _byValue(Sector, sector_str, Sector.UNKNOWN),
        _byValue(IndustryGroup, ig_str, IndustryGroup.UNKNOWN),
        score,
    )


__all__ = [
    "classify",
    "KSIC_TO_SECTOR",
    "MANUAL_OVERRIDES",
    "PRODUCT_KEYWORDS",
    "_matchKeywords",
]
