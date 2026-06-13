"""scan 프리빌드 SSOT 정합성 contract.

회귀 사례 (2026-05-17): scanner 들이 호출하는 apiType 13 종 중 `shortTermBond` ·
`commercialPaper` · `investedCompany` 3 종이 빌더 `SCAN_API_TYPES` 에 누락되어
dartlab.scan("debt") · network axis 가 silent thrift error 로 실패.

본 테스트는 세 SSOT 가 어긋나는 순간 즉시 fail 한다:
1. 빌더 `SCAN_API_TYPES` (scan/builders/kr/report/build.py)
2. 다운로드 무결성 `_REQUIRED_REPORT_FILES` (scan/io/parquet.py)
3. 실소비자 — scan 엔진 `scanParquets(apiType, ...)` (scan/{debt,capital,governance,...})
   + 터미널 런타임 어댑터 `read('apiType', ...)` (ui/packages/runtime/src/adapters/public/sources/reportSource.ts,
   HF `dart/scan/report/*.parquet` hyparquet 직독 — 2026-06-12 동급 소비 표면, 플랫폼 단계-4a-2 에서
   landing/src/lib/terminal/data/reportSeries.ts → runtime sources 로 승격).
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from dartlab.scan.builders.kr.report.build import SCAN_API_TYPES
from dartlab.scan.io.parquet import _REQUIRED_REPORT_FILES

pytestmark = pytest.mark.unit

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SCAN_DIR = _REPO_ROOT / "src" / "dartlab" / "scan"
# 터미널 런타임 어댑터 데이터 소스 (플랫폼 단계-4a-2 승격 위치). reportSource.ts 의 read() 호출이 SSOT.
# 디렉토리 전체 스캔 — 향후 소스 파일 rename/분할에도 견딘다 (scan 엔진 스캔과 동형).
_RUNTIME_SOURCES_DIR = _REPO_ROOT / "ui" / "packages" / "runtime" / "src" / "adapters" / "public" / "sources"
_CALL_RE = re.compile(r"scanParquets\(\s*['\"]([a-zA-Z][a-zA-Z0-9_]*)['\"]")
# reportSource.ts 내부 read('apiType', code, cols) — dart/scan/report/{apiType}.parquet 직독 호출
_TS_CALL_RE = re.compile(r"\bread\(\s*'([a-zA-Z][a-zA-Z0-9_]*)'")


def _scanConsumerApiTypes() -> set[str]:
    """scan/ 디렉토리 안 scanParquets() 첫 인자로 호출되는 apiType set."""
    found: set[str] = set()
    for py in _SCAN_DIR.rglob("*.py"):
        if py.name == "parquet.py" and py.parent.name == "io":
            continue  # 정의부 자체는 skip
        try:
            text = py.read_text(encoding="utf-8")
        except OSError:
            continue
        for m in _CALL_RE.finditer(text):
            apiType = m.group(1)
            # keepCols 안 stockCode/year/quarter 같은 메타가 첫 인자로 잘못 매칭되는 케이스 제외
            if apiType in {"stockCode", "year", "quarter"}:
                continue
            found.add(apiType)
    return found


def _terminalConsumerApiTypes() -> set[str]:
    """터미널 런타임 어댑터 sources 가 read() 로 직독하는 apiType set (reportSource.ts 등)."""
    found: set[str] = set()
    if not _RUNTIME_SOURCES_DIR.is_dir():
        return found
    for ts in _RUNTIME_SOURCES_DIR.rglob("*.ts"):
        try:
            text = ts.read_text(encoding="utf-8")
        except OSError:
            continue
        found.update(m.group(1) for m in _TS_CALL_RE.finditer(text))
    return found


def _consumerApiTypes() -> set[str]:
    """실소비자 전체 — scan 엔진 + landing 터미널 합집합."""
    return _scanConsumerApiTypes() | _terminalConsumerApiTypes()


def test_required_report_matches_builder() -> None:
    """_REQUIRED_REPORT_FILES 와 SCAN_API_TYPES 가 1:1 일치."""
    fromBuilder = {f"{api}.parquet" for api in SCAN_API_TYPES}
    fromRequired = set(_REQUIRED_REPORT_FILES)
    onlyBuilder = fromBuilder - fromRequired
    onlyRequired = fromRequired - fromBuilder
    assert not onlyBuilder, f"빌더에만 있음 (다운로드 무결성 검증 누락): {sorted(onlyBuilder)}"
    assert not onlyRequired, f"무결성 검증에만 있음 (빌더 누락): {sorted(onlyRequired)}"


def test_builder_covers_all_consumers() -> None:
    """scanner 들이 호출하는 모든 apiType 이 빌더 SCAN_API_TYPES 에 포함."""
    consumers = _consumerApiTypes()
    missing = consumers - set(SCAN_API_TYPES)
    assert not missing, (
        f"scanner 호출 apiType 이 빌더 SCAN_API_TYPES 에 없음 → prebuild 미생성 → "
        f"fallback path thrift error 회귀: {sorted(missing)}. "
        f"scan/builders/kr/report/build.SCAN_API_TYPES 와 scan/io/parquet._REQUIRED_REPORT_FILES "
        f"에 동시 추가하라."
    )


def test_no_orphan_apitype_in_builder() -> None:
    """빌더에는 있는데 실소비자(scan 엔진·터미널 모두)가 안 쓰는 apiType 0 (cruft 차단)."""
    consumers = _consumerApiTypes()
    orphan = set(SCAN_API_TYPES) - consumers
    assert not orphan, (
        f"빌더에는 있지만 scan 엔진·landing 터미널 어디서도 쓰지 않는 apiType (cruft): {sorted(orphan)}. "
        f"실제 호출이 있다면 _CALL_RE/_TS_CALL_RE 정규식 점검, 아니면 빌더에서 제거."
    )
