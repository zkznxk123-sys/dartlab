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
    mo.md("""# Scan

전 종목 횡단 분석 — 시장 전체를 한 번에. 13축.""")
    return

@app.cell
def _():
    import dartlab
    dartlab.scan()
    return (dartlab,)

@app.cell(hide_code=True)
def _():
    import marimo as mo
    mo.md("""## 수익성 횡단""")
    return

@app.cell
def _(dartlab):
    dartlab.scan("profitability")
    return

@app.cell(hide_code=True)
def _():
    import marimo as mo
    mo.md("""## 지배구조""")
    return

@app.cell
def _(dartlab):
    dartlab.scan("governance")
    return

@app.cell(hide_code=True)
def _():
    import marimo as mo
    mo.md("""## 부채/리스크""")
    return

@app.cell
def _(dartlab):
    dartlab.scan("debt")
    return


if __name__ == "__main__":
    app.run()
