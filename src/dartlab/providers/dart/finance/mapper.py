"""항목 → snakeId 매핑.

매핑 파이프라인 단계 (입력·사전 양방향 normalize + 짧은 suffix 흡수):

1. account_id prefix 제거 → normalizedId
2. ID_SYNONYMS 로 영문 ID 동의어 통합
3. ACCOUNT_NAME_SYNONYMS 로 한글명 동의어 통합
4. accountMappings.json 직접 조회 (한글명 우선 → 영문ID)
5. 입력 공백 제거 후 사전 직접 조회
6. 사전 공백 변형 역인덱스 조회 (사전 키 공백/tab/ZWSP 흡수)
7. 입력 괄호+공백 제거 후 사전 직접 조회
8. 사전 괄호 변형 역인덱스 조회 (예: '현금의 기타유입' ↔ '현금의기타유입(유출)')
9. 입력 하이픈 제거 후 사전 조회 (실험 081-001)
10. 사전 하이픈 변형 역인덱스 조회
11. 입력 짧은 한국어 suffix 제거 후 사전 재조회 — '액'/'등'/'외' 1글자
    (cycle 12 회귀: '영업양도로 인한 현금 유입' ↔ '영업양도로 인한 현금유입액')
12. 미매핑 → None

데이터 SSOT (`engines.mappers` 학습 파이프라인 참조):

- accountMappings.json — `src/dartlab/reference/data/accountMappings.json` (core 승격, 34,171 entries)
- 로더 — `dartlab.core.utils.labels._loadAccountMappings`
- snakeId 정의 — `standardAccounts` (reference/data/accountMappings.json 안 sub-key)

학습 갱신 절차는 운영자 수동 — JSON 직접 patch 후 `AccountMapper.release()` 로 캐시 무효화.
"""

from __future__ import annotations

import re
from typing import Optional

from dartlab.core.utils.ordering import levelMap as _commonLevelMap
from dartlab.core.utils.ordering import sortOrder as _commonSortOrder

_PREFIX_RE = re.compile(r"^(?:ifrs-full_|ifrs_|dart_|ifrs-smes_)")
_PAREN_RE = re.compile(r"\([^)]*\)")

# 한국어 짧은 명사 suffix — 의미 손실 없는 fold 대상
# '액' 금액 (현금유입액↔현금유입), '등' etc. (자산등↔자산), '외' 외에 (차입금외↔차입금)
# 길이 우선 매칭 (길이 1 만 사용; 더 긴 suffix 추가 시 의미 손실 위험 검토 후)
_KOR_TRIM_SUFFIXES = ("액", "등", "외")

