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
    mo.md("""# Story

4엔진 조립 보고서 — analysis + credit + macro + quant. 6막 서사.""")
    return

@app.cell
def _():
    import dartlab
    c = dartlab.Company("005930")
    return (dartlab, c)

@app.cell(hide_code=True)
def _():
    import marimo as mo
    mo.md("""## 단일 섹션 (메모리 안전 — 추천)""")
    return

@app.cell
def _(c):
    print(c.story("수익성").toMarkdown())
    return

@app.cell
def _(c):
    print(c.story("성장성").toMarkdown())
    return

@app.cell(hide_code=True)
def _():
    import marimo as mo
    mo.md("""## AI 종합의견은 dartlab.ask() 로""")
    return

@app.cell
def _(dartlab):
    # dartlab.ask("삼성전자 반도체 사이클 관점에서 평가해줘")
    return


if __name__ == "__main__":
    app.run()
