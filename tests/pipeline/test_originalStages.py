"""원본=SSOT stage(dartZip·edgarPanel) 데이터손실 가드 단위 — 네트워크 0(mock)."""

from __future__ import annotations

import tarfile

import pytest

pytestmark = pytest.mark.unit


def _makeTar(path, zipNames: list[str]) -> None:
    """zipNames 를 멤버로 갖는 회사 tar 생성(각 멤버는 유효 zip magic)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    for nm in zipNames:
        z = path.parent / nm
        z.write_bytes(b"PK\x03\x04" + b"\x00" * 50)
    with tarfile.open(path, "w") as tf:
        for nm in zipNames:
            tf.add(path.parent / nm, arcname=nm)
    for nm in zipNames:
        (path.parent / nm).unlink()


def test_dartzip_seed_safe_set_404_vs_transient(monkeypatch, tmp_path) -> None:
    """_seedChangedFromHf — 성공·404 는 safe, *일시 실패*·부분추출은 제외(데이터손실 가드)."""
    import huggingface_hub

    import dartlab.config as cfg
    from dartlab.pipeline import hfUpload
    from dartlab.pipeline.stages import dartZip

    monkeypatch.setattr(cfg, "dataDir", str(tmp_path))
    monkeypatch.setattr(hfUpload, "_resolveHfToken", lambda token=None: "x")
    # retryHfCall 패스스루(재시도 로직 우회 — 예외 즉시 전파)
    monkeypatch.setattr("dartlab.core.hfRetry.retryHfCall", lambda fn, *a, **k: fn(*a, **k))

    from huggingface_hub.utils import EntryNotFoundError

    tarDir = tmp_path / "_hf"
    _makeTar(tarDir / "AAA.tar", ["r1.zip", "r2.zip"])  # 완전 tar(2 멤버)

    def fakeDownload(*, repo_id, repo_type, filename, token):
        code = filename.split("/")[-1][:-4]
        if code == "AAA":
            return str(tarDir / "AAA.tar")
        if code == "BBB":
            raise EntryNotFoundError("404")  # 신규 종목
        raise RuntimeError("transient 5xx")  # 일시 실패 → 제외

    monkeypatch.setattr(huggingface_hub, "hf_hub_download", fakeDownload)

    n, safe = dartZip._seedChangedFromHf(["AAA", "BBB", "CCC"], token="x")
    assert safe == {"AAA", "BBB"}  # CCC(일시 실패) 제외
    assert n == 1  # AAA 만 실제 추출
    extracted = sorted(p.name for p in (tmp_path / "original" / "dart" / "docs" / "AAA").glob("*.zip"))
    assert extracted == ["r1.zip", "r2.zip"]  # 완전 추출


def test_dartzip_seed_partial_extract_excluded(monkeypatch, tmp_path) -> None:
    """부분 추출(zip < tar 멤버)은 무결성 실패 → safe 제외(잘린 panel·tar 덮어쓰기 차단)."""
    import huggingface_hub

    import dartlab.config as cfg
    from dartlab.pipeline import hfUpload
    from dartlab.pipeline.stages import dartZip

    monkeypatch.setattr(cfg, "dataDir", str(tmp_path))
    monkeypatch.setattr(hfUpload, "_resolveHfToken", lambda token=None: "x")
    monkeypatch.setattr("dartlab.core.hfRetry.retryHfCall", lambda fn, *a, **k: fn(*a, **k))

    # 멤버 0 인 빈 tar → 정상(공집합). 손상 tar 는 tarfile 이 raise → 제외.
    bad = tmp_path / "_hf" / "DDD.tar"
    bad.parent.mkdir(parents=True, exist_ok=True)
    bad.write_bytes(b"not a tar at all")

    monkeypatch.setattr(huggingface_hub, "hf_hub_download", lambda **k: str(bad))
    n, safe = dartZip._seedChangedFromHf(["DDD"], token="x")
    assert safe == set() and n == 0  # 손상 tar → 제외


def test_seed_ticker_panel_404_vs_transient(monkeypatch, tmp_path) -> None:
    """_seedTickerPanel — board 404=False, board 일시실패=None, cell 일시실패=None(셀 손실 가드)."""
    import huggingface_hub

    import dartlab.config as cfg
    from dartlab.pipeline import hfUpload
    from dartlab.pipeline.stages import edgarPanel

    monkeypatch.setattr(cfg, "dataDir", str(tmp_path))
    monkeypatch.setattr(hfUpload, "_resolveHfToken", lambda token=None: "x")
    monkeypatch.setattr("dartlab.core.hfRetry.retryHfCall", lambda fn, *a, **k: fn(*a, **k))

    from huggingface_hub.utils import EntryNotFoundError

    state = {"boardErr": None, "cellErr": None}

    def fake(*, repo_id, repo_type, filename, token, local_dir):
        if "panelCell" in filename:
            if state["cellErr"]:
                raise state["cellErr"]
        elif state["boardErr"]:
            raise state["boardErr"]
        return filename

    monkeypatch.setattr(huggingface_hub, "hf_hub_download", fake)

    # board 404 → False(신규)
    state.update(boardErr=EntryNotFoundError("404"), cellErr=None)
    assert edgarPanel._seedTickerPanel("AAR", token="x") is False
    # board 일시실패 → None
    state.update(boardErr=RuntimeError("5xx"), cellErr=None)
    assert edgarPanel._seedTickerPanel("AAR", token="x") is None
    # board ok + cell 404 → True(셀 0 종목 정상)
    state.update(boardErr=None, cellErr=EntryNotFoundError("404"))
    assert edgarPanel._seedTickerPanel("AAR", token="x") is True
    # board ok + cell 일시실패 → None(기존 셀 손실 방지)
    state.update(boardErr=None, cellErr=RuntimeError("5xx"))
    assert edgarPanel._seedTickerPanel("AAR", token="x") is None


def test_universe_ticker_by_cik_multiclass(monkeypatch) -> None:
    """_universeTickerByCik — 한 CIK 의 복수 ticker(주식클래스)를 list 로 모음."""
    import polars as pl

    from dartlab.pipeline.stages import edgarPanel

    uni = pl.DataFrame({"cik": [1652044, 1652044, 320193], "ticker": ["GOOGL", "GOOG", "AAPL"]})
    monkeypatch.setattr(
        "dartlab.core.dataLoader.loadEdgarListedUniverse", lambda *, forceUpdate=False: uni, raising=False
    )
    m = edgarPanel._universeTickerByCik()
    assert sorted(m["0001652044"]) == ["GOOG", "GOOGL"]  # 두 클래스 모두 보존
    assert m["0000320193"] == ["AAPL"]
