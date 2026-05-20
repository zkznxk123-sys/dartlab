"""미커버 한글 → 사전 매핑 추천 (hash 기반 후보 top-k).

`operation.mappingRefresh` 의 Step 3 (SA korName substring 후보 추출) 의
*보조 진전 layer*. SA substring 결과에 *추가 신호* 로 top-k 후보 + confidence
제공. **자동 매핑 X — 운영자 검토 보조만**.

본 모듈은 *후보 추천* 만 반환. 호출자가 confidence 보고 *사람 검토 후 박기*.
직접 `accountMappings.json` 수정 권한 없음 — `mappingPromote.py` 만.

알고리즘:
    V7-style 4-region characteristic hash (256-bit) + MinHash (64-hash) + cluster
    weight + margin/overlap gate. 시도 폴더 실증 (V1~V10) 결과 leave-out
    92.9% (group HH) / 카카오 None 실증 AUTO 24% (정답 ~43%, 부분 정답 ~43%,
    환각 ~14%) 검증 기반.

참조:
    - 시도 코드: `tests/_attempts/semantic/accountMapperHashEval{V7,V10}.py`
    - 운영 SSOT: `src/dartlab/skills/specs/operation/mappingRefresh.md`
    - 사전: `src/dartlab/reference/data/accountMappings.json`
"""

from __future__ import annotations

import hashlib
from collections import Counter
from dataclasses import dataclass

from dartlab.core.utils.labels import _loadAccountMappings

_JAMO_BASE = ord("가")
_NUM_MH = 64
_DEFAULT_WEIGHTS = (1, 2, 2, 0)  # (jamo, char, bigram, random)


@dataclass(frozen=True, slots=True)
class Candidate:
    """미커버 한글 매칭 후보.

    Attributes:
        snakeId: 사전 snakeId.
        score: weighted hamming - minhash bonus - cluster bonus. 낮을수록 가깝다.
        hitKor: 사전 안 매칭된 한글 변형.
        confidence: 'high' | 'medium' | 'low'.
        overlap: 입력 ↔ hitKor bigram set 최소 비율 (0.0 ~ 1.0).
    """

    snakeId: str
    score: float
    hitKor: str
    confidence: str
    overlap: float


# === 4-region characteristic + MinHash helpers ===


def _decomposeJamo(c: str):
    """한글 1 글자 → (cho, jung, jong) jamo tuple. 한자/영문은 빈 tuple."""
    if not ("가" <= c <= "힣"):
        return ()
    i = ord(c) - _JAMO_BASE
    cho = i // 588
    jung = (i % 588) // 28
    jong = i % 28
    return (cho, jung, jong) if jong else (cho, jung)


def _characteristicRegions(s: str) -> tuple[int, int, int, int]:
    """4-region 256-bit characteristic hash.

    Region 0 (bits 0..63): jamo bloom — 한국어 음운 공유 (자/사 = ㅏ ㅈ 공유).
    Region 1 (bits 64..127): char bloom — 한글자 단위 공유 (자기/자사 = '자' 공유).
    Region 2 (bits 128..191): bigram bloom — 2-글자 단위 (유상/유상증 = '유상' 공유).
    Region 3 (bits 192..255): blake-like random — 동음이의 변별 (식별만).

    Args:
        s: 입력 한글 (공백 제거 후 처리).

    Returns:
        (r0, r1, r2, r3) — region 별 64-bit int.
    """
    s = s.replace(" ", "")
    r0 = r1 = r2 = r3 = 0
    for c in s:
        for j in _decomposeJamo(c):
            r0 |= 1 << (int(hashlib.md5(f"jamo{j}".encode()).hexdigest()[:8], 16) % 64)
    for c in s:
        r1 |= 1 << (int(hashlib.md5(f"char{c}".encode()).hexdigest()[:8], 16) % 64)
    for i in range(len(s) - 1):
        r2 |= 1 << (int(hashlib.md5(f"bg{s[i : i + 2]}".encode()).hexdigest()[:8], 16) % 64)
    h = int(hashlib.md5(s.encode()).hexdigest()[:16], 16)
    for i in range(8):
        r3 |= 1 << ((h >> (i * 4)) & 63)
    return (r0, r1, r2, r3)


def _popcount(x: int) -> int:
    return bin(x).count("1")


def _weightedDistance(a, b, weights=_DEFAULT_WEIGHTS) -> int:
    """region 별 Hamming distance 가중 합. weights=(1,2,2,0) 가 semantic 신호 우선."""
    return sum(_popcount(a[i] ^ b[i]) * weights[i] for i in range(4))


def _minhash(s: str) -> tuple[int, ...]:
    """2-gram MinHash 64-hash signature.

    Args:
        s: 입력 한글.

    Returns:
        64-tuple of uint32 min hash values.
    """
    s = s.replace(" ", "")
    g = {s[i : i + 2] for i in range(len(s) - 1)} or {s}
    hs = [2**32 - 1] * _NUM_MH
    for ng in g:
        for i in range(_NUM_MH):
            h = int(hashlib.md5((str(i) + ng).encode()).hexdigest()[:8], 16)
            if h < hs[i]:
                hs[i] = h
    return tuple(hs)


