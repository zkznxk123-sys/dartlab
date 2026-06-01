"""Horizon Meaning Learner V193 - fragment-first meaning capsule.

아이디어:
    V190/V191 은 canonical snakeId token typed sibling proof 로 open held-out 에서 작은 신호를 보였지만,
    accountMappings 중심이었다. V192 predictive contrast capsule 은 실패했다. 원인은 canonical snakeId token 기반
    capsule 이 `cash/flow/operating` 같은 넓은 statement 경험을 잘못된 후보에도 보상했기 때문이다.

    V193 은 원래 목표로 되돌아간다. 학습 단위는 account alias 가 아니라 `data/dart/panel/{corp}/{period}.parquet`
    의 block/contentRaw 이다. `allFilings` 는 넓은 raw filing/event context 로, `panelCell` 은 statement/value/label
    anchor 로만 붙인다. 수평선 좌표는 의미가 아니라 빠른 주소이며, 의미는 fragment/block/cell 주변 경험을 sparse
    proof object, 즉 meaning capsule 로 응결해 비교한다.

    절차:
    - panel block 을 독립 fragment 로 읽고 chapter/section/block/order/xbrl/contentRaw 경험을 capsule atom 으로 만든다.
    - allFilings raw filing 은 report/event context fragment 로 잘라 같은 capsule 공간에 넣는다.
    - panelCell label/statement/axis 는 전역 label hint 로 만들고, query/fragment text 가 label fragment 를 공유하면
      cell statement/value anchor atom 을 추가한다.
    - query 도 같은 방식으로 capsule 을 만든다.
    - posting 으로 후보를 빠르게 모은 뒤 surface baseline 과 capsule scorer 를 나란히 비교한다.
    - scorer 는 capsule overlap, 같은 target cohort 안의 contrast contradiction, query core role residual 을 본다.

실행 코드:
    uv run python -X utf8 -m py_compile tests/_attempts/horizonMeaning/horizonMeaningLearnerV193Test.py
    uv run python -X utf8 tests/_attempts/horizonMeaning/horizonMeaningLearnerV193Test.py
    $env:DARTLAB_HORIZON_V193_PANEL_FILE_LIMIT='220'; $env:DARTLAB_HORIZON_V193_ALL_FILINGS_FILE_LIMIT='32'; uv run python -X utf8 tests/_attempts/horizonMeaning/horizonMeaningLearnerV193Test.py

검증 기준:
    - accountMappings 는 학습 중심이 아니라 보조 guard 로만 사용한다.
    - 문서/공시 의미 probe 8 개를 surface baseline 과 capsule ranker 로 동시에 평가한다.
    - 각 probe 는 topK 의 corp/period/chapter/section/report/rceptNo/snippet/proof 를 출력한다.
    - rubric 은 semantic hit, exact-only, contradiction, boilerplate, cell anchor 사용 여부를 본다.
    - 80 수준 smoke 에서 capsule 이 surface baseline 보다 의미 hit 를 못 올리면 실패로 기록한다.

결과:
    기본 smoke 는 fragments=10724, panelFiles=120, panelRows=11428, allFilingFiles=18, allFilingRows=504,
    cellFiles=0, cellRows=0, cellHintTerms=0, atoms=80866, postings=75440 이었다. 현재 로컬 워크트리에는
    `data/dart/panelCell` 이 없어 panelCell anchor 는 비활성으로 확인됐다.

    초안은 noData/negation 을 proof object 로 보지 않아 `전환사채 발행`, `유상증자 발행 조건` 에서
    `해당사항 없습니다` block 을 상위로 올렸다. 이후 `role:negation:noData`, `negated:*` atom 을 추가하고
    같은 target 안에서 mixed contrast(`inflow` query 후보에 `outflow`, `investing` query 후보에 `operating` 등) 를
    contradiction 으로 잡게 했다.

    최종 smoke 는 baselineTop1Semantic=6/8, baselineTop3Semantic=6/8, capsuleTop1Semantic=6/8,
    capsuleTop3Semantic=6/8, capsuleTop1ExactOnly=0, capsuleTop1Contradiction=1, capsuleTop1CellAnchored=0,
    queryCellAnchored=0 이었다. accountGuard 는 cases=40, top5SiblingEvidence=4/40 이었다.

결론:
    실패/진단 성공. V193 은 학습 단위를 panel/allFilings fragment 로 옮겼고 noData/contrast proof 를 capsule 안에
    넣었지만, smoke 에서 surface baseline 을 넘지 못했다. `현금 유입 투자활동` 은 한 block 안에 유입/유출/영업/투자
    경험이 섞여 target-specific statement path 가 필요했고, `영업권 손상` 은 target(goodwill) 은 맞지만 action(impairment)
    이 빠진 변동표가 계속 높았다. 다음은 단순 block capsule 이 아니라 panel block 을 sentence/table row 단위로 더 쪼개고,
    같은 block 내부에서도 role span 을 분리한 local capsule 을 만들어야 한다. panelCell anchor 는 로컬 데이터 부재로
    검증하지 못했다.
"""

from __future__ import annotations

import hashlib
import html
import math
import os
import re
import time
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path

import polars as pl

ROOT = Path(__file__).resolve().parents[3]
PANEL_DIR = ROOT / "data" / "dart" / "panel"
PANEL_CELL_DIR = ROOT / "data" / "dart" / "panelCell"
ALL_FILINGS_DIR = ROOT / "data" / "dart" / "allFilings"
MAPPING_PATH = ROOT / "src" / "dartlab" / "reference" / "data" / "accountMappings.json"

