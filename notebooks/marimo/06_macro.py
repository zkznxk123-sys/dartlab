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
    # 가이드 — 사이클/금리/자산/심리/유동성
    dartlab.macro()
    return (dartlab,)


@app.cell
def _(dartlab):
    # 사이클
    dartlab.macro("사이클")
    return


@app.cell
def _(dartlab):
    # 금리
    dartlab.macro("금리")
    return


if __name__ == "__main__":
    app.run()
