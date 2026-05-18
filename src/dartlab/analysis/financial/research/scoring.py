"""정량 스코어링 프레임워크 — facade. 본체는 `_scoringDescriptive` / `_scoringValuation`.

Piotroski F-Score, Magic Formula, QMJ, Lynch Fair Value,
Buffett Owner Earnings, DuPont 3-factor. 모든 함수는 연간 시계열(buildAnnual 결과)을
입력으로 받는다.
"""

from __future__ import annotations

from dartlab.analysis.financial.research._scoringDescriptive import (
    _latest,
    _latestTwo,
    _round,
    _val,
    calcMagicFormula,
    calcPiotroski,
)
from dartlab.analysis.financial.research._scoringValuation import (
    _identifyDriver,
    calcAllScores,
    calcBuffettOwnerEarnings,
    calcDuPont,
    calcLynchFairValue,
    calcQmj,
)

__all__ = [
    "_identifyDriver",
    "_latest",
    "_latestTwo",
    "_round",
    "_val",
    "calcAllScores",
    "calcBuffettOwnerEarnings",
    "calcDuPont",
    "calcLynchFairValue",
    "calcMagicFormula",
    "calcPiotroski",
    "calcQmj",
]
