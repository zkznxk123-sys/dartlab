"""Horizon Posting Meaning Search v1 — 역인덱스 경험 패턴 의미 조회 시도.

아이디어
-------
agipath 의 stem / 수평선 / 불 패턴 아이디어를 그대로 이식하지 않고, DartLab 공시 검색
문제에 맞춰 "의미 단위 조회" 로 재정의한다.

핵심 가설:
1. 의미 단위는 문서 전체가 아니라 문장, 문단, 표 행에 가까운 짧은 unit 이다.
2. stem 의 의미는 학습된 embedding 이 아니라 그 stem 이 등장한 unit 의 좌우 posting 경험이다.
3. 수평선은 stem 문자열에서 결정되는 고정 주소이고, 주변 stem 들은 그 주소 위 bucket 에 불을 켠다.
4. 검색은 exact inverted hit 와 horizon fire expansion 을 결합하면 GPU/embedding 없이 의미 조회가 가능하다.

구조
----
data/dart/allFilings/*.parquet + data/dart/docs/*.parquet 을 읽어 한 파일 안에서 모델을 만든다.

- postingTable[unitId] = (stemId, stemId, ...)
- stemTable[stemId] = {"stem": str, "unitIds": list[int]}
- stemPosMap[stemId] = tuple(ord(ch) for ch in stem)
- fireTable[stemId] = {left/right horizon bucket: weighted count}
- dimToStems[fireDim] = 같은 horizon fire dim 을 가진 stem 들

검색 루틴
---------
1. query 를 stem 으로 변환한다.
2. exact stem posting 으로 후보 unit 을 만든다.
3. query stem 들의 fire pattern 과 sparse dot 이 높은 stem 을 의미 확장 후보로 잡는다.
4. exact coverage, 순서/거리, 확장 stem hit, section title hit 를 합쳐 top-K unit 을 반환한다.

실행 코드
---------
기본 샘플 실행:
    uv run --no-sync python -X utf8 tests/_attempts/horizonMeaning/horizonPostingMeaningSearchTest.py

더 크게 실행:
    $env:DARTLAB_HORIZON_MAX_UNITS="120000"
    uv run --no-sync python -X utf8 tests/_attempts/horizonMeaning/horizonPostingMeaningSearchTest.py

전체 파일을 끝까지 읽기:
    $env:DARTLAB_HORIZON_MAX_UNITS="0"
    uv run --no-sync python -X utf8 tests/_attempts/horizonMeaning/horizonPostingMeaningSearchTest.py

결과 기록
---------
2026-05-28 기본 샘플 실행:
- command: uv run --no-sync python -X utf8 tests/_attempts/horizonMeaning/horizonPostingMeaningSearchTest.py
- input: allFilings 20,000 units + docs 20,000 units = 40,000 meaning units
- build: stems 28,008 / postings 560,137 / horizon buckets 2,048 / total 6.3s / build 4.3s
- 확인된 신호:
  - "유상증자 목적" → 유상증자 결정의 자금조달 목적, 제3자배정 목적 unit 상위 노출.
  - "매출채권 회수 지연" → 매출채권 회수/선수금 편중, 매출채권 관리 및 회수 위험 unit 상위 노출.
  - "대손충당금 증가" → 대손충당금/매출채권 증가 및 설정현황 unit 상위 노출.
  - "반도체 HBM 투자" → HBM exact 는 샘플에서 미해결, 반도체/투자 unit 은 상위 노출.
- 한계:
  - fire expansion 이 의미 형제도 찾지만 숫자/표 조각/회사명 결합 stem 잡음도 같이 올린다.
  - 현재 v1 은 exact posting 이 주 신호이고 horizon fire 는 보조 신호로 낮은 가중치가 안전하다.
  - 다음 시도는 stem 정규화, 표 셀 정리, 중복 unit collapse, 관계형 query scoring 이 필요하다.
"""

from __future__ import annotations

import math
import os
import re
import time
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path

import polars as pl

ROOT = Path(__file__).resolve().parents[3]
ALLFILINGS_DIR = ROOT / "data" / "dart" / "allFilings"
DOCS_DIR = ROOT / "data" / "dart" / "docs"

