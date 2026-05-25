"""tests/audit/testCoverageGate.py 자체 회귀 — Track 6 (게이트 자체 검증).

본 SSOT — [tests/POLICY.md](../POLICY.md) §5 Track 5.

게이트 스크립트가 의도대로 동작하는지 검증한다:
- 공개 함수 (`def foo`) 만 잡고 private (`_foo`) 는 무시
- exempt 경로 (cli/main.py, server/api/*, viz/charts/*) 는 skip
- abstract method (ellipsis 본문) 는 skip
- tests/ 어디든 함수명 substring 있으면 PASS

본 PR 의 부드러운 도입 정책 — warning-only (default), `--fail-on-missing` 트리거
시에만 exit 1.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

_REPO = Path(__file__).resolve().parents[2]
_GATE_PATH = _REPO / "tests" / "audit" / "testCoverageGate.py"


def _loadGateModule():
    """testCoverageGate.py 를 module 로 동적 로드 — scripts/ 가 sys.path 에 없으므로."""
    spec = importlib.util.spec_from_file_location("testCoverageGate", _GATE_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["testCoverageGate"] = module
    spec.loader.exec_module(module)
    return module


def test_gate_module_loads() -> None:
    """게이트 스크립트가 import 에러 없이 로드."""
    gate = _loadGateModule()
    assert hasattr(gate, "runGate")
    assert hasattr(gate, "_extractPublicFunctions")
    assert hasattr(gate, "_isExempt")


def test_isExempt_cli_main(tmp_path: Path) -> None:
    """cli/main.py 같은 진입점은 exempt."""
    gate = _loadGateModule()
    assert gate._isExempt("cli/main.py") is True
    assert gate._isExempt("server/api/router.py") is True
    assert gate._isExempt("providers/dart/openapi/client.py") is True
    assert gate._isExempt("viz/charts/heatmap.py") is True
    assert gate._isExempt("mcp/server.py") is True


def test_isExempt_normal_path() -> None:
    """일반 경로는 exempt 아님."""
    gate = _loadGateModule()
    assert gate._isExempt("core/formatting.py") is False
    assert gate._isExempt("quant/factor/calc.py") is False
    assert gate._isExempt("analysis/financial/ratios.py") is False


def test_isExempt_init_py() -> None:
    """__init__.py 는 항상 exempt (재export)."""
    gate = _loadGateModule()
    assert gate._isExempt("core/__init__.py") is True
    assert gate._isExempt("quant/__init__.py") is True


def test_extractPublicFunctions_skips_private(tmp_path: Path) -> None:
    """`_foo` 같은 private 은 추출 안 함."""
    gate = _loadGateModule()
    f = tmp_path / "sample.py"
    f.write_text(
        """
def publicOne():
    return 1

def _privateOne():
    return 2

def publicTwo():
    return 3
""",
        encoding="utf-8",
    )
    funcs = gate._extractPublicFunctions(f)
    names = [n for n, _ in funcs]
    assert "publicOne" in names
    assert "publicTwo" in names
    assert "_privateOne" not in names


def test_extractPublicFunctions_skips_abstract(tmp_path: Path) -> None:
    """ellipsis 본문 (Protocol/abstract) 은 skip."""
    gate = _loadGateModule()
    f = tmp_path / "sample.py"
    f.write_text(
        """
from typing import Protocol

class MyProto(Protocol):
    def doSomething(self) -> int: ...

def realFunc():
    return 1

def passOnly():
    pass
""",
        encoding="utf-8",
    )
    funcs = gate._extractPublicFunctions(f)
    names = [n for n, _ in funcs]
    assert "realFunc" in names
    assert "doSomething" not in names
    assert "passOnly" not in names


def test_extractPublicFunctions_skips_abstractmethod_decorator(tmp_path: Path) -> None:
    """@abstractmethod 데코레이터는 skip."""
    gate = _loadGateModule()
    f = tmp_path / "sample.py"
    f.write_text(
        """
from abc import abstractmethod

class Base:
    @abstractmethod
    def mustImplement(self):
        return 1

def normalFunc():
    return 2
""",
        encoding="utf-8",
    )
    funcs = gate._extractPublicFunctions(f)
    names = [n for n, _ in funcs]
    assert "normalFunc" in names
    assert "mustImplement" not in names


def test_runGate_all_returns_report() -> None:
    """src/dartlab 전체 게이트 실행 → Report 반환 (warning-only)."""
    gate = _loadGateModule()
    files = gate._allSrcFiles()
    assert len(files) > 0
    # 부분만 검사 (전체는 시간 소모) — 첫 10 파일
    report = gate.runGate(files[:10])
    assert report.checked_files >= 0
    assert report.total_public_funcs >= 0
    # warning-only 모드 — missing 이 있어도 정상 동작
    assert isinstance(report.missing, list)


def test_runGate_known_covered_function() -> None:
    """formatComma 처럼 tests/core/test_formatting.py 가 직접 검증하는 함수는 missing 아님."""
    gate = _loadGateModule()
    formatting_file = _REPO / "src" / "dartlab" / "core" / "formatting.py"
    assert formatting_file.exists()
    report = gate.runGate([formatting_file])
    missing_names = {m.func_name for m in report.missing}
    # formatComma, formatKr, formatDecimal — 본 PR Track 6 oracle test 에 모두 참조됨
    assert "formatComma" not in missing_names, f"formatComma 가 누락으로 잡힘 (missing={missing_names})"
    assert "formatKr" not in missing_names
    assert "formatDecimal" not in missing_names


def test_loadBaseline_empty_when_no_file(tmp_path: Path) -> None:
    """baseline 파일 없으면 빈 set."""
    gate = _loadGateModule()
    assert gate._loadBaseline(tmp_path / "absent.json") == set()


def test_loadBaseline_parses_missing_tuples(tmp_path: Path) -> None:
    """baseline JSON 의 missing list → (path, func) 튜플 집합."""
    gate = _loadGateModule()
    import json as _json

    f = tmp_path / "baseline.json"
    f.write_text(
        _json.dumps(
            {
                "missing": [
                    {"path": "core/foo.py", "func": "barFunc", "line": 10},
                    {"path": "credit/baz.py", "func": "qux", "line": 20},
                ]
            }
        ),
        encoding="utf-8",
    )
    baseline = gate._loadBaseline(f)
    assert ("core/foo.py", "barFunc") in baseline
    assert ("credit/baz.py", "qux") in baseline
    assert len(baseline) == 2


def test_baseline_file_exists() -> None:
    """실 baseline JSON (tests/audit/_baselines/testCoverage.json) 존재 + 파싱 가능."""
    gate = _loadGateModule()
    baseline_path = _REPO / "tests" / "audit" / "_baselines" / "testCoverage.json"
    assert baseline_path.exists(), f"baseline 누락: {baseline_path}"
    baseline = gate._loadBaseline(baseline_path)
    # 본 PR 도입 시점 baseline 1097 — 35% 부채. 0 이면 baseline 깨짐.
    assert len(baseline) > 100, f"baseline 항목 너무 적음 (len={len(baseline)})"
