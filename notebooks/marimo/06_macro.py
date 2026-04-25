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
    mo.md("""# Macro

시장 레벨 매크로 해석 — 사이클/금리/자산/심리/유동성.""")
    return

@app.cell
def _():
    import dartlab
    dartlab.macro()
    return (dartlab,)

@app.cell
def _(dartlab):
    dartlab.macro("사이클")
    return

@app.cell
def _(dartlab):
    dartlab.macro("금리")
    return


if __name__ == "__main__":
    app.run()
