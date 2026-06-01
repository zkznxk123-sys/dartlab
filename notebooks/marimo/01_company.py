# /// script
# requires-python = ">=3.12"
# dependencies = ["dartlab", "marimo"]
# ///

import marimo

__generated_with = "0.22.0"
app = marimo.App(width="medium")


# Company
#
# panel 사상 — `c.panel` 을 잡는 순간 항목×기간 격자. 모든 공시/재무에 단일 표면.
@app.cell
def _():
    import dartlab

    c = dartlab.Company("005930")
    c.corpName
    return (dartlab, c)


# 격자 + 행 검색
@app.cell
def _(c):
    # 전체 공시 수평화 격자 (항목 × 기간)
    c.panel()
    return


@app.cell
def _(c):
    # 항목명 행 검색 (raw 공시)
    c.panel("매출")
    return


# native 재무제표 (소문자) / finance (대문자)
@app.cell
def _(c):
    # native 손익 — 사업보고서 항목 그대로, XBRL+옛 통합 (2013~)
    c.panel("is", freq="year")
    return


@app.cell
def _(c):
    # finance 손익 — XBRL 정규화 숫자
    c.panel("IS", freq="year")
    return


# native 재무비율 (소문자) / finance 비율 (대문자)
@app.cell
def _(c):
    # native 비율 — 5표 항목으로 계산 (깊은 history)
    c.panel("ratios")
    return


@app.cell
def _(c):
    # finance 비율
    c.panel("RATIOS")
    return


# 공시 / 본문 검색
@app.cell
def _(c):
    c.filings().head(10)
    return


@app.cell
def _(c):
    # 본문 전체 검색
    c.panel.search("재고")
    return


if __name__ == "__main__":
    app.run()
