"""SCE normalizeCause + normalizeDetail + 매처 helper — sceMapper.py 분할 (규칙 3 LoC).

`sceMapper.py` 962 LoC 가 규칙 3 임계 (>800) 위반. cause / detail 매처 함수 묶음
(~336 줄) 을 본 모듈로 분리. 호출자 호환 — sceMapper.py 재내보내기.
"""

from __future__ import annotations

import re

from dartlab.providers.dart.finance.sceMapper import (
    _CAUSE_NOSPACE,
    CAUSE_FALLBACK_PATTERNS,
    CAUSE_SYNONYMS,
    DETAIL_MAP,
)


def normalizeCause(accountNm: str) -> str:
    """SCE ``account_nm`` → 변동사유 snakeId — 2-tier 매트릭스 행축 정규화.

    SCE (자본변동표) 는 행 = 변동사유 (당기순이익/배당/유상증자/...) × 열 = 자본항목
    (자본금/자본잉여금/이익잉여금/...) 2-tier 매트릭스. 본 함수는 **행축** (cause) 만 담당,
    열축은 ``normalizeDetail`` 이 처리.

    3-tier 매칭 (정공법 — 직접 매치 → 공백 제거 → fallback 패턴):
      1. ``CAUSE_SYNONYMS`` 정확 매치 (~200 entry 동의어 사전).
      2. 공백 제거 후 ``_CAUSE_NOSPACE`` 매치 (공시별 띄어쓰기 변종 흡수).
      3. ``CAUSE_FALLBACK_PATTERNS`` substring 매치 (~50 패턴, 정렬 순서 중요).
      4. 모두 실패 시 ``"unmapped:{원본}"`` 마커 반환 — caller 가 미매핑 비율 측정.

    Args:
        accountNm: SCE 변동사유 원문 (DART XBRL ``account_nm`` 그대로). 예: ``"당기순이익"``
            / ``"연결당기순이익"`` / ``"배당금지급"`` / ``"유상증자 (현금출자)"``.

    Returns:
        str — 변동사유 snakeId (예: ``"net_income"`` / ``"dividends_paid"`` /
        ``"capital_increase"``) 또는 ``"unmapped:{원본}"`` (미매핑).

    Raises:
        없음. ``accountNm=None`` 호출 시 AttributeError 가능 — caller 가 보장.

    Example:
        >>> normalizeCause("당기순이익")
        'net_income'
        >>> normalizeCause("배당금 지급")
        'dividends_paid'
              ``"capital_increase"`` / ``"acquisition_treasury"``) 또는 ``"unmapped:{원본}"``.
            - None 반환 X — 항상 str.
        Prerequisites:
            - ``CAUSE_SYNONYMS`` 사전 (모듈 상수, ~200 entry).
            - ``_CAUSE_NOSPACE`` 공백 제거 인덱스 (자동 생성).
            - ``CAUSE_FALLBACK_PATTERNS`` 정렬된 패턴 리스트.
        Freshness:
            - 매핑 사전은 정적 — 신규 변동사유 등장 시 수동 갱신.
            - DART 분기 마감 후 신종 변동사유 cadence (드물게).
        Dataflow:
            - account_nm (raw XBRL) → ``.strip()`` 정규화
            - → (tier 1) ``CAUSE_SYNONYMS`` 직접 매치
            - → (tier 2) 공백 제거 후 ``_CAUSE_NOSPACE`` 매치
            - → (tier 3) ``CAUSE_FALLBACK_PATTERNS`` substring 매치
            - → snakeId 또는 ``"unmapped:{원본}"`` 마커.
        TargetMarkets:
            - KR (DART) — IFRS 한국 적용 회사 SCE 공시 한정.
    """
    nm = accountNm.strip()
    if nm in CAUSE_SYNONYMS:
        return CAUSE_SYNONYMS[nm]

    noSpace = nm.replace(" ", "")
    if noSpace in _CAUSE_NOSPACE:
        return _CAUSE_NOSPACE[noSpace]

    for pattern, snakeId in CAUSE_FALLBACK_PATTERNS:
        if pattern in nm:
            return snakeId

    return f"unmapped:{nm}"


def _matchOwnersEquity(last: str) -> str | None:
    """소유주·지배 관련 자본 패턴."""
    if "자본" in last and ("소유주" in last or "지배" in last):
        return "owners_equity"
    if "지배" in last and ("지분" in last or "귀속" in last or "소유" in last):
        return "owners_equity"
    if "지배기업" in last and len(last) < 15:
        return "owners_equity"
    if last in ("소계", "합계", "총계"):
        return "owners_equity"
    if "소유주" in last and "자본" in last:
        return "owners_equity"
    if "소유주귀속" in last or "소유주 귀속" in last:
        return "owners_equity"
    if "자본합계" in last:
        return "owners_equity"
    if "총자본" in last:
        return "owners_equity"
    if "지배주주" in last:
        return "owners_equity"
    return None


