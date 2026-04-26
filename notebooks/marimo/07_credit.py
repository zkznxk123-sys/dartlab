# /// script
# requires-python = ">=3.12"
# dependencies = ["dartlab", "marimo"]
# ///

import marimo

__generated_with = "0.22.0"
app = marimo.App(width="medium")


@app.cell
def _():
    # credit — 독립 신용평가. 무인자 호출 = 가이드 + 종합 등급
    import dartlab
    c = dartlab.Company("005930")
    c.credit()
    return (dartlab, c)


@app.cell
def _(c):
    # 종합 등급 — dCR-AA, healthScore, pdEstimate
    c.credit("등급")
    return


@app.cell
def _(c):
    # 등급 + 서사 + 지표 시계열 + 신평사 괴리 설명
    c.credit("등급", detail=True)
    return


@app.cell
def _(c):
    # 7축 중 수익성 축
    c.credit("수익성")
    return


@app.cell
def _(c):
    # 7축 중 부채 축
    c.credit("부채")
    return


if __name__ == "__main__":
    app.run()
