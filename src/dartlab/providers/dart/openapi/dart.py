"""Dart — OpenDART API 클라이언트.

사용법 1 — 회사 객체 (추천):
    from dartlab import Dart

    d = Dart()
    s = d("삼성전자")

    s.finance(2020)                      # 2020~현재 Q1~Q4 전부
    s.report("배당", 2020)               # 배당 2020~현재
    s.filings("2024")                    # 공시 목록
    s.info()                             # 기업 개황
    s.shares()                           # 지분공시
    s.saveFinance("삼성전자.parquet", 2020)  # 저장 (eddmpython 호환)

사용법 2 — 직접 호출:
    d.finstate("삼성전자", 2020, end=2024, q=0)
    d.report("삼성전자", "배당", 2020, end=2024)
    d.finstateMulti(["삼성전자", "SK하이닉스"], 2023)
"""

from __future__ import annotations

import io
import zipfile
from datetime import date, datetime
from pathlib import Path
from typing import Literal

import polars as pl

from dartlab import config as _dartlabConfig
from dartlab.core.dataConfig import DATA_RELEASES
from dartlab.providers.dart.openapi.client import DartClient

# ── 내부 상수 ──────────────────────────────────────────────
from dartlab.providers.dart.openapi.constants import (
    CODE_TO_LABEL as _CODE_TO_LABEL,
)
from dartlab.providers.dart.openapi.constants import (
    QUARTER_TO_CODE as _QUARTER_TO_CODE,
)
from dartlab.providers.dart.openapi.corpCode import (
    findCorpCode,
    loadCorpCodes,
    searchCompanies,
)
from dartlab.providers.dart.openapi.dateUtil import defaultEnd, defaultStart, parseDate
from dartlab.providers.dart.openapi.disclosure import (
    CORP_CLASS,
    FILING_TYPES,
    _resolveCorpCode,
    companyInfo,
    listFilings,
)
from dartlab.providers.dart.openapi.saver import (
    enrichFinance,
    enrichReport,
)
from dartlab.providers.dart.openapi.saver import (
    save as _saveFile,
)

# 사업보고서 주요정보 29개 + 주요사항보고 27개 = 56개 카테고리
_REPORT_ENDPOINTS: dict[str, str] = {
    # ── 사업보고서 주요정보 (정기보고서) ──
    "증자감자": "irdsSttus",
    "배당": "alotMatter",
    "자기주식": "tesstkAcqsDspsSttus",
    "최대주주": "hyslrSttus",
    "최대주주변동": "hyslrChgSttus",
    "소액주주": "mrhlSttus",
    "임원": "exctvSttus",
    "직원": "empSttus",
    "이사회임원개인보수": "hmvAuditIndvdlBySttus",
    "이사회임원전체보수": "hmvAuditAllSttus",
    "개인별보수": "indvdlByPay",
    "타법인출자": "otrCprInvstmntSttus",
    "대주주지분변동": "eleStockIstySttus",
    # 추가 보고서 (미등기임원, 채무증권, 감사, 주식총수 등)
    "미등기임원보수": "unrstExctvMendngSttus",
    "주식총수": "stockTotqySttus",
    "회계감사인": "accnutAdtorNmNdAdtOpinion",
    "감사용역체결": "adtServcCnclsSttus",
    "감사비감사계약": "accnutAdtorNonAdtServcCnclsSttus",
    "사외이사변동": "outcmpnyDrctrNdChangeSttus",
    "회사채미상환": "cprndNrdmpBlce",
    "단기사채미상환": "srtpdPsndbtNrdmpBlce",
    "기업어음미상환": "entrprsBilScritsNrdmpBlce",
    "채무증권발행실적": "detScritsIsuAcmslt",
    "조건부자본증권미상환": "cndlCaplScritsNrdmpBlce",
    "신종자본증권미상환": "newCaplScritsNrdmpBlce",
    "공모자금용도": "prvsrpCptalUseDtls",
    "공모자금사용": "pssrpCptalUseDtls",
    "이사감사보수총회인정": "drctrAdtAllMendngSttusGmtsckConfmAmount",
    "이사감사보수지급형태": "drctrAdtAllMendngSttusMendngPymntamtTyCl",
    # ── 주요사항보고 ──
    "부도": "dfOcr",
    "영업정지": "bsnsSspd",
    "회생절차개시": "crtRcvBg",
    "해산사유": "dsRsn",
    "유상증자결정": "piicDecsn",
    "무상증자결정": "fricDecsn",
    "유무상증자결정": "crtskcrtDecsn",
    "감자결정": "crcaDecsn",
    "자기주식취득결정": "tesstkAcqsDecsn",
    "자기주식처분결정": "tesstkDspsDecsn",
    "합병결정": "mrgDecsn",
    "분할결정": "divDecsn",
    "주식교환이전결정": "stkExtrDecsn",
    "사업양도결정": "bsnTrfDecsn",
    "사업양수결정": "bsnInhDecsn",
    "타법인주식양도결정": "otcprStkInvscDecsn",
    "타법인주식양수결정": "otcprStkInvscrInhDecsn",
    "전환사채발행결정": "cvbdIsDecsn",
    "신주인수권부사채발행결정": "bdwtIsDecsn",
    "교환사채발행결정": "exbdIsDecsn",
    "채권관리절차개시": "bnkMngtPcbg",
    "채권관리절차중단": "bnkMngtPcsp",
    "조건부자본증권발행결정": "wdCocobdIsDecsn",
    "해외상장결정": "ovLstDecsn",
    "해외상장폐지결정": "ovDlstDecsn",
    "해외상장": "ovLst",
    "해외상장폐지": "ovDlst",
}

# 정기보고서 전체 28개 카테고리 (saveReport 기본값)
_PERIODIC_REPORT_CATEGORIES: list[str] = [
    # eddmpython 기본 22개
    "배당",
    "직원",
    "임원",
    "최대주주",
    "최대주주변동",
    "소액주주",
    "자기주식",
    "증자감자",
    "이사회임원전체보수",
    "이사회임원개인보수",
    "개인별보수",
    "타법인출자",
    "주식총수",
    "회계감사인",
    "감사용역체결",
    "감사비감사계약",
    "사외이사변동",
    "미등기임원보수",
    "회사채미상환",
    "단기사채미상환",
    "공모자금용도",
    "공모자금사용",
    # 추가 정기보고서 6개
    "대주주지분변동",
    "기업어음미상환",
    "신종자본증권미상환",
    "채무증권발행실적",
    "이사감사보수총회인정",
    "이사감사보수지급형태",
]


def _dataPath(category: str, stockCode: str) -> Path:
    """dartlab 데이터 디렉토리 내 저장 경로.

    {dataDir}/dart/{category}/{stockCode}.parquet
    """
    subDir = DATA_RELEASES.get(category, {}).get("dir", f"dart/{category}")
    dest = Path(_dartlabConfig.dataDir) / subDir / f"{stockCode}.parquet"
    dest.parent.mkdir(parents=True, exist_ok=True)
    return dest


# ── 내부 유틸 ──────────────────────────────────────────────


def _buildPeriods(
    start: int,
    end: int | None,
    quarterly: bool,
    quarter: str,
) -> list[tuple[str, str]]:
    """(bsnsYear, reprtCode) 리스트 생성."""
    endYear = end if end is not None else start
    if endYear < start:
        raise ValueError(f"start({start}) > end({endYear}): 시작 연도가 종료 연도보다 큽니다")
    if start < 2015:
        raise ValueError(f"start={start}: OpenDART는 2015년 이후 데이터만 제공합니다")

    years = range(start, endYear + 1)
    quarters = ["Q1", "Q2", "Q3", "Q4"] if quarterly else [quarter]

    periods = []
    for y in years:
        for q in quarters:
            code = _QUARTER_TO_CODE.get(q, "11011")
            periods.append((str(y), code))
    return periods


def _periodLabel(bsnsYear: str, reprtCode: str) -> str:
    label = _CODE_TO_LABEL.get(reprtCode, reprtCode)
    return f"{bsnsYear} {label}"


def _maybeValidateFinance(df: pl.DataFrame) -> None:
    """opt-in finance schema 검증 — DARTLAB_VALIDATE_SCHEMA=1 일 때만 동작.

    Capabilities:
        production path 의 데이터 drift 차단 — DART API 응답 schema 가 silent
        하게 바뀌면 즉시 warning 로그. 환경변수 OFF (기본) 면 0 비용.
    Args:
        df: Dart.finance 결과 frame.
    Returns:
        None. validate 실패 시 logger.warning, raise 안 함 (production 무중단).
    Example:
        >>> _maybeValidateFinance(df)  # env OFF → no-op
        >>> import os; os.environ['DARTLAB_VALIDATE_SCHEMA'] = '1'
        >>> _maybeValidateFinance(df)  # schema 위반 시 logger.warning
    Guide:
        CI / dev 에서 ON (catch drift), production wheel 사용자는 default OFF.
    SeeAlso:
        dartlab.core.schemas.FinanceSchema.
    Requires:
        dev 환경 — pandera[polars] 설치. production wheel 은 default OFF 라 무영향.
    AIContext:
        본 SSOT 통합 PR 의 데이터 회귀 차단 1 차 방어선.
    Raises:
        없음. validate 실패는 warning 으로만 보고.
    """
    import os

    if not os.environ.get("DARTLAB_VALIDATE_SCHEMA"):
        return
    if df is None or df.is_empty():
        return
    try:
        from dartlab.core.logger import getLogger
        from dartlab.core.schemas import FinanceSchema

        FinanceSchema.validate(df, lazy=True)
    except ImportError:
        return
    except Exception as exc:  # noqa: BLE001 — schema validation drift는 모든 예외 흡수
        from dartlab.core.logger import getLogger

        getLogger(__name__).warning("FinanceSchema drift: %s", str(exc)[:200])


