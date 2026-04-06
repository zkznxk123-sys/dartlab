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
    dartlab.macro()
    return


@app.cell
def _(dartlab):
    dartlab.macro("사이클", market="KR")
    return


if __name__ == "__main__":
    app.run()
