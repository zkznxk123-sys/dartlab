"""EDGAR report extractors — 10-K/XBRL에서 구조화 데이터 추출."""

from dartlab.providers.edgar.report.xbrlLoader import edgarFinancePath, loadXbrlTags

__all__ = ["edgarFinancePath", "loadXbrlTags"]
