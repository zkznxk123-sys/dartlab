"""공공데이터포털(data.go.kr) 금융위원회_주식시세정보 gather — KRX gather 미러.

공공누리/KOGL (비상업 + 출처표시 재배포 가능) 소스. KRX OpenAPI(제3자 제공 금지)와 달리
공개 재배포·표시가 비상업 조건으로 허용된다. 구조는 `gather/krx` 를 그대로 미러:
종목별 전체이력(likeSrtnCd) + 하루치 전종목(basDt) raw fetch → 회사 schema 정규화.

엔드포인트: apis.data.go.kr/1160100/service/GetStockSecuritiesInfoService/getStockPriceInfo
인증키(`DATA_GO_KR_KEY`, 디코딩 키)는 환경변수 자동 read 없음 — 운영자 cron/명시 전달만 (KRX 와 동일 규약).
"""

from __future__ import annotations

from .govApi import GOV_TO_STD, fetchGovBydd, fetchGovStock, normalizeGovFrame

__all__ = ["GOV_TO_STD", "fetchGovBydd", "fetchGovStock", "normalizeGovFrame"]
