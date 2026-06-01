# /// script
# requires-python = ">=3.12"
# dependencies = ["dartlab", "marimo"]
# ///

import marimo

__generated_with = "0.22.0"
app = marimo.App(width="medium")


# Gather
#
# 외부 시장 데이터 수집 — 주가/매크로/뉴스/수급.
@app.cell
def _():
    import dartlab

    dartlab.gather()
    return (dartlab,)


# 주가
@app.cell
def _(dartlab):
    dartlab.gather("price", "005930")
    return


@app.cell
def _(dartlab):
    dartlab.gather("price", "KOSPI")
    return


# 매크로
@app.cell
def _(dartlab):
    dartlab.gather("macro")
    return


# 수급 (KR 전용)
@app.cell
def _(dartlab):
    dartlab.gather("flow", "005930")
    return


# 뉴스
@app.cell
def _(dartlab):
    dartlab.gather("news", "삼성전자")
    return


if __name__ == "__main__":
    app.run()
