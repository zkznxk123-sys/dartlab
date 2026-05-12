"""DataEntry — finance 카테고리 진입점 (Cut 8 분할).

단일 진실의 원천은 list 자체. 로직은 ``core/registry.py``.
"""

from __future__ import annotations

from dartlab.core.dataEntry import ColumnMeta, DataEntry  # noqa: F401

_FINANCE_ENTRIES: list[DataEntry] = [
    # ═══════════════════════════════════════════════════════
    # finance — 시계열 재무제표
    # ═══════════════════════════════════════════════════════
    DataEntry(
        name="annual.IS",
        label="손익계산서(연도별)",
        category="finance",
        dataType="timeseries",
        description="연도별 손익계산서 시계열. 매출액, 영업이익, 순이익 등 전체 계정.",
        requires="finance",
        columns=(ColumnMeta("항목", "K-IFRS 손익계산서 계정과목"),),
        analysisHints=(
            "매출 성장률(YoY) 계산",
            "영업이익률(영업이익/매출액) 추이",
            "순이익률(당기순이익/매출액) 추이",
            "매출원가율 변동 확인",
        ),
        relatedModules=("annual.BS", "annual.CF"),
        maxRows=50,
    ),
    DataEntry(
        name="annual.BS",
        label="재무상태표(연도별)",
        category="finance",
        dataType="timeseries",
        description="연도별 재무상태표 시계열. 자산, 부채, 자본 전체 계정.",
        requires="finance",
        columns=(ColumnMeta("항목", "K-IFRS 재무상태표 계정과목"),),
        analysisHints=(
            "부채비율(부채총계/자본총계) 추이",
            "유동비율(유동자산/유동부채) 확인",
            "자산 구성 변화 (유형 vs 무형 비중)",
        ),
        relatedModules=("annual.IS", "annual.CF"),
        maxRows=50,
    ),
    DataEntry(
        name="annual.CF",
        label="현금흐름표(연도별)",
        category="finance",
        dataType="timeseries",
        description="연도별 현금흐름표 시계열. 영업/투자/재무활동 현금흐름.",
        requires="finance",
        columns=(ColumnMeta("항목", "K-IFRS 현금흐름표 계정과목"),),
        analysisHints=(
            "영업활동CF가 양수인지 확인 (음수 = 위험)",
            "FCF = 영업활동CF - 자본적지출",
            "재무활동CF로 차입/상환 패턴 파악",
        ),
        relatedModules=("annual.IS", "annual.BS"),
        maxRows=50,
    ),
    DataEntry(
        name="timeseries.IS",
        label="손익계산서(분기별)",
        category="finance",
        dataType="timeseries",
        description="분기별 손익계산서 standalone 시계열.",
        requires="finance",
        relatedModules=("timeseries.BS", "timeseries.CF"),
    ),
    DataEntry(
        name="timeseries.BS",
        label="재무상태표(분기별)",
        category="finance",
        dataType="timeseries",
        description="분기별 재무상태표 시점잔액 시계열.",
        requires="finance",
        relatedModules=("timeseries.IS", "timeseries.CF"),
    ),
    DataEntry(
        name="timeseries.CF",
        label="현금흐름표(분기별)",
        category="finance",
        dataType="timeseries",
        description="분기별 현금흐름표 standalone 시계열.",
        requires="finance",
        relatedModules=("timeseries.IS", "timeseries.BS"),
    ),
]
