"""블로그 5편 + 셀트리온 finance 표 전수 검증.

각 글에서 markdown finance 표를 파싱하고 dartlab `c.select(..., freq="Y")`
실측값과 1:1 비교한다. 코드/표/실측 3자 정합 확인.

실행:
    uv run python -X utf8 scripts/audit/auditBlogFinance.py
"""

from __future__ import annotations
import re
from pathlib import Path
import dartlab

POSTS = [
    ("000660", "blog/05-company-reports/01-000660-skhynix/index.md"),
    ("003230", "blog/05-company-reports/02-003230-samyang-foods/index.md"),
    ("034020", "blog/05-company-reports/03-034020-doosan-enerbility/index.md"),
    ("196170", "blog/05-company-reports/04-196170-alteogen/index.md"),
    ("011200", "blog/05-company-reports/05-011200-hmm/index.md"),
    ("068270", "blog/05-company-reports/06-068270-celltrion/index.md"),
]


# (raw markdown text → numeric value in 원). value can be None on parse fail.
def parseCell(raw: str) -> float | None:
    s = raw.strip().replace("**", "").replace("*", "")
    if s in ("", "—", "-", "???", "?"):
        return None
    s = s.replace(",", "").replace("원", "").replace("조", "").replace("억", "")
    s = s.replace("+", "")
    try:
        return float(s)
    except ValueError:
        return None


def normalize(actual: float | None, unit: str) -> float | None:
    """실측값(원) → 표시 단위로 정규화."""
    if actual is None:
        return None
    if unit == "조":
        return actual / 1e12
    if unit == "억":
        return actual / 1e8
    if unit == "백만":
        return actual / 1e6
    return actual


def detectUnit(text: str) -> str:
    """표 단위 텍스트에서 추출. 우선순위: 가장 가까운 단위 키워드."""
    # 가장 가까운 단위 (text 끝쪽 = 표에 가까움)
    last_eok = max(text.rfind("억원"), text.rfind("(억"))
    last_jo = max(text.rfind("조원"), text.rfind("(조"))
    last_mil = text.rfind("백만원")
    if last_mil > max(last_eok, last_jo):
        return "백만"
    if last_eok > last_jo:
        return "억"
    return "조"


def parseTable(block: str):
    """markdown table → list of (label, {year: cellValue}) + headers."""
    lines = [l.strip() for l in block.strip().split("\n") if l.strip().startswith("|")]
    if len(lines) < 3:
        return None, None
    header = [h.strip() for h in lines[0].strip("|").split("|")]
    # year columns: skip first label col, parse rest
    year_cols = []
    for h in header[1:]:
        m = re.search(r"(20\d{2})", h)
        if m:
            year_cols.append(m.group(1))
        else:
            year_cols.append(None)
    rows = []
    for line in lines[2:]:  # skip header + separator
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) < 2:
            continue
        label = cells[0].strip().replace("**", "").strip()
        values = {}
        for i, col in enumerate(year_cols, start=1):
            if col is None or i >= len(cells):
                continue
            values[col] = parseCell(cells[i])
        rows.append((label, values))
    return rows, year_cols


def findFinanceTables(text: str):
    """마크다운에서 c.select(...) 코드 블록 + 그 직후 표를 추출."""
    pattern = re.compile(
        r'```python\n([^`]*?c\.select\("(IS|BS|CF|CIS)",\s*\[([^\]]+)\][^)]*\)[^`]*?)\n```\s*\n+(\|[^\n]+\|\n\|[-:\s|]+\|\n(?:\|[^\n]+\|\n?)+)',
        re.DOTALL,
    )
    out = []
    for m in pattern.finditer(text):
        code = m.group(1)
        topic = m.group(2)
        keys_raw = m.group(3)
        keys = [k.strip().strip('"').strip("'") for k in keys_raw.split(",")]
        keys = [k for k in keys if k]
        table = m.group(4)
        # 단위 컨텍스트: 표 첫 컬럼 헤더 + 표 직전 400자 (섹션 타이틀 포함)
        first_col_header = ""
        first_line = table.split("\n")[0]
        if "|" in first_line:
            cells = first_line.strip("|").split("|")
            if cells:
                first_col_header = cells[0]
        before_ctx = text[max(0, m.start() - 400) : m.start()]
        out.append(
            {
                "code": code.strip(),
                "topic": topic,
                "keys": keys,
                "table": table,
                "unitHint": first_col_header + " " + before_ctx,
                "lineApprox": text[: m.start()].count("\n") + 1,
            }
        )
    return out


def auditPost(code: str, path: str):
    text = Path(path).read_text(encoding="utf-8")
    tables = findFinanceTables(text)
    if not tables:
        return [{"path": path, "warn": "no finance tables found"}]

    c = dartlab.Company(code)
    issues = []
    for t in tables:
        try:
            df = c.select(t["topic"], t["keys"], freq="Y")
        except Exception as e:
            issues.append(
                {
                    "path": path,
                    "line": t["lineApprox"],
                    "topic": t["topic"],
                    "keys": t["keys"],
                    "error": f"select failed: {e}",
                }
            )
            continue

        rows, year_cols = parseTable(t["table"])
        if rows is None:
            continue
        unit = detectUnit(t.get("unitHint", "") + " " + t["table"])

        # build actual lookup: {label: {year: value}}
        label_col = "항목" if "항목" in df.columns else df.columns[0]
        actual = {}
        for r in df.to_dicts():
            lbl = r.get(label_col)
            actual[lbl] = {k: v for k, v in r.items() if k.isdigit() and len(k) == 4}

        for label, year_values in rows:
            if label not in actual:
                # try fuzzy label match (label 변형)
                continue
            for year, table_v in year_values.items():
                if table_v is None:
                    continue
                act_raw = actual[label].get(year)
                act_norm = normalize(act_raw, unit)
                if act_norm is None:
                    # 표가 0이고 실측이 None이면 "데이터 없음 = 0" 으로 본문에서 의미 동일
                    if table_v == 0:
                        continue
                    issues.append(
                        {
                            "path": path,
                            "line": t["lineApprox"],
                            "topic": t["topic"],
                            "label": label,
                            "year": year,
                            "table": table_v,
                            "actual": None,
                            "msg": "actual missing",
                        }
                    )
                    continue
                # tolerance: 0.5단위 반올림 + 1% 상대 (둘 중 큰 값)
                tol = max(0.55, abs(act_norm) * 0.012)
                if abs(act_norm - table_v) > tol:
                    issues.append(
                        {
                            "path": path,
                            "line": t["lineApprox"],
                            "topic": t["topic"],
                            "label": label,
                            "year": year,
                            "table": table_v,
                            "actual": round(act_norm, 3),
                            "diff": round(act_norm - table_v, 3),
                            "unit": unit,
                        }
                    )
    return issues


def main():
    all_issues = []
    for code, path in POSTS:
        print(f"\n=== {code} {Path(path).parent.name} ===")
        issues = auditPost(code, path)
        if not issues:
            print("  OK — all values match")
            continue
        for it in issues:
            print(f"  {it}")
        all_issues.extend(issues)

    print(f"\n=== TOTAL: {len(all_issues)} issues ===")
    Path("scripts/_audit_blog_finance_report.md").write_text(
        "# Blog Finance Audit\n\n" + f"{len(all_issues)} mismatches\n\n" + "\n".join(f"- {it}" for it in all_issues),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
