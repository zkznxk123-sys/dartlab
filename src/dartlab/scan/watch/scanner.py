"""변화 감지 스캐너.

단일 기업 또는 로컬 panel corpus 전체를 순회하며
sections diff + 중요도 스코어링을 실행한다.

사용법::

    from dartlab.scan.watch.scanner import scan_company, scan_market

    # 단일 기업 (Company 객체)
    result = scan_company(company)

    # 시장 전체 (로컬에 있는 panel parquet 기준)
    top = scan_market(sector="반도체", top_n=20)
"""

from __future__ import annotations

from dataclasses import dataclass

from dartlab.core.logger import getLogger

_log = getLogger(__name__)


import polars as pl

from dartlab.providers._common.diff import DiffResult, sectionsDiff
from dartlab.scan.watch.scorer import ScoredChange, scoreChanges, scoredToDataframe


@dataclass
class ScanResult:
    """단일 기업 스캔 결과."""

    stockCode: str
    corpName: str | None
    diffResult: DiffResult
    scored: list[ScoredChange]

    @property
    def topScore(self) -> float:
        """감지된 변화 중 최고 점수 반환.

        Returns
        -------
        float
            scored list 의 첫 원소 (정렬 후 최고) 의 score. 비어 있으면 0.0.

        Capabilities:
            - ScanResult method. 단일 기업 변화 결과 → 최고 점수 또는 DataFrame 변환.

        AIContext:
            ``scanCompany`` 결과 인스턴스 method. 호출자가 후속 사용.

        Guide/When/How:
            ScanResult 인스턴스에서 직접. 빈 list → 0.0 또는 빈 df.

        Requires:
            - ScanResult.scored list

        SeeAlso:
            - :func:`scanCompany` — ScanResult 생성

        Raises
        ------
        없음.

        Examples
        --------
        >>> result.topScore
        85.0
        """
        if not self.scored:
            return 0.0
        return self.scored[0].score

    def toDataframe(self) -> pl.DataFrame:
        """스코어링 결과를 DataFrame으로.

        Returns
        -------
        pl.DataFrame
            stockCode/corpName 컬럼 + ScoredChange 컬럼 (topic, score, reason, ...).

        Raises
        ------
        polars.PolarsError
            scoredToDataframe 가 발생시키는 예외 전파.

        Capabilities:
            - ScanResult.scored 를 DataFrame 으로. stockCode/corpName 컬럼 추가.

        AIContext:
            ``scanMarket`` aggregation 시 종목별 row 통합 source.

        Guide:
            ScanResult 후처리. 빈 scored → 빈 df.

        When:
            ScanResult 인스턴스에서 직접.

        How:
            ``scoredToDataframe`` 위임 → stockCode/corpName 컬럼 추가.

        Requires:
            - :func:`scoredToDataframe`

        SeeAlso:
            - :func:`scanMarket` — 본 메서드 호출자

        Examples
        --------
        >>> df = result.toDataframe()
        >>> df.columns
        """
        df = scoredToDataframe(self.scored)
        if df.height > 0:
            df = df.with_columns(
                pl.lit(self.stockCode).alias("stockCode"),
                pl.lit(self.corpName or "").alias("corpName"),
            )
        return df


def scanCompany(
    company: object,
    *,
    topic: str | None = None,
) -> ScanResult | None:
    """단일 기업의 sections diff + 중요도 스코어링.

    Args:
        company: dartlab Company 객체 (panel text wide 조회 가능).
        topic: 특정 topic만 필터링 (None이면 전체).

    Returns:
        ScanResult 또는 sections가 없으면 None.

    Raises:
        없음 — sections 누락 시 None 반환.

    Capabilities:
        - 단일 기업 panel text wide → diff → 중요도 score 통합. topic 필터로 특정 영역 한정.

    AIContext:
        ``Company.watch()`` 의 entry. AI agent 가 "이 기업 변화" 단일 종목 질문 시 본 함수 dispatch.

    Guide:
        - panel text 없으면 None — caller 가 안내.

    When:
        Company.watch() 호출 시. scanMarket 의 inner iteration.

    How:
        ``panelTextWide`` 추출 → topic 필터 (선택) → ``sectionsDiff`` → ``scoreChanges`` →
        ScanResult.

    Requires:
        - ``Company.panel`` / 내부 panel text wide helper
        - ``sectionsDiff`` · ``scoreChanges``

    SeeAlso:
        - :func:`scanMarket` — 전종목 버전 (본 함수 반복 호출)
        - :func:`scoreChanges` — 중요도 SSOT

    Example:
        >>> import dartlab
        >>> c = dartlab.Company("005930")
        >>> result = scanCompany(c, topic="riskManagement")
        >>> result.topScore if result else "no diff"
    """
    # providers.dart.panel.text.panelTextWide(panel 섹션 topic×period) SSOT.
    from dartlab.providers.dart.panel.text import panelTextWide

    stockCode = getattr(company, "stockCode", "")
    panelSections = panelTextWide(stockCode) if stockCode else None
    if panelSections is None:
        return None

    if topic is not None and "topic" in panelSections.columns:
        panelSections = panelSections.filter(pl.col("topic") == topic)
        if panelSections.height == 0:
            return None

    diffResult = sectionsDiff(panelSections)
    if not diffResult.summaries:
        return None

    scored = scoreChanges(diffResult, sections=panelSections)

    corpName = getattr(company, "corpName", None)

    return ScanResult(
        stockCode=stockCode,
        corpName=corpName,
        diffResult=diffResult,
        scored=scored,
    )


