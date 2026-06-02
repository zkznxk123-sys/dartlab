"""gather.original.dart.collect — archiveDartOriginals unit 테스트 (네트워크 0)."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.unit

_PERIODIC = {
    "corp_cls": "Y",
    "stock_code": "005930",
    "report_nm": "사업보고서 (2025.12)",
    "rcept_no": "20260601000001",
}
_NONPERIODIC = {
    "corp_cls": "Y",
    "stock_code": "005930",
    "report_nm": "주요사항보고서(유상증자결정)",
    "rcept_no": "20260601000002",
}


class _FakeClient:
    """OriginalDartClient 흉내 — 한 날짜에 정기 1 + 비정기 1, getBytes 는 유효 zip."""

    def __init__(self, *_, **__):
        self.byteCalls = 0

    def getFilingsPage(self, *, bgnDe, endDe, pageNo=1, pageCount=100, corpCls=None):
        if pageNo == 1:
            return {"status": "000", "list": [_PERIODIC, _NONPERIODIC], "total_page": 1}
        return {"status": "013", "list": [], "total_page": 1}

    def getBytes(self, endpoint, params=None):
        self.byteCalls += 1
        return b"PK\x03\x04" + b"\x00" * 100

    def close(self):
        return None


def test_iterDays_and_isPeriodic() -> None:
    """_iterDays 내림차순 + _isPeriodic 정기보고서 판정."""
    from dartlab.gather.original.dart import collect

    assert collect._iterDays("20260601", "20260603") == ["20260603", "20260602", "20260601"]
    assert collect._isPeriodic("반기보고서 (2025.06)") is True
    assert collect._isPeriodic("주요사항보고서") is False


def test_archive_splits_docs_and_allFilings(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    """정기→docs/ · 비정기→allFilings/ 분리 저장 + 유효 zip(PK magic)."""
    import dartlab.config as cfg
    from dartlab.gather.original import paths
    from dartlab.gather.original.dart import collect

    monkeypatch.setattr(cfg, "dataDir", str(tmp_path))
    monkeypatch.setattr(collect, "OriginalDartClient", _FakeClient)

    stats = collect.archiveDartOriginals("20260601", "20260601", scope="all", showProgress=False)

    docsZip = paths.dartDocsDir("005930") / "20260601000001.zip"
    miscZip = paths.dartFilingsDir("005930") / "20260601000002.zip"
    assert docsZip.exists() and miscZip.exists()
    assert docsZip.read_bytes()[:4] == b"PK\x03\x04"
    assert stats["ok"] == 2 and stats["error"] == 0


def test_archive_idempotent_skip(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    """재실행 시 기존 zip skip (수집 0)."""
    import dartlab.config as cfg
    from dartlab.gather.original.dart import collect

    monkeypatch.setattr(cfg, "dataDir", str(tmp_path))
    monkeypatch.setattr(collect, "OriginalDartClient", _FakeClient)

    collect.archiveDartOriginals("20260601", "20260601", scope="all", showProgress=False)
    stats2 = collect.archiveDartOriginals("20260601", "20260601", scope="all", showProgress=False)
    assert stats2["ok"] == 0 and stats2["skipped"] == 2


def test_scope_nonperiodic_only(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    """scope=nonperiodic 면 비정기만 수집(정기 store 중복 0)."""
    import dartlab.config as cfg
    from dartlab.gather.original import paths
    from dartlab.gather.original.dart import collect

    monkeypatch.setattr(cfg, "dataDir", str(tmp_path))
    monkeypatch.setattr(collect, "OriginalDartClient", _FakeClient)

    collect.archiveDartOriginals("20260601", "20260601", scope="nonperiodic", showProgress=False)
    assert not (paths.dartDocsDir("005930") / "20260601000001.zip").exists()
    assert (paths.dartFilingsDir("005930") / "20260601000002.zip").exists()
