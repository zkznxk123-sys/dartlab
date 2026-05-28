"""Gather macro mixin — 거시경제 지표 (KR ECOS + US FRED) 4 메서드."""

from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import polars as pl

from ..infra.telemetry import emitGatherFetch
from .context import GatherMixinContext

log = logging.getLogger(__name__)


class _GatherMacroMixin(GatherMixinContext):
    """거시지표 메서드 모음 — KR/US + Sprint 2 EU/GLOBAL (ECB/BIS/OECD/IMF SDMX)."""

    _KNOWN_MARKETS = {"KR", "US", "EU", "GLOBAL"}

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

    # Sprint 2 PR2 — ECB Data Portal 8 핵심 지표 (SDMX live, HF 미동기)
    _MACRO_EU = [
        "ECB_M3",
        "ECB_HICP",
        "ECB_DEPO_RATE",
        "ECB_MRO_RATE",
        "ECB_UNEMP",
        "ECB_EURUSD",
        "ECB_BUND_10Y",
        "ECB_GDP_EA",
    ]

    # Sprint 2 PR3~5 — BIS + OECD + IMF 핵심 지표 (SDMX live)
    _MACRO_GLOBAL = [
        # BIS — 글로벌 정책금리 4 국 + 환율
        "BIS_POLICY_RATE_US",
        "BIS_POLICY_RATE_EU",
        "BIS_POLICY_RATE_JP",
        "BIS_POLICY_RATE_KR",
        "BIS_EER_BROAD_USD",
        # OECD — 선행지표 + 신뢰지수
        "OECD_LEI",
        "OECD_BCI",
        "OECD_CCI",
        # IMF — 환율 + 원유
        "IMF_FX_USD_KRW",
        "IMF_FX_USD_JPY",
        "IMF_OIL_BRENT",
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
            if market == "EU":
                return self._macroEU(indicator, start=start, end=end)
            if market == "GLOBAL":
                return self._macroGlobal(indicator, start=start, end=end)
            return self._macroUS(indicator, start=start, end=end, apiKey=apiKey, scope=scope)
        finally:
            emitGatherFetch("macro", (time.monotonic() - t0) * 1000, cacheHit=False, market=market)

    def _detectMarket(self, indicator: str) -> str:
        """지표 코드로 market 자동 감지.

        Sprint 2 prefix 룰 (ECB_/BIS_/OECD_/IMF_) 가 KR/US 보다 우선. 그 외:
        ECOS 카탈로그에 있으면 KR, 없으면 US.

        Parameters
        ----------
        indicator : str
            거시지표 코드 ("CPI", "FEDFUNDS", "ECB_M3", "BIS_POLICY_RATE_US" 등).

        Returns
        -------
        str
            "EU" — ``ECB_`` prefix.
            "GLOBAL" — ``BIS_`` / ``OECD_`` / ``IMF_`` prefix.
            "KR" — ECOS 카탈로그 등록.
            "US" — 그 외 (FRED 가정).
        """
        if indicator.startswith("ECB_"):
            return "EU"
        if indicator.startswith(("BIS_", "OECD_", "IMF_")):
            return "GLOBAL"
        try:
            from dartlab.gather.ecos.catalog import getEntry

            if getEntry(indicator):
                return "KR"
        except ImportError:
            pass
        return "US"

    def _macroEU(
        self,
        indicator: str | None,
        *,
        start: str | None,
        end: str | None,
    ):
        """EU 거시지표 — ECB SDMX live fetch.

        Sig: ``_macroEU(indicator, *, start, end) -> pl.DataFrame | None``

        Capabilities: ECB facade 위임 — 단일 indicator 또는 _MACRO_EU 전체.
        AIContext: macro(market="EU") 의 backend.
        Guide: HF 동기화 없음 — 항상 live SDMX. apiKey 불필요 (ECB 무인증).
        When: market="EU" 분기 진입 시.
        How: indicator None 이면 _MACRO_EU compare 흉내 (각 series 호출), 있으면 단일 series.

        Args:
            indicator: ``ECB_`` prefix ID 또는 None.
            start: ``startPeriod`` (예: ``"2020-01"``). None 가능.
            end: ``endPeriod``. None 가능.

        Returns:
            pl.DataFrame | None — SDMX 응답. 실패 시 logger.warning + None.

        Raises:
            없음 — 모든 예외 흡수.

        Example:
            >>> g.macro("EU", "ECB_M3")

        See Also:
            ``dartlab.gather.ecb.Ecb`` — 위임 대상.
        """
        t0 = time.monotonic()
        try:
            try:
                from dartlab.gather.ecb import Ecb
                from dartlab.gather.infra.sdmxClient import SdmxClientError
            except ImportError:
                log.debug("ecb 모듈 없음 — EU macro 수집 생략")
                return None
            e = Ecb()
            try:
                if indicator:
                    return e.series(indicator, startPeriod=start, endPeriod=end)
                # 전체 — _MACRO_EU 8 지표 wide
                import polars as pl

                out: pl.DataFrame | None = None
                for ind in self._MACRO_EU:
                    try:
                        df = e.series(ind, startPeriod=start, endPeriod=end)
                        df = df.select(["date", pl.col("value").alias(ind)])
                        out = df if out is None else out.join(df, on="date", how="full", coalesce=True)
                    except SdmxClientError as exc:
                        log.debug("macro EU %s 실패: %s", ind, exc)
                return out.sort("date") if out is not None else None
            finally:
                e.close()
        except Exception as exc:  # noqa: BLE001 — silent observer
            log.warning("macro EU 실패: %s", exc)
            return None
        finally:
            emitGatherFetch("macroEU", (time.monotonic() - t0) * 1000, cacheHit=False, market="EU")

    def _macroGlobal(
        self,
        indicator: str | None,
        *,
        start: str | None,
        end: str | None,
    ):
        """GLOBAL 거시지표 — BIS/OECD/IMF SDMX live fetch.

        Sig: ``_macroGlobal(indicator, *, start, end) -> pl.DataFrame | None``

        Capabilities: prefix (``BIS_``/``OECD_``/``IMF_``) → 해당 facade 위임.
        AIContext: macro(market="GLOBAL") 의 backend — 3 SDMX provider 공통 진입.
        Guide: indicator 가 None 이면 _MACRO_GLOBAL compare. 단일 indicator 는 prefix 라우팅.
        When: market="GLOBAL" 분기 진입.
        How: indicator prefix → provider 선택 → facade.series 위임.

        Args:
            indicator: ``BIS_``/``OECD_``/``IMF_`` prefix ID 또는 None.
            start: ``startPeriod``.
            end: ``endPeriod``.

        Returns:
            pl.DataFrame | None — wide (전체) 또는 단일 series.

        Raises:
            없음 — 모든 예외 흡수.

        Example:
            >>> g.macro("GLOBAL", "BIS_POLICY_RATE_US")

        See Also:
            ``dartlab.gather.bis.Bis`` · ``dartlab.gather.oecd.Oecd`` · ``dartlab.gather.imf.Imf``.
        """
        t0 = time.monotonic()
        try:
            from dartlab.gather.infra.sdmxClient import SdmxClientError

            try:
                from dartlab.gather.bis import Bis
                from dartlab.gather.imf import Imf
                from dartlab.gather.oecd import Oecd
            except ImportError:
                log.debug("bis/oecd/imf 일부 모듈 없음 — GLOBAL macro 부분 생략")
                return None

            def _factoryFor(ind: str):
                if ind.startswith("BIS_"):
                    return Bis()
                if ind.startswith("OECD_"):
                    return Oecd()
                if ind.startswith("IMF_"):
                    return Imf()
                return None

            if indicator:
                facade = _factoryFor(indicator)
                if facade is None:
                    log.warning("macro GLOBAL prefix 미인식: %s", indicator)
                    return None
                try:
                    return facade.series(indicator, startPeriod=start, endPeriod=end)
                except SdmxClientError as exc:
                    log.warning("macro GLOBAL %s 실패: %s", indicator, exc)
                    return None
                finally:
                    facade.close()

            # 전체 — _MACRO_GLOBAL wide
            import polars as pl

            facades: dict[str, object] = {}
            try:
                out: pl.DataFrame | None = None
                for ind in self._MACRO_GLOBAL:
                    prov = ind.split("_", 1)[0]
                    if prov not in facades:
                        f = _factoryFor(ind)
                        if f is None:
                            continue
                        facades[prov] = f
                    try:
                        df = facades[prov].series(ind, startPeriod=start, endPeriod=end)  # type: ignore[attr-defined]
                        df = df.select(["date", pl.col("value").alias(ind)])
                        out = df if out is None else out.join(df, on="date", how="full", coalesce=True)
                    except SdmxClientError as exc:
                        log.debug("macro GLOBAL %s 실패: %s", ind, exc)
                return out.sort("date") if out is not None else None
            finally:
                for f in facades.values():
                    if hasattr(f, "close"):
                        f.close()  # type: ignore[attr-defined]
        finally:
            emitGatherFetch("macroGlobal", (time.monotonic() - t0) * 1000, cacheHit=False, market="GLOBAL")

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
        t0 = time.monotonic()
        try:
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
        finally:
            emitGatherFetch("macroKR", (time.monotonic() - t0) * 1000, cacheHit=False, market="KR")

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
        t0 = time.monotonic()
        try:
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
        finally:
            emitGatherFetch("macroUS", (time.monotonic() - t0) * 1000, cacheHit=False, market="US")
