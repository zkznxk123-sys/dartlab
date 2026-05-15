"""viz/financial — IS / BS / CF / Ratios 가공 SSOT.

포함 예정 (Phase A.6 + B 에서 채움):
- rawNormalize.py — Company.rawFinance (14557×27) → 표준 long-form
- periods.py — reprt_code (11013/11012/11014/11011) → period label
- incomeStatement.py — IS 가공 (overview / marginTrend / revenueTrend / costStructure)
- balanceSheet.py — BS 가공 (overview / composition / leverage)
- cashFlow.py — CF 가공 (overview / waterfall / freeCashFlow)
- ratios.py — Ratios 4 (profitability / stability / efficiency / growth)

`viz/rich/financial.py` (Jupyter Table) + `viz/dashboard/financial.py` (web component)
가 모두 이 module 을 import. 가공 로직 SSOT — 외부 위치에 중복 금지.
"""

from __future__ import annotations
