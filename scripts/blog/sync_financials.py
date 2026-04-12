"""
블로그 재무데이터 자동 동기화.

각 블로그의 frontmatter stockCode를 읽어 dartlab으로 최신 데이터를 뽑고,
AUTO:START ~ AUTO:END 영역을 교체한다. 본문은 절대 건드리지 않는다.

사용:
  uv run python -X utf8 scripts/blog/sync_financials.py              # 전체
  uv run python -X utf8 scripts/blog/sync_financials.py 000660       # 단일 종목
  uv run python -X utf8 scripts/blog/sync_financials.py --dry-run    # 미리보기
"""

import gc
import re
import sys
from datetime import datetime
from pathlib import Path

BLOG_DIR = Path("blog/05-company-reports")
AUTO_START = "<!-- AUTO:START — sync_financials.py가 자동 생성. 수동 편집 금지 -->"
AUTO_END = "<!-- AUTO:END -->"

IS_ITEMS = [
    "매출액", "매출원가", "매출총이익",
    "판매비와관리비", "영업이익",
    "금융수익", "금융비용", "당기순이익",
]
BS_ITEMS = [
    "자산총계", "유동자산", "비유동자산",
    "부채총계", "유동부채", "비유동부채", "자본총계",
]
CF_ITEMS = [
    "영업활동현금흐름", "투자활동현금흐름", "재무활동현금흐름",
]


def parse_frontmatter(text: str) -> dict:
    """frontmatter에서 stockCode, corpName 추출."""
    m = re.match(r"^---\n(.+?)\n---", text, re.DOTALL)
    if not m:
        return {}
    fm = {}
    for line in m.group(1).splitlines():
        if ":" in line:
            key, val = line.split(":", 1)
            fm[key.strip()] = val.strip().strip('"').strip("'")
    return fm


def fmt_억(val: float | None) -> str:
    """원 단위 float → 억원 단위 문자열 (천단위 콤마)."""
    if val is None:
        return "—"
    v = val / 1e8
    if abs(v) >= 1:
        return f"{v:,.0f}"
    return f"{v:,.1f}"


def build_table(rows: list[tuple[str, list[str]]], years: list[str], title: str) -> str:
    """마크다운 테이블 생성."""
    lines = [f"### {title}\n"]
    header = "| 항목 | " + " | ".join(years) + " |"
    sep = "|---|" + "|".join(["---:" for _ in years]) + "|"
    lines.append(header)
    lines.append(sep)
    for name, vals in rows:
        cells = " | ".join(vals)
        lines.append(f"| {name} | {cells} |")
    lines.append("")
    return "\n".join(lines)


