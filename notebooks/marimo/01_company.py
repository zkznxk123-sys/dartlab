# /// script
# requires-python = ">=3.12"
# dependencies = ["dartlab", "marimo"]
# ///

import marimo

__generated_with = "0.22.0"
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
    # 사용 가능한 토픽 목록
    c.topics
    return


@app.cell
def _(c):
    c.sections
    return


@app.cell
def _(c):
    # 손익계산서 조회
    c.show("IS")
    return


if __name__ == "__main__":
    app.run()
