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
    "매출액",
    "매출원가",
    "매출총이익",
    "판매비와관리비",
    "영업이익",
    "금융수익",
    "금융비용",
    "당기순이익",
]
BS_ITEMS = [
    "자산총계",
    "유동자산",
    "비유동자산",
    "부채총계",
    "유동부채",
    "비유동부채",
    "자본총계",
]
CF_ITEMS = [
    "영업활동현금흐름",
    "투자활동현금흐름",
    "재무활동현금흐름",
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


def fmt_억(val: float | None, is_edgar: bool = False) -> str:
    """원 단위 float → 억원 단위 문자열. EDGAR는 달러 그대로($M)."""
    if val is None:
        return "—"
    if is_edgar:
        # EDGAR: 이미 달러 단위. $M으로 표시
        v = val / 1e6
        if abs(v) >= 1:
            return f"{v:,.0f}"
        return f"{v:,.1f}"
    v = val / 1e8
    if abs(v) >= 1:
        return f"{v:,.0f}"
    return f"{v:,.1f}"


def build_table(rows: list[tuple[str, list[str]]], years: list[str], title: str) -> str:
    """마크다운 테이블 생성."""
    lines = []
    if title:
        lines.append(f"### {title}\n")
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
    """dartlab으로 데이터 추출. Company 1개만 로드 후 해제.

    기간 라벨은 DART/EDGAR 모두 fiscal 라벨 그대로 사용 (예: UAA FY26 Q3 = "2026Q3").
    DART 전통과 일관 — 회계연도 자체가 정보. 캘린더 remap 안 함.
    """
    import dartlab

    try:
        c = dartlab.Company(stock_code)
    except Exception as e:
        print(f"  [WARN] Company({stock_code}) 로드 실패: {e}")
        return None

    is_edgar = getattr(c, "market", "KR") == "US"
    result = {"stockCode": stock_code, "corpName": getattr(c, "corpName", stock_code), "isEdgar": is_edgar}
    freq_kw = {} if is_edgar else {"freq": "Y"}

    # --- IS ---
    try:
        df = c.select("IS", IS_ITEMS, **freq_kw)
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
                    vals.append(fmt_억(v, is_edgar))
                rows.append((item, vals))
        result["IS"] = {"years": years, "rows": rows}
    except Exception as e:
        print(f"  [WARN] IS 추출 실패: {e}")
        result["IS"] = None

    # --- BS ---
    try:
        df = c.select("BS", BS_ITEMS, **freq_kw)
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
                    vals.append(fmt_억(v, is_edgar))
                rows.append((item, vals))
        result["BS"] = {"years": years, "rows": rows}
    except Exception as e:
        print(f"  [WARN] BS 추출 실패: {e}")
        result["BS"] = None

    # --- CF ---
    try:
        df = c.select("CF", CF_ITEMS, **freq_kw)
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
                    vals.append(fmt_억(v, is_edgar))
                rows.append((item, vals))
        result["CF"] = {"years": years, "rows": rows}
    except Exception as e:
        print(f"  [WARN] CF 추출 실패: {e}")
        result["CF"] = None

    # --- SCE ---
    try:
        df = c.show("SCE", **freq_kw) if not is_edgar else None
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
                    vals.append(fmt_억(v, is_edgar) if isinstance(v, (int, float)) else str(v or "—"))
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
            if is_edgar:
                # EDGAR: period_key, form_type, accession_no
                for row in df.head(10).iter_rows(named=True):
                    acc = row.get("accession_no", "").replace("-", "")
                    sec_url = f"https://www.sec.gov/Archives/edgar/data/{acc}" if acc else ""
                    # 더 정확한 SEC 뷰어 URL
                    acc_dash = row.get("accession_no", "")
                    sec_url = (
                        f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={stock_code}&type={row.get('form_type', '')}&dateb=&owner=include&count=10"
                        if acc_dash
                        else ""
                    )
                    filings.append(
                        {
                            "year": row.get("period_key", ""),
                            "reportType": row.get("form_type", ""),
                            "url": sec_url,
                            "linkText": "SEC에서 보기",
                        }
                    )
            else:
                # DART: year, rceptDate, rceptNo, reportType, dartUrl
                for row in df.head(10).iter_rows(named=True):
                    filings.append(
                        {
                            "year": row.get("year", ""),
                            "reportType": row.get("reportType", ""),
                            "url": row.get("dartUrl", ""),
                            "linkText": "DART에서 보기",
                        }
                    )
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
    """IS 데이터로 ComboChart data prop (매출=라인, 영업이익/당기순이익=막대)."""
    d = data.get("IS")
    if not d:
        return ""
    years = d["years"]
    row_map = {name: vals for name, vals in d["rows"]}
    매출 = row_map.get("매출액", ["—"] * len(years))
    영업이익 = row_map.get("영업이익", ["—"] * len(years))
    순이익 = row_map.get("당기순이익", ["—"] * len(years))

    items = []
    for i, y in enumerate(years):
        rev = 매출[i].replace(",", "").replace("—", "null")
        op = 영업이익[i].replace(",", "").replace("—", "null")
        ni = 순이익[i].replace(",", "").replace("—", "null")
        items.append(f'{{year:"{y}",매출액:{rev},영업이익:{op},당기순이익:{ni}}}')
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
    """CF 데이터로 ComboChart data prop (영업/투자/재무 3항목 막대)."""
    d = data.get("CF")
    if not d:
        return ""
    years = d["years"]
    row_map = {name: vals for name, vals in d["rows"]}
    ocf = row_map.get("영업활동현금흐름", ["—"] * len(years))
    icf = row_map.get("투자활동현금흐름", ["—"] * len(years))
    fcf = row_map.get("재무활동현금흐름", ["—"] * len(years))

    items = []
    for i, y in enumerate(years):
        o = ocf[i].replace(",", "").replace("—", "0")
        inv = icf[i].replace(",", "").replace("—", "0")
        fin = fcf[i].replace(",", "").replace("—", "0")
        items.append(f'{{year:"{y}",영업CF:{o},투자CF:{inv},재무CF:{fin}}}')
    return "[" + ",".join(items) + "]"


def build_auto_section(data: dict) -> str:
    """AUTO 영역 전체 마크다운 생성."""
    sc = data["stockCode"]
    is_edgar = data.get("isEdgar", False)
    unit_label = "$M" if is_edgar else "억원"
    parts = [AUTO_START, ""]

    # 차트 import는 AUTO 밖 본문 <script>에서 처리
    # (AUTO 안에 <script> 넣으면 mdsvex 충돌)
    parts.append("")

    # --- Filings ---
    if data.get("filings"):
        parts.append("## 공시 자료\n")
        parts.append("| 기간 | 보고서 | 링크 |")
        parts.append("|------|--------|------|")
        for f in data["filings"]:
            url = f.get("url", "")
            link_text = f.get("linkText", "보기")
            parts.append(f"| {f['year']} | {f['reportType']} | [{link_text}]({url}) |")
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

    # IS: 제목 → 차트(매출=라인, 영업이익/당기순이익=막대) → 테이블
    if data.get("IS"):
        d = data["IS"]
        parts.append("### 손익계산서 (IS) — 단위 " + unit_label + "\n")
        chart_data = _build_chart_data_is(data)
        if chart_data:
            parts.append(
                f"<ComboChart data={{{chart_data}}} "
                f'lineKeys={{["매출액"]}} barKeys={{["영업이익","당기순이익"]}} '
                f'lineColors={{["#22c55e"]}} barColors={{["#3b82f6","#f59e0b"]}} '
                f'title="매출(라인) vs 영업이익·당기순이익(막대)" unit="' + unit_label + '" />'
            )
            parts.append("")
        parts.append(build_table(d["rows"], d["years"], ""))

    # BS: 제목 → 차트(부채/자본 스택) → 테이블
    if data.get("BS"):
        d = data["BS"]
        parts.append("### 재무상태표 (BS) — 단위 " + unit_label + "\n")
        chart_data = _build_chart_data_bs(data)
        if chart_data:
            parts.append(f'<StackBar data={{{chart_data}}} title="부채 vs 자본 구조" unit="' + unit_label + '" />')
            parts.append("")
        parts.append(build_table(d["rows"], d["years"], ""))

    # CF: 제목 → 차트(영업/투자/재무 3막대) → 테이블
    if data.get("CF"):
        d = data["CF"]
        parts.append("### 현금흐름표 (CF) — 단위 " + unit_label + "\n")
        chart_data = _build_chart_data_cf(data)
        if chart_data:
            parts.append(
                f"<ComboChart data={{{chart_data}}} "
                f'barKeys={{["영업CF","투자CF","재무CF"]}} '
                f'barColors={{["#22c55e","#ef4444","#3b82f6"]}} '
                f'title="영업·투자·재무 현금흐름" unit="' + unit_label + '" />'
            )
            parts.append("")
        parts.append(build_table(d["rows"], d["years"], ""))

    # SCE
    if data.get("SCE") and len(data["SCE"]["rows"]) > 0:
        d = data["SCE"]
        parts.append(build_table(d["rows"], d["years"], "자본변동표 (SCE) — 단위 " + unit_label + ""))

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
        print("  SKIP: 데이터 추출 실패")
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
                new_text = text[: m.start()] + "\n\n---\n\n" + auto_section + "\n"
                replaced = True
                print("  기존 수동 부록 → AUTO 교체")
                break

        if not replaced:
            # 끝에 신규 삽입
            if text.rstrip().endswith("---"):
                new_text = text.rstrip() + "\n\n" + auto_section + "\n"
            else:
                new_text = text.rstrip() + "\n\n---\n\n" + auto_section + "\n"
            print("  AUTO 신규 삽입")

    # 본문 <script>에 차트 import 보장 (AUTO 안에 넣으면 mdsvex 충돌)
    chart_imports = [
        "import ComboChart from '$lib/components/blog/ComboChart.svelte';",
        "import StackBar from '$lib/components/blog/StackBar.svelte';",
    ]
    if "<script>" in new_text:
        for imp in chart_imports:
            if imp not in new_text:
                new_text = new_text.replace("</script>", imp + "\n</script>", 1)
    else:
        # <script> 블록 자체가 없으면 frontmatter 뒤에 삽입
        new_text = new_text.replace("---\n\n", "---\n\n<script>\n" + "\n".join(chart_imports) + "\n</script>\n\n", 1)

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
