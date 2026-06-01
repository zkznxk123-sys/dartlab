# /// script
# requires-python = ">=3.12"
# dependencies = ["dartlab", "marimo"]
# ///

import marimo

__generated_with = "0.22.0"
app = marimo.App(width="medium")


# Search
#
# 전체 공시 원문 검색 — stem ID 역인덱스. 모델 불필요, cold start 0ms.
@app.cell
def _():
    import dartlab

    dartlab.search("유상증자")
    return (dartlab,)


@app.cell
def _(dartlab):
    dartlab.search("대표이사 변경", corp="005930")
    return


@app.cell
def _(dartlab):
    dartlab.searchName("삼성")
    return


if __name__ == "__main__":
    app.run()
