"""macro 흡수 stage — 구조 동등 + secret 격리 + 의존게이트.

흡수 검증 SSOT: in-library ``stages/macro.py`` (runMacroData/Cycle/Regime) + ``stages/
prebuild.py`` (runMacroJson) 가 옛 ``.github/scripts/{sync,prebuild}`` 스크립트와 *구조
동등* 산출을 만드는지 단언한다.

구조 동등 정의 = "타임스탬프 필드(``asOf``/``computedAt``) 제외 후 정규화 deep-equal +
parquet schema/정렬/dtype 동일" (byte 비교 아님 — 날짜 비결정·PRD §7.3 ground-truth
정정 2). observations 는 타임스탬프 컬럼이 없으나 live FRED API 라 value/row 는
run-to-run 미세 변동 가능 → schema/sort/dtype/정렬키 단언으로 한정.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

# observations 스키마 / manifest 컬럼 — buildMacroData._write 산출 계약(불변).
_OBS_SCHEMA = {"seriesId": "String", "date": "Date", "value": "Float64"}
_MANIFEST_COLS = {
    "source",
    "seriesId",
    "label",
    "group",
    "frequency",
    "unit",
    "description",
    "rowCount",
    "startDate",
    "latestDate",
    "providerUpdatedAt",
    "updatedAtUtc",
    "status",
    "error",
}

# cycle/regime JSON 키 계약 (live data/macro/{cycle,regime}/*.json 동형, §6.2).
_CYCLE_REQUIRED = {"market", "phase", "phaseLabel", "confidence", "signals", "sectorStrategy"}
_REGIME_REQUIRED = {"market", "forecast", "rates"}  # gar/regimeBand 는 US 전용
_MACRO_JSON_REQUIRED = {"version", "asOf", "kr", "us", "transmission", "sectorTailwind", "regime"}

# 동등 비교에서 제외하는 비결정 타임스탬프 필드(PRD §7.3·§12 성공기준 2).
_TIMESTAMP_FIELDS = {"asOf", "computedAt"}


# ──────────────────────────────────────────────────────────────────────────
# 구조 동등 — runMacroData (FRED, live HF bulk cache·no FRED key needed)
# ──────────────────────────────────────────────────────────────────────────


@pytest.fixture(scope="module")
def fredObs(tmp_path_factory, monkeypatch_session):
    """runMacroData(source='fred', upload=False) → observations.parquet (temp data dir)."""
    import polars as pl

    from dartlab.pipeline.stages.macro import runMacroData

    dataDir = tmp_path_factory.mktemp("macroData")
    monkeypatch_session.setenv("DARTLAB_DATA_DIR", str(dataDir))
    res = runMacroData(source="fred", upload=False)
    assert res.report.err == 0, f"runMacroData fred 실패: {res.report.failures}"
    obsPath = dataDir / "macro" / "fred" / "observations.parquet"
    manifestPath = dataDir / "macro" / "fred" / "manifest.parquet"
    assert obsPath.exists(), "observations.parquet 미작성"
    assert manifestPath.exists(), "manifest.parquet 미작성"
    return pl.read_parquet(obsPath), pl.read_parquet(manifestPath)


@pytest.fixture(scope="session")
def monkeypatch_session():
    from _pytest.monkeypatch import MonkeyPatch

    mp = MonkeyPatch()
    yield mp
    mp.undo()


@pytest.mark.network
@pytest.mark.slow
@pytest.mark.requires_data
def test_macro_data_fred_schema_equivalent(fredObs):
    """observations.parquet schema/dtype 가 buildMacroData._write 계약과 동일."""
    obs, _ = fredObs
    schema = {name: str(dtype) for name, dtype in obs.schema.items()}
    assert schema == _OBS_SCHEMA, f"observations schema drift: {schema}"
    assert obs.height > 0, "observations 0행 — FRED bulk 캐시/카탈로그 비정상"


@pytest.mark.network
@pytest.mark.slow
@pytest.mark.requires_data
def test_macro_data_fred_sorted(fredObs):
    """observations 가 (seriesId, date) 정렬 — _write sort 계약."""
    obs, _ = fredObs
    sortedObs = obs.sort(["seriesId", "date"])
    assert obs.equals(sortedObs), "observations 가 (seriesId, date) 정렬 아님 — _write 회귀"


@pytest.mark.network
@pytest.mark.slow
@pytest.mark.requires_data
def test_macro_data_fred_manifest(fredObs):
    """manifest 컬럼 집합이 buildMacroData 계약과 동일 + source=fred."""
    _, manifest = fredObs
    assert set(manifest.columns) == _MANIFEST_COLS, f"manifest 컬럼 drift: {set(manifest.columns)}"
    assert manifest.height > 0
    assert set(manifest.get_column("source").unique().to_list()) == {"fred"}


# ──────────────────────────────────────────────────────────────────────────
# 구조 동등 — runMacroCycle / runMacroRegime (HF bulk cache, live data 동형)
# ──────────────────────────────────────────────────────────────────────────


def _stripTimestamps(obj):
    """asOf/computedAt 재귀 제거 — 비결정 타임스탬프 동등 비교 제외."""
    if isinstance(obj, dict):
        return {k: _stripTimestamps(v) for k, v in obj.items() if k not in _TIMESTAMP_FIELDS}
    if isinstance(obj, list):
        return [_stripTimestamps(v) for v in obj]
    return obj


@pytest.mark.network
@pytest.mark.slow
@pytest.mark.requires_data
def test_macro_cycle_keys_equivalent(tmp_path, monkeypatch):
    """runMacroCycle 산출 JSON 키가 cycle 계약(§6.2)과 동일 (KR/US)."""
    from dartlab.pipeline.stages.macro import runMacroCycle

    monkeypatch.setenv("DARTLAB_DATA_DIR", str(tmp_path))
    res = runMacroCycle(upload=False)
    assert res.report.err == 0, f"runMacroCycle 실패: {res.report.failures}"
    for market in ("kr", "us"):
        path = tmp_path / "macro" / "cycle" / f"{market}.json"
        assert path.exists(), f"cycle {market}.json 미작성"
        data = json.loads(path.read_text(encoding="utf-8"))
        assert _CYCLE_REQUIRED <= set(data.keys()), f"cycle {market} 키 누락: {_CYCLE_REQUIRED - set(data.keys())}"
        assert data["market"] == market.upper()


@pytest.mark.network
@pytest.mark.slow
@pytest.mark.requires_data
def test_macro_regime_keys_equivalent(tmp_path, monkeypatch):
    """runMacroRegime 산출 JSON 키가 regime 계약(§6.2)과 동일 (US=forecast 4모델)."""
    from dartlab.pipeline.stages.macro import runMacroRegime

    monkeypatch.setenv("DARTLAB_DATA_DIR", str(tmp_path))
    res = runMacroRegime(upload=False)
    assert res.report.err == 0, f"runMacroRegime 실패: {res.report.failures}"
    for market in ("kr", "us"):
        path = tmp_path / "macro" / "regime" / f"{market}.json"
        assert path.exists(), f"regime {market}.json 미작성"
        data = json.loads(path.read_text(encoding="utf-8"))
        assert _REGIME_REQUIRED <= set(data.keys()), f"regime {market} 키 누락: {_REGIME_REQUIRED - set(data.keys())}"
        assert data["market"] == market.upper()
    # US 는 gar/regimeBand + forecast.models 4종까지 산출(분석 깊이 계약).
    usData = json.loads((tmp_path / "macro" / "regime" / "us.json").read_text(encoding="utf-8"))
    assert "gar" in usData and "regimeBand" in usData, "US regime: gar/regimeBand 누락"
    assert isinstance(usData["forecast"]["models"], dict)


# ──────────────────────────────────────────────────────────────────────────
# 구조 동등 — runMacroJson (offline, macro.json v20)
# ──────────────────────────────────────────────────────────────────────────


@pytest.mark.requires_data
def test_macro_json_v20_structure():
    """runMacroJson 산출 macro.json 이 v20 스키마(키 집합)와 동일.

    OUT(landing/static/dashboards/macro.json)을 백업→실행→키 검증→복원. offline 가드는
    cycle/regime 로컬 cache(data/macro) hit 으로 충족(외부 API 0).
    """
    from dartlab.pipeline.stages.prebuild import _MACRO_JSON_OUT, runMacroJson

    out = Path(_MACRO_JSON_OUT)
    backup = out.read_bytes() if out.exists() else None
    try:
        res = runMacroJson(upload=False)
        assert res.report.err == 0, f"runMacroJson 실패: {res.report.failures}"
        data = json.loads(out.read_text(encoding="utf-8"))
        assert set(data.keys()) == _MACRO_JSON_REQUIRED, f"macro.json 키 drift: {set(data.keys())}"
        assert data["version"] == "v20"
        assert set(data["regime"].keys()) == {"kr", "us"}
        # asOf 는 비결정(date.today) — 키 존재만 단언, 값 비교 제외.
        assert "asOf" in data
    finally:
        if backup is not None:
            out.write_bytes(backup)


# ──────────────────────────────────────────────────────────────────────────
# secret 격리
# ──────────────────────────────────────────────────────────────────────────


@pytest.mark.unit
def test_macro_data_no_push_when_upload_false(monkeypatch, tmp_path):
    """upload=False → uploadCategoryToHf 미호출(push 0·crash 0)."""
    import dartlab.pipeline.stages.macro as macroMod

    calls: list = []
    monkeypatch.setattr(macroMod, "uploadCategoryToHf", lambda *a, **k: calls.append((a, k)))
    monkeypatch.setattr(macroMod, "_buildFred", lambda outDir: outDir.mkdir(parents=True, exist_ok=True))
    monkeypatch.setenv("DARTLAB_DATA_DIR", str(tmp_path))
    res = macroMod.runMacroData(source="fred", upload=False, token=None)
    assert res.report.ok == 1
    assert calls == [], "upload=False 인데 push 발생"


@pytest.mark.unit
def test_macro_data_push_failure_isolated(monkeypatch, tmp_path):
    """upload=True + 토큰 부재 → report.fail(crash 아님). secret 미노출."""
    import dartlab.pipeline.stages.macro as macroMod

    def _raiseNoToken(*a, **k):
        raise ValueError("HF_TOKEN 필요 — 인자/env/.env 어디에도 없음")

    monkeypatch.setattr(macroMod, "uploadCategoryToHf", _raiseNoToken)
    monkeypatch.setattr(macroMod, "_buildFred", lambda outDir: outDir.mkdir(parents=True, exist_ok=True))
    monkeypatch.setenv("DARTLAB_DATA_DIR", str(tmp_path))
    res = macroMod.runMacroData(source="fred", upload=True, token=None)
    assert res.report.ok == 1  # 빌드는 성공
    assert res.report.fail == 1, "push 실패가 격리(report.fail)되지 않음"


@pytest.mark.unit
def test_macro_data_push_uses_full_folder(monkeypatch, tmp_path):
    """upload=True → uploadCategoryToHf(cat, fullUpload=True) — macro 는 changed 매니페스트 없음.

    macro 는 changed_macroFred.txt 를 만들지 않으므로 full-folder 업로드여야 스크립트
    deploy(upload_folder) 와 의미 동등(증분 부분 업로드 silent drift 차단·PRD §7.3·§8.2-5).
    """
    import dartlab.pipeline.stages.macro as macroMod

    seen: list = []
    monkeypatch.setattr(macroMod, "uploadCategoryToHf", lambda cat, **k: seen.append((cat, k)))
    monkeypatch.setattr(macroMod, "_buildFred", lambda outDir: outDir.mkdir(parents=True, exist_ok=True))
    monkeypatch.setenv("DARTLAB_DATA_DIR", str(tmp_path))
    macroMod.runMacroData(source="fred", upload=True, token="tok")
    assert seen, "upload=True 인데 push 미발생"
    cat, kwargs = seen[0]
    assert cat == "macroFred"
    assert kwargs.get("fullUpload") is True, "macro push 가 full-folder(fullUpload=True) 아님 — 증분 drift 위험"
    # changed 매니페스트가 생성되지 않았는지 단언.
    assert not (tmp_path / "macro" / "fred" / "changed_macroFred.txt").exists()


# ──────────────────────────────────────────────────────────────────────────
# 의존게이트 — data 실패 시 cycle/regime skip + report.err
# ──────────────────────────────────────────────────────────────────────────


@pytest.mark.unit
def test_macro_gate_data_fail_skips_cycle_regime(monkeypatch):
    """runMacroData 실패 → cycle/regime 미실행 + macro report.err."""
    import dartlab.pipeline.stages.macro as macroMod
    from dartlab.pipeline.types import StageResult

    def _failData(**k):
        r = StageResult(category="macroData")
        r.report.err = 1
        return r

    cycleCalls: list = []
    regimeCalls: list = []
    monkeypatch.setattr(macroMod, "runMacroData", _failData)
    monkeypatch.setattr(macroMod, "runMacroCycle", lambda **k: cycleCalls.append(k) or StageResult("macroCycle"))
    monkeypatch.setattr(macroMod, "runMacroRegime", lambda **k: regimeCalls.append(k) or StageResult("macroRegime"))
    res = macroMod.runMacro(upload=False)
    assert cycleCalls == [], "data 실패인데 cycle 실행됨 (게이트 회귀)"
    assert regimeCalls == [], "data 실패인데 regime 실행됨 (게이트 회귀)"
    assert res.report.err == 1
    assert "data:1" in res.report.failures[0]


@pytest.mark.unit
def test_macro_gate_cycle_independent_of_regime(monkeypatch):
    """data 성공 시 cycle 실패가 regime 빌드를 막지 않음(상호 독립)."""
    import dartlab.pipeline.stages.macro as macroMod
    from dartlab.pipeline.types import StageResult

    def _okData(**k):
        r = StageResult(category="macroData")
        r.report.ok = 1
        return r

    def _failCycle(**k):
        r = StageResult(category="macroCycle")
        r.report.err = 1
        return r

    regimeCalls: list = []

    def _okRegime(**k):
        regimeCalls.append(k)
        r = StageResult(category="macroRegime")
        r.report.ok = 1
        return r

    monkeypatch.setattr(macroMod, "runMacroData", _okData)
    monkeypatch.setattr(macroMod, "runMacroCycle", _failCycle)
    monkeypatch.setattr(macroMod, "runMacroRegime", _okRegime)
    res = macroMod.runMacro(upload=False)
    assert regimeCalls, "cycle 실패가 regime 실행을 막음 (독립성 회귀)"
    assert res.report.err == 1  # cycle 실패는 macro 전체 err
    assert "cycle:1/regime:0" in res.report.failures[0]


@pytest.mark.unit
def test_macro_all_ok(monkeypatch):
    """data/cycle/regime 전부 성공 → macro report.ok."""
    import dartlab.pipeline.stages.macro as macroMod
    from dartlab.pipeline.types import StageResult

    def _ok(cat):
        def _fn(**k):
            r = StageResult(category=cat)
            r.report.ok = 1
            return r

        return _fn

    monkeypatch.setattr(macroMod, "runMacroData", _ok("macroData"))
    monkeypatch.setattr(macroMod, "runMacroCycle", _ok("macroCycle"))
    monkeypatch.setattr(macroMod, "runMacroRegime", _ok("macroRegime"))
    res = macroMod.runMacro(upload=False)
    assert res.report.ok == 1 and res.report.err == 0


# ──────────────────────────────────────────────────────────────────────────
# registry 등록
# ──────────────────────────────────────────────────────────────────────────


@pytest.mark.unit
def test_macro_json_registered():
    """buildRegistry 에 macroJson 등록 + offline + run 바인딩."""
    from dartlab.pipeline.registry import buildRegistry
    from dartlab.pipeline.stages.prebuild import runMacroJson

    reg = buildRegistry()
    assert "macroJson" in reg
    assert reg["macroJson"].run is runMacroJson
    assert reg["macroJson"].online is False, "macroJson 은 offline stage 여야 함"
    # macro stage 는 그대로 유지(uploadCategories).
    assert reg["macro"].uploadCategories == ("macroFred", "macroEcos", "macroCustoms")
