# /// script
# requires-python = ">=3.12"
# dependencies = ["dartlab", "marimo"]
# ///

import marimo

__generated_with = "0.23.2"
app = marimo.App(width="medium")


@app.cell
def _():
    # gather — 외부 시장 데이터 (주가/수급/매크로/뉴스). 무인자 호출 = 가이드
    import dartlab
    dartlab.gather()
    return (dartlab,)


@app.cell
def _(dartlab):
    # KR OHLCV — 종목코드만 넘기면 한국 시장으로 자동 라우팅
    dartlab.gather("price", "005930")
    return


@app.cell
def _(dartlab):
    # 지수도 같은 인터페이스
    dartlab.gather("price", "KOSPI")
    return


@app.cell
def _(dartlab):
    # KRX 전 상장사 종가 — start 만 지정하면 그 시점부터 현재까지
    dartlab.gather("krx", "close", start="20210101")
    return


@app.cell
def _(dartlab):
    # 매크로 지표 — 미국 FRED + 한국 ECOS 자동 라우팅
    dartlab.gather("macro")
    return


@app.cell
def _(dartlab):
    # 수급 (외국인/기관/개인 순매수)
    dartlab.gather("flow", "005930")
    return


@app.cell
def _(dartlab):
    # 뉴스 — Google News RSS
    dartlab.gather("news", "삼성전자")
    return


if __name__ == "__main__":
    app.run()
