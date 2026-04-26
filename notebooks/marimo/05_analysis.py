# /// script
# requires-python = ">=3.12"
# dependencies = ["dartlab", "marimo"]
# ///

import marimo

__generated_with = "0.22.0"
app = marimo.App(width="medium")


@app.cell
def _():
    # analysis — 14축 재무 분석 + forecast + valuation. 무인자 호출 = 가이드
    import dartlab
    c = dartlab.Company("005930")
    c.analysis()
    return (dartlab, c)


@app.cell
def _(c):
    # 수익성 — 마진 추이, ROE/ROA 분해
    c.analysis("수익성")
    return


@app.cell
def _(c):
    # 성장성 — 매출/이익 성장률과 인과
    c.analysis("성장성")
    return


@app.cell
def _(c):
    # 안정성 — 부채비율, 유동성, 이자보상배율
    c.analysis("안정성")
    return


@app.cell
def _(c):
    # 현금흐름 — OCF/FCF 패턴, 재투자 vs 환원
    c.analysis("현금흐름")
    return


@app.cell
def _(c):
    # 매출전망 — 시계열 forecast + 시나리오
    c.analysis("매출전망")
    return


@app.cell
def _(c):
    # 가치평가 — DCF/Multiple/RIM 다중 모델
    c.analysis("가치평가")
    return


if __name__ == "__main__":
    app.run()
