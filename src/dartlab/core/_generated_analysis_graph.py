"""Analysis Graph generated from capability contracts.

수정하지 마세요. scripts/build/generateSpec.py 를 실행하세요.
"""

import json

ANALYSIS_GRAPH: dict = json.loads(
    r"""
{
    "contracts": {
        "capabilities.valid_key": {
            "contractId": "capabilities.valid_key",
            "kind": "ai_contract",
            "priority": 70,
            "questionTriggers": {
                "any": [
                    "뭐 할 수",
                    "어떻게 써",
                    "사용법",
                    "help",
                    "capabilities"
                ]
            },
            "questionTypes": [
                "meta_help"
            ],
            "requiredEvidence": [
                "valid_key_or_search"
            ],
            "sourceKey": "aiContract.capabilities.valid_key",
            "summary": "capabilities key 오염 방지 계약",
            "tool": "capabilities",
            "toolArgPolicy": [
                "reject_polluted_capabilities_key"
            ],
            "toolMatch": [
                {
                    "tool": "capabilities"
                }
            ],
            "toolNames": [
                "capabilities",
                "Read"
            ]
        },
        "cashflow.primary": {
            "contractId": "cashflow.primary",
            "evidenceSchema": {
                "metricKeys": [
                    "OCF",
                    "FCF",
                    "CAPEX",
                    "metric",
                    "axis"
                ],
                "periodKeys": [
                    "period",
                    "year"
                ],
                "targetKeys": [
                    "stockCode",
                    "target"
                ],
                "valueKeys": [
                    "value",
                    "OCF",
                    "FCF",
                    "CAPEX"
                ]
            },
            "kind": "ai_contract",
            "preflightActions": [
                {
                    "argsTemplate": {
                        "axis": "현금흐름"
                    },
                    "primaryEvidence": true,
                    "tool": "analysis"
                },
                {
                    "argsTemplate": {
                        "freq": "Y",
                        "raw": false,
                        "scope": "consolidated",
                        "topic": "CF"
                    },
                    "primaryEvidence": true,
                    "tool": "show"
                }
            ],
            "priority": 85,
            "questionTriggers": {
                "any": [
                    "현금흐름",
                    "cashflow",
                    "cash flow",
                    "fcf",
                    "ocf"
                ]
            },
            "questionTypes": [
                "cashflow"
            ],
            "requiredEvidence": [
                "target",
                "metric",
                "period",
                "value"
            ],
            "sourceKey": "aiContract.cashflow.primary",
            "summary": "현금흐름 질문 primary evidence 계약",
            "toolNames": [
                "analysis",
                "show",
                "credit",
                "capabilities"
            ],
            "visualPolicy": {
                "preferredType": "chart",
                "requiredFor": [
                    "cashflow"
                ]
            }
        },
        "company.analysis": {
            "artifactPolicy": {
                "primaryCsv": true
            },
            "contractId": "company.analysis",
            "evidenceSchema": {
                "metricKeys": [
                    "metric",
                    "axis",
                    "score",
                    "value"
                ],
                "periodKeys": [
                    "period",
                    "basePeriod",
                    "year"
                ],
                "targetKeys": [
                    "stockCode",
                    "target",
                    "code"
                ],
                "valueKeys": [
                    "value",
                    "score"
                ]
            },
            "priority": 90,
            "questionTypes": [
                "company_compare",
                "cashflow"
            ],
            "requiredEvidence": [
                "target",
                "metric",
                "period",
                "value"
            ],
            "sourceKey": "Company.analysis",
            "tool": "analysis",
            "toolMatch": [
                {
                    "tool": "analysis"
                }
            ],
            "toolNames": [
                "analysis",
                "show",
                "credit",
                "pastInsight",
                "capabilities"
            ]
        },
        "comparison.same_axis": {
            "artifactPolicy": {
                "primaryCsv": true
            },
            "comparisonCompleteness": {
                "minTargets": 2,
                "mode": "same_metric_each_target"
            },
            "contractId": "comparison.same_axis",
            "evidenceSchema": {
                "metricKeys": [
                    "metric",
                    "axis",
                    "score",
                    "value"
                ],
                "periodKeys": [
                    "period",
                    "basePeriod",
                    "year"
                ],
                "targetKeys": [
                    "stockCode",
                    "target",
                    "code"
                ],
                "valueKeys": [
                    "value",
                    "score"
                ]
            },
            "kind": "ai_contract",
            "preflightActions": [
                {
                    "argsTemplate": {
                        "axis": "종합평가"
                    },
                    "primaryEvidence": true,
                    "tool": "analysis"
                }
            ],
            "priority": 90,
            "questionTriggers": {
                "any": [
                    "비교",
                    "대비",
                    "vs",
                    " versus ",
                    "둘 중",
                    "어느 쪽",
                    "누가",
                    "경쟁력"
                ]
            },
            "questionTypes": [
                "company_compare"
            ],
            "requiredEvidence": [
                "target",
                "metric",
                "period",
                "value"
            ],
            "sourceKey": "aiContract.comparison.same_axis",
            "summary": "회사 비교 동일 축 evidence 계약",
            "toolArgPolicy": [
                "no_missing_side_in_comparison"
            ],
            "toolBudget": {
                "maxHeavyCallsPerTargetTool": 1,
                "skipTools": [
                    "quant"
                ]
            },
            "toolNames": [
                "searchCompany",
                "analysis",
                "credit",
                "show",
                "pastInsight",
                "scan",
                "gather",
                "macro",
                "industry",
                "pythonExec"
            ],
            "visualPolicy": {
                "preferredType": "chart_or_diagram",
                "requiredFor": [
                    "company_compare"
                ]
            }
        },
        "disclosure.importance": {
            "artifactPolicy": {
                "primaryCsv": true
            },
            "contractId": "disclosure.importance",
            "evidenceSchema": {
                "asOfKeys": [
                    "filedAt",
                    "date",
                    "rceptDt"
                ],
                "basisKeys": [
                    "basis",
                    "title",
                    "reportName"
                ],
                "metricKeys": [
                    "formType",
                    "reportName",
                    "title"
                ],
                "periodKeys": [
                    "filedAt",
                    "date",
                    "rceptDt"
                ],
                "targetKeys": [
                    "stockCode",
                    "corpCode"
                ]
            },
            "freshness": {
                "cadence": "filing_date",
                "disclosureRequired": true
            },
            "kind": "ai_contract",
            "priority": 80,
            "questionTriggers": {
                "any": [
                    "공시",
                    "filing",
                    "dart",
                    "보고서"
                ]
            },
            "questionTypes": [
                "disclosure_importance"
            ],
            "requiredEvidence": [
                "filedAt",
                "title",
                "formType",
                "basis"
            ],
            "sourceKey": "aiContract.disclosure.importance",
            "summary": "공시 중요도 분석 근거 깊이 계약",
            "tool": "disclosure",
            "toolArgPolicy": [
                "title_only_scope_must_not_be_presented_as_body_analysis",
                "sections_false",
                "max_chars_4000"
            ],
            "toolMatch": [
                {
                    "tool": "disclosure"
                },
                {
                    "tool": "filings"
                },
                {
                    "tool": "liveFilings"
                },
                {
                    "tool": "search"
                }
            ],
            "toolNames": [
                "disclosure",
                "liveFilings",
                "filings",
                "readFiling",
                "search",
                "capabilities"
            ],
            "visualPolicy": {
                "preferredType": "diagram",
                "requiredFor": [
                    "disclosure_importance"
                ]
            }
        },
        "gather.krx.close": {
            "artifactPolicy": {
                "primaryCsv": true
            },
            "comparisonCompleteness": {
                "mode": "full_universe_ranking"
            },
            "contractId": "gather.krx.close",
            "evidenceSchema": {
                "asOfKeys": [
                    "asOf",
                    "end",
                    "date"
                ],
                "basisKeys": [
                    "rank",
                    "corpName",
                    "stockCode"
                ],
                "metricKeys": [
                    "returnPct",
                    "close_return_pct"
                ],
                "periodKeys": [
                    "period",
                    "date"
                ],
                "targetKeys": [
                    "stockCode",
                    "code"
                ],
                "unit": "%",
                "valueKeys": [
                    "returnPct",
                    "value"
                ]
            },
            "freshness": {
                "cadence": "daily",
                "maxStaleBusinessDays": 10
            },
            "preflightActions": [
                {
                    "argsTemplate": {
                        "kind": "krx_price_mover"
                    },
                    "primaryEvidence": true,
                    "tool": "pythonExec"
                }
            ],
            "priority": 100,
            "questionTriggers": {
                "allAny": [
                    [
                        "주가",
                        "가격",
                        "종목",
                        "stock",
                        "price"
                    ],
                    [
                        "오른",
                        "상승",
                        "급등",
                        "수익률",
                        "모멘텀",
                        "랭킹",
                        "순위",
                        "mover",
                        "return",
                        "ranking",
                        "rank"
                    ]
                ]
            },
            "questionTypes": [
                "recent_price_mover"
            ],
            "requiredEvidence": [
                "asOf",
                "period",
                "universe",
                "metric"
            ],
            "sourceKey": "gather.krx",
            "tool": "gather",
            "toolArgPolicy": [
                "start_lte_end",
                "end_not_future",
                "target_close_for_price_returns"
            ],
            "toolMatch": [
                {
                    "args": {
                        "axis": "krx",
                        "targetIn": [
                            "",
                            "close",
                            "raw"
                        ]
                    },
                    "tool": "gather"
                }
            ],
            "toolNames": [
                "pythonExec",
                "gather",
                "capabilities"
            ],
            "visualPolicy": {
                "preferredType": "chart",
                "requiredFor": [
                    "recent_price_mover"
                ]
            }
        },
        "macro.recent": {
            "contractId": "macro.recent",
            "evidenceSchema": {
                "asOfKeys": [
                    "date",
                    "asOf"
                ],
                "metricKeys": [
                    "metric",
                    "target"
                ],
                "periodKeys": [
                    "date",
                    "period"
                ],
                "targetKeys": [
                    "target",
                    "metric"
                ],
                "valueKeys": [
                    "value",
                    "close"
                ]
            },
            "freshness": {
                "cadence": "daily_or_policy",
                "discloseMixedAsOf": true,
                "maxStaleBusinessDays": 10
            },
            "priority": 75,
            "questionTriggers": {
                "allAny": [
                    [
                        "최근",
                        "현재",
                        "오늘",
                        "어제",
                        "latest",
                        "recent",
                        "지금"
                    ],
                    [
                        "금리",
                        "환율",
                        "fx",
                        "rate",
                        "macro",
                        "원달러",
                        "usdkrw"
                    ]
                ]
            },
            "questionTypes": [
                "macro_recent"
            ],
            "requiredEvidence": [
                "asOf",
                "metric",
                "value"
            ],
            "sourceKey": "gather.macro",
            "tool": "gather",
            "toolMatch": [
                {
                    "args": {
                        "axis": "macro"
                    },
                    "tool": "gather"
                }
            ],
            "toolNames": [
                "gather",
                "macro",
                "capabilities"
            ],
            "visualPolicy": {
                "preferredType": "chart",
                "requiredFor": [
                    "macro_recent"
                ]
            }
        }
    },
    "edges": [
        {
            "from": "contract:company.analysis",
            "kind": "usesTool",
            "to": "tool:analysis"
        },
        {
            "from": "route:company_compare",
            "kind": "requiresContract",
            "to": "contract:company.analysis"
        },
        {
            "from": "route:cashflow",
            "kind": "requiresContract",
            "to": "contract:company.analysis"
        },
        {
            "from": "contract:capabilities.valid_key",
            "kind": "usesTool",
            "to": "tool:capabilities"
        },
        {
            "from": "route:meta_help",
            "kind": "requiresContract",
            "to": "contract:capabilities.valid_key"
        },
        {
            "from": "route:cashflow",
            "kind": "requiresContract",
            "to": "contract:cashflow.primary"
        },
        {
            "from": "route:company_compare",
            "kind": "requiresContract",
            "to": "contract:comparison.same_axis"
        },
        {
            "from": "contract:disclosure.importance",
            "kind": "usesTool",
            "to": "tool:disclosure"
        },
        {
            "from": "route:disclosure_importance",
            "kind": "requiresContract",
            "to": "contract:disclosure.importance"
        },
        {
            "from": "contract:gather.krx.close",
            "kind": "usesTool",
            "to": "tool:gather"
        },
        {
            "from": "route:recent_price_mover",
            "kind": "requiresContract",
            "to": "contract:gather.krx.close"
        },
        {
            "from": "contract:macro.recent",
            "kind": "usesTool",
            "to": "tool:gather"
        },
        {
            "from": "route:macro_recent",
            "kind": "requiresContract",
            "to": "contract:macro.recent"
        }
    ],
    "graphVersion": 1,
    "nodes": [
        {
            "id": "contract:company.analysis",
            "kind": "contract",
            "label": "company.analysis",
            "source": "Company.analysis"
        },
        {
            "id": "tool:analysis",
            "kind": "tool",
            "label": "analysis",
            "source": "Company.analysis"
        },
        {
            "id": "contract:capabilities.valid_key",
            "kind": "contract",
            "label": "capabilities key 오염 방지 계약",
            "source": "aiContract.capabilities.valid_key"
        },
        {
            "id": "tool:capabilities",
            "kind": "tool",
            "label": "capabilities",
            "source": "aiContract.capabilities.valid_key"
        },
        {
            "id": "contract:cashflow.primary",
            "kind": "contract",
            "label": "현금흐름 질문 primary evidence 계약",
            "source": "aiContract.cashflow.primary"
        },
        {
            "id": "contract:comparison.same_axis",
            "kind": "contract",
            "label": "회사 비교 동일 축 evidence 계약",
            "source": "aiContract.comparison.same_axis"
        },
        {
            "id": "contract:disclosure.importance",
            "kind": "contract",
            "label": "공시 중요도 분석 근거 깊이 계약",
            "source": "aiContract.disclosure.importance"
        },
        {
            "id": "tool:disclosure",
            "kind": "tool",
            "label": "disclosure",
            "source": "aiContract.disclosure.importance"
        },
        {
            "id": "contract:gather.krx.close",
            "kind": "contract",
            "label": "gather.krx.close",
            "source": "gather.krx"
        },
        {
            "id": "tool:gather",
            "kind": "tool",
            "label": "gather",
            "source": "gather.krx"
        },
        {
            "id": "contract:macro.recent",
            "kind": "contract",
            "label": "macro.recent",
            "source": "gather.macro"
        },
        {
            "id": "tool:gather",
            "kind": "tool",
            "label": "gather",
            "source": "gather.macro"
        }
    ],
    "routes": [
        {
            "contractIds": [
                "company.analysis",
                "comparison.same_axis"
            ],
            "id": "route:company_compare",
            "questionType": "company_compare",
            "toolNames": [
                "analysis",
                "show",
                "credit",
                "pastInsight",
                "capabilities",
                "searchCompany",
                "scan",
                "gather",
                "macro",
                "industry",
                "pythonExec"
            ],
            "triggers": {}
        },
        {
            "contractIds": [
                "company.analysis",
                "cashflow.primary"
            ],
            "id": "route:cashflow",
            "questionType": "cashflow",
            "toolNames": [
                "analysis",
                "show",
                "credit",
                "pastInsight",
                "capabilities"
            ],
            "triggers": {}
        },
        {
            "contractIds": [
                "capabilities.valid_key"
            ],
            "id": "route:meta_help",
            "questionType": "meta_help",
            "toolNames": [
                "capabilities",
                "Read"
            ],
            "triggers": {
                "any": [
                    "뭐 할 수",
                    "어떻게 써",
                    "사용법",
                    "help",
                    "capabilities"
                ]
            }
        },
        {
            "contractIds": [
                "disclosure.importance"
            ],
            "id": "route:disclosure_importance",
            "questionType": "disclosure_importance",
            "toolNames": [
                "disclosure",
                "liveFilings",
                "filings",
                "readFiling",
                "search",
                "capabilities"
            ],
            "triggers": {
                "any": [
                    "공시",
                    "filing",
                    "dart",
                    "보고서"
                ]
            }
        },
        {
            "contractIds": [
                "gather.krx.close"
            ],
            "id": "route:recent_price_mover",
            "questionType": "recent_price_mover",
            "toolNames": [
                "pythonExec",
                "gather",
                "capabilities"
            ],
            "triggers": {
                "allAny": [
                    [
                        "주가",
                        "가격",
                        "종목",
                        "stock",
                        "price"
                    ],
                    [
                        "오른",
                        "상승",
                        "급등",
                        "수익률",
                        "모멘텀",
                        "랭킹",
                        "순위",
                        "mover",
                        "return",
                        "ranking",
                        "rank"
                    ]
                ]
            }
        },
        {
            "contractIds": [
                "macro.recent"
            ],
            "id": "route:macro_recent",
            "questionType": "macro_recent",
            "toolNames": [
                "gather",
                "macro",
                "capabilities"
            ],
            "triggers": {
                "allAny": [
                    [
                        "최근",
                        "현재",
                        "오늘",
                        "어제",
                        "latest",
                        "recent",
                        "지금"
                    ],
                    [
                        "금리",
                        "환율",
                        "fx",
                        "rate",
                        "macro",
                        "원달러",
                        "usdkrw"
                    ]
                ]
            }
        }
    ],
    "sourceHash": "b9407e50c34ed0e3"
}
"""
)
