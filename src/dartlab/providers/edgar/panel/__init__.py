"""EDGAR panel (공시 수평화) read 표면 — market-neutral reader 재사용 (marketNs="us").

``providers.dart.panel`` 의 ``Panel`` 을 그대로 재사용한다 (EDGAR 도 동일 schema·canonicalKey
계약, 값만 us-gaap). US panel artifact 가 있으면 ``Panel(cik, marketNs="us")`` 로 read.

공개표면 (deep leaf import 금지, R6):
    - ``Panel`` (``Panel(cik, marketNs="us")``) — 한 회사 공시 수평화 보드.
"""

from dartlab.providers.dart.panel import Panel

__all__ = ["Panel"]
