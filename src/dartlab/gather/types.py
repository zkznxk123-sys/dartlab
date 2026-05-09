"""Gather 엔진 데이터 타입 — 멀티소스 수집 결과."""

from __future__ import annotations

from dataclasses import dataclass, field

# ══════════════════════════════════════
# 도메인 설정
# ══════════════════════════════════════


@dataclass(slots=True)
class DomainConfig:
    """도메인별 rate limit + 동시 연결 정책.

    Attributes
    ----------
    rpm : int
        분당 최대 요청 수 (회/분). 기본 30.
    concurrency : int
        동시 연결 수 상한. 기본 2.
    timeout : float
        요청 타임아웃 (초). 기본 10.0.
    jitter_min : float
        요청 전 최소 랜덤 대기 (초). 기본 0.3.
    jitter_max : float
        요청 전 최대 랜덤 대기 (초). 기본 1.5.
    min_interval : float
        요청 간 최소 간격 (초). 0이면 제한 없음. 기본 0.0.
    """

    rpm: int = 30
    concurrency: int = 2
    timeout: float = 10.0
    jitter_min: float = 0.3  # 요청 전 최소 랜덤 대기 (초)
    jitter_max: float = 1.5  # 요청 전 최대 랜덤 대기 (초)
    min_interval: float = 0.0  # 요청 간 최소 간격 (초, 0=제한 없음)


# ══════════════════════════════════════
# 수집 데이터 타입
# ══════════════════════════════════════


@dataclass
class PriceSnapshot:
    """주가 스냅샷.

    Attributes
    ----------
    current : float
        현재가 (원 또는 해당 통화).
    change : float
        전일 대비 변동 (원).
    change_pct : float
        전일 대비 변동률 (%).
    high_52w : float
        52주 최고가 (원).
    low_52w : float
        52주 최저가 (원).
    volume : int
        거래량 (주).
    market_cap : float
        시가총액 (억원).
    per : float | None
        PER (배).
    pbr : float | None
        PBR (배).
    dividend_yield : float | None
        배당수익률 (%).
    source : str
        데이터 출처.
    fetched_at : str
        수집 시각 (ISO 형식).
    currency : str
        통화 코드 ("KRW", "USD" 등).
    exchange : str
        거래소 코드.
    market : str
        시장 코드 ("KR", "US" 등).
    is_stale : bool
        stale cache 반환 여부.
    """

    current: float = 0.0
    change: float = 0.0
    change_pct: float = 0.0
    high_52w: float = 0.0
    low_52w: float = 0.0
    volume: int = 0
    market_cap: float = 0.0  # 억원
    per: float | None = None
    pbr: float | None = None
    dividend_yield: float | None = None
    source: str = ""
    fetched_at: str = ""
    # 글로벌 확장 (기본값 → 하위호환)
    currency: str = "KRW"
    exchange: str = ""
    market: str = "KR"
    is_stale: bool = False

    def __repr__(self) -> str:
        stale_tag = " [stale]" if self.is_stale else ""
        lines = [f"[주가 — {self.source}{stale_tag}]"]
        lines.append(f"  현재가: {self.current:,.0f}")
        if self.change != 0:
            lines.append(f"  변동: {self.change:+,.0f} ({self.change_pct:+.2f}%)")
        if self.per is not None:
            lines.append(f"  PER: {self.per:.2f}")
        if self.pbr is not None:
            lines.append(f"  PBR: {self.pbr:.2f}")
        if self.high_52w > 0:
            lines.append(f"  52주: {self.low_52w:,.0f}~{self.high_52w:,.0f}")
        return "\n".join(lines)


