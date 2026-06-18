from __future__ import annotations

from pathlib import Path

import polars as pl


class FakeGather:
    def macro(self, seriesId: str) -> pl.DataFrame:
        base = float(len(seriesId))
        return pl.DataFrame(
            {
                "date": ["2026-04-30", "2026-05-31"],
                "value": [base, base + 1.5],
            }
        )


def testAnalyzeTransmissionReturnsSectorEdgesWithLineage(monkeypatch) -> None:
    from dartlab.macro.transmission import transmission

    monkeypatch.setattr(transmission, "getGather", lambda asOf=None: FakeGather())
    result = transmission.analyzeTransmission(market="KR", sectorKey="semiconductor")

    assert result["market"] == "KR"
    assert result["drivers"]
    assert result["edges"]
    assert result["asOf"] == "2026-05-31"
    assert {edge["evidenceLabel"] for edge in result["edges"]} <= {"OBS", "PRIOR", "TPL"}
    assert {"fx-export-revenue", "export-demand-revenue", "rate-debt-interest"} <= {
        edge["id"] for edge in result["edges"]
    }
    for driver in result["drivers"]:
        lineage = driver["sourceLineage"]
        assert lineage["sourceSeriesId"] == driver["sourceSeriesId"]
        assert lineage["date"] == "2026-05-31"
        assert lineage["value"] is not None
        assert lineage["artifactPath"].startswith("macro/")


def testMacroTransmissionPublicDispatch(monkeypatch) -> None:
    import dartlab
    from dartlab.macro.transmission import transmission

    monkeypatch.setattr(transmission, "getGather", lambda asOf=None: FakeGather())
    result = dartlab.macro("전파", market="KR", sectorKey="bank")

    assert result["market"] == "KR"
    assert any(edge["id"] == "rate-bank-margin" for edge in result["edges"])
    assert result["sourceRefs"][0] == "dartlab://macro/transmission"


def testTransmissionDoesNotImportCompanyOrAnalysis() -> None:
    root = Path(__file__).resolve().parents[2]
    source = (root / "src" / "dartlab" / "macro" / "transmission" / "transmission.py").read_text(encoding="utf-8")

    assert "dartlab.analysis" not in source
    assert "dartlab.company" not in source
    assert "Company(" not in source
