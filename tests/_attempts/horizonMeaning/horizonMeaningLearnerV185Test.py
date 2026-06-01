"""Horizon Meaning Learner V185 - polarity-role certificate on open held-out.

아이디어:
    V184 는 accountMappings open held-out harness 를 만들었고, V183 의 4/4 closed probe 가 일반화 증거가
    아님을 확인했다. V185 는 같은 held-out split 위에서 첫 구조적 개선을 검증한다.

    새 메커니즘은 polarity-role certificate 다. query alias 와 train candidate aliases 에서 일반 finance
    구조 슬롯을 추출한다. 슬롯은 `flow:in/out`, `delta:increase/decrease/net`,
    `transaction:acquire/dispose/issue/redeem`, `valuation:gain/loss`,
    `statement:cashflow/balance/income`, `cf:operating/investing/financing`,
    `object:debt/equity/derivative/lease/subsidiary/...` 계열이다.

    각 snakeId 는 held-out alias 를 제외한 train aliases 로만 slot profile 을 만든다. scoring 은 V184 의
    surface/hash baseline 을 그대로 출력하고, 그 위에 certificate score 를 별도로 출력한다. 즉 개선 여부는
    같은 held-out, 같은 후보 universe, 같은 train leakage=0 조건에서 비교된다.

    이 실험은 특정 11개 probe 나 forbidden pair 를 모르며, 일반 방향성/역할 슬롯만 사용한다. 목표는
    "경험을 비교 가능한 증거 객체로 만든다"는 horizonMeaning 아이디어가 open held-out 에서 surface/hash
    baseline 을 실제로 올리는지 확인하는 것이다.

실행 코드:
    uv run python -X utf8 -m py_compile tests/_attempts/horizonMeaning/horizonMeaningLearnerV185Test.py
    uv run python -X utf8 tests/_attempts/horizonMeaning/horizonMeaningLearnerV185Test.py

검증 기준:
    - held-out query surface 는 train candidate alias 에 없어야 한다.
    - 후보는 평가 11개가 아니라 accountMappings 의 수천 canonical snakeId 여야 한다.
    - baseline 과 certificate 의 no-sj/with-sj Top1/Top5/MRR 를 같은 split 에서 비교한다.
    - certificateWithSj MRR 과 Top1/Top5 가 V184 baselineWithSj 보다 올라야 개념 신호로 본다.

결과:
    py_compile 통과.

    기본 320 held-out:
        heldout=320, trainEntries=17,340, snakes=4,840, leakedAliases=0
        avgCandidateSnakes noSj=1,436.9, withSj=1,459.6
        baselineNoSj: Top1=104/320, Top3=184/320, Top5=214/320, Top10=247/320, Miss=2/320, MRR=0.4858
        baselineWithSj: Top1=121/320, Top3=203/320, Top5=229/320, Top10=262/320, Miss=2/320, MRR=0.5318
        certificateNoSj: Top1=107/320, Top3=183/320, Top5=224/320, Top10=250/320, Miss=2/320, MRR=0.4943
        certificateWithSj: Top1=126/320, Top3=208/320, Top5=237/320, Top10=264/320, Miss=2/320, MRR=0.5467
        withSj rank movement: improved=74, same=220, worsened=26

    HELDOUT_LIMIT=600, 사실상 eligible 전체에 가까운 497 held-out:
        heldout=497, trainEntries=17,194, snakes=4,840, leakedAliases=0
        avgCandidateSnakes noSj=1,446.1, withSj=1,459.4
        baselineNoSj: Top1=167/497, Top3=295/497, Top5=342/497, Top10=386/497, Miss=2/497, MRR=0.4944
        baselineWithSj: Top1=192/497, Top3=319/497, Top5=359/497, Top10=409/497, Miss=2/497, MRR=0.5392
        certificateNoSj: Top1=172/497, Top3=294/497, Top5=354/497, Top10=394/497, Miss=2/497, MRR=0.5030
        certificateWithSj: Top1=200/497, Top3=327/497, Top5=372/497, Top10=414/497, Miss=2/497, MRR=0.5529
        withSj rank movement: improved=116, same=342, worsened=39

    개선 신호:
        상각후원가금융자산 감소/순감소증가, 파생상품 현금유출, 비지배지분 유상감자처럼 방향/역할이 있는
        query 에서 rank 가 다수 개선됐다.

    남은 실패:
        `사업매각으로인한현금유입액 -> gains_on_business_combination` 은 cashflow 표면이 너무 강해 BS gold 로
        못 넘어간다. `신종자본증권발행 -> issue_of_hybrid_bond` 는 bonds/hybrid_bond family 안의
        canonical hierarchy 를 구분하지 못한다. `리스설비 -> leased_assets` 는 lease/income/equipment 역할이
        충돌한다.

결론:
    성공/작은 구조 개선. V185 는 open held-out 에서 V184 surface/hash baseline 을 실제로 올렸다.
    절대 성능은 아직 낮지만, polarity-role certificate 가 11개 closed probe 가 아닌 497 held-out 에서
    MRR 0.5392 -> 0.5529, Top1 192 -> 200, Top5 359 -> 372 로 개선했다.

    의미 있는 점은 "경험을 비교 가능한 증거 객체로 뭉친다"는 방향이 open 평가에서 처음으로 수치 개선을
    냈다는 것이다. 하지만 아직 규칙 기반 slot 이며 corpus 경험을 직접 학습한 것은 아니다.

    다음 실험은 slot rule 을 더 늘리는 것이 아니라, train alias/corpus 문맥에서 canonical hierarchy 와
    role transition 을 자동 학습해야 한다. 특히 `bonds -> hybrid_bond -> issue_of_hybrid_bond`,
    `cashflow surface -> BS/IS canonical`, `inflow/outflow vs gain/loss` 를 graph path certificate 로 분리해야 한다.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
import time
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
MAPPING_PATH = ROOT / "src" / "dartlab" / "reference" / "data" / "accountMappings.json"

HELDOUT_LIMIT = int(os.environ.get("DARTLAB_HORIZON_V185_HELDOUT_LIMIT", "320"))
MIN_CLUSTER_SIZE = int(os.environ.get("DARTLAB_HORIZON_V185_MIN_CLUSTER_SIZE", "4"))
MAX_TRAIN_ALIASES_PER_SNAKE = int(os.environ.get("DARTLAB_HORIZON_V185_MAX_TRAIN_ALIASES_PER_SNAKE", "80"))
POOL_LIMIT = int(os.environ.get("DARTLAB_HORIZON_V185_POOL_LIMIT", "5200"))
POSTING_ROW_LIMIT = int(os.environ.get("DARTLAB_HORIZON_V185_POSTING_ROW_LIMIT", "2600"))
TOP_K = int(os.environ.get("DARTLAB_HORIZON_V185_TOP_K", "10"))
NUM_MH = int(os.environ.get("DARTLAB_HORIZON_V185_NUM_MH", "32"))

HANGUL_START = 0xAC00
HANGUL_END = 0xD7A3
JAMO_BASE = 0xAC00
SPACE_RE = re.compile(r"\s+")

SLOT_RULES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("flow:in", ("유입", "수입", "입금", "수취", "회수")),
    ("flow:out", ("유출", "지출", "지급", "상환", "납부")),
    ("delta:increase", ("증가", "증대", "증액", "확대")),
    ("delta:decrease", ("감소", "감액", "축소", "차감")),
    ("delta:net", ("증감", "변동", "순증감", "순증가", "순감소")),
    ("transaction:acquire", ("취득", "매입", "인수", "매수")),
    ("transaction:dispose", ("처분", "매각", "양도", "제거")),
    ("transaction:issue", ("발행", "유상증자", "신주")),
    ("transaction:redeem", ("상환", "소각", "감자")),
    ("valuation:gain", ("이익", "수익", "환입", "차익")),
    ("valuation:loss", ("손실", "비용", "손상", "상각", "차손")),
    ("statement:cashflow", ("현금흐름", "현금유입", "현금유출", "영업활동", "투자활동", "재무활동")),
    ("statement:balance", ("자산", "부채", "자본", "채권", "채무", "재고", "유형", "무형")),
    ("statement:income", ("매출", "수익", "비용", "손익", "이익", "원가", "판관")),
    ("cf:operating", ("영업활동",)),
    ("cf:investing", ("투자활동",)),
    ("cf:financing", ("재무활동",)),
    ("object:cash", ("현금", "예금")),
    ("object:receivable", ("채권", "매출채권", "미수", "수취")),
    ("object:payable", ("채무", "매입채무", "미지급")),
    ("object:debt", ("차입", "사채", "채무증권", "전환사채", "신종자본증권")),
    ("object:lease", ("리스",)),
    ("object:derivative", ("파생",)),
    ("object:equity", ("자본", "지분", "주식", "주주", "신주", "자기주")),
    ("object:subsidiary", ("종속기업", "종속회사", "연결범위")),
    ("object:associate", ("관계기업", "공동기업")),
    ("object:financialAsset", ("금융자산", "상각후원가", "공정가치", "매도가능")),
    ("object:provision", ("충당", "충당부채")),
    ("object:tax", ("법인세", "세금")),
    ("object:inventory", ("재고", "제품", "상품", "완성")),
    ("object:tangible", ("유형자산", "설비", "건물", "토지")),
    ("object:intangible", ("무형자산", "영업권", "개발비", "라이선스")),
)

EXCLUSIVE_SLOT_GROUPS: tuple[tuple[str, ...], ...] = (
    ("flow:in", "flow:out"),
    ("delta:increase", "delta:decrease"),
    ("transaction:acquire", "transaction:dispose"),
    ("transaction:issue", "transaction:redeem"),
    ("valuation:gain", "valuation:loss"),
    ("cf:operating", "cf:investing", "cf:financing"),
)


@dataclass(frozen=True)
class AliasEntry:
    alias: str
    snake: str
    sj: str
    clusterSize: int
    regions: tuple[int, int, int, int]
    mh: tuple[int, ...]
    bigrams: frozenset[str]
    trigrams: frozenset[str]
    chars: frozenset[str]
    slots: Counter[str]


@dataclass(frozen=True)
class HeldoutCase:
    alias: str
    snake: str
    sj: str
    trainSize: int
    clusterSize: int


@dataclass(frozen=True)
class SnakeProfile:
    snake: str
    sj: str
    slots: Counter[str]
    aliasCount: int


def stableHashInt(value: str) -> int:
    return int(hashlib.blake2b(value.encode("utf-8"), digest_size=8).hexdigest(), 16)


def hasHangul(value: str) -> bool:
    return any(HANGUL_START <= ord(ch) <= HANGUL_END for ch in value)


def cleanSurface(value: object) -> str:
    text = "" if value is None else str(value)
    text = SPACE_RE.sub("", text)
    out = []
    for ch in text:
        code = ord(ch)
        if HANGUL_START <= code <= HANGUL_END or ch.isascii() and ch.isalnum():
            out.append(ch)
    return "".join(out)


def usefulAlias(value: str) -> bool:
    if not value or not hasHangul(value):
        return False
    if len(value) < 3 or len(value) > 48:
        return False
    if sum(1 for ch in value if HANGUL_START <= ord(ch) <= HANGUL_END) < 2:
        return False
    return True


def ngrams(value: str, n: int) -> frozenset[str]:
    if len(value) < n:
        return frozenset({value}) if value else frozenset()
    return frozenset(value[index : index + n] for index in range(len(value) - n + 1))


def structuralSlots(value: str, sj: str = "") -> Counter[str]:
    slots: Counter[str] = Counter()
    for slot, terms in SLOT_RULES:
        for term in terms:
            if term in value:
                slots[slot] += 1
                slots[f"term:{term}"] += 1
    if sj:
        slots[f"sj:{sj}"] += 2
    if "현금" in value and ("유입" in value or "유출" in value or "흐름" in value):
        slots["statement:cashflow"] += 2
    if ("증가" in value or "감소" in value or "증감" in value) and ("현금" in value or "흐름" in value):
        slots["statement:cashflow"] += 1
    if "순" in value and ("증가" in value or "감소" in value or "증감" in value):
        slots["delta:net"] += 1
    return slots


def decomposeJamo(ch: str) -> tuple[int, ...]:
    code = ord(ch)
    if not (HANGUL_START <= code <= HANGUL_END):
        return ()
    offset = code - JAMO_BASE
    cho = offset // 588
    jung = (offset % 588) // 28
    jong = offset % 28
    return (cho, jung, jong) if jong else (cho, jung)


def bitIndex(namespace: str, value: object) -> int:
    return int(hashlib.md5(f"{namespace}:{value}".encode("utf-8")).hexdigest()[:8], 16) % 64


def characteristicRegions(value: str) -> tuple[int, int, int, int]:
    r0 = r1 = r2 = r3 = 0
    for ch in value:
        for jamo in decomposeJamo(ch):
            r0 |= 1 << bitIndex("jamo", jamo)
    for ch in value:
        r1 |= 1 << bitIndex("char", ch)
    for gram in ngrams(value, 2):
        r2 |= 1 << bitIndex("bg", gram)
    raw = int(hashlib.blake2b(value.encode("utf-8"), digest_size=8).hexdigest(), 16)
    for index in range(8):
        r3 |= 1 << ((raw >> (index * 4)) & 63)
    return r0, r1, r2, r3


def popcount(value: int) -> int:
    return value.bit_count()


def weightedDistance(left: tuple[int, int, int, int], right: tuple[int, int, int, int]) -> int:
    weights = (1, 2, 2, 0)
    return sum(popcount(left[index] ^ right[index]) * weights[index] for index in range(4))


def minhash(value: str) -> tuple[int, ...]:
    grams = ngrams(value, 2) or frozenset({value})
    rows = [2**32 - 1] * NUM_MH
    for gram in grams:
        for index in range(NUM_MH):
            digest = int(hashlib.md5(f"{index}:{gram}".encode("utf-8")).hexdigest()[:8], 16)
            if digest < rows[index]:
                rows[index] = digest
    return tuple(rows)


def mhSim(left: tuple[int, ...], right: tuple[int, ...]) -> float:
    if not left or not right:
        return 0.0
    return sum(1 for lval, rval in zip(left, right) if lval == rval) / min(len(left), len(right))


def overlap(left: frozenset[str], right: frozenset[str]) -> float:
    denom = min(len(left), len(right))
    if denom <= 0:
        return 0.0
    return len(left & right) / denom


def containMass(query: str, candidate: str) -> float:
    if not query or not candidate:
        return 0.0
    if query in candidate or candidate in query:
        return min(len(query), len(candidate)) / max(len(query), len(candidate))
    return 0.0


def loadClusters() -> tuple[dict[str, list[str]], dict[str, str]]:
    raw = json.loads(MAPPING_PATH.read_text(encoding="utf-8"))
    mappings: dict[str, str] = raw.get("mappings", {})
    standard: dict[str, dict] = raw.get("standardAccounts", {})
    aliasToSnakes: dict[str, set[str]] = defaultdict(set)
    for alias, snake in mappings.items():
        clean = cleanSurface(alias)
        if usefulAlias(clean):
            aliasToSnakes[clean].add(str(snake))
    clusters: dict[str, list[str]] = defaultdict(list)
    for alias, snakes in aliasToSnakes.items():
        if len(snakes) != 1:
            continue
        snake = next(iter(snakes))
        clusters[snake].append(alias)
    normalized = {
        snake: sorted(set(aliases), key=lambda item: (stableHashInt(f"{snake}:{item}"), item))
        for snake, aliases in clusters.items()
    }
    sjBySnake = {snake: str(meta.get("sj", "")) for snake, meta in standard.items() if isinstance(meta, dict)}
    return normalized, sjBySnake


def buildSplit() -> tuple[list[HeldoutCase], list[AliasEntry], Counter[str], dict[str, SnakeProfile]]:
    clusters, sjBySnake = loadClusters()
    heldout: list[HeldoutCase] = []
    heldoutAliases: set[str] = set()
    eligible = [
        (snake, aliases)
        for snake, aliases in clusters.items()
        if len(aliases) >= MIN_CLUSTER_SIZE and sjBySnake.get(snake, "")
    ]
    eligible.sort(key=lambda row: stableHashInt(row[0]))
    for snake, aliases in eligible:
        candidates = [alias for alias in aliases if 4 <= len(alias) <= 34]
        if not candidates:
            continue
        alias = sorted(candidates, key=lambda item: stableHashInt(f"heldout:{snake}:{item}"))[0]
        trainSize = len([item for item in aliases if item != alias])
        if trainSize < MIN_CLUSTER_SIZE - 1:
            continue
        heldout.append(
            HeldoutCase(
                alias=alias,
                snake=snake,
                sj=sjBySnake.get(snake, ""),
                trainSize=trainSize,
                clusterSize=len(aliases),
            )
        )
        heldoutAliases.add(alias)
        if len(heldout) >= HELDOUT_LIMIT:
            break

    clusterSizes = Counter({snake: len(aliases) for snake, aliases in clusters.items()})
    entries: list[AliasEntry] = []
    for snake, aliases in clusters.items():
        trainAliases = [alias for alias in aliases if alias not in heldoutAliases]
        trainAliases = sorted(trainAliases, key=lambda item: (stableHashInt(f"train:{snake}:{item}"), item))
        for alias in trainAliases[:MAX_TRAIN_ALIASES_PER_SNAKE]:
            entries.append(
                AliasEntry(
                    alias=alias,
                    snake=snake,
                    sj=sjBySnake.get(snake, ""),
                    clusterSize=clusterSizes[snake],
                    regions=characteristicRegions(alias),
                    mh=minhash(alias),
                    bigrams=ngrams(alias, 2),
                    trigrams=ngrams(alias, 3),
                    chars=frozenset(alias),
                    slots=structuralSlots(alias, sjBySnake.get(snake, "")),
                )
            )
    profileSlots: dict[str, Counter[str]] = defaultdict(Counter)
    profileCounts: Counter[str] = Counter()
    for entry in entries:
        profileCounts[entry.snake] += 1
        for slot, value in entry.slots.items():
            profileSlots[entry.snake][slot] += max(0.0, float(value))
    profiles = {
        snake: SnakeProfile(
            snake=snake,
            sj=sjBySnake.get(snake, ""),
            slots=Counter(dict(slots.most_common(64))),
            aliasCount=profileCounts[snake],
        )
        for snake, slots in profileSlots.items()
    }
    return heldout, entries, clusterSizes, profiles


def buildPostings(entries: list[AliasEntry]) -> tuple[dict[str, tuple[int, ...]], dict[str, tuple[int, ...]]]:
    bigramRows: dict[str, list[int]] = defaultdict(list)
    charRows: dict[str, list[int]] = defaultdict(list)
    for index, entry in enumerate(entries):
        for gram in entry.bigrams:
            bigramRows[gram].append(index)
        for ch in entry.chars:
            charRows[ch].append(index)
    return (
        {key: tuple(rows[:POSTING_ROW_LIMIT]) for key, rows in bigramRows.items()},
        {key: tuple(rows[:POSTING_ROW_LIMIT]) for key, rows in charRows.items()},
    )


def sjCompatible(querySj: str, candidateSj: str) -> bool:
    if not querySj or querySj == "COMMON":
        return True
    return candidateSj in {"", "COMMON", querySj}


def candidatePool(
    query: str,
    querySj: str,
    entries: list[AliasEntry],
    bigramPostings: dict[str, tuple[int, ...]],
    charPostings: dict[str, tuple[int, ...]],
    *,
    withSj: bool,
) -> Counter[int]:
    votes: Counter[int] = Counter()
    for gram in ngrams(query, 2):
        for index in bigramPostings.get(gram, ()):
            if not withSj or sjCompatible(querySj, entries[index].sj):
                votes[index] += 4
    for ch in query:
        for index in charPostings.get(ch, ()):
            if not withSj or sjCompatible(querySj, entries[index].sj):
                votes[index] += 1
    if len(votes) < 20:
        for index, entry in enumerate(entries):
            if not withSj or sjCompatible(querySj, entry.sj):
                votes[index] += 0
    return Counter(dict(votes.most_common(POOL_LIMIT)))


def entryScore(
    query: str,
    qRegions: tuple[int, int, int, int],
    qMh: tuple[int, ...],
    qBigrams: frozenset[str],
    qTrigrams: frozenset[str],
    entry: AliasEntry,
    vote: float,
) -> float:
    hamming = weightedDistance(qRegions, entry.regions)
    mhBonus = mhSim(qMh, entry.mh) * 46.0
    bigramBonus = overlap(qBigrams, entry.bigrams) * 24.0
    trigramBonus = overlap(qTrigrams, entry.trigrams) * 16.0
    contains = containMass(query, entry.alias) * 10.0
    clusterBonus = min(18.0, math.log1p(max(0, entry.clusterSize)) * 2.0)
    voteBonus = math.log1p(max(0.0, vote)) * 1.6
    lengthPenalty = abs(len(query) - len(entry.alias)) * 0.55
    return hamming + lengthPenalty - mhBonus - bigramBonus - trigramBonus - contains - clusterBonus - voteBonus


def structuralCertificateDelta(querySlots: Counter[str], entry: AliasEntry, profile: SnakeProfile | None) -> float:
    if not querySlots:
        return 0.0
    profileSlots = Counter()
    if profile is not None:
        profileSlots.update(profile.slots)
    candidateSlots = Counter(profileSlots)
    candidateSlots.update(entry.slots)

    reward = 0.0
    conflict = 0.0
    queryCore = {slot for slot in querySlots if not slot.startswith("term:") and not slot.startswith("sj:")}
    if not queryCore:
        return 0.0
    for slot in queryCore:
        if candidateSlots.get(slot, 0) > 0:
            reward += 3.6 + min(2.2, math.log1p(candidateSlots[slot]))
    for group in EXCLUSIVE_SLOT_GROUPS:
        present = [slot for slot in group if querySlots.get(slot, 0) > 0]
        if not present:
            continue
        expected = set(present)
        alternatives = set(group) - expected
        if any(candidateSlots.get(slot, 0) > 0 for slot in expected):
            reward += 4.0
        elif any(candidateSlots.get(slot, 0) > 0 for slot in alternatives):
            conflict += 10.0
        elif group[0].split(":", 1)[0] in {"flow", "delta", "transaction"}:
            conflict += 1.8
    if querySlots.get("statement:cashflow", 0) and candidateSlots.get("statement:cashflow", 0) <= 0:
        conflict += 4.8
    if (
        querySlots.get("statement:balance", 0)
        and candidateSlots.get("statement:cashflow", 0) > 0
        and candidateSlots.get("statement:balance", 0) <= 0
    ):
        conflict += 3.2
    if querySlots.get("statement:income", 0) and candidateSlots.get("statement:income", 0) <= 0:
        conflict += 2.4
    objectSlots = [slot for slot in queryCore if slot.startswith("object:")]
    if objectSlots:
        objectHits = sum(1 for slot in objectSlots if candidateSlots.get(slot, 0) > 0)
        reward += objectHits * 4.0
        if objectHits == 0:
            conflict += min(6.0, 2.0 + len(objectSlots) * 1.4)
    termHits = sum(1 for slot in querySlots if slot.startswith("term:") and candidateSlots.get(slot, 0) > 0)
    reward += min(6.0, termHits * 0.8)
    return conflict - reward


def rankCase(
    case: HeldoutCase,
    entries: list[AliasEntry],
    profiles: dict[str, SnakeProfile],
    bigramPostings: dict[str, tuple[int, ...]],
    charPostings: dict[str, tuple[int, ...]],
    *,
    withSj: bool,
    useCertificate: bool,
) -> tuple[int | None, tuple[tuple[str, float, str], ...], int]:
    query = case.alias
    qRegions = characteristicRegions(query)
    qMh = minhash(query)
    qBigrams = ngrams(query, 2)
    qTrigrams = ngrams(query, 3)
    qSlots = structuralSlots(query, case.sj)
    pool = candidatePool(query, case.sj, entries, bigramPostings, charPostings, withSj=withSj)
    best: dict[str, tuple[float, str]] = {}
    for index, vote in pool.items():
        entry = entries[index]
        score = entryScore(query, qRegions, qMh, qBigrams, qTrigrams, entry, vote)
        if useCertificate:
            score += structuralCertificateDelta(qSlots, entry, profiles.get(entry.snake))
        prior = best.get(entry.snake)
        if prior is None or score < prior[0]:
            best[entry.snake] = (score, entry.alias)
    rows = sorted(((snake, score, alias) for snake, (score, alias) in best.items()), key=lambda row: row[1])
    rank: int | None = None
    for index, (snake, _score, _alias) in enumerate(rows, start=1):
        if snake == case.snake:
            rank = index
            break
    return rank, tuple(rows[:TOP_K]), len(best)


def summarize(ranks: list[int | None]) -> dict[str, float]:
    total = len(ranks) or 1
    return {
        "top1": sum(1 for rank in ranks if rank == 1),
        "top3": sum(1 for rank in ranks if rank is not None and rank <= 3),
        "top5": sum(1 for rank in ranks if rank is not None and rank <= 5),
        "top10": sum(1 for rank in ranks if rank is not None and rank <= 10),
        "miss": sum(1 for rank in ranks if rank is None),
        "mrr": sum(0.0 if rank is None else 1.0 / rank for rank in ranks) / total,
    }


def fmtSummary(label: str, ranks: list[int | None]) -> str:
    row = summarize(ranks)
    total = len(ranks) or 1
    return (
        f"{label} Top1={int(row['top1'])}/{total} "
        f"Top3={int(row['top3'])}/{total} Top5={int(row['top5'])}/{total} "
        f"Top10={int(row['top10'])}/{total} Miss={int(row['miss'])}/{total} MRR={row['mrr']:.4f}"
    )


def main() -> None:
    started = time.perf_counter()
    heldout, entries, clusterSizes, profiles = buildSplit()
    leaked = sorted({case.alias for case in heldout} & {entry.alias for entry in entries})
    print("V185 accountMappings open held-out audit")
    print(
        f"heldout={len(heldout)} trainEntries={len(entries)} snakes={len(clusterSizes)} "
        f"eligibleClusters={sum(1 for _snake, size in clusterSizes.items() if size >= MIN_CLUSTER_SIZE)} leakedAliases={len(leaked)}"
    )
    if leaked:
        raise RuntimeError(f"held-out aliases leaked into train entries: {leaked[:5]}")
    bigramPostings, charPostings = buildPostings(entries)
    print(f"postings bigrams={len(bigramPostings)} chars={len(charPostings)}")

    baseRanksNoSj: list[int | None] = []
    baseRanksWithSj: list[int | None] = []
    certRanksNoSj: list[int | None] = []
    certRanksWithSj: list[int | None] = []
    wrongNoSj: list[tuple[HeldoutCase, int | None, tuple[tuple[str, float, str], ...], int]] = []
    wrongWithSj: list[tuple[HeldoutCase, int | None, tuple[tuple[str, float, str], ...], int]] = []
    poolSizesNoSj: list[int] = []
    poolSizesWithSj: list[int] = []
    improved = worsened = same = 0

    for case in heldout:
        baseNo, _baseRowsNo, candidateCountNo = rankCase(
            case, entries, profiles, bigramPostings, charPostings, withSj=False, useCertificate=False
        )
        baseSj, _baseRowsSj, candidateCountSj = rankCase(
            case, entries, profiles, bigramPostings, charPostings, withSj=True, useCertificate=False
        )
        rankNo, rowsNo, _candidateCountNo2 = rankCase(
            case, entries, profiles, bigramPostings, charPostings, withSj=False, useCertificate=True
        )
        rankSj, rowsSj, _candidateCountSj2 = rankCase(
            case, entries, profiles, bigramPostings, charPostings, withSj=True, useCertificate=True
        )
        baseRanksNoSj.append(baseNo)
        baseRanksWithSj.append(baseSj)
        certRanksNoSj.append(rankNo)
        certRanksWithSj.append(rankSj)
        poolSizesNoSj.append(candidateCountNo)
        poolSizesWithSj.append(candidateCountSj)
        baseValue = 999999 if baseSj is None else baseSj
        certValue = 999999 if rankSj is None else rankSj
        if certValue < baseValue:
            improved += 1
        elif certValue > baseValue:
            worsened += 1
        else:
            same += 1
        if rankNo != 1 and len(wrongNoSj) < 12:
            wrongNoSj.append((case, rankNo, rowsNo, candidateCountNo))
        if rankSj != 1 and len(wrongWithSj) < 12:
            wrongWithSj.append((case, rankSj, rowsSj, candidateCountSj))

    print(fmtSummary("baselineNoSj", baseRanksNoSj))
    print(fmtSummary("baselineWithSj", baseRanksWithSj))
    print(fmtSummary("certificateNoSj", certRanksNoSj))
    print(fmtSummary("certificateWithSj", certRanksWithSj))
    print(f"withSj rank movement improved={improved} same={same} worsened={worsened}")
    print(
        f"avgCandidateSnakes noSj={sum(poolSizesNoSj) / max(1, len(poolSizesNoSj)):.1f} "
        f"withSj={sum(poolSizesWithSj) / max(1, len(poolSizesWithSj)):.1f}"
    )
    print("noSj wrong sample")
    for case, rank, rows, candidateCount in wrongNoSj:
        top = ", ".join(f"{snake}:{alias}:{score:.1f}" for snake, score, alias in rows[:3])
        print(
            f"  query={case.alias} expected={case.snake} sj={case.sj} rank={rank} candidates={candidateCount} top={top}"
        )
    print("withSj wrong sample")
    for case, rank, rows, candidateCount in wrongWithSj:
        top = ", ".join(f"{snake}:{alias}:{score:.1f}" for snake, score, alias in rows[:3])
        print(
            f"  query={case.alias} expected={case.snake} sj={case.sj} rank={rank} candidates={candidateCount} top={top}"
        )
    print(f"seconds={time.perf_counter() - started:.1f}")


if __name__ == "__main__":
    main()
