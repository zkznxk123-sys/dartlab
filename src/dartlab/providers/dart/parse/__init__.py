"""DART provider parse 도메인 — 공시 viewer 페이지 파싱 + table 변환 + diff.

Capabilities:
    - viewerPageExtractor: DART 공시 뷰어 페이지 HTML → text/sub-docs 파싱
    - tableHorizontalizer: markdown table 기간 간 수평화
    - diffEvaluator: 텍스트 변화 추적 (기간 비교)
"""