@dataclass
class RevenueConsensus:
    """애널리스트 매출/이익 컨센서스 — 네이버 금융 finance/annual API.

    Attributes
    ----------
    fiscal_year : int
        회계연도.
    revenue_est : float
        예상 매출 (억원).
    operating_profit_est : float | None
        예상 영업이익 (억원).
    net_income_est : float | None
        예상 순이익 (억원).
    eps_est : float | None
        예상 EPS (원).
    per_est : float | None
        예상 PER (배).
    source : str
        데이터 출처.
    """

    fiscal_year: int = 0
    revenue_est: float = 0.0  # 예상 매출 (억원)
    operating_profit_est: float | None = None  # 예상 영업이익 (억원)
    net_income_est: float | None = None  # 예상 순이익 (억원)
    eps_est: float | None = None  # 예상 EPS (원)
    per_est: float | None = None  # 예상 PER (배)
    source: str = ""

    def __repr__(self) -> str:
        parts = [f"RevenueConsensus({self.fiscal_year})"]
        if self.revenue_est:
            parts.append(f"매출={self.revenue_est:,.0f}억")
        if self.operating_profit_est:
            parts.append(f"영업이익={self.operating_profit_est:,.0f}억")
        if self.eps_est:
            parts.append(f"EPS={self.eps_est:,.0f}원")
        return " ".join(parts)


@dataclass
class FlowData:
    """투자자별 수급 데이터.

    Attributes
    ----------
    foreign_net : float
        외국인 순매수 (주).
    institution_net : float
        기관 순매수 (주).
    foreign_holding_ratio : float
        외국인 보유 비율 (%).
    source : str
        데이터 출처.
    """

    foreign_net: float = 0.0  # 외국인 순매수 (주)
    institution_net: float = 0.0  # 기관 순매수 (주)
    foreign_holding_ratio: float = 0.0  # 외국인 보유 비율 (%)
    source: str = ""

    def __repr__(self) -> str:
        return (
            f"Flow(외국인={self.foreign_net:+,.0f}, "
            f"기관={self.institution_net:+,.0f}, "
            f"외국인비중={self.foreign_holding_ratio:.1f}%)"
        )


@dataclass
class NewsItem:
    """뉴스 항목.

    Attributes
    ----------
    date : str
        발행일 (YYYY-MM-DD).
    title : str
        기사 제목.
    source : str
        언론사/출처.
    url : str
        기사 URL.
    """

    date: str = ""  # ISO date (YYYY-MM-DD)
    title: str = ""
    source: str = ""
    url: str = ""


@dataclass
class SectorInfo:
    """업종 분류 정보.

    Attributes
    ----------
    sectorCode : str
        업종 코드.
    sectorName : str
        업종명.
    industryCode : str
        산업 코드.
    industryName : str
        산업명.
    market : str
        시장 구분 (KOSPI/KOSDAQ).
    source : str
        데이터 출처.
    """

    sectorCode: str = ""
    sectorName: str = ""
    industryCode: str = ""
    industryName: str = ""
    market: str = ""  # KOSPI/KOSDAQ
    source: str = ""

    def __repr__(self) -> str:
        parts = [f"Sector({self.sectorName}"]
        if self.industryName:
            parts[0] += f"/{self.industryName}"
        parts[0] += f", {self.market})"
        return parts[0]


@dataclass
class ShortSellingData:
    """공매도 잔고/거래 데이터.

    Attributes
    ----------
    date : str
        기준일 (YYYY-MM-DD).
    shortVolume : int
        공매도 거래량 (주).
    shortAmount : int
        공매도 거래대금 (원).
    totalVolume : int
        전체 거래량 (주).
    shortRatio : float
        공매도 비중 (%).
    balance : int
        공매도 잔고 수량 (주).
    balanceRatio : float
        공매도 잔고 비율 (%).
    source : str
        데이터 출처.
    """

    date: str = ""
    shortVolume: int = 0
    shortAmount: int = 0  # 원
    totalVolume: int = 0
    shortRatio: float = 0.0  # 공매도 비중 (%)
    balance: int = 0  # 잔고 수량
    balanceRatio: float = 0.0  # 잔고 비율 (%)
    source: str = ""

    def __repr__(self) -> str:
        return f"Short(비중={self.shortRatio:.1f}%, 잔고비율={self.balanceRatio:.1f}%)"


