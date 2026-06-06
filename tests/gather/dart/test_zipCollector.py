"""DART ZIP collector boundary tests."""

from __future__ import annotations

import io
import zipfile

from dartlab.gather.dart import zipCollector


class _Client:
    def __init__(self, payload: bytes | None) -> None:
        self.payload = payload

    def getBytes(self, endpoint: str, params: dict[str, str]) -> bytes | None:
        assert endpoint == "document.xml"
        assert params == {"rcept_no": "202503310001"}
        return self.payload


def _zipPayload(files: dict[str, bytes]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for name, payload in files.items():
            zf.writestr(name, payload)
    return buf.getvalue()


def test_collect_one_zip_parses_largest_xml(monkeypatch) -> None:
    payload = _zipPayload(
        {
            "small.xml": b"<ROOT>small</ROOT>",
            "large.xml": "<ROOT><TITLE>사업의 개요</TITLE></ROOT>".encode("utf-8"),
        }
    )

    def fakeParse(xmlContent: str) -> list[dict[str, str]]:
        assert "사업의 개요" in xmlContent
        return [{"sectionLeaf": "사업의 개요"}]

    monkeypatch.setattr(zipCollector, "_parseSections", fakeParse)

    rows = zipCollector._collectOneZip(_Client(payload), "202503310001")

    assert rows == [{"sectionLeaf": "사업의 개요"}]


def test_collect_one_zip_returns_none_for_bad_zip() -> None:
    assert zipCollector._collectOneZip(_Client(b"not-a-zip"), "202503310001") is None
