"""EDGAR ops — calendar/insiderTrades placeholder (룰 2 mirror).

Implementation status
---------------------
- 구현 상태: **미구현 (reserved)**
- 대응 dart 모듈: ``providers/dart/ops/`` (3 파일 / 694 줄) — calendar (공시 캘린더
  예측), insiderTrades (임원거래 raw fetch).
- SEC EDGAR 측 본질:
  - **calendar 등가**: SEC 의 Filing Calendar (10-K/10-Q 분기별 due date) — DART 와
    달리 통일된 cadence (회계연도 종료 후 60/90 일) 라 통계적 예측이 단순.
  - **insiderTrades 등가**: Form 4 (insider transactions) — SEC EDGAR 의
    ``/cgi-bin/browse-edgar?action=getcompany&type=4`` 노출. 별도 데이터 표면 가능.

언제 채울 것인가
----------------
- **calendar**: 미국 회사 다종목 분석 흐름에서 due date 알림이 필요한 시점. 우선순위
  낮음 (사용자 시나리오 부재).
- **insiderTrades**: 한국 임원거래 분석 (dart/ops/insiderTrades) 정착 후 미국 등가
  요구 시. Form 4 파싱 = HTML viewer 별도 처리 + XBRL 부재로 비용 높음.

본 폴더는 mirror 만족 placeholder. ``__all__ = []``.
"""

__all__: list[str] = []
