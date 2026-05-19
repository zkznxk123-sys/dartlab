"""tests/run.py 의 GATES dict 와 .github/workflows/ci-*.yml 의 matrix.gate 일치 검증.

# Capabilities
GATES ↔ YAML matrix drift 차단. 한쪽에만 게이트 추가 시 PR fail.

# Example
    pytest tests/audit/test_runEntrypoint.py -v

# Returns
모든 게이트가 tier 별로 정확히 한 YAML 의 matrix.gate 에 등장 → 통과.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "tests"))

from run import GATES, REALDATA_SHARDS  # noqa: E402

WORKFLOWS = REPO_ROOT / ".github" / "workflows"


def _extractInvokedGates(yaml_path: Path) -> set[str]:
    """YAML 안의 모든 `tests/run.py gate <name>` 호출 + matrix.include 의 `gate: X` 캡쳐.

    실제 게이트 호출이 정의 (matrix include or 직접 run 라인) 중 어디에 있든
    잡는다. fan-out 구조 (realdata-plan / realdata-suite 등) 도 포함.
    """
    text = yaml_path.read_text(encoding="utf-8")
    out: set[str] = set()
    # 1) `python ... tests/run.py gate <name>` 직접 호출
    for m in re.finditer(r"tests/run\.py\s+gate\s+([A-Za-z0-9_-]+)", text):
        out.add(m.group(1))
    # 2) `matrix.include` 의 `- gate: X` 또는 `gate: X` 한 줄
    for line in text.splitlines():
        m = re.match(r"\s*-?\s*gate:\s*([A-Za-z0-9_-]+)\s*$", line)
        if m:
            out.add(m.group(1))
    return out


@pytest.mark.unit
def test_gatesDictNoDuplicates():
    names = [g.name for g in GATES.values()]
    assert len(names) == len(set(names)), f"중복 name: {names}"


@pytest.mark.unit
def test_gatesAllHaveCmd():
    empty = [g.name for g in GATES.values() if not g.cmd]
    assert not empty, f"cmd 비어있는 게이트: {empty}"


@pytest.mark.unit
def test_matrixParamPlaceholderPresent():
    """matrix_param 설정된 게이트는 cmd 안에 placeholder 필수."""
    for gate in GATES.values():
        if gate.matrix_param == "python":
            assert "{cov_flags}" in gate.cmd, f"{gate.name}: {{cov_flags}} 누락"
        elif gate.matrix_param == "test":
            assert "{test_file}" in gate.cmd, f"{gate.name}: {{test_file}} 누락"


@pytest.mark.unit
@pytest.mark.parametrize(
    "tier,filename",
    [
        ("fast", "ci-fast.yml"),
        ("full", "ci-full.yml"),
        ("nightly", "ci-nightly.yml"),
    ],
)
def test_gatesDictMatchesYamlMatrix(tier, filename):
    """GATES tier 별 → 대응 YAML 의 matrix.gate 와 정확히 일치."""
    yaml_path = WORKFLOWS / filename
    if not yaml_path.exists():
        pytest.skip(f"{filename} 미존재 (PR 머지 전 단계)")
    dict_gates = {g.name for g in GATES.values() if g.tier == tier}
    yaml_gates = _extractInvokedGates(yaml_path)
    if not yaml_gates:
        pytest.skip(f"{filename} 에 tests/run.py gate 호출 없음 — 신형 dispatch 미적용")
    only_dict = dict_gates - yaml_gates
    only_yaml = yaml_gates - dict_gates
    msg = []
    if only_dict:
        msg.append(f"GATES 에만 있음 ({tier}): {sorted(only_dict)}")
    if only_yaml:
        msg.append(f"YAML 에만 있음 ({filename}): {sorted(only_yaml)}")
    assert not msg, "\n".join(msg)


@pytest.mark.unit
def test_realdataShardsMatchNightlyMatrix():
    """REALDATA_SHARDS 상수 ↔ ci-nightly.yml realdata-suite-full matrix 일치."""
    yaml_path = WORKFLOWS / "ci-nightly.yml"
    if not yaml_path.exists():
        pytest.skip("ci-nightly.yml 미존재")
    text = yaml_path.read_text(encoding="utf-8")
    # test_file 블록 추출 — multi-line `-` items
    in_block = False
    yaml_shards: set[str] = set()
    for line in text.splitlines():
        s = line.strip()
        if s.startswith("test_file:"):
            in_block = True
            continue
        if in_block:
            m = re.match(r"-\s*([\w.]+\.py)", s)
            if m:
                yaml_shards.add(m.group(1))
            elif s and not s.startswith("-") and not s.startswith("#"):
                in_block = False
    if not yaml_shards:
        pytest.skip("realdata-suite-full matrix 미발견 (신형 dispatch 적용 전)")
    diff_dict = set(REALDATA_SHARDS) - yaml_shards
    diff_yaml = yaml_shards - set(REALDATA_SHARDS)
    assert not diff_dict and not diff_yaml, f"REALDATA_SHARDS 에만: {sorted(diff_dict)}\nYAML 에만: {sorted(diff_yaml)}"


@pytest.mark.unit
def test_totalGateCountFrozen():
    """29 게이트 동결 — 의도 없는 추가/삭제 방지. 변경 시 본 테스트 함께 수정."""
    assert len(GATES) == 29, f"게이트 수 변경: {len(GATES)} (의도된 변경이면 본 테스트도 수정)"


@pytest.mark.unit
def test_tierDistributionFrozen():
    from collections import Counter

    c = Counter(g.tier for g in GATES.values())
    assert dict(c) == {"fast": 16, "full": 6, "nightly": 7}, f"tier 분포 변경: {dict(c)}"
