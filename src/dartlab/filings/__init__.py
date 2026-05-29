"""filings — 독립 다시장 disclosure 패키지 (옛 ``providers`` 와 무관한 새 기반).

규제 공시(DART/EDGAR/…)를 **수평화 sections SSOT** 로 노출하는 자기완결 패키지.
옛 providers 의 덕지덕지(591줄 mapper · 4-Phase runtime build · docsProfileBuilder
두꺼운 merge)를 버리고 처음부터 깨끗하게 설계.

진입점:
    >>> from dartlab.filings import Company, companies   # doctest: +SKIP
    >>> c = Company("005930")            # marketNs="kr" 기본       # doctest: +SKIP
    >>> c.show("BS")                     # finance 정규화 account×period  # doctest: +SKIP
    >>> c.show("inventoryDisclosure")    # docs sections contentRaw       # doctest: +SKIP
    >>> companies(["005930","000660"]).show("BS")   # 회사 간 비교        # doctest: +SKIP

구조:
    - ``core/`` — 시장 무관 (schema·sections reader·bridge·canonical·tagstrip·period·
      loader·memory·MarketBackend Protocol).
    - ``dart/`` — KR (config·finance·report·classify·loader·build). EDGAR/EDINET 향후.

독립성: ``dartlab.config`` + polars/lxml/huggingface_hub 만 의존. providers/scan/
dataLoader 의존 0 (providers 폐기·core 변경이 filings 를 깨뜨리지 못함).
"""

from __future__ import annotations

from dartlab.filings.company import Company
from dartlab.filings.group import Group, companies

__all__ = ["Company", "Group", "companies"]
