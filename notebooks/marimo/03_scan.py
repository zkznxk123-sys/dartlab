# /// script
# requires-python = ">=3.12"
# dependencies = ["dartlab", "marimo"]
# ///

import marimo

__generated_with = "0.22.0"
app = marimo.App(width="medium")


# Scan
#
# 전 종목 횡단 분석 — 시장 전체를 한 번에. 13축.
@app.cell
def _():
    import dartlab

    dartlab.scan()
    return (dartlab,)


# 수익성 횡단
@app.cell
def _(dartlab):
    dartlab.scan("profitability")
    return


# 지배구조
@app.cell
def _(dartlab):
    dartlab.scan("governance")
    return


# 부채/리스크
@app.cell
def _(dartlab):
    dartlab.scan("debt")
    return


if __name__ == "__main__":
    app.run()