def _mhSim(a, b) -> float:
    """MinHash Jaccard estimate."""
    return sum(1 for x, y in zip(a, b) if x == y) / len(a)


def _bigramOverlap(a: str, b: str) -> float:
    """min(|A∩B| / |A|, |A∩B| / |B|) — bigram set 최소 비율."""
    a = a.replace(" ", "")
    b = b.replace(" ", "")
    ga = {a[i : i + 2] for i in range(len(a) - 1)} or {a}
    gb = {b[i : i + 2] for i in range(len(b) - 1)} or {b}
    inter = ga & gb
    denom = min(len(ga), len(gb))
    return len(inter) / denom if denom else 0.0


# === Module-level lazy cache ===


_dictCache: list[dict] | None = None


def _loadDict() -> list[dict]:
    """`accountMappings.json` 로드 + 한글 매핑 hash precompute. lazy singleton.

    Returns:
        list of dict {kor, snake, hash, mh, sj, cs}. 영문 ID 매핑 제외.

    Notes:
        - 첫 호출 ~2~3 초 (33,221 한글 × hash 계산)
        - 이후 module-level cache 재사용
        - 사전 갱신 시 `_invalidate()` 호출 필수
    """
    global _dictCache
    if _dictCache is not None:
        return _dictCache
    data = _loadAccountMappings()
    mappings = data.get("mappings", {})
    sa = data.get("standardAccounts", {})
    korItems = [(k, v) for k, v in mappings.items() if not any("a" <= c <= "z" or "A" <= c <= "Z" for c in k)]
    clusterSize = Counter(v for _, v in korItems)
    cache = []
    for k, v in korItems:
        cache.append(
            {
                "kor": k,
                "snake": v,
                "hash": _characteristicRegions(k),
                "mh": _minhash(k),
                "sj": sa.get(v, {}).get("sj", ""),
                "cs": clusterSize[v],
            }
        )
    _dictCache = cache
    return _dictCache


def _invalidate() -> None:
    """사전 갱신 시 hash 캐시 무효화. `AccountMapper.release()` 와 동행 호출."""
    global _dictCache
    _dictCache = None


# === Public API ===


def recommend(
    accountNm: str,
    sj: str = "",
    topK: int = 3,
    *,
    marginMin: int = 10,
    overlapMin: float = 0.5,
) -> list[Candidate]:
    """미커버 한글 → 사전 매핑 추천 top-k.

    **자동 매핑 X — 후보 추천 보조만**. 호출자가 ``confidence`` 보고 운영자 검토 결정.

    Args:
        accountNm: 미커버 한글 계정명 (예: ``"장기매도가능증권의 처분"``).
        sj: ``sj_div`` (BS/IS/CF/CIS/SCE). 비어 있으면 전체 사전 검색.
        topK: 반환 후보 수.
        marginMin: top-1/top-2 distance margin 임계. 통과 시 confidence 강화.
        overlapMin: bigram overlap 임계. 통과 시 confidence 강화.

    Returns:
        Top-k Candidate 리스트, score 오름차순.

    Example:
        >>> cands = recommend("장기매도가능증권의 처분", sj="CF")
        >>> cands[0].snakeId
        'disposal_of_available_for_sale_securities'
        >>> cands[0].confidence
        'high'

    Notes:
        confidence 분류 (V10 카카오 None 29 실증 기반):
            - ``high`` — margin ≥ marginMin AND overlap ≥ overlapMin (정답률 ~43%, 부분 정답 ~43%)
            - ``medium`` — 둘 중 한 가드만 통과
            - ``low`` — 둘 다 미통과 (사람 의미 검토 strict 필요)
    """
    if not accountNm:
        return []
    cache = _loadDict()
    inputH = _characteristicRegions(accountNm)
    inputMh = _minhash(accountNm)
    candidates = []
    for d in cache:
        if sj and d["sj"] != sj:
            continue
        h = _weightedDistance(inputH, d["hash"])
        m = _mhSim(inputMh, d["mh"])
        s = h - m * 50 - min(d["cs"], 20) * 0.5
        candidates.append((s, d["snake"], d["kor"]))
    if not candidates:
        return []
    candidates.sort()
    topRaw = candidates[:topK]
    # confidence 분류 (top-1 기준; top-2 부재 시 margin = inf)
    if len(candidates) >= 2:
        margin = candidates[1][0] - candidates[0][0]
    else:
        margin = float("inf")
    result = []
    for s, snake, hitKor in topRaw:
        overlap = _bigramOverlap(accountNm, hitKor)
        marginOk = margin >= marginMin
        overlapOk = overlap >= overlapMin
        if marginOk and overlapOk:
            conf = "high"
        elif marginOk or overlapOk:
            conf = "medium"
        else:
            conf = "low"
        result.append(
            Candidate(
                snakeId=snake,
                score=s,
                hitKor=hitKor,
                confidence=conf,
                overlap=overlap,
            )
        )
    return result
