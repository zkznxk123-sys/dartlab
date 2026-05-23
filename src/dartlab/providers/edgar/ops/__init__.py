"""EDGAR ops — SEC calendar + insiderTrades placeholder (룰 2 mirror).

Implementation status
---------------------
- 구현 상태 (calendar): **구현 완료 (v1)** — `calendar.py` ~180 줄.
- 구현 상태 (insiderTrades): **미구현 (reserved)** — Form 4 파싱 비용 큼.

대응 dart 모듈: ``providers/dart/ops/`` (3 파일 / 694 줄) — calendar (KR fiscal
cycle 예측), insiderTrades (임원거래 raw fetch).

SEC EDGAR 측 본질:
- **calendar**: SEC Reg S-X 의 고정 deadline (10-K 75 일 / 10-Q 40 일) 기반
  예측. dart 보다 단순 (KR 은 사업/분기/반기 3 종 + 변동 deadline).
- **insiderTrades**: Form 4 — SEC EDGAR ``/cgi-bin/browse-edgar?action=
  getcompany&type=4`` 노출. HTML viewer 파싱 + XBRL 부재로 비용 높음 (별
  cycle 진행).
"""

from dartlab.providers.edgar.ops.calendar import OUTPUT_SCHEMA, predictCalendar

__all__ = ["predictCalendar", "OUTPUT_SCHEMA"]
