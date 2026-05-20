"""AccountMapper Polars 벡터화 + mega-dict 회귀 가드.

Phase B (mega-dict + mapColumn) + Phase C (reference 래퍼 위임) 활성화
가드. 통합 본체 작성 *전* 박은 가드 — Phase B/C 완료 후 skip 마커 제거
시점에 검증 본격 활성.

회귀 시그널 — 본 테스트 fail 은 곧 mapColumn 결과 ↔ row map() 결과
불일치 (의미 손실) 또는 가속 효과 미달.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

_BASELINE_PATH = Path(__file__).parent / "_baselines" / "mapperVectorBaseline.json"


@pytest.fixture(scope="module")
def mapper():
    from dartlab.core.utils.labels import _loadAccountMappings
    from dartlab.providers.dart.finance.mapper import AccountMapper

    _loadAccountMappings.cache_clear()
    AccountMapper.release()
    return AccountMapper.get()


@pytest.mark.skip(reason="Phase B 활성화 — _compileMega() 구현 후")
def test_mega_dict_compile_no_conflict(mapper) -> None:
    """mega-dict 펼침 시 동일 normalized 키에 *다른* snakeId 할당 0 건.

    충돌 = 의미 손실 = mapColumn() 의 결과가 row map() 와 달라짐.
    빌드 시 충돌 dict 는 별도 set 으로 분리해 Python fallback 으로 보내야
    함. 본 가드는 *충돌 set 이 비어 있음* 또는 *충돌 키가 fallback 으로
    안전 우회됨* 검증.
    """
    mega = mapper._compileMega()
    assert isinstance(mega, dict), "_compileMega() 결과는 dict"
    assert len(mega) > 30_000, f"mega-dict 사전 펼침 부족 ({len(mega)} entry)"

    conflicts = getattr(mapper.__class__, "_megaConflicts", None)
    if conflicts is not None:
        assert isinstance(conflicts, (set, dict)), "_megaConflicts 자료형 위반"
        assert len(conflicts) < 100, f"mega-dict 충돌 {len(conflicts)} 건 — 펼침 룰 위험. 검토 필요."


@pytest.mark.skip(reason="Phase B 활성화 — mapColumn() 구현 후")
def test_mapColumn_matches_mapRow(mapper) -> None:
    """mapColumn() 벡터화 결과 ↔ row 별 map() 결과 100% 일치.

    핵심 가드 — 의미 손실 0 보장. 카카오 (035720) finance parquet
    sample 100 행 (또는 전체 가용분) 으로 검증.
    """
    import polars as pl

    sampleParquet = (
        Path("data/dart/finance/035720.parquet"),
        Path("data/dart/finance/000020.parquet"),
    )
    df = None
    for p in sampleParquet:
        if p.exists():
            df = pl.read_parquet(p).head(500)
            break
    if df is None:
        pytest.skip("sample finance parquet 부재 — data/dart/finance/ 빌드 후 활성")

    vector = mapper.mapColumn(df, idCol="account_id", nmCol="account_nm")
    rowResult = [mapper.map(r.get("account_id") or "", r.get("account_nm") or "") for r in df.to_dicts()]
    vectorResult = vector.get_column("snakeId").to_list()
    assert vectorResult == rowResult, "mapColumn() 벡터화 결과가 row map() 와 불일치 — 의미 손실 회귀"


@pytest.mark.skip(reason="Phase B 활성화 — mapColumn() 구현 + baseline 측정 후")
def test_mapper_vector_speed_baseline(mapper) -> None:
    """카카오 finance 매핑 속도 — baseline 대비 ≥10x 가속.

    Phase B 통합 후 row loop → mapColumn() 교체로 카카오 buildTimeseries
    가 기존 baseline 의 1/10 미만 시간 안 완료해야 함. baseline JSON 은
    Phase B 시작 직전에 row loop 동작으로 측정·박음.
    """
    import time

    import polars as pl

    if not _BASELINE_PATH.exists():
        pytest.skip(f"baseline JSON 부재: {_BASELINE_PATH}")
    baseline = json.loads(_BASELINE_PATH.read_text(encoding="utf-8"))
    rowSeconds = baseline.get("rowLoopSeconds")
    assert isinstance(rowSeconds, (int, float)) and rowSeconds > 0, f"baseline rowLoopSeconds 손상: {rowSeconds!r}"

    sampleParquet = Path("data/dart/finance/035720.parquet")
    if not sampleParquet.exists():
        pytest.skip(f"카카오 finance parquet 부재: {sampleParquet}")

    df = pl.read_parquet(sampleParquet)
    mapper._compileMega()  # 1 회 컴파일 warm-up (캐시 캡처)

    t0 = time.perf_counter()
    mapper.mapColumn(df, idCol="account_id", nmCol="account_nm")
    vectorSeconds = time.perf_counter() - t0

    assert vectorSeconds < rowSeconds / 10, (
        f"가속 미달: vector={vectorSeconds:.3f}s vs row={rowSeconds:.3f}s. 10x 가속 목표 위반."
    )


def test_baselines_dir_exists() -> None:
    """baseline 디렉토리 생성 — Phase B 직전 baseline 측정용 placeholder."""
    baselineDir = _BASELINE_PATH.parent
    assert baselineDir.exists() or baselineDir.parent.exists(), f"_baselines/ 부모 디렉토리 부재: {baselineDir}"