def _fetchSeries(
    client: DartClient,
    endpoint: str,
    corpCode: str,
    corpName: str,
    periods: list[tuple[str, str]],
    title: str,
    extraParams: dict | None = None,
) -> pl.DataFrame:
    """여러 기간 연속 조회 → concat + rich.progress."""
    from rich.progress import BarColumn, MofNCompleteColumn, Progress, SpinnerColumn, TextColumn

    from dartlab.core.logger import getConsole

    frames: list[pl.DataFrame] = []

    progress = Progress(
        SpinnerColumn(),
        TextColumn("[bold blue]{task.description}"),
        BarColumn(),
        MofNCompleteColumn(),
        console=getConsole(),
    )
    _task = progress.add_task(f"{title} | {corpName}", total=len(periods))
    with progress:
        for bsnsYear, reprtCode in periods:
            progress.update(_task, description=f"{title} | {corpName} | {_periodLabel(bsnsYear, reprtCode)}")

            params: dict[str, str] = {
                "corp_code": corpCode,
                "bsns_year": bsnsYear,
                "reprt_code": reprtCode,
            }
            if extraParams:
                params.update(extraParams)

            df = client.getDf(f"{endpoint}.json", params)
            if df.height > 0:
                frames.append(df)
            progress.advance(_task)

    if not frames:
        return pl.DataFrame()
    return pl.concat(frames, how="diagonal_relaxed")


