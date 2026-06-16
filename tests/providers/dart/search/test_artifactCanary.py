"""providers/dart/search/artifactCanary.py tests."""

from __future__ import annotations

import polars as pl


def test_build_source_canary_pack_from_meta_samples_sources() -> None:
    from dartlab.providers.dart.search.artifactCanary import buildSourceCanaryPackFromMeta

    pack = buildSourceCanaryPackFromMeta(
        pl.DataFrame(
            [
                {
                    "source": "allFilings",
                    "sourceRef": "dart:allFilings:1#section=0",
                    "rcept_no": "1",
                    "text": "유상증자 자금조달 계획",
                    "sourceDataAsOf": "20260615",
                },
                {
                    "source": "news",
                    "sourceRef": "news:fx",
                    "rcept_no": "news:fx",
                    "text": "환율 리스크 관련 기사",
                    "sourceDataAsOf": "20260615",
                },
                {
                    "source": "panel",
                    "sourceRef": "dart:panel:1#section=0",
                    "rcept_no": "1",
                    "text": "사업보고서 공통 문구",
                    "sourceDataAsOf": "20260615",
                },
                {
                    "source": "edgar-panel",
                    "sourceRef": "edgar:panel:1#section=0",
                    "rcept_no": "1",
                    "text": "UNITED STATES SECURITIES AND EXCHANGE COMMISSION",
                    "sourceDataAsOf": "20260615",
                },
            ]
        )
    )

    assert [row["target"] for row in pack] == ["filing", "edgar", "news", "filing", "noAnswer"]
    assert pack[0]["expectedSource"] == "allFilings"
    assert pack[0]["query"].startswith("공시 원문")
    assert pack[0]["requireAnswerable"] is True
    assert "expectedSourceRef" in pack[0]
    assert pack[1]["expectedSource"] == "edgar-panel"
    assert "expectedSourceRef" not in pack[1]
    assert pack[2]["query"] == "뉴스 기사"
    assert "expectedSourceRef" not in pack[2]
    assert pack[3]["expectedSource"] == "panel"
    assert "expectedSourceRef" not in pack[3]
    assert pack[-1]["expectedAnswerable"] is False


def test_build_source_canary_pack_empty_meta_keeps_no_answer() -> None:
    from dartlab.providers.dart.search.artifactCanary import buildSourceCanaryPackFromMeta

    assert buildSourceCanaryPackFromMeta(pl.DataFrame()) == [
        {
            "query": "zzqwvxnotlistedalpha999",
            "target": "noAnswer",
            "expectedAnswerable": False,
            "topK": 10,
        }
    ]