def _matchAccumulatedOci(last: str) -> str | None:
    """기타포괄손익누계 관련 패턴."""
    if "매도가능" in last and ("평가" in last or "손익" in last):
        return "accumulated_oci"
    if "해외사업" in last and "환산" in last:
        return "accumulated_oci"
    if "지분법" in last and ("자본" in last or "변동" in last):
        return "accumulated_oci"
    if "공정가치" in last and ("평가" in last or "손익" in last):
        return "accumulated_oci"
    if "파생상품" in last and "평가" in last:
        return "accumulated_oci"
    if "포괄손익누계" in last:
        return "accumulated_oci"
    if "연결" in last and "포괄" in last:
        return "accumulated_oci"
    if "외화환산" in last or "해외환산" in last or "환산손익" in last:
        return "accumulated_oci"
    if "현금흐름위험회피" in last:
        return "accumulated_oci"
    if "FV_OCI" in last or "FVOCI" in last:
        return "accumulated_oci"
    return None


def _matchCapitalSurplus(last: str) -> str | None:
    """자본잉여금·감자차·합병차익 관련."""
    if "감자차" in last:
        return "capital_surplus"
    if "합병" in last and "차" in last:
        return "capital_surplus"
    if "할인발행" in last:
        return "capital_surplus"
    if "불입자본" in last or "불입 자본" in last:
        return "capital_surplus"
    if "불입자금" in last:
        return "capital_surplus"
    return None


def _matchOtherEquity(last: str) -> str | None:
    """기타자본·주식선택권·출자전환 등."""
    if "전환권" in last or "신주인수권" in last:
        return "other_equity"
    if last == "기타":
        return "other_equity"
    if "주식매입선택권" in last or "주식매수선택권" in last:
        return "other_equity"
    if "종속기업" in last and ("취득" in last or "추가" in last):
        return "other_equity"
    if "기타 자본" in last or "기타자본" in last:
        return "other_equity"
    if "기타지분" in last:
        return "other_equity"
    if last == "자본" or last == "자본 조정":
        return "other_equity"
    if "종속기업" in last and ("평가" in last or "손실" in last):
        return "other_equity"
    if "자기조정" in last or "자본조" in last:
        return "other_equity"
    if "주식기준보상" in last or "주식결제형" in last or "종업원급여" in last:
        return "other_equity"
    if "기타의자본" in last:
        return "other_equity"
    if "출자전환" in last:
        return "other_equity"
    if "기타" == last.strip():
        return "other_equity"
    return None


def _matchNoncontrolling(last: str) -> str | None:
    """비지배주주 지분."""
    if "외부주주" in last or "소수주주" in last:
        return "noncontrolling_interest"
    if "비지배주주" in last or "비지배" in last:
        return "noncontrolling_interest"
    if "비재비지분" in last:
        return "noncontrolling_interest"
    return None


def _matchRetainedEarnings(last: str) -> str | None:
    """이익잉여금 관련."""
    if "잉여금" in last:
        return "retained_earnings"
    if "이익영여금" in last:
        return "retained_earnings"
    if "연구인력" in last or "개발준비금" in last:
        return "retained_earnings"
    return None


def _matchMisc(last: str) -> str | None:
    """기타 단일 결과 패턴 (share_premium, held_for_sale, revaluation)."""
    if "주식발행" in last and ("초과" in last or "과" in last):
        return "share_premium"
    if "매각예정" in last:
        return "held_for_sale"
    if "재평가" in last and ("차익" in last or "이익" in last):
        return "revaluation_surplus"
    return None


_DETAIL_PATTERN_MATCHERS = (
    _matchOwnersEquity,
    _matchAccumulatedOci,
    _matchCapitalSurplus,
    _matchNoncontrolling,
    _matchRetainedEarnings,
    _matchOtherEquity,
    _matchMisc,
)


def _matchDetailPatterns(last: str) -> str | None:
    """7 그룹 matcher 를 순차 시도. 첫 매치 반환."""
    for matcher in _DETAIL_PATTERN_MATCHERS:
        result = matcher(last)
        if result is not None:
            return result
    return None


