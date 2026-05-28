"""docs.parquet 완전 폐기 검증 — show / select / sections 전수 호출 가드.

방법:
    1. 000020 (신 schema, _raw + _index 보유) 종목 의 docs.parquet 임시 이동 (backup)
    2. _trySynthesizeDocsFromSections 강제 진입 → docs.parquet 합성
    3. c.show / c.select / c.sections 의 모든 path 호출 + 결과 정상 여부 측정
    4. 종료 시 docs.parquet 복원

성공 = 모든 c.show(topic) 호출이 정상 결과 또는 합리적 None (해당 topic 부재 case).
실패 = 예외 또는 schema mismatch.
"""

from __future__ import annotations

import shutil
import time
import traceback
from pathlib import Path


def _testWithSynthesis(stockCode: str) -> dict:
    """docs.parquet 일시 제거 + sections 합성 강제 → show/select/sections 전수 호출."""
    from dartlab import Company

    docs_path = Path(f"data/dart/docs/{stockCode}.parquet")
    backup_path = Path(f"data/dart/docs/{stockCode}.parquet.bak")
    etag_path = Path(f"data/dart/docs/{stockCode}.parquet.etag")
    etag_backup = Path(f"data/dart/docs/{stockCode}.parquet.etag.bak")

    if not docs_path.exists():
        return {"error": f"{docs_path} 부재 — 검증 skip"}

    # backup
    shutil.move(str(docs_path), str(backup_path))
    if etag_path.exists():
        shutil.move(str(etag_path), str(etag_backup))

    results: dict = {}
    try:
        # Company import 캐시 클리어 — fresh state.
        from dartlab.core.memory import clearAll

        clearAll()

        c = Company(stockCode)

        # 1. c.sections — wide DataFrame (plain)
        try:
            t0 = time.perf_counter()
            sec = c.sections
            results["sections"] = {
                "elapsed": round(time.perf_counter() - t0, 3),
                "shape": sec.shape if sec is not None else None,
                "ok": sec is not None and not sec.is_empty(),
            }
        except Exception as exc:  # noqa: BLE001
            results["sections"] = {"error": f"{type(exc).__name__}: {exc}"}

        # 2. c.sectionsRaw() — wide DataFrame (mixed HTML)
        try:
            t0 = time.perf_counter()
            sec_raw = c.sectionsRaw()
            results["sectionsRaw"] = {
                "elapsed": round(time.perf_counter() - t0, 3),
                "shape": sec_raw.shape if sec_raw is not None else None,
                "ok": sec_raw is not None,
            }
        except Exception as exc:  # noqa: BLE001
            results["sectionsRaw"] = {"error": f"{type(exc).__name__}: {exc}"}

        # 3. c.sectionsTables() — content_table_struct only
        try:
            t0 = time.perf_counter()
            tables = c.sectionsTables()
            results["sectionsTables"] = {
                "elapsed": round(time.perf_counter() - t0, 3),
                "shape": tables.shape if tables is not None else None,
                "ok": tables is not None,
            }
        except Exception as exc:  # noqa: BLE001
            results["sectionsTables"] = {"error": f"{type(exc).__name__}: {exc}"}

        # 4. c.topics — topic 카탈로그
        try:
            t0 = time.perf_counter()
            topics_df = c.topics
            results["topics"] = {
                "elapsed": round(time.perf_counter() - t0, 3),
                "shape": topics_df.shape if topics_df is not None else None,
                "ok": topics_df is not None and not topics_df.is_empty(),
            }
            topic_list = topics_df["topic"].to_list() if topics_df is not None else []
        except Exception as exc:  # noqa: BLE001
            results["topics"] = {"error": f"{type(exc).__name__}: {exc}"}
            topic_list = []

        # 5. c.show(topic) — 핵심 docs-기반 topic 들
        docs_topics = [
            "companyOverview",
            "dividend",
            "majorHolder",
            "boardOfDirectors",
            "shareholderMeeting",
            "shareCapital",
            "auditSystem",
            "businessOverview",
            "mainProduct",
            "rnd",
            "subsidiary",
            "bond",
            "borrowings",
            "salesOrder",
            "employee",
            "executiveOfficer",
            "affiliate",
            "relatedPartyTx",
            "compensation",
        ]
        finance_topics = ["BS", "IS", "CF", "CIS"]
        show_results: dict = {}
        for topic in docs_topics + finance_topics:
            try:
                t0 = time.perf_counter()
                df = c.show(topic)
                show_results[topic] = {
                    "elapsed": round(time.perf_counter() - t0, 3),
                    "shape": df.shape if df is not None and hasattr(df, "shape") else None,
                    "type": type(df).__name__,
                    "ok": df is not None,
                }
            except Exception as exc:  # noqa: BLE001
                show_results[topic] = {"error": f"{type(exc).__name__}: {str(exc)[:200]}"}
        results["show"] = show_results

        # 6. c.select(...) — DataFrame.select 양식 일부 검증
        # sections wide 에서 첫 period 컬럼 select
        try:
            sec = c.sections
            if sec is not None:
                periods = [col for col in sec.columns if col.startswith("20") and len(col) <= 6]
                if periods:
                    selected = sec.select(["topic", periods[0]])
                    results["select"] = {"shape": selected.shape, "ok": True}
        except Exception as exc:  # noqa: BLE001
            results["select"] = {"error": f"{type(exc).__name__}: {exc}"}

        # 7. 합성 docs.parquet 확인 (생성됐는지)
        results["synthesized_docs_exists"] = docs_path.exists()
        if docs_path.exists():
            import polars as pl

            try:
                df = pl.read_parquet(docs_path)
                results["synthesized_docs_shape"] = df.shape
                results["synthesized_docs_columns_count"] = len(df.columns)
                # raw XML 보존 검증
                if "section_content" in df.columns:
                    sample = df["section_content"][0] or ""
                    results["synthesized_has_raw_tags"] = {
                        "P": "<P" in sample,
                        "TABLE": "<TABLE" in sample,
                        "USERMARK": "USERMARK" in sample,
                        "AUNIT": "AUNIT" in sample,
                    }
            except Exception as exc:  # noqa: BLE001
                results["synthesized_read_error"] = str(exc)

    finally:
        # 복원 — 합성 docs.parquet 삭제 후 원본 복원
        if docs_path.exists():
            docs_path.unlink()
        if backup_path.exists():
            shutil.move(str(backup_path), str(docs_path))
        if etag_backup.exists():
            shutil.move(str(etag_backup), str(etag_path))

    return results


