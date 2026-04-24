# /// script
# requires-python = ">=3.12"
# dependencies = ["dartlab", "marimo"]
# ///

import marimo

__generated_with = "0.23.2"
app = marimo.App(width="medium")


@app.cell
def _():
    import dartlab

    # 가이드 — 어떤 축이 있는지
    dartlab.gather()
    return (dartlab,)


@app.cell
def _(dartlab):
    # 주가
    dartlab.gather("price", "005930")
    return


@app.cell
def _(dartlab):
    # 코스피 지수
    dartlab.gather("price", "KOSPI")
    return


@app.cell
def _(dartlab):
    # KRX 종가 회사별 시계열 — target="close" (기본), 행=stockCode+corpName, 열=일자
    dartlab.gather(
        "krx",
        start="2025-06-01", 
        end="2025-06-30",
    )
    return


@app.cell
def _(dartlab):
    # 거래량 매트릭스 — target positional 만 변경
    dartlab.gather(
        "krx", "volume",
        start="2025-06-01", end="2026-04-24",
        stockCodes=["005930", "000660", "035720", "207940", "005380"],
    )
    return


@app.cell
def _(dartlab):
    # 보조지표 자동 — target="rsi14" 전종목 동시 group_by 계산
    dartlab.gather(
        "krx", "rsi14",
        start="2026-01-24", end="2026-04-24",
        stockCodes=["005930", "000660", "035720"],
    )
    return


@app.cell
def _(dartlab):
    # 시총 wide + 단일종목 OHLCV+30지표 (gather/price 의 indicators 옵션)
    dartlab.gather("price", "005930", indicators=["ma20", "rsi14", "macd", "atr14"])
    return


@app.cell
def _(dartlab):
    # target="raw" — long DataFrame escape hatch (events join 등 자유 가공)
    # 본인 KRX 키 직접: import os; gather("krx", "close", start="...", apiKey=os.environ["KRX_API_KEY"])
    dartlab.gather("krx", "raw", start="2025-01-31")  # 단일일자는 start 만
    return


@app.cell
def _(dartlab):
    # 매크로
    dartlab.gather("macro")
    return


@app.cell
def _(dartlab):
    # 수급 (KR 전용)
    dartlab.gather("flow", "005930")
    return


@app.cell
def _(dartlab):
    # 뉴스
    dartlab.gather("news", "삼성전자")
    return


if __name__ == "__main__":
    app.run()
