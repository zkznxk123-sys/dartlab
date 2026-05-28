"""SDMX (Statistical Data and Metadata eXchange) 통합 client — ECB/BIS/OECD/IMF.

4 provider 모두 SDMX-JSON 응답 (BIS 는 XML 도 제공하나 JSON 우선) 을 받아서
polars DataFrame ``(date, value, dimension_id, dimension_label)`` 형식으로 정규화.
provider 별 base URL 차이만 ``PROVIDER_ENDPOINTS`` 에 박고 나머지 파싱은 공통화.

```python
from dartlab.gather.infra.sdmxClient import SdmxClient
client = SdmxClient()
df = client.fetch("ECB", "BSI", "M.U2.Y.V.M30.X.1.U2.2300.Z01.E",
                  startPeriod="2020-01", endPeriod="2024-12")
```

호출 흐름:
1. PROVIDER_ENDPOINTS lookup → base URL
2. URL 빌드 (`{base}/data/{dataflow}/{key}?startPeriod=...&endPeriod=...`)
3. httpx GET (Accept: application/vnd.sdmx.data+json;version=1.0.0-wd)
4. ``_parseSdmxJson`` → polars DataFrame

미등록 provider 또는 응답 schema 변경 시 ``SdmxClientError`` raise.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

import httpx
import polars as pl

log = logging.getLogger(__name__)


class SdmxClientError(Exception):
    """SDMX 응답 파싱 또는 HTTP 실패."""


@dataclass(frozen=True, slots=True)
class _ProviderEndpoint:
    """provider 별 base URL + 응답 형식 메타."""

    base_url: str
    accept_header: str
    name: str


# provider → endpoint. 신규 provider 추가는 본 dict 에만.
PROVIDER_ENDPOINTS: dict[str, _ProviderEndpoint] = {
    "ECB": _ProviderEndpoint(
        base_url="https://data-api.ecb.europa.eu/service",
        accept_header="application/vnd.sdmx.data+json;version=1.0.0-wd",
        name="ECB Data Portal",
    ),
    "BIS": _ProviderEndpoint(
        base_url="https://stats.bis.org/api/v1",
        accept_header="application/vnd.sdmx.data+json;version=1.0.0-wd",
        name="BIS Statistics",
    ),
    "OECD": _ProviderEndpoint(
        base_url="https://sdmx.oecd.org/public/rest",
        accept_header="application/vnd.sdmx.data+json;version=1.0.0-wd",
        name="OECD SDMX",
    ),
    "IMF": _ProviderEndpoint(
        base_url="https://sdmxcentral.imf.org/ws/public/sdmxapi/rest",
        accept_header="application/vnd.sdmx.data+json;version=1.0.0-wd",
        name="IMF SDMX Central",
    ),
}

DEFAULT_TIMEOUT = 30.0


class SdmxClient:
    """SDMX-JSON 통합 fetch client.

    Attributes:
        _session: 재사용 httpx.Client.
        _timeout: 요청 타임아웃 (초).
    """

    def __init__(self, *, timeout: float = DEFAULT_TIMEOUT) -> None:
        self._session = httpx.Client(
            headers={"User-Agent": "dartlab-sdmx/1.0"},
            follow_redirects=True,
        )
        self._timeout = timeout

    def fetch(
        self,
        provider: str,
        dataflow: str,
        key: str,
        *,
        startPeriod: str | None = None,
        endPeriod: str | None = None,
    ) -> pl.DataFrame:
        """provider 의 1 series 시계열 fetch → ``(date, value)`` DataFrame.

        Sig: ``fetch(provider, dataflow, key, *, startPeriod=None, endPeriod=None) -> pl.DataFrame``

        Capabilities: SDMX-JSON GET + observation 추출 + polars DataFrame 정규화.
        AIContext: ECB/BIS/OECD/IMF facade 의 backend — 4 provider 공통 진입.
        Guide: SDMX-JSON 1.0 만 지원. provider 별 응답 미세 차이는 ``_parseSdmxJson`` 흡수.
        When: provider catalog 의 1 indicator → 시계열 조회.
        How: PROVIDER_ENDPOINTS lookup → URL 빌드 → httpx GET → ``_parseSdmxJson`` → DataFrame.

        Args:
            provider: ``"ECB"``/``"BIS"``/``"OECD"``/``"IMF"`` 중 하나.
            dataflow: SDMX dataflow ID (예: ECB ``"BSI"``, OECD ``"DSD_SHA"``).
            key: 차원 키 (점 구분). SDMX 표준 — ``"FREQ.REF_AREA.IND.UNIT_MEASURE"``.
            startPeriod: 시작 (예: ``"2020-01"`` / ``"2020"``). None 이면 전 기간.
            endPeriod: 종료. None 이면 현재.

        Returns:
            DataFrame schema:
                - ``date`` : pl.Date — 관측 시점 (frequency 따라 일/월/분기)
                - ``value`` : pl.Float64 — 관측값
                - ``provider`` : pl.Utf8 — provider 코드
                - ``dataflow`` : pl.Utf8 — dataflow ID
                - ``key`` : pl.Utf8 — 차원 키

        Raises:
            SdmxClientError: 미등록 provider / 4xx-5xx / JSON schema 불일치.

        Example:
            >>> df = SdmxClient().fetch("ECB", "BSI",
            ...     "M.U2.Y.V.M30.X.1.U2.2300.Z01.E",
            ...     startPeriod="2020-01")

        See Also:
            ``_parseSdmxJson`` — 응답 정규화.
            ``PROVIDER_ENDPOINTS`` — 신규 provider 추가 지점.
        """
        if provider not in PROVIDER_ENDPOINTS:
            available = ", ".join(sorted(PROVIDER_ENDPOINTS))
            raise SdmxClientError(f"미등록 SDMX provider: '{provider}'. 가용: {available}")
        endpoint = PROVIDER_ENDPOINTS[provider]

        url = f"{endpoint.base_url}/data/{dataflow}/{key}"
        params: dict[str, str] = {}
        if startPeriod:
            params["startPeriod"] = startPeriod
        if endPeriod:
            params["endPeriod"] = endPeriod

        headers = {"Accept": endpoint.accept_header}
        try:
            resp = self._session.get(url, params=params, headers=headers, timeout=self._timeout)
        except httpx.HTTPError as exc:
            raise SdmxClientError(f"{provider} HTTP 실패: {exc}") from exc

        if resp.status_code >= 400:
            raise SdmxClientError(f"{provider} HTTP {resp.status_code}: {resp.text[:200]}")

        try:
            payload = resp.json()
        except ValueError as exc:
            raise SdmxClientError(f"{provider} JSON 파싱 실패: {exc}") from exc

        df = _parseSdmxJson(payload)
        return df.with_columns(
            pl.lit(provider).alias("provider"),
            pl.lit(dataflow).alias("dataflow"),
            pl.lit(key).alias("key"),
        )

    def close(self) -> None:
        """HTTP 세션 종료 — connection pool 정리."""
        self._session.close()


def _parseSdmxJson(payload: dict) -> pl.DataFrame:
    """SDMX-JSON 응답 → ``(date, value)`` DataFrame.

    Sig: ``_parseSdmxJson(payload) -> pl.DataFrame``

    Capabilities: SDMX-JSON 1.0 데이터셋의 첫 series 만 추출 + 시간 축 매핑.
    AIContext: ``SdmxClient.fetch`` 의 응답 정규화 — 사용자 호출 금지.
    Guide: 다중 series 응답은 첫 번째만 사용 (1 dataflow + 1 key = 1 series 전제).
    When: SDMX GET 200 직후.
    How: dataSets[0].series 첫 키 → observations dict → structure.observation 시간 축 매핑.

    Args:
        payload: SDMX-JSON 응답 dict.

    Returns:
        DataFrame ``(date: pl.Date, value: pl.Float64)``. observation 0 건 시 빈 DF.

    Raises:
        SdmxClientError: dataSets / structure 누락 시.

    Example:
        내부 헬퍼.

    See Also:
        ``SdmxClient.fetch`` — caller.
    """
    if "dataSets" not in payload or not payload["dataSets"]:
        raise SdmxClientError("dataSets 누락 또는 빈 배열")
    if "structure" not in payload:
        raise SdmxClientError("structure 누락")

    series_dict = payload["dataSets"][0].get("series", {})
    if not series_dict:
        return pl.DataFrame(schema={"date": pl.Date, "value": pl.Float64})

    obs_dim = payload["structure"].get("dimensions", {}).get("observation", [])
    if not obs_dim:
        raise SdmxClientError("structure.dimensions.observation 누락")
    # 첫 observation dimension 의 values = 시간 축
    time_values = obs_dim[0].get("values", [])
    period_ids = [v.get("id", "") for v in time_values]

    # 첫 series 만 사용
    first_series_key = next(iter(series_dict))
    observations = series_dict[first_series_key].get("observations", {})

    rows_date: list[str] = []
    rows_value: list[float | None] = []
    for idx_str, obs_arr in observations.items():
        idx = int(idx_str)
        if idx >= len(period_ids):
            continue
        date_str = period_ids[idx]
        if not isinstance(obs_arr, list) or not obs_arr:
            continue
        v = obs_arr[0]
        rows_date.append(date_str)
        rows_value.append(float(v) if v is not None else None)

    if not rows_date:
        return pl.DataFrame(schema={"date": pl.Date, "value": pl.Float64})

    # SDMX period 다양 (YYYY / YYYY-MM / YYYY-MM-DD / YYYY-Qn) — 정공법 python 파싱.
    # polars when/then 은 모든 branch 평가하므로 cast 실패 위험. python loop 단순 + 안전.
    from datetime import date as _date

    dates: list[_date | None] = []
    for raw in rows_date:
        dates.append(_periodToDate(raw))
    df = pl.DataFrame({"date": dates, "value": rows_value})
    return df.select(["date", "value"]).sort("date")


def _periodToDate(raw: str):
    """SDMX period 문자열 → datetime.date.

    포맷:
        - ``YYYY`` → ``YYYY-01-01``
        - ``YYYY-MM`` → ``YYYY-MM-01``
        - ``YYYY-MM-DD`` → 그대로
        - ``YYYY-Qn`` (n=1..4) → ``YYYY-{(n-1)*3+1:02d}-01``

    Returns None on 파싱 실패.
    """
    from datetime import date as _date

    if not raw:
        return None
    try:
        if "-Q" in raw and len(raw) == 7:  # YYYY-Qn
            year = int(raw[:4])
            q = int(raw[6])
            month = (q - 1) * 3 + 1
            return _date(year, month, 1)
        if len(raw) == 4:  # YYYY
            return _date(int(raw), 1, 1)
        if len(raw) == 7:  # YYYY-MM
            return _date(int(raw[:4]), int(raw[5:7]), 1)
        if len(raw) == 10:  # YYYY-MM-DD
            return _date(int(raw[:4]), int(raw[5:7]), int(raw[8:10]))
    except (ValueError, IndexError):
        return None
    return None
