"""DART finance — XBRL parquet → account×period 정규화 (statementWide 엔진).

요구: 재무제표 5종(BS/IS/CIS/CF/SCE)+ratios 의 정규화 wide. 계정매퍼는 ``mapping/``
한 경계로 격리(나중 통째 swap), SCE 는 ``sce/`` 묶음. caller 는 본 공개 표면만
import (deep leaf path 금지 — feedback_clean_module_tree).
"""

from __future__ import annotations

from dartlab.core.utils.extract import (
    getAnnualValues,
    getLatest,
    getRevenueGrowth3Y,
    getTTM,
)

from .mapping import AccountMapper
from .pivot import buildAnnual, buildCumulative, buildTimeseries
from .scanAccount import scanAccount, scanRatio, scanRatioList
from .sce import buildSceAnnual, buildSceMatrix

__all__ = [
    "AccountMapper",
    "buildAnnual",
    "buildCumulative",
    "buildSceAnnual",
    "buildSceMatrix",
    "buildTimeseries",
    "getAnnualValues",
    "getLatest",
    "getRevenueGrowth3Y",
    "getTTM",
    "scanAccount",
    "scanRatio",
    "scanRatioList",
]
