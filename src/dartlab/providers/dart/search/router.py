"""결정론 intent 라우터 — 질의 → 공시 이벤트 예측 → canon 본문어 확장 (content lane R* 의 확장축 2).

IDF 가중 bigram 라우팅(학습·임베딩 0). 이벤트별 시드 질의에서 route 가중치를 도출하되,
이벤트 34%+ 에 등장하는 bigram(glue: "회사·있어" 류)은 제거하고 이벤트당 상위 120 bigram 만
유지해 모델을 bounded(~수 KB)로 고정한다. report_nm 은 query-time 미사용(평가 누수 차단).

artifact 계약: ``router.json`` = ``{"v": 1, "events": {event: {"route": {bigram: w}, "canon": [...]}}}``
— 빌드는 운영 스크립트(buildSearchMain)가 events.json 시드에서 도출해 인덱스와 동거 배포,
런타임은 부재 시 None 으로 graceful(라우팅 lane 생략, plain BM25 보존).
"""

from __future__ import annotations

import json
import math
from collections import Counter
from pathlib import Path

from dartlab.providers.dart.search.fieldIndex import _activeIndexDir, tokenizeContent

ROUTER_VERSION = 1
GLUE_FRAC = 0.34  # 이벤트 34%+ 공유 bigram = glue 제거
ROUTE_TOPK = 120  # 이벤트당 route bigram 상한 (bounded 모델)


def buildRouterModel(events: dict[str, dict]) -> dict:
    """이벤트 spec → bounded 라우터 모델 (router.json 내용물).

    Args:
        events: ``{event: {"router": [시드 질의...], "canon": [본문어...]}}`` spec.

    Raises:
        없음 (빈 spec 이면 빈 events 모델).

    Example:
        >>> m = buildRouterModel({"dividend": {"router": ["배당 얼마 줘?"], "canon": ["배당금"]}})
        >>> m["v"]
        1

    Returns:
        dict — ``{"v": 1, "events": {event: {"route": {bigram: weight}, "canon": [...]}}}``.
    """
    names = list(events)
    bagf: dict[str, Counter] = {ev: Counter() for ev in names}
    for ev, spec in events.items():
        for q in spec.get("router", []):
            for bg in tokenizeContent(q):
                bagf[ev][bg] += 1
    ni = max(1, len(names))
    dfi: Counter = Counter()
    for ev in names:
        for bg in bagf[ev]:
            dfi[bg] += 1
    # glue = 이벤트 34%+ 공유 bigram. 단 최소 2개 이벤트 공유여야 glue (이벤트 수가 적을 때
    # 전부가 glue 로 오판되는 퇴화 차단 — 12 이벤트 프로덕션에선 4.08 로 원식과 동일).
    glue = {bg for bg, d in dfi.items() if d >= max(2.0, ni * GLUE_FRAC)}
    idf = {bg: math.log((ni + 1) / (d + 0.5)) for bg, d in dfi.items()}
    out: dict[str, dict] = {}
    for ev in names:
        dl = math.sqrt(sum(bagf[ev].values())) or 1.0
        w = {bg: round(idf[bg] * c / dl, 5) for bg, c in bagf[ev].items() if bg not in glue}
        out[ev] = {
            "route": dict(sorted(w.items(), key=lambda kv: -kv[1])[:ROUTE_TOPK]),
            "canon": list(events[ev].get("canon", [])),
        }
    return {"v": ROUTER_VERSION, "events": out}


def loadRouterModel(inDir: Path | None = None) -> dict | None:
    """router.json 로드. 부재·파손·버전 불일치 시 None (라우팅 lane graceful 생략).

    Args:
        inDir: 인덱스 디렉터리. None 이면 활성 인덱스 디렉터리(_activeIndexDir).

    Raises:
        없음 (OSError/JSONDecodeError 는 None 으로 흡수).

    Example:
        >>> loadRouterModel(Path("/nonexistent")) is None
        True

    Returns:
        dict 또는 None — buildRouterModel 형태의 모델.
    """
    path = (inDir or _activeIndexDir()) / "router.json"
    if not path.exists():
        return None
    try:
        model = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(model, dict) or model.get("v") != ROUTER_VERSION or "events" not in model:
        return None
    return model


def predictEvent(model: dict, query: str) -> str | None:
    """질의 → 최상위 이벤트 (모든 이벤트 0 점이면 None = 미라우팅).

    Args:
        model: buildRouterModel/loadRouterModel 산출 모델.
        query: 자연어 질의.

    Raises:
        없음.

    Example:
        >>> m = buildRouterModel({"dividend": {"router": ["배당 얼마나 줘?"], "canon": []}})
        >>> predictEvent(m, "배당 언제 주나")
        'dividend'

    Returns:
        str 또는 None — 예측 이벤트 키.
    """
    qc = Counter(tokenizeContent(query))
    best, bestScore = None, 0.0
    for ev, spec in model.get("events", {}).items():
        route = spec.get("route", {})
        s = sum(c * route.get(bg, 0.0) for bg, c in qc.items())
        if s > bestScore:
            best, bestScore = ev, s
    return best


def routeCanon(model: dict | None, query: str) -> list[str]:
    """질의 → 예측 이벤트의 canon 본문어. 모델 부재·미라우팅이면 빈 리스트 (always-safe).

    Args:
        model: 라우터 모델 (None 허용 — 빈 리스트 반환).
        query: 자연어 질의.

    Raises:
        없음.

    Example:
        >>> routeCanon(None, "배당")
        []

    Returns:
        list[str] — canon 본문어 (확장 lane 의 0.5 가중 대상).
    """
    if not model:
        return []
    ev = predictEvent(model, query)
    if not ev:
        return []
    return list(model.get("events", {}).get(ev, {}).get("canon", []))
