# /// script
# requires-python = ">=3.12"
# dependencies = ["dartlab", "marimo"]
# ///

import marimo

__generated_with = "0.22.0"
app = marimo.App(width="medium")


@app.cell
def _():
    # listing — 종목/공시/topic 카탈로그. 무인자 호출 = 가이드
    import dartlab
    dartlab.listing()
    return (dartlab,)


@app.cell
def _(dartlab):
    # 전 상장사 메타 — 코드/이름/섹터/시장
    dartlab.listing("all")
    return


@app.cell
def _(dartlab):
    # 단일 종목의 모든 공시 메타데이터
    dartlab.listing("filings", corp="005930")
    return


if __name__ == "__main__":
    app.run()
