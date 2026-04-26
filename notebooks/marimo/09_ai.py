# /// script
# requires-python = ">=3.12"
# dependencies = ["dartlab", "marimo"]
# ///

import marimo

__generated_with = "0.22.0"
app = marimo.App(width="medium")


@app.cell
def _():
    # ai — LLM 기반 적극적 분석가. dartlab 엔진을 도구로 호출
    # provider 키 필요 (GEMINI_API_KEY · GROQ_API_KEY · OPENAI_API_KEY 등)
    import dartlab
    return (dartlab,)


@app.cell
def _(dartlab):
    # 자연어 질문 — AI 가 코드를 작성·실행하면서 답한다
    # 키 없으면 주석 유지하고 가이드만 본다
    # dartlab.ask("삼성전자 수익성 분석해줘")
    _ = dartlab
    return


@app.cell
def _(dartlab):
    # 무료 provider 로 전환
    # dartlab.ask("삼성전자 분석", provider="gemini")
    _ = dartlab
    return


@app.cell
def _(dartlab):
    # Company-bound 대화 — 종목 컨텍스트가 자동으로 묶인다
    # dartlab.chat("005930", "배당 추세는?")
    _ = dartlab
    return


if __name__ == "__main__":
    app.run()
