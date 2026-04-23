"""실험 121 — DuckPGQ 그래프 쿼리 스파이크.

의도:
- industry/edges.json + nodes.json 을 DuckDB 에 로드
- duckpgq community extension 설치/로드 시도
- 1-hop / 2-hop / shortest path / degree centrality 쿼리 실행
- Python set-expansion baseline 과 비교
- 피크 RSS + wall clock 기록

실행:
    cd experiments/121_duckpgqGraph
    uv run --with duckdb --with psutil python -X utf8 001_spike.py

결과:
    stdout 전체 + result.json 에 요약 저장.
"""

from __future__ import annotations

import gc
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
INDUSTRY_DIR = ROOT / "src" / "dartlab" / "industry"


def _pid_rss_mb() -> float:
    import psutil

    p = psutil.Process()
    return p.memory_info().rss / 1024 / 1024


def _measure(label: str, fn, *args, **kwargs):
    gc.collect()
    rss_before = _pid_rss_mb()
    t0 = time.perf_counter()
    result = fn(*args, **kwargs)
    t1 = time.perf_counter()
    rss_after = _pid_rss_mb()
    elapsed_ms = (t1 - t0) * 1000
    delta_mb = rss_after - rss_before
    print(f"  [{label}]  {elapsed_ms:>8.2f} ms   Δ RSS {delta_mb:>+6.1f} MB   peak {rss_after:.1f} MB")
    return result, elapsed_ms, rss_after


def _load_data():
    nodes = json.loads((INDUSTRY_DIR / "nodes.json").read_text(encoding="utf-8"))
    edges = json.loads((INDUSTRY_DIR / "edges.json").read_text(encoding="utf-8"))
    return nodes, edges


# ── Python baseline ───────────────────────────────────────────────


def _python_khop(edges: list[dict], start: str, k: int) -> set[str]:
    """set expansion 으로 start 에서 k hop 이내 reachable (supplier/customer 방향 무시 무향)."""
    adj: dict[str, set[str]] = {}
    for e in edges:
        s, t = e["fromCode"], e["toCode"]
        adj.setdefault(s, set()).add(t)
        adj.setdefault(t, set()).add(s)
    frontier = {start}
    visited = {start}
    for _ in range(k):
        next_frontier = set()
        for node in frontier:
            next_frontier |= adj.get(node, set())
        next_frontier -= visited
        visited |= next_frontier
        frontier = next_frontier
        if not frontier:
            break
    return visited - {start}


def _python_degree(edges: list[dict], industry: str) -> dict[str, int]:
    deg: dict[str, int] = {}
    for e in edges:
        if e.get("industry") != industry:
            continue
        for k in (e["fromCode"], e["toCode"]):
            deg[k] = deg.get(k, 0) + 1
    return deg


# ── DuckDB / DuckPGQ ──────────────────────────────────────────────


def _duckdb_setup():
    import duckdb

    con = duckdb.connect(":memory:")
    return con


def _try_duckpgq(con) -> bool:
    """community extension duckpgq 설치/로드 시도. 실패 시 False."""
    try:
        con.execute("INSTALL duckpgq FROM community;")
        con.execute("LOAD duckpgq;")
        con.execute("SELECT 1;")
        return True
    except Exception as exc:  # noqa: BLE001
        print(f"  [duckpgq] INSTALL/LOAD 실패: {exc}")
        return False


