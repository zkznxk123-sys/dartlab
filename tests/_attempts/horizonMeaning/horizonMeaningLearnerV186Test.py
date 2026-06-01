"""Horizon Meaning Learner V186 - self-supervised path atom automaton.

아이디어:
    수평선 좌표는 의미가 아니라 고정 주소다. 의미는 주소 주변에 누적된 경험, 즉 같이 나온 조각의 순서,
    앞뒤 위치, 역할 슬롯, statement role, canonical family 안에서 반복된 path 의 겹침으로 만들어진다.

    V185 는 open held-out 에서 finance polarity/role slot 을 손으로 추출해 surface/hash baseline 을 올렸다.
    V186 은 그 슬롯을 그대로 늘리지 않고, train alias 경험을 자동 비교 가능한 path atom 으로 바꾼다.
    각 alias 는 다음 atom 을 만든다.

    - boundary atom: 2/3/4-gram, prefix/suffix, 가능한 내부 cut(left>right)
    - slot atom: flow/delta/transaction/valuation/statement/object/sj
    - path atom: slotGram, slotPair, preSlot, sufSlot, sjSlot

    held-out alias 는 train 후보에서 제거한다. 각 snakeId 는 train alias 의 path atom 만 누적하고, 전체 snake
    document frequency 로 generic atom 을 낮춘 뒤 residualAtoms 를 만든다. query 는 자신의 path atom 을 만들고,
    candidate 는 snake residualAtoms + alias local pathAtoms 로 비교된다. 즉 "스템 자체"가 아니라 "스템/조각이
    canonical 경험 안에서 어떤 순서와 역할로 같이 불렸는가"를 sparse proof 로 비교한다.

실행 코드:
    uv run python -X utf8 -m py_compile tests/_attempts/horizonMeaning/horizonMeaningLearnerV186Test.py
    uv run python -X utf8 tests/_attempts/horizonMeaning/horizonMeaningLearnerV186Test.py
    $env:DARTLAB_HORIZON_V186_HELDOUT_LIMIT='600'; uv run python -X utf8 tests/_attempts/horizonMeaning/horizonMeaningLearnerV186Test.py

검증 기준:
    - held-out query surface 는 train candidate alias 에 없어야 한다.
    - 후보는 평가 11개가 아니라 accountMappings 의 수천 canonical snakeId 여야 한다.
    - V184 baseline, V185 polarity-role certificate, V186 path atom automaton 을 같은 split 에서 비교한다.
    - V186 certificateWithSj 가 V185 certificateWithSj 의 Top1/Top5/MRR 을 넘으면 "경험 atom" 개선 신호로 본다.

결과:
    py_compile 통과.

    HELDOUT_LIMIT=80 sanity:
        heldout=80, trainEntries=17,545, snakes=4,840, leakedAliases=0
        baselineWithSj: Top1=27/80, Top5=56/80, MRR=0.5011
        certificateWithSj: Top1=32/80, Top5=59/80, MRR=0.5535
        withSj rank movement: improved=26, same=48, worsened=6

    기본 320 held-out:
        heldout=320, trainEntries=17,340, snakes=4,840, leakedAliases=0
        baselineNoSj: Top1=104/320, Top3=184/320, Top5=214/320, Top10=247/320, Miss=2/320, MRR=0.4858
        baselineWithSj: Top1=121/320, Top3=203/320, Top5=229/320, Top10=262/320, Miss=2/320, MRR=0.5318
        certificateNoSj: Top1=110/320, Top3=188/320, Top5=225/320, Top10=254/320, Miss=2/320, MRR=0.5034
        certificateWithSj: Top1=128/320, Top3=214/320, Top5=239/320, Top10=265/320, Miss=2/320, MRR=0.5541
        withSj rank movement: improved=92, same=199, worsened=29

    HELDOUT_LIMIT=600, 사실상 eligible 전체에 가까운 497 held-out:
        heldout=497, trainEntries=17,194, snakes=4,840, leakedAliases=0
        baselineNoSj: Top1=167/497, Top3=295/497, Top5=342/497, Top10=386/497, Miss=2/497, MRR=0.4944
        baselineWithSj: Top1=192/497, Top3=319/497, Top5=359/497, Top10=409/497, Miss=2/497, MRR=0.5392
        certificateNoSj: Top1=175/497, Top3=302/497, Top5=354/497, Top10=401/497, Miss=2/497, MRR=0.5104
        certificateWithSj: Top1=202/497, Top3=332/497, Top5=375/497, Top10=418/497, Miss=2/497, MRR=0.5587
        withSj rank movement: improved=145, same=312, worsened=40

    V185 대비:
        320 withSj: Top1 126 -> 128, Top5 237 -> 239, MRR 0.5467 -> 0.5541
        497 withSj: Top1 200 -> 202, Top5 372 -> 375, MRR 0.5529 -> 0.5587

결론:
    성공/작은 개념 상승. V186 은 V185 의 규칙 슬롯 위에 자동 path atom residual profile 을 붙여 open held-out
    497 에서 추가 개선을 냈다. 개선 폭은 크지 않지만, "경험을 atom 으로 압축하고 canonical residual 로 비교한다"는
    방향은 얇은 손튜닝보다 낫다.

    아직 한계도 분명하다. 이 파일은 accountMappings alias 경험만 학습했고, docs/allfiling 의 row/table/sentence
    경험 그래프까지 들어간 것은 아니다. `사업매각으로인한현금유입액` 은 cashflow 표면이 BS gold 를 누르고,
    `신종자본증권발행` 은 bonds/hybrid_bond/issue_of_hybrid_bond hierarchy 를 여전히 완전히 못 가른다.

    다음 실험은 alias path atom 을 corpus object path 로 올려야 한다. 후보별로 `row/table/value/statement/relation`
    경험을 atom화하고, surface boundary 는 후보 생성에만 쓰고 ranking 은 canonical residual path proof 로 해야 한다.
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

HELDOUT_LIMIT = int(os.environ.get("DARTLAB_HORIZON_V186_HELDOUT_LIMIT", "320"))
MIN_CLUSTER_SIZE = int(os.environ.get("DARTLAB_HORIZON_V186_MIN_CLUSTER_SIZE", "4"))
MAX_TRAIN_ALIASES_PER_SNAKE = int(os.environ.get("DARTLAB_HORIZON_V186_MAX_TRAIN_ALIASES_PER_SNAKE", "80"))
POOL_LIMIT = int(os.environ.get("DARTLAB_HORIZON_V186_POOL_LIMIT", "5200"))
POSTING_ROW_LIMIT = int(os.environ.get("DARTLAB_HORIZON_V186_POSTING_ROW_LIMIT", "2600"))
TOP_K = int(os.environ.get("DARTLAB_HORIZON_V186_TOP_K", "10"))
NUM_MH = int(os.environ.get("DARTLAB_HORIZON_V186_NUM_MH", "32"))
PATH_ATOM_LIMIT = int(os.environ.get("DARTLAB_HORIZON_V186_PATH_ATOM_LIMIT", "96"))
PATH_RESIDUAL_LIMIT = int(os.environ.get("DARTLAB_HORIZON_V186_PATH_RESIDUAL_LIMIT", "64"))

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
    coreSlots: frozenset[str]
    pathAtoms: Counter[str]


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
    coreSlots: frozenset[str]
    pathAtoms: Counter[str]
    residualAtoms: Counter[str]
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


def coreSlotKeys(slots: Counter[str]) -> frozenset[str]:
    return frozenset(slot for slot in slots if not slot.startswith("term:") and not slot.startswith("sj:"))


def boundaryAtoms(value: str) -> tuple[str, ...]:
    atoms: list[str] = []
    grams2 = sorted(ngrams(value, 2))
    grams3 = sorted(ngrams(value, 3))
    grams4 = sorted(ngrams(value, 4))
    for gram in grams2:
        atoms.append(f"g2:{gram}")
    for gram in grams3:
        atoms.append(f"g3:{gram}")
    for gram in grams4[:24]:
        atoms.append(f"g4:{gram}")
    for size in (2, 3, 4, 5):
        if len(value) >= size:
            atoms.append(f"pre{size}:{value[:size]}")
            atoms.append(f"suf{size}:{value[-size:]}")
    for index in range(2, min(len(value), 13)):
        left = value[:index]
        right = value[index:]
        if 2 <= len(left) <= 8 and 2 <= len(right) <= 10:
            atoms.append(f"cut:{left}>{right}")
    return tuple(atoms)


def pathAtomsForAlias(value: str, sj: str = "") -> Counter[str]:
    slots = structuralSlots(value, sj)
    atoms: Counter[str] = Counter()
    for atom in boundaryAtoms(value):
        atoms[atom] += 1.0
    slotKeys = sorted(slot for slot in slots if not slot.startswith("term:") and not slot.startswith("sj:"))
    termKeys = sorted(slot for slot in slots if slot.startswith("term:"))
    for slot in slotKeys:
        atoms[f"slot:{slot}"] += 2.0
    for term in termKeys:
        atoms[f"termPath:{term[5:]}"] += 1.0
    grams3 = tuple(sorted(ngrams(value, 3)))[:28]
    for slot in slotKeys[:10]:
        for gram in grams3:
            atoms[f"slotGram:{slot}|{gram}"] += 0.85
    for leftIndex, left in enumerate(slotKeys):
        for right in slotKeys[leftIndex + 1 :]:
            atoms[f"slotPair:{left}|{right}"] += 1.5
    for size in (2, 3, 4):
        if len(value) >= size:
            prefix = value[:size]
            suffix = value[-size:]
            for slot in slotKeys[:10]:
                atoms[f"preSlot:{prefix}|{slot}"] += 1.1
                atoms[f"sufSlot:{suffix}|{slot}"] += 1.1
    if sj:
        for slot in slotKeys[:10]:
            atoms[f"sjSlot:{sj}|{slot}"] += 1.2
    return Counter(dict(atoms.most_common(PATH_ATOM_LIMIT)))


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
            slots = structuralSlots(alias, sjBySnake.get(snake, ""))
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
                    slots=slots,
                    coreSlots=coreSlotKeys(slots),
                    pathAtoms=pathAtomsForAlias(alias, sjBySnake.get(snake, "")),
                )
            )
    profileSlots: dict[str, Counter[str]] = defaultdict(Counter)
    profileAtoms: dict[str, Counter[str]] = defaultdict(Counter)
    profileCounts: Counter[str] = Counter()
    for entry in entries:
        profileCounts[entry.snake] += 1
        for slot, value in entry.slots.items():
            profileSlots[entry.snake][slot] += max(0.0, float(value))
        for atom, value in entry.pathAtoms.items():
            profileAtoms[entry.snake][atom] += max(0.0, float(value))
    atomSnakeDf: Counter[str] = Counter()
    for snake, atoms in profileAtoms.items():
        for atom in atoms:
            atomSnakeDf[atom] += 1
    totalSnakes = max(1, len(profileAtoms))
    residualAtoms: dict[str, Counter[str]] = {}
    for snake, atoms in profileAtoms.items():
        residual: Counter[str] = Counter()
        aliasCount = max(1, profileCounts[snake])
        for atom, raw in atoms.items():
            support = float(raw) / aliasCount
            df = atomSnakeDf.get(atom, 1)
            idf = math.log((totalSnakes + 1.0) / (df + 0.5))
            if idf <= 0.25:
                continue
            residual[atom] = support * idf
        residualAtoms[snake] = Counter(dict(residual.most_common(PATH_RESIDUAL_LIMIT)))
    profiles = {
        snake: SnakeProfile(
            snake=snake,
            sj=sjBySnake.get(snake, ""),
            slots=Counter(dict(slots.most_common(64))),
            coreSlots=coreSlotKeys(slots),
            pathAtoms=Counter(dict(profileAtoms.get(snake, Counter()).most_common(PATH_ATOM_LIMIT))),
            residualAtoms=residualAtoms.get(snake, Counter()),
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


def canonicalPathAutomatonDelta(
    queryAtoms: Counter[str],
    queryCoreSlots: frozenset[str],
    entry: AliasEntry,
    profile: SnakeProfile | None,
) -> float:
    if not queryAtoms or profile is None:
        return 0.0
    if not profile.residualAtoms and not entry.pathAtoms:
        return 0.0

    shared = 0.0
    sharedKinds: Counter[str] = Counter()
    for atom, qWeight in queryAtoms.items():
        cWeight = profile.residualAtoms.get(atom, 0.0) + entry.pathAtoms.get(atom, 0.0) * 0.35
        if cWeight <= 0.0:
            continue
        gain = 1.0
        if atom.startswith("slotPair:"):
            gain = 2.0
        elif atom.startswith("slotGram:"):
            gain = 1.7
        elif atom.startswith("preSlot:") or atom.startswith("sufSlot:") or atom.startswith("sjSlot:"):
            gain = 1.55
        elif atom.startswith("cut:"):
            gain = 1.25
        elif atom.startswith("slot:"):
            gain = 1.35
        shared += math.sqrt(max(0.0, qWeight)) * math.sqrt(max(0.0, cWeight)) * gain
        sharedKinds[atom.split(":", 1)[0]] += 1

    conflict = 0.0
    qSlots = queryCoreSlots
    for group in EXCLUSIVE_SLOT_GROUPS:
        queryHits = set(group) & qSlots
        if not queryHits:
            continue
        candidateHits = (set(group) & profile.coreSlots) or (set(group) & entry.coreSlots)
        if candidateHits and not (candidateHits & queryHits):
            conflict += 7.0
        elif not candidateHits:
            conflict += 0.8
    if qSlots and not (qSlots & profile.coreSlots) and not (qSlots & entry.coreSlots):
        conflict += 2.5
    diversity = sum(1 for count in sharedKinds.values() if count > 0)
    reward = min(24.0, shared * 0.34 + diversity * 1.15)
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
    qSlots = Counter()
    qCoreSlots: frozenset[str] = frozenset()
    qPathAtoms = Counter()
    if useCertificate:
        qSlots = structuralSlots(query, case.sj)
        qCoreSlots = coreSlotKeys(qSlots)
        qPathAtoms = pathAtomsForAlias(query, case.sj)
    pool = candidatePool(query, case.sj, entries, bigramPostings, charPostings, withSj=withSj)
    best: dict[str, tuple[float, str]] = {}
    for index, vote in pool.items():
        entry = entries[index]
        score = entryScore(query, qRegions, qMh, qBigrams, qTrigrams, entry, vote)
        if useCertificate:
            score += structuralCertificateDelta(qSlots, entry, profiles.get(entry.snake))
            score += canonicalPathAutomatonDelta(qPathAtoms, qCoreSlots, entry, profiles.get(entry.snake))
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
    print("V186 accountMappings open held-out audit")
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
