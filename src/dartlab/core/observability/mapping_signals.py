"""5 신호 평가 — `accountMappings.json` 자동 보강 후보의 안전성 측정.

본 모듈은 `mapping_ledger` 가 누적한 미커버 계정 관측 ndjson 을 그룹화한
뒤, 각 (accountId, accountNm) 그룹에 대해 5 신호를 계산하여 자동 적용
가능성을 측정한다. 모든 신호는 *조언* 이지 prod 매핑 사전 patch 의 권한이
아니다. 운영자 review CLI 와 promote CLI 가 단독 권한.

신호 5 종:
    S1 빈도            occurrenceCount 합 ≥ MIN_FREQUENCY
    S2 회사 분산        고유 stockCode 수 ≥ MIN_CORPORATE_DISPERSION
    S3 한글 정규화 매칭 standardAccounts.korName 와 Levenshtein 유사도 ≥ KOR_MATCH_THRESHOLD
    S4 IFRS 동의어 1 hop accountNm/accountId 정규화 후 mappings 직 hit
    S5 오타 거부        jamo 단위 1 자모 차이 IFRS korName 존재 시 *거부*

autoEligible = S1 ∧ S2 ∧ (S3 ∨ S4) ∧ ¬S5
suggestedSnakeId = S4 hit 우선, 그 다음 S3 best.
confidence = S3 점수 (없으면 0.0).

reason (S5 거부 시): {"reason": "typo_suspect", "suggestedFix": "<유사 korName>"}.

AIContext:
    - 자동화 안전장치: S5 가 가장 보수적. 1 자모 차이는 오타 가능성 — 사용자
      확인 없이 매핑 사전에 등록하면 가짜 매칭 위험.
    - 신호 임계치는 모듈 상수 (튜닝 시 단위 테스트도 함께 수정).
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

MIN_FREQUENCY = 5
MIN_CORPORATE_DISPERSION = 3
KOR_MATCH_THRESHOLD = 0.85
TYPO_JAMO_DISTANCE = 1
SUFFIX_TAIL_CHARS = 3  # 마지막 N 자 액션 단어 비교
SUFFIX_MISMATCH_PENALTY = 0.5  # 끝 N 자 다를 때 점수 곱


@dataclass(frozen=True)
class SignalResult:
    """단일 (accountId, accountNm) 그룹의 5 신호 평가 결과."""

    accountId: str
    accountNm: str
    occurrenceCount: int
    corporateDispersion: int
    s1Frequency: bool
    s2Dispersion: bool
    s3KorMatchScore: float
    s3KorMatchSnakeId: str | None
    s4IfrsSynonymSnakeId: str | None
    s5TypoSuspect: bool
    s5SuggestedFix: str | None
    autoEligible: bool
    suggestedSnakeId: str | None
    confidence: float

    def breakdown(self) -> dict:
        """Args: 없음.

        Returns:
            5 신호 raw 결과를 JSON 직렬화 가능한 dict 로.

        Example:
            >>> r = SignalResult("", "name", 5, 3, True, True, 0.9, "x", None,
            ...                  False, None, True, "x", 0.9)
            >>> r.breakdown()["s1"]
            True

        Raises:
            없음.
        """
        return {
            "s1": self.s1Frequency,
            "s2": self.s2Dispersion,
            "s3Score": self.s3KorMatchScore,
            "s3Snake": self.s3KorMatchSnakeId,
            "s4Snake": self.s4IfrsSynonymSnakeId,
            "s5Typo": self.s5TypoSuspect,
            "s5Fix": self.s5SuggestedFix,
        }


def _normalizeKor(name: str) -> str:
    """한글 공백·괄호·하이픈 제거 후 비교용 키로."""
    cleaned = re.sub(r"[\s()\[\]/.,\-_]", "", name or "")
    return cleaned


def _levenshtein(a: str, b: str) -> int:
    """표준 Levenshtein. O(n*m). 짧은 문자열용."""
    if a == b:
        return 0
    if not a:
        return len(b)
    if not b:
        return len(a)
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        curr = [i] + [0] * len(b)
        for j, cb in enumerate(b, 1):
            cost = 0 if ca == cb else 1
            curr[j] = min(curr[j - 1] + 1, prev[j] + 1, prev[j - 1] + cost)
        prev = curr
    return prev[-1]


def _ratio(a: str, b: str) -> float:
    """0~1 유사도 = 1 - dist / max(len)."""
    if not a and not b:
        return 1.0
    maxLen = max(len(a), len(b))
    if maxLen == 0:
        return 1.0
    return 1.0 - _levenshtein(a, b) / maxLen


def _jamoDistance(a: str, b: str) -> int:
    """NFD 정규화 후 자모 단위 Levenshtein — 한글 1 자모 typo 검출용."""
    aJamo = unicodedata.normalize("NFD", a or "")
    bJamo = unicodedata.normalize("NFD", b or "")
    return _levenshtein(aJamo, bJamo)


def signalFrequency(occurrenceCount: int) -> bool:
    """Args:
        occurrenceCount: 그룹의 총 관측 행 수.

    Returns:
        ``MIN_FREQUENCY`` (=5) 이상이면 True.

    Example:
        >>> signalFrequency(5)
        True
        >>> signalFrequency(4)
        False

    Raises:
        없음.
    """
    return occurrenceCount >= MIN_FREQUENCY


def signalCorporateDispersion(stockCodes: list[str]) -> bool:
    """Args:
        stockCodes: 그룹에서 관측된 종목코드 리스트 (중복 허용).

    Returns:
        고유 종목 수가 ``MIN_CORPORATE_DISPERSION`` (=3) 이상이면 True.
        빈 문자열은 unknown 으로 취급, dispersion 에서 제외.

    Example:
        >>> signalCorporateDispersion(["005930", "000660", "035720"])
        True
        >>> signalCorporateDispersion(["005930", "005930", ""])
        False

    Raises:
        없음.
    """
    unique = {c for c in (stockCodes or []) if c}
    return len(unique) >= MIN_CORPORATE_DISPERSION


def signalKorNameMatch(accountNm: str, standardAccounts: dict[str, dict]) -> tuple[str | None, float]:
    """후보 accountNm 과 standardAccounts.korName 중 best Levenshtein 매칭.

    Args:
        accountNm: 후보 한글 계정명.
        standardAccounts: ``{snakeId: {"korName": str, ...}, ...}`` dict.

    Returns:
        (snakeId, score) — score 가 ``KOR_MATCH_THRESHOLD`` (=0.85) 미만이면
        snakeId 는 None. 빈 입력은 (None, 0.0).

    Example:
        >>> sa = {"other_financial_assets": {"korName": "기타금융자산"}}
        >>> snake, score = signalKorNameMatch("기타의금융자산", sa)
        >>> snake
        'other_financial_assets'
        >>> round(score, 2) >= 0.85
        True

    Raises:
        없음.
    """
    if not accountNm or not standardAccounts:
        return None, 0.0
    needle = _normalizeKor(accountNm)
    needleTail = needle[-SUFFIX_TAIL_CHARS:] if len(needle) >= SUFFIX_TAIL_CHARS else needle
    bestId: str | None = None
    bestScore = 0.0
    for snakeId, meta in standardAccounts.items():
        korName = (meta or {}).get("korName", "")
        candidate = _normalizeKor(korName)
        if not candidate:
            continue
        score = _ratio(needle, candidate)
        # 액션 접미 가드 — 자산/처분손실/감소/증가/평가 등 의미를 결정짓는 끝 N 자
        # 가 다르면 점수 페널티. "자산 처분손실" 이 "자산" 으로 매핑되는 환각 차단.
        candidateTail = candidate[-SUFFIX_TAIL_CHARS:] if len(candidate) >= SUFFIX_TAIL_CHARS else candidate
        if needleTail != candidateTail:
            score *= SUFFIX_MISMATCH_PENALTY
        if score > bestScore:
            bestScore = score
            bestId = snakeId
    if bestScore < KOR_MATCH_THRESHOLD:
        return None, bestScore
    return bestId, bestScore


def signalIfrsSynonym(accountId: str, accountNm: str, mappings: dict[str, str]) -> str | None:
    """accountId 또는 정규화된 accountNm 이 mappings 에 직 hit 여부.

    Args:
        accountId: DART account_id (보통 ``-표준계정코드 미사용-``).
        accountNm: 한글 계정명.
        mappings: ``accountMappings.json`` 의 ``mappings`` dict (key=한글명/ID,
            value=snakeId).

    Returns:
        매핑된 snakeId 또는 None.

    Example:
        >>> mp = {"자산총계": "total_assets"}
        >>> signalIfrsSynonym("", "자산총계", mp)
        'total_assets'
        >>> signalIfrsSynonym("", "없는계정", mp) is None
        True

    Raises:
        없음.
    """
    if mappings:
        if accountId and accountId in mappings:
            return mappings[accountId]
        if accountNm and accountNm in mappings:
            return mappings[accountNm]
        normalized = _normalizeKor(accountNm)
        if normalized and normalized in mappings:
            return mappings[normalized]
    return None


def signalTypoReject(accountNm: str, standardAccounts: dict[str, dict]) -> tuple[bool, str | None]:
    """1 자모 차이의 표준 korName 이 있으면 *거부* 플래그.

    완전 일치는 typo 가 아니므로 거부하지 않는다 (S4 가 처리).

    Args:
        accountNm: 후보 한글 계정명.
        standardAccounts: ``{snakeId: {"korName": str}, ...}``.

    Returns:
        (rejected, suggestedFix) — rejected 가 True 면 suggestedFix 는 가장
        가까운 standardAccounts.korName (또는 의심 부분).

    Example:
        >>> sa = {"controlling_equity": {"korName": "지배기업소유주지분"}}
        >>> signalTypoReject("지배지업소유주지분", sa)
        (True, '지배기업소유주지분')
        >>> signalTypoReject("자산총계", sa)
        (False, None)

    Raises:
        없음.
    """
    if not accountNm or not standardAccounts:
        return False, None
    for meta in standardAccounts.values():
        korName = (meta or {}).get("korName", "")
        if not korName or korName == accountNm:
            continue
        distance = _jamoDistance(accountNm, korName)
        if 0 < distance <= TYPO_JAMO_DISTANCE:
            return True, korName
    return False, None


def evaluate(
    accountId: str,
    accountNm: str,
    occurrenceCount: int,
    stockCodes: list[str],
    standardAccounts: dict[str, dict],
    mappings: dict[str, str],
) -> SignalResult:
    """단일 그룹에 5 신호를 모두 적용해 합성.

    Args:
        accountId: DART account_id.
        accountNm: 한글 계정명.
        occurrenceCount: 그룹의 총 관측 행 수.
        stockCodes: 관측된 종목코드 리스트 (중복 허용).
        standardAccounts: accountMappings.json 의 standardAccounts.
        mappings: accountMappings.json 의 mappings (한글명→snakeId).

    Returns:
        ``SignalResult`` — autoEligible 합성 + suggestedSnakeId.

    Example:
        >>> sa = {"other_financial_assets": {"korName": "기타금융자산"}}
        >>> r = evaluate("", "기타의금융자산", 14,
        ...              ["005930", "000660", "035720"], sa, {})
        >>> r.autoEligible
        True
        >>> r.suggestedSnakeId
        'other_financial_assets'

    Raises:
        없음.
    """
    s1 = signalFrequency(occurrenceCount)
    s2 = signalCorporateDispersion(stockCodes)
    s4Snake = signalIfrsSynonym(accountId, accountNm, mappings)
    s3Snake, s3Score = signalKorNameMatch(accountNm, standardAccounts)
    s5Reject, s5Fix = signalTypoReject(accountNm, standardAccounts)

    suggested: str | None
    if s4Snake is not None:
        suggested = s4Snake
    elif s3Snake is not None:
        suggested = s3Snake
    else:
        suggested = None

    autoEligible = bool(s1 and s2 and (s3Snake is not None or s4Snake is not None) and not s5Reject)

    return SignalResult(
        accountId=accountId,
        accountNm=accountNm,
        occurrenceCount=occurrenceCount,
        corporateDispersion=len({c for c in stockCodes if c}),
        s1Frequency=s1,
        s2Dispersion=s2,
        s3KorMatchScore=s3Score,
        s3KorMatchSnakeId=s3Snake,
        s4IfrsSynonymSnakeId=s4Snake,
        s5TypoSuspect=s5Reject,
        s5SuggestedFix=s5Fix,
        autoEligible=autoEligible,
        suggestedSnakeId=suggested,
        confidence=s3Score,
    )
