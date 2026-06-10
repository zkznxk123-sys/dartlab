"""공공데이터포털(data.go.kr) 금융위원회_주식시세정보 gather.

공공누리/KOGL (비상업 + 출처표시 재배포 가능) 소스 (공개 재배포·표시가 비상업 조건으로 허용). 구조:
주가 = 종목별 전체이력(likeSrtnCd) + 하루치 전종목(basDt); 지수 = 하루치 전지수(basDt) raw
fetch → 회사/KRX-raw/KRX-지수 schema 정규화.

엔드포인트:
    주가  apis.data.go.kr/1160100/service/GetStockSecuritiesInfoService/getStockPriceInfo
    지수  apis.data.go.kr/1160100/service/GetMarketIndexInfoService/getStockMarketIndex
인증키(`DATA_GO_KR_KEY`, 디코딩 키)는 환경변수 자동 read 없음 — 운영자 cron/명시 전달만.
"""

from __future__ import annotations

from .govApi import (
    GOV_IDX_TO_KRX,
    GOV_TO_KRXRAW,
    GOV_TO_STD,
    fetchGovBydd,
    fetchGovIndex,
    fetchGovStock,
    normalizeGovFrame,
    normalizeGovIndexFrame,
    normalizeGovToKrxRaw,
)

__all__ = [
    "GOV_IDX_TO_KRX",
    "GOV_TO_KRXRAW",
    "GOV_TO_STD",
    "fetchGovBydd",
    "fetchGovIndex",
    "fetchGovStock",
    "normalizeGovFrame",
    "normalizeGovIndexFrame",
    "normalizeGovToKrxRaw",
]
