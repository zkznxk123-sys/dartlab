# /// script
# requires-python = ">=3.12"
# dependencies = ["dartlab", "marimo"]
# ///

import marimo

__generated_with = "0.23.1"
app = marimo.App(width="medium")


@app.cell
def _():
    # AI provider 키 필요 (GEMINI_API_KEY, GROQ_API_KEY 등)
    import dartlab

    dartlab.ask("뭐할수있니")
    return


@app.cell
def _():
    # Company-bound 대화
    # dartlab.chat("005930", "배당 추세는?")
    return


if __name__ == "__main__":
    app.run()
