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
    # 가이드 — 7축 dCR 등급
    c.credit()
    return (c,)


@app.cell
def _(c):
    # 등급
    c.credit("등급")
    return


@app.cell
def _(c):
    # 수익성
    c.credit("수익성")
    return


@app.cell
def _(c):
    # 부채
    c.credit("부채")
    return


if __name__ == "__main__":
    app.run()
