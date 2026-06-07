"""비용상세 정규화 단일 SSOT (pure, L0 core).

목적:
    손익계산서 비용 상세(판관비 명세·비용 성격별)의 정본 데이터(뼈대, 판관비 상세
    후보, 비용 성격별 카테고리, source lane 계약, row role, 출력 스키마, exact
    label 맵, 누수 term 리스트)를 *한 모듈*로 통합한다. finance 와 결합하기 위한
    reconciliation 타깃(snakeId)·band·by-nature 타깃 해소·운영 lifecycle 까지 박는다.

원칙:
    1. 이 모듈은 **순수**다. polars/dartlab import 0, I/O 0 (L0 core).
    2. 정본은 여기 하나뿐이다. panel/builder 는 이 모듈을 import 해서 쓰고 로컬 사본을
       두지 않는다 (정공법 SSOT).
    3. exact label 맵 숫자(WiseReport unique 47 / natural unique 124)는 동결 기준.
       신규 라벨은 quarantine lifecycle 을 거쳐 승격한다.

레이어 매핑:
    - 이 모듈                  → ``core/accounts/expenseDetail.py`` (L0, 순수)
    - panel 추출               → ``providers/dart/panel/expenseDetail.py`` (L1, finance import 0)
    - finance 합성             → ``providers/dart/builder/expenseDetailBuilder.py`` (composition)

self-test (assertSsot):
    statement row 20, sga detail 후보 8, 비용 카테고리 16, WiseReport exact unique 47,
    natural exact unique 124, cross collision 0, source lane 6, row role 7,
    output schema 23(+reconciledTarget), reconciliation 타깃 4.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any


# ───────────────────────── dataclasses ─────────────────────────
@dataclass(frozen=True)
class WiseReportTargetRow:
    """WiseReport 손익계산서 뼈대 행 — 키·라벨·순서·계층·매퍼 카테고리 계약."""

    key: str
    label: str
    order: int
    level: int
    rowKind: str
    parentKey: str | None
    mapperCategories: tuple[str, ...]
    aliases: tuple[str, ...]
    note: str = ""


@dataclass(frozen=True)
class ExpenseCategory:
    """비용의 성격별 표준 카테고리 — 키·라벨·alias·소속 statement 버킷."""

    key: str
    label: str
    order: int
    aliases: tuple[str, ...]
    statementBuckets: tuple[str, ...]


@dataclass(frozen=True)
class SourceLaneContract:
    """비용상세 source lane 계약 — lane·canonical 등급·reconcile 타깃·신뢰도·게이트."""

    sourceLane: str
    sourceClass: str
    canonicalStatus: str
    directTargets: tuple[str, ...]
    evidenceTargets: tuple[str, ...]
    confidence: str
    requiredGate: tuple[str, ...]
    note: str


@dataclass(frozen=True)
class RowRoleContract:
    """표 행 role 계약 — detail/total/functionalTotal/header 등 role 과 canonical 처리 규칙."""

    rowRole: str
    canonicalStatus: str
    note: str


@dataclass(frozen=True)
class OutputColumnContract:
    """출력 long DataFrame 컬럼 계약 — 이름·dtype·필수 여부·설명."""

    column: str
    dtype: str
    required: bool
    note: str


@dataclass(frozen=True)
class ReconciliationTarget:
    """finance IS reconcile 타깃 — statementKey ↔ snakeId ↔ 계정명 매핑."""

    statementKey: str
    snakeId: str
    accountNm: str
    note: str


@dataclass(frozen=True)
class ReconciliationBand:
    """상대오차 band → reconciliationStatus(matched/near/partial/mismatch) 매핑 계약."""

    status: str
    maxRelDiff: float | None
    note: str


@dataclass(frozen=True)
class QuarantineStage:
    """quarantine → promote lifecycle 단계 — 단계·이름·담당·액션·게이트."""

    stage: int
    name: str
    owner: str
    action: str
    gate: str


@dataclass(frozen=True)
class MainIntegrationStep:
    """본진 이관 단계 — step·타깃 파일·담당 레이어·액션·게이트."""

    step: int
    target: str
    ownerLayer: str
    action: str
    gate: str


# ──────────────────── 손익계산서 뼈대(계정이미지 SSOT) ────────────────────
WISE_REPORT_STATEMENT_ROWS: tuple[WiseReportTargetRow, ...] = (
    WiseReportTargetRow(
        "sales", "수익(매출액)", 10, 0, "statement", None, (), ("수익(매출액)", "매출액", "수익", "영업수익")
    ),
    WiseReportTargetRow("costOfSales", "매출원가", 20, 0, "functionalCost", None, (), ("매출원가",)),
    WiseReportTargetRow("grossProfit", "매출총이익", 30, 0, "subtotal", None, (), ("매출총이익",)),
    WiseReportTargetRow(
        "sellingGeneralAdministrativeExpenses",
        "판매비와관리비",
        40,
        0,
        "functionalCost",
        None,
        (),
        ("판매비와관리비", "판매비 및 관리비", "판매관리비", "판관비"),
    ),
    WiseReportTargetRow(
        "operatingProfit",
        "영업이익(손실)",
        50,
        0,
        "subtotal",
        None,
        (),
        ("영업이익(손실)", "영업이익", "영업손실", "영업손익"),
    ),
    WiseReportTargetRow("otherIncome", "기타수익", 60, 0, "nonOperating", None, (), ("기타수익", "기타이익")),
    WiseReportTargetRow("otherExpenses", "기타비용", 70, 0, "nonOperating", None, (), ("기타비용", "기타영업비용")),
    WiseReportTargetRow(
        "equityMethodProfit",
        "지분법이익",
        80,
        0,
        "nonOperating",
        None,
        (),
        ("지분법이익", "지분법손익", "관계기업", "공동기업"),
    ),
    WiseReportTargetRow("financeIncome", "금융수익", 90, 0, "nonOperating", None, (), ("금융수익", "금융이익")),
    WiseReportTargetRow(
        "profitBeforeTax",
        "법인세비용차감전순이익(손실)",
        100,
        0,
        "subtotal",
        None,
        (),
        ("법인세비용차감전순이익(손실)", "법인세비용차감전순이익", "법인세차감전순이익", "세전이익"),
    ),
    WiseReportTargetRow("incomeTaxExpense", "법인세비용", 110, 0, "tax", None, (), ("법인세비용", "법인세")),
    WiseReportTargetRow(
        "continuingOperationsProfit",
        "계속영업이익(손실)",
        120,
        0,
        "subtotal",
        None,
        (),
        ("계속영업이익(손실)", "계속영업이익", "계속영업손실"),
    ),
    WiseReportTargetRow(
        "basicEps",
        "기본주당이익(손실)",
        130,
        0,
        "perShare",
        None,
        (),
        ("기본주당이익(손실)", "기본주당이익", "기본주당손실"),
    ),
    WiseReportTargetRow(
        "netIncome",
        "당기순이익(손실)",
        140,
        0,
        "subtotal",
        None,
        (),
        ("당기순이익(손실)", "당기순이익", "당기순손실", "분기순이익", "반기순이익"),
    ),
    WiseReportTargetRow(
        "dilutedEps",
        "희석주당이익(손실)",
        150,
        0,
        "perShare",
        None,
        (),
        ("희석주당이익(손실)", "희석주당이익", "희석주당손실"),
    ),
    WiseReportTargetRow("financeCosts", "금융비용", 160, 0, "nonOperating", None, (), ("금융비용", "금융원가")),
    WiseReportTargetRow(
        "controllingInterestNetIncome",
        "지배기업의 소유주에게 귀속되는 당기순이익(손실)",
        170,
        0,
        "attribution",
        None,
        (),
        ("지배기업의소유주에게귀속되는당기순이익", "지배기업", "지배주주"),
    ),
    WiseReportTargetRow(
        "nonControllingInterestNetIncome",
        "비지배지분에 귀속되는 당기순이익(손실)",
        180,
        0,
        "attribution",
        None,
        (),
        ("비지배지분에귀속되는당기순이익", "비지배", "비지배주주"),
    ),
    WiseReportTargetRow(
        "basicEpsWon", "기본주당이익(손실) (단위:원)", 190, 0, "perShare", None, (), ("기본주당이익(손실)(단위:원)",)
    ),
    WiseReportTargetRow(
        "dilutedEpsWon", "희석주당이익(손실) (단위:원)", 200, 0, "perShare", None, (), ("희석주당이익(손실)(단위:원)",)
    ),
)


SGA_DETAIL_CANDIDATE_ROWS: tuple[WiseReportTargetRow, ...] = (
    WiseReportTargetRow(
        "personnelExpense",
        "인건비",
        41,
        1,
        "expenseDetail",
        "sellingGeneralAdministrativeExpenses",
        ("employeeBenefits",),
        ("인건비", "종업원급여", "급여", "퇴직급여", "복리후생"),
    ),
    WiseReportTargetRow(
        "depreciationAmortizationExpense",
        "유무형자산상각비",
        42,
        1,
        "expenseDetail",
        "sellingGeneralAdministrativeExpenses",
        ("depreciationAmortization",),
        ("유무형자산상각비", "감가상각비", "무형자산상각비", "사용권자산상각비"),
    ),
    WiseReportTargetRow(
        "researchDevelopmentExpense",
        "연구개발비",
        43,
        1,
        "expenseDetail",
        "sellingGeneralAdministrativeExpenses",
        ("researchDevelopment",),
        ("연구개발비", "연구개발", "경상연구개발비", "경상개발비"),
    ),
    WiseReportTargetRow(
        "advertisingExpense",
        "광고선전비",
        44,
        1,
        "expenseDetail",
        "sellingGeneralAdministrativeExpenses",
        ("advertisingPromotion",),
        ("광고선전비", "광고선전", "광고비"),
    ),
    WiseReportTargetRow(
        "sellingExpense",
        "판매비",
        45,
        1,
        "expenseDetail",
        "sellingGeneralAdministrativeExpenses",
        (),
        ("판매비",),
        "WiseReport label 이 판매비로 직접 잡힐 때만 승격한다.",
    ),
    WiseReportTargetRow(
        "administrativeExpense",
        "관리비",
        46,
        1,
        "expenseDetail",
        "sellingGeneralAdministrativeExpenses",
        (),
        ("관리비",),
        "WiseReport label 이 관리비로 직접 잡힐 때만 승격한다.",
    ),
    WiseReportTargetRow(
        "otherCostLikeExpense",
        "기타원가성비용",
        47,
        1,
        "expenseDetail",
        "sellingGeneralAdministrativeExpenses",
        (),
        ("기타원가성비용",),
        "WiseReport label 이 기타원가성비용으로 직접 잡힐 때만 승격한다.",
    ),
    WiseReportTargetRow(
        "otherSgaExpense",
        "기타",
        48,
        1,
        "expenseDetail",
        "sellingGeneralAdministrativeExpenses",
        ("otherOperatingExpense",),
        ("기타",),
        "WiseReport 의 판관비 하위 기타. exact-only 로만 통과시킨다.",
    ),
)


# ──────────────────── 비용 성격별 카테고리(expensesByNature) ────────────────────
EXPENSE_CATEGORIES: tuple[ExpenseCategory, ...] = (
    ExpenseCategory(
        "materialsPurchased",
        "원재료/상품매입",
        10,
        ("원재료", "원부재료", "재료비", "상품매입", "소모품사용", "상품의매입"),
        ("costOfSales", "operatingExpenseBridge"),
    ),
    ExpenseCategory(
        "inventoryChange",
        "재고자산변동",
        20,
        ("재고자산의변동", "재고자산변동", "제품및재공품", "제품과재공품", "제품재공품"),
        ("costOfSales", "operatingExpenseBridge"),
    ),
    ExpenseCategory(
        "employeeBenefits",
        "종업원급여",
        30,
        ("종업원급여", "종업원급", "인건비", "급여", "퇴직급여", "복리후생", "주식보상"),
        ("costOfSales", "sellingGeneralAdministrativeExpenses", "operatingExpenseBridge"),
    ),
    ExpenseCategory(
        "depreciationAmortization",
        "감가상각/무형자산상각",
        40,
        ("감가상각", "상각비", "무형자산상각", "사용권자산상각"),
        ("costOfSales", "sellingGeneralAdministrativeExpenses", "operatingExpenseBridge"),
    ),
    ExpenseCategory(
        "outsourcingServices",
        "외주/용역",
        50,
        ("외주", "용역비", "외주가공", "외주용역"),
        ("costOfSales", "sellingGeneralAdministrativeExpenses", "operatingExpenseBridge"),
    ),
    ExpenseCategory(
        "commissionsFees",
        "지급수수료",
        60,
        ("지급수수료", "수수료비용", "판매수수료", "수수료"),
        ("sellingGeneralAdministrativeExpenses", "operatingExpenseBridge"),
    ),
    ExpenseCategory(
        "advertisingPromotion",
        "광고선전/판매촉진",
        70,
        ("광고선전", "광고비", "판매촉진", "마케팅"),
        ("sellingGeneralAdministrativeExpenses", "operatingExpenseBridge"),
    ),
    ExpenseCategory(
        "freightLogistics",
        "운반/물류",
        80,
        ("운반", "운송", "물류", "배송", "포장비"),
        ("costOfSales", "sellingGeneralAdministrativeExpenses", "operatingExpenseBridge"),
    ),
    ExpenseCategory(
        "rentLease",
        "임차/리스",
        90,
        ("임차료", "지급임차료", "리스료", "사용권자산"),
        ("sellingGeneralAdministrativeExpenses", "operatingExpenseBridge"),
    ),
    ExpenseCategory(
        "taxesDues",
        "세금과공과",
        100,
        ("세금과공과", "세금공과", "공과금"),
        ("sellingGeneralAdministrativeExpenses", "operatingExpenseBridge"),
    ),
    ExpenseCategory(
        "researchDevelopment",
        "연구개발",
        110,
        ("연구개발", "경상연구", "개발비"),
        ("costOfSales", "sellingGeneralAdministrativeExpenses", "operatingExpenseBridge"),
    ),
    ExpenseCategory(
        "badDebtImpairment",
        "대손상각/손상",
        120,
        ("대손상각", "손상차손", "손실충당금", "대손충당"),
        ("sellingGeneralAdministrativeExpenses", "operatingExpenseBridge"),
    ),
    ExpenseCategory(
        "utilities",
        "수도광열/전력",
        130,
        ("수도광열", "전력", "동력", "가스수도", "통신비"),
        ("costOfSales", "sellingGeneralAdministrativeExpenses", "operatingExpenseBridge"),
    ),
    ExpenseCategory(
        "insurance",
        "보험료",
        140,
        ("보험료",),
        ("sellingGeneralAdministrativeExpenses", "operatingExpenseBridge"),
    ),
    ExpenseCategory(
        "travelEntertainment",
        "여비교통/접대",
        150,
        ("여비교통", "접대", "회의비"),
        ("sellingGeneralAdministrativeExpenses", "operatingExpenseBridge"),
    ),
    ExpenseCategory(
        "otherOperatingExpense",
        "기타",
        900,
        ("기타비용", "기타영업비용"),
        ("costOfSales", "sellingGeneralAdministrativeExpenses", "operatingExpenseBridge"),
    ),
)


# ──────────────────── 주석 source title 패턴 ────────────────────
NOTE_SOURCE_PATTERNS: dict[str, tuple[str, ...]] = {
    "expensesByNature": (
        "비용의 성격별 분류",
        "비용의성격별분류",
        "성격별 비용",
        "성격별비용",
        "영업비용의 성격",
        "영업비용의성격",
        "성격별 분류",
    ),
    "sgaDetail": (
        "판매비와관리비",
        "판매비 및 관리비",
        "판매관리비",
        "판관비",
        "일반영업비용",
    ),
    "costOfSalesDetail": (
        "매출원가",
        "제조원가",
        "매출원가 및 판매비와관리비",
        "매출원가와 판매비와관리비",
    ),
    "operatingExpenseBridge": (
        "영업비용",
        "총영업비용",
        "영업수익 및 영업비용",
        "영업수익, 영업비용",
    ),
    "existingDartLabTopic": (
        "costByNature",
        "NT_D834300",
        "NT_D834305",
        "NT_D834310",
        "NT_D834315",
    ),
}


# ──────────────────── exact label 맵 (동결 기준 WiseReport 47 / natural 124) ────────────────────
WISE_REPORT_EXACT_LABEL_MAP: dict[str, tuple[str, ...]] = {
    "personnelExpense": (
        "인건비",
        "종업원급여",
        "종업원급여비용",
        "급여",
        "임금",
        "상여",
        "상여금",
        "급여및상여",
        "급여 및 상여 등",
        "급여 및 수당",
        "급여및수당",
        "퇴직급여",
        "퇴직급여비용",
        "복리후생",
        "복리후생비",
        "주식보상",
        "주식보상비용",
        "기타장기종업원급여",
    ),
    "depreciationAmortizationExpense": (
        "유무형자산상각비",
        "유무형자산상각",
        "감가상각비",
        "감가상각비 및 무형자산상각비",
        "감가상각비, 무형자산상각비",
        "감가상각비와 무형자산상각비",
        "감가상각 및 무형자산상각비",
        "감가상각비 및 무형자산 상각",
        "감가상각비 및 무형자산 상각비",
        "감가상각",
        "무형자산상각비",
        "무형자산상각",
        "사용권자산상각비",
        "사용권자산상각",
    ),
    "researchDevelopmentExpense": (
        "연구개발비",
        "연구개발",
        "경상연구개발비",
        "경상연구개발",
        "경상개발비",
        "시험연구비",
        "연구비",
    ),
    "advertisingExpense": (
        "광고선전비",
        "광고선전",
        "광고비",
    ),
    "sellingExpense": ("판매비",),
    "administrativeExpense": (
        "관리비",
        "일반관리비",
    ),
    "otherCostLikeExpense": ("기타원가성비용",),
    "otherSgaExpense": (
        "기타",
        "기타판매관리비",
        "기타판관비",
    ),
}


NATURAL_EXACT_LABEL_MAP: dict[str, tuple[str, ...]] = {
    "materialsPurchased": (
        "원재료",
        "원재료비",
        "재료비",
        "원부재료",
        "상품매입",
        "상품매입액",
        "상품의매입",
        "원재료등의사용액및상품매입액등",
        "원재료및상품매입액",
        "원재료와상품매입액",
        "원재료및저장품",
        "원재료및소모품사용",
        "원재료 및 상품 사용액",
        "원재료 및 상품 등의 사용액",
        "원재료의 사용 및 상품의 매입",
        "원재료와 소모품의 사용액",
        "원재료와 소모품의 사용",
        "원재료, 저장품 및 소모품 사용",
    ),
    "inventoryChange": (
        "재고자산의변동",
        "재고자산변동",
        "제품및재공품등의변동",
        "제품및재공품의변동",
        "제품과재공품의변동",
        "제품반제품및재공품의변동",
        "제품반제품상품재공품의변동",
        "제품재공품및상품의변동",
        "제품, 반제품, 상품 및 재공품의 변동",
        "제품, 상품 및 반제품의 변동",
        "제품과 재공품의 감소(증가)",
        "제품과 반제품의 변동",
    ),
    "outsourcingServices": (
        "외주가공비",
        "외주가공",
        "외주비",
        "외주용역비",
        "외주용역",
        "용역비",
        "임가공비",
        "서비스비",
        "기술용역비",
    ),
    "commissionsFees": (
        "지급수수료",
        "수수료비용",
        "판매수수료",
        "카드수수료",
        "중개수수료",
        "제수수료",
        "수수료",
    ),
    "advertisingPromotion": (
        "판매촉진비",
        "판매촉진",
        "마케팅비",
        "판매장려금",
        "협력사마케팅비",
    ),
    "freightLogistics": (
        "운반비",
        "운송비",
        "운반보관료",
        "운반보관비",
        "물류비",
        "배송비",
        "포장비",
        "제품수송비",
        "판매물류비",
    ),
    "rentLease": (
        "임차료",
        "지급임차료",
        "리스료",
        "리스비용",
        "렌탈료",
        "리스료 및 임차료",
        "운용리스료 및 임차료",
        "임차료 및 사용료",
        "운용리스료",
    ),
    "taxesDues": (
        "세금과공과",
        "세금공과",
        "제세공과",
        "제세공과금",
        "공과금",
    ),
    "badDebtImpairment": (
        "대손상각비",
        "대손상각",
        "대손충당금전입",
        "손실충당금전입",
        "손상차손",
        "매출채권손상차손",
        "대손상각비(환입)",
        "대손상각비(손실충당금환입)",
    ),
    "utilities": (
        "수도광열비",
        "수도광열",
        "전력비",
        "동력비",
        "가스수도료",
        "통신비",
        "유틸리티비",
        "동력 및 수도광열비",
        "동력용수비",
    ),
    "insurance": ("보험료",),
    "travelEntertainment": (
        "여비교통비",
        "여비교통",
        "출장비",
        "접대비",
        "회의비",
        "교통비",
    ),
    "otherOperatingExpense": (
        "소모품비",
        "수선비",
        "소모수선비",
        "교육훈련비",
        "품질관리비",
        "판매보증비",
        "판매보증충당부채전입",
        "판매보증충당부채전입액",
        "시험비",
        "견본비",
        "견본품비",
        "도서인쇄비",
        "차량유지비",
        "판매수리비",
        "수선유지비",
        "정보처리비",
        "전산비",
        "사무관리비",
        "사무용품비",
        "시험검사비",
        "전산운영비",
        "잡비",
        "기타비용",
        "기타영업비용",
        "기타경비",
        "기타의 경비",
    ),
}


# ──────────────────── row role 분류용 term 리스트 ────────────────────
TOTAL_TERMS: tuple[str, ...] = ("합계", "합 계", "총계", "소계", "계", "비용의합계", "총영업비용")
FUNCTIONAL_TOTAL_TERMS: tuple[str, ...] = (
    "매출원가",
    "판매비와관리비",
    "판매비및관리비",
    "판매관리비",
    "판관비",
    "영업비용",
    "영업수익",
    "매출액",
    "영업이익",
    "성격별비용",  # by-nature 노트 자체 총계 행("성격별 비용") — detail 더블카운트 방지 + noteTotal 앵커.
)
HEADER_TERMS: tuple[str, ...] = ("구분", "구 분", "항목", "과목", "계정과목", "내역", "단위")
REVENUE_LEAKAGE_TERMS: tuple[str, ...] = (
    "수수료수익",
    "수수료수입",
    "보험수익",
    "보험금수익",
    "재보험수익",
    "이자수익",
    "배당금수익",
    "임대수익",
)
BALANCE_SHEET_LEAKAGE_TERMS: tuple[str, ...] = (
    "확정급여채무",
    "퇴직급여채무",
    "퇴직급여부채",
    "순확정급여부채",
    "차량운반구",
    "미지급",
    "미수",
    "충당부채",
)


# ──────────────────── source lane 계약 ────────────────────
SOURCE_LANE_CONTRACT: tuple[SourceLaneContract, ...] = (
    SourceLaneContract(
        "strictSgaDetail",
        "functionDetail",
        "canonicalCandidate",
        ("sellingGeneralAdministrativeExpenses",),
        (),
        "high",
        ("noteLineage", "rowRoleDetail", "exactWiseLabel", "periodAmount"),
        "판관비 주석 표의 하위 상세. WiseReport 판관비 상세 child row 로 직접 승격 가능한 1순위 lane.",
    ),
    SourceLaneContract(
        "strictCostOfSalesDetail",
        "functionDetail",
        "canonicalCandidate",
        ("costOfSales",),
        (),
        "high",
        ("noteLineage", "rowRoleDetail", "periodAmount"),
        "매출원가 주석 표의 하위 상세. 판관비 child row 에 흡수하지 않고 costOfSales 상세로만 둔다.",
    ),
    SourceLaneContract(
        "strictExpensesByNature",
        "natureBridge",
        "evidenceBridge",
        (),
        ("costOfSales", "sellingGeneralAdministrativeExpenses", "operatingProfit"),
        "mediumHigh",
        ("noteLineage", "rowRoleDetail", "naturalExactLabel", "periodAmount", "reconciliation"),
        "비용의 성격별 분류. 원재료/급여/상각/수수료 등 자연분류는 뽑되 기능별 row 로 임의 배분하지 않는다.",
    ),
    SourceLaneContract(
        "looseOperatingBridge",
        "looseBridge",
        "evidenceOnly",
        (),
        ("operatingProfit",),
        "low",
        ("noteLineage", "periodAmount"),
        "영업비용 bridge 는 false positive 가 크므로 정규 비용상세 승격 금지.",
    ),
    SourceLaneContract(
        "titleLoose",
        "looseTitle",
        "evidenceOnly",
        (),
        (),
        "low",
        ("manualReview",),
        "제목 hit 만으로 잡힌 row. source 후보 원장에는 남기되 canonical 생성 금지.",
    ),
    SourceLaneContract(
        "contentOnlyLoose",
        "looseContent",
        "blocked",
        (),
        (),
        "veryLow",
        ("manualReview",),
        "본문 단어 hit 만 있는 row. attempt04 precision proxy 가 낮아 본진 입력에서 차단한다.",
    ),
)
CANONICAL_SOURCE_LANES: tuple[str, ...] = ("strictExpensesByNature", "strictSgaDetail")
STRICT_SOURCE_LANES: tuple[str, ...] = (
    "strictExpensesByNature",
    "strictSgaDetail",
    "strictCostOfSalesDetail",
)


ROW_ROLE_CONTRACT: tuple[RowRoleContract, ...] = (
    RowRoleContract(
        "detail", "canonicalCandidate", "금액이 있는 개별 비용 행. source/label gate 통과 시 output row 생성."
    ),
    RowRoleContract(
        "total", "reconcileOnly", "합계/총계/소계. detail 로 승격하지 않고 reconciliation 기준으로만 사용."
    ),
    RowRoleContract(
        "functionalTotal", "reconcileOnly", "매출원가/판관비/영업비용 등 기능별 합계. detail 이 아니라 부모 row anchor."
    ),
    RowRoleContract("header", "blocked", "구분/항목/계정과목/단위 같은 표 헤더. 금액이 있어도 차단."),
    RowRoleContract("excludedRevenue", "blocked", "수수료수익/보험수익/이자수익 등 수익 계정 누수 차단."),
    RowRoleContract("excludedAsset", "blocked", "사용권자산/차량운반구/확정급여채무 등 BS/자산 누수 차단."),
    RowRoleContract("quarantine", "reviewOnly", "strict source 에 있으나 exact label 또는 role 이 확정되지 않은 후보."),
)


# ──────────────────── 출력 long statement 스키마 (22 컬럼) ────────────────────
OUTPUT_SCHEMA: tuple[OutputColumnContract, ...] = (
    OutputColumnContract("stockCode", "str", True, "종목코드."),
    OutputColumnContract("corpName", "str|null", False, "회사명. panel 에 없으면 null."),
    OutputColumnContract("period", "str", True, "보고기간. 최신 먼저 정렬."),
    OutputColumnContract("scope", "str", True, "consolidated/separate. finance CFS 결합 키."),
    OutputColumnContract(
        "statementRowKey",
        "str",
        True,
        "부모 손익계산서 row. costOfSales 또는 sellingGeneralAdministrativeExpenses 중심.",
    ),
    OutputColumnContract("statementRowLabel", "str", True, "부모 손익계산서 표시 라벨."),
    OutputColumnContract("detailKey", "str", True, "WiseReport child row 또는 natural category key."),
    OutputColumnContract("detailLabel", "str", True, "표시 라벨."),
    OutputColumnContract(
        "naturalExpenseKey", "str|null", False, "비용의 성격별 분류 key. 기능별 상세만 있으면 null 가능."
    ),
    OutputColumnContract("sourceLane", "str", True, "sourceMapper lane."),
    OutputColumnContract("sourceConfidence", "str", True, "high/mediumHigh/low/blocked."),
    OutputColumnContract("sourceChapter", "str|null", False, "chapter lineage."),
    OutputColumnContract("sourcePath", "str|null", False, "sectionPath/block lineage."),
    OutputColumnContract("sourceRef", "str", True, "panel row/block/table 위치를 재현할 수 있는 ref."),
    OutputColumnContract("labelOriginal", "str", True, "원본 행 라벨."),
    OutputColumnContract("labelNormalized", "str", True, "정규화 라벨."),
    OutputColumnContract("amount", "float|int", True, "금액."),
    OutputColumnContract("unit", "str|null", False, "원/천원/백만원 등 단위."),
    OutputColumnContract("rowRole", "str", True, "detail/total/functionalTotal/header/leakage/quarantine."),
    OutputColumnContract("mapperVersion", "str", True, "매퍼 버전."),
    OutputColumnContract("reconciliationStatus", "str", True, "matched/near/partial/unchecked/mismatch."),
    OutputColumnContract("canonicalStatus", "str", True, "canonicalCandidate/evidenceBridge/evidenceOnly/blocked."),
    OutputColumnContract(
        "reconciledTarget",
        "str|null",
        False,
        "by-nature 행이 정합한 IS 집계 — operatingExpense(매출원가+판관비) vs sga. sga 명세 행은 null.",
    ),
)


# ──────────────────── finance 결합 reconciliation ────────────────────
# finance buildAnnual IS snakeId SSOT — 손익계산서 기능별 합계 row 와 join 키.
RECONCILIATION_TARGETS: tuple[ReconciliationTarget, ...] = (
    ReconciliationTarget(
        "sellingGeneralAdministrativeExpenses",
        "selling_and_administrative_expenses",
        "판매비와관리비",
        "판관비 상세 detail 합 = 이 값. 제조/일반 기업의 1순위 검산 타깃.",
    ),
    ReconciliationTarget(
        "costOfSales",
        "cost_of_sales",
        "매출원가",
        "매출원가 상세 detail 합 = 이 값.",
    ),
    ReconciliationTarget(
        "operatingProfit",
        "operating_profit",
        "영업이익",
        "영업이익 고정점. 영업비용 = 매출액 - 영업이익 의 검산 anchor.",
    ),
    ReconciliationTarget(
        "sales",
        "sales",
        "매출액",
        "매출액 고정점. 영업비용 bridge 검산용.",
    ),
)
# lane 별 reconciliation 정책 — detail 합을 어떤 IS 타깃과 맞추는가.
RECONCILIATION_LANE_POLICY: dict[str, dict[str, Any]] = {
    "strictSgaDetail": {
        "reconcileAgainst": ["sellingGeneralAdministrativeExpenses"],
        "rule": "판관비 상세 detail row 합 ≈ 판관비(selling_and_administrative_expenses).",
    },
    "strictCostOfSalesDetail": {
        "reconcileAgainst": ["costOfSales"],
        "rule": "매출원가 상세 detail row 합 ≈ 매출원가(cost_of_sales).",
    },
    "strictExpensesByNature": {
        "reconcileAgainst": ["costOfSales+sellingGeneralAdministrativeExpenses"],
        "rule": "비용 성격별 detail 합 ≈ 매출원가 + 판관비(=영업비용). 단일 계정 흡수 금지, bridge 검산만.",
    },
}
# 상대오차 band — reconciliationStatus.
RECONCILIATION_BANDS: tuple[ReconciliationBand, ...] = (
    ReconciliationBand("matched", 0.01, "상대오차 ≤ 1%. detail 합이 IS 타깃과 사실상 일치."),
    ReconciliationBand("near", 0.05, "상대오차 ≤ 5%. 반올림/단위/소액 미분류 수준."),
    ReconciliationBand("partial", 0.20, "상대오차 ≤ 20%. detail 일부 누락/혼입. evidence 로만."),
    ReconciliationBand("mismatch", None, "상대오차 > 20%. 매퍼 누수/소스 오선택 의심. canonical 차단."),
)


def reconciliationStatus(detailSum: float | None, target: float | None) -> str:
    """detail 합과 IS 타깃의 상대오차로 reconciliationStatus 판정."""
    if detailSum is None or target is None:
        return "unchecked"
    if target == 0:
        return "unchecked"
    relDiff = abs(detailSum - target) / abs(target)
    for band in RECONCILIATION_BANDS:
        if band.maxRelDiff is None:
            return band.status
        if relDiff <= band.maxRelDiff:
            return band.status
    return "mismatch"


# ──────────────────── v2 — 단위·scale·closure·ratio-mode (DESIGN_DEBATE.md) ────────────────────
# 노트 텍스트 선언 단위 → 원 환산 factor. finance 비율 추론보다 우선.
UNIT_FACTORS: tuple[tuple[str, float], ...] = (
    ("십억원", 1_000_000_000.0),
    ("억원", 100_000_000.0),
    ("백만원", 1_000_000.0),
    ("천원", 1_000.0),
    ("원", 1.0),
)
_UNIT_RE = re.compile(r"단\s*위\s*[:：]?\s*\(?\s*([가-힣]*원)")
# closure 게이트 — detail 합 / 노트 자체 총계 가 이 band 안이면 정상 분해(frankenblock·중복테이블 배제).
CLOSURE_BAND: tuple[float, float] = (0.80, 1.05)


def parseDeclaredUnit(text: object) -> tuple[float, str] | None:
    """노트/부모/제표 텍스트에서 '단위: 백만원' 류 선언을 찾아 (factor, label) 반환. 없으면 None.

    finance 비율 추론(yearUnitScale)보다 우선하는 결정적 단위 결정. 텍스트는 HTML
    제거 후 앞부분만 보면 충분(단위 선언은 표 머리에 온다).
    """
    raw = re.sub(r"<[^>]+>", " ", str(text or ""))
    match = _UNIT_RE.search(raw[:800])
    if not match:
        return None
    token = match.group(1)
    for label, factor in UNIT_FACTORS:
        if token == label:
            return factor, label
    return None


def yearUnitScale(panel: float | None, finance: float | None, fallback: float = 1.0) -> float:
    """연도별 단위 scale(10^n). 회사가 연도별로 단위를 바꾸는 케이스 대응.

    ratio 를 10^n 으로 반올림하므로 단위(10의 거듭제곱)만 잡고, 정수배 과다추출
    (당기/전기 2중 → ratio 0.5 → round 0 → scale 1)은 안 가려 순환논리 0. 선언 단위가
    있으면 그것을 쓰고, 없을 때만 본 함수로 finance 대조 추론.
    """
    if panel and panel > 0 and finance:
        import math

        return 10.0 ** round(math.log10(abs(finance) / panel))
    return fallback


def closureRatio(detailSum: float | None, noteTotal: float | None) -> float | None:
    """detail 합 / 노트 자체 총계. 1.0 근처면 정상 분해, ≫1 이면 frankenblock/중복."""
    if not detailSum or not noteTotal:
        return None
    return detailSum / noteTotal


def closureOk(detailSum: float | None, noteTotal: float | None) -> bool:
    """detail 합이 노트 총계에 닫히는가(CLOSURE_BAND 안). 블록 선택 게이트."""
    ratio = closureRatio(detailSum, noteTotal)
    return ratio is not None and CLOSURE_BAND[0] <= ratio <= CLOSURE_BAND[1]


# 비용 라벨에 붙는 기능(function) 태그 — panel 셀분할이 [비용항목, 기능, 금액] 에서
# 기능을 라벨 셀에 ', 판관비' 식으로 인코딩한다. 떼면 깨끗한 비용 라벨, 떼낸 기능은 lane 신호.
FUNCTION_TAG_LANE: dict[str, str] = {
    "판매비와관리비": "strictSgaDetail",
    "판매비및관리비": "strictSgaDetail",
    "판매관리비": "strictSgaDetail",
    "판관비": "strictSgaDetail",
    "매출원가": "strictCostOfSalesDetail",
    "제조원가": "strictCostOfSalesDetail",
}


def stripFunctionTag(label: object) -> tuple[str, str | None]:
    """라벨 끝의 ', 판관비'/', 매출원가' 기능 태그를 분리. (cleanLabel, lane|None) 반환.

    panel 셀분할 포맷(기아 등)은 '광고선전비, 판관비' 처럼 기능을 라벨에 붙인다. 마지막
    콤마/슬래시 토큰이 정확히 기능 태그일 때만 떼어, 비용 라벨을 깨끗이 하고 그 기능으로
    lane(판관비/매출원가)을 row 단위로 알 수 있게 한다. '기타판매비와관리비'(콤마 없음)나
    '감가상각비, 무형자산상각비'(마지막이 비용)는 떼지 않는다.
    """
    text = str(label or "")
    parts = [p.strip() for p in re.split(r"[,/]", text)]
    if len(parts) >= 2 and parts[-1] in FUNCTION_TAG_LANE:
        lane = FUNCTION_TAG_LANE[parts[-1]]
        clean = parts[0] if len(parts) == 2 else ", ".join(parts[:-1])
        return clean, lane
    return text, None


def ratioMode(coverage: float | None) -> str:
    """reconciliation 불일치를 고칠 수 있는 버그 vs honest 한계로 분류(ratio-mode 택소노미).

    정수배(당기/전기 dedup)·pow10(단위)·blowup 은 dedupBug(고칠 수 있음), 비정수
    1.05~1.95·과소추출은 honestGap(데이터 한계). match band 는 matched.
    """
    if coverage is None:
        return "unchecked"
    for k in (2, 3, 4, 5):
        if abs(coverage - k) / k <= 0.04:
            return "dedupBug:int"
    for p in (10.0, 100.0, 1000.0):
        if abs(coverage - p) / p <= 0.05:
            return "dedupBug:unit"
    if coverage > 5:
        return "dedupBug:blowup"
    if 0.95 <= coverage <= 1.05:
        return "matched"
    if 1.05 < coverage < 1.95:
        return "honestGap:over"
    return "honestGap:under"


# ──────────────────── v6 — by-nature(성격별) 노트 타깃 해소 (DESIGN_DEBATE v6) ────────────────────
# 비용의 성격별 분류(NT_D834300/305) 노트는 두 종류다:
#   (1) 영업비용 전체 성격별 — 원재료/재고/제품변동/상품매입(=COGS 성격) 마커 보유 → 매출원가+판관비 정합.
#   (2) 판관비 성격별 — COGS 성격 항목 없음 → 판관비(sga) 단독 정합.
# 정공: COGS 성격 마커가 타깃을 *양성 결정*하고, finance 는 *사후검산(통과/기각)* 만 한다. finance 로
# 타깃을 *고르지* 않는다(v2 §8 "finance 로 선택" 순환 회피 — C의 강제조건 ①). 마커 *부재*는 sga *후보*
# 일 뿐, 몰래 opex 인 노트는 sga 검산에서 ratio≫1 로 *기각*되어 과대계상 0 (C의 강제조건 ③).
BY_NATURE_OPEX_MARKERS: tuple[str, ...] = (
    "원재료",
    "재료비",
    "재고자산의변동",
    "재고의변동",
    "재고자산변동",
    "제품및재공품의변동",
    "제품과재공품의변동",
    "제품의변동",
    "재공품의변동",
    "상품매입",
    "상품의매입",
    "원재료매입",
    "원재료및저장품",
    "매입액",
)


def hasOpexNatureMarker(labels: object) -> bool:
    """라벨 집합에 COGS 성격 마커(원재료/재고변동/상품매입 등)가 있는가 — 영업비용 전체 노트 양성 신호."""
    norm = [normalizeLabel(x) for x in (labels or [])]
    return any(any(marker in label for marker in BY_NATURE_OPEX_MARKERS) for label in norm)


def resolveByNatureTarget(labels: object, financeSga: float | None, financeCogs: float | None) -> dict[str, Any]:
    """성격별 노트 정합 타깃을 *내용 마커*로 결정. finance 는 checkTotal 만 제공(검산은 호출자 몫).

    마커 있음 → 'operatingExpense'(checkTotal = 매출원가+판관비), 없음 → 'sga'(checkTotal = 판관비).
    반환 target/checkTotal 로 호출자가 10^n scale 후 ratio band 검산해 통과/기각한다(사후검산).
    checkTotal None(finance 부재)이면 검산 불가 → 호출자가 ambiguous 처리.
    """
    markerHit = hasOpexNatureMarker(labels)
    if markerHit:
        target = "operatingExpense"
        checkTotal = (
            (financeCogs or 0.0) + (financeSga or 0.0) if (financeCogs is not None or financeSga is not None) else None
        )
    else:
        target = "sga"
        checkTotal = financeSga
    return {"target": target, "checkTotal": checkTotal, "markerHit": markerHit}


# ──────────────────── quarantine → promote 운영 lifecycle ────────────────────
QUARANTINE_LIFECYCLE: tuple[QuarantineStage, ...] = (
    QuarantineStage(
        1,
        "observe",
        "panel builder(attempt09/본진 panel provider)",
        "strict source 안에서 exact 매핑 실패한 detail 라벨을 quarantine 으로 누적하고 빈도순 원장에 남긴다.",
        "canonical output 에 절대 넣지 않는다. quarantine 카운터에만 적재.",
    ),
    QuarantineStage(
        2,
        "review",
        "운영자(사람)",
        "빈도 상위 quarantine 라벨을 모아 비용 성격/판관비 상세 후보인지 사람이 판정한다. 누수(수익/자산/합계)면 role term 에 추가.",
        "10 라벨 묶음 단위 review. 자동 승격 금지(docstring auto-sweep 금지와 동일 정신).",
    ),
    QuarantineStage(
        3,
        "promote",
        "운영자(사람)",
        "확정된 라벨만 WISE_REPORT_EXACT_LABEL_MAP 또는 NATURAL_EXACT_LABEL_MAP 에 exact 로 추가하고 mapperVersion 을 올린다.",
        "추가 후 buildExactIndex collision 0 · cross collision 0 재확인. reconciliation 회귀 없을 것.",
    ),
    QuarantineStage(
        4,
        "freeze",
        "운영자(사람)",
        "unique label 카운트(현재 WiseReport 47 / natural 124)를 새 기준으로 동결하고 attempt08 foundation 가드 숫자를 갱신한다.",
        "가드 숫자 갱신 commit 과 매퍼 추가 commit 을 같은 변경 단위로 묶는다.",
    ),
)


# ──────────────────── 본진 이관 plan ────────────────────
MAIN_INTEGRATION_PLAN: tuple[MainIntegrationStep, ...] = (
    MainIntegrationStep(
        1,
        "src/dartlab/core/accounts/expenseDetail.py",
        "L0 core/accounts",
        "이 모듈(expenseDetailSsot)을 그대로 이관한다. 뼈대·lane·role·schema·label map·term·reconciliation 타깃·lifecycle 전부 순수 dict/dataclass.",
        "core 가 상위 계층 import 0. panel/polars/finance 의존 0. 기존 core/accounts SSOT(aliases/labels/normalize)와 형제.",
    ),
    MainIntegrationStep(
        2,
        "src/dartlab/providers/dart/panel/expenseDetail.py",
        "L1 providers/dart/panel",
        "panel parquet note table 을 읽어 sourceLane/rowRole/labelMapper 적용 후 long rows 생성. 표 파싱은 panel.text.parsePanelXmlTables + tableRows.tableToRowDicts 재사용(regex 재발명 금지).",
        "docs.parquet/sections import 0. 입력은 panel parquet(readLong) 만. core.accounts.expenseDetail import.",
    ),
    MainIntegrationStep(
        3,
        "src/dartlab/providers/dart/finance/expenseDetail.py",
        "L1 providers/dart/finance",
        "finance buildAnnual IS(판관비/매출원가/영업이익) 와 panel 비용상세 long rows 를 reconciliation 해서 confidence 부여. strict lane canonical/evidence 분리, loose canonical 0.",
        "finance 본체(statements/pivot) 무수정. RECONCILIATION_TARGETS snakeId 로 join. reconciliationStatus band 적용.",
    ),
    MainIntegrationStep(
        4,
        "finance facade — expenseDetail() verb + StatementsResult.expenseDetail",
        "L1 public facade review",
        "compare 처럼 톱레벨 동사 1개(expenseDetail) 또는 StatementsResult 에 expenseDetail 필드 추가. finance 는 그대로 굴리고 별도 long DataFrame 으로 결합.",
        "operation.apiContract review 후 노출. panel wide identity 불가침([[feedback_panel_wide_identity]]).",
    ),
    MainIntegrationStep(
        5,
        "tests/providers/dart/testExpenseDetail.py",
        "test mirror",
        "대표 제조(005930)/플랫폼(035420)/금융(055550)/보험(000810) 으로 canonical/evidence/blocked/reconcile 케이스 고정.",
        "전체 pytest 금지. targeted test + Guard quick.",
    ),
)


FOUNDATION_VERSION = "expenseDetailSsot.v1.0"
MAPPER_VERSION = "exact-label-v1-2026-06-06"


# ──────────────────── 순수 helper ────────────────────
def normalizeText(rawText: object) -> str:
    """공백 제거 + 소문자화 — 라벨/제목 비교용 정규화."""
    return "".join(str(rawText or "").split()).lower()


def normalizeLabel(rawLabel: object) -> str:
    """normalizeText + 구두점·구분자 제거 — exact label 매칭 키."""
    text = normalizeText(rawLabel)
    for token in ("ㆍ", "·", "/", "\\", "-", "_", ",", ".", ":", ";", "*", "(", ")", "[", "]"):
        text = text.replace(token, "")
    return text


def containsAny(rawText: object, aliases: tuple[str, ...]) -> bool:
    """정규화 텍스트에 alias 중 하나라도 포함되는지."""
    normalizedText = normalizeText(rawText)
    return any(normalizeText(alias) in normalizedText for alias in aliases)


def categoryKeysForText(rawText: object) -> tuple[str, ...]:
    """텍스트가 alias로 매칭되는 비용 카테고리 key 들."""
    return tuple(category.key for category in EXPENSE_CATEGORIES if containsAny(rawText, category.aliases))


def sourceKindsForText(rawText: object) -> tuple[str, ...]:
    """텍스트가 매칭되는 주석 source kind(판관비명세/성격별 등) key 들."""
    return tuple(key for key, patterns in NOTE_SOURCE_PATTERNS.items() if containsAny(rawText, patterns))


def buildExactIndex(mapData: dict[str, tuple[str, ...]]) -> dict[str, str]:
    """{categoryKey: labels} → {정규화라벨: categoryKey} exact 역인덱스(충돌 검출)."""
    exactIndex: dict[str, str] = {}
    for categoryKey, labels in mapData.items():
        for label in labels:
            normalized = normalizeLabel(label)
            if normalized in exactIndex and exactIndex[normalized] != categoryKey:
                raise ValueError(f"exact label collision: {label} -> {exactIndex[normalized]} / {categoryKey}")
            exactIndex[normalized] = categoryKey
    return exactIndex


WISE_EXACT_INDEX: dict[str, str] = buildExactIndex(WISE_REPORT_EXACT_LABEL_MAP)
NATURAL_EXACT_INDEX: dict[str, str] = buildExactIndex(NATURAL_EXACT_LABEL_MAP)


def mapExactLabel(label: object) -> dict[str, Any]:
    """정규화 라벨을 WiseReport / natural exact 인덱스로 매핑. 둘 다 없으면 quarantine."""
    normalized = normalizeLabel(label)
    if normalized in WISE_EXACT_INDEX:
        return {"kind": "wiseReportExact", "categoryKey": WISE_EXACT_INDEX[normalized]}
    if normalized in NATURAL_EXACT_INDEX:
        return {"kind": "naturalExact", "categoryKey": NATURAL_EXACT_INDEX[normalized]}
    return {"kind": "quarantine", "categoryKey": None}


# stem 폴백 — *명확한 형태 변이*만(사용권자산감가상각비→감가상각). longest-distinctive-first 순서로
# 충돌 해소(대손상각 먼저, 그다음 일반 상각). suffix/contains 앵커. **role=detail 통과 행에서만**
# 호출되므로(누수는 classifyStrictRowRole 가 차단) contains 누수가 구조적으로 불가능.
# "집 없는" 라벨(수출제비용·사무비·하자보수비)은 일부러 안 넣는다 — 강제 배정은 비교가능성 위조(skeptic).
STEM_RULES: tuple[tuple[tuple[str, ...], str], ...] = (
    (("대손상각", "대손충당금", "손실충당금", "대손"), "badDebtImpairment"),
    (("세금과공과", "제세공과", "공과금"), "taxesDues"),
    (
        ("사용권자산상각", "투자부동산상각", "유형자산상각", "무형자산상각", "감가상각", "상각비"),
        "depreciationAmortization",
    ),
    (("연구개발", "경상연구", "조사연구", "기술개발", "경상개발", "시험연구"), "researchDevelopment"),
    (("종업원급여", "퇴직급여", "복리후생", "주식보상", "잡급", "제수당"), "employeeBenefits"),
    (("지급수수료", "수수료비용"), "commissionsFees"),
    (("광고선전", "판매촉진"), "advertisingPromotion"),
    (("임차료", "리스료"), "rentLease"),
    (("여비교통", "출장비"), "travelEntertainment"),
)


def stemCategory(label: object) -> str | None:
    """명확한 형태 변이 라벨을 카테고리 root 로 매핑(없으면 None). exact 실패 후 폴백."""
    normalized = normalizeLabel(label)
    for roots, category in STEM_RULES:
        if any(root in normalized for root in roots):
            return category
    return None


def mapExpenseLabel(label: object) -> dict[str, Any]:
    """exact → stem 폴백 → quarantine. panel/finance 가 쓰는 매핑 표면(stem 포함)."""
    exact = mapExactLabel(label)
    if exact["kind"] != "quarantine":
        return exact
    stem = stemCategory(label)
    if stem is not None:
        return {"kind": "stem", "categoryKey": stem}
    return {"kind": "quarantine", "categoryKey": None}


# coarse fold — 16 카테고리/8 detail key 를 비교가능 8 버킷으로. reconciliation/비교는 coarse 로.
# 변이 폭발은 카테고리가 잘게 쪼개져 생기므로 coarse 가 변이 문제를 *증발*시킨다(skeptic).
COARSE_FOLD: dict[str, str] = {
    "personnelExpense": "personnel",
    "employeeBenefits": "personnel",
    "depreciationAmortizationExpense": "depreciation",
    "depreciationAmortization": "depreciation",
    "researchDevelopmentExpense": "rnd",
    "researchDevelopment": "rnd",
    "advertisingExpense": "adPromo",
    "advertisingPromotion": "adPromo",
    "commissionsFees": "feesServices",
    "outsourcingServices": "feesServices",
    "taxesDues": "taxesDues",
    "rentLease": "rentLease",
    "insurance": "etc",
    "travelEntertainment": "etc",
    "materialsPurchased": "materials",
    "inventoryChange": "materials",
    "freightLogistics": "logistics",
    "utilities": "etc",
    "badDebtImpairment": "etc",
    "otherOperatingExpense": "etc",
    "sellingExpense": "etc",
    "administrativeExpense": "etc",
    "otherCostLikeExpense": "etc",
    "otherSgaExpense": "etc",
}


def coarseBucket(categoryKey: object) -> str:
    """detail key → coarse 비교가능 버킷. 미지/quarantine → etc."""
    return COARSE_FOLD.get(str(categoryKey or ""), "etc")


def exactOrContainsAny(label: str, terms: tuple[str, ...]) -> bool:
    """정규화 라벨에 terms 중 하나라도 substring 으로 포함되는지."""
    return any(normalizeLabel(term) in label for term in terms)


def isTotalLabel(label: str) -> bool:
    """합계/총계/소계 류 총계 라벨인지(TOTAL_TERMS)."""
    normalized = normalizeLabel(label)
    return any(normalized == normalizeLabel(term) or normalizeLabel(term) in normalized for term in TOTAL_TERMS)


def isFunctionalLabel(label: str) -> bool:
    """매출원가/판관비/영업비용 등 기능별 합계 라벨인지(기타 접두는 제외)."""
    normalized = normalizeLabel(label)
    # "기타판매비와관리비"/"기타영업비용" 처럼 기타 접두 라벨은 기능별 합계가 아니라
    # 비용 상세 버킷이다. 기능별 term 을 포함해도 functionalTotal 로 보지 않는다.
    if normalized.startswith("기타"):
        return False
    return any(normalizeLabel(term) in normalized for term in FUNCTIONAL_TOTAL_TERMS)


def isHeaderLabel(label: str) -> bool:
    """구분/항목/계정과목 등 표 헤더 라벨인지(HEADER_TERMS exact)."""
    normalized = normalizeLabel(label)
    return any(normalized == normalizeLabel(term) for term in HEADER_TERMS)


def classifyStrictRowRole(label: str, fallbackRowKind: str) -> str:
    """strict source 안 detail 행의 role 분류 (pure). 누수/합계/헤더를 detail 에서 제거."""
    normalized = normalizeLabel(label)
    if fallbackRowKind in {"total", "functionalTotal", "header"}:
        return fallbackRowKind
    if any(normalized == normalizeLabel(term) for term in TOTAL_TERMS):
        return "total"
    if any(normalized == normalizeLabel(term) for term in HEADER_TERMS):
        return "header"
    if not normalized.startswith("기타") and any(normalizeLabel(term) in normalized for term in FUNCTIONAL_TOTAL_TERMS):
        return "functionalTotal"
    if exactOrContainsAny(normalized, REVENUE_LEAKAGE_TERMS):
        return "excludedRevenue"
    if "사용권자산" in normalized and "상각" not in normalized:
        return "excludedAsset"
    if "판매보증충당부채전입" in normalized:
        return "detail"
    if exactOrContainsAny(normalized, BALANCE_SHEET_LEAKAGE_TERMS):
        return "excludedAsset"
    return "detail"


def orderedWiseReportRows() -> tuple[WiseReportTargetRow, ...]:
    """뼈대 행 + 판관비 상세 후보 행을 order 순으로 합쳐 반환."""
    return tuple(sorted((*WISE_REPORT_STATEMENT_ROWS, *SGA_DETAIL_CANDIDATE_ROWS), key=lambda row: row.order))


def laneContractByName() -> dict[str, SourceLaneContract]:
    """{sourceLane: SourceLaneContract} 조회 dict."""
    return {contract.sourceLane: contract for contract in SOURCE_LANE_CONTRACT}


def reconciliationTargetByKey() -> dict[str, ReconciliationTarget]:
    """{statementKey: ReconciliationTarget} 조회 dict."""
    return {target.statementKey: target for target in RECONCILIATION_TARGETS}


# ──────────────────── self-test ────────────────────
def ssotSummary() -> dict[str, Any]:
    """SSOT 동결 수치(뼈대/카테고리/exact label/스키마/타깃 수) 요약 — self-test 기준."""
    wiseReverse: dict[str, list[str]] = {}
    for key, labels in WISE_REPORT_EXACT_LABEL_MAP.items():
        for label in labels:
            wiseReverse.setdefault(normalizeLabel(label), []).append(key)
    naturalReverse: dict[str, list[str]] = {}
    for key, labels in NATURAL_EXACT_LABEL_MAP.items():
        for label in labels:
            naturalReverse.setdefault(normalizeLabel(label), []).append(key)
    crossCollision = sorted(set(wiseReverse) & set(naturalReverse))
    return {
        "foundationVersion": FOUNDATION_VERSION,
        "mapperVersion": MAPPER_VERSION,
        "statementRowCount": len(WISE_REPORT_STATEMENT_ROWS),
        "sgaDetailCandidateRowCount": len(SGA_DETAIL_CANDIDATE_ROWS),
        "expenseCategoryCount": len(EXPENSE_CATEGORIES),
        "wiseExactRawLabelCount": sum(len(v) for v in WISE_REPORT_EXACT_LABEL_MAP.values()),
        "wiseExactUniqueLabelCount": len(WISE_EXACT_INDEX),
        "naturalExactRawLabelCount": sum(len(v) for v in NATURAL_EXACT_LABEL_MAP.values()),
        "naturalExactUniqueLabelCount": len(NATURAL_EXACT_INDEX),
        "crossMapCollisionCount": len(crossCollision),
        "sourceLaneCount": len(SOURCE_LANE_CONTRACT),
        "rowRoleCount": len(ROW_ROLE_CONTRACT),
        "outputSchemaColumnCount": len(OUTPUT_SCHEMA),
        "reconciliationTargetCount": len(RECONCILIATION_TARGETS),
        "quarantineLifecycleStageCount": len(QUARANTINE_LIFECYCLE),
        "mainIntegrationStepCount": len(MAIN_INTEGRATION_PLAN),
    }


def assertSsot() -> None:
    """SSOT 동결 수치 + v2/v6 헬퍼 동작을 self-test 로 강제(회귀 가드)."""
    summary = ssotSummary()
    assert summary["statementRowCount"] == 20, summary["statementRowCount"]
    assert summary["sgaDetailCandidateRowCount"] == 8, summary["sgaDetailCandidateRowCount"]
    assert summary["expenseCategoryCount"] == 16, summary["expenseCategoryCount"]
    assert summary["wiseExactUniqueLabelCount"] == 47, summary["wiseExactUniqueLabelCount"]
    assert summary["naturalExactUniqueLabelCount"] == 124, summary["naturalExactUniqueLabelCount"]
    assert summary["crossMapCollisionCount"] == 0, summary["crossMapCollisionCount"]
    assert summary["sourceLaneCount"] == 6, summary["sourceLaneCount"]
    assert summary["outputSchemaColumnCount"] == 23, summary["outputSchemaColumnCount"]
    # v2 helpers.
    assert parseDeclaredUnit("(단위: 백만원)") == (1_000_000.0, "백만원")
    assert parseDeclaredUnit("계정과목 금액") is None
    assert yearUnitScale(1000.0, 1_000_000.0) == 1000.0
    assert yearUnitScale(2.0, 1.0) == 1.0  # 정수배 과다추출은 scale 1 — 안 가림.
    assert closureOk(99.0, 100.0) and not closureOk(200.0, 100.0)
    assert ratioMode(2.0) == "dedupBug:int" and ratioMode(1000.0) == "dedupBug:unit"
    assert ratioMode(1.0) == "matched" and ratioMode(1.3) == "honestGap:over"
    assert summary["reconciliationTargetCount"] == 4, summary["reconciliationTargetCount"]
    # detail 후보는 전부 판관비 child.
    assert all(row.parentKey == "sellingGeneralAdministrativeExpenses" for row in SGA_DETAIL_CANDIDATE_ROWS)
    # reconciliation band 단조성.
    assert reconciliationStatus(100.0, 100.0) == "matched"
    assert reconciliationStatus(104.0, 100.0) == "near"
    assert reconciliationStatus(115.0, 100.0) == "partial"
    assert reconciliationStatus(200.0, 100.0) == "mismatch"
    assert reconciliationStatus(None, 100.0) == "unchecked"
    # v6 — by-nature 타깃 해소 (마커가 타깃 결정, finance 는 checkTotal 만).
    assert hasOpexNatureMarker(["급여", "원재료 등의 사용액"]) is True
    assert hasOpexNatureMarker(["급여", "감가상각비", "광고선전비"]) is False
    opex = resolveByNatureTarget(["원재료 사용액", "급여", "광고선전비"], 30.0, 70.0)
    assert opex["target"] == "operatingExpense" and opex["checkTotal"] == 100.0, opex
    sga = resolveByNatureTarget(["급여", "감가상각비", "지급수수료"], 30.0, 70.0)
    assert sga["target"] == "sga" and sga["checkTotal"] == 30.0, sga
    # 매출원가 없는 회사(플랫폼) — 마커 없으면 sga 타깃, 영업비용=판관비.
    noCogs = resolveByNatureTarget(["급여", "지급수수료"], 50.0, None)
    assert noCogs["target"] == "sga" and noCogs["checkTotal"] == 50.0, noCogs


def main() -> int:
    """self-test 실행 + SSOT 요약 출력(CLI)."""
    import json

    assertSsot()
    print(json.dumps(ssotSummary(), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
