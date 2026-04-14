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

    # 가이드 — 어떤 축이 있는지
    dartlab.gather()
    return (dartlab,)


@app.cell
def _(dartlab):
    # 주가
    dartlab.gather("price", "005930")
    return


@app.cell
def _(dartlab):
    # 코스피 지수
    dartlab.gather("price", "KOSPI")
    return


@app.cell
def _(dartlab):
    # 매크로
    dartlab.gather("macro")
    return


@app.cell
def _(dartlab):
    # 수급 (KR 전용)
    dartlab.gather("flow", "005930")
    return


@app.cell
def _(dartlab):
    # 뉴스
    dartlab.gather("news", "삼성전자")
    return


if __name__ == "__main__":
    app.run()
