"""인사이트 분석 엔진.

7영역 등급 분석 + 이상치 탐지 + 종합 요약.

사용법::

    from dartlab.analysis.financial.insight import analyzeFinancial as analyze

    result = analyze("005930")
    result.grades()        # {'performance': 'A', 'profitability': 'B', ...}
    result.anomalies       # [Anomaly(...), ...]
    result.summary         # "삼성전자는 실적, 재무건전성 등..."
    result.profile         # "premium"
"""

from dartlab.analysis.financial.insight.pipeline import analyzeFinancial, analyzeAudit

# 호환 alias — 외부 코드가 analyze 로 import 가능 (점진 마이그레이션)
analyze = analyzeFinancial
from dartlab.analysis.financial.insight.types import (
    AnalysisResult,
    Anomaly,
    AuditDataForAnomaly,
    DistressAxis,
    DistressResult,
    Flag,
    InsightResult,
    MarketDataForDistress,
    ModelScore,
)

__all__ = [
    "analyze",
    "analyzeFinancial",
    "analyzeAudit",
    "AnalysisResult",
    "Anomaly",
    "AuditDataForAnomaly",
    "DistressAxis",
    "DistressResult",
    "Flag",
    "InsightResult",
    "MarketDataForDistress",
    "ModelScore",
]
