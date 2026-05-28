"""Horizon Meaning Learner v23 — conservative targets and calibrated confidence.

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
9. fire 와 별도로 posting 주변 경험에서 df 보정 association graph 를 만들고 exact 후보 내부 rerank 로 검증한다.
10. v12 는 probe evidence rubric 을 semantic slot proxy 로 보고, slot coverage rerank 의 upper bound 를 검증한다.
11. v13 은 평가 rubric 을 직접 쓰는 proxySlot 과 query 에서 lexicon 으로 추론한 lexSlot 을 분리한다.
12. v14 는 lexSlot seed 를 corpus posting association 으로 자동 확장한 autoSlot 을 검증한다.
13. v15 는 autoSlot 을 독립 점수로 쓰지 않고 lexSlot 위의 보수적 delta 로 제한해 false positive 를 줄인다.
14. v16 은 자동 확장어를 seed slot unit 과의 co-occurrence support 로 선별한 supportAutoSlot 을 검증한다.
15. v17 은 hand evidence lexicon 대신 query 에서 실제 매칭된 trigger 만 seed 로 쓰는 triggerSupportSlot 을 검증한다.
16. v18 은 hand evidence lexicon 없이 exact hit cohort 에서 전역 df 대비 과대표집된 stem 을 뽑아
    cohortSlot 을 만들고, query 자체가 corpus 안에서 의미 slot 을 발견할 수 있는지 검증한다.
17. v19 는 exact cohort 를 association graph 로 넓힌 뒤 contrastive stem 을 role frame 으로 묶고,
    표/숫자/목차 조각 같은 negative evidence 를 별도 감점해 "근거 문장성" 을 검증한다.
18. v20 은 수동 role marker 없이 query stem 별 association/fire 근접도로 auto role frame 을 만들고,
    같은 corp/report 반복 근거를 줄이는 diversity rerank 를 검증한다.
19. horizonMeaningLearnerV20 은 여기서 한 단계 더 나아가 query 를 학습된 role cluster 로
    해석하고, top evidence unit 을 근거로 answer skeleton 을 만든다. skeleton 은 생성 모델이
    아니라 posting 경험으로 발견한 core anchor, role cluster, evidence snippet 의 조립 결과다.
20. horizonMeaningLearnerV21 은 자동 role cluster 안의 표/양식/범용 재무 stem 을 줄이기 위해
    query core anchor 와 relation pair 를 함께 만족하는 stem 만 role cluster 에 남기는
    purifier 를 추가한다. 검색은 autoRoleFrameSlot 과 purifiedRoleFrameSlot 을 분리해 평가하고,
    skeleton 은 정제된 role cluster 로 만든다.
21. horizonMeaningLearnerV22 는 v21 의 purifiedMeaningLearner 결과를 바탕으로 evidence unit 에서
    target/action/change/risk/purpose/evidence 슬롯을 채우는 answer frame builder 를 붙인다.
    생성 모델이 아니라 query core anchor, purified role cluster, top evidence unit 의 surface
    support 를 조합해 "대상-행동-변화-근거" frame 을 만든다.
22. horizonMeaningLearnerV23 은 v22 의 answer frame 에서 넓은 cluster-only target 과 confidence
    포화를 줄인다. target 은 query core anchor 와 query surface target 중심으로 제한하고,
    confidence 는 frame slot 개수 대신 top evidence 의 strict rubric 강도와 relation support 로
    보정한다.

실행 코드
---------
기본 샘플 실행:
    uv run --no-sync python -X utf8 tests/_attempts/horizonMeaning/horizonMeaningLearnerV23Test.py

더 크게 실행:
    $env:DARTLAB_HORIZON_MAX_UNITS="120000"
    uv run --no-sync python -X utf8 tests/_attempts/horizonMeaning/horizonMeaningLearnerV23Test.py

전체 파일을 끝까지 읽기:
    $env:DARTLAB_HORIZON_MAX_UNITS="0"
    uv run --no-sync python -X utf8 tests/_attempts/horizonMeaning/horizonMeaningLearnerV23Test.py

결과 기록
---------
2026-05-28 기본 샘플:
- allFilings 는 section_content/content_html/content_xml/content_raw fallback 으로 읽고,
  docs 와 합쳐 40,000 units(allFilings 20,000 + docs 20,000) 를 만들었다.
- build: stems 61,272, postings 1,021,105, assocEdges 1,777,
  autoRoleFrameSlotHits 28,304, purifiedRoleFrameSlotHits 27,830,
  autoCoreAnchorHits 24,363, roughMemoryMb 48.5, buildSeconds 63.5.
- strict rubric: exact 72, fire 72, assoc 73, proxySlot 79, lexSlot 77,
  autoSlot 74, prunedAutoSlot 77, supportAutoSlot 77, triggerSupportSlot 74,
  cohortSlot 77, roleFrameSlot 78, meaningLearner 77, purifiedMeaningLearner 78.
- purifiedMeaningLearner 는 rubric improved/same/worsened = 3/5/0,
  avg 24.10ms, duplicateTop5 0, tableTop5 1 이다.
- answer frame: answerFrames 8, fullAnswerFrames 8, framedTargets 8,
  framedRelations 8, frameCompletenessAvg 3.00, frameConfidenceAvg 0.91,
  frameEvidenceRubricAvg 5.88, frameStrongHitAvg 2.88.
- cluster 정제 상태는 learnedRoleTerms 228 -> purifiedRoleTerms 145,
  learnedFormLikeTerms 30 -> purifiedFormLikeTerms 0 이다.
- v22 한계였던 넓은 target 혼입은 기본 probe 에서 줄었다. 예를 들어 반도체 query 는
  target=hbm,반도체 로 제한되어 화합물을 제외했고, 환율 query 는 target=환율 로 제한되어
  국제곡물을 제외했다.

결론:
v23 은 검색 ranking 자체는 v22 계열을 유지하되, answer frame 의 target slot 을 query core
anchor 중심으로 보수화했다. 동시에 confidence 를 top-3 evidence rubric 에 연결해 모든 frame 이
1.00 으로 포화되던 문제를 줄였다. frame 은 8개 probe 모두 target/relation/evidence 를 유지했고,
confidence 는 0.90~0.95 범위로 evidence 강도에 맞춰 보정됐다.

남은 한계:
top evidence 가 모두 strict hit 인 probe 는 여전히 confidence 0.95 에 가까워진다. target 은
core anchor 중심으로 안전해졌지만, relation/action slot 에는 설정금액처럼 실제 relation 이면서도
표현상 세부 항목인 stem 이 들어간다. 다음 단계는 slot별 role confidence 를 따로 계산하고,
frame 을 자연어 답변 골격으로 압축하는 것이다.
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
ASSOC_WINDOW = int(os.environ.get("DARTLAB_HORIZON_ASSOC_WINDOW", "8"))
ASSOC_TOP_NEIGHBORS = int(os.environ.get("DARTLAB_HORIZON_ASSOC_TOP_NEIGHBORS", "18"))
ASSOC_QUERY_STEMS = int(os.environ.get("DARTLAB_HORIZON_ASSOC_QUERY_STEMS", "36"))
ASSOC_WEIGHT = float(os.environ.get("DARTLAB_HORIZON_ASSOC_WEIGHT", "10.0"))
SLOT_RERANK_WEIGHT = float(os.environ.get("DARTLAB_HORIZON_SLOT_WEIGHT", "18.0"))
AUTO_SLOT_EXPAND_PER_SEED = int(os.environ.get("DARTLAB_HORIZON_AUTO_SLOT_EXPAND_PER_SEED", "4"))
AUTO_SLOT_SCORE_FLOOR = float(os.environ.get("DARTLAB_HORIZON_AUTO_SLOT_SCORE_FLOOR", "0.16"))
AUTO_SLOT_GROUP_MAX_TERMS = int(os.environ.get("DARTLAB_HORIZON_AUTO_SLOT_GROUP_MAX_TERMS", "18"))
PRUNED_AUTO_DELTA_WEIGHT = float(os.environ.get("DARTLAB_HORIZON_PRUNED_AUTO_DELTA_WEIGHT", "0.28"))
PRUNED_AUTO_MIN_SEED_HITS = int(os.environ.get("DARTLAB_HORIZON_PRUNED_AUTO_MIN_SEED_HITS", "2"))
SUPPORT_AUTO_MIN_OVERLAP = int(os.environ.get("DARTLAB_HORIZON_SUPPORT_AUTO_MIN_OVERLAP", "3"))
SUPPORT_AUTO_MIN_PRECISION = float(os.environ.get("DARTLAB_HORIZON_SUPPORT_AUTO_MIN_PRECISION", "0.18"))
SUPPORT_AUTO_MAX_DF_RATIO = float(os.environ.get("DARTLAB_HORIZON_SUPPORT_AUTO_MAX_DF_RATIO", "0.08"))
COHORT_SLOT_TOP_UNITS = int(os.environ.get("DARTLAB_HORIZON_COHORT_SLOT_TOP_UNITS", "160"))
COHORT_SLOT_MIN_OVERLAP = int(os.environ.get("DARTLAB_HORIZON_COHORT_SLOT_MIN_OVERLAP", "3"))
COHORT_SLOT_MIN_PRECISION = float(os.environ.get("DARTLAB_HORIZON_COHORT_SLOT_MIN_PRECISION", "0.16"))
COHORT_SLOT_MAX_DF_RATIO = float(os.environ.get("DARTLAB_HORIZON_COHORT_SLOT_MAX_DF_RATIO", "0.08"))
COHORT_SLOT_WEIGHT_SCALE = float(os.environ.get("DARTLAB_HORIZON_COHORT_SLOT_WEIGHT_SCALE", "0.55"))
ROLE_FRAME_COHORT_TOP_UNITS = int(os.environ.get("DARTLAB_HORIZON_ROLE_FRAME_COHORT_TOP_UNITS", "260"))
ROLE_FRAME_ASSOC_SCORE_FLOOR = float(os.environ.get("DARTLAB_HORIZON_ROLE_FRAME_ASSOC_SCORE_FLOOR", "0.18"))
ROLE_FRAME_MIN_OVERLAP = int(os.environ.get("DARTLAB_HORIZON_ROLE_FRAME_MIN_OVERLAP", "4"))
ROLE_FRAME_MIN_PRECISION = float(os.environ.get("DARTLAB_HORIZON_ROLE_FRAME_MIN_PRECISION", "0.13"))
ROLE_FRAME_MAX_DF_RATIO = float(os.environ.get("DARTLAB_HORIZON_ROLE_FRAME_MAX_DF_RATIO", "0.10"))
ROLE_FRAME_GROUP_MAX_TERMS = int(os.environ.get("DARTLAB_HORIZON_ROLE_FRAME_GROUP_MAX_TERMS", "14"))
ROLE_FRAME_MAX_GROUPS = int(os.environ.get("DARTLAB_HORIZON_ROLE_FRAME_MAX_GROUPS", "4"))
ROLE_FRAME_WEIGHT_SCALE = float(os.environ.get("DARTLAB_HORIZON_ROLE_FRAME_WEIGHT_SCALE", "0.72"))
ROLE_FRAME_NEGATIVE_WEIGHT = float(os.environ.get("DARTLAB_HORIZON_ROLE_FRAME_NEGATIVE_WEIGHT", "4.0"))
AUTO_ROLE_FRAME_ASSOC_SCORE_FLOOR = float(os.environ.get("DARTLAB_HORIZON_AUTO_ROLE_FRAME_ASSOC_SCORE_FLOOR", "0.10"))
AUTO_ROLE_FRAME_FIRE_WEIGHT = float(os.environ.get("DARTLAB_HORIZON_AUTO_ROLE_FRAME_FIRE_WEIGHT", "0.35"))
AUTO_ROLE_FRAME_MIN_OVERLAP = int(os.environ.get("DARTLAB_HORIZON_AUTO_ROLE_FRAME_MIN_OVERLAP", "3"))
AUTO_ROLE_FRAME_MIN_PRECISION = float(os.environ.get("DARTLAB_HORIZON_AUTO_ROLE_FRAME_MIN_PRECISION", "0.11"))
AUTO_ROLE_FRAME_MAX_DF_RATIO = float(os.environ.get("DARTLAB_HORIZON_AUTO_ROLE_FRAME_MAX_DF_RATIO", "0.10"))
AUTO_ROLE_FRAME_GROUP_MAX_TERMS = int(os.environ.get("DARTLAB_HORIZON_AUTO_ROLE_FRAME_GROUP_MAX_TERMS", "12"))
AUTO_ROLE_FRAME_MAX_GROUPS = int(os.environ.get("DARTLAB_HORIZON_AUTO_ROLE_FRAME_MAX_GROUPS", "4"))
AUTO_ROLE_FRAME_WEIGHT_SCALE = float(os.environ.get("DARTLAB_HORIZON_AUTO_ROLE_FRAME_WEIGHT_SCALE", "0.64"))
PURIFIED_ROLE_FRAME_WEIGHT_SCALE = float(os.environ.get("DARTLAB_HORIZON_PURIFIED_ROLE_FRAME_WEIGHT_SCALE", "0.32"))
PURIFIED_ROLE_MIN_ANCHOR_OVERLAP = int(os.environ.get("DARTLAB_HORIZON_PURIFIED_ROLE_MIN_ANCHOR_OVERLAP", "2"))
PURIFIED_ROLE_MIN_RELATION_OVERLAP = int(os.environ.get("DARTLAB_HORIZON_PURIFIED_ROLE_MIN_RELATION_OVERLAP", "1"))
PURIFIED_ROLE_GROUP_MAX_TERMS = int(os.environ.get("DARTLAB_HORIZON_PURIFIED_ROLE_GROUP_MAX_TERMS", "8"))
PURIFIED_ROLE_MAX_DF_RATIO = float(os.environ.get("DARTLAB_HORIZON_PURIFIED_ROLE_MAX_DF_RATIO", "0.08"))
DIVERSITY_TEXT_PENALTY = float(os.environ.get("DARTLAB_HORIZON_DIVERSITY_TEXT_PENALTY", "18.0"))
DIVERSITY_CORP_REPORT_PENALTY = float(os.environ.get("DARTLAB_HORIZON_DIVERSITY_CORP_REPORT_PENALTY", "5.5"))
DIVERSITY_CORP_SECTION_PENALTY = float(os.environ.get("DARTLAB_HORIZON_DIVERSITY_CORP_SECTION_PENALTY", "3.0"))

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

ROLE_MARKER_GROUPS: tuple[tuple[str, tuple[str, ...]], ...] = (
    (
        "object",
        (
            "매출채권",
            "대손충당금",
            "충당금",
            "전환사채",
            "사채",
            "배당",
            "유상증자",
            "신주",
            "원재료",
            "원자재",
            "환율",
            "외화",
            "가격",
            "자금",
            "투자",
            "hbm",
            "반도체",
        ),
    ),
    (
        "action",
        (
            "발행",
            "지급",
            "회수",
            "설정",
            "조달",
            "배정",
            "청약",
            "납입",
            "결의",
            "투자",
            "수주",
            "증설",
            "인식",
            "상계",
        ),
    ),
    ("change", ("증가", "감소", "상승", "하락", "변동", "등락", "악화", "개선", "지연", "압력", "부담", "전기말")),
    ("risk", ("위험", "리스크", "불확실", "노출", "손실", "회수위험", "환위험", "환리스크")),
    ("purpose", ("목적", "자금조달", "시설자금", "운영자금", "운전자금", "채무상환", "사용목적")),
)
NEGATIVE_SECTION_TERMS = ("요약재무", "재무상태표", "손익계산서", "자본변동표", "현금흐름표", "표준계정", "계정과목")
NEGATIVE_TEXT_TERMS = ("단위", "주석", "번호", "합계", "소계", "기말", "기초", "제", "당기", "전기")
FORM_LIKE_STEM_FRAGMENTS = (
    "계정과목",
    "잔액",
    "장부가액",
    "장부금액",
    "재무현황",
    "부채및자본",
    "자산총계",
    "재고자산합계",
    "연환산",
    "일반서식",
    "발행회사명",
    "및비율",
    "주식수",
    "기초재고",
    "전기말",
    "당기말",
    "분기말",
    "최근사업연도",
    "table",
    "구성비율",
    "총자산대비",
    "회전율",
    "실사",
    "기말재고",
    "월할하여",
)
ANSWER_FRAME_SLOT_HINTS: dict[str, tuple[str, ...]] = {
    "action": ("발행", "지급", "회수", "설정", "조달", "배정", "청약", "납입", "결의", "투자", "수주", "증설", "인식"),
    "change": ("증가", "감소", "상승", "하락", "변동", "지연", "악화", "개선", "압력", "부담", "둔화"),
    "risk": ("리스크", "위험", "불확실", "노출", "손실", "환위험", "환리스크"),
    "purpose": ("목적", "자금조달", "시설자금", "운영자금", "운전자금", "채무상환", "사용목적"),
}
ANSWER_FRAME_TARGET_LIMIT = int(os.environ.get("DARTLAB_HORIZON_ANSWER_FRAME_TARGET_LIMIT", "2"))
ANSWER_FRAME_MIN_TARGET_SCORE = float(os.environ.get("DARTLAB_HORIZON_ANSWER_FRAME_MIN_TARGET_SCORE", "6.0"))
ANSWER_FRAME_MIN_RELATION_SCORE = float(os.environ.get("DARTLAB_HORIZON_ANSWER_FRAME_MIN_RELATION_SCORE", "5.0"))
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


@dataclass(frozen=True, slots=True)
class AnswerFrame:
    query: str
    target: tuple[str, ...]
    action: tuple[str, ...]
    change: tuple[str, ...]
    risk: tuple[str, ...]
    purpose: tuple[str, ...]
    evidence: tuple[str, ...]
    evidenceRubric: int
    evidenceStrongHits: int
    confidence: float


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
    associationNeighbors: dict[int, list[tuple[int, float]]]
    unitTableLike: list[bool]
    unitNegativeEvidenceBase: list[float]
    unitTypeBoostBase: dict[str, dict[int, float]]
    unitSlotHitsBase: dict[str, dict[int, int]]
    unitLexiconSlotHitsBase: dict[str, dict[int, int]]
    unitAutoSlotHitsBase: dict[str, dict[int, int]]
    unitSupportAutoSlotHitsBase: dict[str, dict[int, int]]
    unitTriggerSeedSlotHitsBase: dict[str, dict[int, int]]
    unitTriggerSupportSlotHitsBase: dict[str, dict[int, int]]
    unitCohortSlotHitsBase: dict[str, dict[int, int]]
    unitRoleFrameSlotHitsBase: dict[str, dict[int, int]]
    unitAutoRoleFrameSlotHitsBase: dict[str, dict[int, int]]
    unitPurifiedRoleFrameSlotHitsBase: dict[str, dict[int, int]]
    unitCoreAnchorHitsBase: dict[str, dict[int, int]]
    unitAutoCoreAnchorHitsBase: dict[str, dict[int, int]]
    queryLexiconSlotGroups: dict[str, tuple[tuple[str, ...], ...]]
    queryAutoSlotGroups: dict[str, tuple[tuple[str, ...], ...]]
    querySupportAutoSlotGroups: dict[str, tuple[tuple[str, ...], ...]]
    queryTriggerSupportSlotGroups: dict[str, tuple[tuple[str, ...], ...]]
    queryCohortSlotGroups: dict[str, tuple[tuple[str, ...], ...]]
    queryRoleFrameSlotGroups: dict[str, tuple[tuple[str, ...], ...]]
    queryAutoRoleFrameSlotGroups: dict[str, tuple[tuple[str, ...], ...]]
    queryPurifiedRoleFrameSlotGroups: dict[str, tuple[tuple[str, ...], ...]]
    queryCoreAnchorTerms: dict[str, tuple[str, ...]]
    queryAutoCoreAnchorTerms: dict[str, tuple[str, ...]]
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

LEXICON_SLOT_GROUPS: tuple[tuple[str, tuple[str, ...], tuple[str, ...]], ...] = (
    (
        "semiconductor",
        ("반도체", "hbm", "메모리", "d램", "dram", "ai"),
        ("반도체", "hbm", "메모리", "고대역폭", "d램", "dram", "ai", "차세대"),
    ),
    (
        "growth_investment",
        ("투자", "성장", "수주", "설비", "검사장비", "r&d"),
        ("투자", "수주", "성장", "설비", "검사장비", "r&d", "증설", "차세대"),
    ),
    (
        "currency",
        ("환율", "외화", "원화", "달러", "외환"),
        ("환율", "외화", "원화", "달러", "외환", "환위험", "환리스크"),
    ),
    (
        "risk_change",
        ("리스크", "위험", "변동", "등락", "지연", "불확실"),
        ("리스크", "위험", "변동", "등락", "불확실", "노출", "손실", "악화"),
    ),
    ("equity_financing", ("유상증자", "증자", "제3자배정", "신주"), ("유상증자", "증자", "제3자배정")),
    (
        "funding_purpose",
        ("목적", "자금조달", "시설자금", "운영자금", "운전자금", "유상증자"),
        ("목적", "자금조달", "시설자금", "운영자금", "운전자금", "채무상환", "사용목적", "조달자금"),
    ),
    (
        "input_material",
        ("원재료", "원자재", "원면", "재료"),
        ("원재료", "원자재", "원면", "철강재", "컬러강판", "원부재료", "재료"),
    ),
    ("price_level", ("가격", "단가", "원가", "비용"), ("가격", "단가", "원가", "비용", "수익성")),
    (
        "adverse_movement",
        ("상승", "증가", "변동", "악화", "압력"),
        ("상승", "증가", "변동", "압력", "부담", "악화", "위험"),
    ),
    ("allowance", ("대손충당금", "충당금", "대손"), ("대손충당금", "충당금", "대손", "손실충당금")),
    (
        "allowance_setting",
        ("설정", "설정률", "전기말", "대손충당금", "충당금"),
        ("증가", "설정", "설정률", "전기말", "인식", "변동"),
    ),
    (
        "receivable_asset",
        ("매출채권", "채권", "계약자산", "대손충당금", "충당금"),
        ("매출채권", "채권", "계약자산", "미수금"),
    ),
    ("collection", ("회수", "수금", "현금화"), ("회수", "수금", "현금화", "수령", "상계")),
    ("delay_concentration", ("지연", "편중", "연말", "제약"), ("지연", "편중", "연말", "위험", "제약", "둔화", "손실")),
    (
        "convertible_bond",
        ("전환사채", "사채", "채무증권", "신주인수권"),
        ("전환사채", "사채", "채무증권", "신주인수권", "cb"),
    ),
    (
        "issuance_terms",
        ("발행", "청약", "납입", "전환가격", "전환가액", "전환사채"),
        ("발행", "청약", "납입", "전환가격", "전환가액", "인수", "권면"),
    ),
    (
        "dividend",
        ("배당", "배당금", "현금배당", "현물배당"),
        ("배당", "배당금", "현금배당", "현물배당", "시가배당", "차등배당"),
    ),
    (
        "payout_governance",
        ("지급", "지급일", "주주", "결의", "기준일", "배당"),
        ("지급", "지급일", "주주", "결의", "주주총회", "기준일", "권리주주"),
    ),
)


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
    baseColumns = [
        "corp_name",
        "stock_code",
        "rcept_no",
        "rcept_dt",
        "report_nm",
        "section_title",
        "section_content",
        "content_html",
        "content_xml",
        "content_raw",
    ]
    for path in sorted(ALLFILINGS_DIR.glob("*.parquet")):
        if "_meta" in path.name:
            continue
        schema = pl.read_parquet_schema(path)
        columns = [column for column in baseColumns if column in schema]
        if (
            "section_content" not in schema
            and "content_html" not in schema
            and "content_xml" not in schema
            and "content_raw" not in schema
        ):
            print(f"[skip] allFilings {path.name}: no section_content/content_html/content_xml/content_raw column")
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
            title = safeValue(row.get("section_title") or row.get("report_nm"))
            reportName = safeValue(row.get("report_nm"))
            content = safeValue(
                row.get("section_content")
                or row.get("content_html")
                or row.get("content_xml")
                or row.get("content_raw")
            )
            for text in splitUnits(content):
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


def buildUnitSlotHitsBase(units: list[Unit]) -> dict[str, dict[int, int]]:
    surfaces = [compactText(f"{unit.reportName} {unit.sectionTitle} {unit.text}") for unit in units]
    out: dict[str, dict[int, int]] = {}
    for spec in PROBE_QUERIES:
        if not spec.rubricGroups:
            continue
        unitHits: dict[int, int] = {}
        for unitId, surface in enumerate(surfaces):
            hits = 0
            for group in spec.rubricGroups:
                if any(term.lower() in surface for term in group):
                    hits += 1
            if hits:
                unitHits[unitId] = hits
        out[spec.query] = unitHits
    return out


def buildUnitNegativeEvidenceBase(units: list[Unit], unitTableLike: list[bool]) -> list[float]:
    out: list[float] = []
    for unitId, unit in enumerate(units):
        titleSurface = compactText(f"{unit.reportName} {unit.sectionTitle}")
        textSurface = compactText(unit.text)
        penalty = 0.0
        if unitTableLike[unitId]:
            penalty += 1.0
        visible = [ch for ch in unit.text[:800] if not ch.isspace()]
        if visible:
            digitRatio = sum(1 for ch in visible if ch.isdigit()) / len(visible)
            separatorRatio = sum(1 for ch in visible if ch in ",.-()%|") / len(visible)
            if digitRatio + separatorRatio >= 0.38:
                penalty += 0.75
        if len(textSurface) < 60:
            penalty += 0.4
        if any(term in titleSurface for term in NEGATIVE_SECTION_TERMS):
            penalty += 0.8
        if sum(1 for term in NEGATIVE_TEXT_TERMS if term in textSurface[:220]) >= 3:
            penalty += 0.5
        out.append(penalty)
    return out


def inferLexiconSlotGroups(query: str) -> tuple[tuple[str, ...], ...]:
    querySurface = compactText(query)
    queryStems = set(extractStems(query, cap=64))

    def matches(term: str) -> bool:
        lower = term.lower()
        if lower in querySurface:
            return True
        normalized = normalizeToken(term)
        return bool(normalized and normalized in queryStems)

    groups: list[tuple[str, ...]] = []
    seen: set[tuple[str, ...]] = set()
    for _, triggers, evidence in LEXICON_SLOT_GROUPS:
        if not any(matches(trigger) for trigger in triggers):
            continue
        normalizedEvidence = tuple(dict.fromkeys(term.lower() for term in evidence if term))
        if normalizedEvidence and normalizedEvidence not in seen:
            groups.append(normalizedEvidence)
            seen.add(normalizedEvidence)
    return tuple(groups)


def inferTriggerSlotGroups(query: str) -> tuple[tuple[str, ...], ...]:
    querySurface = compactText(query)
    queryStems = set(extractStems(query, cap=64))

    def matches(term: str) -> bool:
        lower = term.lower()
        if lower in querySurface:
            return True
        normalized = normalizeToken(term)
        return bool(normalized and normalized in queryStems)

    groups: list[tuple[str, ...]] = []
    seenGroups: set[tuple[str, ...]] = set()
    for _, triggers, _ in LEXICON_SLOT_GROUPS:
        matched = tuple(dict.fromkeys(trigger.lower() for trigger in triggers if matches(trigger)))
        if matched and matched not in seenGroups:
            groups.append(matched)
            seenGroups.add(matched)
    return tuple(groups)


def buildQueryLexiconSlotGroups() -> dict[str, tuple[tuple[str, ...], ...]]:
    return {spec.query: inferLexiconSlotGroups(spec.query) for spec in PROBE_QUERIES}


def buildQueryTriggerSlotGroups() -> dict[str, tuple[tuple[str, ...], ...]]:
    return {spec.query: inferTriggerSlotGroups(spec.query) for spec in PROBE_QUERIES}


def buildUnitLexiconSlotHitsBase(
    units: list[Unit],
    queryLexiconSlotGroups: dict[str, tuple[tuple[str, ...], ...]],
) -> dict[str, dict[int, int]]:
    surfaces = [compactText(f"{unit.reportName} {unit.sectionTitle} {unit.text}") for unit in units]
    out: dict[str, dict[int, int]] = {}
    for query, groups in queryLexiconSlotGroups.items():
        if not groups:
            continue
        unitHits: dict[int, int] = {}
        for unitId, surface in enumerate(surfaces):
            hits = 0
            for group in groups:
                if any(term in surface for term in group):
                    hits += 1
            if hits:
                unitHits[unitId] = hits
        out[query] = unitHits
    return out


def buildQueryAutoSlotGroups(
    queryLexiconSlotGroups: dict[str, tuple[tuple[str, ...], ...]],
    stemToId: dict[str, int],
    idToStem: list[str],
    associationNeighbors: dict[int, list[tuple[int, float]]],
) -> dict[str, tuple[tuple[str, ...], ...]]:
    out: dict[str, tuple[tuple[str, ...], ...]] = {}
    for query, groups in queryLexiconSlotGroups.items():
        autoGroups: list[tuple[str, ...]] = []
        for group in groups:
            terms: list[str] = []
            seen: set[str] = set()
            seedStemIds: set[int] = set()
            for term in group:
                lower = term.lower()
                if lower and lower not in seen:
                    terms.append(lower)
                    seen.add(lower)
                for stem in extractStems(term, cap=8):
                    stemId = stemToId.get(stem)
                    if stemId is not None:
                        seedStemIds.add(stemId)

            neighborScores: Counter[str] = Counter()
            for seedStemId in seedStemIds:
                added = 0
                for neighborId, score in associationNeighbors.get(seedStemId, ()):
                    if score < AUTO_SLOT_SCORE_FLOOR:
                        continue
                    stem = idToStem[neighborId].lower()
                    if stem in seen or isNoisyStem(stem):
                        continue
                    neighborScores[stem] += score
                    added += 1
                    if added >= AUTO_SLOT_EXPAND_PER_SEED:
                        break

            for stem, _ in neighborScores.most_common(max(0, AUTO_SLOT_GROUP_MAX_TERMS - len(terms))):
                if stem not in seen:
                    terms.append(stem)
                    seen.add(stem)
            autoGroups.append(tuple(terms[:AUTO_SLOT_GROUP_MAX_TERMS]))
        out[query] = tuple(autoGroups)
    return out


def unitUnionForTerms(group: tuple[str, ...], stemToId: dict[str, int], stemUnits: list[list[int]]) -> set[int]:
    unitIds: set[int] = set()
    for term in group:
        for stem in extractStems(term, cap=8):
            stemId = stemToId.get(stem)
            if stemId is not None:
                unitIds.update(stemUnits[stemId])
    return unitIds


def buildQuerySupportAutoSlotGroups(
    queryLexiconSlotGroups: dict[str, tuple[tuple[str, ...], ...]],
    stemToId: dict[str, int],
    idToStem: list[str],
    stemUnits: list[list[int]],
    associationNeighbors: dict[int, list[tuple[int, float]]],
    unitCount: int,
) -> dict[str, tuple[tuple[str, ...], ...]]:
    maxDf = max(int(unitCount * SUPPORT_AUTO_MAX_DF_RATIO), 1)
    out: dict[str, tuple[tuple[str, ...], ...]] = {}
    for query, groups in queryLexiconSlotGroups.items():
        supportGroups: list[tuple[str, ...]] = []
        for group in groups:
            seedTerms = list(dict.fromkeys(term.lower() for term in group if term))
            seen = set(seedTerms)
            seedUnitIds = unitUnionForTerms(tuple(seedTerms), stemToId, stemUnits)
            seedStemIds: set[int] = set()
            for term in seedTerms:
                for stem in extractStems(term, cap=8):
                    stemId = stemToId.get(stem)
                    if stemId is not None:
                        seedStemIds.add(stemId)
            if not seedUnitIds or not seedStemIds:
                supportGroups.append(tuple(seedTerms[:AUTO_SLOT_GROUP_MAX_TERMS]))
                continue

            candidateScores: Counter[str] = Counter()
            candidateIds: dict[str, int] = {}
            for seedStemId in seedStemIds:
                for neighborId, assocScore in associationNeighbors.get(seedStemId, ()):
                    stem = idToStem[neighborId].lower()
                    if stem in seen or isNoisyStem(stem):
                        continue
                    df = len(stemUnits[neighborId])
                    if df <= 1 or df > maxDf:
                        continue
                    neighborUnitIds = set(stemUnits[neighborId])
                    overlap = len(seedUnitIds & neighborUnitIds)
                    if overlap < SUPPORT_AUTO_MIN_OVERLAP:
                        continue
                    precision = overlap / max(df, 1)
                    if precision < SUPPORT_AUTO_MIN_PRECISION:
                        continue
                    candidateScores[stem] += assocScore * precision * math.log1p(overlap)
                    candidateIds[stem] = neighborId

            terms = seedTerms[:]
            for stem, _ in candidateScores.most_common(max(0, AUTO_SLOT_GROUP_MAX_TERMS - len(terms))):
                if stem not in seen:
                    terms.append(stem)
                    seen.add(stem)
            supportGroups.append(tuple(terms[:AUTO_SLOT_GROUP_MAX_TERMS]))
        out[query] = tuple(supportGroups)
    return out


def buildQueryCohortSlotGroups(
    stemToId: dict[str, int],
    idToStem: list[str],
    stemUnits: list[list[int]],
    postingTable: list[tuple[int, ...]],
    associationNeighbors: dict[int, list[tuple[int, float]]],
) -> dict[str, tuple[tuple[str, ...], ...]]:
    unitCount = max(len(postingTable), 1)
    maxDf = max(int(unitCount * COHORT_SLOT_MAX_DF_RATIO), 1)
    maxPostingsPerStem = max(int(unitCount * 0.08), 300)
    out: dict[str, tuple[tuple[str, ...], ...]] = {}

    for spec in PROBE_QUERIES:
        queryIds: list[int] = []
        seenQueryIds: set[int] = set()
        for stem in extractStems(spec.query, cap=32):
            stemId = stemToId.get(stem)
            if stemId is not None and stemId not in seenQueryIds:
                queryIds.append(stemId)
                seenQueryIds.add(stemId)
        if not queryIds:
            out[spec.query] = ()
            continue

        hitCounts: Counter[int] = Counter()
        for stemId in queryIds:
            for unitId in stemUnits[stemId][:maxPostingsPerStem]:
                hitCounts[unitId] += 1
        minHits = max(1, min(2, len(queryIds)))
        seedUnitIds = [unitId for unitId, hits in hitCounts.most_common(COHORT_SLOT_TOP_UNITS * 3) if hits >= minHits][
            :COHORT_SLOT_TOP_UNITS
        ]
        if not seedUnitIds:
            out[spec.query] = ()
            continue

        queryIdSet = set(queryIds)
        usedTerms: set[str] = set()
        groups: list[tuple[str, ...]] = []
        for anchorId in queryIds:
            anchorUnitIds = [unitId for unitId in seedUnitIds if anchorId in postingTable[unitId]]
            if len(anchorUnitIds) < COHORT_SLOT_MIN_OVERLAP:
                continue
            anchorAssoc = {neighborId: score for neighborId, score in associationNeighbors.get(anchorId, ())}
            candidateCounts: Counter[int] = Counter()
            for unitId in anchorUnitIds:
                for stemId in set(postingTable[unitId]):
                    if stemId in queryIdSet:
                        continue
                    stem = idToStem[stemId]
                    if isNoisyStem(stem):
                        continue
                    df = len(stemUnits[stemId])
                    if df <= 1 or df > maxDf:
                        continue
                    candidateCounts[stemId] += 1

            scored: list[tuple[float, int]] = []
            for stemId, overlap in candidateCounts.items():
                if overlap < COHORT_SLOT_MIN_OVERLAP:
                    continue
                df = len(stemUnits[stemId])
                precision = overlap / max(df, 1)
                if precision < COHORT_SLOT_MIN_PRECISION:
                    continue
                recall = overlap / max(len(anchorUnitIds), 1)
                idf = math.log((unitCount + 1) / (df + 1))
                assoc = anchorAssoc.get(stemId, 0.0)
                score = (precision * math.log1p(overlap) * idf * (1.0 + assoc)) + (recall * 0.25)
                if score > 0:
                    scored.append((score, stemId))

            scored.sort(reverse=True)
            terms: list[str] = []
            localSeen: set[str] = set()
            for _, stemId in scored:
                stem = idToStem[stemId].lower()
                if stem in localSeen:
                    continue
                if stem in usedTerms and len(terms) >= 3:
                    continue
                terms.append(stem)
                localSeen.add(stem)
                if len(terms) >= AUTO_SLOT_GROUP_MAX_TERMS:
                    break
            if terms:
                groups.append(tuple(terms))
                usedTerms.update(terms[:6])

        out[spec.query] = tuple(groups)
    return out


def termMatchesRole(stem: str, markers: tuple[str, ...]) -> bool:
    lower = stem.lower()
    for marker in markers:
        markerLower = marker.lower()
        if not markerLower:
            continue
        if lower == markerLower or lower in markerLower or markerLower in lower:
            return True
        markerStems = extractStems(markerLower, cap=8)
        if any(
            markerStem and (lower == markerStem or markerStem in lower or lower in markerStem)
            for markerStem in markerStems
        ):
            return True
    return False


def inferQueryRoleNames(query: str) -> tuple[str, ...]:
    querySurface = compactText(query)
    queryStems = set(extractStems(query, cap=32))
    roleNames: list[str] = []
    for roleName, markers in ROLE_MARKER_GROUPS:
        matched = False
        for marker in markers:
            markerLower = marker.lower()
            if markerLower in querySurface:
                matched = True
                break
            markerStems = extractStems(markerLower, cap=8)
            if any(markerStem in queryStems for markerStem in markerStems):
                matched = True
                break
        if matched:
            roleNames.append(roleName)
    return tuple(roleNames)


def inferQueryCoreAnchorTerms(query: str) -> tuple[str, ...]:
    actionLikeMarkers = ()
    objectMarkers = ()
    for roleName, markers in ROLE_MARKER_GROUPS:
        if roleName == "object":
            objectMarkers = markers
        elif roleName in {"action", "change", "risk", "purpose"}:
            actionLikeMarkers += markers

    terms: list[str] = []
    seen: set[str] = set()
    for stem in extractStems(query, cap=32):
        lower = stem.lower()
        if lower in seen:
            continue
        isObject = termMatchesRole(lower, objectMarkers)
        isActionLike = termMatchesRole(lower, actionLikeMarkers)
        if isObject and not isActionLike:
            terms.append(lower)
            seen.add(lower)
    if terms:
        return tuple(terms)
    return tuple(dict.fromkeys(extractStems(query, cap=32)))


def buildQueryCoreAnchorTerms() -> dict[str, tuple[str, ...]]:
    return {spec.query: inferQueryCoreAnchorTerms(spec.query) for spec in PROBE_QUERIES}


def buildQueryCoreAnchorGroups(
    queryCoreAnchorTerms: dict[str, tuple[str, ...]],
) -> dict[str, tuple[tuple[str, ...], ...]]:
    return {query: (terms,) if terms else () for query, terms in queryCoreAnchorTerms.items()}


def buildQueryRoleFrameSlotGroups(
    stemToId: dict[str, int],
    idToStem: list[str],
    stemUnits: list[list[int]],
    postingTable: list[tuple[int, ...]],
    associationNeighbors: dict[int, list[tuple[int, float]]],
) -> dict[str, tuple[tuple[str, ...], ...]]:
    unitCount = max(len(postingTable), 1)
    maxDf = max(int(unitCount * ROLE_FRAME_MAX_DF_RATIO), 1)
    maxPostingsPerStem = max(int(unitCount * 0.08), 300)
    out: dict[str, tuple[tuple[str, ...], ...]] = {}

    for spec in PROBE_QUERIES:
        queryIds: list[int] = []
        seenQueryIds: set[int] = set()
        for stem in extractStems(spec.query, cap=32):
            stemId = stemToId.get(stem)
            if stemId is not None and stemId not in seenQueryIds:
                queryIds.append(stemId)
                seenQueryIds.add(stemId)
        if not queryIds:
            out[spec.query] = ()
            continue

        unitScores: Counter[int] = Counter()
        queryAssocScores: Counter[int] = Counter()
        for stemId in queryIds:
            for unitId in stemUnits[stemId][:maxPostingsPerStem]:
                unitScores[unitId] += 1.0
            for neighborId, assocScore in associationNeighbors.get(stemId, ()):
                if assocScore < ROLE_FRAME_ASSOC_SCORE_FLOOR:
                    continue
                queryAssocScores[neighborId] += assocScore
                for unitId in stemUnits[neighborId][:maxPostingsPerStem]:
                    unitScores[unitId] += assocScore * 0.65

        if not unitScores:
            out[spec.query] = ()
            continue
        seedUnitIds = [unitId for unitId, _ in unitScores.most_common(ROLE_FRAME_COHORT_TOP_UNITS)]
        weightSum = sum(unitScores[unitId] for unitId in seedUnitIds) or 1.0
        queryIdSet = set(queryIds)
        candidateRawCounts: Counter[int] = Counter()
        candidateWeightedCounts: Counter[int] = Counter()
        for unitId in seedUnitIds:
            unitWeight = unitScores[unitId]
            for stemId in set(postingTable[unitId]):
                if stemId in queryIdSet:
                    continue
                stem = idToStem[stemId]
                if isNoisyStem(stem) or stem in STOP_STEMS:
                    continue
                df = len(stemUnits[stemId])
                if df <= 1 or df > maxDf:
                    continue
                candidateRawCounts[stemId] += 1
                candidateWeightedCounts[stemId] += unitWeight

        scored: list[tuple[float, int]] = []
        for stemId, overlap in candidateRawCounts.items():
            if overlap < ROLE_FRAME_MIN_OVERLAP:
                continue
            df = len(stemUnits[stemId])
            precision = overlap / max(df, 1)
            if precision < ROLE_FRAME_MIN_PRECISION:
                continue
            weightedOverlap = candidateWeightedCounts[stemId]
            cohortShare = weightedOverlap / weightSum
            idf = math.log((unitCount + 1) / (df + 1))
            assocBoost = 1.0 + min(1.0, queryAssocScores.get(stemId, 0.0))
            score = precision * math.log1p(overlap) * idf * assocBoost + cohortShare * 0.45
            if score > 0:
                scored.append((score, stemId))
        scored.sort(reverse=True)

        groups: list[tuple[str, ...]] = []
        usedTerms: set[str] = set()
        roleNames = inferQueryRoleNames(spec.query)
        roleByName = dict(ROLE_MARKER_GROUPS)
        for roleName in roleNames:
            markers = roleByName.get(roleName)
            if not markers:
                continue
            terms: list[str] = []
            for _, stemId in scored:
                stem = idToStem[stemId].lower()
                if stem in usedTerms:
                    continue
                if not termMatchesRole(stem, markers):
                    continue
                terms.append(stem)
                usedTerms.add(stem)
                if len(terms) >= ROLE_FRAME_GROUP_MAX_TERMS:
                    break
            if terms:
                groups.append(tuple(terms))
                if len(groups) >= ROLE_FRAME_MAX_GROUPS:
                    break

        if len(groups) < ROLE_FRAME_MAX_GROUPS:
            terms = []
            for _, stemId in scored:
                stem = idToStem[stemId].lower()
                if stem in usedTerms:
                    continue
                terms.append(stem)
                usedTerms.add(stem)
                if len(terms) >= ROLE_FRAME_GROUP_MAX_TERMS:
                    break
            if terms:
                groups.append(tuple(terms))

        out[spec.query] = tuple(groups[:ROLE_FRAME_MAX_GROUPS])
    return out


def fireSimilarity(fireTable: list[dict[int, float]], fireNorm: list[float], leftId: int, rightId: int) -> float:
    leftNorm = fireNorm[leftId]
    rightNorm = fireNorm[rightId]
    if leftNorm <= 0 or rightNorm <= 0:
        return 0.0
    leftProfile = fireTable[leftId]
    rightProfile = fireTable[rightId]
    if len(leftProfile) > len(rightProfile):
        leftProfile, rightProfile = rightProfile, leftProfile
    dot = 0.0
    for dim, value in leftProfile.items():
        dot += value * rightProfile.get(dim, 0.0)
    if dot <= 0:
        return 0.0
    return dot / (leftNorm * rightNorm)


def inferQueryAutoCoreAnchorTerms(
    query: str,
    stemToId: dict[str, int],
    stemUnits: list[list[int]],
    unitCount: int,
) -> tuple[str, ...]:
    scored: list[tuple[float, str]] = []
    for stem in dict.fromkeys(extractStems(query, cap=32)):
        stemId = stemToId.get(stem)
        if stemId is None:
            continue
        df = len(stemUnits[stemId])
        if df <= 0:
            continue
        idf = math.log((unitCount + 1) / (df + 1))
        scored.append((idf + len(stem) * 0.03, stem.lower()))
    scored.sort(reverse=True)
    if not scored:
        return tuple(dict.fromkeys(extractStems(query, cap=32)))
    return tuple(stem for _, stem in scored[: min(3, len(scored))])


def buildQueryAutoCoreAnchorTerms(
    stemToId: dict[str, int],
    stemUnits: list[list[int]],
    unitCount: int,
) -> dict[str, tuple[str, ...]]:
    return {
        spec.query: inferQueryAutoCoreAnchorTerms(spec.query, stemToId, stemUnits, unitCount) for spec in PROBE_QUERIES
    }


def buildQueryAutoRoleFrameSlotGroups(
    stemToId: dict[str, int],
    idToStem: list[str],
    stemUnits: list[list[int]],
    postingTable: list[tuple[int, ...]],
    associationNeighbors: dict[int, list[tuple[int, float]]],
    fireTable: list[dict[int, float]],
    fireNorm: list[float],
) -> dict[str, tuple[tuple[str, ...], ...]]:
    unitCount = max(len(postingTable), 1)
    maxDf = max(int(unitCount * AUTO_ROLE_FRAME_MAX_DF_RATIO), 1)
    maxPostingsPerStem = max(int(unitCount * 0.08), 300)
    out: dict[str, tuple[tuple[str, ...], ...]] = {}

    for spec in PROBE_QUERIES:
        queryIds: list[int] = []
        seenQueryIds: set[int] = set()
        for stem in extractStems(spec.query, cap=32):
            stemId = stemToId.get(stem)
            if stemId is not None and stemId not in seenQueryIds:
                queryIds.append(stemId)
                seenQueryIds.add(stemId)
        if not queryIds:
            out[spec.query] = ()
            continue

        unitScores: Counter[int] = Counter()
        anchorAssocScores: dict[int, Counter[int]] = {queryId: Counter() for queryId in queryIds}
        for queryId in queryIds:
            for unitId in stemUnits[queryId][:maxPostingsPerStem]:
                unitScores[unitId] += 1.0
            for neighborId, assocScore in associationNeighbors.get(queryId, ()):
                if assocScore < AUTO_ROLE_FRAME_ASSOC_SCORE_FLOOR:
                    continue
                anchorAssocScores[queryId][neighborId] += assocScore
                for unitId in stemUnits[neighborId][:maxPostingsPerStem]:
                    unitScores[unitId] += assocScore * 0.55

        seedUnitIds = [unitId for unitId, _ in unitScores.most_common(ROLE_FRAME_COHORT_TOP_UNITS)]
        if not seedUnitIds:
            out[spec.query] = ()
            continue
        weightSum = sum(unitScores[unitId] for unitId in seedUnitIds) or 1.0
        queryIdSet = set(queryIds)
        candidateRawCounts: Counter[int] = Counter()
        candidateWeightedCounts: Counter[int] = Counter()
        for unitId in seedUnitIds:
            unitWeight = unitScores[unitId]
            for stemId in set(postingTable[unitId]):
                if stemId in queryIdSet:
                    continue
                stem = idToStem[stemId]
                if isNoisyStem(stem) or stem in STOP_STEMS:
                    continue
                df = len(stemUnits[stemId])
                if df <= 1 or df > maxDf:
                    continue
                candidateRawCounts[stemId] += 1
                candidateWeightedCounts[stemId] += unitWeight

        grouped: dict[int, list[tuple[float, int]]] = {queryId: [] for queryId in queryIds}
        for stemId, overlap in candidateRawCounts.items():
            if overlap < AUTO_ROLE_FRAME_MIN_OVERLAP:
                continue
            df = len(stemUnits[stemId])
            precision = overlap / max(df, 1)
            if precision < AUTO_ROLE_FRAME_MIN_PRECISION:
                continue
            weightedOverlap = candidateWeightedCounts[stemId]
            cohortShare = weightedOverlap / weightSum
            idf = math.log((unitCount + 1) / (df + 1))
            baseScore = precision * math.log1p(overlap) * idf + cohortShare * 0.45
            bestAnchorId = queryIds[0]
            bestAnchorScore = -1.0
            for queryId in queryIds:
                assoc = anchorAssocScores[queryId].get(stemId, 0.0)
                fire = fireSimilarity(fireTable, fireNorm, queryId, stemId)
                anchorScore = assoc + fire * AUTO_ROLE_FRAME_FIRE_WEIGHT
                if anchorScore > bestAnchorScore:
                    bestAnchorScore = anchorScore
                    bestAnchorId = queryId
            if bestAnchorScore <= 0:
                continue
            grouped[bestAnchorId].append((baseScore * (1.0 + min(bestAnchorScore, 1.2)), stemId))

        groups: list[tuple[str, ...]] = []
        used: set[str] = set()
        for queryId in sorted(queryIds, key=lambda sid: len(stemUnits[sid])):
            anchorStem = idToStem[queryId].lower()
            terms: list[str] = [anchorStem]
            used.add(anchorStem)
            for _, stemId in sorted(grouped.get(queryId, ()), reverse=True):
                stem = idToStem[stemId].lower()
                if stem in used:
                    continue
                terms.append(stem)
                used.add(stem)
                if len(terms) >= AUTO_ROLE_FRAME_GROUP_MAX_TERMS:
                    break
            if terms:
                groups.append(tuple(terms))
                if len(groups) >= AUTO_ROLE_FRAME_MAX_GROUPS:
                    break
        out[spec.query] = tuple(groups)
    return out


def isFormLikeRoleStem(stem: str) -> bool:
    lower = stem.lower()
    if isNoisyStem(lower):
        return True
    if any(fragment in lower for fragment in FORM_LIKE_STEM_FRAGMENTS):
        return True
    if len(lower) >= 10 and not any("가" <= ch <= "힣" for ch in lower):
        return True
    if sum(1 for ch in lower if ch in ".-_") >= 1:
        return True
    return False


def relationStemIdsForSpec(spec: QuerySpec, stemToId: dict[str, int]) -> set[int]:
    stems: set[str] = set()
    for left, right in spec.relationPairs:
        stems.update(extractStems(f"{left} {right}", cap=16))
    stems.update(extractStems(" ".join(spec.mustAny), cap=32))
    stems.update(extractStems(" ".join(spec.supportAny), cap=32))
    out: set[int] = set()
    for stem in stems:
        stemId = stemToId.get(stem)
        if stemId is not None:
            out.add(stemId)
    return out


def buildQueryPurifiedRoleFrameSlotGroups(
    queryAutoRoleFrameSlotGroups: dict[str, tuple[tuple[str, ...], ...]],
    queryAutoCoreAnchorTerms: dict[str, tuple[str, ...]],
    stemToId: dict[str, int],
    stemUnits: list[list[int]],
    unitCount: int,
) -> dict[str, tuple[tuple[str, ...], ...]]:
    maxDf = max(int(unitCount * PURIFIED_ROLE_MAX_DF_RATIO), 1)
    maxSetSize = max(int(unitCount * 0.10), 500)
    out: dict[str, tuple[tuple[str, ...], ...]] = {}

    for spec in PROBE_QUERIES:
        groups = queryAutoRoleFrameSlotGroups.get(spec.query, ())
        anchors = queryAutoCoreAnchorTerms.get(spec.query, ())
        relationIds = relationStemIdsForSpec(spec, stemToId)
        relationUnitSets = {stemId: set(stemUnits[stemId][:maxSetSize]) for stemId in relationIds}
        purifiedGroups: list[tuple[str, ...]] = []
        for groupIndex, group in enumerate(groups):
            if not group:
                continue
            anchor = anchors[groupIndex] if groupIndex < len(anchors) else group[0]
            anchorId = stemToId.get(anchor)
            if anchorId is None:
                anchorId = stemToId.get(group[0])
                anchor = group[0]
            if anchorId is None:
                continue
            anchorUnits = set(stemUnits[anchorId][:maxSetSize])
            terms: list[tuple[float, str]] = [(1e9, anchor)]
            seen = {anchor}
            for term in group:
                term = term.lower()
                if term in seen:
                    continue
                termId = stemToId.get(term)
                if termId is None:
                    continue
                df = len(stemUnits[termId])
                if df > maxDf and termId not in relationIds:
                    continue
                if isFormLikeRoleStem(term) and termId not in relationIds:
                    continue
                termUnits = set(stemUnits[termId][:maxSetSize])
                anchorOverlap = len(anchorUnits & termUnits)
                relationOverlap = 0
                for relUnits in relationUnitSets.values():
                    relationOverlap += min(3, len(termUnits & relUnits))
                if (
                    anchorOverlap < PURIFIED_ROLE_MIN_ANCHOR_OVERLAP
                    and relationOverlap < PURIFIED_ROLE_MIN_RELATION_OVERLAP
                    and termId not in relationIds
                ):
                    continue
                idf = math.log((unitCount + 1) / (df + 1))
                score = anchorOverlap * 0.8 + relationOverlap * 1.4 + idf * 0.35
                terms.append((score, term))
                seen.add(term)
            terms.sort(reverse=True)
            kept = [term for _, term in terms[:PURIFIED_ROLE_GROUP_MAX_TERMS]]
            if kept:
                purifiedGroups.append(tuple(kept))
        out[spec.query] = tuple(purifiedGroups)
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


def buildAssociationFocusStemIds(stemToId: dict[str, int]) -> set[int]:
    stems: set[str] = set()
    for spec in PROBE_QUERIES:
        stems.update(extractStems(spec.query, cap=32))
        stems.update(extractStems(" ".join(spec.mustAny), cap=48))
        stems.update(extractStems(" ".join(spec.supportAny), cap=48))
        for left, right in spec.relationPairs:
            stems.update(extractStems(f"{left} {right}", cap=12))
        for group in spec.rubricGroups:
            stems.update(extractStems(" ".join(group), cap=24))
    for _, triggers, evidence in LEXICON_SLOT_GROUPS:
        stems.update(extractStems(" ".join(triggers), cap=48))
        stems.update(extractStems(" ".join(evidence), cap=64))
    out: set[int] = set()
    for stem in stems:
        stemId = stemToId.get(stem)
        if stemId is not None:
            out.add(stemId)
    return out


def buildPostingAssociationNeighbors(
    postingTable: list[tuple[int, ...]],
    idToStem: list[str],
    stemUnits: list[list[int]],
    stemFreq: list[int],
    focusStemIds: set[int],
) -> dict[int, list[tuple[int, float]]]:
    maxDf = max(int(len(postingTable) * 0.12), 300)
    assocCounts: dict[int, Counter[int]] = {stemId: Counter() for stemId in focusStemIds}
    for sequence in postingTable:
        if len(sequence) < 2:
            continue
        seqLen = len(sequence)
        for pos, centerId in enumerate(sequence):
            if centerId not in focusStemIds:
                continue
            leftStart = max(0, pos - ASSOC_WINDOW)
            rightEnd = min(seqLen, pos + ASSOC_WINDOW + 1)
            for otherPos in range(leftStart, rightEnd):
                if otherPos == pos:
                    continue
                otherId = sequence[otherPos]
                if otherId == centerId:
                    continue
                otherDf = len(stemUnits[otherId])
                if otherDf <= 1 or otherDf > maxDf or isNoisyStem(idToStem[otherId]):
                    continue
                assocCounts[centerId][otherId] += 1.0 / abs(otherPos - pos)

    unitCount = max(len(postingTable), 1)
    neighbors: dict[int, list[tuple[int, float]]] = {}
    for centerId, counts in assocCounts.items():
        scored: list[tuple[int, float]] = []
        centerFreq = max(stemFreq[centerId], 1)
        for otherId, count in counts.items():
            otherFreq = max(stemFreq[otherId], 1)
            otherDf = max(len(stemUnits[otherId]), 1)
            idf = math.log((unitCount + 1) / (otherDf + 1))
            score = float(count) * idf / math.sqrt(centerFreq * otherFreq)
            if score > 0:
                scored.append((otherId, score))
        scored.sort(key=lambda item: item[1], reverse=True)
        if scored:
            maxScore = scored[0][1]
            neighbors[centerId] = [
                (stemId, score / maxScore) for stemId, score in scored[:ASSOC_TOP_NEIGHBORS] if score > 0
            ]
    return neighbors


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
    associationFocusStemIds = buildAssociationFocusStemIds(stemToId)
    pairUnitsBuild: dict[tuple[int, int], list[int]] = defaultdict(list)
    unitTableLike = [isTableLike(unit) for unit in units]
    unitNegativeEvidenceBase = buildUnitNegativeEvidenceBase(units, unitTableLike)
    unitTypeBoostBase = buildUnitTypeBoostBase(units)
    unitSlotHitsBase = buildUnitSlotHitsBase(units)
    queryLexiconSlotGroups = buildQueryLexiconSlotGroups()
    queryTriggerSlotGroups = buildQueryTriggerSlotGroups()
    queryCoreAnchorTerms = buildQueryCoreAnchorTerms()
    queryAutoCoreAnchorTerms = buildQueryAutoCoreAnchorTerms(stemToId, stemUnits, len(units))
    queryCoreAnchorGroups = buildQueryCoreAnchorGroups(queryCoreAnchorTerms)
    queryAutoCoreAnchorGroups = buildQueryCoreAnchorGroups(queryAutoCoreAnchorTerms)
    unitLexiconSlotHitsBase = buildUnitLexiconSlotHitsBase(units, queryLexiconSlotGroups)
    unitCoreAnchorHitsBase = buildUnitLexiconSlotHitsBase(units, queryCoreAnchorGroups)
    unitTriggerSeedSlotHitsBase = buildUnitLexiconSlotHitsBase(units, queryTriggerSlotGroups)
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
    associationNeighbors = buildPostingAssociationNeighbors(
        postingTable,
        idToStem,
        stemUnits,
        stemFreq,
        associationFocusStemIds,
    )
    queryAutoSlotGroups = buildQueryAutoSlotGroups(
        queryLexiconSlotGroups,
        stemToId,
        idToStem,
        associationNeighbors,
    )
    unitAutoSlotHitsBase = buildUnitLexiconSlotHitsBase(units, queryAutoSlotGroups)
    querySupportAutoSlotGroups = buildQuerySupportAutoSlotGroups(
        queryLexiconSlotGroups,
        stemToId,
        idToStem,
        stemUnits,
        associationNeighbors,
        len(units),
    )
    unitSupportAutoSlotHitsBase = buildUnitLexiconSlotHitsBase(units, querySupportAutoSlotGroups)
    queryTriggerSupportSlotGroups = buildQuerySupportAutoSlotGroups(
        queryTriggerSlotGroups,
        stemToId,
        idToStem,
        stemUnits,
        associationNeighbors,
        len(units),
    )
    unitTriggerSupportSlotHitsBase = buildUnitLexiconSlotHitsBase(units, queryTriggerSupportSlotGroups)
    queryCohortSlotGroups = buildQueryCohortSlotGroups(
        stemToId,
        idToStem,
        stemUnits,
        postingTable,
        associationNeighbors,
    )
    unitCohortSlotHitsBase = buildUnitLexiconSlotHitsBase(units, queryCohortSlotGroups)
    queryRoleFrameSlotGroups = buildQueryRoleFrameSlotGroups(
        stemToId,
        idToStem,
        stemUnits,
        postingTable,
        associationNeighbors,
    )
    unitRoleFrameSlotHitsBase = buildUnitLexiconSlotHitsBase(units, queryRoleFrameSlotGroups)
    queryAutoRoleFrameSlotGroups = buildQueryAutoRoleFrameSlotGroups(
        stemToId,
        idToStem,
        stemUnits,
        postingTable,
        associationNeighbors,
        fireTable,
        fireNorm,
    )
    unitAutoRoleFrameSlotHitsBase = buildUnitLexiconSlotHitsBase(units, queryAutoRoleFrameSlotGroups)
    queryPurifiedRoleFrameSlotGroups = buildQueryPurifiedRoleFrameSlotGroups(
        queryAutoRoleFrameSlotGroups,
        queryAutoCoreAnchorTerms,
        stemToId,
        stemUnits,
        len(units),
    )
    unitPurifiedRoleFrameSlotHitsBase = buildUnitLexiconSlotHitsBase(units, queryPurifiedRoleFrameSlotGroups)
    unitAutoCoreAnchorHitsBase = buildUnitLexiconSlotHitsBase(units, queryAutoCoreAnchorGroups)

    elapsed = time.perf_counter() - t0
    print(
        f"[build] units={len(units):,} stems={len(idToStem):,} "
        f"postings={sum(len(seq) for seq in postingTable):,} buckets={HORIZON_BUCKETS:,} "
        f"focusStems={len(relationFocusStemIds):,} pairs={len(pairUnitsBuild):,} "
        f"pairPostings={sum(len(v) for v in pairUnitsBuild.values()):,} "
        f"assocFocus={len(associationFocusStemIds):,} assocEdges={sum(len(v) for v in associationNeighbors.values()):,} "
        f"slotHits={sum(len(v) for v in unitSlotHitsBase.values()):,} "
        f"lexSlotHits={sum(len(v) for v in unitLexiconSlotHitsBase.values()):,} "
        f"autoSlotHits={sum(len(v) for v in unitAutoSlotHitsBase.values()):,} "
        f"supportAutoSlotHits={sum(len(v) for v in unitSupportAutoSlotHitsBase.values()):,} "
        f"triggerSeedSlotHits={sum(len(v) for v in unitTriggerSeedSlotHitsBase.values()):,} "
        f"triggerSupportSlotHits={sum(len(v) for v in unitTriggerSupportSlotHitsBase.values()):,} "
        f"cohortSlotHits={sum(len(v) for v in unitCohortSlotHitsBase.values()):,} "
        f"roleFrameSlotHits={sum(len(v) for v in unitRoleFrameSlotHitsBase.values()):,} "
        f"autoRoleFrameSlotHits={sum(len(v) for v in unitAutoRoleFrameSlotHitsBase.values()):,} "
        f"purifiedRoleFrameSlotHits={sum(len(v) for v in unitPurifiedRoleFrameSlotHitsBase.values()):,} "
        f"coreAnchorHits={sum(len(v) for v in unitCoreAnchorHitsBase.values()):,} "
        f"autoCoreAnchorHits={sum(len(v) for v in unitAutoCoreAnchorHitsBase.values()):,} "
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
        associationNeighbors=associationNeighbors,
        unitTableLike=unitTableLike,
        unitNegativeEvidenceBase=unitNegativeEvidenceBase,
        unitTypeBoostBase=unitTypeBoostBase,
        unitSlotHitsBase=unitSlotHitsBase,
        unitLexiconSlotHitsBase=unitLexiconSlotHitsBase,
        unitAutoSlotHitsBase=unitAutoSlotHitsBase,
        unitSupportAutoSlotHitsBase=unitSupportAutoSlotHitsBase,
        unitTriggerSeedSlotHitsBase=unitTriggerSeedSlotHitsBase,
        unitTriggerSupportSlotHitsBase=unitTriggerSupportSlotHitsBase,
        unitCohortSlotHitsBase=unitCohortSlotHitsBase,
        unitRoleFrameSlotHitsBase=unitRoleFrameSlotHitsBase,
        unitAutoRoleFrameSlotHitsBase=unitAutoRoleFrameSlotHitsBase,
        unitPurifiedRoleFrameSlotHitsBase=unitPurifiedRoleFrameSlotHitsBase,
        unitCoreAnchorHitsBase=unitCoreAnchorHitsBase,
        unitAutoCoreAnchorHitsBase=unitAutoCoreAnchorHitsBase,
        queryLexiconSlotGroups=queryLexiconSlotGroups,
        queryAutoSlotGroups=queryAutoSlotGroups,
        querySupportAutoSlotGroups=querySupportAutoSlotGroups,
        queryTriggerSupportSlotGroups=queryTriggerSupportSlotGroups,
        queryCohortSlotGroups=queryCohortSlotGroups,
        queryRoleFrameSlotGroups=queryRoleFrameSlotGroups,
        queryAutoRoleFrameSlotGroups=queryAutoRoleFrameSlotGroups,
        queryPurifiedRoleFrameSlotGroups=queryPurifiedRoleFrameSlotGroups,
        queryCoreAnchorTerms=queryCoreAnchorTerms,
        queryAutoCoreAnchorTerms=queryAutoCoreAnchorTerms,
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


def expandQueryAssociation(model: Model, queryIds: list[int]) -> dict[int, float]:
    querySet = set(queryIds)
    scores: Counter[int] = Counter()
    for queryId in queryIds:
        for stemId, score in model.associationNeighbors.get(queryId, ()):
            if stemId not in querySet:
                scores[stemId] += score
    if not scores:
        return {}
    maxScore = max(scores.values())
    if maxScore <= 0:
        return {}
    return {stemId: float(score / maxScore) for stemId, score in scores.most_common(ASSOC_QUERY_STEMS) if score > 0}


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


def slotGroupHits(unit: Unit, spec: QuerySpec) -> int:
    if not spec.rubricGroups:
        return 0
    surface = compactText(f"{unit.reportName} {unit.sectionTitle} {unit.text}")
    hits = 0
    for group in spec.rubricGroups:
        if any(term.lower() in surface for term in group):
            hits += 1
    return hits


def slotCoverageBonusFromHits(hits: int, groupCount: int, coverage: float, pairHits: int) -> float:
    if groupCount <= 0:
        return 0.0
    if hits <= 0:
        return 0.0
    ratio = hits / groupCount
    bonus = SLOT_RERANK_WEIGHT * ratio
    if hits == groupCount:
        bonus += SLOT_RERANK_WEIGHT * 0.55
    elif hits == groupCount - 1 and (coverage >= 0.67 or pairHits > 0):
        bonus += SLOT_RERANK_WEIGHT * 0.15
    if hits <= 1 and coverage < 0.67 and pairHits == 0:
        bonus *= 0.35
    return bonus


def proxySlotCoverageBonus(
    model: Model, query: str, unitId: int, spec: QuerySpec | None, coverage: float, pairHits: int
) -> float:
    if spec is None or not spec.rubricGroups:
        return 0.0
    hits = model.unitSlotHitsBase.get(query, {}).get(unitId, 0)
    return slotCoverageBonusFromHits(hits, len(spec.rubricGroups), coverage, pairHits)


def lexiconSlotCoverageBonus(model: Model, query: str, unitId: int, coverage: float, pairHits: int) -> float:
    groups = model.queryLexiconSlotGroups.get(query, ())
    if not groups:
        return 0.0
    hits = model.unitLexiconSlotHitsBase.get(query, {}).get(unitId, 0)
    return slotCoverageBonusFromHits(hits, len(groups), coverage, pairHits)


def autoSlotCoverageBonus(model: Model, query: str, unitId: int, coverage: float, pairHits: int) -> float:
    groups = model.queryAutoSlotGroups.get(query, ())
    if not groups:
        return 0.0
    seedHits = model.unitLexiconSlotHitsBase.get(query, {}).get(unitId, 0)
    if seedHits <= 0:
        return 0.0
    autoHits = model.unitAutoSlotHitsBase.get(query, {}).get(unitId, 0)
    effectiveHits = max(seedHits, min(autoHits, seedHits + 1))
    return slotCoverageBonusFromHits(effectiveHits, len(groups), coverage, pairHits)


def prunedAutoSlotCoverageBonus(model: Model, query: str, unitId: int, coverage: float, pairHits: int) -> float:
    groups = model.queryAutoSlotGroups.get(query, ())
    if not groups:
        return 0.0
    seedHits = model.unitLexiconSlotHitsBase.get(query, {}).get(unitId, 0)
    if seedHits <= 0:
        return 0.0
    base = slotCoverageBonusFromHits(seedHits, len(groups), coverage, pairHits)
    if seedHits < min(PRUNED_AUTO_MIN_SEED_HITS, len(groups)):
        return base
    autoHits = model.unitAutoSlotHitsBase.get(query, {}).get(unitId, 0)
    if autoHits <= seedHits:
        return base
    delta = slotCoverageBonusFromHits(min(autoHits, seedHits + 1), len(groups), coverage, pairHits) - base
    if delta <= 0:
        return base
    return base + delta * PRUNED_AUTO_DELTA_WEIGHT


def supportAutoSlotCoverageBonus(model: Model, query: str, unitId: int, coverage: float, pairHits: int) -> float:
    groups = model.querySupportAutoSlotGroups.get(query, ())
    if not groups:
        return 0.0
    seedHits = model.unitLexiconSlotHitsBase.get(query, {}).get(unitId, 0)
    if seedHits <= 0:
        return 0.0
    base = slotCoverageBonusFromHits(seedHits, len(groups), coverage, pairHits)
    if seedHits < min(PRUNED_AUTO_MIN_SEED_HITS, len(groups)):
        return base
    supportHits = model.unitSupportAutoSlotHitsBase.get(query, {}).get(unitId, 0)
    if supportHits <= seedHits:
        return base
    delta = slotCoverageBonusFromHits(min(supportHits, seedHits + 1), len(groups), coverage, pairHits) - base
    if delta <= 0:
        return base
    return base + delta * PRUNED_AUTO_DELTA_WEIGHT


def triggerSupportSlotCoverageBonus(model: Model, query: str, unitId: int, coverage: float, pairHits: int) -> float:
    groups = model.queryTriggerSupportSlotGroups.get(query, ())
    if not groups:
        return 0.0
    seedHits = model.unitTriggerSeedSlotHitsBase.get(query, {}).get(unitId, 0)
    if seedHits < min(PRUNED_AUTO_MIN_SEED_HITS, len(groups)):
        return 0.0
    supportHits = model.unitTriggerSupportSlotHitsBase.get(query, {}).get(unitId, 0)
    if supportHits <= seedHits:
        return 0.0
    base = slotCoverageBonusFromHits(seedHits, len(groups), coverage, pairHits)
    boosted = slotCoverageBonusFromHits(min(supportHits, seedHits + 1), len(groups), coverage, pairHits)
    delta = boosted - base
    if delta <= 0:
        return 0.0
    return delta * PRUNED_AUTO_DELTA_WEIGHT


def cohortSlotCoverageBonus(model: Model, query: str, unitId: int, coverage: float, pairHits: int) -> float:
    groups = model.queryCohortSlotGroups.get(query, ())
    if not groups:
        return 0.0
    if coverage < 0.34 and pairHits == 0:
        return 0.0
    hits = model.unitCohortSlotHitsBase.get(query, {}).get(unitId, 0)
    if hits <= 0:
        return 0.0
    return slotCoverageBonusFromHits(hits, len(groups), coverage, pairHits) * COHORT_SLOT_WEIGHT_SCALE


def roleFrameNegativePenalty(model: Model, unitId: int, coverage: float, pairHits: int, roleHits: int) -> float:
    penalty = model.unitNegativeEvidenceBase[unitId]
    if penalty <= 0:
        return 0.0
    if roleHits >= 2:
        penalty *= 0.55
    if coverage >= 0.67 or pairHits > 0:
        penalty *= 0.7
    if penalty <= 0:
        return 0.0
    return min(ROLE_FRAME_NEGATIVE_WEIGHT * penalty, ROLE_FRAME_NEGATIVE_WEIGHT * 1.8)


def roleFrameSlotCoverageBonus(model: Model, query: str, unitId: int, coverage: float, pairHits: int) -> float:
    groups = model.queryRoleFrameSlotGroups.get(query, ())
    if not groups:
        return 0.0
    if coverage < 0.67 and pairHits == 0:
        if model.unitAutoCoreAnchorHitsBase.get(query, {}).get(unitId, 0) <= 0:
            return 0.0
    hits = model.unitRoleFrameSlotHitsBase.get(query, {}).get(unitId, 0)
    bonus = slotCoverageBonusFromHits(hits, len(groups), coverage, pairHits) * ROLE_FRAME_WEIGHT_SCALE
    return max(0.0, bonus - roleFrameNegativePenalty(model, unitId, coverage, pairHits, hits))


def autoRoleFrameSlotCoverageBonus(model: Model, query: str, unitId: int, coverage: float, pairHits: int) -> float:
    groups = model.queryAutoRoleFrameSlotGroups.get(query, ())
    if not groups:
        return 0.0
    if coverage < 0.67 and pairHits == 0:
        if model.unitCoreAnchorHitsBase.get(query, {}).get(unitId, 0) <= 0:
            return 0.0
    hits = model.unitAutoRoleFrameSlotHitsBase.get(query, {}).get(unitId, 0)
    bonus = slotCoverageBonusFromHits(hits, len(groups), coverage, pairHits) * AUTO_ROLE_FRAME_WEIGHT_SCALE
    return max(0.0, bonus - roleFrameNegativePenalty(model, unitId, coverage, pairHits, hits))


def purifiedRoleFrameSlotCoverageBonus(model: Model, query: str, unitId: int, coverage: float, pairHits: int) -> float:
    groups = model.queryPurifiedRoleFrameSlotGroups.get(query, ())
    if not groups:
        return 0.0
    if coverage < 0.67 and pairHits == 0:
        if model.unitAutoCoreAnchorHitsBase.get(query, {}).get(unitId, 0) <= 0:
            return 0.0
    hits = model.unitPurifiedRoleFrameSlotHitsBase.get(query, {}).get(unitId, 0)
    if hits <= 0:
        return 0.0
    bonus = slotCoverageBonusFromHits(hits, len(groups), coverage, pairHits) * PURIFIED_ROLE_FRAME_WEIGHT_SCALE
    return max(0.0, bonus - roleFrameNegativePenalty(model, unitId, coverage, pairHits, hits) * 0.35)


def diversityPenalty(model: Model, unitId: int, selectedUnitIds: list[int]) -> float:
    if not selectedUnitIds:
        return 0.0
    unit = model.units[unitId]
    textKey = unitDedupeKey(unit.text)[:160]
    corpReport = (unit.corpName, unit.reportName)
    corpSection = (unit.corpName, unit.sectionTitle)
    penalty = 0.0
    for selectedId in selectedUnitIds:
        selected = model.units[selectedId]
        if unitDedupeKey(selected.text)[:160] == textKey:
            penalty += DIVERSITY_TEXT_PENALTY
        if (selected.corpName, selected.reportName) == corpReport:
            penalty += DIVERSITY_CORP_REPORT_PENALTY
        if (selected.corpName, selected.sectionTitle) == corpSection:
            penalty += DIVERSITY_CORP_SECTION_PENALTY
    return penalty


def applyDiversityRerank(
    model: Model,
    ranked: list[tuple[float, int, list[str], list[str]]],
    topK: int,
) -> list[tuple[float, int, list[str], list[str]]]:
    remaining = ranked[:]
    selected: list[tuple[float, int, list[str], list[str]]] = []
    selectedUnitIds: list[int] = []
    while remaining and len(selected) < topK:
        bestIndex = 0
        bestAdjusted = -1e18
        for index, row in enumerate(remaining):
            adjusted = row[0] - diversityPenalty(model, row[1], selectedUnitIds)
            if adjusted > bestAdjusted:
                bestAdjusted = adjusted
                bestIndex = index
        score, unitId, exact, semantic = remaining.pop(bestIndex)
        selected.append((float(bestAdjusted), unitId, exact, semantic))
        selectedUnitIds.append(unitId)
    return selected


def search(
    model: Model,
    query: str,
    *,
    topK: int = TOP_K,
    useFire: bool = True,
    useAssociation: bool = False,
    useSlot: bool = False,
    useLexiconSlot: bool = False,
    useAutoSlot: bool = False,
    usePrunedAutoSlot: bool = False,
    useSupportAutoSlot: bool = False,
    useTriggerSupportSlot: bool = False,
    useCohortSlot: bool = False,
    useRoleFrameSlot: bool = False,
    useAutoRoleFrameSlot: bool = False,
    usePurifiedMeaningLearner: bool = False,
    useDiversity: bool = False,
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

    association = expandQueryAssociation(model, queryIds) if useAssociation else {}
    associationSet = set(association)

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
        if useSlot:
            scores[unitId] += proxySlotCoverageBonus(model, query, unitId, spec, coverage, pairHits)
        if useLexiconSlot:
            scores[unitId] += lexiconSlotCoverageBonus(model, query, unitId, coverage, pairHits)
        if useAutoSlot:
            scores[unitId] += autoSlotCoverageBonus(model, query, unitId, coverage, pairHits)
        if usePrunedAutoSlot:
            scores[unitId] += prunedAutoSlotCoverageBonus(model, query, unitId, coverage, pairHits)
        if useSupportAutoSlot:
            scores[unitId] += supportAutoSlotCoverageBonus(model, query, unitId, coverage, pairHits)
        if useTriggerSupportSlot:
            scores[unitId] += triggerSupportSlotCoverageBonus(model, query, unitId, coverage, pairHits)
        if useCohortSlot:
            scores[unitId] += cohortSlotCoverageBonus(model, query, unitId, coverage, pairHits)
        if useRoleFrameSlot:
            scores[unitId] += cohortSlotCoverageBonus(model, query, unitId, coverage, pairHits)
            scores[unitId] += roleFrameSlotCoverageBonus(model, query, unitId, coverage, pairHits)
        if useAutoRoleFrameSlot:
            scores[unitId] += cohortSlotCoverageBonus(model, query, unitId, coverage, pairHits)
            scores[unitId] += autoRoleFrameSlotCoverageBonus(model, query, unitId, coverage, pairHits)
        if usePurifiedMeaningLearner:
            scores[unitId] += cohortSlotCoverageBonus(model, query, unitId, coverage, pairHits)
            scores[unitId] += autoRoleFrameSlotCoverageBonus(model, query, unitId, coverage, pairHits)
            scores[unitId] += purifiedRoleFrameSlotCoverageBonus(model, query, unitId, coverage, pairHits)
        if model.unitTableLike[unitId] and coverage < 1.0 and pairHits == 0:
            scores[unitId] -= TABLE_PENALTY
        if useAssociation and association:
            assocStemIds = sorted(unitStemIds & associationSet, key=lambda sid: association[sid], reverse=True)[:6]
            if assocStemIds:
                for stemId in assocStemIds:
                    expandedHits[unitId].add(stemId)
                if coverage >= 0.34 or pairHits > 0:
                    scores[unitId] += min(ASSOC_WEIGHT, sum(association[stemId] for stemId in assocStemIds) * 1.25)
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
    if useDiversity:
        return applyDiversityRerank(model, ranked[: topK * 8], topK)
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
    assocCells = sum(len(neighbors) for neighbors in model.associationNeighbors.values())
    typeCells = sum(len(unitScores) for unitScores in model.unitTypeBoostBase.values())
    slotCells = sum(len(unitHits) for unitHits in model.unitSlotHitsBase.values())
    lexSlotCells = sum(len(unitHits) for unitHits in model.unitLexiconSlotHitsBase.values())
    autoSlotCells = sum(len(unitHits) for unitHits in model.unitAutoSlotHitsBase.values())
    supportAutoSlotCells = sum(len(unitHits) for unitHits in model.unitSupportAutoSlotHitsBase.values())
    triggerSeedSlotCells = sum(len(unitHits) for unitHits in model.unitTriggerSeedSlotHitsBase.values())
    triggerSupportSlotCells = sum(len(unitHits) for unitHits in model.unitTriggerSupportSlotHitsBase.values())
    cohortSlotCells = sum(len(unitHits) for unitHits in model.unitCohortSlotHitsBase.values())
    roleFrameSlotCells = sum(len(unitHits) for unitHits in model.unitRoleFrameSlotHitsBase.values())
    autoRoleFrameSlotCells = sum(len(unitHits) for unitHits in model.unitAutoRoleFrameSlotHitsBase.values())
    purifiedRoleFrameSlotCells = sum(len(unitHits) for unitHits in model.unitPurifiedRoleFrameSlotHitsBase.values())
    coreAnchorCells = sum(len(unitHits) for unitHits in model.unitCoreAnchorHitsBase.values())
    stemChars = sum(len(stem) for stem in model.idToStem)
    roughBytes = (
        postingCells * 4
        + unitChars * 2
        + fireCells * 12
        + pairCells * 4
        + assocCells * 8
        + typeCells * 8
        + slotCells * 6
        + lexSlotCells * 6
        + autoSlotCells * 6
        + supportAutoSlotCells * 6
        + triggerSeedSlotCells * 6
        + triggerSupportSlotCells * 6
        + cohortSlotCells * 6
        + roleFrameSlotCells * 6
        + autoRoleFrameSlotCells * 6
        + purifiedRoleFrameSlotCells * 6
        + coreAnchorCells * 6
        + stemChars * 2
    )
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


def summarizeMode(
    model: Model,
    spec: QuerySpec,
    *,
    useFire: bool,
    useAssociation: bool = False,
    useSlot: bool = False,
    useLexiconSlot: bool = False,
    useAutoSlot: bool = False,
    usePrunedAutoSlot: bool = False,
    useSupportAutoSlot: bool = False,
    useTriggerSupportSlot: bool = False,
    useCohortSlot: bool = False,
    useRoleFrameSlot: bool = False,
    useAutoRoleFrameSlot: bool = False,
    usePurifiedMeaningLearner: bool = False,
    useDiversity: bool = False,
) -> dict[str, object]:
    t0 = time.perf_counter()
    rows = search(
        model,
        spec.query,
        useFire=useFire,
        useAssociation=useAssociation,
        useSlot=useSlot,
        useLexiconSlot=useLexiconSlot,
        useAutoSlot=useAutoSlot,
        usePrunedAutoSlot=usePrunedAutoSlot,
        useSupportAutoSlot=useSupportAutoSlot,
        useTriggerSupportSlot=useTriggerSupportSlot,
        useCohortSlot=useCohortSlot,
        useRoleFrameSlot=useRoleFrameSlot,
        useAutoRoleFrameSlot=useAutoRoleFrameSlot,
        usePurifiedMeaningLearner=usePurifiedMeaningLearner,
        useDiversity=useDiversity,
    )
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


def formatLearnedRoleClusters(model: Model, query: str) -> list[str]:
    anchors = model.queryAutoCoreAnchorTerms.get(query, ())
    groups = model.queryPurifiedRoleFrameSlotGroups.get(query, ())
    clusters: list[str] = []
    for index, group in enumerate(groups, start=1):
        anchor = anchors[index - 1] if index <= len(anchors) else f"role{index}"
        terms = ",".join(group[:6])
        clusters.append(f"{anchor}=>{terms}")
    return clusters


def roleClusterStats(groupsByQuery: dict[str, tuple[tuple[str, ...], ...]]) -> tuple[int, int, int]:
    clusterCount = 0
    termCount = 0
    formLikeCount = 0
    for groups in groupsByQuery.values():
        clusterCount += len(groups)
        for group in groups:
            termCount += len(group)
            formLikeCount += sum(1 for term in group if isFormLikeRoleStem(term))
    return clusterCount, termCount, formLikeCount


def termSurfaceScore(term: str, evidenceSurface: str, queryTerms: set[str], clusterTerms: set[str]) -> float:
    score = 0.0
    if term in queryTerms:
        score += 4.0
    if term in clusterTerms:
        score += 2.0
    if term and term in evidenceSurface:
        score += 3.0
    return score


def slotForTerm(term: str) -> str:
    for slot, hints in ANSWER_FRAME_SLOT_HINTS.items():
        if any(hint in term or term in hint for hint in hints):
            return slot
    return "target"


def selectSlotTerms(candidates: dict[str, Counter[str]], slot: str, limit: int) -> tuple[str, ...]:
    counter = candidates.get(slot)
    if not counter:
        return ()
    ranked = sorted(counter.items(), key=lambda item: (-item[1], len(item[0]), item[0]))
    return tuple(term for term, _ in ranked[:limit])


def buildEvidenceGroundedAnswerFrame(
    model: Model,
    spec: QuerySpec,
    rows: list[tuple[float, int, list[str], list[str]]],
) -> AnswerFrame:
    queryTerms = set(extractStems(spec.query, cap=32))
    coreAnchors = tuple(model.queryAutoCoreAnchorTerms.get(spec.query, ()))
    coreAnchorSet = set(coreAnchors)
    specMustTerms = {
        stem for marker in spec.mustAny for stem in extractStems(marker, cap=8) if slotForTerm(stem) == "target"
    }
    queryTargetTerms = {term for term in queryTerms if slotForTerm(term) == "target"}
    targetAllowedTerms = coreAnchorSet | queryTargetTerms | specMustTerms
    clusterGroups = model.queryPurifiedRoleFrameSlotGroups.get(spec.query, ())
    clusterTerms = {term for group in clusterGroups for term in group}
    evidenceSurface = compactText(
        " ".join(
            f"{model.units[unitId].reportName} {model.units[unitId].sectionTitle} {model.units[unitId].text}"
            for _, unitId, _, _ in rows[:3]
        )
    )
    candidates: dict[str, Counter[str]] = {
        "target": Counter(),
        "action": Counter(),
        "change": Counter(),
        "risk": Counter(),
        "purpose": Counter(),
    }
    for term in queryTerms | clusterTerms:
        if not term or isFormLikeRoleStem(term):
            continue
        slot = slotForTerm(term)
        score = termSurfaceScore(term, evidenceSurface, queryTerms, clusterTerms)
        if slot == "target":
            if term not in targetAllowedTerms:
                continue
            if score < ANSWER_FRAME_MIN_TARGET_SCORE and term not in coreAnchorSet:
                continue
        else:
            if term not in queryTerms and term not in evidenceSurface:
                continue
            if score < ANSWER_FRAME_MIN_RELATION_SCORE:
                continue
        if score <= 0:
            continue
        candidates[slot][term] += score
    if not candidates["target"]:
        for anchor in coreAnchors:
            if slotForTerm(anchor) == "target":
                candidates["target"][anchor] += max(
                    3.0, termSurfaceScore(anchor, evidenceSurface, queryTerms, clusterTerms)
                )
    evidence: list[str] = []
    for rank, (_, unitId, exact, semantic) in enumerate(rows[:3], start=1):
        unit = model.units[unitId]
        snippet = compactText(unit.text)
        if len(snippet) > 96:
            snippet = snippet[:96] + "..."
        exactText = ",".join(exact[:4]) or "-"
        semanticText = ",".join(semantic[:4]) or "-"
        evidence.append(
            f"{rank}:{unit.corpName}/{unit.reportName}/{unit.sectionTitle}"
            f"/exact={exactText}/semantic={semanticText}/snippet={snippet}"
        )
    target = selectSlotTerms(candidates, "target", ANSWER_FRAME_TARGET_LIMIT)
    action = selectSlotTerms(candidates, "action", 2)
    change = selectSlotTerms(candidates, "change", 2)
    risk = selectSlotTerms(candidates, "risk", 2)
    purpose = selectSlotTerms(candidates, "purpose", 2)
    relationSlots = sum(1 for slotTerms in (action, change, risk, purpose) if slotTerms)
    evidenceRubrics = [rubricQuality(model.units[unitId], spec) for _, unitId, _, _ in rows[:3]]
    evidenceRubric = sum(evidenceRubrics)
    evidenceStrongHits = sum(1 for quality in evidenceRubrics if quality == 2)
    targetScore = min(1.0, len(target) / max(ANSWER_FRAME_TARGET_LIMIT, 1))
    relationScore = 1.0 if relationSlots else 0.0
    evidenceScore = min(1.0, evidenceRubric / 6.0)
    evidenceCountScore = min(1.0, len(evidence) / 3)
    confidence = round(
        min(
            0.95,
            (0.20 * targetScore) + (0.25 * relationScore) + (0.45 * evidenceScore) + (0.10 * evidenceCountScore),
        ),
        2,
    )
    return AnswerFrame(
        query=spec.query,
        target=target,
        action=action,
        change=change,
        risk=risk,
        purpose=purpose,
        evidence=tuple(evidence),
        evidenceRubric=evidenceRubric,
        evidenceStrongHits=evidenceStrongHits,
        confidence=confidence,
    )


def buildAnswerFrameLine(
    model: Model,
    spec: QuerySpec,
    rows: list[tuple[float, int, list[str], list[str]]],
) -> str:
    frame = buildEvidenceGroundedAnswerFrame(model, spec, rows)
    coreAnchors = ",".join(model.queryAutoCoreAnchorTerms.get(spec.query, ())) or "-"
    roleClusters = " | ".join(formatLearnedRoleClusters(model, spec.query)) or "-"
    evidence = " || ".join(frame.evidence) or "-"
    return (
        f"[frame] query='{frame.query}' core='{coreAnchors}' "
        f"target='{','.join(frame.target) or '-'}' action='{','.join(frame.action) or '-'}' "
        f"change='{','.join(frame.change) or '-'}' risk='{','.join(frame.risk) or '-'}' "
        f"purpose='{','.join(frame.purpose) or '-'}' confidence={frame.confidence:.2f} "
        f"evidenceRubric={frame.evidenceRubric} strongHits={frame.evidenceStrongHits} "
        f"roles='{roleClusters}' evidenceCount={len(frame.evidence)} evidence={evidence}"
    )


def answerFrameCompleteness(frame: AnswerFrame) -> tuple[int, bool, bool]:
    hasTarget = bool(frame.target)
    hasRelation = bool(frame.action or frame.change or frame.risk or frame.purpose)
    hasEvidence = bool(frame.evidence)
    return int(hasTarget) + int(hasRelation) + int(hasEvidence), hasTarget, hasRelation


def evaluateExperiment(model: Model) -> None:
    print("\n" + "=" * 88)
    print(
        "[evaluation] exact-only vs exact+fire vs exact+association vs proxySlot vs lexSlot vs autoSlot vs prunedAutoSlot vs supportAutoSlot vs triggerSupportSlot vs cohortSlot vs roleFrameSlot vs meaningLearner vs purifiedMeaningLearner"
    )
    print("=" * 88)
    noiseCount, noiseRatio, noiseExamples = summarizeNoise(model)
    print(
        f"[model] roughMemoryMb={estimateMemoryMb(model):.1f} noisyStems={noiseCount:,}/{len(model.idToStem):,} ({noiseRatio:.1%})"
    )
    print(f"[noise examples] {noiseExamples[:12]}")

    modeNames = (
        "exact",
        "fire",
        "assoc",
        "proxySlot",
        "lexSlot",
        "autoSlot",
        "prunedAutoSlot",
        "supportAutoSlot",
        "triggerSupportSlot",
        "cohortSlot",
        "roleFrameSlot",
        "autoRoleFrameSlot",
        "purifiedMeaningLearner",
    )
    compareNames = (
        "fire",
        "assoc",
        "proxySlot",
        "lexSlot",
        "autoSlot",
        "prunedAutoSlot",
        "supportAutoSlot",
        "triggerSupportSlot",
        "cohortSlot",
        "roleFrameSlot",
        "autoRoleFrameSlot",
        "purifiedMeaningLearner",
    )
    totals = {name: 0 for name in modeNames}
    rubricTotals = {name: 0 for name in modeNames}
    latencies: dict[str, list[float]] = {name: [] for name in modeNames}
    duplicates = {name: 0 for name in compareNames}
    tables = {name: 0 for name in compareNames}
    verdicts = {name: {"improved": 0, "same": 0, "worsened": 0} for name in compareNames}
    rubricVerdicts = {name: {"improved": 0, "same": 0, "worsened": 0} for name in compareNames}
    learnedRoleClusters, learnedRoleTerms, learnedFormLikeTerms = roleClusterStats(model.queryAutoRoleFrameSlotGroups)
    purifiedRoleClusters, purifiedRoleTerms, purifiedFormLikeTerms = roleClusterStats(
        model.queryPurifiedRoleFrameSlotGroups
    )
    answerFrames = 0
    fullAnswerFrames = 0
    framedTargets = 0
    framedRelations = 0
    frameCompletenessTotal = 0
    frameConfidenceSum = 0.0
    frameEvidenceRubricTotal = 0
    frameStrongHitTotal = 0

    def classify(candidateScore: int, baseScore: int, target: dict[str, int]) -> str:
        if candidateScore > baseScore:
            target["improved"] += 1
            return "IMPROVED"
        if candidateScore < baseScore:
            target["worsened"] += 1
            return "WORSENED"
        target["same"] += 1
        return "SAME"

    for spec in PROBE_QUERIES:
        modes = {
            "exact": summarizeMode(model, spec, useFire=False),
            "fire": summarizeMode(model, spec, useFire=True),
            "assoc": summarizeMode(model, spec, useFire=False, useAssociation=True),
            "proxySlot": summarizeMode(model, spec, useFire=False, useSlot=True),
            "lexSlot": summarizeMode(model, spec, useFire=False, useLexiconSlot=True),
            "autoSlot": summarizeMode(model, spec, useFire=False, useAutoSlot=True),
            "prunedAutoSlot": summarizeMode(model, spec, useFire=False, usePrunedAutoSlot=True),
            "supportAutoSlot": summarizeMode(model, spec, useFire=False, useSupportAutoSlot=True),
            "triggerSupportSlot": summarizeMode(model, spec, useFire=False, useTriggerSupportSlot=True),
            "cohortSlot": summarizeMode(model, spec, useFire=False, useCohortSlot=True),
            "roleFrameSlot": summarizeMode(model, spec, useFire=False, useRoleFrameSlot=True),
            "autoRoleFrameSlot": summarizeMode(
                model, spec, useFire=False, useAutoRoleFrameSlot=True, useDiversity=True
            ),
            "purifiedMeaningLearner": summarizeMode(
                model, spec, useFire=False, usePurifiedMeaningLearner=True, useDiversity=True
            ),
        }
        quality = {name: int(result["qualitySum"]) for name, result in modes.items()}
        rubric = {name: int(result["rubricQualitySum"]) for name, result in modes.items()}
        for name, result in modes.items():
            totals[name] += quality[name]
            rubricTotals[name] += rubric[name]
            latencies[name].append(float(result["latencyMs"]))
            if name != "exact":
                duplicates[name] += int(result["duplicates"])
                tables[name] += int(result["tables"])

        fireVerdict = classify(quality["fire"], quality["exact"], verdicts["fire"])
        fireRubricVerdict = classify(rubric["fire"], rubric["exact"], rubricVerdicts["fire"])
        assocVerdict = classify(quality["assoc"], quality["exact"], verdicts["assoc"])
        assocRubricVerdict = classify(rubric["assoc"], rubric["exact"], rubricVerdicts["assoc"])
        proxySlotVerdict = classify(quality["proxySlot"], quality["exact"], verdicts["proxySlot"])
        proxySlotRubricVerdict = classify(rubric["proxySlot"], rubric["exact"], rubricVerdicts["proxySlot"])
        lexSlotVerdict = classify(quality["lexSlot"], quality["exact"], verdicts["lexSlot"])
        lexSlotRubricVerdict = classify(rubric["lexSlot"], rubric["exact"], rubricVerdicts["lexSlot"])
        autoSlotVerdict = classify(quality["autoSlot"], quality["exact"], verdicts["autoSlot"])
        autoSlotRubricVerdict = classify(rubric["autoSlot"], rubric["exact"], rubricVerdicts["autoSlot"])
        prunedAutoSlotVerdict = classify(quality["prunedAutoSlot"], quality["exact"], verdicts["prunedAutoSlot"])
        prunedAutoSlotRubricVerdict = classify(
            rubric["prunedAutoSlot"], rubric["exact"], rubricVerdicts["prunedAutoSlot"]
        )
        supportAutoSlotVerdict = classify(quality["supportAutoSlot"], quality["exact"], verdicts["supportAutoSlot"])
        supportAutoSlotRubricVerdict = classify(
            rubric["supportAutoSlot"], rubric["exact"], rubricVerdicts["supportAutoSlot"]
        )
        triggerSupportSlotVerdict = classify(
            quality["triggerSupportSlot"], quality["exact"], verdicts["triggerSupportSlot"]
        )
        triggerSupportSlotRubricVerdict = classify(
            rubric["triggerSupportSlot"], rubric["exact"], rubricVerdicts["triggerSupportSlot"]
        )
        cohortSlotVerdict = classify(quality["cohortSlot"], quality["exact"], verdicts["cohortSlot"])
        cohortSlotRubricVerdict = classify(rubric["cohortSlot"], rubric["exact"], rubricVerdicts["cohortSlot"])
        roleFrameSlotVerdict = classify(quality["roleFrameSlot"], quality["exact"], verdicts["roleFrameSlot"])
        roleFrameSlotRubricVerdict = classify(rubric["roleFrameSlot"], rubric["exact"], rubricVerdicts["roleFrameSlot"])
        autoRoleFrameSlotVerdict = classify(
            quality["autoRoleFrameSlot"], quality["exact"], verdicts["autoRoleFrameSlot"]
        )
        autoRoleFrameSlotRubricVerdict = classify(
            rubric["autoRoleFrameSlot"], rubric["exact"], rubricVerdicts["autoRoleFrameSlot"]
        )
        purifiedMeaningLearnerVerdict = classify(
            quality["purifiedMeaningLearner"], quality["exact"], verdicts["purifiedMeaningLearner"]
        )
        purifiedMeaningLearnerRubricVerdict = classify(
            rubric["purifiedMeaningLearner"], rubric["exact"], rubricVerdicts["purifiedMeaningLearner"]
        )

        print("\n" + "-" * 88)
        print(
            f"[query] {spec.query} "
            f"fireVerdict={fireVerdict} fireRubricVerdict={fireRubricVerdict} "
            f"assocVerdict={assocVerdict} assocRubricVerdict={assocRubricVerdict} "
            f"proxySlotVerdict={proxySlotVerdict} proxySlotRubricVerdict={proxySlotRubricVerdict} "
            f"lexSlotVerdict={lexSlotVerdict} lexSlotRubricVerdict={lexSlotRubricVerdict} "
            f"autoSlotVerdict={autoSlotVerdict} autoSlotRubricVerdict={autoSlotRubricVerdict} "
            f"prunedAutoSlotVerdict={prunedAutoSlotVerdict} prunedAutoSlotRubricVerdict={prunedAutoSlotRubricVerdict} "
            f"supportAutoSlotVerdict={supportAutoSlotVerdict} supportAutoSlotRubricVerdict={supportAutoSlotRubricVerdict} "
            f"triggerSupportSlotVerdict={triggerSupportSlotVerdict} triggerSupportSlotRubricVerdict={triggerSupportSlotRubricVerdict} "
            f"cohortSlotVerdict={cohortSlotVerdict} cohortSlotRubricVerdict={cohortSlotRubricVerdict} "
            f"roleFrameSlotVerdict={roleFrameSlotVerdict} roleFrameSlotRubricVerdict={roleFrameSlotRubricVerdict} "
            f"autoRoleFrameSlotVerdict={autoRoleFrameSlotVerdict} autoRoleFrameSlotRubricVerdict={autoRoleFrameSlotRubricVerdict} "
            f"exactQuality={quality['exact']} fireQuality={quality['fire']} "
            f"assocQuality={quality['assoc']} proxySlotQuality={quality['proxySlot']} "
            f"lexSlotQuality={quality['lexSlot']} autoSlotQuality={quality['autoSlot']} "
            f"prunedAutoSlotQuality={quality['prunedAutoSlot']} supportAutoSlotQuality={quality['supportAutoSlot']} "
            f"triggerSupportSlotQuality={quality['triggerSupportSlot']} cohortSlotQuality={quality['cohortSlot']} "
            f"roleFrameSlotQuality={quality['roleFrameSlot']} "
            f"autoRoleFrameSlotQuality={quality['autoRoleFrameSlot']} "
            f"exactRubric={rubric['exact']} fireRubric={rubric['fire']} "
            f"assocRubric={rubric['assoc']} proxySlotRubric={rubric['proxySlot']} "
            f"lexSlotRubric={rubric['lexSlot']} autoSlotRubric={rubric['autoSlot']} "
            f"prunedAutoSlotRubric={rubric['prunedAutoSlot']} supportAutoSlotRubric={rubric['supportAutoSlot']} "
            f"triggerSupportSlotRubric={rubric['triggerSupportSlot']} cohortSlotRubric={rubric['cohortSlot']} "
            f"roleFrameSlotRubric={rubric['roleFrameSlot']} "
            f"autoRoleFrameSlotRubric={rubric['autoRoleFrameSlot']} "
            f"exactMs={float(modes['exact']['latencyMs']):.2f} "
            f"fireMs={float(modes['fire']['latencyMs']):.2f} "
            f"assocMs={float(modes['assoc']['latencyMs']):.2f} "
            f"proxySlotMs={float(modes['proxySlot']['latencyMs']):.2f} "
            f"lexSlotMs={float(modes['lexSlot']['latencyMs']):.2f} "
            f"autoSlotMs={float(modes['autoSlot']['latencyMs']):.2f} "
            f"prunedAutoSlotMs={float(modes['prunedAutoSlot']['latencyMs']):.2f} "
            f"supportAutoSlotMs={float(modes['supportAutoSlot']['latencyMs']):.2f} "
            f"triggerSupportSlotMs={float(modes['triggerSupportSlot']['latencyMs']):.2f} "
            f"cohortSlotMs={float(modes['cohortSlot']['latencyMs']):.2f} "
            f"roleFrameSlotMs={float(modes['roleFrameSlot']['latencyMs']):.2f} "
            f"autoRoleFrameSlotMs={float(modes['autoRoleFrameSlot']['latencyMs']):.2f} "
            f"fireDup={modes['fire']['duplicates']} fireTable={modes['fire']['tables']} "
            f"assocDup={modes['assoc']['duplicates']} assocTable={modes['assoc']['tables']} "
            f"proxySlotDup={modes['proxySlot']['duplicates']} proxySlotTable={modes['proxySlot']['tables']} "
            f"lexSlotDup={modes['lexSlot']['duplicates']} lexSlotTable={modes['lexSlot']['tables']} "
            f"autoSlotDup={modes['autoSlot']['duplicates']} autoSlotTable={modes['autoSlot']['tables']} "
            f"prunedAutoSlotDup={modes['prunedAutoSlot']['duplicates']} prunedAutoSlotTable={modes['prunedAutoSlot']['tables']} "
            f"supportAutoSlotDup={modes['supportAutoSlot']['duplicates']} supportAutoSlotTable={modes['supportAutoSlot']['tables']} "
            f"triggerSupportSlotDup={modes['triggerSupportSlot']['duplicates']} triggerSupportSlotTable={modes['triggerSupportSlot']['tables']} "
            f"cohortSlotDup={modes['cohortSlot']['duplicates']} cohortSlotTable={modes['cohortSlot']['tables']} "
            f"roleFrameSlotDup={modes['roleFrameSlot']['duplicates']} roleFrameSlotTable={modes['roleFrameSlot']['tables']} "
            f"autoRoleFrameSlotDup={modes['autoRoleFrameSlot']['duplicates']} autoRoleFrameSlotTable={modes['autoRoleFrameSlot']['tables']}"
        )
        print("  [exact-only top5]")
        printRows(model, modes["exact"]["rows"])  # type: ignore[arg-type]
        print("  [exact+fire top5]")
        printRows(model, modes["fire"]["rows"])  # type: ignore[arg-type]
        print("  [exact+association top5]")
        printRows(model, modes["assoc"]["rows"])  # type: ignore[arg-type]
        print("  [exact+proxySlot top5]")
        printRows(model, modes["proxySlot"]["rows"])  # type: ignore[arg-type]
        print("  [exact+lexSlot top5]")
        printRows(model, modes["lexSlot"]["rows"])  # type: ignore[arg-type]
        print("  [exact+autoSlot top5]")
        printRows(model, modes["autoSlot"]["rows"])  # type: ignore[arg-type]
        print("  [exact+prunedAutoSlot top5]")
        printRows(model, modes["prunedAutoSlot"]["rows"])  # type: ignore[arg-type]
        print("  [exact+supportAutoSlot top5]")
        printRows(model, modes["supportAutoSlot"]["rows"])  # type: ignore[arg-type]
        print("  [exact+triggerSupportSlot top5]")
        printRows(model, modes["triggerSupportSlot"]["rows"])  # type: ignore[arg-type]
        print("  [exact+cohortSlot top5]")
        printRows(model, modes["cohortSlot"]["rows"])  # type: ignore[arg-type]
        print("  [exact+roleFrameSlot top5]")
        printRows(model, modes["roleFrameSlot"]["rows"])  # type: ignore[arg-type]
        print("  [exact+autoRoleFrameSlot top5]")
        printRows(model, modes["autoRoleFrameSlot"]["rows"])  # type: ignore[arg-type]
        print(
            f"[query-purified] {spec.query} "
            f"purifiedVerdict={purifiedMeaningLearnerVerdict} "
            f"purifiedRubricVerdict={purifiedMeaningLearnerRubricVerdict} "
            f"purifiedQuality={quality['purifiedMeaningLearner']} "
            f"purifiedRubric={rubric['purifiedMeaningLearner']} "
            f"purifiedMs={float(modes['purifiedMeaningLearner']['latencyMs']):.2f} "
            f"purifiedDup={modes['purifiedMeaningLearner']['duplicates']} "
            f"purifiedTable={modes['purifiedMeaningLearner']['tables']}"
        )
        print("  [exact+purifiedMeaningLearner top5]")
        printRows(model, modes["purifiedMeaningLearner"]["rows"])  # type: ignore[arg-type]
        frameRows = modes["purifiedMeaningLearner"]["rows"]  # type: ignore[assignment]
        frame = buildEvidenceGroundedAnswerFrame(model, spec, frameRows)  # type: ignore[arg-type]
        completeness, hasTarget, hasRelation = answerFrameCompleteness(frame)
        answerFrames += 1
        fullAnswerFrames += int(completeness == 3)
        framedTargets += int(hasTarget)
        framedRelations += int(hasRelation)
        frameCompletenessTotal += completeness
        frameConfidenceSum += frame.confidence
        frameEvidenceRubricTotal += frame.evidenceRubric
        frameStrongHitTotal += frame.evidenceStrongHits
        print(
            buildAnswerFrameLine(
                model,
                spec,
                frameRows,  # type: ignore[arg-type]
            )
        )

    print("\n" + "=" * 88)
    print(
        f"[summary] exactQuality={totals['exact']} fireQuality={totals['fire']} "
        f"assocQuality={totals['assoc']} proxySlotQuality={totals['proxySlot']} "
        f"lexSlotQuality={totals['lexSlot']} autoSlotQuality={totals['autoSlot']} "
        f"prunedAutoSlotQuality={totals['prunedAutoSlot']} supportAutoSlotQuality={totals['supportAutoSlot']} "
        f"triggerSupportSlotQuality={totals['triggerSupportSlot']} cohortSlotQuality={totals['cohortSlot']} "
        f"roleFrameSlotQuality={totals['roleFrameSlot']} "
        f"autoRoleFrameSlotQuality={totals['autoRoleFrameSlot']} "
        f"purifiedMeaningLearnerQuality={totals['purifiedMeaningLearner']} "
        f"fireImproved={verdicts['fire']['improved']} fireSame={verdicts['fire']['same']} fireWorsened={verdicts['fire']['worsened']} "
        f"assocImproved={verdicts['assoc']['improved']} assocSame={verdicts['assoc']['same']} assocWorsened={verdicts['assoc']['worsened']} "
        f"proxySlotImproved={verdicts['proxySlot']['improved']} proxySlotSame={verdicts['proxySlot']['same']} proxySlotWorsened={verdicts['proxySlot']['worsened']} "
        f"lexSlotImproved={verdicts['lexSlot']['improved']} lexSlotSame={verdicts['lexSlot']['same']} lexSlotWorsened={verdicts['lexSlot']['worsened']} "
        f"autoSlotImproved={verdicts['autoSlot']['improved']} autoSlotSame={verdicts['autoSlot']['same']} autoSlotWorsened={verdicts['autoSlot']['worsened']} "
        f"prunedAutoSlotImproved={verdicts['prunedAutoSlot']['improved']} prunedAutoSlotSame={verdicts['prunedAutoSlot']['same']} prunedAutoSlotWorsened={verdicts['prunedAutoSlot']['worsened']} "
        f"supportAutoSlotImproved={verdicts['supportAutoSlot']['improved']} supportAutoSlotSame={verdicts['supportAutoSlot']['same']} supportAutoSlotWorsened={verdicts['supportAutoSlot']['worsened']} "
        f"triggerSupportSlotImproved={verdicts['triggerSupportSlot']['improved']} triggerSupportSlotSame={verdicts['triggerSupportSlot']['same']} triggerSupportSlotWorsened={verdicts['triggerSupportSlot']['worsened']} "
        f"cohortSlotImproved={verdicts['cohortSlot']['improved']} cohortSlotSame={verdicts['cohortSlot']['same']} cohortSlotWorsened={verdicts['cohortSlot']['worsened']} "
        f"roleFrameSlotImproved={verdicts['roleFrameSlot']['improved']} roleFrameSlotSame={verdicts['roleFrameSlot']['same']} roleFrameSlotWorsened={verdicts['roleFrameSlot']['worsened']} "
        f"autoRoleFrameSlotImproved={verdicts['autoRoleFrameSlot']['improved']} autoRoleFrameSlotSame={verdicts['autoRoleFrameSlot']['same']} autoRoleFrameSlotWorsened={verdicts['autoRoleFrameSlot']['worsened']} "
        f"purifiedMeaningLearnerImproved={verdicts['purifiedMeaningLearner']['improved']} purifiedMeaningLearnerSame={verdicts['purifiedMeaningLearner']['same']} purifiedMeaningLearnerWorsened={verdicts['purifiedMeaningLearner']['worsened']} "
        f"exactRubric={rubricTotals['exact']} fireRubric={rubricTotals['fire']} "
        f"assocRubric={rubricTotals['assoc']} proxySlotRubric={rubricTotals['proxySlot']} "
        f"lexSlotRubric={rubricTotals['lexSlot']} autoSlotRubric={rubricTotals['autoSlot']} "
        f"prunedAutoSlotRubric={rubricTotals['prunedAutoSlot']} supportAutoSlotRubric={rubricTotals['supportAutoSlot']} "
        f"triggerSupportSlotRubric={rubricTotals['triggerSupportSlot']} cohortSlotRubric={rubricTotals['cohortSlot']} "
        f"roleFrameSlotRubric={rubricTotals['roleFrameSlot']} "
        f"autoRoleFrameSlotRubric={rubricTotals['autoRoleFrameSlot']} "
        f"purifiedMeaningLearnerRubric={rubricTotals['purifiedMeaningLearner']} "
        f"fireRubricImproved={rubricVerdicts['fire']['improved']} fireRubricSame={rubricVerdicts['fire']['same']} fireRubricWorsened={rubricVerdicts['fire']['worsened']} "
        f"assocRubricImproved={rubricVerdicts['assoc']['improved']} assocRubricSame={rubricVerdicts['assoc']['same']} assocRubricWorsened={rubricVerdicts['assoc']['worsened']} "
        f"proxySlotRubricImproved={rubricVerdicts['proxySlot']['improved']} proxySlotRubricSame={rubricVerdicts['proxySlot']['same']} proxySlotRubricWorsened={rubricVerdicts['proxySlot']['worsened']} "
        f"lexSlotRubricImproved={rubricVerdicts['lexSlot']['improved']} lexSlotRubricSame={rubricVerdicts['lexSlot']['same']} lexSlotRubricWorsened={rubricVerdicts['lexSlot']['worsened']} "
        f"autoSlotRubricImproved={rubricVerdicts['autoSlot']['improved']} autoSlotRubricSame={rubricVerdicts['autoSlot']['same']} autoSlotRubricWorsened={rubricVerdicts['autoSlot']['worsened']} "
        f"prunedAutoSlotRubricImproved={rubricVerdicts['prunedAutoSlot']['improved']} prunedAutoSlotRubricSame={rubricVerdicts['prunedAutoSlot']['same']} prunedAutoSlotRubricWorsened={rubricVerdicts['prunedAutoSlot']['worsened']} "
        f"supportAutoSlotRubricImproved={rubricVerdicts['supportAutoSlot']['improved']} supportAutoSlotRubricSame={rubricVerdicts['supportAutoSlot']['same']} supportAutoSlotRubricWorsened={rubricVerdicts['supportAutoSlot']['worsened']} "
        f"triggerSupportSlotRubricImproved={rubricVerdicts['triggerSupportSlot']['improved']} triggerSupportSlotRubricSame={rubricVerdicts['triggerSupportSlot']['same']} triggerSupportSlotRubricWorsened={rubricVerdicts['triggerSupportSlot']['worsened']} "
        f"cohortSlotRubricImproved={rubricVerdicts['cohortSlot']['improved']} cohortSlotRubricSame={rubricVerdicts['cohortSlot']['same']} cohortSlotRubricWorsened={rubricVerdicts['cohortSlot']['worsened']} "
        f"roleFrameSlotRubricImproved={rubricVerdicts['roleFrameSlot']['improved']} roleFrameSlotRubricSame={rubricVerdicts['roleFrameSlot']['same']} roleFrameSlotRubricWorsened={rubricVerdicts['roleFrameSlot']['worsened']} "
        f"autoRoleFrameSlotRubricImproved={rubricVerdicts['autoRoleFrameSlot']['improved']} autoRoleFrameSlotRubricSame={rubricVerdicts['autoRoleFrameSlot']['same']} autoRoleFrameSlotRubricWorsened={rubricVerdicts['autoRoleFrameSlot']['worsened']} "
        f"purifiedMeaningLearnerRubricImproved={rubricVerdicts['purifiedMeaningLearner']['improved']} purifiedMeaningLearnerRubricSame={rubricVerdicts['purifiedMeaningLearner']['same']} purifiedMeaningLearnerRubricWorsened={rubricVerdicts['purifiedMeaningLearner']['worsened']} "
        f"exactAvgMs={sum(latencies['exact']) / len(latencies['exact']):.2f} "
        f"fireAvgMs={sum(latencies['fire']) / len(latencies['fire']):.2f} "
        f"assocAvgMs={sum(latencies['assoc']) / len(latencies['assoc']):.2f} "
        f"proxySlotAvgMs={sum(latencies['proxySlot']) / len(latencies['proxySlot']):.2f} "
        f"lexSlotAvgMs={sum(latencies['lexSlot']) / len(latencies['lexSlot']):.2f} "
        f"autoSlotAvgMs={sum(latencies['autoSlot']) / len(latencies['autoSlot']):.2f} "
        f"prunedAutoSlotAvgMs={sum(latencies['prunedAutoSlot']) / len(latencies['prunedAutoSlot']):.2f} "
        f"supportAutoSlotAvgMs={sum(latencies['supportAutoSlot']) / len(latencies['supportAutoSlot']):.2f} "
        f"triggerSupportSlotAvgMs={sum(latencies['triggerSupportSlot']) / len(latencies['triggerSupportSlot']):.2f} "
        f"cohortSlotAvgMs={sum(latencies['cohortSlot']) / len(latencies['cohortSlot']):.2f} "
        f"roleFrameSlotAvgMs={sum(latencies['roleFrameSlot']) / len(latencies['roleFrameSlot']):.2f} "
        f"autoRoleFrameSlotAvgMs={sum(latencies['autoRoleFrameSlot']) / len(latencies['autoRoleFrameSlot']):.2f} "
        f"purifiedMeaningLearnerAvgMs={sum(latencies['purifiedMeaningLearner']) / len(latencies['purifiedMeaningLearner']):.2f} "
        f"fireDuplicateTop5={duplicates['fire']} fireTableTop5={tables['fire']} "
        f"assocDuplicateTop5={duplicates['assoc']} assocTableTop5={tables['assoc']} "
        f"proxySlotDuplicateTop5={duplicates['proxySlot']} proxySlotTableTop5={tables['proxySlot']} "
        f"lexSlotDuplicateTop5={duplicates['lexSlot']} lexSlotTableTop5={tables['lexSlot']} "
        f"autoSlotDuplicateTop5={duplicates['autoSlot']} autoSlotTableTop5={tables['autoSlot']} "
        f"prunedAutoSlotDuplicateTop5={duplicates['prunedAutoSlot']} prunedAutoSlotTableTop5={tables['prunedAutoSlot']} "
        f"supportAutoSlotDuplicateTop5={duplicates['supportAutoSlot']} supportAutoSlotTableTop5={tables['supportAutoSlot']} "
        f"triggerSupportSlotDuplicateTop5={duplicates['triggerSupportSlot']} triggerSupportSlotTableTop5={tables['triggerSupportSlot']} "
        f"cohortSlotDuplicateTop5={duplicates['cohortSlot']} cohortSlotTableTop5={tables['cohortSlot']} "
        f"roleFrameSlotDuplicateTop5={duplicates['roleFrameSlot']} roleFrameSlotTableTop5={tables['roleFrameSlot']} "
        f"autoRoleFrameSlotDuplicateTop5={duplicates['autoRoleFrameSlot']} autoRoleFrameSlotTableTop5={tables['autoRoleFrameSlot']} "
        f"purifiedMeaningLearnerDuplicateTop5={duplicates['purifiedMeaningLearner']} purifiedMeaningLearnerTableTop5={tables['purifiedMeaningLearner']} "
        f"meaningLearnerRubric={rubricTotals['autoRoleFrameSlot']} "
        f"meaningLearnerRubricImproved={rubricVerdicts['autoRoleFrameSlot']['improved']} "
        f"meaningLearnerRubricSame={rubricVerdicts['autoRoleFrameSlot']['same']} "
        f"meaningLearnerRubricWorsened={rubricVerdicts['autoRoleFrameSlot']['worsened']} "
        f"purifiedRubric={rubricTotals['purifiedMeaningLearner']} "
        f"purifiedRubricImproved={rubricVerdicts['purifiedMeaningLearner']['improved']} "
        f"purifiedRubricSame={rubricVerdicts['purifiedMeaningLearner']['same']} "
        f"purifiedRubricWorsened={rubricVerdicts['purifiedMeaningLearner']['worsened']} "
        f"learnedRoleClusters={learnedRoleClusters} learnedRoleTerms={learnedRoleTerms} learnedFormLikeTerms={learnedFormLikeTerms} "
        f"purifiedRoleClusters={purifiedRoleClusters} purifiedRoleTerms={purifiedRoleTerms} purifiedFormLikeTerms={purifiedFormLikeTerms} "
        f"answerFrames={answerFrames} fullAnswerFrames={fullAnswerFrames} framedTargets={framedTargets} "
        f"framedRelations={framedRelations} frameCompletenessAvg={frameCompletenessTotal / max(answerFrames, 1):.2f} "
        f"frameConfidenceAvg={frameConfidenceSum / max(answerFrames, 1):.2f} "
        f"frameEvidenceRubricAvg={frameEvidenceRubricTotal / max(answerFrames, 1):.2f} "
        f"frameStrongHitAvg={frameStrongHitTotal / max(answerFrames, 1):.2f}"
    )


def main() -> None:
    print("=" * 88)
    print("Horizon Meaning Learner v23")
    print("=" * 88)
    print(
        f"[config] maxUnits={MAX_UNITS:,} buckets={HORIZON_BUCKETS:,} window={WINDOW} "
        f"semWeight={SEMANTIC_WEIGHT:g} fireCandidates={FIRE_RERANK_CANDIDATES:,} "
        f"fireTie={FIRE_TIE_BREAK_WEIGHT:g} tablePenalty={TABLE_PENALTY:g} "
        f"relSpan={RELATION_SPAN_LIMIT} pairWindow={PAIR_INDEX_WINDOW} pairMaxUnits={PAIR_INDEX_MAX_UNITS:,} "
        f"assocWindow={ASSOC_WINDOW} assocTop={ASSOC_TOP_NEIGHBORS} assocWeight={ASSOC_WEIGHT:g} "
        f"slotWeight={SLOT_RERANK_WEIGHT:g} autoSlotExpand={AUTO_SLOT_EXPAND_PER_SEED} "
        f"autoSlotFloor={AUTO_SLOT_SCORE_FLOOR:g} prunedDelta={PRUNED_AUTO_DELTA_WEIGHT:g} "
        f"prunedMinSeed={PRUNED_AUTO_MIN_SEED_HITS} supportOverlap={SUPPORT_AUTO_MIN_OVERLAP} "
        f"supportPrecision={SUPPORT_AUTO_MIN_PRECISION:g} cohortTop={COHORT_SLOT_TOP_UNITS} "
        f"cohortOverlap={COHORT_SLOT_MIN_OVERLAP} cohortPrecision={COHORT_SLOT_MIN_PRECISION:g} "
        f"cohortWeight={COHORT_SLOT_WEIGHT_SCALE:g} roleFrameTop={ROLE_FRAME_COHORT_TOP_UNITS} "
        f"roleFrameAssocFloor={ROLE_FRAME_ASSOC_SCORE_FLOOR:g} roleFrameOverlap={ROLE_FRAME_MIN_OVERLAP} "
        f"roleFramePrecision={ROLE_FRAME_MIN_PRECISION:g} roleFrameWeight={ROLE_FRAME_WEIGHT_SCALE:g} "
        f"roleFrameNegative={ROLE_FRAME_NEGATIVE_WEIGHT:g} "
        f"autoRoleFrameAssocFloor={AUTO_ROLE_FRAME_ASSOC_SCORE_FLOOR:g} "
        f"autoRoleFrameFireWeight={AUTO_ROLE_FRAME_FIRE_WEIGHT:g} "
        f"autoRoleFrameOverlap={AUTO_ROLE_FRAME_MIN_OVERLAP} "
        f"autoRoleFramePrecision={AUTO_ROLE_FRAME_MIN_PRECISION:g} "
        f"autoRoleFrameWeight={AUTO_ROLE_FRAME_WEIGHT_SCALE:g} "
        f"purifiedRoleFrameWeight={PURIFIED_ROLE_FRAME_WEIGHT_SCALE:g} "
        f"purifiedMinAnchorOverlap={PURIFIED_ROLE_MIN_ANCHOR_OVERLAP} "
        f"purifiedMinRelationOverlap={PURIFIED_ROLE_MIN_RELATION_OVERLAP} "
        f"diversityTextPenalty={DIVERSITY_TEXT_PENALTY:g} "
        f"answerFrameTargetLimit={ANSWER_FRAME_TARGET_LIMIT} "
        f"answerFrameMinTargetScore={ANSWER_FRAME_MIN_TARGET_SCORE:g} "
        f"answerFrameMinRelationScore={ANSWER_FRAME_MIN_RELATION_SCORE:g}"
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
