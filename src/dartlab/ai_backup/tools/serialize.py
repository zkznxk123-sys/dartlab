"""Tool 반환값 직렬화 — LLM 전달용 / UI 표시용 2종.

LLM 전달은 토큰 절약 (head + shape + columns). UI 는 aiview.autoEnrich 부착 무제한.
"""

from __future__ import annotations

import re
from typing import Any

_MAX_LLM_CHARS = 8000
_MAX_DF_ROWS_LLM = 20
_MAX_DF_ROWS_UI = 100
_EVIDENCE_LABELS = {
    "period": "기간",
}


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
    """Polars DataFrame → GFM markdown table. 수동 row iter 로 빌드.

    Polars 내장 ``ASCII_MARKDOWN`` + ``fmt_str_lengths=80`` 조합은 셀 폭 초과 시
    행 안에서 줄바꿈을 삽입해 GFM 구조를 파괴한다 (사용자 보고 2026-04-23).
    수동 빌드로 교체하고 셀 포맷은 `aiview._formatNum` SSOT 재사용
    (비율·금액·지수 표기 자동 감지 및 한국어 단위 변환).
    """
    try:
        import polars as pl
    except ImportError:
        return str(df)[:_MAX_LLM_CHARS]

    if not isinstance(df, pl.DataFrame):
        return str(df)[:_MAX_LLM_CHARS]

    from dartlab.ai.context.aiview import _formatNum

    rows, cols = df.shape
    shapeNote = f"shape: ({rows}, {cols})"

    if rows > maxRows:
        if "date" in df.columns and maxRows >= 10:
            headRows = min(5, maxRows // 2)
            tailRows = maxRows - headRows
            shown = pl.concat([df.head(headRows), df.tail(tailRows)], how="vertical")
            truncNote = f" — 상위 {headRows}개 + 최신 {tailRows}개 (전체 {rows}개)"
        else:
            shown = df.head(maxRows)
            truncNote = f" — 상위 {maxRows}개 (전체 {rows}개)"
    else:
        shown = df
        truncNote = ""

    columns = list(shown.columns)
    header = "| " + " | ".join(columns) + " |"
    divider = "| " + " | ".join(["---"] * len(columns)) + " |"
    bodyLines: list[str] = []
    for row in shown.iter_rows(named=True):
        cells: list[str] = []
        for col in columns:
            val = row.get(col)
            if val is None:
                cells.append("-")
            elif isinstance(val, bool):
                cells.append("true" if val else "false")
            elif isinstance(val, (int, float)):
                cells.append(_formatNum(val, col))
            else:
                s = str(val).replace("|", "\\|").replace("\n", " ")
                if len(s) > 80:
                    s = s[:77] + "..."
                cells.append(s)
        bodyLines.append("| " + " | ".join(cells) + " |")

    body = "\n".join([header, divider, *bodyLines])
    return f"{shapeNote}{truncNote}\n\n{body}"


# ── dict 직렬화 (analysis/credit/gather 반환값) ────────────


def _isTabularList(v: Any) -> bool:
    """list[dict] 이고 모든 원소가 동일 키 집합을 가진 표 스키마인지 판정.

    길이 2+ 필요 (단일 원소는 표 이점 없음). 키 2+ 필요 (단일 컬럼은 리스트로 충분).
    """
    if not isinstance(v, list) or len(v) < 2:
        return False
    if not all(isinstance(x, dict) for x in v):
        return False
    firstKeys = tuple(v[0].keys())
    if len(firstKeys) < 2:
        return False
    return all(tuple(x.keys()) == firstKeys for x in v)


def _formatCell(v: Any, field: str = "") -> str:
    """표 셀 렌더 — SSOT 는 `aiview._formatNum` (한국어 단위 자동 감지).

    숫자 포맷 중복 금지: list[dict] / DataFrame 경로가 같은 엔진 경유.
    None · bool · dict · list · 긴 문자열은 여기서 처리.
    """
    if v is None:
        return "-"
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (int, float)):
        from dartlab.ai.context.aiview import _formatNum

        return _formatNum(v, field)
    if isinstance(v, str):
        s = v.strip()
        if not s:
            return "-"
        if len(s) > 60:
            return s[:57] + "..."
        return s.replace("|", "\\|").replace("\n", " ")
    if isinstance(v, (list, tuple)):
        return f"[{len(v)}개]"
    if isinstance(v, dict):
        return f"{{{len(v)}키}}"
    return str(v)[:60]