PANEL_FILE_LIMIT = int(os.environ.get("DARTLAB_HORIZON_V193_PANEL_FILE_LIMIT", "120"))
PANEL_ROWS_PER_FILE = int(os.environ.get("DARTLAB_HORIZON_V193_PANEL_ROWS_PER_FILE", "180"))
PANEL_CELL_FILE_LIMIT = int(os.environ.get("DARTLAB_HORIZON_V193_PANEL_CELL_FILE_LIMIT", "160"))
PANEL_CELL_ROWS_PER_FILE = int(os.environ.get("DARTLAB_HORIZON_V193_PANEL_CELL_ROWS_PER_FILE", "220"))
ALL_FILINGS_FILE_LIMIT = int(os.environ.get("DARTLAB_HORIZON_V193_ALL_FILINGS_FILE_LIMIT", "18"))
ALL_FILINGS_ROWS_PER_FILE = int(os.environ.get("DARTLAB_HORIZON_V193_ALL_FILINGS_ROWS_PER_FILE", "28"))
ALL_FILINGS_CHARS = int(os.environ.get("DARTLAB_HORIZON_V193_ALL_FILINGS_CHARS", "2600"))
MAX_FRAGMENTS = int(os.environ.get("DARTLAB_HORIZON_V193_MAX_FRAGMENTS", "16000"))
POSTING_ATOM_LIMIT = int(os.environ.get("DARTLAB_HORIZON_V193_POSTING_ATOM_LIMIT", "360"))
CANDIDATE_LIMIT = int(os.environ.get("DARTLAB_HORIZON_V193_CANDIDATE_LIMIT", "900"))
TOP_K = int(os.environ.get("DARTLAB_HORIZON_V193_TOP_K", "5"))
ACCOUNT_GUARD_LIMIT = int(os.environ.get("DARTLAB_HORIZON_V193_ACCOUNT_GUARD_LIMIT", "40"))

TAG_RE = re.compile(r"<[^>]+>")
SPACE_RE = re.compile(r"\s+")
NUM_RE = re.compile(r"\d")
HANGUL_RE = re.compile(r"[가-힣]+")
TOKEN_RE = re.compile(r"[가-힣A-Za-z0-9]+")


@dataclass(frozen=True)
class Probe:
    query: str
    expected: frozenset[str]
    anti: frozenset[str]


@dataclass
class Fragment:
    idx: int
    source: str
    corp: str
    period: str
    rceptNo: str
    reportNm: str
    chapter: str
    section: str
    block: str
    order: int
    text: str
    snippet: str
    capsule: Counter[str]
    terms: frozenset[str]
    anchors: frozenset[str]


@dataclass(frozen=True)
class SearchRow:
    fragment: Fragment
    score: float
    surfaceScore: float
    sharedAtoms: tuple[str, ...]
    contradiction: tuple[str, ...]
    residual: tuple[str, ...]


ROLE_RULES: tuple[tuple[str, str, tuple[str, ...]], ...] = (
    ("action", "issue", ("발행", "유상증자", "신주", "공모", "사모")),
    ("action", "redeem", ("상환", "소각", "조기상환", "만기상환")),
    ("action", "change", ("변경", "변동", "교체", "정정")),
    ("action", "acquire", ("취득", "매입", "인수", "매수", "보유")),
    ("action", "dispose", ("처분", "매각", "양도", "제거")),
    ("action", "payment", ("지급", "배당", "지출", "상환", "납부")),
    ("action", "inflow", ("유입", "수입", "입금", "수취", "회수")),
    ("action", "outflow", ("유출", "지출", "지급", "상환", "납부")),
    ("action", "increase", ("증가", "증대", "증액", "확대")),
    ("action", "decrease", ("감소", "감액", "축소", "차감")),
    ("action", "impairment", ("손상", "손상차손", "감액손실")),
    ("action", "lawsuit", ("소송", "피소", "분쟁", "청구")),
    ("target", "capitalIncrease", ("유상증자", "증자", "신주", "자본금")),
    ("target", "majorShareholder", ("최대주주", "주요주주", "대주주")),
    ("target", "treasuryStock", ("자기주식", "자사주")),
    ("target", "convertibleBond", ("전환사채", "전환사채권", "cb")),
    ("target", "bond", ("사채", "채권", "회사채")),
    ("target", "dividend", ("배당", "현금배당", "현물배당")),
    ("target", "cash", ("현금", "예금", "현금및현금성자산")),
    ("target", "litigation", ("소송", "분쟁", "우발", "청구")),
    ("target", "provision", ("충당부채", "충당금", "충당")),
    ("target", "goodwill", ("영업권", "영업권손상")),
    ("target", "investment", ("투자", "투자활동", "관계기업", "종속기업")),
    ("target", "asset", ("자산", "유형자산", "무형자산", "금융자산")),
    ("target", "debt", ("부채", "차입", "차입금", "채무")),
    ("statement", "cashflow", ("현금흐름", "영업활동", "투자활동", "재무활동", "cf")),
    ("statement", "balance", ("재무상태표", "자산", "부채", "자본", "bs")),
    ("statement", "income", ("손익계산서", "포괄손익", "매출", "수익", "비용", "is")),
    ("modifier", "condition", ("조건", "발행가액", "행사가액", "만기", "이율", "기간")),
    ("modifier", "investing", ("투자활동", "투자")),
    ("modifier", "operating", ("영업활동", "영업")),
    ("modifier", "financing", ("재무활동", "재무")),
    ("modifier", "current", ("유동", "단기")),
    ("modifier", "noncurrent", ("비유동", "장기")),
    ("modifier", "amount", ("금액", "가액", "총액", "액면")),
)

