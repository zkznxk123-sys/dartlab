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
    # 종목코드로 Company 생성
    c = dartlab.Company("005930")
    return (c,)


@app.cell
def _(c):
    # 수익성 섹션 보고서 (analysis+credit+macro+quant 조합)
    c.review("수익성")
    return


if __name__ == "__main__":
    app.run()
