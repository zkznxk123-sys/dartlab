"""entityGraphCatalog builder tests."""

from __future__ import annotations

import json

import polars as pl
import pytest

pytestmark = pytest.mark.unit


class _FakeCompany:
    def __init__(self, code: str) -> None:
        self.code = code

    def industry(self) -> dict:
        return {
            "chainName": "semiconductor",
            "stageName": "후공정",
            "confidence": 0.91,
            "peers": [
                {"stockCode": "172670", "corpName": "에이엘티"},
                {"stockCode": "077360", "corpName": "덕산하이메탈"},
            ],
        }


def _fakeCredit(code: str) -> dict:
    grade = {"042700": "dCR-AA", "172670": "dCR-BB", "077360": "dCR-BBB-"}[code]
    return {
        "grade": grade,
        "axes": [
            {"name": "사업안정성", "score": 4.0},
            {"name": "현금흐름", "score": 7.0},
        ],
    }


def test_build_entity_graph_catalog_from_injected_engines() -> None:
    from dartlab.providers.dart.search.entityGraphCatalog import buildEntityGraphCatalog

    listing = pl.DataFrame(
        [
            {"종목코드": "042700", "회사명": "한미반도체"},
            {"종목코드": "172670", "회사명": "에이엘티"},
            {"종목코드": "077360", "회사명": "덕산하이메탈"},
        ]
    )

    catalog = buildEntityGraphCatalog(
        ["042700"],
        neighborsPerSeed=2,
        companyFactory=_FakeCompany,
        creditFn=_fakeCredit,
        listing=listing,
        generatedAt="2026-06-16T00:00:00+00:00",
    )

    assert catalog.height == 3
    seed = catalog.filter(pl.col("stockCode") == "042700").row(0, named=True)
    assert seed["corpName"] == "한미반도체"
    assert seed["grade"] == "dCR-AA"
    assert seed["weakAxis"] == "현금흐름"
    assert seed["stageName"] == "후공정"
    assert seed["dataAsOf"] == "20260616"
    neighbors = json.loads(seed["neighborsJson"])
    assert [row["stockCode"] for row in neighbors] == ["172670", "077360"]


def test_seed_codes_from_search_catalog_picks_top_stock_codes(tmp_path) -> None:
    from dartlab.providers.dart.search.entityGraphCatalog import seedCodesFromSearchCatalog

    path = tmp_path / "catalog.parquet"
    pl.DataFrame(
        [
            {"stockCode": "042700"},
            {"stockCode": "042700"},
            {"stockCode": "005930"},
            {"stockCode": "bad"},
        ]
    ).write_parquet(path)

    assert seedCodesFromSearchCatalog(path, maxSeeds=2) == ["042700", "005930"]


def test_prepare_entity_graph_catalog_artifact_copies_explicit_catalog(tmp_path, monkeypatch) -> None:
    from dartlab.providers.dart.search.entityGraphCatalog import prepareEntityGraphCatalogArtifact

    source = tmp_path / "source.parquet"
    pl.DataFrame([{"stockCode": "042700", "corpName": "한미반도체"}]).write_parquet(source)
    out = tmp_path / "out"
    monkeypatch.setenv("DARTLAB_SEARCH_ENTITY_GRAPH_CATALOG", str(source))

    summary = prepareEntityGraphCatalogArtifact(out)

    assert summary["mode"] == "copied"
    assert (out / "entityGraphCatalog.parquet").exists()
