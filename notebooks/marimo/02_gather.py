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
    # gather 가이드 — 사용 가능한 축 확인
    dartlab.gather()
    return


@app.cell
def _(dartlab):
    # 삼성전자 주가 수집
    dartlab.gather("price", "005930")
    return


if __name__ == "__main__":
    app.run()
