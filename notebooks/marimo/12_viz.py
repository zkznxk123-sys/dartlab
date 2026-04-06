# /// script
# requires-python = ">=3.12"
# dependencies = ["dartlab", "marimo"]
# ///

import marimo

__generated_with = "0.21.1"
app = marimo.App(width="medium")


@app.cell
def _():
    from dartlab.viz import emit_chart
    return (emit_chart,)


@app.cell
def _(emit_chart):
    emit_chart({
        "chartType": "line",
        "title": "삼성전자 매출 추이",
        "categories": ["2021", "2022", "2023", "2024", "2025"],
        "series": [{"name": "매출 (조원)", "data": [279.6, 302.2, 258.9, 300.9, 333.6]}],
    })
    return


if __name__ == "__main__":
    app.run()
