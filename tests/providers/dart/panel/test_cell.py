"""panel cell read mirror — freq 토큰 선택 + acode×period pivot (합성 parquet, 데이터 0).

``cell.py`` 의 ``readCellWide``/``_freqMask``/``_periodLabelExpr``/``cellStatements``. 합성 셀
parquet 을 tmp dataDir 에 써서 freq 분기·평탄화·dedup 을 검증 (lxml/network 0, R2).
"""

from __future__ import annotations

import ast
from pathlib import Path

import polars as pl
import pytest

pytestmark = pytest.mark.unit

from dartlab.providers.dart.panel.cellSchema import CELL_SCHEMA


def _cellRows() -> list[dict]:
    """합성 셀 행 — IS2 Revenue(연간/분기단독/누적) + EF 같은 acode 2축(충돌)."""
    rows = []
    # IS2 Revenue 연간 (FY annual report, 2025Q4 filing): CFY 2025, PFY 2024
    for year, mode, q, flow, scope2, val in [
        (2025, "Y", 4, "d", "ConsolidatedMember", "100"),
        (2024, "Y", 4, "d", "ConsolidatedMember", "90"),
    ]:
        rows.append(_row("2025Q4", "IS2", "ifrs-full_Revenue", "매출액", year, flow, q, mode, scope2, val))
    # IS2 Revenue 분기 (2025Q3 filing): 단독 Q3 + 누적 9M
    rows.append(_row("2025Q3", "IS2", "ifrs-full_Revenue", "매출액", 2025, "d", 3, "Q", "ConsolidatedMember", "30"))
    rows.append(_row("2025Q3", "IS2", "ifrs-full_Revenue", "매출액", 2025, "d", 3, "A", "ConsolidatedMember", "75"))
    # EF 같은 acode 2 축 (평탄화 충돌 회피)
    rows.append(_row("2025Q4", "EF", "ifrs-full_Equity", "자본", 2025, "e", 4, "Y", "RetainedEarningsMember", "7"))
    rows.append(_row("2025Q4", "EF", "ifrs-full_Equity", "자본", 2025, "e", 4, "Y", "IssuedCapitalMember", "1"))
    return rows


def _row(fp, stmt, acode, label, year, flow, q, mode, member, val):
    return {
        "corp": "TEST01",
        "rceptNo": "2026" + fp[-2:] + "00000000",
        "filingPeriod": fp,
        "statement": stmt,
        "scope": "consolidated",
        "acode": acode,
        "label": label,
        "ctxYear": year,
        "ctxFlow": flow,
        "ctxQuarter": q,
        "ctxMode": mode,
        "axisPath": member,
        "valueRaw": val,
        "cellOrder": 0,
    }


def _writeCells(tmp: Path) -> None:
    out = tmp / "dart" / "panelCell" / "TEST01"
    out.mkdir(parents=True)
    df = pl.DataFrame(_cellRows(), schema=CELL_SCHEMA)
    for fp in df["filingPeriod"].unique():
        df.filter(pl.col("filingPeriod") == fp).write_parquet(str(out / f"{fp}.parquet"))


@pytest.fixture
def cellEnv(tmp_path, monkeypatch):
    import dartlab.config as cfg

    monkeypatch.setattr(cfg, "dataDir", str(tmp_path))
    _writeCells(tmp_path)
    return tmp_path


def test_cell_statements() -> None:
    """셀 대상 = 재무 5표."""
    from dartlab.providers.dart.panel.cell import cellStatements

    assert cellStatements() == frozenset({"BS", "IS2", "IS3", "CF", "EF"})


def test_freq_year_selects_fy(cellEnv) -> None:
    """freq=year → ctxMode=Y (dFY) 만, 열=연도."""
    from dartlab.providers.dart.panel.cell import readCellWide

    w = readCellWide("TEST01", statement="IS2", freq="year")
    assert w is not None
    periodCols = [c for c in w.columns if c.isdigit()]
    assert set(periodCols) == {"2025", "2024"}
    rev = w.filter(pl.col("acode") == "ifrs-full_Revenue")
    assert rev["2025"][0] == "100" and rev["2024"][0] == "90"


def test_freq_quarter_vs_ytd_token_split(cellEnv) -> None:
    """freq=quarter → 단독(Q)=30, ytd → 누적(A)=75 (같은 분기, 다른 토큰)."""
    from dartlab.providers.dart.panel.cell import readCellWide

    q = readCellWide("TEST01", statement="IS2", freq="quarter")
    y = readCellWide("TEST01", statement="IS2", freq="ytd")
    qv = q.filter(pl.col("acode") == "ifrs-full_Revenue")["2025Q3"][0]
    yv = y.filter(pl.col("acode") == "ifrs-full_Revenue")["2025Q3"][0]
    assert qv == "30"  # 단독
    assert yv == "75"  # 누적