def extract_data(stock_code: str) -> dict | None:
    """dartlab으로 데이터 추출. Company 1개만 로드 후 해제."""
    import dartlab

    try:
        c = dartlab.Company(stock_code)
    except Exception as e:
        print(f"  [WARN] Company({stock_code}) 로드 실패: {e}")
        return None

    result = {"stockCode": stock_code, "corpName": getattr(c, "corpName", stock_code)}

    # --- IS ---
    try:
        df = c.select("IS", IS_ITEMS, freq="Y")
        years = [col for col in df.columns if col not in ("항목", "snakeId")][:5]
        rows = []
        for item in IS_ITEMS:
            filtered = df.filter(df["항목"] == item)
            if len(filtered) == 0:
                rows.append((item, ["—"] * len(years)))
            else:
                vals = []
                for y in years:
                    v = filtered[y][0] if y in filtered.columns else None
                    vals.append(fmt_억(v))
                rows.append((item, vals))
        result["IS"] = {"years": years, "rows": rows}
    except Exception as e:
        print(f"  [WARN] IS 추출 실패: {e}")
        result["IS"] = None

    # --- BS ---
    try:
        df = c.select("BS", BS_ITEMS, freq="Y")
        years = [col for col in df.columns if col not in ("항목", "snakeId")][:5]
        rows = []
        for item in BS_ITEMS:
            filtered = df.filter(df["항목"] == item)
            if len(filtered) == 0:
                rows.append((item, ["—"] * len(years)))
            else:
                vals = []
                for y in years:
                    v = filtered[y][0] if y in filtered.columns else None
                    vals.append(fmt_억(v))
                rows.append((item, vals))
        result["BS"] = {"years": years, "rows": rows}
    except Exception as e:
        print(f"  [WARN] BS 추출 실패: {e}")
        result["BS"] = None

    # --- CF ---
    try:
        df = c.select("CF", CF_ITEMS, freq="Y")
        years = [col for col in df.columns if col not in ("항목", "snakeId")][:5]
        rows = []
        for item in CF_ITEMS:
            filtered = df.filter(df["항목"] == item)
            if len(filtered) == 0:
                rows.append((item, ["—"] * len(years)))
            else:
                vals = []
                for y in years:
                    v = filtered[y][0] if y in filtered.columns else None
                    vals.append(fmt_억(v))
                rows.append((item, vals))
        result["CF"] = {"years": years, "rows": rows}
    except Exception as e:
        print(f"  [WARN] CF 추출 실패: {e}")
        result["CF"] = None

    # --- SCE ---
    try:
        df = c.show("SCE", freq="Y")
        if df is not None and len(df) > 0:
            years = [col for col in df.columns if re.match(r"^\d{4}", col)][:5]
            item_col = "항목" if "항목" in df.columns else df.columns[0]
            rows = []
            for row in df.iter_rows(named=True):
                name = row.get(item_col, "")
                if not name or name == "":
                    continue
                vals = []
                for y in years:
                    v = row.get(y)
                    vals.append(fmt_억(v) if isinstance(v, (int, float)) else str(v or "—"))
                # "cause / detail" 형태면 cause만 사용
                display_name = name.split(" / ")[0].strip() if " / " in name else name
                rows.append((display_name, vals))
            # 너무 많으면 주요 항목만 (15행 제한)
            result["SCE"] = {"years": years, "rows": rows[:15]}
        else:
            result["SCE"] = None
    except Exception as e:
        print(f"  [WARN] SCE 추출 실패: {e}")
        result["SCE"] = None

    # --- Filings ---
    try:
        df = c.filings()
        if df is not None and len(df) > 0:
            filings = []
            for row in df.head(10).iter_rows(named=True):
                filings.append({
                    "year": row.get("year", ""),
                    "rceptDate": row.get("rceptDate", ""),
                    "reportType": row.get("reportType", ""),
                    "dartUrl": row.get("dartUrl", ""),
                })
            result["filings"] = filings
        else:
            result["filings"] = []
    except Exception as e:
        print(f"  [WARN] filings 추출 실패: {e}")
        result["filings"] = []

    # 메모리 해제
    del c
    gc.collect()

    return result


def _build_chart_data_is(data: dict) -> str:
    """IS 데이터로 LineChart data prop 문자열 생성."""
    d = data.get("IS")
    if not d:
        return ""
    years = d["years"]
    # rows를 dict로 변환
    row_map = {name: vals for name, vals in d["rows"]}
    매출 = row_map.get("매출액", ["—"] * len(years))
    영업이익 = row_map.get("영업이익", ["—"] * len(years))

    items = []
    for i, y in enumerate(years):
        rev = 매출[i].replace(",", "").replace("—", "null")
        op = 영업이익[i].replace(",", "").replace("—", "null")
        items.append(f'{{year:"{y}",매출:{rev},영업이익:{op}}}')
    return "[" + ",".join(items) + "]"


