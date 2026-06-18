"""``_segNameFromAxis`` 영업부문 축 파싱 단위 테스트 (순수 함수, 데이터 불요).

회귀 가드: 옛 코드가 파이프 접미사(``OperatingSegmentsMember|``) 형식만 인식해
평탄화(flattened) axisPath 회사(LG화학류)를 0부문으로 떨궜다. 두 인코딩 형식을
모두 처리하고 조정행·총계를 배제하는지 고정한다.
"""

from __future__ import annotations

from dartlab.analysis.financial._revenueSelect import _segNameFromAxis

# 삼성전자류 — 파이프 접미사 형식
_PIPE = "ConsolidatedMember|OperatingSegmentsMember|entity00126380_DxDivisionMemberOfStatementOfFinancialPositionMember"
# LG화학류 — 평탄화(flattened) 형식. 옛 코드가 None 으로 떨군 회귀 케이스.
_FLAT = (
    "ConsolidatedMember|"
    "entity00356361_LgEnergySolutionLtdMemberOfOperatingSegmentsMemberOf"
    "DisclosureOfOperatingSegmentsTableOfMember"
)


def test_pipe_suffix_form():
    """파이프 접미사 형식 → 부문 토큰 (삼성전자류, 회귀 없음)."""
    assert _segNameFromAxis(_PIPE) == "DxDivision"


def test_flattened_form():
    """평탄화 형식 → 부문 토큰 (LG화학류, 옛 코드 회귀 수정)."""
    assert _segNameFromAxis(_FLAT) == "LgEnergySolutionLtd"


def test_reconciling_items_excluded():
    """조정행(ReconcilingItems) = None."""
    ap = (
        "ConsolidatedMember|"
        "entity00356361_MaterialReconcilingItemsMemberOfOperatingSegmentsMemberOf"
        "DisclosureOfOperatingSegmentsTableOfMember"
    )
    assert _segNameFromAxis(ap) is None


def test_consolidated_total_excluded():
    """총계(단독 ConsolidatedMember)·부문축 부재·None = None."""
    assert _segNameFromAxis("ConsolidatedMember") is None
    assert _segNameFromAxis("entity00126380_SomeOtherAxisMember") is None
    assert _segNameFromAxis(None) is None
    assert _segNameFromAxis("") is None


def test_operating_segments_rollup_excluded():
    """부문 롤업 총계행(entity 접두 없는 ``...|OperatingSegmentsMember``) = None.

    회귀 가드: 평탄화 가드 도입 시 ``re.sub`` 폴백이 이 행을 허위 부문
    "OperatingSegments" 로 잡아 삼성전자에 가짜 50% 부문을 만든 회귀.
    """
    assert _segNameFromAxis("ConsolidatedMember|OperatingSegmentsMember") is None
