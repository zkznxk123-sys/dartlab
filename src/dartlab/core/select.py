"""SelectResult / ChartResult — select() 반환 래퍼.

c.select("IS", ["매출액", "영업이익"]).chart() 체이닝을 지원한다.
DataFrame 위임으로 기존 Polars 코드와 100% 호환.

렌더링은 render(fmt) 하나에 집중:
- render("rich")     → Rich Console 테이블 (터미널)
- render("html")     → Rich Console export_html (Jupyter/Marimo)
- render("markdown") → 마크다운 테이블
- render("json")     → JSON 직렬화
"""

from __future__ import annotations

import json
import re
from typing import Any

import polars as pl

from dartlab.core.formatting import formatComma, formatDecimal
from dartlab.core.palette import COLORS as _COLORS

_PERIOD_RE = re.compile(r"^\d{4}(Q[1-4])?$")


def _isPeriod(name: str) -> bool:
    return bool(_PERIOD_RE.fullmatch(name))


def _periodCols(df: pl.DataFrame) -> list[str]:
    return [c for c in df.columns if _isPeriod(c)]


def _metaCols(df: pl.DataFrame) -> list[str]:
    return [c for c in df.columns if not _isPeriod(c)]


def _isNumericDf(df: pl.DataFrame) -> bool:
    """기간 컬럼 중 숫자 타입이 하나라도 있으면 True."""
    for c in _periodCols(df):
        if df[c].dtype in (pl.Float64, pl.Float32, pl.Int64, pl.Int32):
            return True
    return False


def _fmtVal(val: Any) -> str:
    """셀 값 포맷 — select 특화: 큰 float 은 정수 반올림, 작은 float 은 .2f."""
    if val is None:
        return "-"
    if isinstance(val, float) and abs(val) < 1:
        return formatDecimal(val, decimals=2, nullStr="-")
    return formatComma(val, decimals=0)


# ══════════════════════════════════════
# SelectResult
# ══════════════════════════════════════


