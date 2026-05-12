"""scan 4축 시장 스냅샷 — 전종목 지표 사전 계산 + percentile 즉시 조회.

rank 엔진의 buildSnapshot/getRank 패턴과 동일.
첫 호출 시 전종목 scan 실행 (~4분) → JSON 저장 → 이후 즉시 조회.

사용법::

    from dartlab.scan.builders.kr.snapshot import buildScanSnapshot, getScanPosition

    buildScanSnapshot()  # 최초 1회
    pos = getScanPosition("005930")
    # → {governance: {value, percentile, ...}, workforce: ..., capital: ..., debt: ...}
"""

from __future__ import annotations

import bisect
import json
import threading
from pathlib import Path

from dartlab.core.logger import getLogger

_log = getLogger(__name__)


def _cacheDir() -> Path:
    """scan 스냅샷 캐시 디렉토리.

    Returns
    -------
    Path
        ~/.dartlab/data/_cache/
    """
    from dartlab import config

    return Path(config.dataDir) / "_cache"


def _cachePath() -> Path:
    """scan 스냅샷 JSON 캐시 경로.

    Returns
    -------
    Path
        ~/.dartlab/data/_cache/scan_snapshot.json
    """
    return _cacheDir() / "scan_snapshot.json"


def buildScanSnapshot(*, verbose: bool = True) -> dict[str, dict]:
    """전종목 scan 4축 핵심 지표 스냅샷 생성.

    기존 scan 함수를 그대로 호출하여 종목별 핵심 지표를 추출한다.
    결과를 JSON으로 저장하여 이후 조회는 즉시 가능.

    Parameters
    ----------
    verbose : bool
        진행 로그 출력 여부.

    Returns
    -------
    dict[str, dict]
        {종목코드: snapshot} 매핑. 각 snapshot:
            governance_score : float | None — 지배구조 총점 (점)
            governance_grade : str | None — 지배구조 등급 (A~E)
            rev_per_employee : float | None — 직원당 매출 (억)
            capital_class : str | None — 주주환원 분류 (환원형/중립/희석형)
            icr : float | None — 이자보상배율 (배)
            debt_risk : str | None — 부채 위험등급 (안전/관찰/주의/고위험)
    """
    if verbose:
        _log.info("[scan] 전종목 스냅샷 빌드 시작...")

    # ── governance: 총점 ──
    if verbose:
        _log.info("  [1/4] governance 스캔...")
    from dartlab.scan.governance.scanner import (
        scanAuditOpinion,
        scanMajorHolderPct,
        scanOutsideDirectors,
        scanPayRatio,
    )
    from dartlab.scan.governance.scorer import (
        grade,
        scoreAudit,
        scoreOutsideRatio,
        scoreOwnership,
        scorePayRatio,
    )

    holder_pct = scanMajorHolderPct()
    outside_ratio = scanOutsideDirectors()
    pay_ratio = scanPayRatio()
    audit_opinion = scanAuditOpinion()

    all_codes = set(holder_pct) | set(outside_ratio) | set(pay_ratio) | set(audit_opinion)
    governance_scores: dict[str, float] = {}
    governance_grades: dict[str, str] = {}
    for code in all_codes:
        s = (
            scoreOwnership(holder_pct.get(code))
            + scoreOutsideRatio(outside_ratio.get(code))
            + scorePayRatio(pay_ratio.get(code))
            + scoreAudit(audit_opinion.get(code))
        )
        governance_scores[code] = s
        governance_grades[code] = grade(s)

    if verbose:
        _log.info("    governance: %d종목", len(governance_scores))

    # ── workforce: 직원당매출 ──
    if verbose:
        _log.info("  [2/4] workforce 스캔...")
    from dartlab.scan.workforce.scanner import scanRevenuePerEmployee

    rev_per_emp = scanRevenuePerEmployee()
    if verbose:
        _log.info("    workforce: %d종목", len(rev_per_emp))

    # ── capital: 분류 ──
    if verbose:
        _log.info("  [3/4] capital 스캔...")
    from dartlab.scan.capital.classifier import classifyReturn
    from dartlab.scan.capital.scanner import (
        scanCapitalChange,
        scanDividend,
        scanTreasuryStock,
    )

    dividends = scanDividend()
    treasury = scanTreasuryStock()
    cap_changes = scanCapitalChange()

    capital_classes: dict[str, str] = {}
    all_cap_codes = set(dividends) | set(treasury) | set(cap_changes)
    for code in all_cap_codes:
        div_info = dividends.get(code, {})
        trs_info = treasury.get(code, {})
        chg_info = cap_changes.get(code, {})

        has_div = div_info.get("배당여부", False)
        hasBuyback = trs_info.get("당기취득", False)
        recent_inc = chg_info.get("최근증자", False)

        cls, _ = classifyReturn(has_div, hasBuyback, recent_inc)
        capital_classes[code] = cls

    if verbose:
        _log.info("    capital: %d종목", len(capital_classes))

    # ── debt: ICR + 위험등급 ──
    if verbose:
        _log.info("  [4/4] debt 스캔...")
    from dartlab.scan.debt.risk import classifyRisk, scanIcr
    from dartlab.scan.debt.scanner import scanBonds

    icr_map = scanIcr()
    bonds_map = scanBonds()

    debt_risk: dict[str, str] = {}
    debt_icr: dict[str, float] = {}
    all_debt_codes = set(icr_map) | set(bonds_map)
    for code in all_debt_codes:
        icr_val = icr_map.get(code)
        bond_info = bonds_map.get(code, {})
        short_pct = bond_info.get("단기비중")
        debt_risk[code] = classifyRisk(icr_val, short_pct)
        if icr_val is not None:
            debt_icr[code] = icr_val

    if verbose:
        _log.info("    debt: %d종목 (ICR %d종목)", len(debt_risk), len(debt_icr))

    # ── 통합 ──
    all_known = set(governance_scores) | set(rev_per_emp) | set(capital_classes) | set(debt_risk)

    snapshot: dict[str, dict] = {}
    for code in all_known:
        snapshot[code] = {
            "governance_score": governance_scores.get(code),
            "governance_grade": governance_grades.get(code),
            "rev_per_employee": rev_per_emp.get(code),
            "capital_class": capital_classes.get(code),
            "icr": debt_icr.get(code),
            "debt_risk": debt_risk.get(code),
        }

    # ── 분포 통계 (percentile 계산용 정렬 배열) ──
    gov_sorted = sorted(v for v in governance_scores.values() if v is not None)
    rpe_sorted = sorted(v for v in rev_per_emp.values() if v is not None)
    icr_sorted = sorted(v for v in debt_icr.values() if v is not None)

    cap_dist = {}
    for cls in capital_classes.values():
        cap_dist[cls] = cap_dist.get(cls, 0) + 1

    distributions = {
        "governance_score": gov_sorted,
        "rev_per_employee": rpe_sorted,
        "icr": icr_sorted,
        "capital_class_dist": cap_dist,
    }

    # ── 저장 ──
    cache_dir = _cacheDir()
    cache_dir.mkdir(parents=True, exist_ok=True)
    payload = {"snapshot": snapshot, "distributions": distributions}
    _cachePath().write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    if verbose:
        _log.info("  [scan] %d종목 스냅샷 저장: %s", len(snapshot), _cachePath())

    return snapshot


