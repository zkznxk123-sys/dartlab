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
    # 자연어 질문 → AI 분석
    dartlab.ask("삼성전자 수익성 분석해줘")
    return


if __name__ == "__main__":
    app.run()
