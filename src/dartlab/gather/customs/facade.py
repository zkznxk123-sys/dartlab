"""관세청 무역통계 facade — FRED/ECOS 와 동일 호출계약(.series/.catalog/.close).

월별 수출입을 산업 사이클 선행지표로 macro 회귀에 투입한다. 미국 FRED 산업지표의
한국 실수출 대응물.

Usage::

    from dartlab.gather.customs import Customs

    c = Customs()                               # DATA_GO_KR_KEY 자동 해석
    c.series("8542")                            # 반도체 월별 수출액(USD)
    c.series("8703", metric="balPayments")      # 승용차 무역수지
    c.catalog("자동차")                          # 자동차 group HS 카탈로그
"""

from __future__ import annotations

import polars as pl

from .catalog import CATALOG, getAllEntries
from .client import CustomsClient
from .series import fetchSeries


class Customs:
    """관세청 품목별 수출입실적 facade."""

    def __init__(self, apiKey: str | None = None) -> None:
        self._client = CustomsClient(apiKey=apiKey)

    def series(
        self,
        hsCode: str,
        *,
        start: str | None = None,
        end: str | None = None,
        metric: str = "expDlr",
        limit: int | None = None,
    ) -> pl.DataFrame:
        """HS 품목 월별 국가총계 수출입 시계열 (date, value).

        Capabilities: 관세청 월별 수출/수입/무역수지 시계열 — macro 회귀 외생변수.
        AIContext: 업종 수출 모멘텀이 분기 매출 6~8주 선행 — FRED 산업지표 한국 대응.

        Args:
            hsCode: HS 코드 (2/4/6자리, 예 ``"8542"``).
            start: 시작 'YYYY-MM'/'YYYYMM'. None 이면 ``"200001"``.
            end: 종료. None 이면 현재 월.
            metric: ``"expDlr"``(수출 USD, 기본)·``"impDlr"``·``"balPayments"``.
            limit: 최근 N개월만 반환 (tail). None 이면 전체.

        Returns:
            pl.DataFrame — date(Date, 월초)·value(Float64). 빈 결과는 빈 스키마.

        Raises:
            ValueError: metric 이 expDlr/impDlr/balPayments 외.
            CustomsError: API 오류.

        Requires:
            DATA_GO_KR_KEY 인증키 + 관세청 API 네트워크(HTTP).

        Example:
            >>> Customs().series("8542", start="2025-01")  # doctest: +SKIP
        """
        return fetchSeries(self._client, hsCode, start=start, end=end, metric=metric, limit=limit)

    def catalog(self, group: str | None = None) -> pl.DataFrame:
        """등록 HS 품목 카탈로그 (id/label/group/frequency/unit/description).

        Capabilities: 큐레이션된 수출주력 HS 품목 메타 — group 필터.

        Args:
            group: 산업 group 필터 (예 ``"반도체"``). None 이면 전체.

        Returns:
            pl.DataFrame — id·label·group·frequency·unit·description.

        Raises:
            없음.

        Requires:
            없음 — 정적 카탈로그(네트워크·인증 불필요).

        Example:
            >>> Customs().catalog("반도체").height
            2
        """
        entries = CATALOG.get(group, []) if group else getAllEntries()
        return pl.DataFrame(
            {
                "id": [e.id for e in entries],
                "label": [e.label for e in entries],
                "group": [e.group for e in entries],
                "frequency": [e.frequency for e in entries],
                "unit": [e.unit for e in entries],
                "description": [e.description for e in entries],
            },
            schema={
                "id": pl.Utf8,
                "label": pl.Utf8,
                "group": pl.Utf8,
                "frequency": pl.Utf8,
                "unit": pl.Utf8,
                "description": pl.Utf8,
            },
        )

    def close(self) -> None:
        """HTTP 세션 종료 (idempotent).

        Raises:
            없음.

        Example:
            >>> Customs(apiKey="x").close()
        """
        self._client.close()