def _build_chart_data_bs(data: dict) -> str:
    """BS 데이터로 StackBar data prop 문자열 생성."""
    d = data.get("BS")
    if not d:
        return ""
    years = d["years"]
    row_map = {name: vals for name, vals in d["rows"]}
    부채 = row_map.get("부채총계", ["—"] * len(years))
    자본 = row_map.get("자본총계", ["—"] * len(years))

    items = []
    for i, y in enumerate(years):
        debt = 부채[i].replace(",", "").replace("—", "0")
        eq = 자본[i].replace(",", "").replace("—", "0")
        items.append(
            f'{{year:"{y}",segments:[{{label:"부채",value:{debt},color:"#ef4444"}},'
            f'{{label:"자본",value:{eq},color:"#22c55e"}}]}}'
        )
    return "[" + ",".join(items) + "]"


def _build_chart_data_cf(data: dict) -> str:
    """CF 데이터로 BarChart data prop 문자열 생성 (영업CF)."""
    d = data.get("CF")
    if not d:
        return ""
    years = d["years"]
    row_map = {name: vals for name, vals in d["rows"]}
    ocf = row_map.get("영업활동현금흐름", ["—"] * len(years))

    items = []
    for i, y in enumerate(years):
        v = ocf[i].replace(",", "").replace("—", "0")
        items.append(f'{{label:"{y}",value:{v}}}')
    return "[" + ",".join(items) + "]"


def build_auto_section(data: dict) -> str:
    """AUTO 영역 전체 마크다운 생성."""
    sc = data["stockCode"]
    parts = [AUTO_START, ""]

    # --- Svelte 차트 import ---
    parts.append("<script>")
    parts.append("import LineChart from '$lib/components/blog/LineChart.svelte';")
    parts.append("import BarChart from '$lib/components/blog/BarChart.svelte';")
    parts.append("import StackBar from '$lib/components/blog/StackBar.svelte';")
    parts.append("</script>")
    parts.append("")

    # --- Filings ---
    if data.get("filings"):
        parts.append("## 공시 / Filings\n")
        parts.append("| 기간 | 보고서 | 링크 |")
        parts.append("|------|--------|------|")
        for f in data["filings"]:
            url = f["dartUrl"]
            parts.append(f"| {f['year']} | {f['reportType']} | [DART에서 보기]({url}) |")
        parts.append("")
        parts.append("> 전체 공시 목록은 dartlab에서 확인:")
        parts.append("> ```python")
        parts.append("> import dartlab")
        parts.append(f'> c = dartlab.Company("{sc}")')
        parts.append("> c.filings()")
        parts.append("> ```")
        parts.append("")

    # --- 재무제표 ---
    parts.append("## 재무제표 — 최근 5개년\n")
    parts.append("> 아래는 최근 5개년 요약입니다. 전체 기간·분기별 데이터는 dartlab에서 직접 확인할 수 있습니다:")
    parts.append("> ```python")
    parts.append("> import dartlab")
    parts.append(f'> c = dartlab.Company("{sc}")')
    parts.append('> c.show("IS")              # 손익계산서 (분기)')
    parts.append('> c.show("IS", freq="Y")    # 손익계산서 (연간)')
    parts.append('> c.show("BS")              # 재무상태표')
    parts.append('> c.show("CF")              # 현금흐름표')
    parts.append('> c.show("SCE")             # 자본변동표')
    parts.append('> c.show("ratios")          # 재무비율')
    parts.append("> ```")
    parts.append("")

    # IS + 차트
    if data.get("IS"):
        d = data["IS"]
        chart_data = _build_chart_data_is(data)
        if chart_data:
            parts.append(f'<LineChart data={{{chart_data}}} title="매출 vs 영업이익 추이" unit="억원" />')
            parts.append("")
        parts.append(build_table(d["rows"], d["years"], "손익계산서 (IS) — 단위 억원"))

    # BS + 차트
    if data.get("BS"):
        d = data["BS"]
        chart_data = _build_chart_data_bs(data)
        if chart_data:
            parts.append(f'<StackBar data={{{chart_data}}} title="부채 vs 자본 구조" unit="억원" />')
            parts.append("")
        parts.append(build_table(d["rows"], d["years"], "재무상태표 (BS) — 단위 억원"))

    # CF + 차트
    if data.get("CF"):
        d = data["CF"]
        chart_data = _build_chart_data_cf(data)
        if chart_data:
            parts.append(f'<BarChart data={{{chart_data}}} title="영업활동 현금흐름" unit="억원" />')
            parts.append("")
        parts.append(build_table(d["rows"], d["years"], "현금흐름표 (CF) — 단위 억원"))

    # SCE
    if data.get("SCE") and len(data["SCE"]["rows"]) > 0:
        d = data["SCE"]
        parts.append(build_table(d["rows"], d["years"], "자본변동표 (SCE) — 단위 억원"))

    now = datetime.now().strftime("%Y-%m-%d")
    parts.append(f"*최종 갱신: {now} | dartlab 실측 (DART 공시 기준)*")
    parts.append("")
    parts.append(AUTO_END)

    return "\n".join(parts)


