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
    # quant 가이드 — 사용 가능한 축 확인
    c.quant()
    return


@app.cell
def _(c):
    # 모멘텀 신호 분석
    c.quant("모멘텀")
    return


if __name__ == "__main__":
    app.run()
