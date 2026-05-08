"""골든 trace 실패 taxonomy 분류기 — 5 범주.

P0 측정 인프라의 핵심: 실 LLM 답변 trace 를 결정적 키워드 매칭으로 분류해
P1 풍부화 전후 ROI 비교의 신호를 만든다.

5 범주:
- tool_missing: 필요한 도구 호출 누락 (expectedTools 미충족)
- ref_missing: 숫자 claim 에 ref 없음 (답변에 숫자/퍼센트가 있는데 valueRef·tableRef 없음)
- industry_branch_missing: 산업 분기 누락 (industryBranch.mustMention=True 인데 keywords 미언급)
- null_zero_substitution: 결손값 0 대체 신호 (답변에 "0 으로 채움" 같은 명시 또는 "0%" 가 있는데 결손 회사)
- calc_error: 가공 계산 실패 (답변이 ValueError/TypeError 어구 또는 코드 실행 실패 메시지)

분류는 키워드 매칭이라 false positive 가능 — 골든 baseline freeze 시 운영자가 spot check.
"""

from __future__ import annotations

import re
from typing import Any

import pytest


def classify(case: dict[str, Any], result: dict[str, Any]) -> dict[str, bool]:
    """5 범주 분류 결과 dict.

    Parameters
    ----------
    case : dict
        cases.yaml 의 한 케이스 — expectedTools / expectedSkillRefs / industryBranch 등 메타.
    result : dict
        runGoldenTrace 결과 — answerText / id / 등.

    Returns
    -------
    dict[str, bool]
        5 범주 키 + 값 (True 면 해당 실패 패턴 발견).
    """
    answer = str(result.get("answerText") or "")
    if not answer:
        # 답변 자체가 비면 모든 카테고리 fail 로 표시.
        return {
            "tool_missing": True,
            "ref_missing": True,
            "industry_branch_missing": True,
            "null_zero_substitution": False,
            "calc_error": True,
        }

    return {
        "tool_missing": _toolMissing(case, answer, result),
        "ref_missing": _refMissing(answer),
        "industry_branch_missing": _industryBranchMissing(case, answer),
        "null_zero_substitution": _nullZeroSubstitution(answer),
        "calc_error": _calcError(answer),
    }


_REF_TOKEN_RE = re.compile(r"<(value|table|date|execution|skill|api|web)Ref:[^>]+>")
# 끝의 단위 (% / 원 / 배 / 억 / 조) 는 non-word char — \b 매치 안 되므로 closing boundary 제거.
_NUMBER_RE = re.compile(r"\b\d+(?:\.\d+)?\s*(?:%|원|배|억|조)")


def _toolMissing(case: dict[str, Any], answer: str, result: dict[str, Any]) -> bool:
    """expectedTools 가 명시되어 있고 답변이 너무 짧으면 도구 호출 안 한 신호.

    실제 trace 로그가 outcome_log 에 있으면 그걸로 정밀 검증할 수 있지만,
    본 분류기는 답변 길이 + 톤만 본다 (heuristic).
    """
    expected_tools = case.get("expectedTools") or []
    if not expected_tools:
        return False
    # 답변이 거의 비어있는 경우만 tool_missing — 짧은 답변도 도구 호출 후 합성 가능.
    if len(answer) < 50:
        return True
    # "도구 없이" / "데이터 없이" 같은 답변 톤
    return any(phrase in answer for phrase in ("도구 없이", "데이터 없이 답할 수 없", "수집 후 다시"))


def _refMissing(answer: str) -> bool:
    """답변에 숫자가 있는데 ref token 이 없으면 ref_missing.

    숫자 = 비율/금액/배수. ref token = `<valueRef:...>` 등.
    """
    has_number = bool(_NUMBER_RE.search(answer))
    has_ref = bool(_REF_TOKEN_RE.search(answer))
    return has_number and not has_ref


