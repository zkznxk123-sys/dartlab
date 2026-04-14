# /// script
# requires-python = ">=3.12"
# dependencies = ["dartlab", "marimo"]
# ///

import marimo

__generated_with = "0.23.1"
app = marimo.App(width="medium")


@app.cell
def _():
    import dartlab

    c = dartlab.Company("TSLA")
    c.corpName
    return (c,)


@app.cell
def _(c):
    # 손익계산서 (분기)
    c.show("IS")
    return


@app.cell
def _(c):
    # 연간 합산
    c.show("IS", freq="Y")
    return


@app.cell
def _(c):
    # 행 필터
    c.select("IS")
    return


@app.cell
def _(c):
    # 주석 — 재고자산
    c.show("inventory")
    return


@app.cell
def _(c):
    c.sections.head(20)
    return


@app.cell
def _(c):
    c.filings().head(10)
    return


if __name__ == "__main__":
    app.run()