NO_DATA_TERMS = (
    "해당사항 없습니다",
    "해당사항없습니다",
    "해당 사항 없습니다",
    "내역 없음",
    "내역없음",
    "발행내용은 없습니다",
    "변동사항 없음",
    "없습니다",
    "없음",
)

CONTRAST_GROUPS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("flow", ("inflow", "outflow")),
    ("delta", ("increase", "decrease")),
    ("deal", ("acquire", "dispose")),
    ("issueRedeem", ("issue", "redeem")),
    ("activity", ("operating", "investing", "financing")),
    ("maturity", ("current", "noncurrent")),
)

PROBES: tuple[Probe, ...] = (
    Probe(
        "유상증자 발행 조건",
        frozenset({"action:issue", "target:capitalIncrease", "modifier:condition"}),
        frozenset({"action:redeem"}),
    ),
    Probe("최대주주 변경", frozenset({"action:change", "target:majorShareholder"}), frozenset()),
    Probe(
        "현금 유입 투자활동",
        frozenset({"action:inflow", "target:cash", "modifier:investing"}),
        frozenset({"action:outflow", "modifier:financing"}),
    ),
    Probe("소송 충당부채", frozenset({"action:lawsuit", "target:litigation", "target:provision"}), frozenset()),
    Probe("자기주식 취득", frozenset({"action:acquire", "target:treasuryStock"}), frozenset({"action:dispose"})),
    Probe("전환사채 발행", frozenset({"action:issue", "target:convertibleBond"}), frozenset({"action:redeem"})),
    Probe("배당 지급", frozenset({"action:payment", "target:dividend"}), frozenset()),
    Probe("영업권 손상", frozenset({"action:impairment", "target:goodwill"}), frozenset()),
)


def cleanText(value: object, *, limit: int | None = None) -> str:
    text = "" if value is None else str(value)
    if limit is not None and len(text) > limit:
        text = text[:limit]
    text = html.unescape(text)
    text = TAG_RE.sub(" ", text)
    text = text.replace("\u00a0", " ")
    text = SPACE_RE.sub(" ", text).strip()
    return text


def compactText(value: str) -> str:
    return re.sub(r"[^0-9A-Za-z가-힣]+", "", value).lower()


def stableHashInt(value: str) -> int:
    return int(hashlib.blake2b(value.encode("utf-8"), digest_size=8).hexdigest(), 16)


def normalizedTerms(value: str) -> frozenset[str]:
    terms: set[str] = set()
    for token in TOKEN_RE.findall(value.lower()):
        if len(token) < 2:
            continue
        if NUM_RE.fullmatch(token):
            continue
        if HANGUL_RE.fullmatch(token):
            if len(token) <= 12:
                terms.add(token)
            for size in (2, 3, 4, 5):
                if len(token) < size:
                    continue
                for index in range(len(token) - size + 1):
                    gram = token[index : index + size]
                    if not NUM_RE.search(gram):
                        terms.add(gram)
        else:
            terms.add(token[:24])
    return frozenset(terms)


def roleHits(value: str) -> dict[str, set[str]]:
    compact = compactText(value)
    hits: dict[str, set[str]] = defaultdict(set)
    for role, key, terms in ROLE_RULES:
        for term in terms:
            normalized = compactText(term)
            if normalized and normalized in compact:
                hits[role].add(key)
                break
    return hits


def hasNoDataEvidence(value: str) -> bool:
    compact = compactText(value)
    return any(compactText(term) in compact for term in NO_DATA_TERMS)


def roleAtoms(hits: dict[str, set[str]]) -> set[str]:
    return {f"{role}:{key}" for role, keys in hits.items() for key in keys}


def rolePairAtoms(hits: dict[str, set[str]]) -> Counter[str]:
    atoms: Counter[str] = Counter()
    targets = sorted(hits.get("target", ()))
    actions = sorted(hits.get("action", ()))
    modifiers = sorted(hits.get("modifier", ()))
    statements = sorted(hits.get("statement", ()))
    for target in targets:
        for action in actions:
            atoms[f"cap:targetAction:{target}|{action}"] += 4.0
        for modifier in modifiers:
            atoms[f"cap:targetModifier:{target}|{modifier}"] += 2.8
        for statement in statements:
            atoms[f"cap:targetStatement:{target}|{statement}"] += 2.2
    for statement in statements:
        for action in actions:
            atoms[f"cap:statementAction:{statement}|{action}"] += 2.6
        for modifier in modifiers:
            atoms[f"cap:statementModifier:{statement}|{modifier}"] += 1.8
    return atoms


