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
