# /// script
# requires-python = ">=3.12"
# dependencies = ["dartlab", "marimo"]
# ///

import marimo

__generated_with = "0.22.0"
app = marimo.App(width="medium")


@app.cell
def _():
    # scan — 전 종목 횡단 분석. 무인자 호출 = 가이드 (사용 가능한 축 목록)
    import dartlab
    dartlab.scan()
    return (dartlab,)


@app.cell
def _(dartlab):
    # 수익성 횡단 — 전 상장사 ROE/ROA/영업이익률 한 번에
    dartlab.scan("profitability")
    return


@app.cell
def _(dartlab):
    # 지배구조 — 최대주주/이사회/감사 등 거버넌스 횡단
    dartlab.scan("governance")
    return


@app.cell
def _(dartlab):
    # 부채/리스크 — 부채비율/이자보상배율 등 안정성 횡단
    dartlab.scan("debt")
    return


@app.cell
def _(dartlab):
    # 단일 계정 횡단 — 매출액 시계열을 전 상장사 기준으로
    dartlab.scan("account", "매출액")
    return


@app.cell
def _(dartlab):
    # 단일 비율 횡단 — ROE 만 뽑기
    dartlab.scan("ratio", "roe")
    return


if __name__ == "__main__":
    app.run()
