"""realData 스모크 — 엔진별 실제 데이터 파이프라인 검증.

목적:
    기존 unit/integration 테스트는 editable 소스와 로컬 parquet 스냅샷을
    그대로 사용한다. 그래서 "HF parquet은 최신, 설치된 wheel은 구버전"처럼
    데이터↔코드 스키마가 어긋나 조용히 None 을 리턴하는 실제 사용자 크래시를
    잡지 못한다. (예: c.sections → _call_module("sections") → None →
    AttributeError on .raw.columns.)

    realData 스위트는 반대로 "엔진의 공식 공개 진입점을 실제 데이터로 호출하고
    None/빈 결과/비정상 shape 를 즉시 실패로 처리"한다. 한 엔진당 1~2개의
    canonical smoke 만 유지 — coverage 목적이 아니라 회귀 방어용이다.

동작 규칙:
    - 기본은 005930 (삼성전자) 모듈 scope — Company 1개만 로딩
    - AAPL(EDGAR) 테스트는 별도 fixture — 필요 시점에만 로드/해제
    - 데이터 없으면 자동 skip (CI 에서 requires_data 로 묶임)
    - API 키 필요한 엔진(macro/ai)은 키 없으면 skip

실행:
    bash tests/test-lock.sh tests/realData -m "realData" -v --tb=short
"""

from __future__ import annotations

import gc
import os

import pytest

from tests.conftest import AAPL, SAMSUNG, _has_data


@pytest.fixture(scope="module")
def samsungRealData():
    """실제 데이터로 완전 초기화된 삼성전자 Company.

    module scope — 각 테스트 파일 단위로 로드/해제.
    session scope 금지 (Polars 네이티브 메모리 누수 위험).
    """
    if not _has_data(SAMSUNG, "docs"):
        pytest.skip(f"삼성전자 docs 데이터 없음 ({SAMSUNG}.parquet)")
    from dartlab import Company

    c = Company(SAMSUNG)
    yield c
    del c
    gc.collect()


@pytest.fixture(scope="module")
def aaplRealData():
    """실제 데이터로 완전 초기화된 Apple (EDGAR) Company."""
    if not _has_data(AAPL, "edgar"):
        pytest.skip(f"EDGAR finance 데이터 없음 ({AAPL}.parquet)")
    from dartlab import Company

    c = Company(AAPL)
    yield c
    del c
    gc.collect()


def _requireEnv(varName: str) -> None:
    """환경변수 미설정 시 skip. ECOS/FRED/AI provider 키 가드."""
    if not os.environ.get(varName) or os.environ.get(varName) == "test_dummy":
        pytest.skip(f"{varName} 환경변수 미설정 — 실제 API 테스트 불가")


@pytest.fixture
def requireEcosKey():
    _requireEnv("ECOS_API_KEY")


@pytest.fixture
def requireFredKey():
    _requireEnv("FRED_API_KEY")


@pytest.fixture
def requireAiKey():
    """AI 엔진 테스트 가드 — 최소 1개 provider 키 필요."""
    providers = ("OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GOOGLE_API_KEY", "GEMINI_API_KEY")
    if not any(os.environ.get(p) for p in providers):
        pytest.skip(f"AI provider 키 없음 — {providers} 중 하나 필요")