def capsuleForText(
    text: str,
    *,
    source: str,
    chapter: str = "",
    section: str = "",
    block: str = "",
    reportNm: str = "",
    xbrlClass: str = "",
    xbrlMatched: bool = False,
    cellHints: dict[str, Counter[str]] | None = None,
) -> tuple[Counter[str], frozenset[str], frozenset[str]]:
    joined = " ".join(item for item in (text, chapter, section, block, reportNm, xbrlClass) if item)
    terms = normalizedTerms(joined)
    hits = roleHits(joined)
    capsule: Counter[str] = Counter()
    anchors: set[str] = set()

    capsule[f"src:{source}"] += 0.7
    if xbrlMatched:
        capsule["xbrl:matched"] += 1.2
    if xbrlClass:
        for term in normalizedTerms(xbrlClass):
            capsule[f"xbrl:{term}"] += 0.8
    for field, value in (("chapter", chapter), ("section", section), ("block", block), ("report", reportNm)):
        for term in tuple(normalizedTerms(value))[:12]:
            capsule[f"meta:{field}:{term}"] += 0.55
    for term in terms:
        if len(term) < 2:
            continue
        weight = 0.38
        if len(term) >= 4:
            weight += 0.12
        capsule[f"stem:{term}"] += weight
        capsule[f"addr:{stableHashInt(term) % 4096}"] += 0.03
    for atom in roleAtoms(hits):
        capsule[f"role:{atom}"] += 3.0
    capsule.update(rolePairAtoms(hits))
    if hasNoDataEvidence(joined):
        capsule["role:negation:noData"] += 5.0
        for role, keys in hits.items():
            for key in keys:
                capsule[f"negated:{role}:{key}"] += 2.5

    if cellHints:
        for term in terms:
            hints = cellHints.get(term)
            if not hints:
                continue
            anchors.add(term)
            for atom, weight in hints.items():
                capsule[atom] += min(3.0, float(weight))
    return capsule, terms, frozenset(anchors)


def selectedPanelFiles() -> list[Path]:
    files = sorted(PANEL_DIR.glob("*/*.parquet"), key=lambda path: (path.name, path.parent.name), reverse=True)
    preferred = [
        path for path in files if path.parent.name in {"005930", "000660", "035420", "000270", "005380", "000810"}
    ]
    rest = [path for path in files if path not in set(preferred)]
    return (preferred + rest)[:PANEL_FILE_LIMIT]


def selectedPanelCellFiles() -> list[Path]:
    files = sorted(PANEL_CELL_DIR.glob("*/*.parquet"), key=lambda path: (path.name, path.parent.name), reverse=True)
    preferred = [
        path for path in files if path.parent.name in {"005930", "000660", "035420", "000270", "005380", "000810"}
    ]
    rest = [path for path in files if path not in set(preferred)]
    return (preferred + rest)[:PANEL_CELL_FILE_LIMIT]


def selectedAllFilingFiles() -> list[Path]:
    files = [path for path in ALL_FILINGS_DIR.glob("*.parquet") if not path.name.endswith("_meta.parquet")]
    return sorted(files, key=lambda path: path.stem, reverse=True)[:ALL_FILINGS_FILE_LIMIT]


def buildCellHints() -> tuple[dict[str, Counter[str]], Counter[str]]:
    hints: dict[str, Counter[str]] = defaultdict(Counter)
    stats: Counter[str] = Counter()
    stats["cellDirExists"] = int(PANEL_CELL_DIR.exists())
    for path in selectedPanelCellFiles():
        try:
            df = (
                pl.scan_parquet(str(path))
                .select(
                    "statement",
                    "label",
                    "axisPath",
                    "valueRaw",
                    "corp",
                    "filingPeriod",
                )
                .head(PANEL_CELL_ROWS_PER_FILE)
                .collect()
            )
        except Exception as exc:  # pragma: no cover - attempts diagnostic
            stats[f"cellError:{type(exc).__name__}"] += 1
            continue
        stats["cellFiles"] += 1
        stats["cellRows"] += df.height
        for row in df.iter_rows(named=True):
            label = cleanText(row.get("label"))
            if len(label) < 2:
                continue
            statement = cleanText(row.get("statement"))
            axis = cleanText(row.get("axisPath"))
            value = cleanText(row.get("valueRaw"))
            labelTerms = normalizedTerms(label)
            labelHits = roleHits(label)
            atoms: Counter[str] = Counter()
            if statement:
                atoms[f"cell:statement:{statement.lower()}"] += 1.6
                if statement.upper() == "CF":
                    atoms["role:statement:cashflow"] += 1.6
                elif statement.upper() == "BS":
                    atoms["role:statement:balance"] += 1.4
                elif statement.upper() in {"IS", "CIS"}:
                    atoms["role:statement:income"] += 1.4
            for atom in roleAtoms(labelHits):
                atoms[f"cell:{atom}"] += 1.2
                atoms[f"role:{atom}"] += 0.9
            for pair, weight in rolePairAtoms(labelHits).items():
                atoms[pair] += min(1.2, float(weight) * 0.25)
            if axis and axis.lower() not in {"", "none", "null"}:
                for term in tuple(normalizedTerms(axis))[:4]:
                    atoms[f"cell:axis:{term}"] += 0.45
            if value:
                atoms["cell:valuePresent"] += 0.3
            for term in labelTerms:
                hints[term].update(atoms)
    return {term: Counter(dict(values.most_common(16))) for term, values in hints.items()}, stats


