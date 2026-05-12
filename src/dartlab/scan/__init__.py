"""시장 전체 횡단분석 통합 엔트리포인트 — L1.5 횡단 엔진.

Company = 기업 하나. Scan = 기업 밖 전부. L1 (company · gather) 위에서 전체 종목
universe 를 스캔해 ranking · filter · candidate evidence table 을 만든다.
단일 종목 심층 분석은 L2 분석엔진 (analysis · credit · macro · quant · industry).

사용법::

    import dartlab

    dartlab.scan()                          # 가이드 (축 목록 + 사용법)
    dartlab.scan("governance")              # 전 상장사 거버넌스
    dartlab.scan("governance", "005930")    # 삼성전자만 필터
    dartlab.scan("ratio")                   # 가용 비율 목록
    dartlab.scan("ratio", "roe")            # 전종목 ROE
    dartlab.scan("account", "매출액")       # 전종목 매출액 시계열
    dartlab.scan("fields", "roe")           # 조건형 스크리닝 필드 검색
    dartlab.scan("screen", spec={...})       # field 조건 조합으로 후보 추출
    dartlab.scan("financial")               # 재무 8축 가이드
    dartlab.scan("financial", "수익성")      # 2-level: financial 그룹 내 수익성

본체는 thin facade. Scan 클래스/registry/resolver 는 `dartlab.scan.router`,
한글 컬럼 변환은 `dartlab.scan.rename` 에 분리 (P-S1).
"""

from __future__ import annotations

from dartlab.scan.builders.kr.core import buildChanges, buildFinance, buildReport, buildScan
from dartlab.scan.builders.kr.payload import buildScanPayload, buildUnifiedPayload
from dartlab.scan.builders.kr.snapshot import buildScanSnapshot, getScanPosition
from dartlab.scan.router import Scan, availableScans

__all__ = [
    "Scan",
    "availableScans",
    "buildChanges",
    "buildFinance",
    "buildReport",
    "buildScan",
    "buildScanPayload",
    "buildScanSnapshot",
    "buildUnifiedPayload",
    "getScanPosition",
]
