# /// script
# requires-python = ">=3.12"
# dependencies = ["dartlab", "marimo"]
# ///

import marimo

__generated_with = "0.23.2"
app = marimo.App(width="medium")


@app.cell
def _():
    # scan — 전 종목 횡단 분석. 무인자 호출 = 가이드 (사용 가능한 축 목록)
    import dartlab
    dartlab.scan()
    return (dartlab,)


@app.cell
def _(dartlab):
    # 수익성 횡단 — 전 상장사 ROE/ROA/영업이익률 한 번에
    dartlab.scan("profitability")
    return


@app.cell
def _(dartlab):
    # 단일 계정 횡단 — 매출액 시계열을 전 상장사 기준으로
    dartlab.scan("account", "매출액")
    return


@app.cell
def _(dartlab):
    # 단일 비율 횡단 — ROE 만 뽑기
    dartlab.scan("ratio", "roe")
    return


@app.cell
def _(dartlab):
    # 필드 탐색형 스크리닝 — 엑셀 필터처럼 "어떤 지표를 어떤 조건으로 거를지" 적는다
    # 1) fields: 조건에 쓸 정확한 field 키를 먼저 찾는다
    field_candidates = dartlab.scan("fields", "roe")
    # 2) where: 아래 조건을 모두 만족하는 종목만 남긴다 (AND)
    #    - ROE > 10
    #    - 부채비율 0~100
    # 3) select: 결과표에 매출성장률도 같이 붙인다
    # 4) sort/limit: ROE 높은 순서로 상위 10개만 본다
    screen_spec = {
        "where": [
            {"field": "finance.ratio.roe", "op": ">", "value": 10},
            {"field": "finance.ratio.debtRatio", "op": "between", "value": [0, 100]},
        ],
        "select": ["finance.ratio.revenueGrowth"],
        "sort": {"field": "finance.ratio.roe", "desc": True},
        "limit": 10,
    }
    screen = dartlab.scan("screen", spec=screen_spec, verbose=False)
    field_candidates, screen
    return


if __name__ == "__main__":
    app.run()