def _parseDetailLast(detail: str) -> str | None:
    """detail 문자열 정규화 → 파이프 분리 → 마지막 세그먼트 반환.

    빈 결과면 None (호출자가 "unknown" 반환).
    """
    cleaned = re.sub(r"\s*\[(member|구성요소|구성 요소)\]", "", detail)
    parts = [p.strip() for p in cleaned.split("|") if p.strip()]
    return parts[-1] if parts else None


def _matchDetailMap(last: str) -> str | None:
    """DETAIL_MAP 직접 매칭 (공백 포함 + 무시)."""
    for key, val in DETAIL_MAP.items():
        if key in last:
            return val
    lastNoSpace = last.replace(" ", "")
    for key, val in DETAIL_MAP.items():
        if key.replace(" ", "") in lastNoSpace:
            return val
    return None


def normalizeDetail(detail: str | None) -> str:
    """``account_detail`` → 자본항목 snakeId (Q3.1e orchestrator split).

    파이프 (``|``) 구분 마지막 세그먼트에서 ``DETAIL_MAP`` → 7 패턴 그룹 → unmapped.
    미매핑 시 ``"unmapped:{원본}"`` 반환.

    Args:
        detail: SCE ``account_detail`` 원문. None / 빈 문자열이면 ``"unknown"``.

    Returns:
        자본항목 snakeId (예: ``"retained_earnings"``) 또는 ``"unmapped:{원본}"`` 또는
        special ``"total"``/``"total_separate"``/``"unknown"``.

    Raises:
        없음.

    Example:
        >>> normalizeDetail("자본의 구성요소 | 이익잉여금")
        'retained_earnings'
    """
    if not detail:
        return "unknown"

    detail = detail.replace("\u3000", " ").strip()

    if re.search(r"연결재무제표\s*\[", detail):
        return "total"
    if re.search(r"별도재무제표\s*\[", detail):
        return "total_separate"

    last = _parseDetailLast(detail)
    if last is None:
        return "unknown"

    directMatch = _matchDetailMap(last)
    if directMatch is not None:
        return directMatch

    patternMatch = _matchDetailPatterns(last)
    if patternMatch is not None:
        return patternMatch

    return f"unmapped:{last}"


# ── 한글 표시 라벨 ──────────────────────────────────────────────

CAUSE_LABELS: dict[str, str] = {
    "beginning_equity": "기초자본",
    "adjusted_beginning": "수정후기초",
    "ending_equity": "기말자본",
    "net_income": "당기순이익",
    "dividends": "배당",
    "stock_dividends": "주식배당",
    "treasury_acquired": "자기주식취득",
    "treasury_disposed": "자기주식처분",
    "treasury_retired": "자기주식소각",
    "treasury_change": "자기주식변동",
    "capital_increase": "유상증자",
    "capital_decrease": "감자",
    "fx_translation": "해외사업환산",
    "fvoci_valuation": "FVOCI평가",
    "cashflow_hedge": "현금흐름위험회피",
    "remeasurement_db": "확정급여재측정",
    "associate_oci": "지분법자본변동",
    "intragroup_tx": "연결범위내거래",
    "consolidation_change": "연결범위변동",
    "accounting_change": "회계정책변경",
    "error_correction": "전기오류수정",
    "stock_compensation": "주식보상",
    "stock_options": "주식선택권",
    "convertible_bond": "전환사채",
    "hybrid_issued": "신종자본증권발행",
    "hybrid_interest": "신종자본증권이자",
    "total_comprehensive": "총포괄손익",
    "reclassification": "재분류",
    "nci_change": "비지배지분변동",
    "equity_change_total": "자본변동합계",
    "other_oci": "기타포괄손익",
    "revaluation_surplus": "재평가잉여금",
    "other": "기타",
    "held_for_sale_reclass": "매각예정재분류",
    "retained_earnings_appropriation": "이익잉여금처분",
    "deficit_offset": "결손금보전",
    "debt_equity_swap": "출자전환",
    "merger": "합병",
    "spinoff": "분할",
}

DETAIL_LABELS: dict[str, str] = {
    "share_capital": "자본금",
    "share_premium": "주식발행초과금",
    "capital_surplus": "자본잉여금",
    "retained_earnings": "이익잉여금",
    "other_equity": "기타자본",
    "accumulated_oci": "기타포괄손익누계액",
    "treasury_stock": "자기주식",
    "noncontrolling_interest": "비지배지분",
    "owners_equity": "지배주주지분",
    "total": "합계",
    "total_separate": "합계(별도)",
    "hybrid_capital": "신종자본증권",
    "held_for_sale": "매각예정",
    "revaluation_surplus": "재평가잉여금",
}