ID_SYNONYMS: dict[str, str] = {
    "ShareOfProfitLossOfAssociatesAndJointVenturesAccountedForUsingEquityMethod": "ProfitsOfAssociatesAndJointVenturesAccountedForUsingEquityMethod",
    "OtherIncomeExpenseFromSubsidiariesJointlyControlledEntitiesAndAssociates": "ProfitsOfAssociatesAndJointVenturesAccountedForUsingEquityMethod",
    "RevenueFromOperations": "Revenue",
    "SalesRevenue": "Revenue",
    "OperatingRevenue": "Revenue",
    "GrossProfitLoss": "GrossProfit",
    "OperatingIncome": "OperatingIncomeLoss",
    "OperatingProfit": "OperatingIncomeLoss",
    "ProfitFromOperations": "OperatingIncomeLoss",
    "NonoperatingIncome": "OtherIncome",
    "NonoperatingExpenses": "OtherExpenses",
    "ProfitBeforeTax": "ProfitLossBeforeTax",
    "ProfitBeforeIncomeTax": "ProfitLossBeforeTax",
    "IncomeTaxExpenseBenefit": "IncomeTaxExpense",
    "Profit": "ProfitLoss",
    "NetIncome": "ProfitLoss",
    "NetProfit": "ProfitLoss",
    "EarningsPerShare": "BasicEarningsLossPerShare",
    "EPS": "BasicEarningsLossPerShare",
    "TotalAssets": "Assets",
    "TotalCurrentAssets": "CurrentAssets",
    "Cash": "CashAndCashEquivalents",
    "CashEquivalents": "CashAndCashEquivalents",
    "TradeReceivables": "TradeAndOtherCurrentReceivables",
    "AccountsReceivable": "TradeAndOtherCurrentReceivables",
    "Inventories": "CurrentInventories",
    "Stock": "CurrentInventories",
    "TotalNoncurrentAssets": "NoncurrentAssets",
    "FixedAssets": "NoncurrentAssets",
    "PPE": "PropertyPlantAndEquipment",
    "TangibleAssets": "PropertyPlantAndEquipment",
    "IntangibleAssets": "IntangibleAssetsOtherThanGoodwill",
    "InvestmentInAssociates": "InvestmentsInAssociatesAndJointVentures",
    "TotalLiabilities": "Liabilities",
    "TotalCurrentLiabilities": "CurrentLiabilities",
    "TradePayables": "TradeAndOtherCurrentPayables",
    "AccountsPayable": "TradeAndOtherCurrentPayables",
    "ShortTermBorrowings": "CurrentBorrowings",
    "ShortTermDebt": "CurrentBorrowings",
    "TotalNoncurrentLiabilities": "NoncurrentLiabilities",
    "LongTermBorrowings": "NoncurrentBorrowings",
    "LongTermDebt": "NoncurrentBorrowings",
    "DeferredTax": "DeferredTaxLiabilities",
    "TotalEquity": "Equity",
    "ShareholdersEquity": "Equity",
    "Capital": "IssuedCapital",
    "ShareCapital": "IssuedCapital",
    "AccumulatedProfits": "RetainedEarnings",
    "OperatingCashFlows": "CashFlowsFromOperatingActivities",
    "CashFromOperations": "CashFlowsFromOperatingActivities",
    "InvestingCashFlows": "CashFlowsFromInvestingActivities",
    "CashFromInvesting": "CashFlowsFromInvestingActivities",
    "FinancingCashFlows": "CashFlowsFromFinancingActivities",
    "CashFromFinancing": "CashFlowsFromFinancingActivities",
    "NetCashFlow": "IncreaseDecreaseInCashAndCashEquivalents",
    "CashIncrease": "IncreaseDecreaseInCashAndCashEquivalents",
    "OCI": "OtherComprehensiveIncome",
    "TotalComprehensiveIncome": "ComprehensiveIncome",
}