def _tabularListToMarkdown(rows: list[dict]) -> str:
    """list[dict] → GFM markdown table. 상위 20행까지."""
    keys = list(rows[0].keys())
    shown = rows[:_MAX_DF_ROWS_LLM]
    header = "| " + " | ".join(keys) + " |"
    divider = "| " + " | ".join(["---"] * len(keys)) + " |"
    body = ["| " + " | ".join(_formatCell(r.get(k), k) for k in keys) + " |" for r in shown]
    truncNote = (
        f"\n... ({len(rows) - _MAX_DF_ROWS_LLM}행 생략, 전체 {len(rows)}행)" if len(rows) > _MAX_DF_ROWS_LLM else ""
    )
    return "\n".join([header, divider, *body]) + truncNote


def _dictToSummary(data: dict, *, maxChars: int) -> str:
    """analysis/credit 등 dict 반환값 → 압축 요약.

    표 스키마 (list[dict] 동일 키) 는 markdown table 로 분리 렌더, 나머지는 JSON indent.
    이 형태로 LLM 에 들어가면 응답에도 표로 나올 확률이 높음 (행동 프롬프트 + 입력 모양 일치).
    """
    import json

    tabularBlocks: list[str] = []
    scalarPart: dict[str, Any] = {}

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

    for key, value in data.items():
        if _isTabularList(value):
            tabularBlocks.append(f"### {key}\n\n{_tabularListToMarkdown(value)}")
        else:
            scalarPart[key] = _compress(value)

    parts: list[str] = []
    if scalarPart:
        try:
            parts.append(json.dumps(scalarPart, ensure_ascii=False, indent=2, default=str))
        except (TypeError, ValueError):
            parts.append(str(scalarPart))
    parts.extend(tabularBlocks)

    text = "\n\n".join(parts) if parts else "{}"

    if len(text) > maxChars:
        text = text[:maxChars] + f"\n... (+{len(text) - maxChars} chars 잘림)"
    return text


# ── 공개 API ───────────────────────────────────────────────


def serializeForLlm(result: Any, *, name: str, arguments: dict) -> str:
    """Tool 반환값 → LLM 메시지 문자열. 8KB 상한."""
    header = _evidenceHeader(result, name=name, arguments=arguments)
    try:
        import polars as pl

        if isinstance(result, pl.DataFrame):
            return header + "\n\n" + _dfToMarkdown(result, maxRows=_MAX_DF_ROWS_LLM)
    except ImportError:
        pass

    if isinstance(result, dict):
        return header + "\n\n" + _dictToSummary(result, maxChars=_MAX_LLM_CHARS)

    if isinstance(result, (list, tuple)):
        preview = result[:10]
        suffix = f"\n... (총 {len(result)}개)" if len(result) > 10 else ""
        return header + "\n\n" + "\n".join(str(x)[:200] for x in preview) + suffix

    if result is None:
        return header + "\n\n(None 반환 — 해당 데이터 없음)"

    text = str(result)
    if len(text) > _MAX_LLM_CHARS:
        text = text[:_MAX_LLM_CHARS] + f"\n... (+{len(text) - _MAX_LLM_CHARS} chars 잘림)"
    return header + "\n\n" + text


def _evidenceHeader(result: Any, *, name: str, arguments: dict) -> str:
    """LLM 에 전달할 공통 증거 헤더."""
    from dartlab.ai.runtime.contracts import contractMetadataForTool

    target = (
        arguments.get("stockCode")
        or arguments.get("target")
        or arguments.get("keyword")
        or arguments.get("query")
        or arguments.get("axis")
        or "-"
    )
    lines = [
        "## Evidence",
        f"- 도구명: {name}",
        f"- 대상: {target}",
        "- 데이터 기준: tool_result 원본",
    ]
    contract = contractMetadataForTool(name, arguments)
    if contract:
        lines.append(f"- 계약 키: {contract.get('contractId') or contract.get('contractKey')}")
        required = contract.get("requiredEvidence")
        if required:
            labels = [_EVIDENCE_LABELS.get(str(x), str(x)) for x in required]
            lines.append(f"- 필수 증거: {', '.join(labels)}")
        schema = contract.get("evidenceSchema")
        if isinstance(schema, dict) and schema:
            lines.append(f"- 증거 스키마: {', '.join(str(k) for k in schema.keys())}")
    if isinstance(result, dict):
        summary = result.get("_summary")
        if summary:
            lines.append(f"- _summary: {summary}")
        yoy = result.get("_yoy")
        if yoy:
            lines.append(f"- _yoy: {yoy}")
        assumptions = result.get("assumptions")
        if assumptions:
            lines.append(f"- assumptions: {assumptions}")
        keys = ", ".join(str(k) for k in list(result.keys())[:20])
        lines.append(f"- 결과 구조: dict keys = {keys}")
    else:
        lines.append(f"- 결과 구조: {type(result).__name__}")
    return "\n".join(lines)


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