def _industryBranchMissing(case: dict[str, Any], answer: str) -> bool:
    """industryBranch.mustMention=True 인데 keywords 중 하나도 답변에 없으면 missing."""
    branch = case.get("industryBranch") or {}
    if not branch.get("mustMention"):
        return False
    keywords = branch.get("keywords") or []
    if not keywords:
        return False
    return not any(kw in answer for kw in keywords)


_ZERO_SIGNALS = (
    "0 으로 채",
    "0으로 대체",
    "결손은 0",
    "missing → 0",
)


def _nullZeroSubstitution(answer: str) -> bool:
    """답변에 결손값 0 대체 신호가 있으면 True.

    명시적 표현 + 의심 패턴 ("자산 0 원" 같은 가짜 0).
    """
    if any(sig in answer for sig in _ZERO_SIGNALS):
        return True
    # "0 원" · "0%" 가 *총자산 / 매출 / ROE* 옆에 등장하면 의심
    suspicious = re.search(r"(총자산|매출|매출액|영업이익|순이익|ROE|ROA)\s*(?:은|는|:|=)\s*0\s*(?:%|원|배)", answer)
    return bool(suspicious)


_ERROR_SIGNALS = (
    "ValueError",
    "TypeError",
    "AttributeError",
    "KeyError",
    "코드 실행 실패",
    "계산 실패",
    "Traceback",
)


def _calcError(answer: str) -> bool:
    """답변에 예외 클래스명 또는 실행 실패 어구가 있으면 calc_error."""
    return any(sig in answer for sig in _ERROR_SIGNALS)


# ── 단위 테스트 ───────────────────────────────────────────────────────


@pytest.mark.unit
def test_classify_clean_answer_with_refs() -> None:
    case = {
        "expectedTools": ["ReadSkill", "RunPython"],
        "industryBranch": {"mustMention": True, "keywords": ["반도체"]},
    }
    result = {
        "answerText": (
            "삼성전자의 ROE 는 12.3% <valueRef:value:005930:ratios:2025Q3:roe> 이며 반도체 사이클 회복 신호가 보입니다."
        ),
    }
    cat = classify(case, result)
    assert cat["tool_missing"] is False
    assert cat["ref_missing"] is False
    assert cat["industry_branch_missing"] is False
    assert cat["null_zero_substitution"] is False
    assert cat["calc_error"] is False


@pytest.mark.unit
def test_classify_refMissing_when_number_without_ref() -> None:
    case = {"expectedTools": ["RunPython"], "industryBranch": {"mustMention": False}}
    result = {"answerText": "삼성전자의 ROE 는 12.3% 입니다." * 5}  # 숫자 있음, ref 없음
    cat = classify(case, result)
    assert cat["ref_missing"] is True


@pytest.mark.unit
def test_classify_industryBranchMissing_for_finance_company() -> None:
    case = {
        "expectedTools": ["RunPython"],
        "industryBranch": {"mustMention": True, "keywords": ["은행", "BIS", "NIM"]},
    }
    result = {"answerText": "신한지주의 부채비율은 245% 입니다." * 3}  # 일반 ratio 만, 은행 분기 없음
    cat = classify(case, result)
    assert cat["industry_branch_missing"] is True


@pytest.mark.unit
def test_classify_nullZeroSubstitution() -> None:
    case = {"industryBranch": {"mustMention": False}}
    result = {"answerText": "결손은 0 으로 채워서 계산했습니다. " * 5}
    cat = classify(case, result)
    assert cat["null_zero_substitution"] is True


@pytest.mark.unit
def test_classify_calcError_detects_traceback() -> None:
    case = {"industryBranch": {"mustMention": False}}
    result = {"answerText": "AttributeError: 'DataFrame' object has no attribute 'price'" * 3}
    cat = classify(case, result)
    assert cat["calc_error"] is True


@pytest.mark.unit
def test_classify_emptyAnswer_marks_all_failures() -> None:
    case = {"industryBranch": {"mustMention": True, "keywords": ["반도체"]}}
    result = {"answerText": ""}
    cat = classify(case, result)
    assert cat["tool_missing"] is True
    assert cat["ref_missing"] is True
    assert cat["industry_branch_missing"] is True