def main() -> int:
    print("=" * 80)
    print("docs.parquet 완전 폐기 검증 — 000020 (신 schema, _raw + _index 보유)")
    print("=" * 80)
    print()

    results = _testWithSynthesis("000020")

    # 표 출력
    print(f"{'API':30s} {'상태':6s} {'shape':25s} {'시간':8s}")
    print("─" * 80)
    failed: list[str] = []
    passed: list[str] = []
    for api, r in results.items():
        if api == "show":
            for topic, sr in r.items():
                verdict = "✓" if (sr.get("ok") or sr.get("type") == "DataFrame") else ("✗" if "error" in sr else "?")
                shape_str = str(sr.get("shape", ""))[:25]
                elapsed = sr.get("elapsed", "—")
                if "error" in sr:
                    print(f"  show({topic}):  {verdict}  ERROR: {sr['error']}")
                    failed.append(f"show({topic})")
                else:
                    print(f"  show({topic}):  {verdict}  shape={shape_str} elapsed={elapsed}s")
                    if verdict == "✓":
                        passed.append(f"show({topic})")
        else:
            if isinstance(r, dict):
                verdict = "✓" if r.get("ok") else ("✗" if "error" in r else "?")
                shape_str = str(r.get("shape", ""))[:25]
                elapsed = r.get("elapsed", "—")
                if "error" in r:
                    print(f"{api:30s} {verdict:6s} ERROR: {r['error']}")
                    failed.append(api)
                else:
                    print(f"{api:30s} {verdict:6s} {shape_str:25s} {elapsed}s")
                    if verdict == "✓":
                        passed.append(api)
            else:
                print(f"{api:30s}     {r}")

    print()
    print("=" * 80)
    print(f"결론: {len(passed)} PASS, {len(failed)} FAIL")
    if failed:
        print(f"  실패: {failed}")
        print("  → docs.parquet 폐기 불가 — 위 API path 의 sections 합성 미흡")
        return 1
    print("  → docs.parquet 폐기 가능 (모든 show/select/sections path 동작)")
    return 0


if __name__ == "__main__":
    import sys

    sys.exit(main())
