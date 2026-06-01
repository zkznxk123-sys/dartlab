# /// script
# requires-python = ">=3.12"
# dependencies = ["dartlab", "marimo"]
# ///

import marimo

__generated_with = "0.23.8"
app = marimo.App(width="full")


@app.cell
def _():
    # Company facade — 종목코드 하나로 공시·재무·정형 데이터에 단일 진입점
    import dartlab
    c = dartlab.Company("005930")
    c.corpName
    return (c,)


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
    # 정형 공시 — 배당 이력
    c.show("dividend")
    return


@app.cell
def _(c):
    # sections — topic × period 그리드 전체 (전 기간 비교 가능성의 핵심)
    c.sections
    return


@app.cell
def _(c):
    # filings — 모든 보고서 (DART 뷰어 URL 포함)
    c.filings().head(10)
    return


@app.cell
def _(c):
    c.show("companyOverview")   
    return


@app.cell
def _(c):
    # panel — 정부 XBRL 분류(canonicalKey) 기준 항목 × 기간 수평화 (잡는 순간 pl.DataFrame)
    c.panel
    return


@app.cell
def _(c):
    # 섹션 행 검색 — raw 공시 (한글명/canonicalKey)
    c.panel("재고")
    return


@app.cell
def _(c):
    # 강한 소스 — finance 주입 (= c.show("IS"))
    c.panel("IS")
    return


if __name__ == "__main__":
    app.run()
