"""Pyodide-specific parquet loading for ``core.dataLoader``."""

from __future__ import annotations

from pathlib import Path

import polars as pl

from dartlab.core.dataConfig import DATA_RELEASES, hfBaseUrl


def loadDataPyodide(
    stockCode: str,
    category: str,
    *,
    sinceYear: int | None = None,
    columns: list[str] | None = None,
) -> pl.DataFrame:
    """Pyodide 환경: pre-fetched FS 파일 → pyarrow → polars."""
    import io

    import pyarrow.parquet as pq

    dirPath = DATA_RELEASES[category]["dir"]
    path = Path(f"/data/{dirPath}/{stockCode}.parquet")

    if not path.exists():
        pyodideFetchToFS(stockCode, category, dirPath, path)

    arrowTable = pq.read_table(io.BytesIO(path.read_bytes()))
    try:
        df = pl.from_arrow(arrowTable)
    except (ModuleNotFoundError, ImportError):
        import pyarrow as _pa  # noqa: F811

        try:
            import polars.dependencies as _pdeps

            _pdeps._lazy_import.cache_clear() if hasattr(_pdeps._lazy_import, "cache_clear") else None
            _pdeps.pyarrow = _pa  # type: ignore[attr-defined]
        except (AttributeError, TypeError):
            pass
        try:
            df = pl.from_arrow(arrowTable)
        except (ModuleNotFoundError, ImportError):
            df = pl.DataFrame(arrowTable.to_pydict())

    if sinceYear is not None:
        for colName in ("year", "bsns_year"):
            if colName in df.columns:
                yearCol = pl.col(colName)
                if df.schema[colName] == pl.Utf8:
                    yearCol = yearCol.cast(pl.Int32, strict=False)
                df = df.filter(yearCol >= sinceYear)
                break

    if columns:
        available = [c for c in columns if c in df.columns]
        if available:
            df = df.select(available)

    from dartlab.core.dataLoaderNormalize import normalizeLoadedFrame

    return normalizeLoadedFrame(df, category)


def pyodideFetchScanLite(dataDirForCategory) -> None:
    """Pyodide: scan 경량 프리빌드(`finance-lite.parquet`)만 받아 FS에 저장."""
    from dartlab.core.messaging import emit

    scanDir = Path(dataDirForCategory("scan"))
    scanDir.mkdir(parents=True, exist_ok=True)
    dest = scanDir / "finance-lite.parquet"

    try:
        pyodideFetchToFS("finance-lite", "scan", "dart/scan", dest)
    except (RuntimeError, OSError) as exc:
        emit("scan:prebuild_failed", error=str(exc))
        raise

    if not dest.exists() or dest.stat().st_size < 1024 * 1024:
        emit(
            "scan:prebuild_incomplete",
            missing=["finance-lite.parquet (수신 실패 또는 1MB 미만)"],
        )
        raise RuntimeError("scan finance-lite 수신 실패. 네트워크/HF 응답 확인 후 재시도하세요.")

    sizeMb = dest.stat().st_size / 1024 / 1024
    emit("scan:prebuild_ready", fileCount=f"{sizeMb:.1f}MB (finance-lite)")


def pyodideFetchToFS(stockCode: str, category: str, dirPath: str, path: Path) -> None:
    """Pyodide: HF에서 parquet을 fetch하여 FS에 저장."""
    url = f"{hfBaseUrl(category)}/{stockCode}.parquet"
    path.parent.mkdir(parents=True, exist_ok=True)

    buf = None

    try:
        from pyodide.ffi import run_sync  # type: ignore[import-not-found]
        from pyodide.http import pyfetch  # type: ignore[import-not-found]

        resp = run_sync(pyfetch(url))
        if resp.status == 200:
            buf = bytes(run_sync(resp.bytes()))
    except Exception:
        pass

    if buf is None:
        try:
            import asyncio

            from pyodide.http import pyfetch  # type: ignore[import-not-found]

            async def _fetch():
                resp = await pyfetch(url)
                if resp.status != 200:
                    raise RuntimeError(f"HTTP {resp.status}")
                return await resp.bytes()

            loop = asyncio.get_event_loop()
            if loop.is_running():
                raise RuntimeError("event loop running")
            buf = loop.run_until_complete(_fetch())
        except Exception:
            pass

    if buf is None:
        try:
            from js import XMLHttpRequest  # type: ignore[import-not-found]

            xhr = XMLHttpRequest.new()
            xhr.open("GET", url, False)
            xhr.overrideMimeType("text/plain; charset=x-user-defined")
            xhr.send()
            if xhr.status == 200:
                raw = xhr.responseText
                buf = bytes(ord(c) & 0xFF for c in raw)
        except Exception:
            pass

    if buf is None:
        try:
            from pyodide.http import open_url  # type: ignore[import-not-found]

            resp = open_url(url)
            raw = resp.read()
            buf = raw.encode("latin-1") if isinstance(raw, str) else raw
        except Exception:
            pass

    if buf is None:
        raise RuntimeError(
            f"Pyodide fetch 실패: {url}\n"
            "데이터를 수동으로 로드하세요:\n"
            "  from pyodide.http import pyfetch\n"
            f"  resp = await pyfetch('{url}')\n"
            f"  buf = await resp.bytes()\n"
            "  import os; os.makedirs('/data/{dirPath}', exist_ok=True)\n"
            f"  open('/data/{dirPath}/{stockCode}.parquet', 'wb').write(buf)"
        )

    path.write_bytes(buf)


__all__ = ["loadDataPyodide", "pyodideFetchScanLite", "pyodideFetchToFS"]
