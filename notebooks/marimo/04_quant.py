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
    # 가이드 — 25지표 + 9신호
    c.quant()
    return (c,)


@app.cell
def _(c):
    # 종합 판단
    c.quant("종합")
    return


@app.cell
def _(c):
    # 모멘텀 / RSI
    c.quant("모멘텀")
    return


if __name__ == "__main__":
    app.run()