def test_axispath_no_collision(cellEnv) -> None:
    """같은 acode 다른 axisPath → 별 행 (평탄화 충돌 0)."""
    from dartlab.providers.dart.panel.cell import readCellWide

    w = readCellWide("TEST01", statement="EF", freq="year")
    eq = w.filter(pl.col("acode") == "ifrs-full_Equity")
    assert eq.height == 2  # RetainedEarnings + IssuedCapital
    assert set(eq["axisPath"].to_list()) == {"RetainedEarningsMember", "IssuedCapitalMember"}


def test_absent_artifact_returns_none(tmp_path, monkeypatch) -> None:
    """셀 artifact 없는 종목 → None (경계 이전 graceful)."""
    import dartlab.config as cfg

    monkeypatch.setattr(cfg, "dataDir", str(tmp_path))
    from dartlab.providers.dart.panel.cell import readCellWide

    assert readCellWide("999999", statement="IS2", freq="year") is None


def test_invalid_statement_returns_none() -> None:
    """5표 외 statement → None."""
    from dartlab.providers.dart.panel.cell import readCellWide

    assert readCellWide("005930", statement="NT_D826380", freq="year") is None


def test_read_no_lxml_import() -> None:
    """cell read 표면은 lxml/zipfile import 0 (R2)."""
    src = Path("src/dartlab/providers/dart/panel/cell.py").read_text(encoding="utf-8")
    tree = ast.parse(src)
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(a.name.split(".")[0] for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module.split(".")[0])
    assert "lxml" not in imported and "zipfile" not in imported


# --- readStatement (native 재무제표 — XBRL+옛 항목명 통합) ---


def test_normalize_label() -> None:
    """(주N) strip + 공백 제거 → 매칭 키."""
    from dartlab.providers.dart.panel.cell import _normalizeLabel

    out = pl.select(_normalizeLabel(pl.lit("매출액 (주30)")).alias("x"))["x"][0]
    assert out == "매출액"
    out2 = pl.select(_normalizeLabel(pl.lit("수익(매출액)")).alias("x"))["x"][0]
    assert out2 == "수익(매출액)"  # 주N 아님 → 보존 (개명 항목 별 행)


def _statementRows() -> list[dict]:
    """IS2 top-level 매출 — XBRL(2025/2024) + 옛 통합(2020 매출액, 2015 수익(매출액))."""
    rows = [
        _row("2025Q4", "IS2", "ifrs-full_Revenue", "매출액 (주30)", 2025, "d", 4, "Y", "ConsolidatedMember", "300"),
        _row("2025Q4", "IS2", "ifrs-full_Revenue", "매출액 (주30)", 2024, "d", 4, "Y", "ConsolidatedMember", "290"),
    ]
    # 옛 셀 (acode=None): 같은 항목명(주석번호만 다름) → 통합 / 개명 → 별 행
    rows.append(_oldRow("2020Q4", "매출액 (주28)", 2020, "200"))
    rows.append(_oldRow("2015Q4", "수익(매출액)", 2015, "150"))
    return rows


def _oldRow(fp, label, year, val):
    r = _row(fp, "IS2", None, label, year, "d", 4, "Y", "ConsolidatedMember", val)
    r["rceptNo"] = "20" + fp[:4] + "00000000"  # 연도순 rceptNo (XBRL 최신 우선 dedup)
    return r


@pytest.fixture
def statementEnv(tmp_path, monkeypatch):
    import dartlab.config as cfg

    monkeypatch.setattr(cfg, "dataDir", str(tmp_path))
    out = tmp_path / "dart" / "panelCell" / "ST01"
    out.mkdir(parents=True)
    df = pl.DataFrame(_statementRows(), schema=CELL_SCHEMA)
    for fp in df["filingPeriod"].unique():
        df.filter(pl.col("filingPeriod") == fp).write_parquet(str(out / f"{fp}.parquet"))
    return tmp_path


def test_read_statement_unifies_xbrl_and_old(statementEnv) -> None:
    """항목명 정규화 통합 — '매출액'(XBRL+옛 통합) 한 행이 2025~2020 연속, 개명 '수익(매출액)' 별 행."""
    from dartlab.providers.dart.panel.cell import readStatement

    w = readStatement("ST01", statement="IS2", freq="year")
    assert w is not None
    years = sorted([c for c in w.columns if c.isdigit()])
    assert years == ["2015", "2020", "2024", "2025"]  # XBRL 경계(2024) 넘어 옛 연장
    mae = w.filter(pl.col("account") == "매출액")
    assert mae.height == 1  # (주30)/(주28) 통합
    assert mae["2025"][0] == "300" and mae["2020"][0] == "200"  # XBRL + 옛 한 행
    su = w.filter(pl.col("account") == "수익(매출액)")
    assert su.height == 1 and su["2015"][0] == "150"  # 개명 별 행 (숨김 0)


def test_read_statement_old_acode_none(statementEnv) -> None:
    """옛 셀은 acode 없이도 항목명으로 statement view 에 들어감."""
    from dartlab.providers.dart.panel.cell import readStatement

    w = readStatement("ST01", statement="IS2", freq="year")
    assert "2015" in w.columns  # acode=None 옛 셀이 과거 열 제공
