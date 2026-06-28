"""세그먼트 경제성 — 부문 OI 미공시 시 peer-reconcile 배분으로 마진 도출 (P1c).

사상: 부문 매출은 공시되는데 부문 OI 가 없다고 마진을 *스킵*하는 게 게으름이다. 연결 OI 를
peer-segment 마진 *구조*로 배분하되, 비례 스케일 k 로 **연결 OI 와 정확히 일치**시켜 도출한다
(상대구조=외부 peer, 절대총합=공시). 날조 아님 — 투명한 배분식 + peer 벤치 + 범위 라벨.
SSOT: 02c. 본 모듈은 순수 배분 수식(reconcileSegmentMargins) — peer 데이터 fetch 는 호출부.
"""

from __future__ import annotations


def reconcileSegmentMargins(
    segRevenues: dict[str, float],
    oiTotal: float,
    peerMargins: dict[str, float],
    peerRanges: dict[str, tuple[float, float]] | None = None,
) -> dict | None:
    """연결 영업이익을 부문에 peer 마진 구조로 배분(reconcile) — Σ=OI_total 보장.

    OIhat_i = k × R_i × m_i^peer,  k = OI_total / Σ(R_i × m_i^peer).
    peer 가 알려주는 *상대* 마진 구조를 회사의 *실제* 연결 OI 에 묶는다. 적자부문
    (m_peer<0)은 분모 왜곡 방지를 위해 양수 부문으로만 k 산출 후 적용.

    Args:
        segRevenues: {부문명: 매출}. 양수 매출 + peerMargins 보유 부문만 사용.
        oiTotal: 연결 영업이익(원). 음수(연결적자) 허용.
        peerMargins: {부문명: peer 마진(소수, 0.12=12%)}. 부문↔peer 산업그룹 사상 결과.
        peerRanges: {부문명: (p25, p75)} peer 마진 분포 범위(소수). 없으면 marginRange=None.

    Returns:
        dict | None: {부문: {revenue, oiDerived, marginDerived(%), marginRange([lo,hi]%|None),
        method="peerReconciled", reconcileK}}. 유효 부문 0 또는 분모 0 시 None.

    Example:
        >>> reconcileSegmentMargins({"A": 100.0, "B": 50.0}, 30.0, {"A": 0.25, "B": 0.10})
        {"A": {"oiDerived": ..., "marginDerived": ..., "reconcileK": ...}, "B": {...}}

    Raises:
        없음 — 입력 부족 시 None.
    """
    segs = {s: float(r) for s, r in segRevenues.items() if r and r > 0 and s in peerMargins}
    if not segs:
        return None
    # 적자 부문 제외하고 k 산출(reconcile 부호 왜곡 방지, R3).
    denom = sum(r * peerMargins[s] for s, r in segs.items() if peerMargins[s] > 0)
    if denom == 0:
        return None
    k = oiTotal / denom
    out: dict[str, dict] = {}
    for s, r in segs.items():
        mPeer = peerMargins[s]
        oiHat = k * r * mPeer
        mHat = oiHat / r if r else 0.0
        rng = None
        if peerRanges and s in peerRanges:
            lo, hi = peerRanges[s]
            rng = [round(k * lo * 100, 1), round(k * hi * 100, 1)]
        out[s] = {
            "revenue": r,
            "oiDerived": round(oiHat),
            "marginDerived": round(mHat * 100, 2),
            "marginRange": rng,
            "method": "peerReconciled",
            "reconcileK": round(k, 3),
        }
    return out


__all__ = ["reconcileSegmentMargins"]
