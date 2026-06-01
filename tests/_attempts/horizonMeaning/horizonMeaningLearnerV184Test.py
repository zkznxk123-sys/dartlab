"""Horizon Meaning Learner V184 - accountMappings open held-out audit.

아이디어:
    V183 까지의 4 positive + 7 negative probe 는 FOCUS_TERMS 로 corpus window 를 닫은 closed-world
    평가였다. V184 는 새 scoring 을 깎지 않고, 먼저 평가 우주를 연다.

    accountMappings.json 을 gold 로만 사용해 canonical snakeId 별 alias cluster 를 만든다. 각 cluster 에서
    deterministic held-out alias 1개를 빼고, 나머지 train alias 만 후보 사전으로 사용한다. held-out query 는
    train 사전에 없는 표면이어야 하며, 모든 candidate snakeId 와 경쟁한다.

    이 파일은 V183 을 복사하지 않는다. 목적은 horizonMeaning 계열의 다음 실험을 검증할 open held-out
    기준선을 만드는 것이다. baseline scorer 는 V7-style jamo/char/bigram characteristic hash + MinHash +
    ngram posting prefilter 다. 이는 최종 horizon proof model 이 아니라, "11개 probe 바깥에서 어느 정도의
    신호가 이미 있는가"를 재는 audit harness 이다.

실행 코드:
    uv run python -X utf8 -m py_compile tests/_attempts/horizonMeaning/horizonMeaningLearnerV184Test.py
    uv run python -X utf8 tests/_attempts/horizonMeaning/horizonMeaningLearnerV184Test.py

검증 기준:
    - held-out query surface 는 train candidate alias 에 없어야 한다.
    - 후보는 평가 11개가 아니라 accountMappings 의 수천 canonical snakeId 여야 한다.
    - no-sj 와 with-sj 둘 다 Top1/Top5/MRR 를 기록한다.
    - 결과가 낮으면 V183 rank1 은 closed-world 로 판정하고, 다음은 riVsa/open corpus candidate + proof object
      구조로 전환해야 한다.

결과:
    py_compile 통과.

    기본 320 held-out:
        heldout=320, trainEntries=17,340, snakes=4,840, leakedAliases=0
        avgCandidateSnakes noSj=1,437.5, withSj=1,459.6
        noSj: Top1=104/320, Top3=184/320, Top5=214/320, Top10=247/320, Miss=2/320, MRR=0.4858
        withSj: Top1=121/320, Top3=203/320, Top5=229/320, Top10=262/320, Miss=2/320, MRR=0.5318

    HELDOUT_LIMIT=600, 사실상 eligible 전체에 가까운 497 held-out:
        heldout=497, trainEntries=17,194, snakes=4,840, leakedAliases=0
        avgCandidateSnakes noSj=1,446.5, withSj=1,459.2
        noSj: Top1=167/497, Top3=295/497, Top5=342/497, Top10=386/497, Miss=2/497, MRR=0.4944
        withSj: Top1=192/497, Top3=319/497, Top5=359/497, Top10=409/497, Miss=2/497, MRR=0.5392

    대표 실패:
        리스설비 -> leased_assets 는 interest_income/equipments/lease_expenses 에 밀림.
        현금 유입/유출, 증가/감소 방향이 다른 snakeId 가 top 을 먹는 경우가 반복됨.
        신종자본증권발행 -> issue_of_hybrid_bond 는 bonds/hybrid_bond 계열이 앞섬.

결론:
    성공/진단 전환. V184 는 모델 성능을 올린 실험이 아니라, closed-world 평가를 깬 audit harness 다.
    결과는 다른 세션의 비판을 지지한다. V183 의 4/4, 0/7 guard 는 일반화 증거로 쓰면 안 된다.

    동시에 surface/hash baseline 만으로도 withSj Top5=359/497, MRR=0.5392 까지는 나온다. 즉 후보 생성
    씨앗은 살아 있지만, top1 에 필요한 것은 방향성(유입/유출, 증가/감소), statement role, cash-flow vs
    balance-sheet role, canonical snakeId 간 계층/동의어 equivalence 를 구분하는 experience proof 다.

    다음 실험은 V183 을 더 깎는 것이 아니라, 이 V184 held-out harness 위에서 riVsa/open corpus candidate
    generator 와 horizon proof object 를 붙여 surface baseline 대비 Top1/MRR 이 오르는지 검증해야 한다.
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

HELDOUT_LIMIT = int(os.environ.get("DARTLAB_HORIZON_V184_HELDOUT_LIMIT", "320"))
MIN_CLUSTER_SIZE = int(os.environ.get("DARTLAB_HORIZON_V184_MIN_CLUSTER_SIZE", "4"))
MAX_TRAIN_ALIASES_PER_SNAKE = int(os.environ.get("DARTLAB_HORIZON_V184_MAX_TRAIN_ALIASES_PER_SNAKE", "80"))
POOL_LIMIT = int(os.environ.get("DARTLAB_HORIZON_V184_POOL_LIMIT", "5200"))
POSTING_ROW_LIMIT = int(os.environ.get("DARTLAB_HORIZON_V184_POSTING_ROW_LIMIT", "2600"))
TOP_K = int(os.environ.get("DARTLAB_HORIZON_V184_TOP_K", "10"))
NUM_MH = int(os.environ.get("DARTLAB_HORIZON_V184_NUM_MH", "32"))

HANGUL_START = 0xAC00
HANGUL_END = 0xD7A3
JAMO_BASE = 0xAC00
SPACE_RE = re.compile(r"\s+")


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


@dataclass(frozen=True)
class HeldoutCase:
    alias: str
    snake: str
    sj: str
    trainSize: int
    clusterSize: int


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


def buildSplit() -> tuple[list[HeldoutCase], list[AliasEntry], Counter[str]]:
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
                )
            )
    return heldout, entries, clusterSizes


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


def rankCase(
    case: HeldoutCase,
    entries: list[AliasEntry],
    bigramPostings: dict[str, tuple[int, ...]],
    charPostings: dict[str, tuple[int, ...]],
    *,
    withSj: bool,
) -> tuple[int | None, tuple[tuple[str, float, str], ...], int]:
    query = case.alias
    qRegions = characteristicRegions(query)
    qMh = minhash(query)
    qBigrams = ngrams(query, 2)
    qTrigrams = ngrams(query, 3)
    pool = candidatePool(query, case.sj, entries, bigramPostings, charPostings, withSj=withSj)
    best: dict[str, tuple[float, str]] = {}
    for index, vote in pool.items():
        entry = entries[index]
        score = entryScore(query, qRegions, qMh, qBigrams, qTrigrams, entry, vote)
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
    heldout, entries, clusterSizes = buildSplit()
    leaked = sorted({case.alias for case in heldout} & {entry.alias for entry in entries})
    print("V184 accountMappings open held-out audit")
    print(
        f"heldout={len(heldout)} trainEntries={len(entries)} snakes={len(clusterSizes)} "
        f"eligibleClusters={sum(1 for _snake, size in clusterSizes.items() if size >= MIN_CLUSTER_SIZE)} leakedAliases={len(leaked)}"
    )
    if leaked:
        raise RuntimeError(f"held-out aliases leaked into train entries: {leaked[:5]}")
    bigramPostings, charPostings = buildPostings(entries)
    print(f"postings bigrams={len(bigramPostings)} chars={len(charPostings)}")

    ranksNoSj: list[int | None] = []
    ranksWithSj: list[int | None] = []
    wrongNoSj: list[tuple[HeldoutCase, int | None, tuple[tuple[str, float, str], ...], int]] = []
    wrongWithSj: list[tuple[HeldoutCase, int | None, tuple[tuple[str, float, str], ...], int]] = []
    poolSizesNoSj: list[int] = []
    poolSizesWithSj: list[int] = []

    for case in heldout:
        rankNo, rowsNo, candidateCountNo = rankCase(case, entries, bigramPostings, charPostings, withSj=False)
        rankSj, rowsSj, candidateCountSj = rankCase(case, entries, bigramPostings, charPostings, withSj=True)
        ranksNoSj.append(rankNo)
        ranksWithSj.append(rankSj)
        poolSizesNoSj.append(candidateCountNo)
        poolSizesWithSj.append(candidateCountSj)
        if rankNo != 1 and len(wrongNoSj) < 12:
            wrongNoSj.append((case, rankNo, rowsNo, candidateCountNo))
        if rankSj != 1 and len(wrongWithSj) < 12:
            wrongWithSj.append((case, rankSj, rowsSj, candidateCountSj))

    print(fmtSummary("noSj", ranksNoSj))
    print(fmtSummary("withSj", ranksWithSj))
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
