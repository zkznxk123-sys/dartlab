"""증권사 리서치 메타 수집 — GatherHttpClient 경유 보드 fetch + parse + 해소 (async).

본문은 받지 않고 메타만(제목·URL·날짜·구분·종목). 카테고리별 실패는 격리하고,
(증권사·제목·발간일) 해시로 중복 제거한다. 빅3+하나는 SPA 라 enabled=False(deferred).
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from .config import BROKERS
from .parse import PARSERS
from .resolve import _extractOpinion, _resolveTicker
from .schema import ReportMeta

if TYPE_CHECKING:
    from ...infra.http import GatherHttpClient

log = logging.getLogger(__name__)


def _decode(content: bytes, text: str, enc: str | None) -> str:
    """enc 지정 시 raw bytes 를 해당 인코딩으로 디코드, 아니면 httpx 가 고른 text 사용."""
    if enc:
        return content.decode(enc, errors="replace")
    return text


def _detectBroken(brokerCounts: dict[str, int], enabledKeys: list[str]) -> list[str]:
    """수율 가드 — enabled 증권사 중 수집 0행인 곳(셀렉터 깨짐 의심) 반환.

    스크래핑 제품이 죽는 가장 흔한 이유 = '200 OK + 0행' 조용한 깨짐(HTML 구조 변경).
    enabled 인데 결과 0건이면 파서가 깨졌을 가능성 → 운영자에게 surface (PRD 03 §4).
    """
    return sorted(k for k in enabledKeys if brokerCounts.get(k, 0) == 0)


async def _fetchBroker(key: str, cfg: dict, client: "GatherHttpClient") -> list[ReportMeta]:
    """증권사 1곳의 모든 카테고리를 fetch+parse. 카테고리별 실패는 격리(로그 후 skip)."""
    parser = PARSERS.get(key)
    if parser is None:
        return []
    out: list[ReportMeta] = []
    for label, url in cfg["categories"].items():
        try:
            resp = await client.get(url)
            html = _decode(resp.content, resp.text, cfg.get("enc"))
            out.extend(parser(html, label, url))
        except Exception as exc:  # noqa: BLE001 — 카테고리별 실패 격리
            log.warning("brokerage %s/%s fetch 실패: %s", key, label, exc)
    return out


async def _fetchAsync(
    client: "GatherHttpClient",
    *,
    brokers: list[str] | None = None,
    resolveTickers: bool = True,
    limit: int | None = None,
) -> list[ReportMeta]:
    """enabled 증권사 리서치 메타 수집 → ReportMeta 리스트 (증권사별 실패 격리 + dedup).

    Args:
        client: GatherHttpClient (rate limit + retry).
        brokers: 수집할 broker key 리스트. None 이면 enabled 전체.
        resolveTickers: True 면 제목→종목코드 해소(명시코드 우선·corpCode graceful).
        limit: 반환 최대 건수. None 이면 무제한 (수집된 전체).

    Returns:
        list[ReportMeta] — (증권사·제목·발간일) 기준 중복 제거. limit 지정 시 앞 N건.

    Raises:
        없음 — 증권사·카테고리별 실패는 격리(로그 후 skip).

    Example::

        items = await fetchAsync(client, brokers=["miraeasset"], limit=50)
    """
    keys = brokers or [k for k, v in BROKERS.items() if v.get("enabled")]
    seen: set[str] = set()
    out: list[ReportMeta] = []
    for key in keys:
        cfg = BROKERS.get(key)
        if cfg is None:
            continue
        try:
            rows = await _fetchBroker(key, cfg, client)
        except Exception as exc:  # noqa: BLE001 — 증권사별 실패 격리
            log.warning("brokerage %s fetch 실패: %s", key, exc)
            rows = []
        for r in rows:
            rid = r.reportId()
            if rid in seen:
                continue
            seen.add(rid)
            r.opinion = _extractOpinion(r.title)
            if resolveTickers:
                r.ticker = _resolveTicker(r.title)
            out.append(r)
            if limit is not None and len(out) >= limit:
                return out
    return out