class SelectResult:
    """select() 반환 객체 — DataFrame 위임 + 체이닝."""

    __slots__ = ("_df", "_topic", "_meta")

    def __init__(self, df: pl.DataFrame, topic: str, meta: dict | None = None):
        self._df = df
        self._topic = topic
        self._meta = meta or {}

    # ── DataFrame 위임 ──

    def __getattr__(self, name: str) -> Any:
        return getattr(self._df, name)

    def __getitem__(self, key: Any) -> Any:
        return self._df[key]

    def __len__(self) -> int:
        return len(self._df)

    def __str__(self) -> str:
        return str(self._df)

    # ── 속성 ──

    @property
    def df(self) -> pl.DataFrame:
        """내부 DataFrame."""
        return self._df

    @property
    def topic(self) -> str:
        """데이터 topic명."""
        return self._topic

    @property
    def meta(self) -> dict:
        """corpName, currency 등 메타데이터."""
        return self._meta

    @property
    def isNumeric(self) -> bool:
        """기간 컬럼에 숫자 타입이 있으면 True."""
        return _isNumericDf(self._df)

    # ── render(fmt) 통합 ──

    def render(self, fmt: str = "rich") -> str:
        """통합 렌더러."""
        if fmt == "rich":
            return self._renderRich()
        if fmt == "html":
            return self._renderHtml()
        if fmt == "markdown":
            return self.toMarkdown()
        if fmt == "json":
            return self.toJson()
        raise ValueError(f"지원하지 않는 렌더링 형식: {fmt}")

    def __repr__(self) -> str:
        return self.render("rich")

    def _repr_html_(self) -> str:
        return self.render("html")

    def _repr_markdown_(self) -> str:
        return self.render("markdown")

    # ── Rich 렌더링 ──

    def _title(self) -> str:
        name = self._meta.get("corpName", "")
        if name:
            return f"{name} — {self._topic}"
        return self._topic

    def _toRichTable(self):
        """DataFrame → rich.table.Table."""
        from rich.box import SIMPLE_HEAD
        from rich.table import Table
        from rich.text import Text

        periods = _periodCols(self._df)
        metas = _metaCols(self._df)
        cols = metas + periods

        table = Table(
            box=SIMPLE_HEAD,
            title=self._title(),
            title_style="bold",
            padding=(0, 1),
            show_edge=False,
        )

        for c in cols:
            isPeriodCol = c in periods
            justify = "right" if isPeriodCol else "left"
            style = "cyan" if isPeriodCol else "bold"
            table.add_column(c, justify=justify, style=style, no_wrap=True)

        rows = self._df.to_dicts()
        for row in rows:
            cells: list[str | Text] = []
            for c in cols:
                val = row.get(c)
                cells.append(_fmtVal(val))
            table.add_row(*cells)

        return table

    def _renderRich(self) -> str:
        """Rich Console capture → 텍스트."""
        import io

        from rich.console import Console

        if not self.isNumeric:
            return self._renderRichText()
        console = Console(record=True, file=io.StringIO(), width=120)
        console.print(self._toRichTable())
        return console.export_text()

    def _renderRichText(self) -> str:
        """텍스트 DataFrame → Rich 텍스트 출력."""
        import io

        from rich.console import Console
        from rich.panel import Panel

        periods = _periodCols(self._df)
        if not periods:
            return repr(self._df)
        latest = sorted(periods, reverse=True)[0]
        rows = self._df.to_dicts()
        parts: list[str] = []
        for row in rows:
            val = row.get(latest)
            if val and str(val).strip():
                parts.append(str(val))
        if not parts:
            return repr(self._df)
        console = Console(record=True, file=io.StringIO(), width=120)
        console.print(Panel("\n".join(parts), title=self._title(), border_style="dim"))
        return console.export_text()

    def _renderHtml(self) -> str:
        """Rich Console → HTML (inline styles).

        HTML은 가로 스크롤이 되므로 기간 컬럼 수에 비례해 width를 계산한다.
        width=120 고정 시 62컬럼 IS 같은 경우 기간 컬럼이 전부 잘려 snakeId/항목만 남는다.
        """
        import io

        from rich.console import Console

        if not self.isNumeric:
            return self._renderHtmlText()
        metas = _metaCols(self._df)
        periods = _periodCols(self._df)
        width = max(120, 22 * len(metas) + 12 * len(periods) + 8)
        console = Console(record=True, file=io.StringIO(), force_jupyter=True, width=width)
        console.print(self._toRichTable())
        return console.export_html(inline_styles=True)

    def _renderHtmlText(self) -> str:
        """텍스트 DataFrame → HTML."""
        import io

        from rich.console import Console
        from rich.panel import Panel

        periods = _periodCols(self._df)
        if not periods:
            return f"<pre>{self._df}</pre>"
        latest = sorted(periods, reverse=True)[0]
        rows = self._df.to_dicts()
        parts: list[str] = []
        for row in rows:
            val = row.get(latest)
            if val and str(val).strip():
                parts.append(str(val))
        if not parts:
            return f"<pre>{self._df}</pre>"
        console = Console(record=True, file=io.StringIO(), force_jupyter=True, width=120)
        console.print(Panel("\n".join(parts), title=self._title(), border_style="dim"))
        return console.export_html(inline_styles=True)

    # ── 변환 ──

    def toDict(self) -> list[dict[str, Any]]:
        """DataFrame → list of dicts."""
        return self._df.to_dicts()

    def toMarkdown(self) -> str:
        """마크다운 테이블."""
        rows = self._df.to_dicts()
        if not rows:
            return ""
        cols = list(rows[0].keys())
        lines: list[str] = []
        lines.append("| " + " | ".join(cols) + " |")
        lines.append("| " + " | ".join("---" for _ in cols) + " |")
        for row in rows:
            cells = [_fmtVal(row.get(c)) for c in cols]
            lines.append("| " + " | ".join(cells) + " |")
        return "\n".join(lines)

    def toJson(self) -> str:
        """JSON 직렬화."""
        return json.dumps(
            {
                "topic": self._topic,
                "meta": self._meta,
                "columns": self._df.columns,
                "data": self._df.to_dicts(),
            },
            ensure_ascii=False,
            default=str,
        )

    def toHtml(self) -> str:
        return self.render("html")

    # ── 체이닝 ──

    def chart(self, kind: str = "auto") -> "ChartResult":
        """시계열 차트 생성."""
        return ChartResult(self, kind=kind)


