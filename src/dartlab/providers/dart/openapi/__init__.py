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

# dartKey 모듈은 module load 시점에 CredentialProvider 를 register (정공법 B — DIP).
# core/credentials.py 의 registry 가 dart key 정보 lookup 가능하게 한다.
from dartlab.providers.dart.openapi import dartKey as _dartKey  # noqa: F401
from dartlab.providers.dart.openapi.bulkZipFetcher import (
    FetchStats,
    buildTargetsFromDocsParquet,
    collectAllOriginalZips,
    fetchZipsParallel,
    safeWriteBytes,
    streamZipBytes,
)
from dartlab.providers.dart.openapi.client import DartClient
from dartlab.providers.dart.openapi.dart import Dart, DartCompany, OpenDart, OpenDartCompany
from dartlab.providers.dart.openapi.saver import korColumns
from dartlab.providers.dart.openapi.zipCollector import ZipDocsCollector

__all__ = [
    "OpenDart",
    "OpenDartCompany",
    "Dart",
    "DartCompany",
    "DartClient",
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
