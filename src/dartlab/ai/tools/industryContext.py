"""산업 컨텍스트 badge — Track E (5 phase 라이프사이클 + 밸류체인 peers).

Company.industry() (raw 산업 매핑) + industry.calcs.lifecycle (시계열 phase) 합성.
LLM tool 이 아니라 engineCall.Company.show 응답에 자동 부착되는 헬퍼.

5 phase (UI 표시 SSOT — 플랜 결정 박음):
- 도입: yoy >= 30% — 강한 형성기
- 성장: 10% <= yoy < 30%
- 성숙: 0% <= yoy < 10%
- 재도약: 직전 쇠퇴 후 최근 성장으로 전환된 시계열 패턴 (별도 감지)
- 쇠퇴: yoy < 0%

backend lifecycle 은 4 phase (도입·성장·성숙·쇠퇴) 만 emit. "재도약" 은 본 모듈 안에서 시계열
3 행 패턴 (쇠퇴 → 성장/성숙) 으로 derive — 단일 YoY 로 안 잡히는 turnaround 신호.
"""

from __future__ import annotations

from typing import Any

from dartlab.core.confidence import baseScore

_REBOUND_TRIGGER = ("쇠퇴",)
_REBOUND_FOLLOWERS = ("성장", "도입")


def _detectRebound(phases: list[str]) -> bool:
    """최근 2~3 phase 가 (쇠퇴 → 성장|도입) 패턴이면 재도약 신호."""
    if len(phases) < 2:
        return False
    last = phases[-1]
    if last not in _REBOUND_FOLLOWERS:
        return False
    prior = phases[-3:-1] if len(phases) >= 3 else phases[:-1]
    return any(p in _REBOUND_TRIGGER for p in prior)


def _latestPhase(industryId: str) -> tuple[str, list[str]]:
    """industry 시계열 → (현재 phase, 전체 phase 리스트). 실패 시 ('unknown', [])."""
    if not industryId:
        return "unknown", []
    try:
        from dartlab.industry.calcs.lifecycle import classifyLifecycle
    except ImportError:
        return "unknown", []
    try:
        df = classifyLifecycle(industryId)
    except Exception:
        return "unknown", []
    if df is None or df.is_empty() or "phase" not in df.columns:
        return "unknown", []
    rows = df.sort("연도").to_dicts()
    phases = [str(r.get("phase")) for r in rows if r.get("phase")]
    if not phases:
        return "unknown", []
    current = phases[-1]
    if _detectRebound(phases):
        current = "재도약"
    return current, phases


def getIndustryBadge(company: Any) -> dict[str, Any] | None:
    """Company → industry badge dict 또는 None.

    반환 키:
        industryId (str) — "semiconductor" 등 industry node id.
        industryName (str) — 한국어 표시명.
        stageName (str | None) — 공정 단계 (예: "전공정(FAB)").
        role (str | None) — 제조/설계 등.
        stream (str | None) — upstream/midstream/downstream.
        phase (str) — 도입/성장/성숙/재도약/쇠퇴/unknown (5 phase SSOT).
        peers (list[dict]) — 상위 3 종목 {stockCode, corpName}.
        confidence (int) — 0-100 (산업 매핑 confidence × 100 → int).
        confidenceMethod (str) — "ratio".

    Company.industry() 실패 시 None.
    """
    if company is None or not hasattr(company, "industry"):
        return None
    try:
        raw = company.industry()
    except Exception:
        return None
    if not isinstance(raw, dict):
        return None
    industryId = str(raw.get("industry") or "")
    phase, _ = _latestPhase(industryId)
    rawConfidence = raw.get("confidence")
    if isinstance(rawConfidence, (int, float)):
        confInt = max(0, min(100, int(round(float(rawConfidence) * 100))))
    else:
        confInt = baseScore("ratio")
    peersRaw = raw.get("peers") or []
    peers: list[dict[str, Any]] = []
    for p in peersRaw[:3]:
        if not isinstance(p, dict):
            continue
        peers.append(
            {
                "stockCode": str(p.get("stockCode") or ""),
                "corpName": str(p.get("corpName") or ""),
            }
        )
    return {
        "industryId": industryId,
        "industryName": str(raw.get("industryName") or industryId),
        "stage": raw.get("stage"),
        "stageName": raw.get("stageName"),
        "role": raw.get("role"),
        "stream": raw.get("stream"),
        "phase": phase,
        "peers": peers,
        "confidence": confInt,
        "confidenceMethod": "ratio",
    }


__all__ = ["getIndustryBadge"]
