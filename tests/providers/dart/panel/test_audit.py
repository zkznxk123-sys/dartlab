"""panel TOC 검열기 mirror — auditToc 불변식 4종 탐지 + 수렴 적용 후 잔존만 보고 (합성 parquet, 데이터 0).

``audit.auditToc`` 가 read 와 동일 수렴 Expr 를 적용한 *뒤* 잔존 위반만 잡는지 — 수렴이 접는 era 변형은
위반 아님(미보고), 의도적 분리(다른 항목 슬롯충돌)·오배정은 보고.
"""

from __future__ import annotations

from pathlib import Path

import polars as pl
import pytest

pytestmark = pytest.mark.unit


def _row(corp: str, chapter: str, sectionPath: str, sectionLeaf: str, disclosureKey: str | None = None) -> dict:
    return {
        "corp": corp,
        "chapter": chapter,
        "sectionPath": sectionPath,
        "sectionLeaf": sectionLeaf,
        "disclosureKey": disclosureKey,
    }


@pytest.fixture
def auditEnv(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> str:
    """합성 panel parquet 1종목 — 위반 3종 + 수렴으로 접혀야 할 변형 1종."""
    import dartlab.config as cfg

    monkeypatch.setattr(cfg, "dataDir", str(tmp_path))
    pdir = tmp_path / "dart" / "panel"
    pdir.mkdir(parents=True)
    chI = "I. 회사의 개요"
    chV = "V. 회계감사인의 감사의견 등"
    rows = [
        # duplicateNumber — 같은 번호 다른 항목(의도적 분리) = 보고 대상
        _row("TEST01", chI, chI, "5. 의결권 현황"),
        _row("TEST01", chI, chI, "5. 정관에 관한 사항"),
        # 수렴으로 접혀야 할 era 변형 — alias 가 접으므로 위반 미보고
        _row("TEST01", chV, chV, "1. 외부감사에 관한 사항"),
        _row("TEST01", chV, chV, "1. 감사대상업무"),
        # coreVariant — 비번호 표면변형(수렴 미등재 코어)
        _row("TEST01", chI, chI, "별난 섹션"),
        _row("TEST01", chI, chI, "별난  섹션"),
    ]
    pl.DataFrame(rows).write_parquet(pdir / "TEST01.parquet")
    return "TEST01"


def test_audit_toc_detects_residual_violations(auditEnv: str) -> None:
    """수렴 후 잔존 위반만 보고 — alias 가 접는 변형(감사대상업무)은 미보고, 다른항목 슬롯충돌은 보고."""
    from dartlab.providers.dart.panel.audit import auditToc

    f = auditToc(codes=[auditEnv])
    kinds = set(f["kind"].to_list()) if f.height else set()
    assert "duplicateNumber" in kinds  # 의결권현황 vs 정관 (의도적 분리 — 운영자 판독용 보고)
    assert "coreVariant" in kinds  # 별난 섹션 공백변형
    dup = f.filter(pl.col("kind") == "duplicateNumber")["detail"].to_list()
    assert not any("감사대상업무" in d for d in dup)  # alias 수렴분은 위반 아님


def test_audit_toc_empty_when_clean(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """위반 0 종목 → 빈 findings (schema 보존)."""
    import dartlab.config as cfg
    from dartlab.providers.dart.panel.audit import auditToc

    monkeypatch.setattr(cfg, "dataDir", str(tmp_path))
    pdir = tmp_path / "dart" / "panel"
    pdir.mkdir(parents=True)
    chII = "II. 사업의 내용"
    pl.DataFrame(
        [_row("TEST02", chII, chII, "1. 사업의 개요"), _row("TEST02", chII, chII, "2. 주요 제품 및 서비스")]
    ).write_parquet(pdir / "TEST02.parquet")
    f = auditToc(codes=["TEST02"])
    assert f.height == 0
    assert f.columns == ["corp", "chapter", "kind", "detail"]
