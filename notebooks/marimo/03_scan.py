# /// script
# requires-python = ">=3.12"
# dependencies = ["dartlab", "marimo"]
# ///

import marimo

__generated_with = "0.23.2"
app = marimo.App(width="medium")


@app.cell
def _():
    import dartlab

    # 가이드 — 13축
    dartlab.scan()
    return (dartlab,)


@app.cell
def _(dartlab):
    dartlab.scan("account", "매출액")
    return


if __name__ == "__main__":
    app.run()