def readPanelFragments(cellHints: dict[str, Counter[str]]) -> tuple[list[Fragment], Counter[str]]:
    fragments: list[Fragment] = []
    stats: Counter[str] = Counter()
    for path in selectedPanelFiles():
        if len(fragments) >= MAX_FRAGMENTS:
            break
        try:
            df = (
                pl.scan_parquet(str(path))
                .select(
                    "chapter",
                    "sectionLeaf",
                    "blockLeaf",
                    "xbrlClass",
                    "xbrlMatched",
                    "blockOrder",
                    "contentRaw",
                    "period",
                    "corp",
                    "rceptNo",
                    "disclosureKey",
                )
                .head(PANEL_ROWS_PER_FILE)
                .collect()
            )
        except Exception as exc:  # pragma: no cover - attempts diagnostic
            stats[f"panelError:{type(exc).__name__}"] += 1
            continue
        stats["panelFiles"] += 1
        stats["panelRows"] += df.height
        for row in df.iter_rows(named=True):
            text = cleanText(row.get("contentRaw"), limit=2400)
            if len(text) < 24:
                continue
            chapter = cleanText(row.get("chapter"))
            section = cleanText(row.get("sectionLeaf"))
            block = cleanText(row.get("blockLeaf"))
            capsule, terms, anchors = capsuleForText(
                text,
                source="panel",
                chapter=chapter,
                section=section,
                block=block,
                xbrlClass=cleanText(row.get("xbrlClass")),
                xbrlMatched=bool(row.get("xbrlMatched")),
                cellHints=cellHints,
            )
            fragments.append(
                Fragment(
                    idx=len(fragments),
                    source="panel",
                    corp=cleanText(row.get("corp")),
                    period=cleanText(row.get("period")),
                    rceptNo=cleanText(row.get("rceptNo")),
                    reportNm="",
                    chapter=chapter,
                    section=section,
                    block=block,
                    order=int(row.get("blockOrder") or 0),
                    text=text,
                    snippet=text[:260],
                    capsule=capsule,
                    terms=terms,
                    anchors=anchors,
                )
            )
    addNeighborExperience(fragments)
    return fragments, stats


def readAllFilingFragments(cellHints: dict[str, Counter[str]]) -> tuple[list[Fragment], Counter[str]]:
    fragments: list[Fragment] = []
    stats: Counter[str] = Counter()
    for path in selectedAllFilingFiles():
        if len(fragments) >= MAX_FRAGMENTS:
            break
        try:
            df = (
                pl.scan_parquet(str(path))
                .select("stock_code", "corp_name", "rcept_no", "report_nm", "content_raw", "fetch_status")
                .filter(pl.col("fetch_status").fill_null("") == "ok")
                .head(ALL_FILINGS_ROWS_PER_FILE)
                .collect()
            )
        except Exception as exc:  # pragma: no cover - attempts diagnostic
            stats[f"allFilingError:{type(exc).__name__}"] += 1
            continue
        stats["allFilingFiles"] += 1
        stats["allFilingRows"] += df.height
        for row in df.iter_rows(named=True):
            report = cleanText(row.get("report_nm"))
            raw = cleanText(row.get("content_raw"), limit=ALL_FILINGS_CHARS)
            text = cleanText(f"{report} {raw}")
            if len(text) < 40:
                continue
            capsule, terms, anchors = capsuleForText(
                text,
                source="allFilings",
                reportNm=report,
                cellHints=cellHints,
            )
            fragments.append(
                Fragment(
                    idx=-1,
                    source="allFilings",
                    corp=cleanText(row.get("stock_code")),
                    period=path.stem,
                    rceptNo=cleanText(row.get("rcept_no")),
                    reportNm=report,
                    chapter=report,
                    section=cleanText(row.get("corp_name")),
                    block="",
                    order=0,
                    text=text,
                    snippet=text[:260],
                    capsule=capsule,
                    terms=terms,
                    anchors=anchors,
                )
            )
    return fragments, stats


def addNeighborExperience(fragments: list[Fragment]) -> None:
    grouped: dict[tuple[str, str, str], list[Fragment]] = defaultdict(list)
    for fragment in fragments:
        if fragment.source != "panel":
            continue
        grouped[(fragment.corp, fragment.period, fragment.rceptNo)].append(fragment)
    for rows in grouped.values():
        rows.sort(key=lambda item: item.order)
        for index, fragment in enumerate(rows):
            leftTerms = rows[index - 1].terms if index > 0 else frozenset()
            rightTerms = rows[index + 1].terms if index + 1 < len(rows) else frozenset()
            for term in tuple(sorted(leftTerms))[:10]:
                fragment.capsule[f"neighbor:left:{term}"] += 0.18
            for term in tuple(sorted(rightTerms))[:10]:
                fragment.capsule[f"neighbor:right:{term}"] += 0.18
            for roleAtom in sorted(atom for atom in fragment.capsule if atom.startswith("role:"))[:8]:
                if leftTerms:
                    fragment.capsule[f"order:leftRole:{roleAtom[5:]}"] += 0.25
                if rightTerms:
                    fragment.capsule[f"order:rightRole:{roleAtom[5:]}"] += 0.25


def buildFragments() -> tuple[list[Fragment], dict[str, Counter[str]], Counter[str]]:
    started = time.perf_counter()
    cellHints, cellStats = buildCellHints()
    panelFragments, panelStats = readPanelFragments(cellHints)
    allFilingFragments, allFilingStats = readAllFilingFragments(cellHints)
    fragments = panelFragments + allFilingFragments
    for index, fragment in enumerate(fragments):
        fragment.idx = index
    stats = Counter()
    stats.update(cellStats)
    stats.update(panelStats)
    stats.update(allFilingStats)
    stats["fragments"] = len(fragments)
    stats["cellHintTerms"] = len(cellHints)
    stats["buildMs"] = int((time.perf_counter() - started) * 1000)
    return fragments, cellHints, stats


