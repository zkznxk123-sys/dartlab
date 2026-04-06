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
    dartlab.search("유상증자")
    return


@app.cell
def _(dartlab):
    dartlab.searchName("삼성")
    return


if __name__ == "__main__":
    app.run()