# ══════════════════════════════════════
# ChartResult
# ══════════════════════════════════════


class ChartResult:
    """chart() 반환 객체 — 시각화 + 렌더링.

    Guide:
        AI 역할: AI는 ChartResult/viz를 이미 검증된 표를 시각 설명으로 바꾸는 엔진으로 보고 단일값·무근거 차트를 만들지 않는다.
        When: SelectResult나 DataFrame 기반 근거를 차트로 설명해야 할 때.
        How: 표의 기간/series/value 근거가 충분한지 먼저 확인하고, chart() 결과의 spec을 최종 답변 ref와 연결한다.
    """

    __slots__ = ("_select", "_kind", "_spec")

    def __init__(self, select: SelectResult, *, kind: str = "auto"):
        self._select = select
        self._kind = kind
        self._spec: dict | None = None

    @property
    def select(self) -> SelectResult:
        """원본 SelectResult."""
        return self._select

    @property
    def spec(self) -> dict:
        """ChartSpec JSON dict (기존 tools/chart.py 프로토콜 호환)."""
        if self._spec is None:
            self._spec = self._buildSpec()
        return self._spec

    def _buildSpec(self) -> dict:
        """DataFrame → ChartSpec dict."""
        df = self._select.df
        periods = _periodCols(df)
        metas = _metaCols(df)

        if not periods or not self._select.isNumeric:
            return {"chartType": "none", "title": self._select.topic}

        categories = sorted(periods)
        labelCol = metas[0] if metas else None
        rows = df.to_dicts()

        series: list[dict] = []
        for i, row in enumerate(rows):
            name = str(row.get(labelCol, f"series_{i}")) if labelCol else f"series_{i}"
            data = [row.get(p) for p in categories]
            chartType = "bar" if i == 0 else "line"
            if self._kind != "auto":
                chartType = self._kind
            series.append(
                {
                    "name": name,
                    "data": data,
                    "color": _COLORS[i % len(_COLORS)],
                    "type": chartType,
                }
            )

        meta = self._select.meta.copy()
        title = meta.get("corpName", "")
        if title:
            title = f"{title} — {self._select.topic}"
        else:
            title = self._select.topic

        finalKind = self._kind if self._kind != "auto" else "combo"

        return {
            "chartType": finalKind,
            "title": title,
            "series": series,
            "categories": categories,
            "options": {"unit": meta.get("currency", "")},
            "meta": meta,
        }

    # ── render(fmt) ──

    def render(self, fmt: str = "html") -> str:
        """통합 렌더러."""
        if fmt == "html":
            return self._renderHtml()
        if fmt == "json":
            return self.toJson()
        if fmt == "rich":
            return f"[차트: {self._select.topic}]"
        if fmt == "markdown":
            return self._select.toMarkdown()
        raise ValueError(f"지원하지 않는 렌더링 형식: {fmt}")

    def __repr__(self) -> str:
        return f"ChartResult(topic={self._select.topic!r}, kind={self._kind!r})"

    def _repr_html_(self) -> str:
        return self.render("html")

    def _repr_markdown_(self) -> str:
        return self.render("markdown")

    def _renderHtml(self) -> str:
        """Plotly HTML — viz 가 등록한 ChartHtmlRenderer 사용 (core/render registry).

        viz 가 import 안 된 환경 (pyodide·viz 미설치) 은 markdown fallback.
        """
        if not self._select.isNumeric:
            return self._select.render("html")
        from dartlab.core.render import getRenderer

        renderer = getRenderer()
        if renderer is None:
            return self._select.render("markdown")
        return renderer.htmlFromSpec(self.spec)

    def toJson(self) -> str:
        """ChartSpec JSON."""
        return json.dumps(self.spec, ensure_ascii=False, default=str)

    def toHtml(self) -> str:
        return self.render("html")