@dataclass
class InsiderTrade:
    """내부자(임원/주요주주) 주식 거래.

    Attributes
    ----------
    date : str
        거래일 (YYYY-MM-DD).
    name : str
        거래자 이름.
    position : str
        직위/관계.
    tradeType : str
        거래 유형 (취득/처분/장내매수/장내매도).
    changeShares : int
        변동 주식수 (주).
    afterShares : int
        변동 후 보유 주식수 (주).
    reason : str
        변동 사유.
    source : str
        데이터 출처.
    """

    date: str = ""
    name: str = ""
    position: str = ""
    tradeType: str = ""  # 취득/처분/장내매수/장내매도
    changeShares: int = 0
    afterShares: int = 0
    reason: str = ""
    source: str = ""

    def __repr__(self) -> str:
        return f"Insider({self.name} {self.tradeType} {self.changeShares:+,}주 {self.date})"


@dataclass
class MajorHolder:
    """5% 이상 대량보유 주주.

    Attributes
    ----------
    holderName : str
        보유자 이름.
    shares : int
        보유 주식수 (주).
    ratio : float
        보유비율 (%).
    changeDate : str
        변동일 (YYYY-MM-DD).
    changeType : str
        변동 유형 (취득/처분/변동).
    source : str
        데이터 출처.
    """

    holderName: str = ""
    shares: int = 0
    ratio: float = 0.0  # 보유비율 (%)
    changeDate: str = ""
    changeType: str = ""  # 취득/처분/변동
    source: str = ""

    def __repr__(self) -> str:
        return f"MajorHolder({self.holderName} {self.ratio:.1f}% {self.changeType})"


@dataclass
class InstitutionOwnership:
    """기관/외국인 지분 보유.

    Attributes
    ----------
    holderName : str
        보유 주체명 (예: "외국인 합계").
    shares : int
        보유 주식수 (주).
    ratio : float
        보유비율 (%).
    value : float
        보유금액 (원).
    changeShares : int
        변동수량 (주).
    source : str
        데이터 출처.
    """

    holderName: str = ""
    shares: int = 0
    ratio: float = 0.0  # 보유비율 (%)
    value: float = 0.0  # 보유금액
    changeShares: int = 0  # 변동수량
    source: str = ""

    def __repr__(self) -> str:
        return f"Institution({self.holderName} {self.ratio:.1f}%)"


@dataclass
class UpgradeDowngrade:
    """애널리스트 등급 변경.

    Attributes
    ----------
    date : str
        변경일 (YYYY-MM-DD).
    firm : str
        증권사/리서치 하우스.
    toGrade : str
        변경 후 등급.
    fromGrade : str
        변경 전 등급.
    action : str
        변경 유형 (upgrade/downgrade/init/maintain/reiterated).
    source : str
        데이터 출처.
    """

    date: str = ""
    firm: str = ""
    toGrade: str = ""
    fromGrade: str = ""
    action: str = ""  # upgrade/downgrade/init/maintain/reiterated
    source: str = ""

    def __repr__(self) -> str:
        return f"Rating({self.firm} {self.action}: {self.fromGrade}->{self.toGrade})"


@dataclass
class GatherResult:
    """도메인 1개의 수집 결과 — 병렬 수집 시 반환 단위.

    Attributes
    ----------
    domain : str
        소스 도메인 이름.
    price : PriceSnapshot | None
        주가 스냅샷.
    flow : FlowData | None
        투자자별 수급.
    sector_per : float | None
        업종 평균 PER (배).
    sectorInfo : SectorInfo | None
        업종 분류 정보.
    insiderTrades : list[InsiderTrade]
        내부자 거래 리스트.
    shortSelling : ShortSellingData | None
        공매도 데이터.
    error : str | None
        오류 메시지. 정상이면 None.
    """

    domain: str = ""
    price: PriceSnapshot | None = None
    flow: FlowData | None = None
    sector_per: float | None = None
    sectorInfo: SectorInfo | None = None
    insiderTrades: list[InsiderTrade] = field(default_factory=list)
    shortSelling: ShortSellingData | None = None
    error: str | None = None