def atomIdf(fragments: list[Fragment]) -> dict[str, float]:
    df: Counter[str] = Counter()
    for fragment in fragments:
        for atom in fragment.capsule:
            df[atom] += 1
    total = max(1, len(fragments))
    return {atom: math.log((total + 1.0) / (count + 0.5)) for atom, count in df.items()}


def weightedCapsule(capsule: Counter[str], idf: dict[str, float]) -> Counter[str]:
    weighted: Counter[str] = Counter()
    for atom, raw in capsule.items():
        atomIdfValue = max(0.05, idf.get(atom, 0.35))
        if atom.startswith("addr:"):
            atomIdfValue = min(atomIdfValue, 0.05)
        weighted[atom] = float(raw) * atomIdfValue
    return weighted


def buildPostings(fragments: list[Fragment], idf: dict[str, float]) -> dict[str, tuple[int, ...]]:
    postings: dict[str, list[int]] = defaultdict(list)
    for fragment in fragments:
        weighted = weightedCapsule(fragment.capsule, idf)
        for atom, _weight in weighted.most_common(POSTING_ATOM_LIMIT):
            if atom.startswith("addr:"):
                continue
            postings[atom].append(fragment.idx)
    return {atom: tuple(values) for atom, values in postings.items()}


def queryCapsule(
    query: str, cellHints: dict[str, Counter[str]], idf: dict[str, float]
) -> tuple[Counter[str], frozenset[str], frozenset[str]]:
    capsule, terms, anchors = capsuleForText(query, source="query", cellHints=cellHints)
    return weightedCapsule(capsule, idf), terms, anchors


def candidatePool(query: str, qCapsule: Counter[str], postings: dict[str, tuple[int, ...]]) -> dict[int, float]:
    votes: Counter[int] = Counter()
    for atom, weight in qCapsule.most_common(80):
        if atom.startswith("addr:"):
            continue
        rows = postings.get(atom)
        if not rows:
            continue
        gain = 1.0
        if atom.startswith("cap:"):
            gain = 2.4
        elif atom.startswith("role:"):
            gain = 2.0
        elif atom.startswith("cell:"):
            gain = 1.7
        elif atom.startswith("stem:"):
            gain = 0.8
        for idx in rows[:900]:
            votes[idx] += float(weight) * gain
    if not votes:
        return {}
    return dict(votes.most_common(CANDIDATE_LIMIT))


def roleKeySet(capsule: Counter[str], role: str) -> set[str]:
    prefix = f"role:{role}:"
    return {atom[len(prefix) :] for atom in capsule if atom.startswith(prefix)}


def contrastAtoms(qCapsule: Counter[str], fCapsule: Counter[str]) -> tuple[str, ...]:
    qTargets = roleKeySet(qCapsule, "target")
    fTargets = roleKeySet(fCapsule, "target")
    targetOverlap = qTargets & fTargets
    if not targetOverlap:
        return ()
    contradictions: list[str] = []
    for group, keys in CONTRAST_GROUPS:
        qKeys = {key for key in keys if f"role:action:{key}" in qCapsule or f"role:modifier:{key}" in qCapsule}
        fKeys = {key for key in keys if f"role:action:{key}" in fCapsule or f"role:modifier:{key}" in fCapsule}
        if qKeys and fKeys:
            foreign = fKeys - qKeys
            if foreign:
                contradictions.append(f"{group}:{'/'.join(sorted(qKeys))}!={'/'.join(sorted(foreign))}")
    return tuple(contradictions[:4])


def residualAtoms(qCapsule: Counter[str], fCapsule: Counter[str]) -> tuple[str, ...]:
    residual: list[str] = []
    for atom, weight in qCapsule.most_common(20):
        if atom in fCapsule:
            continue
        if (
            atom.startswith(("role:action:", "role:target:", "cap:targetAction:", "cap:targetModifier:"))
            and weight > 0.8
        ):
            residual.append(atom)
    return tuple(residual[:5])


def surfaceSimilarity(queryTerms: frozenset[str], fragment: Fragment) -> float:
    if not queryTerms or not fragment.terms:
        return 0.0
    shared = queryTerms & fragment.terms
    return len(shared) / max(1, min(len(queryTerms), len(fragment.terms)))


