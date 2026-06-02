"""panel build noteTaxonomy 생성기 — corpus 학습 (scope,제목)→dominant NT_ 코드 + 모듈 직렬화.

``buildNoteTaxonomy`` 가 합성 parquet 코퍼스에서 dominant 제목만 채택(모호 제외)하고 scope 를 분리하는지,
``renderModule`` 직렬화가 round-trip 하는지 검증. 합성 입력(실데이터 0).
"""

from __future__ import annotations

import polars as pl
import pytest

from dartlab.providers.dart.panel.build.noteTaxonomy import (
    buildNoteTaxonomy,
    renderModule,
)

pytestmark = pytest.mark.unit


def _writeCorpus(base, rows: list[tuple[str, str, str]], *, n: int = 1) -> None:
    """합성 panel 코퍼스 — rows=(disclosureKey, xbrlClass, blockLeaf), n 회사에 동일 분포 복제."""
    for i in range(n):
        d = base / f"{i:06d}"
        d.mkdir(parents=True, exist_ok=True)
        pl.DataFrame(
            {
                "disclosureKey": [r[0] for r in rows],
                "xbrlClass": [r[1] for r in rows],
                "blockLeaf": [r[2] for r in rows],
            },
            schema={"disclosureKey": pl.Utf8, "xbrlClass": pl.Utf8, "blockLeaf": pl.Utf8},
        ).write_parquet(str(d / "2024Q4.parquet"))


def test_build_dominant_accepted(tmp_path) -> None:
    """단일 지배 코드(비율 ≥ dominanceRatio) 제목은 채택."""
    # 재고자산 → NT_D826380 만 (지배 100%)
    _writeCorpus(tmp_path, [("NT_D826380", "NT_C_D826380", "재고자산")], n=5)
    tax = buildNoteTaxonomy(panelBaseDir=tmp_path, minFreq=3, dominanceRatio=0.8)
    assert tax.get("consolidated|재고자산") == "NT_D826380"


def test_build_ambiguous_excluded(tmp_path) -> None:
    """한 제목이 두 코드로 50/50 갈리면(무지배) 제외 — false-merge 회피."""
    rows = [("NT_D800600", "NT_C_D800600", "중요한 회계정책")] * 5 + [
        ("NT_D811000", "NT_C_D811000", "중요한 회계정책")
    ] * 5
    _writeCorpus(tmp_path, rows, n=2)
    tax = buildNoteTaxonomy(panelBaseDir=tmp_path, minFreq=3, dominanceRatio=0.8)
    assert "consolidated|중요한회계정책" not in tax  # 0.5 < 0.8 → 제외


def test_build_scope_separation(tmp_path) -> None:
    """연결/별도(xbrlClass _C/_S)는 같은 제목이라도 다른 키·코드."""
    _writeCorpus(
        tmp_path, [("NT_D826380", "NT_C_D826380", "재고자산"), ("NT_D826385", "NT_S_D826385", "재고자산")], n=5
    )
    tax = buildNoteTaxonomy(panelBaseDir=tmp_path, minFreq=3, dominanceRatio=0.8)
    assert tax.get("consolidated|재고자산") == "NT_D826380"
    assert tax.get("standalone|재고자산") == "NT_D826385"


def test_build_minfreq_filters_noise(tmp_path) -> None:
    """총 빈도 < minFreq 제목은 노이즈 컷."""
    _writeCorpus(tmp_path, [("NT_D826380", "NT_C_D826380", "재고자산")], n=2)  # 총 2 < minFreq 3
    tax = buildNoteTaxonomy(panelBaseDir=tmp_path, minFreq=3, dominanceRatio=0.8)
    assert "consolidated|재고자산" not in tax


def test_build_excludes_non_standard_codes(tmp_path) -> None:
    """회사확장 NT_C_U*/DS* 는 표준코드 아님 → 학습 제외(NT_D\\d+ 만)."""
    _writeCorpus(tmp_path, [("NT_C_U800400", "NT_C_U800400", "금융상품범주")], n=5)
    tax = buildNoteTaxonomy(panelBaseDir=tmp_path, minFreq=3, dominanceRatio=0.8)
    assert tax == {}  # 표준 NT_D 코드 0 → 빈 뼈대


def test_render_module_round_trip(tmp_path) -> None:
    """renderModule → exec → NOTE_TAXONOMY dict 동일 (직렬화 무손실)."""
    tax = {"consolidated|재고자산": "NT_D826380", 'standalone|"따옴표"': "NT_D826385"}
    src = renderModule(tax)
    ns: dict = {}
    exec(compile(src, "noteTaxonomyData.py", "exec"), ns)  # noqa: S102 — 생성물 직렬화 검증
    assert ns["NOTE_TAXONOMY"] == tax
