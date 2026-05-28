"""analysis/eventStudy — 사건 → 가격 영향 (newsImpact) + 역방향 (priceShockNews).

L3 newsImpact : 단일 사건 → CAR + t-stat + 동기간 news context.
L4 priceShockNews : |AR|>3σ 일자 자동 검출 + top 5 news context.
"""

from __future__ import annotations