def rankRows(
    query: str,
    fragments: list[Fragment],
    cellHints: dict[str, Counter[str]],
    idf: dict[str, float],
    postings: dict[str, tuple[int, ...]],
) -> tuple[list[SearchRow], list[SearchRow], frozenset[str]]:
    qCapsule, qTerms, qAnchors = queryCapsule(query, cellHints, idf)
    pool = candidatePool(query, qCapsule, postings)
    if not pool:
        return [], [], qAnchors
    capsuleRows: list[SearchRow] = []
    baselineRows: list[SearchRow] = []
    for idx, vote in pool.items():
        fragment = fragments[idx]
        fCapsule = weightedCapsule(fragment.capsule, idf)
        sharedScore = 0.0
        sharedAtoms: list[str] = []
        for atom, qWeight in qCapsule.items():
            fWeight = fCapsule.get(atom, 0.0)
            if fWeight <= 0:
                continue
            gain = 1.0
            if atom.startswith("cap:"):
                gain = 2.4
            elif atom.startswith("role:"):
                gain = 2.0
            elif atom.startswith("cell:"):
                gain = 1.5
            elif atom.startswith("neighbor:") or atom.startswith("order:"):
                gain = 0.55
            sharedScore += math.sqrt(float(qWeight) * float(fWeight)) * gain
            if len(sharedAtoms) < 10 and not atom.startswith("stem:"):
                sharedAtoms.append(atom)
        contradictions = contrastAtoms(qCapsule, fCapsule)
        residual = residualAtoms(qCapsule, fCapsule)
        surface = surfaceSimilarity(qTerms, fragment)
        capsuleScore = sharedScore + float(vote) * 0.012 + surface * 1.3
        capsuleScore -= len(contradictions) * 5.5
        for atom in residual:
            if atom.startswith("role:action:") or atom.startswith("cap:targetAction:"):
                capsuleScore -= 4.2
            elif atom.startswith("role:target:"):
                capsuleScore -= 1.8
            else:
                capsuleScore -= 0.65
        if "role:negation:noData" in fCapsule and any(atom.startswith("role:action:") for atom in qCapsule):
            capsuleScore -= 18.0
        if fragment.anchors:
            capsuleScore += min(1.8, len(fragment.anchors) * 0.28)
        surfaceScore = surface * 9.0 + float(vote) * 0.004
        if "role:negation:noData" in fCapsule and any(atom.startswith("role:action:") for atom in qCapsule):
            surfaceScore -= 7.5
        row = SearchRow(
            fragment=fragment,
            score=capsuleScore,
            surfaceScore=surfaceScore,
            sharedAtoms=tuple(sharedAtoms),
            contradiction=contradictions,
            residual=residual,
        )
        capsuleRows.append(row)
        baselineRows.append(row)
    capsuleRows.sort(key=lambda row: row.score, reverse=True)
    baselineRows.sort(key=lambda row: row.surfaceScore, reverse=True)
    return capsuleRows[:TOP_K], baselineRows[:TOP_K], qAnchors


def semanticEvidence(probe: Probe, row: SearchRow) -> dict[str, object]:
    capsuleAtoms = set(row.fragment.capsule)
    compact = compactText(
        " ".join((row.fragment.text, row.fragment.reportNm, row.fragment.chapter, row.fragment.section))
    )
    expectedHits = 0
    antiHits = 0
    for expected in probe.expected:
        roleAtom = f"role:{expected}"
        key = expected.split(":", 1)[1]
        if roleAtom in capsuleAtoms or compactText(key) in compact:
            expectedHits += 1
    for anti in probe.anti:
        roleAtom = f"role:{anti}"
        key = anti.split(":", 1)[1]
        if roleAtom in capsuleAtoms or compactText(key) in compact:
            antiHits += 1
    exact = compactText(probe.query) in compact
    noData = "role:negation:noData" in capsuleAtoms or hasNoDataEvidence(row.fragment.text)
    boilerplate = len(row.fragment.snippet) < 40 or "document" in row.fragment.snippet.lower()[:80] or noData
    needed = max(1, min(len(probe.expected), 2))
    semantic = expectedHits >= needed and antiHits == 0 and not boilerplate
    return {
        "semantic": semantic,
        "expectedHits": expectedHits,
        "antiHits": antiHits,
        "exact": exact,
        "exactOnly": exact and not semantic,
        "boilerplate": boilerplate,
        "noData": noData,
        "cellAnchored": bool(row.fragment.anchors),
    }


def fmtRow(row: SearchRow) -> str:
    fragment = row.fragment
    location = f"{fragment.source}:{fragment.corp}:{fragment.period}:{fragment.chapter or fragment.reportNm}:{fragment.section}"
    proof = ",".join(row.sharedAtoms[:5]) or "-"
    contra = ",".join(row.contradiction) or "-"
    return (
        f"{location} score={row.score:.2f} surf={row.surfaceScore:.2f} "
        f"anchors={len(fragment.anchors)} contra={contra} proof={proof} "
        f"snippet={fragment.snippet[:150]}"
    )


def evaluateProbes(
    fragments: list[Fragment],
    cellHints: dict[str, Counter[str]],
    idf: dict[str, float],
    postings: dict[str, tuple[int, ...]],
) -> Counter[str]:
    summary: Counter[str] = Counter()
    for probe in PROBES:
        capsuleRows, baselineRows, queryAnchors = rankRows(probe.query, fragments, cellHints, idf, postings)
        capsuleHit = any(bool(semanticEvidence(probe, row)["semantic"]) for row in capsuleRows[:3])
        baselineHit = any(bool(semanticEvidence(probe, row)["semantic"]) for row in baselineRows[:3])
        capsuleTop = semanticEvidence(probe, capsuleRows[0]) if capsuleRows else {}
        baselineTop = semanticEvidence(probe, baselineRows[0]) if baselineRows else {}
        summary["probes"] += 1
        summary["capsuleTop3Semantic"] += int(capsuleHit)
        summary["baselineTop3Semantic"] += int(baselineHit)
        summary["capsuleTop1Semantic"] += int(bool(capsuleTop.get("semantic")))
        summary["baselineTop1Semantic"] += int(bool(baselineTop.get("semantic")))
        summary["capsuleTop1ExactOnly"] += int(bool(capsuleTop.get("exactOnly")))
        summary["capsuleTop1Contradiction"] += int(bool(capsuleTop.get("antiHits")))
        summary["capsuleTop1CellAnchored"] += int(bool(capsuleTop.get("cellAnchored")))
        summary["queryCellAnchored"] += int(bool(queryAnchors))
        print(f"\nQUERY {probe.query} queryCellAnchors={','.join(sorted(queryAnchors)) or '-'}")
        print(
            "  baselineTop1 "
            f"semantic={baselineTop.get('semantic', False)} exact={baselineTop.get('exact', False)} "
            f"expected={baselineTop.get('expectedHits', 0)} anti={baselineTop.get('antiHits', 0)}"
        )
        if baselineRows:
            print("    " + fmtRow(baselineRows[0]))
        print(
            "  capsuleTop1 "
            f"semantic={capsuleTop.get('semantic', False)} exact={capsuleTop.get('exact', False)} "
            f"expected={capsuleTop.get('expectedHits', 0)} anti={capsuleTop.get('antiHits', 0)}"
        )
        for index, row in enumerate(capsuleRows[:3], start=1):
            evidence = semanticEvidence(probe, row)
            print(
                f"    #{index} semantic={evidence['semantic']} exact={evidence['exact']} "
                f"expected={evidence['expectedHits']} anti={evidence['antiHits']} " + fmtRow(row)
            )
    return summary


