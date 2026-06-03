"""DART OpenAPI 클라이언트.

from dartlab import OpenDart

d = OpenDart()
s = d("삼성전자")

s.finance(2020)                         # 2020~현재 Q1~Q4
s.report("배당", 2020)                  # 배당 2020~현재
s.filings("2024")                       # 공시
s.info()                                # 개황
s.shares()                              # 지분공시
s.saveFinance("재무.csv", 2020, kr=True) # 한글 컬럼 저장
호환 alias:
    from dartlab import Dart
"""

# DartClient·키·DartApiError 는 gather 가 fetch 전담 (ETL Extract) — core.dartClient seam 경유.
# DartKeyProvider(CredentialProvider) 등록은 core.credentials 가 gather.dart.keys 발견으로 트리거.
from dartlab.core.dartClient import DartApiError, DartClient
from dartlab.providers.dart.openapi.bulkZipFetcher import (
    FetchStats,
    buildTargetsFromDocsParquet,
    collectAllOriginalZips,
    fetchZipsParallel,
    safeWriteBytes,
    streamZipBytes,
)
from dartlab.providers.dart.openapi.dart import Dart, DartCompany, OpenDart, OpenDartCompany
from dartlab.providers.dart.openapi.saver import korColumns
from dartlab.providers.dart.openapi.zipCollector import ZipDocsCollector

__all__ = [
    "OpenDart",
    "OpenDartCompany",
    "Dart",
    "DartCompany",
    "DartClient",
    "DartApiError",
    "ZipDocsCollector",
    "FetchStats",
    "buildTargetsFromDocsParquet",
    "collectAllOriginalZips",
    "fetchZipsParallel",
    "safeWriteBytes",
    "streamZipBytes",
    "korColumns",
]

# Sections batch build — ProcessPool 병렬 + 디스크 캐시 (Phase 3 옵션 3).
# 본진 API 격상 (커밋 후) 후 사용:
#   from dartlab.providers.dart.docs.sections.diskCache import buildBatchParallel
#   results = buildBatchParallel(["005930", "035720", ...])
