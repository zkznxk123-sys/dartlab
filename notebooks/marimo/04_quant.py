# /// script
# requires-python = ">=3.12"
# dependencies = ["dartlab", "marimo"]
# ///

import marimo

__generated_with = "0.22.0"
app = marimo.App(width="medium")


# Quant
#
# 주가 기술적 분석 — 25지표 + 9신호.
@app.cell
def _():
    import dartlab

    c = dartlab.Company("005930")
    c.quant()
    return (dartlab, c)


# 종합 판단
@app.cell
def _(c):
    c.quant("종합")
    return


# 모멘텀 / RSI
@app.cell
def _(c):
    c.quant("모멘텀")
    return


if __name__ == "__main__":
    app.run()