ACCOUNT_NAME_SYNONYMS: dict[str, str] = {
    "영업이익(손실)": "영업이익",
    "당기순이익(손실)": "당기순이익",
    "법인세비용차감전순이익(손실)": "법인세비용차감전순이익",
    "매출총이익(손실)": "매출총이익",
    "기본주당이익(손실)": "기본주당이익",
    "희석주당이익(손실)": "희석주당이익",
    "총포괄손익": "총포괄이익",
    "매출": "매출액",
    "수익": "매출액",
    "매출액합계": "매출액",
    "영업수익": "매출액",
    "상품매출": "매출액",
    "제품매출": "매출액",
    "용역매출": "매출액",
    "매출원가합계": "매출원가",
    "제조원가": "매출원가",
    "상품매출원가": "매출원가",
    "판매관리비": "판매비와관리비",
    "판관비": "판매비와관리비",
    "판매비": "판매비와관리비",
    "관리비": "판매비와관리비",
    "판매비및관리비": "판매비와관리비",
    "판매및관리비": "판매비와관리비",
    "매출총손익": "매출총이익",
    "영업손익": "영업이익",
    "당기순손익": "당기순이익",
    "순이익": "당기순이익",
    "순손익": "당기순이익",
    "법인세차감전순이익": "법인세비용차감전순이익",
    "세전이익": "법인세비용차감전순이익",
    "법인세비용차감전이익": "법인세비용차감전순이익",
    "기타영업외수익": "기타수익",
    "영업외수익": "기타수익",
    "기타영업외비용": "기타비용",
    "영업외비용": "기타비용",
    "이자수익": "금융수익",
    "이자비용": "금융비용",
    "유동자산합계": "유동자산",
    "비유동자산합계": "비유동자산",
    "고정자산": "비유동자산",
    "자산합계": "자산총계",
    "총자산": "자산총계",
    "현금": "현금및현금성자산",
    "현금성자산": "현금및현금성자산",
    "매출채권": "매출채권및기타채권",
    "단기매출채권": "매출채권및기타채권",
    "재고": "재고자산",
    "상품": "재고자산",
    "제품": "재고자산",
    "유형자산합계": "유형자산",
    "무형자산합계": "무형자산",
    "영업권및무형자산": "무형자산",
    "관계기업투자": "관계기업및공동기업투자",
    "관계회사투자": "관계기업및공동기업투자",
    "유동부채합계": "유동부채",
    "비유동부채합계": "비유동부채",
    "고정부채": "비유동부채",
    "부채합계": "부채총계",
    "총부채": "부채총계",
    "매입채무": "매입채무및기타채무",
    "단기매입채무": "매입채무및기타채무",
    "단기빌림": "단기차입금",
    "유동성장기부채": "단기차입금",
    "장기빌림": "장기차입금",
    "이연법인세": "이연법인세부채",
    "자본합계": "자본총계",
    "총자본": "자본총계",
    "보통주자본금": "자본금",
    "우선주자본금": "자본금",
    "이익잉여금합계": "이익잉여금",
    "미처분이익잉여금": "이익잉여금",
    "기타포괄손익누계액": "기타자본구성요소",
    "영업활동으로인한현금흐름": "영업활동현금흐름",
    "영업활동현금흐름합계": "영업활동현금흐름",
    "영업에서창출된현금흐름": "영업활동현금흐름",
    "투자활동으로인한현금흐름": "투자활동현금흐름",
    "투자활동현금흐름합계": "투자활동현금흐름",
    "재무활동으로인한현금흐름": "재무활동현금흐름",
    "재무활동현금흐름합계": "재무활동현금흐름",
    "현금증가": "현금및현금성자산증감",
    "현금감소": "현금및현금성자산증감",
    "기타포괄이익": "기타포괄손익",
    "포괄손익": "총포괄이익",
    "주당이익": "기본주당이익",
    "주당순이익": "기본주당이익",
    "EPS": "기본주당이익",
    "희석EPS": "희석주당이익",
    "법인세": "법인세비용",
    "법인세등": "법인세비용",
    "당기법인세": "법인세비용",
    "지분법이익": "지분법손익",
    "지분법평가손익": "지분법손익",
    "유형자산감가상각비": "감가상각비",
    "무형자산상각비": "감가상각비",
    "대손비용": "대손상각비",
    "현금배당": "배당금",
    "주식배당": "배당금",
    "매출 액": "매출액",
    "영업 이익": "영업이익",
    "당기 순이익": "당기순이익",
    "자산 총계": "자산총계",
    "부채 총계": "부채총계",
    "자본 총계": "자본총계",
}


def _stripPrefix(accountId: str) -> str:
    return _PREFIX_RE.sub("", accountId)