MAX_UNITS = int(os.environ.get("DARTLAB_HORIZON_MAX_UNITS", "40000"))
MAX_TOKENS_PER_UNIT = int(os.environ.get("DARTLAB_HORIZON_MAX_TOKENS", "80"))
MAX_SECTION_CHARS = int(os.environ.get("DARTLAB_HORIZON_MAX_SECTION_CHARS", "30000"))
MAX_SENTENCES_PER_SECTION = int(os.environ.get("DARTLAB_HORIZON_MAX_SENTENCES_PER_SECTION", "60"))
HORIZON_BUCKETS = int(os.environ.get("DARTLAB_HORIZON_BUCKETS", "2048"))
WINDOW = int(os.environ.get("DARTLAB_HORIZON_WINDOW", "5"))
TOP_K = int(os.environ.get("DARTLAB_HORIZON_TOP_K", "5"))
SEMANTIC_WEIGHT = float(os.environ.get("DARTLAB_HORIZON_SEM_WEIGHT", "35.0"))

TOKEN_RE = re.compile(r"[가-힣A-Za-z0-9][가-힣A-Za-z0-9ㆍ·%.\-_/+]*")
SENT_SPLIT_RE = re.compile(r"(?<=[다음니다요죠함임됨됨])[.!?]\s+|[.!?]\s+|\n+|;\s+")

STOP_STEMS = {
    "그리고",
    "그러나",
    "또한",
    "대한",
    "관련",
    "사항",
    "회사",
    "당사",
    "있다",
    "있는",
    "한다",
    "하여",
    "하며",
    "됩니다",
    "입니다",
    "사업",
    "보고서",
    "분기",
    "반기",
    "제출",
    "공시",
}
KOREAN_SUFFIXES = (
    "으로부터",
    "로부터",
    "에서는",
    "에게서",
    "까지",
    "부터",
    "으로",
    "에서",
    "에게",
    "하고",
    "하며",
    "이다",
    "으로",
    "라는",
    "하는",
    "하여",
    "하고",
    "은",
    "는",
    "이",
    "가",
    "을",
    "를",
    "의",
    "에",
    "로",
    "과",
    "와",
    "도",
    "만",
)

PROBE_QUERIES = [
    "반도체 HBM 투자",
    "환율 리스크",
    "유상증자 목적",
    "원재료 가격 상승",
    "대손충당금 증가",
    "매출채권 회수 지연",
    "전환사채 발행",
    "배당 지급",
]


@dataclass(slots=True)
class Unit:
    source: str
    corpName: str
    stockCode: str
    rceptNo: str
    rceptDate: str
    reportName: str
    sectionTitle: str
    text: str


@dataclass(slots=True)
class Model:
    units: list[Unit]
    postingTable: list[tuple[int, ...]]
    stemToId: dict[str, int]
    idToStem: list[str]
    stemUnits: list[list[int]]
    stemFreq: list[int]
    stemPosMap: list[tuple[int, ...]]
    stemBucket: list[int]
    bucketToStems: list[list[int]]
    fireTable: list[dict[int, float]]
    fireNorm: list[float]
    dimToStems: list[list[tuple[int, float]]]
    buildSeconds: float


def normalizeToken(token: str) -> str:
    token = token.strip(" \t\r\n,，.。;:：()[]{}<>\"'`“”‘’|")
    if not token:
        return ""
    if any("A" <= ch <= "Z" for ch in token):
        token = token.lower()
    if len(token) > 3 and any("가" <= ch <= "힣" for ch in token):
        for suffix in KOREAN_SUFFIXES:
            if token.endswith(suffix) and len(token) > len(suffix) + 2:
                return token[: -len(suffix)]
    return token


def extractStems(text: str, *, cap: int = MAX_TOKENS_PER_UNIT) -> list[str]:
    stems: list[str] = []
    for match in TOKEN_RE.finditer(text or ""):
        stem = normalizeToken(match.group(0))
        if len(stem) < 2 or stem in STOP_STEMS:
            continue
        stems.append(stem)
        if len(stems) >= cap:
            break
    return stems


def splitUnits(text: str) -> list[str]:
    if not text:
        return []
    text = text[:MAX_SECTION_CHARS]
    parts = SENT_SPLIT_RE.split(text)
    units: list[str] = []
    for part in parts:
        part = re.sub(r"\s+", " ", part).strip()
        if len(part) < 20:
            continue
        units.append(part)
        if len(units) >= MAX_SENTENCES_PER_SECTION:
            break
    return units


def safeValue(value: object) -> str:
    if value is None:
        return ""
    return str(value)


def iterAllFilingRows() -> tuple[str, Path, list[str]]:
    columns = [
        "corp_name",
        "stock_code",
        "rcept_no",
        "rcept_dt",
        "report_nm",
        "section_title",
        "section_content",
    ]
    for path in sorted(ALLFILINGS_DIR.glob("*.parquet")):
        if "_meta" in path.name:
            continue
        yield "allFilings", path, columns


