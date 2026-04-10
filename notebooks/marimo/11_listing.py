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
    dartlab.listing()
    return (dartlab,)


@app.cell
def _(dartlab):
    dartlab.listing("filings", corp="005930")
    return


@app.cell
def _(dartlab):
    # DART 전체 법인 (비상장 포함, corp_code 8자리)
    dartlab.listing("dartlist")
    return


if __name__ == "__main__":
    app.run()