@dataclass
class GatherSnapshot:
    """전체 병렬 수집 통합 결과."""

    stock_code: str = ""
    results: dict[str, GatherResult] = field(default_factory=dict)
    collected_at: str = ""
    _news: list[NewsItem] = field(default_factory=list)
    _sectorInfo: SectorInfo | None = None
    _insiderTrades: list[InsiderTrade] = field(default_factory=list)
    _shortSelling: ShortSellingData | None = None

    @property
    def price(self) -> PriceSnapshot | None:
        """첫 번째 가용 주가.

        Returns
        -------
        PriceSnapshot | None
            수집된 소스 중 첫 번째 유효한 주가 스냅샷. 없으면 None.
        """
        for r in self.results.values():
            if r.price:
                return r.price
        return None

    @property
    def flow(self) -> FlowData | None:
        """수집된 수급 데이터 반환.

        Returns
        -------
        FlowData | None
            첫 번째 유효한 수급 데이터. 없으면 None.
        """
        for r in self.results.values():
            if r.flow:
                return r.flow
        return None

    @property
    def news(self) -> list[NewsItem]:
        """수집된 뉴스 항목.

        Returns
        -------
        list[NewsItem]
            뉴스 항목 리스트.
        """
        return self._news

    @property
    def sectorInfo(self) -> SectorInfo | None:
        """수집된 업종 분류.

        Returns
        -------
        SectorInfo | None
            업종 분류 정보. 없으면 None.
        """
        for r in self.results.values():
            if r.sectorInfo:
                return r.sectorInfo
        return self._sectorInfo

    @property
    def insiderTrades(self) -> list[InsiderTrade]:
        """수집된 내부자 거래.

        Returns
        -------
        list[InsiderTrade]
            내부자 거래 리스트.
        """
        for r in self.results.values():
            if r.insiderTrades:
                return r.insiderTrades
        return self._insiderTrades

    @property
    def shortSelling(self) -> ShortSellingData | None:
        """수집된 공매도 데이터.

        Returns
        -------
        ShortSellingData | None
            공매도 데이터. 없으면 None.
        """
        for r in self.results.values():
            if r.shortSelling:
                return r.shortSelling
        return self._shortSelling

    @property
    def sources_available(self) -> list[str]:
        """정상 응답한 소스 목록.

        Returns
        -------
        list[str]
            오류 없이 수집 완료된 소스 이름 리스트.
        """
        return [d for d, r in self.results.items() if r.error is None]

    @property
    def sources_failed(self) -> list[str]:
        """오류가 발생한 소스 목록.

        Returns
        -------
        list[str]
            오류가 발생한 소스 이름 리스트.
        """
        return [d for d, r in self.results.items() if r.error is not None]

    def to_market_snapshot(self) -> MarketSnapshot:
        """Analyst 엔진 호환 flat 스냅샷으로 변환.

        Returns
        -------
        MarketSnapshot
            현재가, 컨센서스, 멀티플, 수급, 52주 범위를 포함한 flat 구조.
        """
        price = self.price
        flow = self.flow

        multiples: dict[str, float] = {}
        price_range: tuple[float, float] | None = None
        current_price = 0.0

        if price:
            current_price = price.current
            if price.per is not None:
                multiples["per"] = price.per
            if price.pbr is not None:
                multiples["pbr"] = price.pbr
            if price.dividend_yield is not None:
                multiples["dividend_yield"] = price.dividend_yield
            if price.low_52w > 0 and price.high_52w > 0:
                price_range = (price.low_52w, price.high_52w)

        # sector_per — 첫 번째 가용 결과에서
        for r in self.results.values():
            if r.sector_per:
                multiples["sector_per"] = r.sector_per
                break

        supply_demand: dict[str, float] = {}
        if flow:
            supply_demand["foreign_net"] = flow.foreign_net
            supply_demand["institution_net"] = flow.institution_net
            supply_demand["foreign_holding_ratio"] = flow.foreign_holding_ratio

        return MarketSnapshot(
            stock_code=self.stock_code,
            current_price=current_price,
            multiples=multiples,
            supply_demand=supply_demand,
            price_range_52w=price_range,
            collected_at=self.collected_at,
            sources_available=self.sources_available,
            sources_failed=self.sources_failed,
        )

    def __repr__(self) -> str:
        lines = [f"[GatherSnapshot — {self.stock_code}]"]
        if self.price:
            lines.append(f"  {self.price}")
        if self.flow:
            lines.append(f"  {self.flow}")
        lines.append(f"  소스: {', '.join(self.sources_available)}")
        if self.sources_failed:
            lines.append(f"  실패: {', '.join(self.sources_failed)}")
        return "\n".join(lines)


