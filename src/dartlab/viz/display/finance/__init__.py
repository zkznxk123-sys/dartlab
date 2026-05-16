"""viz/finance — 재무 데이터를 표준 JSON View 로 변환.

frontend (web · cli · 그 외 소비자) 가 dlCall("viz.finance.views.X") 로 호출.
모든 view 는 schema.View 동일 모양 반환:
  {kind, title, categories, series, evidenceBinding, meta, options?}

원칙:
- 가공 (statements/ratios) 은 dict 반환 — 내부 표현.
- views.py 가 그걸 표준 JSON View 로 포장 — frontend 진입점.
- 컬러·hex 없음. intent (의미 슬롯) 만 — frontend 가 디자인 토큰에 매핑.
- 한국어 label 은 schema 의 `label` 필드 한 곳. data 키는 영문 camelCase.
- periodKind 1 인코딩: "annual" | "quarterly".

서브모듈:
- schema.py       — View / Series / EvidenceBinding TypedDict
- normalize.py    — rawFinance → long-form
- periods.py      — 기간 헬퍼 (resolvePeriods · lastNPeriods)
- accounts.py     — K-IFRS 표준 항목 28 + extractSeries
- statements.py   — IS/BS/CF 가공 (dict 반환)
- ratios.py       — 4 비율 가공 (dict 반환)
- views.py        — 14 View 함수 (frontend 진입점) + VIEWS 디스패치
- _cache.py       — Company LRU(8) + prefetch
"""

from __future__ import annotations

from dartlab.viz.display.finance.views import VIEWS

__all__ = ["VIEWS"]
