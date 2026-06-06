"""DART ``document.xml`` ZIP parser for single-filing reads.

The DART disclosure text SSOT is ``data/dart/panel``. This module only parses a
single OpenDART ``document.xml`` response for caller flows such as
``readFiling`` and catalog repair paths; it does not build or write parquet.
"""

from __future__ import annotations

import io
import zipfile

from dartlab.core.dartClient import DartClient


def _parseSections(xmlContent: str) -> list[dict]:
    """Parse DART XML into section rows through the shared title parser."""
    from dartlab.core.dartBuild import parseSectionsByTitle

    return parseSectionsByTitle(xmlContent)


def _collectOneZip(client: DartClient, rceptNo: str) -> list[dict] | None:
    """Download one ``document.xml`` ZIP and parse its largest XML member."""
    try:
        raw = client.getBytes("document.xml", {"rcept_no": rceptNo})
    except (RuntimeError, OSError):
        return None

    if raw is None:
        return None

    try:
        zf = zipfile.ZipFile(io.BytesIO(raw))
    except zipfile.BadZipFile:
        return None

    names = zf.namelist()
    if not names:
        return None

    largest = max(names, key=lambda n: zf.getinfo(n).file_size)
    content = zf.read(largest)

    xmlContent = None
    for enc in ("utf-8", "euc-kr", "cp949"):
        try:
            xmlContent = content.decode(enc)
            break
        except (UnicodeDecodeError, LookupError):
            continue
    if xmlContent is None:
        xmlContent = content.decode("utf-8", errors="replace")

    return _parseSections(xmlContent)


__all__ = ["_collectOneZip", "_parseSections"]
