"""DART provider builder 도메인 — Company facade backend 빌더.

Capabilities:
    - filingsCatalog: filings / disclosure / liveFilings / readFiling 빌더
    - financeStatementBuilder: BS/IS/CF/CIS/ratios 등 finance topic 빌더
    - scanAggregator: network / governance / workforce / capital / debt 빌더
    - notesSplit: 주석(notes) 블록 분해 헬퍼
    - dataDispatcher: finance 통계표 dispatch core (공개 show + docs 농장 은퇴 후 finance-only)
    - dataShapeUtils: data shape utility (transpose/clean/filter)
"""