class Dart:
    """OpenDART API 통합 클라이언트.

    Parameters
    ----------
    keys : str | list[str] | None
        API 키. 문자열 1개 또는 리스트(로테이션).
        None이면 환경변수 자동 탐색.

    Examples
    --------
    >>> d = Dart()
    >>> d = Dart("your_api_key")
    >>> d = Dart(["key1", "key2", "key3"])
    """

    def __init__(self, keys: str | list[str] | None = None):
        try:
            if isinstance(keys, list):
                self._client = DartClient(apiKeys=keys)
            elif isinstance(keys, str):
                self._client = DartClient(apiKey=keys)
            else:
                self._client = DartClient()
        except ValueError:
            # DART 키 없음 → 원격 서버 프록시 fallback
            from dartlab.providers.dart.openapi.remote import RemoteDartClient

            self._client = RemoteDartClient()

    # ── 공시 검색 ──────────────────────────────────────────

    def filings(
        self,
        corp: str | None = None,
        start: str | datetime | date | None = None,
        end: str | datetime | date | None = None,
        *,
        type: str | None = None,
        final: bool = False,
        market: Literal["Y", "K", "N", "E"] | None = None,
    ) -> pl.DataFrame:
        """OpenDART 공시 목록 조회 — corp/start/end/type/final/market 다축 필터.

        Capabilities:
            - corp: 종목코드 6 / 회사명 / corp_code 8 자리 자동 인식 (resolver 위임).
            - start/end: str/datetime/date 유연 입력. None → start=1년전, end=오늘.
            - type 공시 유형 1 자 코드: A 정기 / B 주요사항 / C 발행 / D 지분 / E 기타 등.
            - market 법인구분: Y/K/N/E.
            - final=True → 최종본만, 정정 제외.

        Args:
            corp: 기업 식별자 또는 None (전체 시장).
            start: 시작일 (str/datetime/date) 또는 None.
            end: 종료일 또는 None.
            type: 공시 유형 코드 또는 None.
            final: 최종본만. 기본 False.
            market: 법인구분 또는 None.

        Returns:
            pl.DataFrame — OpenDART list endpoint 원본 컬럼.

        Example:
            >>> # d.filings("삼성전자", "2024-01", "2024-06")

        Guide:
            - "삼성전자 정기공시" → ``d.filings("삼성전자", type="A")``.
            - "특정 일자 시장 전체" → ``d.filings(start="2024-03-14")``.
            - "유가증권 시장 정기공시" → ``type="A", market="Y"``.

        SeeAlso:
            - ``Dart.search`` — 회사명 검색.
            - ``Dart.corpCode`` — 코드 변환.
            - ``DartCompany.filings`` — 종목 한정 wrapper.
            - ``listFilings`` (모듈) — 본 함수 본체.

        Requires:
            - polars — DataFrame.
            - dartlab.providers.dart.openapi.client — _client (HTTP).
            - DART_API_KEY 환경변수.

        AIContext:
            AI 가 "최근 공시 X" 질문 처리 시 호출. corp 없이 전체 시장 호출 → 결과 큼, AI 가
            limit/필터 추가 권장. type 코드 자동 매핑 (사용자 "정기" → type="A").

        LLM Specifications:
            AntiPatterns:
                - DART_API_KEY 미설정 → ValueError.
                - rate limit (20K/일) 초과 → 차단.
                - start > end → 빈 결과.
                - corp 가 lookup 실패 → 전체 시장 fallback.
            OutputSchema:
                - OpenDART filings 원본 컬럼 (snake_case).
            Prerequisites:
                - DART_API_KEY.
            Freshness:
                - 호출 시점 OpenDART 데이터.
            Dataflow:
                - OpenDART API → 본 함수 → caller.
            TargetMarkets:
                - KR (DART) 한정.

        Raises:
            없음.
        """
        startDate = parseDate(start, asEnd=False) or defaultStart()
        endDate = parseDate(end, asEnd=True) or defaultEnd()

        return listFilings(
            self._client,
            corp=corp,
            start=startDate,
            end=endDate,
            filingType=type,
            finalOnly=final,
            corpClass=market,
        )

    # ── 기업 정보 ──────────────────────────────────────────

    def company(self, corp: str) -> dict[str, str]:
        """기업 개황 조회.

        Examples
        --------
        >>> d.company("삼성전자")
        >>> d.company("005930")

        Args:
            corp: 인자.

        Raises:
            없음.

        Returns:
            dict — 기업 개황 정보 (corpCode/corpName/stockName/stockCode 등).

        LLM Specifications:
            AntiPatterns:
                - DART_API_KEY 미설정 → RuntimeError. caller 사전 검증.
                - 회사명 부분 매치 X — corp 인자는 정확명 또는 stockCode.
            OutputSchema:
                - dict[str, str] — DART openAPI company endpoint 응답 정규화.
            Prerequisites:
                - 인터넷 + DART_API_KEY + corp (회사명 또는 stockCode).
            Freshness:
                - DART OpenAPI 실시간.
            Dataflow:
                - corp → resolveCorpCode → DART API company → 정규화 dict.
            TargetMarkets:
                - KR (DART) 한정.
        """
        return companyInfo(self._client, corp)

    # ── 회사 검색 ──────────────────────────────────────────

    def search(
        self,
        query: str,
        listed: bool = False,
        *,
        limit: int | None = None,
    ) -> pl.DataFrame:
        """OpenDART 회사명 검색 — substring 매칭 (corpCode + name + ticker).

        Capabilities:
            - ``searchCompanies`` wrapper — corp_code parquet 의 회사명/종목코드 검색.
            - listed=True → 종목코드 보유 회사 (상장사) 만.
            - limit=None → 전체.

        Args:
            query: 검색어 (한국어/영문/숫자).
            listed: 상장사만 필터. 기본 False.
            limit: 최대 row 수. None → 무제한.

        Returns:
            pl.DataFrame — 매칭된 회사 메타 (corp_code/corp_name/stock_code/modify_date).

        Example:
            >>> # d.search("삼성", limit=10)
            >>> # d.search("LG", listed=True)

        Guide:
            - "삼성 들어가는 모든 회사" → ``d.search("삼성")``.
            - "상장사만" → ``listed=True``.
            - "단일 종목코드 찾기" → ``d.corpCode("...")`` 사용.

        SeeAlso:
            - ``Dart.corpCode`` — 단일 매칭 lookup.
            - ``Dart.corpCodes`` — 전체 corp_code 테이블.
            - ``searchCompanies`` (모듈 private) — 본 함수 본체.

        Requires:
            - polars — DataFrame.
            - corp_code parquet (OpenDART 의 corpCode.zip 파싱).

        AIContext:
            "회사 검색" / "회사명 lookup" 질문 entry. listed=True 가 default 권장 (비상장사
            제외).

        LLM Specifications:
            AntiPatterns:
                - query 가 매우 짧음 (1 자) → 과도 매칭 (수천 row).
                - corp_code parquet 미빌드 → 빈 결과.
            OutputSchema:
                - pl.DataFrame — corp_code/corp_name/stock_code/modify_date.
            Prerequisites:
                - corp_code parquet.
            Freshness:
                - parquet 갱신 시점.
            Dataflow:
                - OpenDART corpCode.zip → parquet → 본 함수 → AI.
            TargetMarkets:
                - KR (DART) 한정.

        Raises:
            없음.
        """
        return searchCompanies(self._client, query, listedOnly=listed, limit=limit)

    # ── corp_code ──────────────────────────────────────────

    def corpCode(self, query: str) -> str | None:
        """종목코드 / 회사명 → 8 자리 corp_code 1 매칭 변환.

        Capabilities:
            - ``findCorpCode`` wrapper — corp_code parquet 에서 query 1 매칭 lookup.
            - 매칭 없음 → None.
            - 다중 매칭 가능성 — findCorpCode 의 best match 1 개만.

        Args:
            query: 종목코드 6 / 회사명 (한국어/영문).

        Returns:
            str | None — 8 자리 corp_code 또는 매칭 없음 시 None.

        Example:
            >>> # d.corpCode("005930")  # "00126380"
            >>> # d.corpCode("삼성전자")  # "00126380"

        Guide:
            - "종목코드 → corp_code" → 본 함수.
            - "여러 매칭" → ``Dart.search``.
            - 신규 회사 (parquet 갱신 안 됨) → ``corpCodes(refresh=True)``.

        SeeAlso:
            - ``Dart.search`` — 다중 매칭.
            - ``Dart.corpCodes`` — 전체 테이블.
            - ``findCorpCode`` (모듈) — 본 함수 본체.

        Requires:
            - polars — DataFrame (간접).
            - corp_code parquet.

        AIContext:
            AI 가 "종목코드 → corp_code" 내부 변환 시 호출. None 시 회사명 typo / 비상장사
            의심.

        LLM Specifications:
            AntiPatterns:
                - corp_code parquet 신규 회사 누락 (24 h 캐시) → refresh 필요.
                - 동명이인 회사 → best match 1 개만 (other 회사는 search 사용).
            OutputSchema:
                - 1 str (8 자리) 또는 None.
            Prerequisites:
                - corp_code parquet.
            Freshness:
                - parquet 갱신 시점 (24 h 캐시).
            Dataflow:
                - corp_code parquet → findCorpCode → 본 함수 → caller.
            TargetMarkets:
                - KR (DART) 한정.

        Raises:
            없음.
        """
        return findCorpCode(self._client, query)

    def corpCodes(self, refresh: bool = False) -> pl.DataFrame:
        """corp_code 전체 목록 (11만+건, 24시간 캐시).

        Args:
            refresh: 인자.

        Raises:
            없음.

        Example:
            >>> corpCodes(...)

        Returns:
            pl.DataFrame — DART OpenAPI 응답 정규화 결과.

        LLM Specifications:
            AntiPatterns:
                - DART_API_KEY 미설정 → RuntimeError.
                - 일 호출 한도 (1만/일) 초과 시 빈 응답.
                - 전체 corp_code (~11만) 그대로 LLM 노출 → 토큰 폭증. corpCode lookup 후 filter 의무.
            OutputSchema:
                - pl.DataFrame — endpoint 별 정규화 컬럼.
            Prerequisites:
                - 인터넷 + DART_API_KEY 환경변수.
            Freshness:
                - DART OpenAPI 실시간 (분 단위).
            Dataflow:
                - 사용자 인자 → DartClient request → DART API → JSON 정규화 → 본 함수.
            TargetMarkets:
                - KR (DART) 한정.
        """
        return loadCorpCodes(self._client, refresh=refresh)

    # ── 재무제표 ───────────────────────────────────────────

    def finstate(
        self,
        corp: str,
        start: str | int | None = None,
        *,
        end: int | None = None,
        q: int | None = None,
        consolidated: bool = True,
        full: bool = False,
    ) -> pl.DataFrame:
        """OpenDART 재무제표 조회 — 단건 또는 연속 기간 (연간/분기 자동).

        Capabilities:
            - endpoint 자동 선택: full=True → ``fnlttSinglAcntAll`` (전체 계정) / False → ``fnlttSinglAcnt`` (주요 계정만).
            - q 분기 선택: None=연간 (사업보고서), 0=Q1~Q4 전부, 1~4=특정 분기.
            - start~end 범위 → 연속 조회 + 자동 concat.
            - consolidated: True=연결 (CFS), False=별도 (OFS) — full=True 시만 적용.
            - corp 입력 3 종 (종목코드/회사명/corp_code) 자동 인식.

        Args:
            corp: 종목코드 6 / 회사명 / corp_code 8.
            start: 사업연도 (int 또는 str). None → 최근 연도.
            end: 종료 연도 (int). None → start 만.
            q: 분기 선택. None=연간, 0~4.
            consolidated: True=CFS, False=OFS. full=True 시만 의미.
            full: True → 전체 계정. False → 주요 계정만.

        Returns:
            pl.DataFrame — OpenDART finstate 원본 컬럼 (account_id, account_nm, thstrm_amount 등).

        Example:
            >>> # d.finstate("삼성전자")  # 최근 연간
            >>> # d.finstate("삼성전자", 2020, end=2024, q=0)  # 분기별 20건

        Guide:
            - "최근 연간 재무제표" → ``d.finstate(corp)``.
            - "5 년 시계열 (분기)" → ``start=2020, end=2024, q=0``.
            - "별도 전체 계정" → ``consolidated=False, full=True``.

        SeeAlso:
            - ``Dart.finstateMulti`` — 여러 회사 동시.
            - ``Dart.xbrlTaxonomy`` — XBRL 분류체계.
            - ``DartCompany.finance`` — 종목 한정 wrapper.
            - ``Dart.report`` — 정기보고서 metadata.

        Requires:
            - polars + DART_API_KEY + dartlab.providers.dart.openapi.client.

        AIContext:
            AI 가 "이 회사 재무제표" / "5 년 BS/IS/CF" 질문 entry. full=True 시 row 수 많음
            (수백 항목). 분기별 연속은 OpenDART rate limit 주의 (20K/일).

        LLM Specifications:
            AntiPatterns:
                - corp 가 lookup 실패 → ValueError (resolveCorpCode 내부).
                - q=0 + 연속 기간 → 호출 N × 4 → rate limit 빠르게 소진.
                - start > end → 빈 결과.
                - 사업연도가 최신 (예 2025) 인데 OpenDART 미등록 → 빈 결과.
            OutputSchema:
                - pl.DataFrame — OpenDART finstate 원본 컬럼.
            Prerequisites:
                - DART_API_KEY. corp_code 매핑 가능.
            Freshness:
                - 호출 시점 OpenDART 데이터.
            Dataflow:
                - OpenDART API → 본 함수 → caller (또는 DartCompany 경유).
            TargetMarkets:
                - KR (DART) 한정.

        Raises:
            없음.
        """
        corpCodeStr = _resolveCorpCode(self._client, corp)
        startYear = int(start) if start else datetime.now().year - 1
        endpoint = "fnlttSinglAcntAll" if full else "fnlttSinglAcnt"

        extraParams: dict[str, str] = {}
        if full:
            extraParams["fs_div"] = "CFS" if consolidated else "OFS"

        quarterly, quarter = _resolveQ(q, hasRange=end is not None)
        periods = _buildPeriods(startYear, end, quarterly, quarter)

        if len(periods) == 1:
            bsnsYear, reprtCode = periods[0]
            params: dict[str, str] = {
                "corp_code": corpCodeStr,
                "bsns_year": bsnsYear,
                "reprt_code": reprtCode,
                **extraParams,
            }
            df = self._client.getDf(f"{endpoint}.json", params)
            _maybeValidateFinance(df)
            return df

        corpName = self._resolveCorpName(corp)
        df = _fetchSeries(
            self._client,
            endpoint,
            corpCodeStr,
            corpName,
            periods,
            "재무제표",
            extraParams,
        )
        _maybeValidateFinance(df)
        return df

    def finstateMulti(
        self,
        corps: list[str],
        year: str | int | None = None,
        *,
        q: int | None = None,
    ) -> pl.DataFrame:
        """다중기업 재무제표 비교 (한 번의 API 호출).

        Parameters
        ----------
        corps : list[str]
            기업 리스트 (종목코드/회사명/corp_code 혼용 가능).
        year : str | int | None
            사업연도. None이면 최근 연도.
        q : int | None
            분기 선택. None=연간, 1=Q1, 2=Q2, 3=Q3, 4=사업보고서.

        Examples
        --------
        >>> d.finstateMulti(["삼성전자", "SK하이닉스"], 2023)
        >>> d.finstateMulti(["삼성전자", "SK하이닉스"], 2023, q=2)

        Raises:
            없음.

        Args:
            corps: 회사명 또는 stockCode 리스트.
            year: 사업연도 (예 2024). None 이면 직전 연도.
            q: 분기 (1~4). None 이면 4분기 (사업보고서).

        Returns:
            pl.DataFrame — DART OpenAPI 응답 정규화 결과.

        SeeAlso:
            - ``DartClient`` — 본 함수의 HTTP backend.
            - ``Dart`` (facade) — 사용자 진입.

        Requires:
            - dartlab
            - datetime
            - io
            - polars
            - zipfile

        Capabilities:
            - DART OpenAPI endpoint 위임 + 응답 정규화. 회사 식별자 자동 매핑 (corpCode resolve).
              일 호출 한도 (개인 1만/일) 내 호출.

        Guide:
            - "DART OpenAPI 호출" → 본 메서드. 사용자 facade 는 ``Dart()``.

        AIContext:
            internal DART API client — AI 가 직접 호출 시 rate limit 주의.

        LLM Specifications:
            AntiPatterns:
                - DART_API_KEY 미설정 → RuntimeError.
                - 일 호출 한도 초과 시 빈 응답.
                - 회사명 부분 매치 X — 정확명 또는 stockCode/corpCode.
            OutputSchema:
                - pl.DataFrame 또는 dict — endpoint 별 정규화.
            Prerequisites:
                - 인터넷 + DART_API_KEY 환경변수 + 회사 식별자.
            Freshness:
                - DART OpenAPI 실시간 (분 단위).
            Dataflow:
                - 사용자 인자 → DartClient → DART API → JSON → 본 함수.
            TargetMarkets:
                - KR (DART) 한정.
        """
        corpCodes = [_resolveCorpCode(self._client, c) for c in corps]
        bsnsYear = str(year) if year else str(datetime.now().year - 1)
        _, quarter = _resolveQ(q, hasRange=False)
        reprtCode = _QUARTER_TO_CODE.get(quarter, "11011")

        return self._client.getDf(
            "fnlttMultiAcnt.json",
            {
                "corp_code": ",".join(corpCodes),
                "bsns_year": bsnsYear,
                "reprt_code": reprtCode,
            },
        )

    def xbrlTaxonomy(
        self,
        category: str = "BS1",
    ) -> pl.DataFrame:
        """XBRL 택사노미 (표준 계정 체계).

        Parameters
        ----------
        category : str
            sj_div 코드. 사용 가능:
            BS1/BS2/BS3 (재무상태표), IS1/IS2/IS3 (손익계산서),
            CIS1/CIS2 (포괄손익), CF1/CF2/CF3 (현금흐름).

        Examples
        --------
        >>> d.xbrlTaxonomy("BS1")   # 재무상태표
        >>> d.xbrlTaxonomy("IS1")   # 손익계산서
        >>> d.xbrlTaxonomy("CF1")   # 현금흐름표

        Raises:
            없음.

        Args:
            category: report 카테고리 (배당/주식총수/자기주식 등).

        Returns:
            pl.DataFrame — DART OpenAPI 응답 정규화 결과.

        LLM Specifications:
            AntiPatterns:
                - DART_API_KEY 미설정 → RuntimeError.
                - 일 호출 한도 (1만/일) 초과 시 빈 응답.
                - 전체 corp_code (~11만) 그대로 LLM 노출 → 토큰 폭증. corpCode lookup 후 filter 의무.
            OutputSchema:
                - pl.DataFrame — endpoint 별 정규화 컬럼.
            Prerequisites:
                - 인터넷 + DART_API_KEY 환경변수.
            Freshness:
                - DART OpenAPI 실시간 (분 단위).
            Dataflow:
                - 사용자 인자 → DartClient request → DART API → JSON 정규화 → 본 함수.
            TargetMarkets:
                - KR (DART) 한정.
        """
        return self._client.getDf(
            "xbrlTaxonomy.json",
            {"sj_div": category},
        )

    # ── 보고서 API (44개 + 주요사항 28개) ──────────────────

    def report(
        self,
        corp: str,
        reportType: str,
        start: str | int | None = None,
        *,
        end: int | None = None,
        q: int | None = None,
    ) -> pl.DataFrame:
        """사업보고서 주요정보 API — 28 reportType × 단건/연속 기간 자동.

        Capabilities:
            - ``_REPORT_ENDPOINTS`` lookup 으로 reportType → endpoint 변환.
            - 알 수 없는 reportType → ValueError + 사용 가능 목록.
            - start~end 연속 → 자동 concat.
            - q=0 → Q1~Q4 전체. q=1~4 → 특정 분기. q=None → 연간 (사업보고서).
            - 단일 period → single GET, 다중 → ``_fetchSeries`` (rate limit 보호).

        Args:
            corp: 종목코드 / 회사명 / corp_code.
            reportType: 28 종 중 1 (배당/직원/임원/...). ``Dart.reportTypes()`` 로 확인.
            start: 사업연도. None → 최근 연도.
            end: 종료 연도. None → start 만.
            q: 분기 선택. None=연간, 0~4.

        Raises:
            ValueError: reportType 이 28 종 외.

        Returns:
            pl.DataFrame — reportType 별 컬럼 가변 (DART API 원본).

        Example:
            >>> # d.report("삼성전자", "배당", 2020, end=2024, q=2)  # 5 년 Q2

        Guide:
            - "배당 5 년 연간" → ``d.report(corp, "배당", 2020, end=2024)``.
            - "임원 분기별 20 건" → ``q=0``.
            - "reportType 목록" → ``Dart.reportTypes()`` (정적 메서드).

        SeeAlso:
            - ``Dart.reportTypes`` (정적) — 28 종 목록.
            - ``DartCompany.report`` — 종목 한정 wrapper.
            - ``Dart.finstate`` — 재무제표 (별도 API).
            - ``_REPORT_ENDPOINTS`` (모듈) — reportType ↔ endpoint 매핑.

        Requires:
            - polars + DART_API_KEY + dartlab.providers.dart.openapi.client.

        AIContext:
            AI 가 "배당 / 직원 / 임원 / 자기주식 / 감사 등" 카테고리 데이터 질문 entry. 28 종
            카테고리명을 사용자 자연어에 매핑 (예 "배당금" → reportType="배당").

        LLM Specifications:
            AntiPatterns:
                - reportType 영문 표기 사용 (예 "dividend") → ValueError. 한국어만.
                - 신규 회사 (사업보고서 미제출) → 빈 결과.
                - rate limit 초과 → 차단.
            OutputSchema:
                - pl.DataFrame — DART API 원본 컬럼 (reportType 마다 다름).
            Prerequisites:
                - DART_API_KEY + corp_code 매핑.
            Freshness:
                - 호출 시점 OpenDART 데이터.
            Dataflow:
                - OpenDART API → 본 함수 → caller.
            TargetMarkets:
                - KR (DART) 한정.
        """
        corpCodeStr = _resolveCorpCode(self._client, corp)
        startYear = int(start) if start else datetime.now().year - 1

        endpoint = _REPORT_ENDPOINTS.get(reportType)
        if endpoint is None:
            available = ", ".join(sorted(_REPORT_ENDPOINTS.keys()))
            raise ValueError(f"'{reportType}'은 알 수 없는 보고서 유형입니다.\n사용 가능: {available}")

        quarterly, quarter = _resolveQ(q, hasRange=end is not None)
        periods = _buildPeriods(startYear, end, quarterly, quarter)

        if len(periods) == 1:
            bsnsYear, reprtCode = periods[0]
            return self._client.getDf(
                f"{endpoint}.json",
                {
                    "corp_code": corpCodeStr,
                    "bsns_year": bsnsYear,
                    "reprt_code": reprtCode,
                },
            )

        corpName = self._resolveCorpName(corp)
        return _fetchSeries(
            self._client,
            endpoint,
            corpCodeStr,
            corpName,
            periods,
            reportType,
        )

    # ── 지분공시 ───────────────────────────────────────────

    def majorShareholders(self, corp: str) -> pl.DataFrame:
        """대량보유 상황보고 (5% 이상).

        Examples
        --------
        >>> d.majorShareholders("삼성전자")

        Args:
            corp: 인자.

        Raises:
            없음.

        Returns:
            pl.DataFrame — DART OpenAPI 응답 정규화 결과.

        SeeAlso:
            - ``DartClient`` — 본 함수의 HTTP backend.
            - ``Dart`` (facade) — 사용자 진입.

        Requires:
            - dartlab
            - datetime
            - io
            - polars
            - zipfile

        Capabilities:
            - DART OpenAPI endpoint 위임 + 응답 정규화. 회사 식별자 자동 매핑 (corpCode resolve).
              일 호출 한도 (개인 1만/일) 내 호출.

        Guide:
            - "DART OpenAPI 호출" → 본 메서드. 사용자 facade 는 ``Dart()``.

        AIContext:
            internal DART API client — AI 가 직접 호출 시 rate limit 주의.

        LLM Specifications:
            AntiPatterns:
                - DART_API_KEY 미설정 → RuntimeError.
                - 일 호출 한도 초과 시 빈 응답.
                - 회사명 부분 매치 X — 정확명 또는 stockCode/corpCode.
            OutputSchema:
                - pl.DataFrame 또는 dict — endpoint 별 정규화.
            Prerequisites:
                - 인터넷 + DART_API_KEY 환경변수 + 회사 식별자.
            Freshness:
                - DART OpenAPI 실시간 (분 단위).
            Dataflow:
                - 사용자 인자 → DartClient → DART API → JSON → 본 함수.
            TargetMarkets:
                - KR (DART) 한정.
        """
        corpCodeStr = _resolveCorpCode(self._client, corp)
        return self._client.getDf("majorstock.json", {"corp_code": corpCodeStr})

    def executiveShares(self, corp: str) -> pl.DataFrame:
        """임원·주요주주 소유보고.

        Examples
        --------
        >>> d.executiveShares("삼성전자")

        Args:
            corp: 인자.

        Raises:
            없음.

        Returns:
            pl.DataFrame — DART OpenAPI 응답 정규화 결과.

        SeeAlso:
            - ``DartClient`` — 본 함수의 HTTP backend.
            - ``Dart`` (facade) — 사용자 진입.

        Requires:
            - dartlab
            - datetime
            - io
            - polars
            - zipfile

        Capabilities:
            - DART OpenAPI endpoint 위임 + 응답 정규화. 회사 식별자 자동 매핑 (corpCode resolve).
              일 호출 한도 (개인 1만/일) 내 호출.

        Guide:
            - "DART OpenAPI 호출" → 본 메서드. 사용자 facade 는 ``Dart()``.

        AIContext:
            internal DART API client — AI 가 직접 호출 시 rate limit 주의.

        LLM Specifications:
            AntiPatterns:
                - DART_API_KEY 미설정 → RuntimeError.
                - 일 호출 한도 초과 시 빈 응답.
                - 회사명 부분 매치 X — 정확명 또는 stockCode/corpCode.
            OutputSchema:
                - pl.DataFrame 또는 dict — endpoint 별 정규화.
            Prerequisites:
                - 인터넷 + DART_API_KEY 환경변수 + 회사 식별자.
            Freshness:
                - DART OpenAPI 실시간 (분 단위).
            Dataflow:
                - 사용자 인자 → DartClient → DART API → JSON → 본 함수.
            TargetMarkets:
                - KR (DART) 한정.
        """
        corpCodeStr = _resolveCorpCode(self._client, corp)
        return self._client.getDf("elestock.json", {"corp_code": corpCodeStr})

    # ── 공시 서류 ──────────────────────────────────────────

    def document(
        self,
        rceptNo: str,
        savePath: str | Path | None = None,
    ) -> Path:
        """공시서류 원본 다운로드 (ZIP).

        Parameters
        ----------
        rceptNo : str
            접수번호 (filings()의 rcept_no 컬럼).
        savePath : str | Path | None
            저장 경로. None이면 현재 디렉토리에 {rceptNo}.zip.

        Returns
        -------
        Path
            저장된 파일 경로.

        Examples
        --------
        >>> path = d.document("20240312000736")
        >>> path = d.document("20240312000736", "~/downloads/samsung.zip")

        Raises:
            없음.

        Args:
            rceptNo: DART 접수번호 (14 자리 또는 그 형식).
            savePath: 저장 경로. None 이면 메모리만.

        Returns:
            Path — 저장된 파일 경로.

        SeeAlso:
            - ``DartClient`` — 본 함수의 HTTP backend.
            - ``Dart`` (facade) — 사용자 진입.

        Requires:
            - dartlab
            - datetime
            - io
            - polars
            - zipfile

        Capabilities:
            - DART OpenAPI endpoint 위임 + 응답 정규화. 회사 식별자 자동 매핑 (corpCode resolve).
              일 호출 한도 (개인 1만/일) 내 호출.

        Guide:
            - "DART OpenAPI 호출" → 본 메서드. 사용자 facade 는 ``Dart()``.

        AIContext:
            internal DART API client — AI 가 직접 호출 시 rate limit 주의.

        LLM Specifications:
            AntiPatterns:
                - DART_API_KEY 미설정 → RuntimeError.
                - 일 호출 한도 초과 시 빈 응답.
                - 회사명 부분 매치 X — 정확명 또는 stockCode/corpCode.
            OutputSchema:
                - pl.DataFrame 또는 dict — endpoint 별 정규화.
            Prerequisites:
                - 인터넷 + DART_API_KEY 환경변수 + 회사 식별자.
            Freshness:
                - DART OpenAPI 실시간 (분 단위).
            Dataflow:
                - 사용자 인자 → DartClient → DART API → JSON → 본 함수.
            TargetMarkets:
                - KR (DART) 한정.
        """
        raw = self._client.getBytes("document.xml", {"rcept_no": rceptNo})
        dest = Path(savePath) if savePath else Path(f"{rceptNo}.zip")
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(raw)
        return dest

    def documentText(self, rceptNo: str) -> str:
        """공시서류 원본 텍스트 추출 (ZIP 내 XML/HTML).

        Parameters
        ----------
        rceptNo : str
            접수번호.

        Returns
        -------
        str
            공시서류 본문 (HTML/XML). 가장 큰 파일 선택.

        Examples
        --------
        >>> html = d.documentText("20240312000736")

        Raises:
            없음.

        Args:
            rceptNo: DART 접수번호 (14 자리 또는 그 형식).

        Returns:
            str — DART OpenAPI 응답 텍스트.

        SeeAlso:
            - ``DartClient`` — 본 함수의 HTTP backend.
            - ``Dart`` (facade) — 사용자 진입.

        Requires:
            - dartlab
            - datetime
            - io
            - polars
            - zipfile

        Capabilities:
            - DART OpenAPI endpoint 위임 + 응답 정규화. 회사 식별자 자동 매핑 (corpCode resolve).
              일 호출 한도 (개인 1만/일) 내 호출.

        Guide:
            - "DART OpenAPI 호출" → 본 메서드. 사용자 facade 는 ``Dart()``.

        AIContext:
            internal DART API client — AI 가 직접 호출 시 rate limit 주의.

        LLM Specifications:
            AntiPatterns:
                - DART_API_KEY 미설정 → RuntimeError.
                - 일 호출 한도 초과 시 빈 응답.
                - 회사명 부분 매치 X — 정확명 또는 stockCode/corpCode.
            OutputSchema:
                - pl.DataFrame 또는 dict — endpoint 별 정규화.
            Prerequisites:
                - 인터넷 + DART_API_KEY 환경변수 + 회사 식별자.
            Freshness:
                - DART OpenAPI 실시간 (분 단위).
            Dataflow:
                - 사용자 인자 → DartClient → DART API → JSON → 본 함수.
            TargetMarkets:
                - KR (DART) 한정.
        """
        raw = self._client.getBytes("document.xml", {"rcept_no": rceptNo})
        zf = zipfile.ZipFile(io.BytesIO(raw))

        names = zf.namelist()
        if not names:
            raise ValueError(f"공시서류 ZIP이 비어있습니다: {rceptNo}")
        largest = max(names, key=lambda n: zf.getinfo(n).file_size)
        content = zf.read(largest)

        # 인코딩 시도: euc-kr → utf-8
        for encoding in ("euc-kr", "utf-8", "cp949"):
            try:
                return content.decode(encoding)
            except (UnicodeDecodeError, LookupError):
                continue
        return content.decode("utf-8", errors="replace")

    # ── 유틸 ───────────────────────────────────────────────

    def _resolveCorpName(self, corp: str) -> str:
        """progress bar 표시용 회사명 해석."""
        df = loadCorpCodes(self._client)
        if corp.isdigit() and len(corp) == 6:
            match = df.filter(pl.col("stock_code") == corp)
            if match.height > 0:
                return match["corp_name"][0]
        elif corp.isdigit() and len(corp) == 8:
            match = df.filter(pl.col("corp_code") == corp)
            if match.height > 0:
                return match["corp_name"][0]
        return corp

    @staticmethod
    def filingTypes() -> dict[str, str]:
        """공시유형 코드표.

        Args:
            (인자 자동 생성).

        Raises:
            없음.

        Example:
            >>> filingTypes(...)

        Returns:
            dict — 기업 개황 정보 (corpCode/corpName/stockName/stockCode 등).

        LLM Specifications:
            AntiPatterns:
                - DART_API_KEY 미설정 → RuntimeError. caller 사전 검증.
                - 회사명 부분 매치 X — corp 인자는 정확명 또는 stockCode.
            OutputSchema:
                - dict[str, str] — DART openAPI company endpoint 응답 정규화.
            Prerequisites:
                - 인터넷 + DART_API_KEY + corp (회사명 또는 stockCode).
            Freshness:
                - DART OpenAPI 실시간.
            Dataflow:
                - corp → resolveCorpCode → DART API company → 정규화 dict.
            TargetMarkets:
                - KR (DART) 한정.
        """
        return dict(FILING_TYPES)

    @staticmethod
    def markets() -> dict[str, str]:
        """법인구분 코드표.

        Args:
            (인자 자동 생성).

        Raises:
            없음.

        Example:
            >>> markets(...)

        Returns:
            dict — 기업 개황 정보 (corpCode/corpName/stockName/stockCode 등).

        LLM Specifications:
            AntiPatterns:
                - DART_API_KEY 미설정 → RuntimeError. caller 사전 검증.
                - 회사명 부분 매치 X — corp 인자는 정확명 또는 stockCode.
            OutputSchema:
                - dict[str, str] — DART openAPI company endpoint 응답 정규화.
            Prerequisites:
                - 인터넷 + DART_API_KEY + corp (회사명 또는 stockCode).
            Freshness:
                - DART OpenAPI 실시간.
            Dataflow:
                - corp → resolveCorpCode → DART API company → 정규화 dict.
            TargetMarkets:
                - KR (DART) 한정.
        """
        return dict(CORP_CLASS)

    @staticmethod
    def reportTypes() -> list[str]:
        """사업보고서 API 지원 카테고리.

        Args:
            (인자 자동 생성).

        Raises:
            없음.

        Example:
            >>> reportTypes(...)

        Returns:
            list[str] — 결과 목록.

        LLM Specifications:
            AntiPatterns:
                - DART_API_KEY 미설정 → RuntimeError. caller 사전 검증.
                - 일 호출 한도 초과 시 빈 응답.
                - 결과 추측 X — 정확 인자 값 명시.
            OutputSchema:
                - DART OpenAPI 응답 정규화 (메서드별 다름).
            Prerequisites:
                - 인터넷 + DART_API_KEY 환경변수.
            Freshness:
                - DART OpenAPI 실시간 (분 단위).
            Dataflow:
                - 사용자 인자 → DartClient → DART API → JSON → 본 함수.
            TargetMarkets:
                - KR (DART) 한정.
        """
        return sorted(_REPORT_ENDPOINTS.keys())

    def __call__(self, corp: str) -> DartCompany:
        """회사 객체 생성 — 한글 메서드로 모든 API 접근.

        Examples
        --------
        >>> s = d("삼성전자")
        >>> s.재무(2020, end=2024)
        >>> s.배당(2023)
        >>> s.공시("2024")
        """
        return DartCompany(self, corp)

    def __repr__(self) -> str:
        n = len(self._client._keys)
        return f"Dart(keys={n})"