# ══════════════════════════════════════
# Analyst 호환 스냅샷 (flat 구조)
# ══════════════════════════════════════


@dataclass
class PeerData:
    """피어 기업 멀티플 데이터.

    Attributes
    ----------
    ticker : str
        종목코드/티커.
    name : str
        기업명.
    per : float | None
        PER (배).
    pbr : float | None
        PBR (배).
    ev_ebitda : float | None
        EV/EBITDA (배).
    market_cap : float | None
        시가총액 (억원).
    """

    ticker: str = ""
    name: str = ""
    per: float | None = None
    pbr: float | None = None
    ev_ebitda: float | None = None
    market_cap: float | None = None

    def __repr__(self) -> str:
        parts = [f"{self.ticker}({self.name})"]
        if self.per is not None:
            parts.append(f"PER={self.per:.1f}")
        if self.pbr is not None:
            parts.append(f"PBR={self.pbr:.2f}")
        if self.ev_ebitda is not None:
            parts.append(f"EV/EBITDA={self.ev_ebitda:.1f}")
        return " ".join(parts)


@dataclass
class MarketSnapshot:
    """Analyst 호환 flat 시장 데이터 — GatherSnapshot → MarketSnapshot 변환용.

    Attributes
    ----------
    stock_code : str
        종목코드.
    current_price : float
        현재가 (원 또는 해당 통화).
    multiples : dict[str, float]
        멀티플 (per, pbr, dividend_yield, sector_per 등) (배 또는 %).
    peer_multiples : list[PeerData]
        피어 기업 멀티플 리스트.
    supply_demand : dict[str, float]
        수급 (foreign_net, institution_net (주), foreign_holding_ratio (%)).
    macro : dict[str, float]
        매크로 지표.
    price_range_52w : tuple[float, float] | None
        52주 가격 범위 (최저, 최고) (원).
    collected_at : str
        수집 시각 (ISO 형식).
    sources_available : list[str]
        정상 응답 소스 목록.
    sources_failed : list[str]
        오류 발생 소스 목록.
    """

    stock_code: str = ""
    current_price: float = 0.0
    multiples: dict[str, float] = field(default_factory=dict)
    peer_multiples: list[PeerData] = field(default_factory=list)
    supply_demand: dict[str, float] = field(default_factory=dict)
    macro: dict[str, float] = field(default_factory=dict)
    price_range_52w: tuple[float, float] | None = None
    collected_at: str = ""
    sources_available: list[str] = field(default_factory=list)
    sources_failed: list[str] = field(default_factory=list)

    def __repr__(self) -> str:
        lines = [f"[MarketSnapshot — {self.stock_code}]"]
        lines.append(f"  현재가: {self.current_price:,.0f}")
        if self.multiples:
            mult_str = ", ".join(f"{k}={v:.2f}" for k, v in self.multiples.items())
            lines.append(f"  멀티플: {mult_str}")
        if self.price_range_52w:
            lines.append(f"  52주 범위: {self.price_range_52w[0]:,.0f}~{self.price_range_52w[1]:,.0f}")
        return "\n".join(lines)


# ══════════════════════════════════════
# 예외
# ══════════════════════════════════════


class GatherError(Exception):
    """Gather 엔진 기본 예외."""


class SourceUnavailableError(GatherError):
    """소스 접근 불가."""


class RateLimitExceededError(GatherError):
    """Rate limit 초과."""


class CircuitOpenError(SourceUnavailableError):
    """Circuit breaker open — 소스 일시 차단."""
