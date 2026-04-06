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
    # macro 가이드 — 사용 가능한 축 확인
    dartlab.macro()
    return


@app.cell
def _(dartlab):
    # 한국 매크로 사이클 해석
    dartlab.macro("사이클", market="KR")
    return


if __name__ == "__main__":
    app.run()