def _listLocalPanel() -> list[str]:
    """로컬 panel parquet 종목코드 목록 (panel SSOT).

    Returns
    -------
    list[str]
        정렬된 종목코드 목록 (6자리). 디렉토리 없으면 빈 리스트.
    """
    from dartlab.core.dataConfig import DATA_RELEASES
    from dartlab.core.dataLoader import _getDataRoot

    panel_dir = _getDataRoot() / DATA_RELEASES["panel"]["dir"]
    if not panel_dir.exists():
        return []
    return sorted(p.stem for p in panel_dir.glob("*.parquet"))


def scanMarket(
    *,
    sector: str | None = None,
    topN: int = 20,
    minScore: float = 10.0,
    stockCodes: list[str] | None = None,
    verbose: bool = False,
) -> pl.DataFrame:
    """시장 전체 또는 섹터별 변화 감지 스캔.

    로컬에 다운로드된 panel parquet을 순회하며 각 기업의
    sections diff → 중요도 스코어링을 실행한 뒤 상위 변화를 집계한다.

    Args:
        sector: 섹터 필터 (예: "반도체", "IT"). None이면 전체.
        top_n: 상위 N개 결과만 반환.
        min_score: 이 점수 이상만 포함.
        stock_codes: 직접 종목코드 목록 지정 (sector 무시).
        verbose: True이면 진행 상황 출력.

    Returns:
        stockCode, corpName, topic, score, changeRate, reason 등 컬럼의 DataFrame.

    Raises:
        polars.PolarsError: panel parquet 손상 시.

    Example:
        >>> import dartlab
        >>> df = dartlab.scan("digest", sector="반도체", topN=30)
        >>> df.sort("score", descending=True).head()

    Capabilities:
        - 로컬 panel parquet glob → 종목별 ``scanCompany`` 반복 → minScore 이상 row aggregate
          → score 내림차순 topN. sector 필터 또는 명시 stockCodes 지원.

    AIContext:
        ``scanDigest`` 의 source. AI agent 가 시장 전체 변화 다이제스트 빌드 시 본 함수가 raw
        scan 단계.

    Guide:
        - sector / stockCodes 둘 다 None 이면 전체 로컬 panel 종목 대상 (~수천 종목, 분 단위).
        - minScore 임계 조정으로 noise 제거.

    When:
        ``scanDigest`` 진행 또는 manual 시장 분석 시.

    How:
        codes 결정 → 각 종목 ``scanCompany`` → ScanResult.toDataframe → 누적 → score 필터 →
        sort + topN.

    Requires:
        - 로컬 ``data/dart/panel/{stockCode}.parquet`` 들 (panel 섹션 본문)

    SeeAlso:
        - :func:`scanCompany` — 종목당 inner scan
        - :func:`dartlab.scan.watch.scanDigest` — 본 함수 호출자
    """
    if stockCodes is None:
        codes = _listLocalPanel()
    else:
        codes = list(stockCodes)

    if not codes:
        from dartlab.core.messaging import emit

        emit("hint:market_data_needed", category="panel", fn="digest")
        return pl.DataFrame(
            schema={
                "stockCode": pl.Utf8,
                "corpName": pl.Utf8,
                "topic": pl.Utf8,
                "score": pl.Float64,
                "changeRate": pl.Float64,
                "deltaBytes": pl.Int64,
                "latestPeriod": pl.Utf8,
                "reason": pl.Utf8,
            }
        )

    # 섹터 필터링 — core.sector classifier 는 하위 SSOT.
    if sector is not None and stockCodes is None:
        from dartlab.core.sector import classify as classifier

        codes = _filterBySector(codes, sector, classifier=classifier)

    # F5: scan → company 직접 의존 제거. FinanceDataAccessor.lookupCompany 위임 (정공법 B+C).
    from dartlab.core.di import getFinanceAccessor

    accessor = getFinanceAccessor()

    frames: list[pl.DataFrame] = []
    scanned = 0

    for code in codes:
        try:
            c = accessor.lookupCompany(code)
            if c is None:
                continue
            result = scanCompany(c)
            if result is not None and result.scored:
                df = result.toDataframe()
                if df.height > 0:
                    frames.append(df)
            scanned += 1
            if verbose and scanned % 50 == 0:
                _log.info(f"[watch] {scanned}/{len(codes)} 스캔 완료...")
        except (FileNotFoundError, ValueError, KeyError, OSError):
            continue

    if not frames:
        return pl.DataFrame(
            schema={
                "stockCode": pl.Utf8,
                "corpName": pl.Utf8,
                "topic": pl.Utf8,
                "score": pl.Float64,
                "changeRate": pl.Float64,
                "deltaBytes": pl.Int64,
                "latestPeriod": pl.Utf8,
                "reason": pl.Utf8,
            }
        )

    combined = pl.concat(frames, how="diagonal_relaxed")
    combined = combined.filter(pl.col("score") >= minScore)
    combined = combined.sort("score", descending=True).head(topN)

    if verbose:
        _log.info(f"[watch] 스캔 완료: {scanned}개 기업, {combined.height}개 변화 감지")

    return combined


