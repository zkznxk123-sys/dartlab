"""증권사 리서치 메타 스키마 — ReportMeta dataclass + DataFrame 변환.

본문은 담지 않는다 — 링크아웃에 필요한 메타만. report_id(url/제목 해시)가 dedup PK.
DataFrame 컬럼은 PRD 파케이 스키마와 동형(snake): report_id·broker·title·report_type·ticker·pub_date·url.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass

import polars as pl

_COLUMNS = [
    "report_id",
    "broker",
    "broker_name",
    "title",
    "report_type",
    "opinion",
    "ticker",
    "pub_date",
    "url",
    "author",
]


@dataclass
class ReportMeta:
    """리포트 1건의 메타 — 본문 없이 링크아웃에 필요한 최소 필드."""

    broker: str
    brokerName: str
    title: str
    url: str
    pubDate: str
    reportType: str | None = None
    author: str | None = None
    ticker: str | None = None
    opinion: str | None = None

    def reportId(self) -> str:
        """(증권사·제목·발간일) 기반 안정 해시 PK — 재수집 idempotent dedup 키.

        Args:
            없음.

        Returns:
            str — 16자리 16진 해시.

        Raises:
            없음 — 항상 결정적 해시 반환.

        Requires:
            dataclass 필드 ``broker``·``title``·``pubDate``.

        Example::

            ReportMeta("nh", "NH투자", "[한세실업] 과도한 우려", "u", "2026-06-26").reportId()
        """
        raw = f"{self.broker}|{self.title}|{self.pubDate}"
        return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:16]


def toDataFrame(items: list[ReportMeta]) -> pl.DataFrame:
    """ReportMeta 리스트를 PRD 스키마(snake 컬럼) DataFrame 으로 변환.

    Capabilities:
        - ReportMeta dataclass 리스트 → 고정 9 컬럼 polars DataFrame.
        - report_id 는 행마다 자동 계산(증권사·제목·발간일 해시).
        - 빈 입력도 동일 스키마(전부 Utf8)의 빈 DataFrame 보장.

    AIContext:
        - 메타 인덱스 표 — 리포트 *내용*이 아니라 목록·링크·종목.
        - 절대 매수/매도 신호로 재가공하지 않는다.

    Guide:
        mixins/research.py 의 brokerageReports 가 fetch 결과를 표로 만들 때 호출.

    When:
        수집/해소가 끝난 ReportMeta 리스트를 사용자/저장용 표로 낼 때.

    How:
        각 ReportMeta → dict(snake 키) → ``pl.DataFrame(rows).select(_COLUMNS)``.

    Args:
        items: ReportMeta 리스트 (빈 리스트 가능).

    Returns:
        pl.DataFrame — report_id·broker·broker_name·title·report_type·ticker·pub_date·url·author.
        비면 동일 스키마의 빈 DataFrame.

    Requires:
        polars + ReportMeta (schema 모듈 내).

    Raises:
        없음 — 빈 입력은 빈 DataFrame 반환.

    Example::

        df = toDataFrame([ReportMeta("nh", "NH투자", "t", "u", "2026-06-26")])

    See Also:
        ReportMeta : 입력 dataclass.
        mixins.research._GatherResearchMixin.brokerageReports : 본 함수 caller.
    """
    if not items:
        return pl.DataFrame({c: [] for c in _COLUMNS}, schema={c: pl.Utf8 for c in _COLUMNS})
    rows = [
        {
            "report_id": it.reportId(),
            "broker": it.broker,
            "broker_name": it.brokerName,
            "title": it.title,
            "report_type": it.reportType,
            "opinion": it.opinion,
            "ticker": it.ticker,
            "pub_date": it.pubDate,
            "url": it.url,
            "author": it.author,
        }
        for it in items
    ]
    return pl.DataFrame(rows).select(_COLUMNS)