def sync_post(index_path: Path, target_code: str | None, dry_run: bool) -> bool:
    """단일 블로그 파일 동기화."""
    text = index_path.read_text(encoding="utf-8")
    fm = parse_frontmatter(text)
    stock_code = fm.get("stockCode")

    if not stock_code:
        return False

    if target_code and stock_code != target_code:
        return False

    slug = index_path.parent.name
    print(f"\n[{slug}] stockCode={stock_code}")

    # 데이터 추출
    data = extract_data(stock_code)
    if data is None:
        print(f"  SKIP: 데이터 추출 실패")
        return False

    auto_section = build_auto_section(data)

    if dry_run:
        print("--- DRY RUN ---")
        print(auto_section)
        print("--- END ---")
        return True

    # 기존 AUTO 영역 교체 또는 신규 삽입
    if AUTO_START in text:
        # 기존 마커 사이 교체
        pattern = re.escape(AUTO_START) + r".*?" + re.escape(AUTO_END)
        new_text = re.sub(pattern, auto_section, text, flags=re.DOTALL)
    else:
        # 기존 수동 부록 찾아서 교체
        # "## 부록" 또는 "## 재무제표" 패턴 찾기
        manual_patterns = [
            r"\n---\n\n## 부록[^\n]*\n.*$",
            r"\n## 부록[^\n]*\n.*$",
            r"\n## 재무제표[^\n]*\n.*$",
        ]
        replaced = False
        for pat in manual_patterns:
            m = re.search(pat, text, re.DOTALL)
            if m:
                # 수동 부록 제거하고 AUTO 삽입
                new_text = text[:m.start()] + "\n\n---\n\n" + auto_section + "\n"
                replaced = True
                print(f"  기존 수동 부록 → AUTO 교체")
                break

        if not replaced:
            # 끝에 신규 삽입
            if text.rstrip().endswith("---"):
                new_text = text.rstrip() + "\n\n" + auto_section + "\n"
            else:
                new_text = text.rstrip() + "\n\n---\n\n" + auto_section + "\n"
            print(f"  AUTO 신규 삽입")

    index_path.write_text(new_text, encoding="utf-8")
    auto_lines = auto_section.count("\n")
    print(f"  OK: AUTO 영역 {auto_lines}줄 생성")
    return True


def main():
    args = sys.argv[1:]
    dry_run = "--dry-run" in args
    args = [a for a in args if a != "--dry-run"]
    target_code = args[0] if args else None

    if dry_run:
        print("=== DRY RUN 모드 ===\n")

    folders = sorted(BLOG_DIR.iterdir())
    count = 0
    for folder in folders:
        index_path = folder / "index.md"
        if not index_path.is_file():
            continue
        if folder.name.startswith("_"):
            continue
        if sync_post(index_path, target_code, dry_run):
            count += 1

    print(f"\n완료: {count}편 동기화")


if __name__ == "__main__":
    main()
