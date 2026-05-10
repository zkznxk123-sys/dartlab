"""거버넌스 전수 스캔 — 지분율, 사외이사, pay ratio, 감사의견, 소액주주 → 종합 등급.

Public API:
    scan_governance()  → pl.DataFrame (전체 상장사 거버넌스 등급)
"""

from __future__ import annotations

import polars as pl

from dartlab.core.logger import getLogger

_log = getLogger(__name__)


from dartlab.scan.governance.scanner import (
    scanAuditOpinion,
    scanMajorHolderPct,
    scanMinorityHolder,
    scanOutsideDirectors,
    scanPayRatio,
)
from dartlab.scan.governance.scorer import (
    grade,
    scoreAudit,
    scoreMinority,
    scoreOutsideRatio,
    scoreOwnership,
    scorePayRatio,
)


def scanGovernance(*, verbose: bool = True) -> pl.DataFrame:
    """전체 상장사 거버넌스 스캔 → 종합 등급 DataFrame.

    컬럼: 종목코드, 지분율, 사외이사비율, 중도사임, 겸직, pay_ratio,
          감사의견, 소액주주지분, S_지분, S_사외, S_보수, S_감사, S_분산,
          총점, 등급, 유효축수
    """

    def _say(msg: str) -> None:
        if verbose:
            _log.info(msg)

    _say("1/5 최대주주 지분율...")
    holder_map = scanMajorHolderPct()
    _say(f"  → {len(holder_map)}종목")

    _say("2/5 사외이사 비율...")
    outside_map = scanOutsideDirectors()
    _say(f"  → {len(outside_map)}종목")

    _say("3/5 pay ratio...")
    pay_ratio_map = scanPayRatio()
    _say(f"  → {len(pay_ratio_map)}종목")

    _say("4/5 감사의견...")
    audit_map = scanAuditOpinion()
    _say(f"  → {len(audit_map)}종목")

    _say("5/5 소액주주 지분율...")
    minority_map = scanMinorityHolder()
    _say(f"  → {len(minority_map)}종목")

    all_codes = set(holder_map) | set(outside_map) | set(pay_ratio_map) | set(audit_map) | set(minority_map)

    results = []
    for code in all_codes:
        ownership = holder_map.get(code)
        outside_info = outside_map.get(code, {})
        outside_ratio = outside_info.get("사외이사비율") if outside_info else None
        resign = outside_info.get("중도사임", 0) if outside_info else 0
        concurrent = outside_info.get("겸직", 0) if outside_info else 0
        pay_r = pay_ratio_map.get(code)
        audit = audit_map.get(code)
        minority = minority_map.get(code)

        s1 = scoreOwnership(ownership)
        s2 = scoreOutsideRatio(outside_ratio, resign=resign, concurrent=concurrent)
        s3 = scorePayRatio(pay_r)
        s4 = scoreAudit(audit)
        s5 = scoreMinority(minority)
        total = s1 + s2 + s3 + s4 + s5
        g = grade(total)
        n_valid = sum(1 for v in [ownership, outside_ratio, pay_r, audit, minority] if v is not None)

        results.append(
            {
                "stockCode": code,
                "지분율": round(ownership, 1) if ownership is not None else None,
                "사외이사비율": round(outside_ratio, 1) if outside_ratio is not None else None,
                "중도사임": resign,
                "겸직": concurrent,
                "pay_ratio": round(pay_r, 1) if pay_r is not None else None,
                "감사의견": audit or "",
                "소액주주지분": round(minority, 1) if minority is not None else None,
                "S_지분": s1,
                "S_사외": s2,
                "S_보수": s3,
                "S_감사": s4,
                "S_분산": s5,
                "총점": total,
                "등급": g,
                "유효축수": n_valid,
            }
        )

    df = pl.DataFrame(results)
    _say(f"거버넌스 스캔 완료: {df.shape[0]}종목, 5/5")
    return df


__all__ = ["scan_governance"]
