# /// script
# requires-python = ">=3.12"
# dependencies = ["dartlab", "marimo"]
# ///

import marimo

__generated_with = "0.22.0"
app = marimo.App(width="medium")


@app.cell
def _():
    import dartlab

    # AI provider 설정 필요: dartlab setup
    # 예: ollama pull llama3.2 && ollama serve (무료 로컬)
    # 예: export GEMINI_API_KEY=... (무료 API)
    return (dartlab,)


@app.cell
def _(dartlab):
    # AI 분석 — 스트리밍 출력 + 전체 텍스트 반환
    dartlab.ask("삼성전자 최근 매출액 및 영업이익 분석해줘")
    return


@app.cell
def _(dartlab):
    dartlab.ask("삼성전자 성격별 비용 분류도 알수있나")
    return


if __name__ == "__main__":
    app.run()
