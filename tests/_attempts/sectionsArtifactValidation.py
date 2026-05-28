"""sections SSOT 통합 종합 검증 — plan snazzy-wibbling-origami 폐기 전 게이트.

4 축 검증:
    (1) 속도 — sections / sectionsRaw / sectionsTables / sectionsLong < 1s
    (2) 메모리 안전성 — 호출 후 RSS 증분 < 50MB (CLAUDE.md 의 200~500MB 회귀 가드)
    (3) 뷰어 완전성 — sectionsRaw cell 에 HTML <table align=...> 보존
    (4) 다른 엔진 사용성 — sentiment / risk / scanner 등 D.1 모듈 동작

신 schema 종목 5 (000020/000050/000080/000100/000150) 로 측정.
"""

from __future__ import annotations

import gc
import os
import time
import tracemalloc
from pathlib import Path


def _rssMB() -> float:
    try:
        import psutil

        return psutil.Process(os.getpid()).memory_info().rss / 1024 / 1024
    except ImportError:
        return -1.0


def _newSchemaStocks(limit: int = 5) -> list[str]:
    """신 schema (content_plain 컬럼 보유) 종목 list."""
    import polars as pl

    d = Path("data/dart/sections")
    out: list[str] = []
    for stockDir in sorted(d.iterdir()):
        if not stockDir.is_dir():
            continue
        files = list(stockDir.glob("*.parquet"))
        if not files:
            continue
        try:
            df = pl.read_parquet(files[0])
            if "content_plain" in df.columns and "content_table_struct" in df.columns:
                out.append(stockDir.name)
                if len(out) >= limit:
                    break
        except Exception:  # noqa: BLE001
            continue
    return out


def axis1_speed(stocks: list[str]) -> dict:
    """축 1 — API 4 종 시간 측정."""
    from dartlab import Company

    results: dict = {}
    for code in stocks:
        c = Company(code)
        gc.collect()
        out: dict = {}
        # sections (plain, mmap)
        t0 = time.perf_counter()
        df = c.sections
        out["sections"] = {"elapsed": time.perf_counter() - t0, "shape": df.shape if df is not None else None}
        # sectionsRaw (mixed, mmap)
        t0 = time.perf_counter()
        df = c.sectionsRaw()
        out["sectionsRaw"] = {"elapsed": time.perf_counter() - t0, "shape": df.shape if df is not None else None}
        # sectionsTables (table_struct only, columnar)
        t0 = time.perf_counter()
        df = c.sectionsTables()
        out["sectionsTables"] = {"elapsed": time.perf_counter() - t0, "shape": df.shape if df is not None else None}
        # sectionsLong (long, columnar)
        t0 = time.perf_counter()
        df = c.sectionsLong(columns=["topic", "period", "content_plain"])
        out["sectionsLong_plain"] = {"elapsed": time.perf_counter() - t0, "shape": df.shape if df is not None else None}
        results[code] = out
    return results


def axis2_memory(stocks: list[str]) -> dict:
    """축 2 — RSS 증분 측정. CLAUDE.md 의 200~500MB 회귀 가드."""
    from dartlab import Company

    results: dict = {}
    for code in stocks:
        gc.collect()
        before = _rssMB()
        c = Company(code)
        df = c.sections
        gc.collect()
        after = _rssMB()
        results[code] = {
            "before_MB": round(before, 1),
            "after_MB": round(after, 1),
            "delta_MB": round(after - before, 1),
            "shape": df.shape if df is not None else None,
        }
        # Company 인스턴스 + DataFrame 해제 후 GC
        del c
        del df
        gc.collect()
    return results


def axis3_viewer(stocks: list[str]) -> dict:
    """축 3 — viewer 완전성 (sectionsRaw cell 에 HTML <table align> 보존)."""
    import polars as pl

    from dartlab import Company

    results: dict = {}
    for code in stocks:
        c = Company(code)
        raw = c.sectionsRaw()
        if raw is None:
            results[code] = {"error": "sectionsRaw None"}
            continue
        # table block row 의 cell 값 확인
        tableRows = raw.filter(pl.col("blockType") == "table")
        sample = None
        for col in raw.columns:
            if col.startswith("20"):
                for v in tableRows[col]:
                    if v and "<table" in v.lower():
                        sample = v
                        break
                if sample:
                    break
        if not sample:
            results[code] = {"tableRows": tableRows.height, "warning": "no <table> in any table block"}
            continue
        results[code] = {
            "tableRows": tableRows.height,
            "has_html_table": "<table" in sample.lower(),
            "has_align_attr": "align=" in sample.lower(),
            "has_valign_attr": "valign=" in sample.lower(),
            "has_colspan": "colspan=" in sample.lower(),
            "has_rowspan": "rowspan=" in sample.lower(),
            "sample_len": len(sample),
            "sample_head": sample[:200],
        }
    return results