def _load_tables(con, nodes: list[dict], edges: list[dict]) -> None:
    import polars as pl

    nodes_df = pl.from_dicts(
        [{"stockCode": n.get("stockCode"), "corpName": n.get("corpName"), "industry": n.get("industry", "")}
         for n in nodes if n.get("stockCode")]
    ).unique(subset=["stockCode"])
    edges_df = pl.from_dicts(
        [{"fromCode": e.get("fromCode"), "toCode": e.get("toCode"),
          "type": e.get("type", ""), "industry": e.get("industry", "")}
         for e in edges if e.get("fromCode") and e.get("toCode")]
    )

    # DuckDB 1.x 는 polars DataFrame 을 직접 받는다 (pyarrow 불필요).
    con.register("nodes_view", nodes_df)
    con.register("edges_view", edges_df)
    con.execute("CREATE TABLE nodes AS SELECT * FROM nodes_view;")
    con.execute("CREATE TABLE edges AS SELECT * FROM edges_view;")
    con.execute(
        "CREATE INDEX edges_from_idx ON edges(fromCode);"
    ) if False else None  # DuckDB 자동 인덱스


def _duckpgq_create_graph(con) -> None:
    con.execute(
        """
        -CREATE PROPERTY GRAPH industryGraph
            VERTEX TABLES (nodes LABEL Company)
            EDGE TABLES (
                edges
                SOURCE KEY (fromCode) REFERENCES nodes (stockCode)
                DESTINATION KEY (toCode) REFERENCES nodes (stockCode)
                LABEL Flow
            );
        """.replace("-CREATE", "CREATE")
    )


def _duckpgq_khop(con, start: str, k: int) -> list[str]:
    """PGQ MATCH pattern — start 에서 k 이내 reachable."""
    q = f"""
        FROM GRAPH_TABLE(industryGraph
            MATCH (a:Company) -[:Flow]->{{1,{k}}} (b:Company)
            WHERE a.stockCode = '{start}'
            COLUMNS (b.stockCode AS code)
        );
        """
    res = con.execute(q).fetchall()
    return sorted({r[0] for r in res})


def _duckdb_recursive_khop(con, start: str, k: int) -> list[str]:
    """fallback: 재귀 CTE 로 k-hop. 단일 UNION 요구사항을 준수하도록 undirected view 선행."""
    # undirected 뷰를 미리 만들어 재귀 CTE 에서는 단일 UNION 만 사용.
    con.execute("""
        CREATE OR REPLACE TEMPORARY VIEW edges_undirected AS
            SELECT fromCode AS a, toCode AS b FROM edges
            UNION
            SELECT toCode AS a, fromCode AS b FROM edges;
    """)
    q = f"""
        WITH RECURSIVE reach(code, depth) AS (
            SELECT b AS code, 1 AS depth
            FROM edges_undirected WHERE a = '{start}'
            UNION
            SELECT e.b, r.depth + 1
            FROM reach r JOIN edges_undirected e ON e.a = r.code
            WHERE r.depth < {k}
        )
        SELECT DISTINCT code FROM reach WHERE code != '{start}';
        """
    res = con.execute(q).fetchall()
    return sorted({r[0] for r in res})


def _duckdb_degree(con, industry: str) -> dict[str, int]:
    q = f"""
        WITH all_codes AS (
            SELECT fromCode AS code FROM edges WHERE industry = '{industry}'
            UNION ALL
            SELECT toCode AS code FROM edges WHERE industry = '{industry}'
        )
        SELECT code, COUNT(*) AS deg FROM all_codes GROUP BY code ORDER BY deg DESC;
        """
    res = con.execute(q).fetchall()
    return {r[0]: r[1] for r in res}


# ── 메인 ───────────────────────────────────────────────────────────