# ── DartCompany — 회사 프록시 ──────────────────────────────


def _autoEnd() -> int:
    """현재 연도."""
    return datetime.now().year


def _resolveQ(q: int | None, hasRange: bool) -> tuple[bool, str]:
    """q 파라미터 → (quarterly, quarter) 변환.

    q=None + 범위 → Q1~Q4 전부 (quarterly=True)
    q=None + 단건 → annual (quarterly=False)
    q=1    → Q1만
    q=2    → Q2만
    q=3    → Q3만
    q=4    → annual(사업보고서)만
    """
    if q is None:
        if hasRange:
            return True, "annual"  # 범위 → 전분기
        return False, "annual"  # 단건 → 연간 1건

    if q == 0:
        return True, "annual"  # 명시적 전분기

    qMap = {1: "Q1", 2: "Q2", 3: "Q3", 4: "annual"}
    quarter = qMap.get(q)
    if quarter is None:
        raise ValueError(f"q는 0~4 또는 None: q={q}")
    return False, quarter


class DartCompany:
    """회사별 프록시 — 메서드 5개로 전체 API 접근.

    ``d("삼성전자")``로 생성.

    핵심 규칙:
    - start만 주면 end는 자동으로 현재 연도
    - start도 안 주면 최근 1건
    - q 생략 → Q1~Q4 전부 / q=1 → Q1만 / q=2 → Q2만

    Examples
    --------
    >>> s = d("삼성전자")
    >>> s.finance(2022)                # 2022~현재 Q1~Q4 전부
    >>> s.finance(2022, q=4)           # 2022~현재 사업보고서만
    >>> s.report("배당", 2020)         # 2020~현재 Q1~Q4 전부
    >>> s.filings("2024")
    >>> s.info()
    >>> s.shares()
    """

    def __init__(self, dart: Dart, corp: str):
        self._dart = dart
        self._corp = corp

    def report(
        self,
        category: str,
        start: str | int | None = None,
        *,
        end: int | None = None,
        q: int | None = None,
    ) -> pl.DataFrame:
        """사업보고서 56개 카테고리 조회.

        start만 주면 end는 현재 연도까지 자동.

        Parameters
        ----------
        category : str
            카테고리명 (배당, 직원, 임원, 최대주주, 주식총수 등).
        start : int | None
            시작 연도. None이면 최근 1건.
        end : int | None
            종료 연도. None + start있으면 현재 연도.
        q : int | None
            분기 선택. None=Q1~Q4 전부, 1=Q1, 2=Q2, 3=Q3, 4=사업보고서.

        Examples
        --------
        >>> s.report("배당")                  # 최근 1건
        >>> s.report("배당", 2022)            # 2022~현재 Q1~Q4 전부
        >>> s.report("배당", 2022, q=4)       # 2022~현재 사업보고서만
        >>> s.report("배당", 2022, q=2)       # 2022~현재 Q2만
        >>> s.report("직원", 2022, end=2023)  # 2022~2023 Q1~Q4

        Raises:
            없음.

        Args:
            category: report 카테고리 (배당/주식총수/자기주식 등).
            start: 시작 연도 또는 ISO 날짜. None 이면 기본값.
            end: 종료 연도. None 이면 현재 연도.
            q: 분기 (1~4). None 이면 4분기 (사업보고서).

        Returns:
            pl.DataFrame — DART OpenAPI 응답 정규화 결과.

        SeeAlso:
            - ``DartClient`` — 본 함수의 HTTP backend.
            - ``Dart`` (facade) — 사용자 진입.

        Requires:
            - dartlab
            - datetime
            - io
            - polars
            - zipfile

        Capabilities:
            - DART OpenAPI endpoint 위임 + 응답 정규화. 회사 식별자 자동 매핑 (corpCode resolve).
              일 호출 한도 (개인 1만/일) 내 호출.

        Guide:
            - "DART OpenAPI 호출" → 본 메서드. 사용자 facade 는 ``Dart()``.

        AIContext:
            internal DART API client — AI 가 직접 호출 시 rate limit 주의.

        LLM Specifications:
            AntiPatterns:
                - DART_API_KEY 미설정 → RuntimeError.
                - 일 호출 한도 초과 시 빈 응답.
                - 회사명 부분 매치 X — 정확명 또는 stockCode/corpCode.
            OutputSchema:
                - pl.DataFrame 또는 dict — endpoint 별 정규화.
            Prerequisites:
                - 인터넷 + DART_API_KEY 환경변수 + 회사 식별자.
            Freshness:
                - DART OpenAPI 실시간 (분 단위).
            Dataflow:
                - 사용자 인자 → DartClient → DART API → JSON → 본 함수.
            TargetMarkets:
                - KR (DART) 한정.
        """
        if start is not None and end is None:
            end = _autoEnd()
        # DartCompany: start 있으면 기본 전분기 → q=0으로 변환
        effectiveQ = q
        if q is None and start is not None:
            effectiveQ = 0
        return self._dart.report(
            self._corp,
            category,
            start,
            end=end,
            q=effectiveQ,
        )

    def finance(
        self,
        start: str | int | None = None,
        *,
        end: int | None = None,
        q: int | None = None,
        consolidated: bool = True,
        full: bool = False,
    ) -> pl.DataFrame:
        """재무제표 조회.

        start만 주면 end는 현재 연도까지 자동.

        Parameters
        ----------
        start : int | None
            시작 연도. None이면 최근 1건.
        end : int | None
            종료 연도. None + start있으면 현재 연도.
        q : int | None
            분기 선택. None=Q1~Q4 전부, 1=Q1, 2=Q2, 3=Q3, 4=사업보고서.
        full : bool
            True면 전체 계정.
        consolidated : bool
            True=연결, False=별도.

        Examples
        --------
        >>> s.finance()                       # 최근 1건
        >>> s.finance(2022)                   # 2022~현재 Q1~Q4 전부
        >>> s.finance(2022, q=4)              # 2022~현재 사업보고서만
        >>> s.finance(2022, q=2)              # 2022~현재 Q2만
        >>> s.finance(2023, end=2023)         # 2023 Q1~Q4
        >>> s.finance(2020, full=True)        # 전체 계정

        Raises:
            없음.

        Args:
            start: 시작 연도 또는 ISO 날짜. None 이면 기본값.
            end: 종료 연도. None 이면 현재 연도.
            q: 분기 (1~4). None 이면 4분기 (사업보고서).
            consolidated: True 면 연결, False 면 별도.
            full: True 면 모든 계정, False 면 주요 계정만.

        Returns:
            pl.DataFrame — DART OpenAPI 응답 정규화 결과.

        SeeAlso:
            - ``DartClient`` — 본 함수의 HTTP backend.
            - ``Dart`` (facade) — 사용자 진입.

        Requires:
            - dartlab
            - datetime
            - io
            - polars
            - zipfile

        Capabilities:
            - DART OpenAPI endpoint 위임 + 응답 정규화. 회사 식별자 자동 매핑 (corpCode resolve).
              일 호출 한도 (개인 1만/일) 내 호출.

        Guide:
            - "DART OpenAPI 호출" → 본 메서드. 사용자 facade 는 ``Dart()``.

        AIContext:
            internal DART API client — AI 가 직접 호출 시 rate limit 주의.

        LLM Specifications:
            AntiPatterns:
                - DART_API_KEY 미설정 → RuntimeError.
                - 일 호출 한도 초과 시 빈 응답.
                - 회사명 부분 매치 X — 정확명 또는 stockCode/corpCode.
            OutputSchema:
                - pl.DataFrame 또는 dict — endpoint 별 정규화.
            Prerequisites:
                - 인터넷 + DART_API_KEY 환경변수 + 회사 식별자.
            Freshness:
                - DART OpenAPI 실시간 (분 단위).
            Dataflow:
                - 사용자 인자 → DartClient → DART API → JSON → 본 함수.
            TargetMarkets:
                - KR (DART) 한정.
        """
        if start is not None and end is None:
            end = _autoEnd()
        effectiveQ = q
        if q is None and start is not None:
            effectiveQ = 0
        return self._dart.finstate(
            self._corp,
            start,
            end=end,
            q=effectiveQ,
            consolidated=consolidated,
            full=full,
        )

    def filings(
        self,
        start: str | datetime | date | None = None,
        end: str | datetime | date | None = None,
        *,
        type: str | None = None,
        final: bool = False,
    ) -> pl.DataFrame:
        """공시 목록 조회.

        Examples
        --------
        >>> s.filings()                  # 최근 1년
        >>> s.filings("2024")            # 2024년 전체
        >>> s.filings("2024-01", "2024-06")
        >>> s.filings(type="A")          # 정기공시만
        >>> s.filings(final=True)        # 최종보고서만

        Args:
            start: 인자.
            end: 인자.
            type: 인자.
            final: 인자.

        Raises:
            없음.

        Returns:
            pl.DataFrame — DART OpenAPI 응답 정규화 결과.

        LLM Specifications:
            AntiPatterns:
                - DART_API_KEY 미설정 → RuntimeError.
                - 일 호출 한도 (1만/일) 초과 시 빈 응답.
                - 전체 corp_code (~11만) 그대로 LLM 노출 → 토큰 폭증. corpCode lookup 후 filter 의무.
            OutputSchema:
                - pl.DataFrame — endpoint 별 정규화 컬럼.
            Prerequisites:
                - 인터넷 + DART_API_KEY 환경변수.
            Freshness:
                - DART OpenAPI 실시간 (분 단위).
            Dataflow:
                - 사용자 인자 → DartClient request → DART API → JSON 정규화 → 본 함수.
            TargetMarkets:
                - KR (DART) 한정.
        """
        return self._dart.filings(
            self._corp,
            start,
            end,
            type=type,
            final=final,
        )

    def info(self) -> dict[str, str]:
        """기업 개황.

        Examples
        --------
        >>> s.info()

        Args:
            (인자 자동 생성).

        Raises:
            없음.

        Returns:
            dict — 기업 개황 정보 (corpCode/corpName/stockName/stockCode 등).

        LLM Specifications:
            AntiPatterns:
                - DART_API_KEY 미설정 → RuntimeError. caller 사전 검증.
                - 회사명 부분 매치 X — corp 인자는 정확명 또는 stockCode.
            OutputSchema:
                - dict[str, str] — DART openAPI company endpoint 응답 정규화.
            Prerequisites:
                - 인터넷 + DART_API_KEY + corp (회사명 또는 stockCode).
            Freshness:
                - DART OpenAPI 실시간.
            Dataflow:
                - corp → resolveCorpCode → DART API company → 정규화 dict.
            TargetMarkets:
                - KR (DART) 한정.
        """
        return self._dart.company(self._corp)

    def shares(
        self,
        type: Literal["major", "executive", "all"] = "all",
    ) -> pl.DataFrame | dict[str, pl.DataFrame]:
        """지분공시.

        Parameters
        ----------
        type : str
            "major" = 대량보유만, "executive" = 임원만, "all" = 둘 다.

        Examples
        --------
        >>> s.shares()                # {"major": ..., "executive": ...}
        >>> s.shares("major")         # 대량보유만
        >>> s.shares("executive")     # 임원만

        Raises:
            없음.

        Args:
            type: 주주 종류 — "major" / "executive" / "all".

        Returns:
            pl.DataFrame 또는 dict[str, pl.DataFrame] — 주주 종류별 결과.

        SeeAlso:
            - ``DartClient`` — 본 함수의 HTTP backend.
            - ``Dart`` (facade) — 사용자 진입.

        Requires:
            - dartlab
            - datetime
            - io
            - polars
            - zipfile

        Capabilities:
            - DART OpenAPI endpoint 위임 + 응답 정규화. 회사 식별자 자동 매핑 (corpCode resolve).
              일 호출 한도 (개인 1만/일) 내 호출.

        Guide:
            - "DART OpenAPI 호출" → 본 메서드. 사용자 facade 는 ``Dart()``.

        AIContext:
            internal DART API client — AI 가 직접 호출 시 rate limit 주의.

        LLM Specifications:
            AntiPatterns:
                - DART_API_KEY 미설정 → RuntimeError.
                - 일 호출 한도 초과 시 빈 응답.
                - 회사명 부분 매치 X — 정확명 또는 stockCode/corpCode.
            OutputSchema:
                - pl.DataFrame 또는 dict — endpoint 별 정규화.
            Prerequisites:
                - 인터넷 + DART_API_KEY 환경변수 + 회사 식별자.
            Freshness:
                - DART OpenAPI 실시간 (분 단위).
            Dataflow:
                - 사용자 인자 → DartClient → DART API → JSON → 본 함수.
            TargetMarkets:
                - KR (DART) 한정.
        """
        if type == "major":
            return self._dart.majorShareholders(self._corp)
        if type == "executive":
            return self._dart.executiveShares(self._corp)
        return {
            "major": self._dart.majorShareholders(self._corp),
            "executive": self._dart.executiveShares(self._corp),
        }

    def document(
        self,
        rceptNo: str,
        savePath: str | Path | None = None,
    ) -> Path:
        """공시서류 다운로드.

        Examples
        --------
        >>> s.document(filings["rcept_no"][0])

        Args:
            rceptNo: 인자.
            savePath: 인자.

        Raises:
            없음.

        Returns:
            Path — 저장된 파일 경로.

        LLM Specifications:
            AntiPatterns:
                - DART_API_KEY 미설정 → RuntimeError. caller 사전 검증.
                - 일 호출 한도 초과 시 빈 응답.
                - 결과 추측 X — 정확 인자 값 명시.
            OutputSchema:
                - DART OpenAPI 응답 정규화 (메서드별 다름).
            Prerequisites:
                - 인터넷 + DART_API_KEY 환경변수.
            Freshness:
                - DART OpenAPI 실시간 (분 단위).
            Dataflow:
                - 사용자 인자 → DartClient → DART API → JSON → 본 함수.
            TargetMarkets:
                - KR (DART) 한정.
        """
        return self._dart.document(rceptNo, savePath)

    def documentText(self, rceptNo: str) -> str:
        """공시서류 텍스트 추출.

        Examples
        --------
        >>> s.documentText(filings["rcept_no"][0])

        Args:
            rceptNo: 인자.

        Raises:
            없음.

        Returns:
            str — DART OpenAPI 응답 텍스트.

        LLM Specifications:
            AntiPatterns:
                - DART_API_KEY 미설정 → RuntimeError. caller 사전 검증.
                - 일 호출 한도 초과 시 빈 응답.
                - 결과 추측 X — 정확 인자 값 명시.
            OutputSchema:
                - DART OpenAPI 응답 정규화 (메서드별 다름).
            Prerequisites:
                - 인터넷 + DART_API_KEY 환경변수.
            Freshness:
                - DART OpenAPI 실시간 (분 단위).
            Dataflow:
                - 사용자 인자 → DartClient → DART API → JSON → 본 함수.
            TargetMarkets:
                - KR (DART) 한정.
        """
        return self._dart.documentText(rceptNo)

    # ── 저장 ──────────────────────────────────────────────

    def saveFinance(
        self,
        start: str | int | None = None,
        *,
        end: int | None = None,
        q: int | None = None,
        full: bool = True,
    ) -> Path:
        """재무제표 조회 → {dataDir}/dart/finance/{stockCode}.parquet 저장.

        eddmpython/dartlab 호환 포맷. full=True 기본 (전체 계정).

        Examples
        --------
        >>> s.saveFinance(2020)         # 2020~현재 전분기
        >>> s.saveFinance(2023, q=4)    # 2023 사업보고서만

        Args:
            start: 인자.
            end: 인자.
            q: 인자.
            full: 인자.

        Raises:
            없음.

        Returns:
            Path — 저장된 파일 경로.

        SeeAlso:
            - ``DartClient`` — 본 함수의 HTTP backend.
            - ``Dart`` (facade) — 사용자 진입.

        Requires:
            - dartlab
            - datetime
            - io
            - polars
            - zipfile

        Capabilities:
            - DART OpenAPI endpoint 위임 + 응답 정규화. 회사 식별자 자동 매핑 (corpCode resolve).
              일 호출 한도 (개인 1만/일) 내 호출.

        Guide:
            - "DART OpenAPI 호출" → 본 메서드. 사용자 facade 는 ``Dart()``.

        AIContext:
            internal DART API client — AI 가 직접 호출 시 rate limit 주의.

        LLM Specifications:
            AntiPatterns:
                - DART_API_KEY 미설정 → RuntimeError.
                - 일 호출 한도 초과 시 빈 응답.
                - 회사명 부분 매치 X — 정확명 또는 stockCode/corpCode.
            OutputSchema:
                - pl.DataFrame 또는 dict — endpoint 별 정규화.
            Prerequisites:
                - 인터넷 + DART_API_KEY 환경변수 + 회사 식별자.
            Freshness:
                - DART OpenAPI 실시간 (분 단위).
            Dataflow:
                - 사용자 인자 → DartClient → DART API → JSON → 본 함수.
            TargetMarkets:
                - KR (DART) 한정.
        """
        stockCode = self._resolveStockCode()
        corpName = self._dart._resolveCorpName(self._corp)
        path = _dataPath("finance", stockCode)

        # CFS + OFS 양쪽 수집 (릴리즈 호환)
        frames: list[pl.DataFrame] = []
        for consolidated in (True, False):
            df = self.finance(start, end=end, q=q, full=full, consolidated=consolidated)
            if df.height > 0:
                fsDiv = "CFS" if consolidated else "OFS"
                if "fs_div" not in df.columns:
                    df = df.with_columns(pl.lit(fsDiv).alias("fs_div"))
                frames.append(df)

        if not frames:
            return path
        combined = pl.concat(frames, how="diagonal_relaxed")
        enriched = enrichFinance(combined, stockCode, corpName)
        return _saveFile(enriched, path)

    def _resolveStockCode(self) -> str:
        """종목코드 해석."""
        if self._corp.isdigit() and len(self._corp) == 6:
            return self._corp
        df = loadCorpCodes(self._dart._client)
        match = df.filter(pl.col("corp_name") == self._corp)
        if match.height > 0:
            code = match["stock_code"][0].strip()
            if code:
                return code
        match = df.filter(pl.col("corp_name").str.contains(self._corp, literal=True))
        if match.height > 0:
            code = match["stock_code"][0].strip()
            if code:
                return code
        return ""

    def saveReport(
        self,
        start: str | int | None = None,
        *,
        end: int | None = None,
        q: int | None = None,
        categories: list[str] | None = None,
    ) -> Path:
        """전체 보고서 누적 저장 → {dataDir}/dart/report/{stockCode}.parquet.

        eddmpython 호환 — 1파일에 22개 apiType 누적.

        Parameters
        ----------
        start, end, q : report()와 동일.
        categories : list[str] | None
            저장할 카테고리 목록. None이면 주요 22개 전부.

        Examples
        --------
        >>> s.saveReport(2020)                    # 2020~현재 전분기
        >>> s.saveReport(2023, q=4)               # 2023 사업보고서만
        >>> s.saveReport(2020, categories=["배당","직원"])  # 일부만

        Raises:
            없음.

        Args:
            start: 시작 연도 또는 ISO 날짜. None 이면 기본값.
            end: 종료 연도. None 이면 현재 연도.
            q: 분기 (1~4). None 이면 4분기 (사업보고서).
            categories: 처리 카테고리 리스트. None 이면 전체.

        Returns:
            Path — 저장된 파일 경로.

        SeeAlso:
            - ``DartClient`` — 본 함수의 HTTP backend.
            - ``Dart`` (facade) — 사용자 진입.

        Requires:
            - dartlab
            - datetime
            - io
            - polars
            - zipfile

        Capabilities:
            - DART OpenAPI endpoint 위임 + 응답 정규화. 회사 식별자 자동 매핑 (corpCode resolve).
              일 호출 한도 (개인 1만/일) 내 호출.

        Guide:
            - "DART OpenAPI 호출" → 본 메서드. 사용자 facade 는 ``Dart()``.

        AIContext:
            internal DART API client — AI 가 직접 호출 시 rate limit 주의.

        LLM Specifications:
            AntiPatterns:
                - DART_API_KEY 미설정 → RuntimeError.
                - 일 호출 한도 초과 시 빈 응답.
                - 회사명 부분 매치 X — 정확명 또는 stockCode/corpCode.
            OutputSchema:
                - pl.DataFrame 또는 dict — endpoint 별 정규화.
            Prerequisites:
                - 인터넷 + DART_API_KEY 환경변수 + 회사 식별자.
            Freshness:
                - DART OpenAPI 실시간 (분 단위).
            Dataflow:
                - 사용자 인자 → DartClient → DART API → JSON → 본 함수.
            TargetMarkets:
                - KR (DART) 한정.
        """
        from rich.progress import BarColumn, MofNCompleteColumn, Progress, SpinnerColumn, TextColumn

        from dartlab.core.logger import getConsole

        targets = categories or _PERIODIC_REPORT_CATEGORIES
        stockCode = self._resolveStockCode()
        corpCodeStr = _resolveCorpCode(self._dart._client, self._corp)
        corpName = self._dart._resolveCorpName(self._corp)
        frames: list[pl.DataFrame] = []

        _progress = Progress(
            SpinnerColumn(),
            TextColumn("[bold blue]{task.description}"),
            BarColumn(),
            MofNCompleteColumn(),
            console=getConsole(),
        )
        _task = _progress.add_task(f"보고서 저장 | {corpName}", total=len(targets))
        with _progress:
            for cat in targets:
                _progress.update(_task, description=f"보고서 저장 | {corpName} | {cat}")
                try:
                    df = self.report(cat, start, end=end, q=q)
                    if df.height > 0:
                        endpoint = _REPORT_ENDPOINTS.get(cat, cat)
                        enriched = enrichReport(df, stockCode, corpCodeStr, cat, endpoint)
                        frames.append(enriched)
                except (ValueError, KeyError, RuntimeError, OSError):
                    pass
                _progress.advance(_task)

        path = _dataPath("report", stockCode)
        if not frames:
            return _saveFile(pl.DataFrame(), path)

        combined = pl.concat(frames, how="diagonal_relaxed")
        return _saveFile(combined, path)

    def saveFilings(
        self,
        start: str | datetime | date | None = None,
        end: str | datetime | date | None = None,
        *,
        type: str | None = None,
        final: bool = False,
    ) -> Path:
        """공시목록 누적 저장 → {dataDir}/dart/filings/{stockCode}.parquet.

        기존 파일이 있으면 합쳐서 누적. 중복(rcept_no) 자동 제거.

        Examples
        --------
        >>> s.saveFilings()               # 최근 1년 공시 목록 저장
        >>> s.saveFilings("2020")         # 2020년~현재 누적
        >>> s.saveFilings("2020", type="A")  # 정기공시만

        Args:
            start: 인자.
            end: 인자.
            type: 인자.
            final: 인자.

        Raises:
            없음.

        Returns:
            Path — 저장된 파일 경로.

        SeeAlso:
            - ``DartClient`` — 본 함수의 HTTP backend.
            - ``Dart`` (facade) — 사용자 진입.

        Requires:
            - dartlab
            - datetime
            - io
            - polars
            - zipfile

        Capabilities:
            - DART OpenAPI endpoint 위임 + 응답 정규화. 회사 식별자 자동 매핑 (corpCode resolve).
              일 호출 한도 (개인 1만/일) 내 호출.

        Guide:
            - "DART OpenAPI 호출" → 본 메서드. 사용자 facade 는 ``Dart()``.

        AIContext:
            internal DART API client — AI 가 직접 호출 시 rate limit 주의.

        LLM Specifications:
            AntiPatterns:
                - DART_API_KEY 미설정 → RuntimeError.
                - 일 호출 한도 초과 시 빈 응답.
                - 회사명 부분 매치 X — 정확명 또는 stockCode/corpCode.
            OutputSchema:
                - pl.DataFrame 또는 dict — endpoint 별 정규화.
            Prerequisites:
                - 인터넷 + DART_API_KEY 환경변수 + 회사 식별자.
            Freshness:
                - DART OpenAPI 실시간 (분 단위).
            Dataflow:
                - 사용자 인자 → DartClient → DART API → JSON → 본 함수.
            TargetMarkets:
                - KR (DART) 한정.
        """
        df = self.filings(start, end, type=type, final=final)
        stockCode = self._resolveStockCode()
        path = _dataPath("filings", stockCode)
        return _saveFile(df, path)

    def xbrl(
        self,
        year: str | int | None = None,
        *,
        q: int | None = None,
    ) -> Path:
        """XBRL 재무제표 원본 파일 다운로드 → {dataDir}/dart/xbrl/{stockCode}_{year}_{q}.zip.

        Parameters
        ----------
        year : int | None
            사업연도. None이면 최근 연도.
        q : int | None
            분기. None이면 사업보고서(Q4).

        Returns
        -------
        Path
            저장된 ZIP 파일 경로.

        Examples
        --------
        >>> s.xbrl(2023)         # 2023 사업보고서 XBRL
        >>> s.xbrl(2024, q=2)    # 2024 반기 XBRL

        Raises:
            없음.

        Args:
            year: 사업연도 (예 2024). None 이면 직전 연도.
            q: 분기 (1~4). None 이면 4분기 (사업보고서).

        Returns:
            Path — 저장된 파일 경로.

        SeeAlso:
            - ``DartClient`` — 본 함수의 HTTP backend.
            - ``Dart`` (facade) — 사용자 진입.

        Requires:
            - dartlab
            - datetime
            - io
            - polars
            - zipfile

        Capabilities:
            - DART OpenAPI endpoint 위임 + 응답 정규화. 회사 식별자 자동 매핑 (corpCode resolve).
              일 호출 한도 (개인 1만/일) 내 호출.

        Guide:
            - "DART OpenAPI 호출" → 본 메서드. 사용자 facade 는 ``Dart()``.

        AIContext:
            internal DART API client — AI 가 직접 호출 시 rate limit 주의.

        LLM Specifications:
            AntiPatterns:
                - DART_API_KEY 미설정 → RuntimeError.
                - 일 호출 한도 초과 시 빈 응답.
                - 회사명 부분 매치 X — 정확명 또는 stockCode/corpCode.
            OutputSchema:
                - pl.DataFrame 또는 dict — endpoint 별 정규화.
            Prerequisites:
                - 인터넷 + DART_API_KEY 환경변수 + 회사 식별자.
            Freshness:
                - DART OpenAPI 실시간 (분 단위).
            Dataflow:
                - 사용자 인자 → DartClient → DART API → JSON → 본 함수.
            TargetMarkets:
                - KR (DART) 한정.
        """
        corpCodeStr = _resolveCorpCode(self._dart._client, self._corp)
        bsnsYear = str(year) if year else str(datetime.now().year - 1)
        _, quarter = _resolveQ(q, hasRange=False)
        reprtCode = _QUARTER_TO_CODE.get(quarter, "11011")

        raw = self._dart._client.getBytes(
            "fnlttXbrl.xml",
            {"corp_code": corpCodeStr, "reprt_code": reprtCode},
        )

        stockCode = self._resolveStockCode()
        qLabel = q if q else 4
        xbrlDir = Path(_dartlabConfig.dataDir) / "dart" / "xbrl"
        xbrlDir.mkdir(parents=True, exist_ok=True)
        dest = xbrlDir / f"{stockCode}_{bsnsYear}_Q{qLabel}.zip"
        dest.write_bytes(raw)
        return dest

    def __repr__(self) -> str:
        methods = "report | finance | filings | info | shares | saveFinance | saveReport | saveFilings | xbrl"
        return f"DartCompany('{self._corp}') — {methods}"


OpenDart = Dart
OpenDartCompany = DartCompany
