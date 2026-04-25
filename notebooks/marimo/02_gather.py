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
    mo.md("""# Gather

외부 시장 데이터 수집 — 주가/매크로/뉴스/수급.""")
    return

@app.cell
def _():
    import dartlab
    dartlab.gather()
    return (dartlab,)

@app.cell(hide_code=True)
def _():
    import marimo as mo
    mo.md("""## 주가""")
    return

@app.cell
def _(dartlab):
    dartlab.gather("price", "005930")
    return

@app.cell
def _(dartlab):
    dartlab.gather("price", "KOSPI")
    return

@app.cell(hide_code=True)
def _():
    import marimo as mo
    mo.md("""## 매크로""")
    return

@app.cell
def _(dartlab):
    dartlab.gather("macro")
    return

@app.cell(hide_code=True)
def _():
    import marimo as mo
    mo.md("""## 수급 (KR 전용)""")
    return

@app.cell
def _(dartlab):
    dartlab.gather("flow", "005930")
    return

@app.cell(hide_code=True)
def _():
    import marimo as mo
    mo.md("""## 뉴스""")
    return

@app.cell
def _(dartlab):
    dartlab.gather("news", "삼성전자")
    return


if __name__ == "__main__":
    app.run()