class AccountMapper:
    """항목 매핑기 (eddmpython v6+v8 파이프라인).

    v6: account_id prefix 제거 + ID_SYNONYMS/ACCOUNT_NAME_SYNONYMS 정규화
    v8: 정규화된 한글명/영문ID → accountMappings.json → standardAccounts snakeId
    """

    _instance: Optional[AccountMapper] = None
    _mappings: Optional[dict[str, str]] = None
    _stdAccountsRaw: Optional[dict[str, dict]] = None
    _noHyphenIndex: Optional[dict[str, str]] = None  # lazy 빌드
    _noSpaceIndex: Optional[dict[str, str]] = None  # 사전 키 공백/특수문자 제거 역인덱스
    _noParenIndex: Optional[dict[str, str]] = None  # 사전 키 괄호+공백 제거 역인덱스

    @classmethod
    def get(cls) -> AccountMapper:
        """싱글턴 AccountMapper 인스턴스 반환.

        Returns:
            동일 process 안에서 항상 같은 ``AccountMapper`` 인스턴스.

        Raises:
            없음.

        Example:
            >>> mapper = AccountMapper.get()
            >>> mapper.map("ifrs-full_Revenue", "매출액")

        SeeAlso:
            - ``accountMappings.json`` / ``AccountMapper`` — 본 모듈 origin.

        Requires:
            - dartlab

        Capabilities:
            - account_id / 한글명 → snakeId 매핑 helper.

        Guide:
            - 사용자 API 는 ``c.show()`` — 본 모듈 직접 호출 X.

        AIContext:
            internal mapper — AI 직접 호출 X.

        LLM Specifications:
            AntiPatterns:
                - 본 모듈 직접 호출 X.
            OutputSchema:
                - str / dict / None.
            Prerequisites:
                - accountMappings.json.
            Freshness:
                - 매핑 학습 갱신 시점.
            Dataflow:
                - account_id → 7 단계 매핑 → snakeId.
            TargetMarkets:
                - KR (DART) 항목 매핑.
        """
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def release(cls) -> None:
        """메모리 해제. 다음 ``get()`` 호출 시 자동 재로드.

        Returns:
            None (class-level cache reset).

        Raises:
            없음.

        Example:
            >>> AccountMapper.release()  # accountMappings.json 갱신 후

        SeeAlso:
            - ``accountMappings.json`` / ``AccountMapper`` — 본 모듈 origin.

        Requires:
            - dartlab

        Capabilities:
            - account_id / 한글명 → snakeId 매핑 helper.

        Guide:
            - 사용자 API 는 ``c.show()`` — 본 모듈 직접 호출 X.

        AIContext:
            internal mapper — AI 직접 호출 X.
        """
        cls._instance = None
        cls._mappings = None
        cls._stdAccountsRaw = None
        cls._noHyphenIndex = None
        cls._noSpaceIndex = None
        cls._noParenIndex = None

    def __init__(self):
        if AccountMapper._mappings is None:
            from dartlab.core.utils.labels import _loadAccountMappings

            data = _loadAccountMappings()
            AccountMapper._mappings = data.get("mappings", {})
            AccountMapper._stdAccountsRaw = data.get("standardAccounts", {})

    @property
    def _stdAccounts(self) -> dict[str, dict]:
        if AccountMapper._stdAccountsRaw is None:
            return {}
        return AccountMapper._stdAccountsRaw

    def _getNoHyphenIndex(self) -> dict[str, str]:
        """하이픈 제거 역인덱스 — 첫 접근 시 lazy 빌드."""
        if AccountMapper._noHyphenIndex is None:
            idx: dict[str, str] = {}
            for key, snakeId in self._mappings.items():
                stripped = key.replace("-", "").replace("–", "").replace("—", "")
                if stripped != key and stripped not in self._mappings:
                    idx[stripped] = snakeId
            AccountMapper._noHyphenIndex = idx
        return AccountMapper._noHyphenIndex

    def _getNoSpaceIndex(self) -> dict[str, str]:
        """사전 키 공백/tab/ZWSP 제거 역인덱스 — 사전 변형 흡수.

        사전에 ``'당기 순이익'`` 형태가 있어도 ``'당기순이익'`` 로 조회 가능.
        """
        if AccountMapper._noSpaceIndex is None:
            idx: dict[str, str] = {}
            for key, snakeId in self._mappings.items():
                stripped = key.replace(" ", "").replace("\t", "").replace("​", "")
                if stripped != key and stripped not in self._mappings:
                    idx[stripped] = snakeId
            AccountMapper._noSpaceIndex = idx
        return AccountMapper._noSpaceIndex

    def _getNoParenIndex(self) -> dict[str, str]:
        """사전 키 괄호+공백 제거 역인덱스 — ``'X(Y)'`` ↔ 입력 ``'X'`` 흡수.

        예: 사전 ``'현금의기타유입(유출)'`` → idx ``'현금의기타유입'``.
        입력 ``'현금의 기타유입'`` → noSpace ``'현금의기타유입'`` 매칭.
        cycle 5 (2026-05-18) 의 케이스 b 류 자동 흡수.
        """
        if AccountMapper._noParenIndex is None:
            idx: dict[str, str] = {}
            for key, snakeId in self._mappings.items():
                noSpace = key.replace(" ", "")
                stripped = _PAREN_RE.sub("", noSpace)
                if stripped != noSpace and stripped and stripped not in self._mappings:
                    idx[stripped] = snakeId
            AccountMapper._noParenIndex = idx
        return AccountMapper._noParenIndex

    def map(self, accountId: str, accountNm: str) -> Optional[str]:
        """``account_id`` + ``account_nm`` → snakeId — DART XBRL 정규화 핵심 함수.

        v8 매핑 순서 (한글명 우선 — 공시 표기 안정):
          1. ``_stripPrefix`` — IFRS/dart prefix 제거 (``ifrs-full_Revenue`` → ``Revenue``).
          2. ``ID_SYNONYMS`` 적용 — 동의어 ID 변환.
          3. ``ACCOUNT_NAME_SYNONYMS`` 적용 — 동의어 한글명 변환.
          4. 한글명 직접 조회 (``self._mappings`` = accountMappings.json 34,171 entry).
          5. 영문 ID 조회.
          6. 공백 제거 fallback.
          7. 괄호 제거 fallback (``매출액(연결)`` → ``매출액``).
          8. 하이픈/대시 제거 양방향 (입력 + 사전 index) — 미매핑 98.5% 가 하이픈 차이 (실험 081-001).

        Args:
            accountId: XBRL ``account_id`` (예: ``"ifrs-full_Revenue"``).
                prefix 포함 raw — 본 함수가 ``_stripPrefix`` 로 제거.
            accountNm: 한글 ``account_nm`` (예: ``"매출액"`` / ``"매출액(연결)"``).
                공시 원본 표기 — 동의어/공백/괄호/하이픈 모두 본 함수에서 정규화.

        Returns:
            str — snakeId (예: ``"sales"`` / ``"operating_profit"``) 또는 None (8 단계 모두 미매핑).

        Raises:
            없음. 미매핑은 None 반환 (예외 X).

        Example:
            >>> mapper = AccountMapper.get()
            >>> mapper.map("ifrs-full_Revenue", "매출액")
            'sales'

        SeeAlso:
            - ``accountMappings.json`` — 34,171 entry mapping (한글명+영문ID).
            - ``ID_SYNONYMS`` / ``ACCOUNT_NAME_SYNONYMS`` — 동의어 사전.
            - ``_stripPrefix`` / ``_PAREN_RE`` — 정규화 헬퍼.
            - ``labelMap`` / ``sortOrder`` / ``levelMap`` — 매핑 결과의 후속 사용처.

        Requires:
            - re (정규식 컴파일)
            - dartlab.providers.dart.finance.accountMappings (JSON origin)

        Capabilities:
            - DART XBRL account_id/account_nm → 표준 snakeId 정규화.
            - 동의어/공백/괄호/하이픈 변종 8 단계 fallback.
            - singleton AccountMapper.get() — JSON parse 1 회만.

        Guide:
            - 사용자 API 는 ``c.show("IS")`` — 본 함수는 내부 정규화 단.
            - 신규 종목 미매핑 신호 시 ``accountMappings.json`` 에 한글명 추가.
            - 매핑 율 측정 = ``map() != None`` 비율 (현재 ~99.7%).

        AIContext:
            internal mapper — AI 직접 호출 X. scanAccount/Company.show 내부 호출만.

        LLM Specifications:
            AntiPatterns:
                - 본 함수 직접 호출 X — ``c.show("IS")`` / ``scanAccount(...)`` 사용.
                - 미매핑 None 무시 → 데이터 손실. caller 가 None 카운트 모니터링 의무.
                - 매핑 실패 시 정규식 1 개 추가 X — ``accountMappings.json`` 직접 갱신.
                - 한 회사 미매핑 1 건 = 전 회사 영향 (singleton). 신중 추가.
            OutputSchema:
                - str — snakeId (소문자 영문 + underscore, 예: ``"net_income"``).
                - None — 8 단계 모두 매핑 실패 시.
            Prerequisites:
                - ``accountMappings.json`` (~34,171 entry, ~2MB) 로드 완료.
                - ``AccountMapper.get()`` singleton 인스턴스 (lazy init).
                - ``ID_SYNONYMS`` / ``ACCOUNT_NAME_SYNONYMS`` 동의어 사전.
            Freshness:
                - accountMappings.json 은 신규 회사 공시 등록 시 수동 추가.
                - DART 분기 마감 후 신종 계정 등장 cadence.
            Dataflow:
                - (accountId, accountNm) raw
                - → ``_stripPrefix`` (IFRS/dart prefix 제거)
                - → ``ID_SYNONYMS`` (영문 ID 동의어)
                - → ``ACCOUNT_NAME_SYNONYMS`` (한글명 동의어)
                - → 한글명 직접 조회 → 영문 ID 조회 → 공백 제거 → 괄호 제거 → 하이픈 양방향
                - → snakeId 또는 None.
            TargetMarkets:
                - KR (DART) — IFRS 한국 적용 회사 + K-IFRS 별도/연결 모두.
        """
        stripped = _stripPrefix(accountId) if accountId else ""
        normalizedId = ID_SYNONYMS.get(stripped, stripped)

        normalizedNm = ACCOUNT_NAME_SYNONYMS.get(accountNm, accountNm) if accountNm else ""

        if normalizedNm and normalizedNm in self._mappings:
            return self._mappings[normalizedNm]

        if normalizedId and normalizedId in self._mappings:
            return self._mappings[normalizedId]

        if normalizedNm:
            noSpace = normalizedNm.replace(" ", "")
            if noSpace != normalizedNm and noSpace in self._mappings:
                return self._mappings[noSpace]

            # 사전 공백 변형 역인덱스 — 사전 키 안 공백/tab/ZWSP 흡수
            nsIdx = self._getNoSpaceIndex()
            if noSpace in nsIdx:
                return nsIdx[noSpace]

            noParen = _PAREN_RE.sub("", noSpace)
            if noParen != noSpace and noParen in self._mappings:
                return self._mappings[noParen]

            # 사전 괄호 변형 역인덱스 — '현금의 기타유입' ↔ '현금의기타유입(유출)'
            npIdx = self._getNoParenIndex()
            if noParen in npIdx:
                return npIdx[noParen]
            if noSpace != noParen and noSpace in npIdx:
                return npIdx[noSpace]

            # 하이픈/대시 정규화 fallback (실험 081-001: 미매핑 98.5%가 하이픈 차이)
            # 양방향: 입력에서 하이픈 제거 → 사전 조회, 사전에서 하이픈 제거 → 역인덱스 조회
            noHyphen = noSpace.replace("-", "").replace("–", "").replace("—", "")
            if noHyphen in self._mappings:
                return self._mappings[noHyphen]
            nhIdx = self._getNoHyphenIndex()
            if noHyphen in nhIdx:
                return nhIdx[noHyphen]

            # 짧은 한국어 suffix 흡수 — '액'/'등'/'외' 1글자
            # cycle 12 회귀: '영업양도로 인한 현금 유입' (사전) ↔ '영업양도로 인한 현금유입액' (입력)
            # 모든 정규화 layer 양쪽에 시도
            for sfx in _KOR_TRIM_SUFFIXES:
                if not noSpace.endswith(sfx):
                    continue
                trimmed = noSpace[: -len(sfx)]
                if not trimmed:
                    continue
                if trimmed in self._mappings:
                    return self._mappings[trimmed]
                if trimmed in nsIdx:
                    return nsIdx[trimmed]
                if trimmed in npIdx:
                    return npIdx[trimmed]
                if trimmed in nhIdx:
                    return nhIdx[trimmed]

        return None

    def labelMap(self) -> dict[str, str]:
        """``snakeId`` → 대표 한글명 매핑.

        SSOT 위임 (``core/utils/labels.getKoreanLabels``).

        Returns:
            ``{snakeId: 한글 라벨, ...}`` dict.

        Raises:
            없음.

        Example:
            >>> mapper.labelMap()["sales"]
            '매출액'

        SeeAlso:
            - ``accountMappings.json`` / ``AccountMapper`` — 본 모듈 origin.

        Requires:
            - dartlab

        Capabilities:
            - account_id / 한글명 → snakeId 매핑 helper.

        Guide:
            - 사용자 API 는 ``c.show()`` — 본 모듈 직접 호출 X.

        AIContext:
            internal mapper — AI 직접 호출 X.

        LLM Specifications:
            AntiPatterns:
                - 본 모듈 직접 호출 X.
            OutputSchema:
                - str / dict / None.
            Prerequisites:
                - accountMappings.json.
            Freshness:
                - 매핑 학습 갱신 시점.
            Dataflow:
                - account_id → 7 단계 매핑 → snakeId.
            TargetMarkets:
                - KR (DART) 항목 매핑.
        """
        from dartlab.core.utils.labels import getKoreanLabels

        return getKoreanLabels()

    def sortOrder(self, sjDiv: str) -> dict[str, int]:
        """``sj_div`` 별 ``snakeId`` → 표시 순서.

        ``common/finance/ordering`` 위임.

        Args:
            sjDiv: BS/IS/CF/CIS/SCE 중 하나.

        Returns:
            ``{snakeId: 정수 순서}`` dict — 낮을수록 먼저 표시.

        Raises:
            없음.

        Example:
            >>> mapper.sortOrder("IS")["sales"]
            10

        LLM Specifications:
            AntiPatterns:
                - 본 모듈 직접 호출 X.
            OutputSchema:
                - str / dict / None.
            Prerequisites:
                - accountMappings.json.
            Freshness:
                - 매핑 학습 갱신 시점.
            Dataflow:
                - account_id → 7 단계 매핑 → snakeId.
            TargetMarkets:
                - KR (DART) 항목 매핑.
        """
        return _commonSortOrder(sjDiv)

    def levelMap(self, sjDiv: str) -> dict[str, int]:
        """``sj_div`` 별 ``snakeId`` → 들여쓰기 레벨.

        ``common/finance/ordering`` 위임.

        Args:
            sjDiv: BS/IS/CF/CIS/SCE 중 하나.

        Returns:
            ``{snakeId: 레벨}`` dict (0=root, 1=sub, ...).

        Raises:
            없음.

        Example:
            >>> mapper.levelMap("BS")["current_assets"]
            1

        LLM Specifications:
            AntiPatterns:
                - 본 모듈 직접 호출 X.
            OutputSchema:
                - str / dict / None.
            Prerequisites:
                - accountMappings.json.
            Freshness:
                - 매핑 학습 갱신 시점.
            Dataflow:
                - account_id → 7 단계 매핑 → snakeId.
            TargetMarkets:
                - KR (DART) 항목 매핑.
        """
        return _commonLevelMap(sjDiv)
