"""Gather macro mixin — 거시경제 지표 (KR ECOS + US FRED) 4 메서드."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import polars as pl

from .context import GatherMixinContext

log = logging.getLogger(__name__)


class _GatherMacroMixin(GatherMixinContext):
    """거시지표 메서드 모음 — Gather 클래스 4 메서드 + 2 클래스 상수."""

    _KNOWN_MARKETS = {"KR", "US"}

    # eddmpython PRIORITY_INDICATORS (12개)
    _MACRO_KR = [
        "CPI",
        "BASE_RATE",
        "USDKRW",
        "M2",
        "CLI",
        "CCI",
        "CSI",
        "IPI",
        "MANUFACTURING",
        "TRADE",
        "HOUSE_PRICE",
        "APT_PRICE",
    ]

    # eddmpython fred/config.py INDICATORS (24개)
    _MACRO_US = [
        "GDP",
        "CPIAUCSL",
        "CPILFESL",
        "PCEPI",
        "PCEPILFE",
        "UNRATE",
        "FEDFUNDS",
        "DGS10",
        "M2SL",
        "TB3MS",
        "SP500",
        "VIXCLS",
        "AAA",
        "HOUST",
        "CSUSHPISA",
        "INDPRO",
        "PAYEMS",
        "RSAFS",
        "CES0500000003",
        "ICSA",
        "USSLIND",
        "UMCSENT",
        "DRTSCILM",
        "DTWEXBGS",
        "DCOILWTICO",
    ]

    def macro(
        self,
        market: str = "KR",
        indicator: str | None = None,
        *,
        start: str | None = None,
        end: str | None = None,
        apiKey: str | None = None,
        scope: str = "default",
    ) -> "pl.DataFrame | None":
        """거시경제 지표 시계열 조회.

        Capabilities:
            - 기본: HuggingFace 벌크 데이터셋 — API 키 불필요
            - KR: ECOS (한국은행) — CPI, 기준금리, 환율 등 12개 핵심 지표
            - US: FRED — GDP, CPI, 실업률, 연방기금금리 등 24개 핵심 지표
            - 스마트 라우팅: 지표 코드만으로 KR/US 자동 감지
            - 전체 지표: wide DataFrame (date + 각 지표 컬럼)
            - 단일 지표: (date, value) DataFrame
            - 직접 API: apiKey 명시 시만 ECOS/FRED API 호출

        AIContext:
            - macro 엔진의 raw 데이터 원천. analysis/quant 가 regime/anomaly 분석에 사용

        Guide:
            indicator 인자가 KR/US 둘 중 어디 코드인지 자동 감지 (스마트 라우팅).
            "CPI" 는 KR, "FEDFUNDS" 는 US 로 자동 분기.

        When:
            거시경제 지표 시계열 필요 시. 단일 지표 또는 시장 전체.

        How:
            indicator → _detectMarket → HF 벌크 또는 직접 API → wide/single DF.

        Args:
            market: "KR" 또는 "US". 지표 코드 직접 전달도 가능 (자동 감지).
            indicator: 지표 코드 ("CPI", "FEDFUNDS" 등). None이면 전체 지표.
            start: 시작일 (YYYY-MM-DD). None이면 기본 기간.
            end: 종료일. None이면 오늘.
            apiKey: ECOS/FRED 직접 API 키. None이면 HF 벌크 데이터셋 사용.
            scope: "default" (기존 핵심 지표) 또는 "catalog" (전체 카탈로그).

        Returns:
            pl.DataFrame | None — wide DataFrame (전체) 또는 (date, value) (단일).

        Requires:
            기본 HF 경로: 불필요.
            직접 API 경로: KR ECOS_API_KEY, US FRED_API_KEY 값을 apiKey 로 명시 전달.

        Raises:
            ValueError: scope 가 ``"default"``/``"catalog"`` 외일 때.

        Example::

            g = getDefaultGather()
            g.macro()                 # KR 전체 지표 wide DF
            g.macro("US")             # US 전체 지표 wide DF
            g.macro("CPI")            # CPI (자동 KR 감지)
            g.macro("FEDFUNDS")       # 연방기금금리 (자동 US 감지)
            g.macro("KR", "CPI")      # 명시적 KR + CPI
            g.macro("US", "SP500")    # 명시적 US + S&P500

        See Also:
            ``dartlab.macro`` 엔진 — 본 raw 데이터의 분석 결과.
            ``dartlab.gather.bulkData.macroHf`` — HF 벌크 경로.
        """
        import time

        from ..infra.telemetry import emitGatherFetch

        t0 = time.monotonic()
        try:
            if scope not in {"default", "catalog"}:
                raise ValueError("scope 는 'default' 또는 'catalog' 여야 합니다.")
            # 스마트 라우팅: market 위치에 지표 코드가 온 경우
            if market not in self._KNOWN_MARKETS:
                indicator = market
                market = self._detectMarket(indicator)
            if market == "KR":
                return self._macroKR(indicator, start=start, end=end, apiKey=apiKey, scope=scope)
            return self._macroUS(indicator, start=start, end=end, apiKey=apiKey, scope=scope)
        finally:
            emitGatherFetch("macro", (time.monotonic() - t0) * 1000, cacheHit=False, market=market)

    def _detectMarket(self, indicator: str) -> str:
        """지표 코드로 market 자동 감지 — ECOS 카탈로그에 있으면 KR, 없으면 US.

        Parameters
        ----------
        indicator : str
            거시지표 코드 ("CPI", "FEDFUNDS" 등).

        Returns
        -------
        str
            "KR" — ECOS 카탈로그에 등록된 지표.
            "US" — 그 외 (FRED 지표로 간주).
        """
        try:
            from dartlab.gather.ecos.catalog import getEntry

            if getEntry(indicator):
                return "KR"
        except ImportError:
            pass
        return "US"

    def _macroKR(
        self,
        indicator: str | None,
        *,
        start: str | None,
        end: str | None,
        apiKey: str | None = None,
        scope: str = "default",
    ):
        """KR 거시지표 — ECOS (한국은행) API 조회.

        Parameters
        ----------
        indicator : str | None
            지표 코드 ("CPI", "BASE_RATE" 등). None이면 12개 핵심 지표 전체.
        start : str | None
            시작일 (YYYY-MM-DD). None이면 기본 기간.
        end : str | None
            종료일 (YYYY-MM-DD). None이면 오늘.

        Returns
        -------
        pl.DataFrame | None
            단일 지표: date (Date), value (Float64) 컬럼.
            전체 지표: date + 각 지표명 컬럼 (wide DataFrame).
            None — HF 데이터셋/ECOS 모듈 미가용 또는 직접 API 실패 시.

        Raises
        ------
        ValueError
            HF 카탈로그 밖 지표를 apiKey 없이 요청한 경우.
        """
        if apiKey is None:
            try:
                from dartlab.gather.bulkData import macroHf
                from dartlab.gather.ecos import catalog as ecos_catalog

                indicator = ecos_catalog.resolveId(indicator)
                ids = ecos_catalog.getAllIds() if scope == "catalog" else self._MACRO_KR
                if indicator:
                    return macroHf.fetchSeries("ecos", indicator, start=start, end=end)
                return macroHf.fetchMulti("ecos", ids, start=start, end=end)
            except Exception as exc:
                if isinstance(exc, ValueError):
                    raise
                log.warning("macro KR HF 실패: %s", exc)
                return None

        try:
            from dartlab.gather.ecos import Ecos
            from dartlab.gather.ecos.types import EcosError
        except ImportError:
            log.debug("ecos 모듈 없음 — KR macro 수집 생략")
            return None
        try:
            ecos = Ecos(apiKey=apiKey)
        except EcosError:
            from dartlab.core.env import promptAndSave

            key = promptAndSave(
                "ECOS_API_KEY",
                label="한국은행 ECOS API 키가 필요합니다.",
                guide="무료 발급: https://ecos.bok.or.kr/api/#/",
            )
            if not key:
                log.info("ECOS_API_KEY 미설정 — KR macro 조회 불가")
                return None
            ecos = Ecos(apiKey=key)
        kwargs: dict = {}
        if start:
            kwargs["start"] = start
        if end:
            kwargs["end"] = end
        try:
            if indicator:
                from dartlab.gather.ecos import catalog as ecos_catalog

                indicator = ecos_catalog.resolveId(indicator)
                return ecos.series(indicator, **kwargs)
            return ecos.compare(self._MACRO_KR, **kwargs)
        except (KeyError, ValueError, OSError, EcosError) as exc:
            log.warning("macro KR 실패: %s", exc)
            return None

    def _macroUS(
        self,
        indicator: str | None,
        *,
        start: str | None,
        end: str | None,
        apiKey: str | None = None,
        scope: str = "default",
    ):
        """US 거시지표 — FRED API 조회.

        Parameters
        ----------
        indicator : str | None
            지표 코드 ("FEDFUNDS", "GDP" 등). None이면 24개 핵심 지표 전체.
        start : str | None
            시작일 (YYYY-MM-DD). None이면 기본 기간.
        end : str | None
            종료일 (YYYY-MM-DD). None이면 오늘.

        Returns
        -------
        pl.DataFrame | None
            단일 지표: date (Date), value (Float64) 컬럼.
            전체 지표: date + 각 지표명 컬럼 (wide DataFrame).
            None — HF 데이터셋/FRED 모듈 미가용 또는 직접 API 실패 시.

        Raises
        ------
        ValueError
            HF 카탈로그 밖 지표를 apiKey 없이 요청한 경우.
        """
        if apiKey is None:
            try:
                from dartlab.gather.bulkData import macroHf
                from dartlab.gather.fred import catalog as fred_catalog

                ids = fred_catalog.getAllIds() if scope == "catalog" else self._MACRO_US
                if indicator:
                    return macroHf.fetchSeries("fred", indicator, start=start, end=end)
                return macroHf.fetchMulti("fred", ids, start=start, end=end)
            except Exception as exc:
                if isinstance(exc, ValueError):
                    raise
                log.warning("macro US HF 실패 (indicator=%s): %s", indicator or "ALL", exc)
                return None

        try:
            from dartlab.gather.fred import Fred
            from dartlab.gather.fred.types import FredError
        except ImportError:
            log.debug("fred 모듈 없음 — US macro 수집 생략")
            return None
        try:
            fred = Fred(apiKey=apiKey)
        except FredError:
            from dartlab.core.env import promptAndSave

            key = promptAndSave(
                "FRED_API_KEY",
                label="FRED API 키가 필요합니다.",
                guide="무료 발급: https://fred.stlouisfed.org/docs/api/api_key.html",
            )
            if not key:
                log.info("FRED_API_KEY 미설정 — US macro 조회 불가")
                return None
            fred = Fred(apiKey=key)
        kwargs: dict = {}
        if start:
            kwargs["start"] = start
        if end:
            kwargs["end"] = end
        try:
            if indicator:
                return fred.series(indicator, **kwargs)
            return fred.compare(self._MACRO_US, **kwargs)
        except (KeyError, ValueError, OSError, FredError) as exc:
            log.warning("macro US 실패 (indicator=%s): %s", indicator or "ALL", exc)
            return None