# ── 조회 ──

_CACHE: dict | None = None
_CACHE_LOCK = threading.Lock()


def _ensureCache() -> dict | None:
    """스냅샷 JSON 캐시 로드 (thread-safe, lazy).

    Returns
    -------
    dict | None
        {"snapshot": {...}, "distributions": {...}}. 캐시 없으면 None.
    """
    global _CACHE
    if _CACHE is not None:
        return _CACHE
    with _CACHE_LOCK:
        if _CACHE is not None:
            return _CACHE
        path = _cachePath()
        if not path.exists():
            return None
        _CACHE = json.loads(path.read_text(encoding="utf-8"))
    return _CACHE


def _percentile(sortedArr: list[float], value: float) -> float:
    """정렬 배열에서 percentile rank 산출.

    Parameters
    ----------
    sorted_arr : list[float]
        오름차순 정렬된 값 배열.
    value : float
        rank를 산출할 값.

    Returns
    -------
    float
        백분위 순위 (%) — 0.0~100.0.
    """
    if not sortedArr:
        return 0.0
    pos = bisect.bisect_right(sortedArr, value)
    return round(pos / len(sortedArr) * 100, 1)


def getScanPosition(stockCode: str) -> dict | None:
    """종목의 scan 4축 시장 내 위치 조회.

    스냅샷이 없으면 None. buildScanSnapshot() 선행 필요.

    Parameters
    ----------
    stockCode : str
        종목코드 (6자리).

    Returns
    -------
    dict | None
        governance : dict | None
            value : float — 지배구조 총점 (점)
            percentile : float — 백분위 (%)
            grade : str — 등급 (A~E)
            total : int — 전종목 수
        workforce : dict | None
            value : float — 직원당 매출 (억)
            percentile : float — 백분위 (%)
            total : int — 전종목 수
        capital : dict | None
            class : str — 주주환원 분류
            distribution : dict — 분류별 종목 수
        debt : dict | None
            icr : float | None — 이자보상배율 (배)
            percentile : float | None — 백분위 (%)
            risk : str — 위험등급
            total : int — 전종목 수
        스냅샷 없으면 None.
    """
    cache = _ensureCache()
    if cache is None:
        return None

    snapshot = cache.get("snapshot", {})
    dist = cache.get("distributions", {})
    company = snapshot.get(stockCode)
    if company is None:
        return None

    result: dict[str, dict | None] = {}

    # governance
    gov_score = company.get("governance_score")
    gov_sorted = dist.get("governance_score", [])
    if gov_score is not None:
        result["governance"] = {
            "value": gov_score,
            "percentile": _percentile(gov_sorted, gov_score),
            "grade": company.get("governance_grade"),
            "total": len(gov_sorted),
        }
    else:
        result["governance"] = None

    # workforce
    rpe = company.get("rev_per_employee")
    rpe_sorted = dist.get("rev_per_employee", [])
    if rpe is not None:
        result["workforce"] = {
            "value": rpe,
            "percentile": _percentile(rpe_sorted, rpe),
            "total": len(rpe_sorted),
        }
    else:
        result["workforce"] = None

    # capital (이산 → percentile 대신 분류 분포)
    cap_cls = company.get("capital_class")
    cap_dist = dist.get("capital_class_dist", {})
    if cap_cls is not None:
        result["capital"] = {
            "class": cap_cls,
            "distribution": cap_dist,
        }
    else:
        result["capital"] = None

    # debt
    icr = company.get("icr")
    icr_sorted = dist.get("icr", [])
    if icr is not None:
        result["debt"] = {
            "icr": icr,
            "percentile": _percentile(icr_sorted, icr),
            "risk": company.get("debt_risk"),
            "total": len(icr_sorted),
        }
    else:
        debt_risk = company.get("debt_risk")
        if debt_risk:
            result["debt"] = {"icr": None, "percentile": None, "risk": debt_risk, "total": len(icr_sorted)}
        else:
            result["debt"] = None

    return result