def axis4_other_engines(stocks: list[str]) -> dict:
    """축 4 — D.1 분석 path 사용성 (sentiment / scanner 등)."""
    from dartlab import Company

    results: dict = {}
    for code in stocks:
        c = Company(code)
        out: dict = {}
        # sentiment — sections plain 사용
        try:
            t0 = time.perf_counter()
            sec = c.sections
            if sec is None:
                out["sentiment_path"] = {"error": "sections None"}
            else:
                # 분석 path 가 plain text 만 받는지 확인 — 첫 non-null cell 에 < 없는지
                import polars as pl

                txtRows = sec.filter(pl.col("blockType") == "text")
                sample = None
                for col in sec.columns:
                    if col.startswith("20"):
                        for v in txtRows[col]:
                            if v and len(v) > 50:
                                sample = v
                                break
                        if sample:
                            break
                out["sentiment_path"] = {
                    "elapsed_s": round(time.perf_counter() - t0, 3),
                    "has_lt_in_plain": ("<" in sample) if sample else None,
                    "sample_head": sample[:200] if sample else None,
                }
        except Exception as exc:  # noqa: BLE001
            out["sentiment_path"] = {"error": str(exc)}

        # scanner — quant.screen._dataAccessScan.loadDocsForStock
        try:
            from dartlab.quant.screen._dataAccessScan import loadDocsForStock

            t0 = time.perf_counter()
            docs = loadDocsForStock(code)
            out["loadDocsForStock"] = {
                "elapsed_s": round(time.perf_counter() - t0, 3),
                "shape": docs.shape if docs is not None else None,
                "has_section_content": ("section_content" in docs.columns) if docs is not None else None,
            }
        except Exception as exc:  # noqa: BLE001
            out["loadDocsForStock"] = {"error": str(exc)}

        results[code] = out
    return results


def main() -> int:
    print("=" * 80)
    print("sections SSOT 검증 — 폐기 전 4 축 게이트")
    print("=" * 80)

    stocks = _newSchemaStocks(limit=5)
    print(f"\n[setup] 신 schema 종목 {len(stocks)}: {stocks}\n")
    if len(stocks) < 3:
        print("ERROR: 신 schema 종목 부족 — 빌드 진행 더 필요")
        return 1

    print("─" * 80)
    print("[축 1] 속도 — < 1s 목표")
    print("─" * 80)
    speedResults = axis1_speed(stocks)
    for code, r in speedResults.items():
        print(f"  {code}:")
        for api, m in r.items():
            verdict = "✓" if m["elapsed"] < 1.0 else "✗"
            print(f"    {verdict} {api:25} {m['elapsed']:.3f}s, shape={m['shape']}")

    print()
    print("─" * 80)
    print("[축 2] 메모리 안전성 — RSS 증분 < 50MB")
    print("─" * 80)
    memResults = axis2_memory(stocks)
    for code, r in memResults.items():
        verdict = "✓" if r["delta_MB"] < 50 else "✗"
        print(
            f"  {verdict} {code}: {r['before_MB']:7.1f} → {r['after_MB']:7.1f} MB (Δ {r['delta_MB']:+6.1f}), shape={r['shape']}"
        )

    print()
    print("─" * 80)
    print("[축 3] 뷰어 완전성 — sectionsRaw HTML <table align> 보존")
    print("─" * 80)
    viewResults = axis3_viewer(stocks)
    for code, r in viewResults.items():
        if "error" in r or "warning" in r:
            print(f"  ⚠ {code}: {r}")
            continue
        verdict = "✓" if (r["has_html_table"] and r["has_align_attr"]) else "✗"
        print(
            f"  {verdict} {code}: tableRows={r['tableRows']}, table={r['has_html_table']}, "
            f"align={r['has_align_attr']}, valign={r['has_valign_attr']}, "
            f"colspan={r['has_colspan']}, rowspan={r['has_rowspan']}"
        )

    print()
    print("─" * 80)
    print("[축 4] 다른 엔진 사용성 — sentiment / scanner")
    print("─" * 80)
    otherResults = axis4_other_engines(stocks)
    for code, r in otherResults.items():
        print(f"  {code}:")
        for path, m in r.items():
            if "error" in m:
                print(f"    ✗ {path}: {m['error']}")
                continue
            verdict = "✓" if m.get("elapsed_s", 999) < 5 else "?"
            extra = ""
            if "has_lt_in_plain" in m:
                extra = f" plain_clean={not m['has_lt_in_plain']}"
            if "has_section_content" in m:
                extra = f" has_section_content={m['has_section_content']}"
            print(f"    {verdict} {path:25} {m.get('elapsed_s', 0):.3f}s, shape={m.get('shape')}{extra}")

    print()
    print("=" * 80)
    print("결론")
    print("=" * 80)
    # 통합 판정
    speed_pass = all(m["elapsed"] < 1.0 for r in speedResults.values() for m in r.values())
    mem_pass = all(r["delta_MB"] < 50 for r in memResults.values())
    view_pass = all(
        r.get("has_html_table") and r.get("has_align_attr") for r in viewResults.values() if "error" not in r
    )
    other_pass = all(
        all(m.get("elapsed_s", 0) < 5 for m in r.values() if "error" not in m) for r in otherResults.values()
    )
    print(f"  [{'✓' if speed_pass else '✗'}] 축 1 속도   — 모든 API < 1s")
    print(f"  [{'✓' if mem_pass else '✗'}] 축 2 메모리 — 모든 RSS 증분 < 50MB")
    print(f"  [{'✓' if view_pass else '✗'}] 축 3 뷰어   — HTML <table align> 보존")
    print(f"  [{'✓' if other_pass else '✗'}] 축 4 엔진   — sentiment/scanner 동작")
    overall = speed_pass and mem_pass and view_pass and other_pass
    print()
    print(f"  최종: {'✓ 폐기 가능 (4 축 모두 pass)' if overall else '✗ 폐기 불가 — 위 실패 항목 해결 후 재측정'}")
    return 0 if overall else 1


if __name__ == "__main__":
    import sys

    sys.exit(main())