def accountGuard(
    fragments: list[Fragment],
    cellHints: dict[str, Counter[str]],
    idf: dict[str, float],
    postings: dict[str, tuple[int, ...]],
) -> Counter[str]:
    stats: Counter[str] = Counter()
    if not MAPPING_PATH.exists():
        return stats
    try:
        import json

        raw = json.loads(MAPPING_PATH.read_text(encoding="utf-8"))
    except Exception as exc:  # pragma: no cover - attempts diagnostic
        stats[f"mappingError:{type(exc).__name__}"] += 1
        return stats
    mappings: dict[str, str] = raw.get("mappings", {})
    clusters: dict[str, list[str]] = defaultdict(list)
    for alias, snake in mappings.items():
        cleaned = cleanText(alias)
        if 3 <= len(cleaned) <= 24:
            clusters[str(snake)].append(cleaned)
    cases: list[tuple[str, str, frozenset[str]]] = []
    for snake, aliases in sorted(clusters.items(), key=lambda item: stableHashInt(item[0])):
        unique = sorted(set(aliases), key=lambda item: stableHashInt(f"{snake}:{item}"))
        if len(unique) < 4:
            continue
        heldout = unique[0]
        siblings = frozenset(unique[1:12])
        cases.append((heldout, snake, siblings))
        if len(cases) >= ACCOUNT_GUARD_LIMIT:
            break
    for alias, _snake, siblings in cases:
        rows, _baseline, _anchors = rankRows(alias, fragments, cellHints, idf, postings)
        stats["accountCases"] += 1
        compactSiblings = {compactText(item) for item in siblings if len(item) >= 3}
        hit = False
        for row in rows[:5]:
            rowCompact = compactText(row.fragment.text)
            if any(sibling and sibling in rowCompact for sibling in compactSiblings):
                hit = True
                break
        stats["accountTop5SiblingEvidence"] += int(hit)
    return stats


def main() -> None:
    started = time.perf_counter()
    fragments, cellHints, buildStats = buildFragments()
    if not fragments:
        raise RuntimeError("no fragments loaded from panel/allFilings")
    idf = atomIdf(fragments)
    postings = buildPostings(fragments, idf)
    print("V193 fragment-first meaning capsule")
    print(
        f"fragments={len(fragments)} panelFiles={buildStats['panelFiles']} panelRows={buildStats['panelRows']} "
        f"allFilingFiles={buildStats['allFilingFiles']} allFilingRows={buildStats['allFilingRows']} "
        f"cellFiles={buildStats['cellFiles']} cellRows={buildStats['cellRows']} cellHintTerms={buildStats['cellHintTerms']} "
        f"cellDirExists={buildStats['cellDirExists']} atoms={len(idf)} postings={len(postings)} buildMs={buildStats['buildMs']}"
    )
    probeStats = evaluateProbes(fragments, cellHints, idf, postings)
    guardStats = accountGuard(fragments, cellHints, idf, postings)
    print("\nSUMMARY")
    print(
        f"baselineTop1Semantic={probeStats['baselineTop1Semantic']}/{probeStats['probes']} "
        f"baselineTop3Semantic={probeStats['baselineTop3Semantic']}/{probeStats['probes']} "
        f"capsuleTop1Semantic={probeStats['capsuleTop1Semantic']}/{probeStats['probes']} "
        f"capsuleTop3Semantic={probeStats['capsuleTop3Semantic']}/{probeStats['probes']} "
        f"capsuleTop1ExactOnly={probeStats['capsuleTop1ExactOnly']} "
        f"capsuleTop1Contradiction={probeStats['capsuleTop1Contradiction']} "
        f"capsuleTop1CellAnchored={probeStats['capsuleTop1CellAnchored']} "
        f"queryCellAnchored={probeStats['queryCellAnchored']}"
    )
    if guardStats:
        print(
            f"accountGuard cases={guardStats['accountCases']} "
            f"top5SiblingEvidence={guardStats['accountTop5SiblingEvidence']}/{max(1, guardStats['accountCases'])}"
        )
    else:
        print("accountGuard cases=0 top5SiblingEvidence=0/0")
    print(f"seconds={time.perf_counter() - started:.1f}")


if __name__ == "__main__":
    main()
