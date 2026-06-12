# /// script
# requires-python = ">=3.12"
# dependencies = ["dartlab", "marimo"]
# ///

import marimo

__generated_with = "0.23.8"
app = marimo.App(width="medium")


@app.cell
def _():
    import dartlab

    dartlab.gather()
    return (dartlab,)


@app.cell
def _(dartlab):
    dartlab.gather("price", "005930")
    return


@app.cell
def _(dartlab):
    dartlab.gather("price", "KOSPI")
    return


@app.cell
def _(dartlab):
    dartlab.gather("macro")
    return


@app.cell
def _(dartlab):
    # 최근 수급 (기본 5거래일)
    dartlab.gather("flow", "005930")
    return


@app.cell
def _(dartlab):
    # 2010년부터 최신 거래일까지 — 자동 페이지네이션
    dartlab.gather(
        "flow",
        "005930",
        start="2010-01-04",
        sleepSec=1.0,
    )
    return


@app.cell
def _():
    # 가능한 전체 이력은 오래 걸릴 수 있어 필요할 때만 실행:
    # dartlab.gather("flow", "005930", all=True, sleepSec=1.0)
    # 여러 종목은 종목 단위 병렬 수집:
    # dartlab.gather("flow", targets=["005930", "000660"], limit=30, parallel=2)
    # 사용자 프록시가 필요하면 병렬 수집에도 같은 호출 범위로 적용:
    # dartlab.gather("flow", targets=["005930", "000660"], limit=30, parallel=2, proxy="http://user:pass@host:port")
    return


@app.cell
def _(dartlab):
    dartlab.gather("news", "삼성전자")
    return


if __name__ == "__main__":
    app.run()
