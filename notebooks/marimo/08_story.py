# /// script
# requires-python = ">=3.12"
# dependencies = ["dartlab", "marimo"]
# ///

import marimo

__generated_with = "0.22.0"
app = marimo.App(width="medium")


@app.cell
def _():
    # story — 4엔진(analysis + credit + macro + quant) 조합 보고서. 6막 서사
    import dartlab
    c = dartlab.Company("005930")
    return (dartlab, c)


@app.cell
def _(c):
    # 단일 섹션 (메모리 안전 — 추천). markdown 문자열로 출력
    print(c.story("수익성").toMarkdown())
    return


@app.cell
def _(c):
    # 다른 섹션도 같은 패턴
    print(c.story("성장성").toMarkdown())
    return


@app.cell
def _(c):
    # 안정성 (부채비율 + 유동성 인과)
    print(c.story("안정성").toMarkdown())
    return


@app.cell
def _(dartlab):
    # AI 종합의견은 dartlab.ask() — 보고서 + 판단 한 번에
    # dartlab.ask("삼성전자 반도체 사이클 관점에서 평가해줘")
    _ = dartlab
    return


if __name__ == "__main__":
    app.run()
