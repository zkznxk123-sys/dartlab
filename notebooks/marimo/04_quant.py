# /// script
# requires-python = ">=3.12"
# dependencies = ["dartlab", "marimo"]
# ///

import marimo

__generated_with = "0.22.0"
app = marimo.App(width="medium")


@app.cell
def _():
    # quant — 가격 기반 정량 신호 (기술/리스크/팩터). 무인자 호출 = 가이드
    import dartlab
    c = dartlab.Company("005930")
    c.quant()
    return (dartlab, c)


@app.cell
def _(c):
    # 종합 판단 — 모든 quant 축의 점수를 한 줄로
    c.quant("종합")
    return


@app.cell
def _(c):
    # 모멘텀 — RSI/MACD/이동평균 등 추세 지표
    c.quant("모멘텀")
    return


@app.cell
def _(c):
    # 변동성 — ATR/표준편차/MaxDD
    c.quant("변동성")
    return


@app.cell
def _(c):
    # 팩터 — 사이즈/밸류/모멘텀/퀄리티 노출도
    c.quant("팩터")
    return


if __name__ == "__main__":
    app.run()
