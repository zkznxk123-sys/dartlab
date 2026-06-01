# /// script
# requires-python = ">=3.12"
# dependencies = ["dartlab", "marimo"]
# ///

import marimo

__generated_with = "0.22.0"
app = marimo.App(width="medium")


# Listing
#
# 상장 종목 / 공시 메타데이터 카탈로그.
@app.cell
def _():
    import dartlab

    dartlab.listing()
    return (dartlab,)


@app.cell
def _(dartlab):
    dartlab.listing("all")
    return


@app.cell
def _(dartlab):
    dartlab.listing("filings", corp="005930")
    return


if __name__ == "__main__":
    app.run()
