"""viz/dashboard — web dashboard 향 component dict + chartSpec SSOT.

포함 예정 (Phase A.5 + A.6 + C 에서 채움):
- companyCache.py — Company 인스턴스 LRU(8) + prefetch (구 dl.py 의 _COMPANY_CACHE 이동)
- financial.py — 14 컴포넌트 (viz.dashboard.financial.*)
- README.md — apiRef catalogue

`viz/financial/*` 가공 결과를 `{data, chartSpec, meta}` 3-키 dict 로 포장. ui/web 의
dashboard 컴포넌트가 `dlCall("viz.dashboard.financial.*")` 로 호출.
"""

from __future__ import annotations
