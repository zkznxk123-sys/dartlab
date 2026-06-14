"""valuationPublishLint guard 테스트 — 발간 표면 한정 투자권유 금지어 차단.

핵심 회귀가드: lint 가 *발간 표면*(reportType: simulation 마크다운)만 스캔하고
src `.py`(leaf 의 정당한 underpriced/strong_buy 사용)는 영원히 안 잡는다(CI red 0).
"""

from __future__ import annotations

import pytest

from tests.audit.valuationPublishLint import (
    SURFACE_ROOTS,
    _isSimulationReport,
    _scanSurface,
)

pytestmark = pytest.mark.unit


def _writeMd(path, frontmatter: str, body: str) -> None:
    path.write_text(f"---\n{frontmatter}\n---\n\n{body}\n", encoding="utf-8")


def test_lint_greenNow() -> None:
    """현재 발간 표면에 simulation 보고서 0건 → 위반 0 (green no-op)."""
    for root in SURFACE_ROOTS:
        assert _scanSurface(root) == []


def test_lint_catchesBannedInSimReport(tmp_path) -> None:
    """reportType: simulation + 금지어 → 위반 ≥ 1 (활성 발화)."""
    md = tmp_path / "92-sim.md"
    _writeMd(md, "reportType: simulation", "적정 범위 대비 목표주가 95000원, 매수의견 제시.")
    violations = _scanSurface(tmp_path)
    assert len(violations) >= 1
    hits = {v[2] for v in violations}
    assert any("목표주가" in h or "매수의견" in h for h in hits)


def test_lint_catchesPersonalization(tmp_path) -> None:
    """reportType: simulation + 개인화 추천 어휘 → 위반 ≥ 1 (Advisers Act 가드)."""
    md = tmp_path / "92-personal.md"
    _writeMd(md, "reportType: simulation", "귀하의 포트폴리오 상황에서는 비중 확대를 권합니다.")
    violations = _scanSurface(tmp_path)
    assert len(violations) >= 1
    assert any("귀하의 포트폴리오" in v[2] or "회원님" in v[2] for v in violations)


def test_lint_ignoresNonSimReport(tmp_path) -> None:
    """reportType 없는(또는 company) 보고서는 금지어 있어도 미스캔 (발간표면 한정 증명)."""
    md = tmp_path / "01-company.md"
    _writeMd(md, "reportType: company", "This stock looks underpriced and is a strong buy.")
    assert _scanSurface(tmp_path) == []


def test_lint_ignoresLeafSource(tmp_path) -> None:
    """src `.py`(leaf)는 reportType 유사 내용이 있어도 항상 False — CI red 0 핵심."""
    py = tmp_path / "priceImplied.py"
    py.write_text('reportType = "simulation"\nsignal = "underpriced"\n', encoding="utf-8")
    assert _isSimulationReport(py) is False
    assert _scanSurface(tmp_path) == []


def test_lint_collectsCleanSimReport(tmp_path) -> None:
    """reportType: simulation + 깨끗 본문 → 표면으로 수집되되 위반 0 (N파일-위반0 green)."""
    md = tmp_path / "92-clean.md"
    _writeMd(md, "reportType: simulation", "현재가는 base case 대비 더 높은 마진 지속을 요구한다.")
    assert _isSimulationReport(md) is True  # 표면으로 수집됨
    assert _scanSurface(tmp_path) == []  # 그러나 위반 0