def main():
    print("=" * 60)
    print("실험 121 — DuckPGQ 그래프 쿼리 스파이크")
    print("=" * 60)

    print("\n[1] 데이터 로드")
    _, t_load, _ = _measure("load json", _load_data)
    nodes, edges = _load_data()  # 실측용 캐시
    print(f"  nodes={len(nodes)}  edges={len(edges)}")

    START = "005930"  # 삼성전자
    INDUSTRY = "semiconductor"

    print("\n[2] Python baseline — set expansion")
    _, py_1hop_ms, _ = _measure("python 1-hop", _python_khop, edges, START, 1)
    _, py_2hop_ms, _ = _measure("python 2-hop", _python_khop, edges, START, 2)
    _, py_3hop_ms, _ = _measure("python 3-hop", _python_khop, edges, START, 3)
    _, py_deg_ms, _ = _measure(f"python degree({INDUSTRY})", _python_degree, edges, INDUSTRY)

    print("\n[3] DuckDB 연결 및 테이블 로드")
    try:
        con = _duckdb_setup()
    except Exception as exc:  # noqa: BLE001
        print(f"  [FATAL] duckdb import 실패: {exc}")
        print("  → uv run --with duckdb --with polars --with pandas 로 실행 필요")
        return 2

    _, t_tables, _ = _measure("load tables", _load_tables, con, nodes, edges)

    print("\n[4] duckpgq 설치/로드 시도")
    has_pgq = _try_duckpgq(con)
    print(f"  duckpgq: {'OK' if has_pgq else 'FALLBACK'}")

    pgq_1 = pgq_2 = pgq_3 = None
    if has_pgq:
        print("\n[5] PGQ property graph 생성")
        try:
            _duckpgq_create_graph(con)
            print("  CREATE PROPERTY GRAPH OK")
            print("\n[6] PGQ MATCH k-hop")
            _, pgq_1, _ = _measure("pgq 1-hop", _duckpgq_khop, con, START, 1)
            _, pgq_2, _ = _measure("pgq 2-hop", _duckpgq_khop, con, START, 2)
            _, pgq_3, _ = _measure("pgq 3-hop", _duckpgq_khop, con, START, 3)
        except Exception as exc:  # noqa: BLE001
            print(f"  [PGQ ERR] {exc}")
            has_pgq = False

    print("\n[7] DuckDB 재귀 CTE fallback")
    _, rec_1, _ = _measure("rcte 1-hop", _duckdb_recursive_khop, con, START, 1)
    _, rec_2, _ = _measure("rcte 2-hop", _duckdb_recursive_khop, con, START, 2)
    _, rec_3, _ = _measure("rcte 3-hop", _duckdb_recursive_khop, con, START, 3)

    print("\n[8] DuckDB degree centrality (SQL GROUP BY)")
    _, duck_deg_ms, _ = _measure(f"duck degree({INDUSTRY})", _duckdb_degree, con, INDUSTRY)

    print("\n" + "=" * 60)
    print("요약")
    print("=" * 60)
    print(f"python 1/2/3-hop: {py_1hop_ms:.1f} / {py_2hop_ms:.1f} / {py_3hop_ms:.1f} ms")
    print(f"rcte   1/2/3-hop: {rec_1:.1f} / {rec_2:.1f} / {rec_3:.1f} ms")
    if has_pgq and pgq_2 is not None:
        print(f"pgq    1/2/3-hop: {pgq_1:.1f} / {pgq_2:.1f} / {pgq_3:.1f} ms")
    print(f"degree     python/duck: {py_deg_ms:.1f} / {duck_deg_ms:.1f} ms")
    print(f"duckpgq 사용 가능: {has_pgq}")

    # 결과 저장
    summary = {
        "nodes": len(nodes),
        "edges": len(edges),
        "start": START,
        "industry": INDUSTRY,
        "pythonBaseline": {"1hop_ms": py_1hop_ms, "2hop_ms": py_2hop_ms, "3hop_ms": py_3hop_ms, "degree_ms": py_deg_ms},
        "duckdbRCTE": {"1hop_ms": rec_1, "2hop_ms": rec_2, "3hop_ms": rec_3},
        "duckpgq": {"available": has_pgq, "1hop_ms": pgq_1, "2hop_ms": pgq_2, "3hop_ms": pgq_3} if has_pgq else {"available": False},
        "duckdbDegree": {"degree_ms": duck_deg_ms},
    }
    out = Path(__file__).parent / "result.json"
    out.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n결과 저장: {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
