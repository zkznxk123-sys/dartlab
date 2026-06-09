"""golden dataset v2 — 10 종 canonical 금융 질문 (마스터 플랜 v2 트랙 5 PR-Q1).

cryptic-discovering-kettle.md v2 트랙 5. 현 ``tests/_attempts/aiQualityBench.py``
의 ``_GOLDEN`` 은 ``expected_substrings`` 평면 list — 답변에 질문 키워드만 있으면
score 100%. 본 v2 schema 는 5 차원 rubric (accuracy / completeness / toolSelection
/ refsQuality / latency) 박힌 엄격 검증.

schema
------
``_GOLDEN_V2`` = list[dict] — 각 dict 의 키:
- id: str
- question: str
- rubric.accuracy.numericChecks: list[{label, patternRegex, groundTruth,
  tolerancePct, groundTruthSource}]
- rubric.completeness: {requiredSlots, forbiddenSlots}
- rubric.toolSelection: {expectedTools, forbiddenTools, matchMode}
- rubric.refsQuality: {minRefCount, expectedKinds}
- rubric.latency: {maxTotalSec, maxFirstChunkMs}
- groundTruthProbe: str | None

groundTruth 는 *정적 기재* (운영자 수동 측정 후 박음) 또는 ``groundTruthProbe``
키로 동적 측정 (예: ``samsungRoe`` → scan.financial.profitability 호출).

본 파일이 PR-Q1 의 _GOLDEN_V2 SSOT. PR-Q3 baseline 박을 때 본 dataset 으로
실 LLM N=10 → strict score 산출 → ``_baselines/aiQualityV2.json`` 저장.
"""

from __future__ import annotations

from typing import Any