def iterDocsRows() -> tuple[str, Path, list[str]]:
    columns = [
        "corp_name",
        "stock_code",
        "rcept_no",
        "rcept_date",
        "report_type",
        "section_title",
        "section_content",
    ]
    for path in sorted(DOCS_DIR.glob("*.parquet")):
        yield "docs", path, columns


def readRows(source: str, path: Path, columns: list[str]):
    try:
        df = pl.read_parquet(path, columns=columns)
    except Exception as exc:
        print(f"[skip] {source} {path.name}: {type(exc).__name__}: {exc}")
        return
    for row in df.iter_rows(named=True):
        yield row


def collectUnits() -> list[Unit]:
    t0 = time.perf_counter()
    maxUnits = MAX_UNITS
    perSourceCap = None if maxUnits <= 0 else max(maxUnits // 2, 1)
    units: list[Unit] = []
    sourceCounts: Counter[str] = Counter()

    for rowSource, path, columns in iterAllFilingRows():
        if perSourceCap is not None and sourceCounts[rowSource] >= perSourceCap:
            break
        for row in readRows(rowSource, path, columns):
            title = safeValue(row.get("section_title"))
            reportName = safeValue(row.get("report_nm"))
            for text in splitUnits(safeValue(row.get("section_content"))):
                units.append(
                    Unit(
                        source=rowSource,
                        corpName=safeValue(row.get("corp_name")),
                        stockCode=safeValue(row.get("stock_code")),
                        rceptNo=safeValue(row.get("rcept_no")),
                        rceptDate=safeValue(row.get("rcept_dt")),
                        reportName=reportName,
                        sectionTitle=title,
                        text=text,
                    )
                )
                sourceCounts[rowSource] += 1
                if perSourceCap is not None and sourceCounts[rowSource] >= perSourceCap:
                    break
            if perSourceCap is not None and sourceCounts[rowSource] >= perSourceCap:
                break

    for rowSource, path, columns in iterDocsRows():
        if perSourceCap is not None and sourceCounts[rowSource] >= perSourceCap:
            break
        for row in readRows(rowSource, path, columns):
            title = safeValue(row.get("section_title"))
            reportName = safeValue(row.get("report_type"))
            for text in splitUnits(safeValue(row.get("section_content"))):
                units.append(
                    Unit(
                        source=rowSource,
                        corpName=safeValue(row.get("corp_name")),
                        stockCode=safeValue(row.get("stock_code")),
                        rceptNo=safeValue(row.get("rcept_no")),
                        rceptDate=safeValue(row.get("rcept_date")),
                        reportName=reportName,
                        sectionTitle=title,
                        text=text,
                    )
                )
                sourceCounts[rowSource] += 1
                if perSourceCap is not None and sourceCounts[rowSource] >= perSourceCap:
                    break
            if perSourceCap is not None and sourceCounts[rowSource] >= perSourceCap:
                break

    print(
        f"[collect] units={len(units):,} "
        f"allFilings={sourceCounts['allFilings']:,} docs={sourceCounts['docs']:,} "
        f"{time.perf_counter() - t0:.1f}s"
    )
    return units


def getStemId(
    stem: str, stemToId: dict[str, int], idToStem: list[str], stemUnits: list[list[int]], stemFreq: list[int]
) -> int:
    found = stemToId.get(stem)
    if found is not None:
        return found
    stemId = len(idToStem)
    stemToId[stem] = stemId
    idToStem.append(stem)
    stemUnits.append([])
    stemFreq.append(0)
    return stemId


def stemPosition(stem: str) -> tuple[int, ...]:
    return tuple(ord(ch) for ch in stem)


def buildModel(units: list[Unit]) -> Model:
    t0 = time.perf_counter()
    stemToId: dict[str, int] = {}
    idToStem: list[str] = []
    stemUnits: list[list[int]] = []
    stemFreq: list[int] = []
    postingTable: list[tuple[int, ...]] = []

    for unitId, unit in enumerate(units):
        stems = extractStems(f"{unit.reportName} {unit.sectionTitle} {unit.text}")
        sequence: list[int] = []
        seen: set[int] = set()
        for stem in stems:
            stemId = getStemId(stem, stemToId, idToStem, stemUnits, stemFreq)
            sequence.append(stemId)
            stemFreq[stemId] += 1
            if stemId not in seen:
                stemUnits[stemId].append(unitId)
                seen.add(stemId)
        postingTable.append(tuple(sequence))

    stemPosMap = [stemPosition(stem) for stem in idToStem]
    sortedStemIds = sorted(range(len(idToStem)), key=lambda sid: stemPosMap[sid])
    stemBucket = [0] * len(idToStem)
    bucketToStems: list[list[int]] = [[] for _ in range(HORIZON_BUCKETS)]
    for rank, stemId in enumerate(sortedStemIds):
        bucket = min((rank * HORIZON_BUCKETS) // max(len(sortedStemIds), 1), HORIZON_BUCKETS - 1)
        stemBucket[stemId] = bucket
        bucketToStems[bucket].append(stemId)

    for stems in bucketToStems:
        stems.sort(key=lambda sid: (len(stemUnits[sid]), idToStem[sid]))

    fireTable: list[dict[int, float]] = [defaultdict(float) for _ in idToStem]
    for sequence in postingTable:
        if not sequence:
            continue
        seqLen = len(sequence)
        for pos, centerId in enumerate(sequence):
            leftStart = max(0, pos - WINDOW)
            rightEnd = min(seqLen, pos + WINDOW + 1)
            for otherPos in range(leftStart, rightEnd):
                if otherPos == pos:
                    continue
                otherId = sequence[otherPos]
                distance = abs(otherPos - pos)
                sideOffset = 0 if otherPos < pos else HORIZON_BUCKETS
                dim = sideOffset + stemBucket[otherId]
                fireTable[centerId][dim] += 1.0 / distance

    for stemId, profile in enumerate(fireTable):
        denom = max(stemFreq[stemId], 1)
        for dim in list(profile):
            profile[dim] /= denom

    fireNorm: list[float] = []
    dimToStems: list[list[tuple[int, float]]] = [[] for _ in range(HORIZON_BUCKETS * 2)]
    for stemId, profile in enumerate(fireTable):
        norm = math.sqrt(sum(value * value for value in profile.values()))
        fireNorm.append(norm)
        if norm <= 0:
            continue
        for dim, value in profile.items():
            dimToStems[dim].append((stemId, value))

    elapsed = time.perf_counter() - t0
    print(
        f"[build] units={len(units):,} stems={len(idToStem):,} "
        f"postings={sum(len(seq) for seq in postingTable):,} buckets={HORIZON_BUCKETS:,} "
        f"{elapsed:.1f}s"
    )
    return Model(
        units=units,
        postingTable=postingTable,
        stemToId=stemToId,
        idToStem=idToStem,
        stemUnits=stemUnits,
        stemFreq=stemFreq,
        stemPosMap=stemPosMap,
        stemBucket=stemBucket,
        bucketToStems=bucketToStems,
        fireTable=fireTable,
        fireNorm=fireNorm,
        dimToStems=dimToStems,
        buildSeconds=elapsed,
    )


def resolveQueryIds(model: Model, query: str) -> list[int]:
    ids: list[int] = []
    seen: set[int] = set()
    for stem in extractStems(query, cap=32):
        stemId = model.stemToId.get(stem)
        if stemId is not None and stemId not in seen:
            ids.append(stemId)
            seen.add(stemId)
            continue
        candidates: list[tuple[int, int, int]] = []
        for candId, cand in enumerate(model.idToStem):
            if stem in cand or cand in stem:
                candidates.append((abs(len(cand) - len(stem)), len(model.stemUnits[candId]), candId))
                if len(candidates) >= 200:
                    break
        for _, _, candId in sorted(candidates)[:3]:
            if candId not in seen:
                ids.append(candId)
                seen.add(candId)
    return ids


def topProfileDims(profile: dict[int, float], limit: int = 48) -> list[tuple[int, float]]:
    return sorted(profile.items(), key=lambda item: item[1], reverse=True)[:limit]


def expandQuery(model: Model, queryIds: list[int]) -> dict[int, float]:
    queryProfile: Counter[int] = Counter()
    querySet = set(queryIds)
    for stemId in queryIds:
        for dim, score in topProfileDims(model.fireTable[stemId]):
            queryProfile[dim] += score

    queryNorm = math.sqrt(sum(value * value for value in queryProfile.values()))
    if queryNorm <= 0:
        return {}

    dotScores: Counter[int] = Counter()
    maxDf = max(int(len(model.units) * 0.12), 200)
    for dim, queryValue in queryProfile.most_common(128):
        for stemId, stemValue in model.dimToStems[dim]:
            if stemId in querySet:
                continue
            df = len(model.stemUnits[stemId])
            if df > maxDf or df == 0:
                continue
            dotScores[stemId] += queryValue * stemValue

    expanded: dict[int, float] = {}
    for stemId, dot in dotScores.items():
        norm = model.fireNorm[stemId]
        if norm <= 0:
            continue
        dfPenalty = math.sqrt(max(len(model.stemUnits[stemId]), 1))
        score = dot / (queryNorm * norm * dfPenalty)
        if score > 0:
            expanded[stemId] = score

    return dict(sorted(expanded.items(), key=lambda item: item[1], reverse=True)[:160])


def proximityBonus(sequence: tuple[int, ...], queryIds: list[int]) -> float:
    positions: list[int] = []
    querySet = set(queryIds)
    for pos, stemId in enumerate(sequence):
        if stemId in querySet:
            positions.append(pos)
    if len(positions) < 2:
        return 0.0
    span = max(positions) - min(positions)
    return 8.0 / (1.0 + span)


def search(model: Model, query: str, *, topK: int = TOP_K) -> list[tuple[float, int, list[str], list[str]]]:
    queryIds = resolveQueryIds(model, query)
    expanded = expandQuery(model, queryIds)
    scores: Counter[int] = Counter()
    exactHits: dict[int, set[int]] = defaultdict(set)
    expandedHits: dict[int, set[int]] = defaultdict(set)
    maxPostingsPerStem = max(int(len(model.units) * 0.08), 300)

    for stemId in queryIds:
        for unitId in model.stemUnits[stemId][:maxPostingsPerStem]:
            scores[unitId] += 20.0
            exactHits[unitId].add(stemId)

    for stemId, stemScore in expanded.items():
        for unitId in model.stemUnits[stemId][:maxPostingsPerStem]:
            scores[unitId] += SEMANTIC_WEIGHT * stemScore
            expandedHits[unitId].add(stemId)

    queryStems = [model.idToStem[sid] for sid in queryIds]
    queryText = " ".join(queryStems)
    for unitId in list(scores):
        unit = model.units[unitId]
        sequence = model.postingTable[unitId]
        coverage = len(exactHits.get(unitId, set())) / max(len(queryIds), 1)
        scores[unitId] += 30.0 * coverage
        scores[unitId] += proximityBonus(sequence, queryIds)
        titleSurface = f"{unit.reportName} {unit.sectionTitle}".lower()
        if any(stem.lower() in titleSurface for stem in queryStems):
            scores[unitId] += 6.0
        if queryText and queryText in titleSurface:
            scores[unitId] += 8.0

    ranked: list[tuple[float, int, list[str], list[str]]] = []
    for unitId, score in scores.most_common(topK * 6):
        exact = [model.idToStem[sid] for sid in sorted(exactHits.get(unitId, set()))]
        semantic = [
            model.idToStem[sid]
            for sid in sorted(expandedHits.get(unitId, set()), key=lambda sid: expanded.get(sid, 0), reverse=True)[:10]
        ]
        ranked.append((float(score), unitId, exact, semantic))
    ranked.sort(key=lambda item: item[0], reverse=True)
    return ranked[:topK]


def printSearchResults(model: Model, query: str) -> None:
    print("\n" + "=" * 88)
    print(f"[query] {query}")
    queryIds = resolveQueryIds(model, query)
    print(f"[query stems] {[model.idToStem[sid] for sid in queryIds]}")
    expanded = expandQuery(model, queryIds)
    print(f"[expanded] {[(model.idToStem[sid], round(score, 4)) for sid, score in list(expanded.items())[:12]]}")
    for rank, (score, unitId, exact, semantic) in enumerate(search(model, query), start=1):
        unit = model.units[unitId]
        text = unit.text.replace("\n", " ")
        if len(text) > 220:
            text = text[:220] + "..."
        print(
            f"{rank}. score={score:.2f} source={unit.source} corp={unit.corpName} "
            f"stock={unit.stockCode} rcept={unit.rceptNo} date={unit.rceptDate}"
        )
        print(f"   report={unit.reportName} | section={unit.sectionTitle}")
        print(f"   exact={exact} semantic={semantic}")
        print(f"   text={text}")


def main() -> None:
    print("=" * 88)
    print("Horizon Posting Meaning Search v1")
    print("=" * 88)
    print(f"[config] maxUnits={MAX_UNITS:,} buckets={HORIZON_BUCKETS:,} window={WINDOW} semWeight={SEMANTIC_WEIGHT:g}")

    t0 = time.perf_counter()
    units = collectUnits()
    if not units:
        raise SystemExit("no units collected from data/dart/allFilings or data/dart/docs")
    model = buildModel(units)
    for query in PROBE_QUERIES:
        printSearchResults(model, query)
    print("\n" + "=" * 88)
    print(f"[done] totalSeconds={time.perf_counter() - t0:.1f} buildSeconds={model.buildSeconds:.1f}")


if __name__ == "__main__":
    main()
