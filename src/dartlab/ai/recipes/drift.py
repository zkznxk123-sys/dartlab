"""Recipe drift 진단 — schema drift + insight drift.

stateless. ValidateRecipe 가 호출하지 않음 — 운영자 CLI (`recipes inspect <id>`) 가 호출.

검사 2 종:
- **schemaDrift**: 최근 N run 의 ``errorClass`` 가 KeyError / AttributeError / ImportError 비율 ↑.
  연결된 엔진의 출력 컬럼이 변경됐을 가능성.
- **insightDrift**: 최근 N run 의 headline 값 분포가 baseline 대비 2σ 이탈. 임계 / regime 변경 시그널.

본 모듈은 *진단* 만 — 자동 status 변경 X. 운영자가 출력을 보고 deprecated 결정.
"""

from __future__ import annotations

import statistics
from dataclasses import asdict, dataclass, field
from typing import Any

import polars as pl

_SCHEMA_DRIFT_ERRORS = ("KeyError", "AttributeError", "ImportError", "ColumnNotFoundError")


@dataclass(frozen=True)
class DriftReport:
    """drift 진단 1 회 결과."""

    skillId: str
    schemaDriftRate: float
    schemaDriftWindow: int
    insightDriftSigma: float | None
    notes: list[str] = field(default_factory=list)
    suggestDeprecate: bool = False

    def toDict(self) -> dict[str, Any]:
        """toDict — TODO 한국어 동작 설명."""
        return asdict(self)


def detectDrift(skillId: str, runs: pl.DataFrame, *, recentN: int = 10, baselineN: int = 30) -> DriftReport:
    """최근 run vs baseline 비교 — schema drift + insight drift 진단.

    Parameters
    ----------
    skillId : str
        대상 recipe id.
    runs : pl.DataFrame
        loadRuns 결과. capturedAt 으로 정렬됨.
    recentN : int
        "최근" window run 수.
    baselineN : int
        "baseline" 비교 window run 수 (recent 직전 baselineN 개).

    Returns
    -------
    DriftReport
        schemaDriftRate / insightDriftSigma / suggestDeprecate.
    """
    notes: list[str] = []
    if runs.height < recentN:
        return DriftReport(
            skillId=skillId,
            schemaDriftRate=0.0,
            schemaDriftWindow=0,
            insightDriftSigma=None,
            notes=[f"run count {runs.height} < recentN {recentN} — drift 진단 보류"],
            suggestDeprecate=False,
        )

    sorted_runs = runs.sort("capturedAt")
    recent = sorted_runs.tail(recentN)
    baseline = sorted_runs.slice(max(0, sorted_runs.height - recentN - baselineN), baselineN)

    # schema drift
    recent_errors = [str(e or "") for e in recent["errorClass"].to_list()]
    schema_drift = sum(1 for e in recent_errors if any(token in e for token in _SCHEMA_DRIFT_ERRORS))
    schema_rate = schema_drift / recentN if recentN else 0.0

    # insight drift — headline 수치값의 기대 분포 변화
    def _floats(df: pl.DataFrame) -> list[float]:
        out: list[float] = []
        for v in df["headlineValue"].to_list():
            if v is None:
                continue
            try:
                out.append(float(v))
            except (TypeError, ValueError):
                continue
        return out

    recent_floats = _floats(recent)
    baseline_floats = _floats(baseline)

    if len(baseline_floats) < 5 or len(recent_floats) < 3:
        sigma = None
        notes.append("insight drift 진단에 필요한 baseline / recent 수치 부족")
    else:
        base_mean = statistics.fmean(baseline_floats)
        base_stdev = statistics.pstdev(baseline_floats)
        recent_mean = statistics.fmean(recent_floats)
        if base_stdev <= 0:
            sigma = None
            notes.append("baseline std-dev 0 — drift 진단 불가")
        else:
            sigma = abs(recent_mean - base_mean) / base_stdev

    # suggestDeprecate — schema drift > 50% 또는 insight drift > 2 σ
    suggest = (schema_rate > 0.5) or (sigma is not None and sigma > 2.0)
    if suggest:
        if schema_rate > 0.5:
            notes.append(f"schema drift {schema_rate:.0%} > 50%")
        if sigma is not None and sigma > 2.0:
            notes.append(f"insight drift {sigma:.2f}σ > 2σ")

    return DriftReport(
        skillId=skillId,
        schemaDriftRate=schema_rate,
        schemaDriftWindow=recentN,
        insightDriftSigma=sigma,
        notes=notes,
        suggestDeprecate=suggest,
    )
