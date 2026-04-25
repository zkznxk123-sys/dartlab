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
    mo.md("""# Analysis

14축 재무 분석 + forecast + valuation. 6막 인과 구조.""")
    return

@app.cell
def _():
    import dartlab
    c = dartlab.Company("005930")
    c.analysis()
    return (dartlab, c)

@app.cell(hide_code=True)
def _():
    import marimo as mo
    mo.md("""## financial 그룹""")
    return

@app.cell
def _(c):
    c.analysis("수익성")
    return

@app.cell
def _(c):
    c.analysis("성장성")
    return

@app.cell
def _(c):
    c.analysis("안정성")
    return

@app.cell
def _(c):
    c.analysis("현금흐름")
    return

@app.cell(hide_code=True)
def _():
    import marimo as mo
    mo.md("""## forecast / valuation""")
    return

@app.cell
def _(c):
    c.analysis("매출전망")
    return

@app.cell
def _(c):
    c.analysis("가치평가")
    return


if __name__ == "__main__":
    app.run()
