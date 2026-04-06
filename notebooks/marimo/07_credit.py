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
    # credit 가이드 — 7축 목록 확인
    c.credit()
    return


@app.cell
def _(c):
    # 채무상환 능력 평가
    c.credit("채무상환")
    return


if __name__ == "__main__":
    app.run()
