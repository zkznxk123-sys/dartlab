"""DART provider builder 도메인 — Company facade backend 빌더.

Capabilities:
    - filingsCatalog: filings / disclosure / liveFilings / readFiling 빌더
    - financeStatementBuilder: BS/IS/CF/CIS/ratios 등 finance topic 빌더
    - scanAggregator: network / governance / workforce / capital / debt 빌더
    - docsSectionsAnalyzer: sections 구조 분석 (freq/coverage/outline)
    - docsProfileBuilder: profile / chapter / topicLabel 메타
    - docsSelectMatcher: select cascade 매칭 로직
    - dataDispatcher: show/select dispatch core
    - dataShapeUtils: data shape utility (transpose/clean/filter)
    - docsIndexBuilder: index rows 빌더 (finance/docs/report)
"""
