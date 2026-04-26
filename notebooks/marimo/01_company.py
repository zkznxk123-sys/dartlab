# /// script
# requires-python = ">=3.12"
# dependencies = ["dartlab", "marimo"]
# ///

import marimo

__generated_with = "0.22.0"
app = marimo.App(width="medium")


@app.cell
def _():
    # Company facade — 종목코드 하나로 공시·재무·정형 데이터에 단일 진입점
    import dartlab
    c = dartlab.Company("005930")
    c.corpName
    return (dartlab, c)


@app.cell
def _(c):
    # 사용 가능한 topic 목록 — show/select 의 인자가 된다
    c.topics
    return


@app.cell
def _(c):
    # 손익계산서 — 분기 단위가 기본
    c.show("IS")
    return


@app.cell
def _(c):
    # 같은 IS 를 연간 합산으로
    c.show("IS", freq="Y")
    return


@app.cell
def _(c):
    # 행 필터 — 매출/영업이익/순이익만
    c.select("IS", ["매출액", "영업이익", "당기순이익"])
    return


@app.cell
def _(c):
    # 주석(Notes) — 재고자산 분해 (원재료/재공품/제품)
    c.show("inventory")
    return


@app.cell
def _(c):
    # 정형 공시 — 배당 이력
    c.show("dividend")
    return


@app.cell
def _(c):
    # sections — topic × period 그리드 전체 (전 기간 비교 가능성의 핵심)
    c.sections.head(20)
    return


@app.cell
def _(c):
    # facts — 모든 XBRL/공시 fact 의 long-form
    c.facts.head(20)
    return


@app.cell
def _(c):
    # trace — 어느 보고서/태그에서 왔는지 source provenance
    c.trace("BS")
    return


@app.cell
def _(c):
    # filings — 모든 보고서 (DART 뷰어 URL 포함)
    c.filings().head(10)
    return


@app.cell
def _(c):
    # diff — 작년 대비 텍스트 변화
    c.diff()
    return


if __name__ == "__main__":
    app.run()
