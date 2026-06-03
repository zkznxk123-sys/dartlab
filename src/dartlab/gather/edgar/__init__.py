"""gather EDGAR/SEC 도메인 — 모든 SEC network fetch 전담 (ETL Extract).

providers/edgar (build/read) 와 분리. client·submissions·facts·tickers·docs·bulk·
universe fetch 를 gather 가 전담. providers build/read 는 core.edgarClient/edgarBuild
seam 으로 접근 (providers\u2620gather 단방향).

서브모듈로 직접 import (lazy __init__ — 순환 회피).
"""
