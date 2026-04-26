# /// script
# requires-python = ">=3.12"
# dependencies = ["dartlab", "marimo"]
# ///

import marimo

__generated_with = "0.22.0"
app = marimo.App(width="medium")


@app.cell
def _():
    # search — 공시 시맨틱 검색 (stem ID 역인덱스, 모델 불필요, cold start 0ms)
    # beta — 인덱스 신선도 한계. 단일 종목은 Company.disclosure 권장
    import dartlab
    dartlab.search("유상증자 결정")
    return (dartlab,)


@app.cell
def _(dartlab):
    # 종목 필터 — 특정 회사 공시만
    dartlab.search("대표이사 변경", corp="005930")
    return


@app.cell
def _(dartlab):
    # 자연어 쿼리도 동작 (정형 키워드가 아니어도 매칭)
    dartlab.search("회사가 돈을 빌렸다")
    return


@app.cell
def _(dartlab):
    # 종목명 검색 — 코드를 모를 때
    dartlab.searchName("삼성")
    return


if __name__ == "__main__":
    app.run()
