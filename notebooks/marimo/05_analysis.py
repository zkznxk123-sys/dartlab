# /// script
# requires-python = ">=3.12"
# dependencies = ["dartlab", "marimo"]
# ///

import marimo

__generated_with = "0.22.0"
app = marimo.App(width="medium")


@app.cell
def _():
    import dartlab

    c = dartlab.Company("005930")
    # 가이드 — 14축 + forecast + valuation
    c.analysis()
    return (c,)


@app.cell
def _(c):
    # 수익성
    c.analysis("수익성")
    return


@app.cell
def _(c):
    # 성장성
    c.analysis("성장성")
    return


@app.cell
def _(c):
    # 안정성
    c.analysis("안정성")
    return


@app.cell
def _(c):
    # 현금흐름
    c.analysis("현금흐름")
    return


@app.cell
def _(c):
    # 매출전망
    c.analysis("매출전망")
    return


@app.cell
def _(c):
    # 가치평가
    c.analysis("가치평가")
    return


if __name__ == "__main__":
    app.run()
