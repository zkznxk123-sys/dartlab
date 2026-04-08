# /// script
# requires-python = ">=3.12"
# dependencies = ["dartlab", "marimo"]
# ///

import marimo

__generated_with = "0.22.0"
app = marimo.App(width="medium")


@app.cell(hide_code=True)
def _():
    import marimo as mo
    mo.md("""# Quant

주가 기술적 분석 — 25지표 + 9신호.""")
    return

@app.cell
def _():
    import dartlab
    c = dartlab.Company("005930")
    c.quant()
    return (dartlab, c)

@app.cell(hide_code=True)
def _():
    import marimo as mo
    mo.md("""## 종합 판단""")
    return

@app.cell
def _(c):
    c.quant("종합")
    return

@app.cell(hide_code=True)
def _():
    import marimo as mo
    mo.md("""## 모멘텀 / RSI""")
    return

@app.cell
def _(c):
    c.quant("모멘텀")
    return


if __name__ == "__main__":
    app.run()
