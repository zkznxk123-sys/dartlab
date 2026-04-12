"""analysis/financial 임계값 중앙 관리.

calc 함수에 하드코딩된 임계값을 한 곳에 모은다.
변경 시 한 곳만 수정하면 전체 반영.
"""

from __future__ import annotations

# ══════════════════════════════════════
# 이익품질 (earningsQuality)
# ══════════════════════════════════════

#: OCF/NI 지속성 판단 기준. >= 0.5면 이익이 현금으로 실현됨
OCF_TO_NI_PERSISTENT = 0.5

#: Sloan accrual ratio 경고 기준. |ratio| > 0.10 → 이익 조작 의심
ACCRUAL_RATIO_WARNING = 0.10

# ══════════════════════════════════════
# 예측신호 (predictionSignals)
# ══════════════════════════════════════

#: 추세 신뢰도 (OLS R²)
TREND_RSQUARED_HIGH = 0.7
TREND_RSQUARED_MEDIUM = 0.4

#: 환율 민감도 (|elasticity|)
FX_SENSITIVITY_HIGH = 0.5
FX_SENSITIVITY_MODERATE = 0.2
