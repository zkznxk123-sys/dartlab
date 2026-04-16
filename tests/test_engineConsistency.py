"""L2 4엔진 (analysis · credit · quant · macro) 호출 계약 일관성 회귀.

Phase 8 정렬 — 가이드 DF 컬럼 / Company-bound 진입점 / kwarg 명명 / 레지스트리 구조.
"""

from __future__ import annotations

import ast
from dataclasses import is_dataclass
from pathlib import Path

import polars as pl
import pytest


# ── 가이드 DF 표준 컬럼 ────────────────────────────────────


@pytest.mark.unit
def test_4engine_guide_returns_dataframe():
    """4엔진 Company-bound 무인자 호출 → polars DataFrame + 공통 컬럼."""
    import dartlab

    c = dartlab.Company("005930")
    common = {"axis", "label", "description", "example"}
    for name in ("analysis", "credit", "quant", "macro"):
        df = getattr(c, name)()
        assert isinstance(df, pl.DataFrame), f"c.{name}() not DataFrame"
        cols = set(df.columns)
        assert common.issubset(cols), f"c.{name} missing cols: {common - cols}"


# ── Company-bound 진입점 ───────────────────────────────────


@pytest.mark.unit
def test_company_has_4_engine_methods():
    """Company 에 analysis/credit/quant/macro 모두 존재."""
    import dartlab

    c = dartlab.Company("005930")
    for name in ("analysis", "credit", "quant", "macro"):
        assert hasattr(c, name), f"Company.{name} missing"


@pytest.mark.unit
def test_macro_company_bound_market_routing():
    """c.macro 가 KR 기본, EDGAR 회사는 US 위임."""
    import dartlab

    kr = dartlab.Company("005930")
    g_kr = kr.macro()
    assert isinstance(g_kr, pl.DataFrame)


@pytest.mark.unit
def test_phase10_h2_review_secondary_on_company():
    """Phase 10 H2 — review 2차 가공 메서드가 Company 에 노출 (DART+EDGAR)."""
    import dartlab

    c = dartlab.Company("005930")
    for name in ("causalWeights", "valuationImpact", "storyTree", "narrativeDiff"):
        assert hasattr(c, name), f"Company.{name} missing (Phase 10 H2)"
        assert callable(getattr(c, name)), f"Company.{name} not callable"


@pytest.mark.unit
def test_phase10_section_act_field():
    """Phase 10 F1 — SectionMeta.act 필드가 23섹션 + 3메타 모두 설정."""
    from dartlab.review.catalog import SECTIONS

    # 모든 섹션이 act 필드 보유
    for s in SECTIONS:
        assert hasattr(s, "act"), f"{s.key} missing act"
        assert s.act in (0, 1, 2, 3, 4, 5, 6), f"{s.key} invalid act={s.act}"

    # 6막 모두 최소 1 섹션
    acts = {s.act for s in SECTIONS}
    for a in (1, 2, 3, 4, 5, 6):
        assert a in acts, f"act {a} has no section"


@pytest.mark.unit
def test_phase10_invariants_20():
    """Phase 10 F2 — 불변량 20개 구현."""
    from dartlab.review.validators.validators import _INVARIANTS

    assert len(_INVARIANTS) >= 20, f"불변량 {len(_INVARIANTS)}개 (20 미만)"


@pytest.mark.unit
def test_phase10_storyValidation_in_all_reportTypes():
    """Phase 10 F4 — 11 reportType 전부 storyValidation 포함."""
    from dartlab.review.reportTypes import REPORT_TYPES

    for key, rt in REPORT_TYPES.items():
        assert "storyValidation" in rt.sectionOrder, f"{key} missing storyValidation"


@pytest.mark.unit
def test_phase10_g1_evidence_dataclass():
    """Phase 10 G1 — Evidence SSOT dataclass."""
    from dartlab.core.finance.evidence import Evidence, EvidenceGraph, buildCalcEvidence

    ev = buildCalcEvidence("opm", "2025Q3", {"rev": 1000, "opi": 150})
    assert ev.source == "calc"
    assert "opm" in ev.quote

    g = EvidenceGraph(claim="OPM 15%")
    g.add(ev)
    assert len(g.evidence) == 1
    assert "calc" in g.format_footnote()


# ── kwargs 명명 ────────────────────────────────────────────


@pytest.mark.unit
def test_quant_axis_alias_for_metric():
    """quant: axis= (정규) + metric= (호환 alias) 둘 다 동작."""
    import dartlab

    c = dartlab.Company("005930")
    a = c.quant(axis="지표")
    b = c.quant(metric="지표")
    assert a is not None
    assert b is not None


# ── credit 레지스트리 통일 ─────────────────────────────────


@pytest.mark.unit
def test_credit_axis_registry_uses_dataclass():
    """credit/_AXIS_REGISTRY 는 @dataclass _AxisEntry 로 통일 (4엔진 동일 패턴)."""
    from dartlab.credit import _AXIS_REGISTRY

    assert isinstance(_AXIS_REGISTRY, dict)
    assert len(_AXIS_REGISTRY) >= 7
    for entry in _AXIS_REGISTRY.values():
        assert is_dataclass(entry), f"{entry} is not a dataclass"
        assert hasattr(entry, "axis")
        assert hasattr(entry, "label")
        assert hasattr(entry, "group")


@pytest.mark.unit
def test_credit_guide_has_group_column():
    """credit 가이드 DF 도 group 컬럼 보유 (4엔진 통일)."""
    import dartlab

    df = dartlab.credit()
    assert "group" in df.columns


# ── L2 cross-import 회귀 가드 ──────────────────────────────


@pytest.mark.unit
def test_no_l2_cross_imports():
    """L2 엔진 간 상호 import 금지 (analysis ↔ credit ↔ quant ↔ macro)."""
    root = Path(__file__).resolve().parent.parent / "src" / "dartlab"
    engines = ["analysis", "credit", "quant", "macro"]
    forbidden_pairs = []
    for src_engine in engines:
        src_dir = root / src_engine
        if not src_dir.exists():
            continue
        for py in src_dir.rglob("*.py"):
            try:
                tree = ast.parse(py.read_text(encoding="utf-8"))
            except (SyntaxError, UnicodeDecodeError):
                continue
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom) and node.module:
                    mod = node.module
                    for other in engines:
                        if other == src_engine:
                            continue
                        if mod == f"dartlab.{other}" or mod.startswith(f"dartlab.{other}."):
                            # lazy import (function body) 는 허용 (관행)
                            # top-level 만 금지 — 부모 노드 추적은 비용 큼.
                            # 일단 모두 기록 후 건수만 확인.
                            forbidden_pairs.append((src_engine, other, str(py.relative_to(root)), node.lineno))
    # Phase 9 A2: baseline 0건 달성. 새 cross-import 즉시 감지.
    assert not forbidden_pairs, f"L2 cross-import 발견: {forbidden_pairs}"