def _filterBySector(codes: list[str], sector: str, *, classifier=None) -> list[str]:
    """종목코드 목록에서 특정 섹터에 해당하는 것만 필터.

    classifier: name → SectorInfo callable (예: industry.classify). 호출자가 주입.
    None 이면 sector 필터 skip (passthrough). scan(L1.5) 가 industry(L2) 를
    직접 import 하지 않도록 inversion (단방향 정책).
    """
    if classifier is None:
        return codes
    from dartlab.gather.krx.listing import codeToName

    filtered = []
    for code in codes:
        try:
            name = codeToName(code)
            if name is None:
                continue
            info = classifier(name)
            if info and sector in (info.sector.value, info.industryGroup.value):
                filtered.append(code)
        except (ValueError, KeyError):
            continue
    return filtered if filtered else codes


# ── watch 엔진 스펙 (former watch/spec.py, P-S5 absorbed) ──


def buildSpec() -> dict:
    """watch 엔진 스펙을 코드에서 자동 추출하여 반환한다.

    Returns
    -------
    dict
        watch 엔진 메타 정보. 구조:

        - name : str — 엔진명 ("watch")
        - description : str — 엔진 설명
        - summary : dict
            - scoringFactors : int — 스코어링 요소 수
            - highWeightTopics : int — 고가중 topic 수
            - lowWeightTopics : int — 저가중 topic 수
            - maxScore : int — 최대 점수 (점, 100)
        - detail : dict
            - scoringFactors : list[str] — 스코어링 요소 설명
            - highWeightTopics : list[str] — 고가중 topic 목록
            - lowWeightTopics : list[str] — 저가중 topic 목록
            - publicAPI : list[str] — 공개 API 사용법

    Requires:
        - scorer 모듈 (TOPIC_WEIGHTS / SCORING_FACTORS) 만 참조 — 외부 의존 없음.

    Raises
    ------
    없음 — scorer constants 만 참조.

    Examples
    --------
    >>> from dartlab.scan.watch.scanner import buildSpec
    >>> spec = buildSpec()
    >>> spec["name"]
    'watch'
    """
    from dartlab.scan.watch.scorer import _HIGH_WEIGHT_TOPICS, _LOW_WEIGHT_TOPICS

    return {
        "name": "watch",
        "description": "sections diff 기반 공시 변화 감지 + 중요도 스코어링",
        "summary": {
            "scoringFactors": 4,
            "highWeightTopics": len(_HIGH_WEIGHT_TOPICS),
            "lowWeightTopics": len(_LOW_WEIGHT_TOPICS),
            "maxScore": 100,
        },
        "detail": {
            "scoringFactors": [
                "changeRate 기반 기본 점수 (최대 50점)",
                "topic 유형 가중치 (핵심 경영 1.5x, 저가중 0.6x)",
                "텍스트 크기 변화율 (최대 30점)",
                "트렌드/리스크 키워드 매칭 (최대 20점)",
            ],
            "highWeightTopics": sorted(_HIGH_WEIGHT_TOPICS),
            "lowWeightTopics": sorted(_LOW_WEIGHT_TOPICS),
            "publicAPI": [
                "Company.watch() — 단일 기업 변화 요약",
                "Company.watch(topic) — 특정 topic 상세",
                "dartlab.digest() — 시장 전체 다이제스트",
                "dartlab.digest(sector=) — 섹터별 다이제스트",
            ],
        },
    }
