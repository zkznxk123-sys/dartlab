"""Tool 반환값 직렬화 — LLM 전달용 / UI 표시용 2종.

LLM 전달은 토큰 절약 (head + shape + columns). UI 는 aiview.autoEnrich 부착 무제한.
"""

from __future__ import annotations

import re
from typing import Any

_MAX_LLM_CHARS = 8000
_MAX_DF_ROWS_LLM = 20
_MAX_DF_ROWS_UI = 100


# ── Polars 유니코드 박스 → GFM 마크다운 테이블 변환 ────────


def polarsTableToMarkdown(text: str) -> str:
    """Polars `print(df)` 유니코드 박스 → 마크다운 테이블.

    Polars 출력 구조:
        ┌──────┬──────┐
        │ col1 ┆ col2 │  ← 헤더
        │ ---  ┆ ---  │  ← 타입 힌트
        │ str  ┆ f64  │  ← 타입 행
        ╞══════╪══════╡  ← 헤더/데이터 구분
        │ val1 ┆ val2 │
        └──────┴──────┘
    """
    if "┌" not in text:
        return text

    lines = text.split("\n")
    result: list[str] = []
    inTable = False
    headerEmitted = False
    colCount = 0

    for line in lines:
        stripped = line.strip()

        if stripped.startswith("┌") and stripped.endswith("┐"):
            inTable = True
            headerEmitted = False
            continue

        if stripped.startswith("└") and stripped.endswith("┘"):
            inTable = False
            continue

        if not inTable:
            result.append(line)
            continue

        if stripped.startswith("╞") or stripped.startswith("├"):
            if not headerEmitted and colCount > 0:
                result.append("| " + " | ".join(["---"] * colCount) + " |")
                headerEmitted = True
            continue

        if "│" in stripped or "┆" in stripped:
            cellsRaw = re.split(r"[│┆]", stripped)
            cells = [c.strip() for c in cellsRaw if c.strip() != ""]

            if all(
                c in ("---", "str", "f64", "i64", "i32", "u32", "u64", "bool", "cat", "date", "datetime") for c in cells
            ):
                continue

            if cells:
                clean = [c for c in cells if c not in ("…", "...")]
                if not clean:
                    continue
                clean = [("-" if c == "null" else c) for c in clean]
                colCount = max(colCount, len(clean))
                result.append("| " + " | ".join(clean) + " |")

    return "\n".join(result)


# ── DataFrame → 마크다운 테이블 ────────────────────────────


def _dfToMarkdown(df: Any, *, maxRows: int) -> str:
    """Polars DataFrame → 마크다운 테이블 + shape 메타."""
    try:
        import polars as pl
    except ImportError:
        return str(df)[:_MAX_LLM_CHARS]

    if not isinstance(df, pl.DataFrame):
        return str(df)[:_MAX_LLM_CHARS]

    rows, cols = df.shape
    shapeNote = f"shape: ({rows}, {cols})"

    if rows > maxRows:
        shown = df.head(maxRows)
        truncNote = f" — 상위 {maxRows}개 (전체 {rows}개)"
    else:
        shown = df
        truncNote = ""

    with pl.Config(
        tbl_formatting="ASCII_MARKDOWN",
        tbl_hide_column_data_types=True,
        tbl_hide_dataframe_shape=True,
        fmt_str_lengths=80,
        tbl_cols=-1,
        tbl_rows=-1,
    ):
        body = str(shown)

    return f"{shapeNote}{truncNote}\n\n{body}"


# ── dict 직렬화 (analysis/credit/gather 반환값) ────────────


def _dictToSummary(data: dict, *, maxChars: int) -> str:
    """analysis/credit 등 dict 반환값 → 압축 요약.

    - 최상위 키 나열
    - 숫자값은 그대로
    - list/dict 는 첫 N개만
    - history list 는 shape 만 + 첫 행
    """
    import json

    def _compress(v: Any, depth: int = 0) -> Any:
        if depth > 3:
            return "..."
        if v is None:
            return None
        if isinstance(v, (int, float, str, bool)):
            if isinstance(v, str) and len(v) > 500:
                return v[:500] + f"... (+{len(v) - 500} chars)"
            return v
        if isinstance(v, list):
            if not v:
                return []
            if len(v) > 5:
                return [_compress(v[0], depth + 1), f"... (총 {len(v)}개)"]
            return [_compress(x, depth + 1) for x in v]
        if isinstance(v, dict):
            return {k: _compress(val, depth + 1) for k, val in v.items()}
        return str(v)[:200]

    compressed = _compress(data)
    try:
        text = json.dumps(compressed, ensure_ascii=False, indent=2, default=str)
    except (TypeError, ValueError):
        text = str(compressed)

    if len(text) > maxChars:
        text = text[:maxChars] + f"\n... (+{len(text) - maxChars} chars 잘림)"
    return text


# ── 공개 API ───────────────────────────────────────────────


def serializeForLlm(result: Any, *, name: str, arguments: dict) -> str:
    """Tool 반환값 → LLM 메시지 문자열. 8KB 상한."""
    try:
        import polars as pl

        if isinstance(result, pl.DataFrame):
            return _dfToMarkdown(result, maxRows=_MAX_DF_ROWS_LLM)
    except ImportError:
        pass

    if isinstance(result, dict):
        return _dictToSummary(result, maxChars=_MAX_LLM_CHARS)

    if isinstance(result, (list, tuple)):
        preview = result[:10]
        suffix = f"\n... (총 {len(result)}개)" if len(result) > 10 else ""
        return "\n".join(str(x)[:200] for x in preview) + suffix

    if result is None:
        return "(None 반환 — 해당 데이터 없음)"

    text = str(result)
    if len(text) > _MAX_LLM_CHARS:
        text = text[:_MAX_LLM_CHARS] + f"\n... (+{len(text) - _MAX_LLM_CHARS} chars 잘림)"
    return text


def serializeForUi(result: Any, *, name: str) -> str:
    """UI 표시용 — 무제한, aiview enrichment 포함."""
    try:
        import polars as pl

        if isinstance(result, pl.DataFrame):
            return _dfToMarkdown(result, maxRows=_MAX_DF_ROWS_UI)
    except ImportError:
        pass

    if isinstance(result, dict):
        # aiview.autoEnrich 부착 시도 — 실패하면 그냥 dict 요약
        try:
            from dartlab.ai.context.aiview import autoEnrich

            enriched = autoEnrich(result)
            return _dictToSummary(enriched, maxChars=20000)
        except (ImportError, Exception):  # noqa: BLE001
            return _dictToSummary(result, maxChars=20000)

    if isinstance(result, (list, tuple)):
        return "\n".join(str(x) for x in result[:50])

    if result is None:
        return "(None)"

    return str(result)
