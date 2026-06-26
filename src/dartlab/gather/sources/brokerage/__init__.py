"""증권사 리서치 메타 인덱스 source — 공개 게시판 자체 스크랩(본문 0·링크아웃).

각 증권사 공개 게시판에서 리포트 메타(제목·URL·발간일·구분·종목)만 수집한다.
본문은 호스팅하지 않고 원본으로 링크아웃 — 링크는 한국 확립 판례상 합법.
관리 SSOT = config.BROKERS (증권사별 url+메커니즘+카테고리+enabled).

공개 진입점: ``getDefaultGather().brokerageReports(...)`` (mixins/research.py).
"""

from __future__ import annotations

from .config import BROKERS, enabledBrokers
from .schema import ReportMeta, toDataFrame

__all__ = [
    "BROKERS",
    "ReportMeta",
    "enabledBrokers",
    "toDataFrame",
]
