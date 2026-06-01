# /// script
# requires-python = ">=3.12"
# dependencies = ["dartlab", "marimo"]
# ///

import marimo

__generated_with = "0.23.8"
app = marimo.App(width="full")


@app.cell
def _():
    # Company facade — 종목코드 하나로 공시·재무·정형 데이터에 단일 진입점
    import dartlab
    c = dartlab.Company("005930")
    c.corpName
    return (c,)


@app.cell
def _(c):
    # filings — 모든 보고서 (DART 뷰어 URL 포함)
    c.filings().head(10)
    return


@app.cell
def _(c):
    # panel — 정부 XBRL 분류(canonicalKey) 기준 항목 × 기간 수평화 (잡는 순간 pl.DataFrame)
    c.panel(tag=False)
    return


@app.cell
def _(c):
    # 섹션 행 검색 — raw 공시 (한글명/canonicalKey)
    c.panel("매출",tag=False)
    return


@app.cell
def _(c):
    c.panel("BS")
    return


@app.cell
def _(c):
    c.panel("IS")
    return


@app.cell
def _(c):
    # 정량 finance is 데이터
    c.panel("IS",freq='year')
    return


@app.cell
def _(c):
    # 사업보고서상의 is 
    c.panel("is",freq='year')
    return


if __name__ == "__main__":
    app.run()
