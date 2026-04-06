# /// script
# requires-python = ">=3.12"
# dependencies = ["dartlab", "marimo"]
# ///

import marimo

__generated_with = "0.21.1"
app = marimo.App(width="medium")


@app.cell
def _():
    import dartlab
    return (dartlab,)


@app.cell
def _(dartlab):
    c = dartlab.Company("005930")
    return (c,)


@app.cell
def _(c):
    c.review("수익성")
    return


if __name__ == "__main__":
    app.run()
