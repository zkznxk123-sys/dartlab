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

    c = dartlab.Company("005930")
    return (c,)


@app.cell
def _(c):
    # 단일 섹션 (메모리 안전 — 추천)
    print(c.review("수익성").toMarkdown())
    return


@app.cell
def _(c):
    print(c.review("성장성").toMarkdown())
    return


@app.cell
def _(c):
    # AI 종합의견 포함
    # c.reviewer(guide="반도체 사이클 관점에서 평가해줘")
    return


if __name__ == "__main__":
    app.run()