_GOLDEN_V2: list[dict[str, Any]] = [
    {
        "id": "q1_roe_basic",
        "question": "삼성전자 ROE",
        "rubric": {
            "accuracy": {
                "numericChecks": [
                    {
                        "label": "samsungRoe2024",
                        "patternRegex": r"ROE[^0-9\-]{0,20}(-?\d+\.?\d*)\s*%",
                        "groundTruth": 8.94,
                        "tolerancePct": 5.0,
                        "groundTruthSource": "scan.financial.profitability.scanProfitability:roe2024",
                    }
                ]
            },
            "completeness": {
                "requiredSlots": ["삼성전자", "005930", "ROE", "%"],
                "forbiddenSlots": ["오류가 발생", "추후 분석"],
            },
            "toolSelection": {
                "expectedTools": ["EngineCall"],
                "forbiddenTools": [],
                "matchMode": "subset",
            },
            "refsQuality": {"minRefCount": 1, "expectedKinds": ["valueRef", "tableRef"]},
            "latency": {"maxTotalSec": 60.0, "maxFirstChunkMs": 5000.0},
        },
        "groundTruthProbe": "samsungRoe",
    },
    {
        "id": "q2_dcf_valuation",
        "question": "삼성전자 적정가격 DCF",
        "rubric": {
            "accuracy": {
                "numericChecks": [
                    {
                        "label": "samsungDcfPerShareKrw",
                        "patternRegex": r"(\d{2,3}[,.]?\d{3})\s*원",
                        "groundTruth": 78000.0,
                        "tolerancePct": 25.0,  # DCF 가정 의존 — 관대
                        "groundTruthSource": "manual:multiStageDcf base scenario 추정",
                    }
                ]
            },
            "completeness": {
                "requiredSlots": ["삼성전자", "DCF", "적정", "원"],
                "forbiddenSlots": ["오류가 발생", "추후 분석"],
            },
            "toolSelection": {
                "expectedTools": ["DCFValuation"],
                "forbiddenTools": ["RunPython"],
                "matchMode": "subset",
            },
            "refsQuality": {"minRefCount": 1, "expectedKinds": ["valueRef", "tableRef", "visualRef"]},
            "latency": {"maxTotalSec": 120.0, "maxFirstChunkMs": 5000.0},
        },
        "groundTruthProbe": None,
    },
    {
        "id": "q3_peer_compare",
        "question": "삼성전자 SK하이닉스 마이크론 비교",
        "rubric": {
            "accuracy": {"numericChecks": []},
            "completeness": {
                "requiredSlots": ["삼성전자", "SK하이닉스", "비교"],
                "forbiddenSlots": ["오류가 발생"],
            },
            "toolSelection": {
                "expectedTools": ["PeerCompareN"],
                "forbiddenTools": ["RunPython"],
                "matchMode": "subset",
            },
            "refsQuality": {"minRefCount": 1, "expectedKinds": ["tableRef"]},
            "latency": {"maxTotalSec": 120.0, "maxFirstChunkMs": 5000.0},
        },
        "groundTruthProbe": None,
    },
    {
        "id": "q4_credit",
        "question": "삼성전자 신용등급",
        "rubric": {
            "accuracy": {
                "numericChecks": []  # 등급은 문자 — 숫자 정확성 검증 없음
            },
            "completeness": {
                "requiredSlots": ["삼성전자", "신용", "등급"],
                "forbiddenSlots": ["오류가 발생"],
            },
            "toolSelection": {
                "expectedTools": ["CreditScorecard"],
                "forbiddenTools": ["RunPython"],
                "matchMode": "subset",
            },
            "refsQuality": {"minRefCount": 1, "expectedKinds": ["valueRef", "tableRef"]},
            "latency": {"maxTotalSec": 150.0, "maxFirstChunkMs": 5000.0},
        },
        "groundTruthProbe": None,
    },
    {
        "id": "q5_sensitivity",
        "question": "삼성전자 DCF 민감도 WACC",
        "rubric": {
            "accuracy": {"numericChecks": []},
            "completeness": {
                "requiredSlots": ["민감도", "WACC", "삼성전자"],
                "forbiddenSlots": ["오류가 발생"],
            },
            "toolSelection": {
                "expectedTools": ["SensitivityAnalysis"],
                "forbiddenTools": ["RunPython"],
                "matchMode": "subset",
            },
            "refsQuality": {"minRefCount": 1, "expectedKinds": ["tableRef", "visualRef"]},
            "latency": {"maxTotalSec": 120.0, "maxFirstChunkMs": 5000.0},
        },
        "groundTruthProbe": None,
    },
    {
        "id": "q6_scenario",
        "question": "금리 100bp 인상 시나리오 영향",
        "rubric": {
            "accuracy": {"numericChecks": []},
            "completeness": {
                "requiredSlots": ["시나리오", "금리"],
                "forbiddenSlots": ["오류가 발생"],
            },
            "toolSelection": {
                "expectedTools": ["ScenarioCompareN", "ScenarioOverlay"],
                "forbiddenTools": ["RunPython"],
                "matchMode": "subset",
            },
            "refsQuality": {"minRefCount": 1, "expectedKinds": ["tableRef"]},
            "latency": {"maxTotalSec": 120.0, "maxFirstChunkMs": 5000.0},
        },
        "groundTruthProbe": None,
    },
    {
        "id": "q7_regression",
        "question": "삼성전자 매출 전망",
        "rubric": {
            "accuracy": {"numericChecks": []},
            "completeness": {
                "requiredSlots": ["삼성전자", "매출"],
                "forbiddenSlots": ["오류가 발생"],
            },
            "toolSelection": {
                "expectedTools": ["RegressionForecast"],
                "forbiddenTools": ["RunPython"],
                "matchMode": "subset",
            },
            "refsQuality": {"minRefCount": 1, "expectedKinds": ["valueRef", "tableRef"]},
            "latency": {"maxTotalSec": 90.0, "maxFirstChunkMs": 5000.0},
        },
        "groundTruthProbe": None,
    },
    {
        "id": "q8_dashboard",
        "question": "삼성전자 한 화면 분석",
        "rubric": {
            "accuracy": {"numericChecks": []},
            "completeness": {
                "requiredSlots": ["삼성전자", "005930"],
                "forbiddenSlots": ["오류가 발생"],
            },
            "toolSelection": {
                "expectedTools": ["CompileFinancialDashboard"],
                "forbiddenTools": ["RunPython"],
                "matchMode": "subset",
            },
            "refsQuality": {"minRefCount": 2, "expectedKinds": ["visualRef", "tableRef"]},
            "latency": {"maxTotalSec": 150.0, "maxFirstChunkMs": 5000.0},
        },
        "groundTruthProbe": None,
    },
    {
        "id": "q9_growth_scan",
        "question": "성장하는 한국 회사 top 5",
        "rubric": {
            "accuracy": {"numericChecks": []},
            "completeness": {
                "requiredSlots": ["성장", "회사"],
                "forbiddenSlots": ["오류가 발생"],
            },
            "toolSelection": {
                "expectedTools": ["EngineCall"],
                "forbiddenTools": [],
                "matchMode": "subset",
            },
            "refsQuality": {"minRefCount": 1, "expectedKinds": ["tableRef"]},
            "latency": {"maxTotalSec": 90.0, "maxFirstChunkMs": 5000.0},
        },
        "groundTruthProbe": None,
    },
    {
        "id": "q10_recall_check",
        "question": "방금 분석한 회사 다시 보여줘",
        "rubric": {
            "accuracy": {"numericChecks": []},
            "completeness": {
                "requiredSlots": ["회사"],
                "forbiddenSlots": ["오류가 발생"],
            },
            "toolSelection": {
                "expectedTools": ["SearchPastSessions"],
                "forbiddenTools": [],
                "matchMode": "subset",
            },
            "refsQuality": {"minRefCount": 0, "expectedKinds": []},
            "latency": {"maxTotalSec": 60.0, "maxFirstChunkMs": 5000.0},
        },
        "groundTruthProbe": None,
    },
]


__all__ = ["_GOLDEN_V2"]
