"""Company 인스턴스의 모든 공개 속성 전수 스모크.

외부 사용자가 `c.X` 라고 읽는 순간 크래시하지 않는지 전수 검증.
dir(c) 기반 자동 enumerate 이므로 새 속성 추가되어도 자동 커버.

결과 정책:
    - **크래시** (exception) → FAIL
    - **None 반환** → 해당 속성이 데이터 부재 시 None 을 공식적으로 허용하는지
      화이트리스트로 구분. 화이트리스트 밖에서 None 은 FAIL.
    - **정상 객체/DataFrame/dict/str/숫자** → PASS

과거 회귀:
    - c.sections None 리턴 → .raw.columns 크래시 (2026-04-19)
    - c.select("IS") 렌더 컬럼 누락 (2026-04-19)
"""

from __future__ import annotations

import pytest

# 데이터 부재 시 None 이 공식 허용되는 속성 (명시적 화이트리스트).
_NONE_ALLOWED: frozenset[str] = frozenset(
    {
        "disclosure",  # 공시 조회 실패 가능
        "liveFilings",  # 네트워크/DART API 의존
        "news",  # Google News RSS 실패 가능
        "keywordTrend",  # 검색 인덱스 없을 수 있음
        "narrativeDiff",  # 이전 기간 없으면 None
        "storyTree",  # 이야기 엔진 미실행 상태
        "retrievalBlocks",  # AI 검색 블록 미빌드
        "validateStory",  # AI 검증 미실행
        "valuationImpact",  # 내부 계산 결과 없음
        "network",  # 관계자/지분 네트워크 없음
        "causalWeights",  # 인과가중 미계산
        "contextSlices",  # AI 컨텍스트 미빌드
        "priority",  # 우선순위 미설정
        "watch",  # 관심 플래그 없음
        "rank",  # 랭킹 데이터 없음
        "status",  # 상태 정보 없음
        "update",  # callable (결과 없어도 OK)
        "view",  # viewer 미초기화
        "table",  # callable
        "resolve",  # static method
        "canHandle",  # boolean 판정 함수
        "search",  # static method
        "listing",  # static method
        "select",  # method
        "show",  # method
        "trace",  # method
        "diff",  # method
        "filings",  # method
        "readFiling",  # method
        "ask",  # method
        "audit",  # method
        "sources",  # method/property
        "topicSummaries",  # method
        "gather",  # method
        "rawDocs",  # 원본 parquet 없을 수 있음
        "rawFinance",  # 원본 parquet 없을 수 있음
        "rawReport",  # 원본 parquet 없을 수 있음
        "facts",  # KG facts 없음 가능
        "fiscalYearEnd",  # 일부 회사 미정의
        "sectorParams",  # market params 없음 가능
        "index",  # 구조 인덱스 미빌드
        "workforce",  # 직원 정보 없을 수 있음
        "governance",  # 지배구조 데이터 없을 수 있음
        "debt",  # 채무 집계 없을 수 있음
        "capital",  # 자본 변동 없을 수 있음
    }
)


def _publicAttrs() -> list[str]:
    """Company 공개 속성 전수 — 실제 인스턴스에서 동적 수집."""
    from dartlab import Company

    c = Company("005930")
    attrs = sorted(a for a in dir(c) if not a.startswith("_"))
    del c
    return attrs


PUBLIC_ATTRS = _publicAttrs()


@pytest.mark.realData
@pytest.mark.integration
@pytest.mark.parametrize("attr", PUBLIC_ATTRS)
def test_companyAttr_accessNoCrash(samsungRealData, attr):
    """c.<attr> 접근이 크래시 없이 동작. None 은 화이트리스트 밖에서 실패.

    method/callable 은 '접근만' 검증 (인자 없이 호출하면 TypeError 발생 가능하므로
    접근 결과가 callable 이면 OK 로 처리).
    """
    try:
        value = getattr(samsungRealData, attr)
    except AttributeError as e:
        pytest.fail(f"c.{attr} AttributeError — 공개 속성 약속 위반: {e}")
    except Exception as e:
        pytest.fail(f"c.{attr} 크래시: {type(e).__name__}: {e}")

    # callable (method/function) 은 접근 가능만 보장
    if callable(value):
        return

    # None 은 화이트리스트에서만 허용
    if value is None:
        if attr in _NONE_ALLOWED:
            return
        pytest.fail(
            f"c.{attr} 가 None — 화이트리스트에 없음. 이 속성이 실제로 None 을 허용한다면 _NONE_ALLOWED 에 추가하라."
        )
