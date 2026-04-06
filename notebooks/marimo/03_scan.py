# /// script
# requires-python = ">=3.12"
# dependencies = ["dartlab", "marimo"]
# ///

import marimo

__generated_with = "0.21.1"
app = marimo.App(width="medium")


@app.cell
def _():
    # dartlab 임포트
    import dartlab
    return (dartlab,)


@app.cell
def _(dartlab):
    # scan 가이드 — 사용 가능한 축 확인
    dartlab.scan()
    return


@app.cell
def _(dartlab):
    # 전종목 수익성 횡단 분석
    dartlab.scan("profitability")
    return


if __name__ == "__main__":
    app.run()
