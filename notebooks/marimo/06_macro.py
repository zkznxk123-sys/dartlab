# /// script
# requires-python = ">=3.12"
# dependencies = ["dartlab", "marimo"]
# ///

import marimo

__generated_with = "0.22.0"
app = marimo.App(width="medium")


@app.cell
def _():
    # macro — 종목코드 없이 경제 환경을 읽는다. 무인자 호출 = 가이드
    import dartlab
    dartlab.macro()
    return (dartlab,)


@app.cell
def _(dartlab):
    # 경기 4국면 판별 (확장/둔화/수축/회복)
    dartlab.macro("사이클")
    return


@app.cell
def _(dartlab):
    # 금리 + Nelson-Siegel 수익률곡선
    dartlab.macro("금리")
    return


@app.cell
def _(dartlab):
    # 침체 예측 — LEI + Cleveland Fed 프로빗 + Hamilton RS + GDP Nowcast
    dartlab.macro("예측")
    return


@app.cell
def _(dartlab):
    # 종합 — 매크로 전체 + 투자전략 + 포트폴리오 매핑
    dartlab.macro("종합")
    return


if __name__ == "__main__":
    app.run()
