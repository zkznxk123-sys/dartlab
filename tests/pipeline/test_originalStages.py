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


def test_dartzip_seed_isolates_count_from_stale_zips(monkeypatch, tmp_path) -> None:
    """무결성 카운트는 *격리 임시 dir* 기준 — dest 의 이전 run 잔재 zip 이 부분추출을 가리지 못한다.

    회귀 가드(finding #6): 옛 코드는 dest 에 바로 풀어 ``len(dest.glob)`` 로 검증해 잔재가 카운트를
    부풀렸다. 완전 tar 는 잔재 보존 + 신규 병합으로 통과하되, 카운트는 새로 푼 셋만 센다.
    """
    import huggingface_hub

    import dartlab.config as cfg
    from dartlab.pipeline import hfUpload
    from dartlab.pipeline.stages import dartZip

    monkeypatch.setattr(cfg, "dataDir", str(tmp_path))
    monkeypatch.setattr(hfUpload, "_resolveHfToken", lambda token=None: "x")
    monkeypatch.setattr("dartlab.core.hfRetry.retryHfCall", lambda fn, *a, **k: fn(*a, **k))

    dest = tmp_path / "original" / "dart" / "docs" / "AAA"
    dest.mkdir(parents=True, exist_ok=True)
    (dest / "stale1.zip").write_bytes(b"PK\x03\x04old1")  # 이전 run 잔재
    (dest / "stale2.zip").write_bytes(b"PK\x03\x04old2")

    tarDir = tmp_path / "_hf"
    _makeTar(tarDir / "AAA.tar", ["r1.zip", "r2.zip"])  # 완전 tar(2 멤버)
    monkeypatch.setattr(huggingface_hub, "hf_hub_download", lambda **k: str(tarDir / "AAA.tar"))

    n, safe = dartZip._seedChangedFromHf(["AAA"], token="x")
    assert safe == {"AAA"} and n == 1
    names = sorted(p.name for p in dest.glob("*.zip"))
    assert names == ["r1.zip", "r2.zip", "stale1.zip", "stale2.zip"]  # 잔재 보존 + 신규 병합


def test_runincremental_partial_fetch_skips_build_without_raw(monkeypatch, tmp_path) -> None:
    """신규 종목 text fetch 가 부분 실패하면 build/changed 제외 + raw 미생성(다음 run 재시도)."""
    import importlib

    import dartlab.config as cfg
    from dartlab.pipeline.stages import edgarPanel
    from dartlab.pipeline.types import StageResult

    # dartlab.gather.original 은 GatherEntry 속성으로 shadow 되어 monkeypatch 의 dotted-path 해소가
    # 깨진다 → 실제 모듈 객체를 importlib 로 얻어 setattr(_runIncremental 의 from-import 가 읽는 곳).
    edgarCollect = importlib.import_module("dartlab.gather.original.edgar.collect")
    edgarBuild = importlib.import_module("dartlab.providers.edgar.panel.build")
    edgarIdentity = importlib.import_module("dartlab.gather.edgar.identity")

    monkeypatch.setattr(cfg, "dataDir", str(tmp_path))
    monkeypatch.setattr(edgarPanel, "_universeTickerByCik", lambda: {"0000099999": ["NEW"]})
    monkeypatch.setattr(edgarPanel, "_seedTickerPanel", lambda ticker, *, token: False)  # 신규(404)
    monkeypatch.setattr(
        edgarCollect,
        "listRecentFilings",
        lambda dates, *, forms: [{"cik": "0000099999", "accession_no": "X-1", "txt_url": "u"}],
    )
    monkeypatch.setattr(edgarIdentity, "loadTickers", lambda refresh=False: None, raising=False)

    listed = {"n": 0}
    fetched = {"n": 0}
    built = {"n": 0}

    def fakeListAll(ticker, *, forms, sinceYear):
        listed["n"] += 1
        return [
            {"cik": "0000099999", "accession_no": "X-1", "txt_url": "u1"},
            {"cik": "0000099999", "accession_no": "X-2", "txt_url": "u2"},
        ]

    def fakeFetch(rows):
        fetched["n"] += 1
        return {"0000099999": [{"cik": "0000099999", "accession_no": "X-1", "text": "x"}]}  # 1/2 부분 실패

    def fakeBuild(ticker, filings, *, overwrite, verbose):
        built["n"] += 1
        return {"rows": 100}

    edgarSubmissions = importlib.import_module("dartlab.gather.original.edgar.submissions")
    monkeypatch.setattr(edgarSubmissions, "listAllFilings", fakeListAll)
    monkeypatch.setattr(edgarCollect, "fetchFilingTexts", fakeFetch)
    monkeypatch.setattr(edgarBuild, "buildEdgarPanel", fakeBuild)

    out = edgarPanel._runIncremental(StageResult(category="edgarPanel"), lookback=3, upload=False, token="x")

    assert listed["n"] == 1 and fetched["n"] == 1
    assert built["n"] == 0  # 부분 fetch → build 제외(부분 panel 박제 방지)
    assert out.rows == 0  # changed 0
    assert not (tmp_path / "original" / "edgar" / "docs").exists()  # raw 저장 없음


def test_seed_ticker_panel_404_vs_transient(monkeypatch, tmp_path) -> None:
    """_seedTickerPanel — panel 404=False, panel 일시실패=None."""
    import huggingface_hub

    import dartlab.config as cfg
    from dartlab.pipeline import hfUpload
    from dartlab.pipeline.stages import edgarPanel

    monkeypatch.setattr(cfg, "dataDir", str(tmp_path))
    monkeypatch.setattr(hfUpload, "_resolveHfToken", lambda token=None: "x")
    monkeypatch.setattr("dartlab.core.hfRetry.retryHfCall", lambda fn, *a, **k: fn(*a, **k))

    from huggingface_hub.utils import EntryNotFoundError

    state = {"boardErr": None}

    def fake(*, repo_id, repo_type, filename, token, local_dir):
        if state["boardErr"]:
            raise state["boardErr"]
        return filename

    monkeypatch.setattr(huggingface_hub, "hf_hub_download", fake)

    # board 404 → False(신규)
    state.update(boardErr=EntryNotFoundError("404"))
    assert edgarPanel._seedTickerPanel("AAR", token="x") is False
    # board 일시실패 → None
    state.update(boardErr=RuntimeError("5xx"))
    assert edgarPanel._seedTickerPanel("AAR", token="x") is None
    # board ok → True
    state.update(boardErr=None)
    assert edgarPanel._seedTickerPanel("AAR", token="x") is True


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
