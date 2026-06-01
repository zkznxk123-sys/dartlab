# /// script
# requires-python = ">=3.12"
# dependencies = ["dartlab", "marimo"]
# ///

import marimo

__generated_with = "0.22.0"
app = marimo.App(width="medium")


# Credit
#
# 독립 신용평가 엔진 — 7축 dCR 등급.
@app.cell
def _():
    import dartlab

    c = dartlab.Company("005930")
    c.credit()
    return (dartlab, c)


@app.cell
def _(c):
    c.credit("등급")
    return


@app.cell
def _(c):
    c.credit("수익성")
    return


@app.cell
def _(c):
    c.credit("부채")
    return


if __name__ == "__main__":
    app.run()
