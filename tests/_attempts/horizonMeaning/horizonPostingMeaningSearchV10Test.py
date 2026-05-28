"""Horizon Posting Meaning Search v10 — evidence rubric validation.

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
4. tokenizer 단계에서 표/숫자/XBRL/slash 결합 stem 잡음을 줄이고, 동일 text unit 을 collapse 한다.
5. v7 의 압축 pair channel 을 유지한다.
6. event/risk/finance 같은 query type 별 report/section hint 를 sparse channel 로 미리 계산한다.
7. fire pattern 은 top exact 후보에 대해서만 tie-breaker 와 explanation stem 으로 계산한다.
8. 문자열 포함 heuristic 과 별도로 probe 별 evidence rubric 을 두어 근거 품질을 더 엄격히 검증한다.

실행 코드
---------
기본 샘플 실행:
    uv run --no-sync python -X utf8 tests/_attempts/horizonMeaning/horizonPostingMeaningSearchV10Test.py

더 크게 실행:
    $env:DARTLAB_HORIZON_MAX_UNITS="120000"
    uv run --no-sync python -X utf8 tests/_attempts/horizonMeaning/horizonPostingMeaningSearchV10Test.py

전체 파일을 끝까지 읽기:
    $env:DARTLAB_HORIZON_MAX_UNITS="0"
    uv run --no-sync python -X utf8 tests/_attempts/horizonMeaning/horizonPostingMeaningSearchV10Test.py

결과 기록
---------
기본 샘플 결과: 40K units, stems 71,755, postings 1,082,237, focused pairs 152,
pairPostings 1,474, rough memory 56.0MB. exactQuality 79 vs fireQuality 80 이지만
probe 별 evidence rubric 은 exactRubric 78 vs fireRubric 78, rubricImproved 0/same 8/worsened 0.
exact 7.55ms vs fire 36.85ms, duplicate top5 0. 결론: fire tie-breaker 는 휴리스틱
품질을 1점 올리지만, 더 엄격한 근거 rubric 에서는 품질 개선 없이 안전한 설명/동률해소 신호다.
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
SEMANTIC_WEIGHT = float(os.environ.get("DARTLAB_HORIZON_SEM_WEIGHT", "14.0"))
FIRE_RERANK_CANDIDATES = int(os.environ.get("DARTLAB_HORIZON_FIRE_CANDIDATES", "100"))
MAX_FIRE_BOOST = float(os.environ.get("DARTLAB_HORIZON_MAX_FIRE_BOOST", "8.0"))
TABLE_PENALTY = float(os.environ.get("DARTLAB_HORIZON_TABLE_PENALTY", "7.0"))
RELATION_PAIR_BONUS = float(os.environ.get("DARTLAB_HORIZON_REL_PAIR_BONUS", "12.0"))
RELATION_SPAN_LIMIT = int(os.environ.get("DARTLAB_HORIZON_REL_SPAN", "14"))
RELATION_RERANK_CANDIDATES = int(os.environ.get("DARTLAB_HORIZON_REL_CANDIDATES", "220"))
FIRE_TIE_BREAK_WEIGHT = float(os.environ.get("DARTLAB_HORIZON_FIRE_TIE_WEIGHT", "0.75"))
PAIR_INDEX_WINDOW = int(os.environ.get("DARTLAB_HORIZON_PAIR_WINDOW", "14"))
PAIR_INDEX_MAX_UNITS = int(os.environ.get("DARTLAB_HORIZON_PAIR_MAX_UNITS", "20000"))

TOKEN_RE = re.compile(r"[가-힣A-Za-z0-9][가-힣A-Za-z0-9ㆍ·%.\-_/+]*")
SENT_SPLIT_RE = re.compile(r"(?<=[다음니다요죠함임됨됨])[.!?]\s+|[.!?]\s+|\n+|;\s+")
HTML_TAG_RE = re.compile(r"<[^>]+>")
TOKEN_BREAK_RE = re.compile(r"[\\/]+")
SPACE_RE = re.compile(r"\s+")
XBRL_MARKERS = ("ifrs-", "ifrs_", "dart_", "xbrl", "member", "axis")

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


@dataclass(frozen=True, slots=True)
class QuerySpec:
    query: str
    mustAny: tuple[str, ...]
    supportAny: tuple[str, ...]
    relationPairs: tuple[tuple[str, str], ...] = ()
    typeHints: tuple[str, ...] = ()
    rubricGroups: tuple[tuple[str, ...], ...] = ()
    badAny: tuple[str, ...] = ()


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
    pairUnits: dict[tuple[int, int], list[int]]
    unitTableLike: list[bool]
    unitTypeBoostBase: dict[str, dict[int, float]]
    buildSeconds: float


PROBE_QUERIES = [
    QuerySpec(
        "반도체 HBM 투자",
        ("반도체", "hbm", "투자"),
        ("ai", "d램", "차세대", "검사장비", "수주"),
        (("반도체", "투자"), ("hbm", "반도체")),
        ("사업의 내용", "투자위험", "핵심투자위험"),
        (("반도체", "hbm"), ("투자", "수주", "성장", "차세대", "ai")),
    ),
    QuerySpec(
        "환율 리스크",
        ("환율", "리스크", "외화"),
        ("원화", "등락", "위험", "변동"),
        (("환율", "리스크"), ("환율", "변동")),
        ("위험관리", "파생거래", "투자위험", "핵심투자위험"),
        (("환율", "외화", "원화"), ("리스크", "위험", "변동", "등락")),
    ),
    QuerySpec(
        "유상증자 목적",
        ("유상증자", "자금조달", "제3자배정"),
        ("시설자금", "운영자금", "목적", "배정"),
        (("유상증자", "목적"), ("자금조달", "목적")),
        ("유상증자 결정", "유상증자결정", "주요사항보고서"),
        (("유상증자", "증자"), ("목적", "자금조달", "시설자금", "운영자금", "제3자배정")),
    ),
    QuerySpec(
        "원재료 가격 상승",
        ("원재료", "가격"),
        ("상승", "변동", "출연료", "콘텐츠"),
        (("원재료", "가격"), ("가격", "상승")),
        ("원재료 및 생산설비", "핵심투자위험", "투자위험"),
        (("원재료", "원자재", "원면"), ("가격", "단가"), ("상승", "변동", "압력", "비용")),
    ),
    QuerySpec(
        "대손충당금 증가",
        ("대손충당금", "충당금"),
        ("증가", "설정", "매출채권", "채권"),
        (("대손충당금", "증가"), ("대손충당금", "설정")),
        ("기타 재무", "재무제표 주석", "위험"),
        (("대손충당금", "충당금"), ("증가", "설정", "설정률", "전기말"), ("매출채권", "채권")),
    ),
    QuerySpec(
        "매출채권 회수 지연",
        ("매출채권", "회수"),
        ("지연", "위험", "수금", "편중"),
        (("매출채권", "회수"), ("회수", "지연")),
        ("핵심투자위험", "회사위험", "기타 재무", "재무제표 주석"),
        (("매출채권", "채권"), ("회수", "수금"), ("지연", "위험", "편중", "연말")),
    ),
    QuerySpec(
        "전환사채 발행",
        ("전환사채", "사채"),
        ("발행", "청약", "신주인수권"),
        (("전환사채", "발행"), ("사채", "발행")),
        ("전환사채권 발행결정", "채무증권", "사채권", "자본으로 인정되는 채무증권"),
        (("전환사채", "사채"), ("발행", "청약", "납입", "전환가격")),
    ),
    QuerySpec(
        "배당 지급",
        ("배당", "지급"),
        ("현금", "주주총회", "결의"),
        (("배당", "지급"), ("현금", "배당")),
        ("현금ㆍ현물배당", "현금ㆍ현물 배당", "배당결정", "배당 결정"),
        (("배당", "배당금"), ("지급", "지급일", "주주", "결의", "현금")),
    ),
]

QUERY_SPEC_BY_QUERY = {spec.query: spec for spec in PROBE_QUERIES}


def normalizeToken(token: str) -> str:
    token = token.strip(" \t\r\n,，.。;:：()[]{}<>\"'`“”‘’|")
    if not token:
        return ""
    if any("A" <= ch <= "Z" for ch in token):
        token = token.lower()
    if not isUsefulStem(token):
        return ""
    if len(token) > 3 and any("가" <= ch <= "힣" for ch in token):
        for suffix in KOREAN_SUFFIXES:
            if token.endswith(suffix) and len(token) > len(suffix) + 2:
                trimmed = token[: -len(suffix)]
                return trimmed if isUsefulStem(trimmed) else ""
    return token


def isUsefulStem(stem: str) -> bool:
    if len(stem) < 2 or stem in STOP_STEMS:
        return False
    lower = stem.lower()
    if any(marker in lower for marker in XBRL_MARKERS):
        return False
    if lower.startswith(("cfy", "pfy", "bpfy")) and any(ch.isdigit() for ch in lower):
        return False
    hasKorean = any("가" <= ch <= "힣" for ch in stem)
    hasAlpha = any(("a" <= ch <= "z") or ("A" <= ch <= "Z") for ch in stem)
    digitCount = sum(1 for ch in stem if ch.isdigit())
    if digitCount and digitCount / max(len(stem), 1) >= 0.45:
        return False
    if not hasKorean and not hasAlpha:
        return False
    if len(stem) > 32:
        return False
    if sum(1 for ch in stem if ch in ".-%_") >= 2:
        return False
    return True


def splitRawToken(token: str) -> list[str]:
    parts: list[str] = []
    for part in TOKEN_BREAK_RE.split(token):
        part = part.strip()
        if part:
            parts.append(part)
    return parts


def extractStems(text: str, *, cap: int = MAX_TOKENS_PER_UNIT) -> list[str]:
    stems: list[str] = []
    for match in TOKEN_RE.finditer(text or ""):
        for rawToken in splitRawToken(match.group(0)):
            stem = normalizeToken(rawToken)
            if not stem:
                continue
            stems.append(stem)
            if len(stems) >= cap:
                break
        if len(stems) >= cap:
            break
    return stems


def cleanText(text: str) -> str:
    text = HTML_TAG_RE.sub(" ", text or "")
    text = text.replace("&nbsp;", " ").replace("&amp;", "&")
    return SPACE_RE.sub(" ", text).strip()


def splitUnits(text: str) -> list[str]:
    if not text:
        return []
    text = cleanText(text[:MAX_SECTION_CHARS])
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


def unitDedupeKey(text: str) -> str:
    normalized = compactText(text)
    normalized = re.sub(r"[\d,.\-()%]+", "#", normalized)
    normalized = SPACE_RE.sub(" ", normalized)
    return normalized[:260]


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
    seenUnitKeys: set[str] = set()
    sourceCounts: Counter[str] = Counter()
    duplicateSkips = 0

    for rowSource, path, columns in iterAllFilingRows():
        if perSourceCap is not None and sourceCounts[rowSource] >= perSourceCap:
            break
        for row in readRows(rowSource, path, columns):
            title = safeValue(row.get("section_title"))
            reportName = safeValue(row.get("report_nm"))
            for text in splitUnits(safeValue(row.get("section_content"))):
                key = unitDedupeKey(text)
                if key in seenUnitKeys:
                    duplicateSkips += 1
                    continue
                seenUnitKeys.add(key)
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
                key = unitDedupeKey(text)
                if key in seenUnitKeys:
                    duplicateSkips += 1
                    continue
                seenUnitKeys.add(key)
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
        f"dupSkips={duplicateSkips:,} "
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


def typeHintBase(typeSurface: str, spec: QuerySpec) -> float:
    if not spec.typeHints:
        return 0.0
    hits = 0
    for hint in spec.typeHints:
        hintLower = hint.lower()
        if hintLower in typeSurface:
            hits += 2
        elif any(part and part in typeSurface for part in hintLower.split()):
            hits += 1
    return hits * 2.5


def buildUnitTypeBoostBase(units: list[Unit]) -> dict[str, dict[int, float]]:
    typeSurfaces = [compactText(f"{unit.reportName} {unit.sectionTitle}") for unit in units]
    out: dict[str, dict[int, float]] = {}
    for spec in PROBE_QUERIES:
        unitScores: dict[int, float] = {}
        for unitId, typeSurface in enumerate(typeSurfaces):
            base = typeHintBase(typeSurface, spec)
            if base > 0:
                unitScores[unitId] = base
        out[spec.query] = unitScores
    return out


def buildRelationFocusStemIds(stemToId: dict[str, int]) -> set[int]:
    stems: set[str] = set()
    for spec in PROBE_QUERIES:
        stems.update(extractStems(spec.query, cap=32))
        for left, right in spec.relationPairs:
            stems.update(extractStems(f"{left} {right}", cap=8))
        stems.update(extractStems(" ".join(spec.mustAny), cap=32))
    out: set[int] = set()
    for stem in stems:
        stemId = stemToId.get(stem)
        if stemId is not None:
            out.add(stemId)
    return out


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

    relationFocusStemIds = buildRelationFocusStemIds(stemToId)
    pairUnitsBuild: dict[tuple[int, int], list[int]] = defaultdict(list)
    unitTableLike = [isTableLike(unit) for unit in units]
    unitTypeBoostBase = buildUnitTypeBoostBase(units)
    for unitId, sequence in enumerate(postingTable):
        if len(sequence) < 2:
            continue
        seenPairs: set[tuple[int, int]] = set()
        seqLen = len(sequence)
        for leftPos, leftStem in enumerate(sequence):
            rightLimit = min(seqLen, leftPos + PAIR_INDEX_WINDOW + 1)
            for rightStem in sequence[leftPos + 1 : rightLimit]:
                if leftStem == rightStem:
                    continue
                if leftStem not in relationFocusStemIds or rightStem not in relationFocusStemIds:
                    continue
                pair = (leftStem, rightStem) if leftStem < rightStem else (rightStem, leftStem)
                seenPairs.add(pair)
        for pair in seenPairs:
            postings = pairUnitsBuild[pair]
            if len(postings) < PAIR_INDEX_MAX_UNITS:
                postings.append(unitId)

    elapsed = time.perf_counter() - t0
    print(
        f"[build] units={len(units):,} stems={len(idToStem):,} "
        f"postings={sum(len(seq) for seq in postingTable):,} buckets={HORIZON_BUCKETS:,} "
        f"focusStems={len(relationFocusStemIds):,} pairs={len(pairUnitsBuild):,} "
        f"pairPostings={sum(len(v) for v in pairUnitsBuild.values()):,} "
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
        pairUnits=dict(pairUnitsBuild),
        unitTableLike=unitTableLike,
        unitTypeBoostBase=unitTypeBoostBase,
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


def buildQueryProfile(model: Model, queryIds: list[int]) -> tuple[Counter[int], float]:
    queryProfile: Counter[int] = Counter()
    for stemId in queryIds:
        for dim, score in topProfileDims(model.fireTable[stemId]):
            queryProfile[dim] += score
    queryNorm = math.sqrt(sum(value * value for value in queryProfile.values()))
    return queryProfile, queryNorm


def expandQueryForCandidateStems(model: Model, queryIds: list[int], candidateStemIds: set[int]) -> dict[int, float]:
    queryProfile, queryNorm = buildQueryProfile(model, queryIds)
    if queryNorm <= 0:
        return {}
    querySet = set(queryIds)
    maxDf = max(int(len(model.units) * 0.12), 200)
    expanded: dict[int, float] = {}
    for stemId in candidateStemIds:
        if stemId in querySet:
            continue
        df = len(model.stemUnits[stemId])
        if df > maxDf or df == 0:
            continue
        profile = model.fireTable[stemId]
        if not profile:
            continue
        if len(profile) < len(queryProfile):
            dot = sum(value * queryProfile.get(dim, 0.0) for dim, value in profile.items())
        else:
            dot = sum(value * profile.get(dim, 0.0) for dim, value in queryProfile.items())
        if dot <= 0:
            continue
        norm = model.fireNorm[stemId]
        if norm <= 0:
            continue
        expanded[stemId] = dot / (queryNorm * norm * math.sqrt(max(df, 1)))
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


def relationStats(sequence: tuple[int, ...], queryIds: list[int]) -> tuple[int, int]:
    querySet = set(queryIds)
    orderedPositions: list[tuple[int, int]] = [
        (pos, stemId) for pos, stemId in enumerate(sequence) if stemId in querySet
    ]
    if len(orderedPositions) < 2:
        return 0, 0
    adjacentPairs = 0
    nearPairs = 0
    for leftIdx, (leftPos, leftStem) in enumerate(orderedPositions):
        for rightPos, rightStem in orderedPositions[leftIdx + 1 :]:
            if leftStem == rightStem:
                continue
            span = rightPos - leftPos
            if span == 1:
                adjacentPairs += 1
            if span <= RELATION_SPAN_LIMIT:
                nearPairs += 1
    return adjacentPairs, nearPairs


def relationSurfaceHits(unit: Unit, spec: QuerySpec) -> int:
    surface = compactText(f"{unit.reportName} {unit.sectionTitle} {unit.text}")
    hits = 0
    for left, right in spec.relationPairs:
        leftAt = surface.find(left.lower())
        rightAt = surface.find(right.lower())
        if leftAt < 0 or rightAt < 0:
            continue
        if abs(leftAt - rightAt) <= 120:
            hits += 1
    return hits


def queryRelationScores(model: Model, queryIds: list[int]) -> Counter[int]:
    relationScores: Counter[int] = Counter()
    uniqueIds = list(dict.fromkeys(queryIds))
    if len(uniqueIds) < 2:
        return relationScores
    for leftIdx, leftStem in enumerate(uniqueIds):
        for rightStem in uniqueIds[leftIdx + 1 :]:
            if leftStem == rightStem:
                continue
            pair = (leftStem, rightStem) if leftStem < rightStem else (rightStem, leftStem)
            for unitId in model.pairUnits.get(pair, ()):
                relationScores[unitId] += 1
    return relationScores


def queryTypeBoost(model: Model, query: str, unitId: int, coverage: float) -> float:
    unitScores = model.unitTypeBoostBase.get(query)
    if not unitScores:
        return 0.0
    base = unitScores.get(unitId, 0.0)
    if base <= 0:
        return 0.0
    return min(10.0, base * max(coverage, 0.5))


def search(
    model: Model, query: str, *, topK: int = TOP_K, useFire: bool = True
) -> list[tuple[float, int, list[str], list[str]]]:
    queryIds = resolveQueryIds(model, query)
    spec = QUERY_SPEC_BY_QUERY.get(query)
    scores: Counter[int] = Counter()
    exactHits: dict[int, set[int]] = defaultdict(set)
    expandedHits: dict[int, set[int]] = defaultdict(set)
    maxPostingsPerStem = max(int(len(model.units) * 0.08), 300)

    for stemId in queryIds:
        for unitId in model.stemUnits[stemId][:maxPostingsPerStem]:
            scores[unitId] += 20.0
            exactHits[unitId].add(stemId)

    relationScores = queryRelationScores(model, queryIds)
    candidateStemIds: set[int] = set()
    fireCandidateUnitIds: set[int] = set()
    if useFire:
        fireCandidateUnitIds = {unitId for unitId, _ in scores.most_common(max(FIRE_RERANK_CANDIDATES, topK * 4))}
        for unitId in fireCandidateUnitIds:
            candidateStemIds.update(model.postingTable[unitId])
    expanded = expandQueryForCandidateStems(model, queryIds, candidateStemIds) if useFire else {}
    expandedSet = set(expanded)

    queryStems = [model.idToStem[sid] for sid in queryIds]
    queryText = " ".join(queryStems)
    for unitId in list(scores):
        unit = model.units[unitId]
        sequence = model.postingTable[unitId]
        unitStemIds = set(sequence)
        coverage = len(exactHits.get(unitId, set())) / max(len(queryIds), 1)
        pairHits = relationScores.get(unitId, 0)
        scores[unitId] += 30.0 * coverage
        scores[unitId] += min(RELATION_PAIR_BONUS, 4.0 * pairHits)
        titleSurface = f"{unit.reportName} {unit.sectionTitle}".lower()
        if any(stem.lower() in titleSurface for stem in queryStems):
            scores[unitId] += 6.0
        if queryText and queryText in titleSurface:
            scores[unitId] += 8.0
        scores[unitId] += queryTypeBoost(model, query, unitId, coverage)
        if model.unitTableLike[unitId] and coverage < 1.0 and pairHits == 0:
            scores[unitId] -= TABLE_PENALTY
        if useFire and expanded and unitId in fireCandidateUnitIds and coverage >= 0.67 and pairHits > 0:
            semanticStemIds = sorted(unitStemIds & expandedSet, key=lambda sid: expanded[sid], reverse=True)[:6]
            for stemId in semanticStemIds:
                expandedHits[unitId].add(stemId)
            if semanticStemIds:
                scores[unitId] += min(FIRE_TIE_BREAK_WEIGHT, sum(expanded[stemId] for stemId in semanticStemIds) * 0.08)

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


def compactText(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "")).strip().lower()


def isTableLike(unit: Unit) -> bool:
    text = unit.text
    if "|" in text or "<td" in text.lower() or "</td>" in text.lower():
        return True
    sample = text[:600]
    visible = [ch for ch in sample if not ch.isspace()]
    if not visible:
        return False
    digitCount = sum(1 for ch in visible if ch.isdigit())
    separatorCount = sum(1 for ch in visible if ch in ",.-()%")
    return (digitCount + separatorCount) / len(visible) >= 0.42


def isNoisyStem(stem: str) -> bool:
    lower = stem.lower()
    if any(marker in lower for marker in XBRL_MARKERS):
        return True
    if len(stem) > 24:
        return True
    if "/" in stem or "\\" in stem:
        return True
    digitCount = sum(1 for ch in stem if ch.isdigit())
    if digitCount and digitCount / max(len(stem), 1) >= 0.35:
        return True
    if sum(1 for ch in stem if ch in ".-%_") >= 2:
        return True
    return False


def estimateMemoryMb(model: Model) -> float:
    postingCells = sum(len(seq) for seq in model.postingTable)
    unitChars = sum(len(unit.text) + len(unit.sectionTitle) + len(unit.reportName) for unit in model.units)
    fireCells = sum(len(profile) for profile in model.fireTable)
    pairCells = sum(len(unitIds) for unitIds in model.pairUnits.values())
    typeCells = sum(len(unitScores) for unitScores in model.unitTypeBoostBase.values())
    stemChars = sum(len(stem) for stem in model.idToStem)
    roughBytes = postingCells * 4 + unitChars * 2 + fireCells * 12 + pairCells * 4 + typeCells * 8 + stemChars * 2
    return roughBytes / 1024 / 1024


def unitQuality(unit: Unit, spec: QuerySpec) -> int:
    surface = compactText(f"{unit.reportName} {unit.sectionTitle} {unit.text}")
    mustHit = any(term.lower() in surface for term in spec.mustAny)
    supportHit = any(term.lower() in surface for term in spec.supportAny)
    relationHit = relationSurfaceHits(unit, spec) > 0
    if mustHit and (supportHit or relationHit):
        return 2
    if mustHit:
        return 1
    return 0


def rubricQuality(unit: Unit, spec: QuerySpec) -> int:
    if not spec.rubricGroups:
        return unitQuality(unit, spec)
    surface = compactText(f"{unit.reportName} {unit.sectionTitle} {unit.text}")
    if any(term.lower() in surface for term in spec.badAny):
        return 0
    groupHits = 0
    for group in spec.rubricGroups:
        if any(term.lower() in surface for term in group):
            groupHits += 1
    if groupHits == len(spec.rubricGroups):
        return 2
    if groupHits >= max(1, len(spec.rubricGroups) - 1):
        return 1
    return 0


def summarizeMode(model: Model, spec: QuerySpec, *, useFire: bool) -> dict[str, object]:
    t0 = time.perf_counter()
    rows = search(model, spec.query, useFire=useFire)
    latencyMs = (time.perf_counter() - t0) * 1000
    qualities = [unitQuality(model.units[unitId], spec) for _, unitId, _, _ in rows]
    rubricQualities = [rubricQuality(model.units[unitId], spec) for _, unitId, _, _ in rows]
    seen: set[str] = set()
    duplicateCount = 0
    tableCount = 0
    for _, unitId, _, _ in rows:
        unit = model.units[unitId]
        key = compactText(unit.text)[:180]
        if key in seen:
            duplicateCount += 1
        seen.add(key)
        if isTableLike(unit):
            tableCount += 1
    return {
        "rows": rows,
        "latencyMs": latencyMs,
        "qualitySum": sum(qualities),
        "strongHits": sum(1 for q in qualities if q == 2),
        "weakHits": sum(1 for q in qualities if q >= 1),
        "rubricQualitySum": sum(rubricQualities),
        "rubricStrongHits": sum(1 for q in rubricQualities if q == 2),
        "rubricWeakHits": sum(1 for q in rubricQualities if q >= 1),
        "duplicates": duplicateCount,
        "tables": tableCount,
    }


def summarizeNoise(model: Model, limit: int = 20) -> tuple[int, float, list[str]]:
    noisy = [stem for stem in model.idToStem if isNoisyStem(stem)]
    examples = sorted(noisy, key=lambda stem: (-len(stem), stem))[:limit]
    return len(noisy), len(noisy) / max(len(model.idToStem), 1), examples


def printRows(model: Model, rows: list[tuple[float, int, list[str], list[str]]]) -> None:
    for rank, (score, unitId, exact, semantic) in enumerate(rows, start=1):
        unit = model.units[unitId]
        text = unit.text.replace("\n", " ")
        if len(text) > 160:
            text = text[:160] + "..."
        print(
            f"    {rank}. score={score:.2f} corp={unit.corpName} stock={unit.stockCode} "
            f"rcept={unit.rceptNo} section={unit.sectionTitle}"
        )
        print(f"       exact={exact} semantic={semantic}")
        print(f"       text={text}")


def evaluateExperiment(model: Model) -> None:
    print("\n" + "=" * 88)
    print("[evaluation] exact-only vs exact+fire")
    print("=" * 88)
    noiseCount, noiseRatio, noiseExamples = summarizeNoise(model)
    print(
        f"[model] roughMemoryMb={estimateMemoryMb(model):.1f} noisyStems={noiseCount:,}/{len(model.idToStem):,} ({noiseRatio:.1%})"
    )
    print(f"[noise examples] {noiseExamples[:12]}")

    exactTotal = 0
    fireTotal = 0
    exactRubricTotal = 0
    fireRubricTotal = 0
    improved = 0
    worsened = 0
    same = 0
    rubricImproved = 0
    rubricWorsened = 0
    rubricSame = 0
    exactLatency: list[float] = []
    fireLatency: list[float] = []
    duplicateTotal = 0
    tableTotal = 0

    for spec in PROBE_QUERIES:
        exact = summarizeMode(model, spec, useFire=False)
        fire = summarizeMode(model, spec, useFire=True)
        exactScore = int(exact["qualitySum"])
        fireScore = int(fire["qualitySum"])
        exactRubricScore = int(exact["rubricQualitySum"])
        fireRubricScore = int(fire["rubricQualitySum"])
        exactTotal += exactScore
        fireTotal += fireScore
        exactRubricTotal += exactRubricScore
        fireRubricTotal += fireRubricScore
        exactLatency.append(float(exact["latencyMs"]))
        fireLatency.append(float(fire["latencyMs"]))
        duplicateTotal += int(fire["duplicates"])
        tableTotal += int(fire["tables"])
        if fireScore > exactScore:
            verdict = "IMPROVED"
            improved += 1
        elif fireScore < exactScore:
            verdict = "WORSENED"
            worsened += 1
        else:
            verdict = "SAME"
            same += 1
        if fireRubricScore > exactRubricScore:
            rubricVerdict = "IMPROVED"
            rubricImproved += 1
        elif fireRubricScore < exactRubricScore:
            rubricVerdict = "WORSENED"
            rubricWorsened += 1
        else:
            rubricVerdict = "SAME"
            rubricSame += 1

        print("\n" + "-" * 88)
        print(
            f"[query] {spec.query} verdict={verdict} rubricVerdict={rubricVerdict} "
            f"exactQuality={exactScore} fireQuality={fireScore} "
            f"exactRubric={exactRubricScore} fireRubric={fireRubricScore} "
            f"exactMs={float(exact['latencyMs']):.2f} fireMs={float(fire['latencyMs']):.2f} "
            f"fireDup={fire['duplicates']} fireTable={fire['tables']}"
        )
        print("  [exact-only top5]")
        printRows(model, exact["rows"])  # type: ignore[arg-type]
        print("  [exact+fire top5]")
        printRows(model, fire["rows"])  # type: ignore[arg-type]

    print("\n" + "=" * 88)
    print(
        f"[summary] exactQuality={exactTotal} fireQuality={fireTotal} "
        f"improved={improved} same={same} worsened={worsened} "
        f"exactRubric={exactRubricTotal} fireRubric={fireRubricTotal} "
        f"rubricImproved={rubricImproved} rubricSame={rubricSame} rubricWorsened={rubricWorsened} "
        f"exactAvgMs={sum(exactLatency) / len(exactLatency):.2f} "
        f"fireAvgMs={sum(fireLatency) / len(fireLatency):.2f} "
        f"fireDuplicateTop5={duplicateTotal} fireTableTop5={tableTotal}"
    )


def main() -> None:
    print("=" * 88)
    print("Horizon Posting Meaning Search v10")
    print("=" * 88)
    print(
        f"[config] maxUnits={MAX_UNITS:,} buckets={HORIZON_BUCKETS:,} window={WINDOW} "
        f"semWeight={SEMANTIC_WEIGHT:g} fireCandidates={FIRE_RERANK_CANDIDATES:,} "
        f"fireTie={FIRE_TIE_BREAK_WEIGHT:g} tablePenalty={TABLE_PENALTY:g} "
        f"relSpan={RELATION_SPAN_LIMIT} pairWindow={PAIR_INDEX_WINDOW} pairMaxUnits={PAIR_INDEX_MAX_UNITS:,}"
    )

    t0 = time.perf_counter()
    units = collectUnits()
    if not units:
        raise SystemExit("no units collected from data/dart/allFilings or data/dart/docs")
    model = buildModel(units)
    evaluateExperiment(model)
    print("\n" + "=" * 88)
    print(f"[done] totalSeconds={time.perf_counter() - t0:.1f} buildSeconds={model.buildSeconds:.1f}")


if __name__ == "__main__":
    main()
