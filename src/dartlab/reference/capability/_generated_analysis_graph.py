"""Analysis Graph generated from CAPABILITIES.

수정하지 마세요. src/dartlab/reference/capability/generateSpec.py 를 실행하세요.
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
            "aicontext": "ask()/chat()에서 분석 결과를 컨텍스트로 주입\nstory가 내부적으로 analysis 결과를 소비",
            "artifactPolicy": {
                "primaryCsv": true
            },
            "capabilities": "22축 분석 (5 group)\nfinancial (14): 수익구조, 자금조달, 자산구조, 현금흐름, 수익성, 성장성, 안정성, 효율성, 종합평가, 이익품질, 비용구조, 자본배분, 투자효율, 재무정합성\nvaluation (1): 가치평가\ngovernance (3): 지배구조, 공시변화, 비교분석\nforecast (2): 매출전망, 예측신호\nmacro (2): 매크로민감도, 밸류에이션밴드\n축 없이 호출 시 22축 가이드 반환\n개별 축 분석 시 Company 바인딩 (self 자동 전달)\n2-level 호출: c.analysis(\"financial\", \"수익성\"), c.analysis(\"valuation\", \"가치평가\")",
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
            "kind": "property",
            "llmSpecs": {
                "antiPatterns": [
                    "axis 만 주고 sub 없이 호출 (그룹 가이드만 반환, 실제 분석 X)",
                    "그룹명 (\"financial\") 을 axis 로, 축명 (\"수익성\") 을 sub 로 — 순서 헷갈림",
                    "sub 에 영문 (\"profitability\") 사용 (실제는 한글)"
                ],
                "freshness": "finance 데이터 기준 — 분기 마감 후 45일.",
                "outputSchema": [
                    "history : list[dict] — 시계열 (period + 지표들)",
                    "displayHints : dict — core 컬럼 목록",
                    "turningPoints : list — 전환점",
                    "dataAsOf : dict — latestPeriod, retrievedAt",
                    "assumptions : dict — 엔진 가정 (overrides 재호출용)"
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
            "requires": "데이터: finance (자동 다운로드)",
            "returnSchema": [
                {
                    "depth": 0,
                    "description": "축별 계산 결과",
                    "name": "{calcName}",
                    "type": "dict",
                    "unit": null
                },
                {
                    "depth": 0,
                    "description": "시계열 ({period, ...지표})",
                    "name": "history",
                    "type": "list[dict]",
                    "unit": null
                },
                {
                    "depth": 0,
                    "description": "core 컬럼 목록",
                    "name": "displayHints",
                    "type": "dict",
                    "unit": null
                },
                {
                    "depth": 0,
                    "description": "전환점 (있으면)",
                    "name": "turningPoints",
                    "type": "list",
                    "unit": null
                },
                {
                    "depth": 0,
                    "description": "경고 플래그",
                    "name": "{calcName}Flags",
                    "type": "list[str]",
                    "unit": null
                },
                {
                    "depth": 0,
                    "description": "latestPeriod, retrievedAt",
                    "name": "dataAsOf",
                    "type": "dict",
                    "unit": null
                }
            ],
            "sourceKey": "Company.analysis",
            "summary": "재무제표 완전 분석 — 22축, 단일 종목 심층 (내부 구현).",
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
                },
                {
                    "argsTemplate": {
                        "fields": [
                            "매출액",
                            "영업이익"
                        ],
                        "freq": "Y",
                        "raw": false,
                        "scope": "consolidated",
                        "topic": "IS"
                    },
                    "primaryEvidence": true,
                    "tool": "show"
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
                    "quant",
                    "credit"
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
            "capabilities": "KOSPI/KOSDAQ 전종목 wide pivot — 행=stockCode+corpName, 열=일자. target (positional) 으로 raw OHLCV (close/open/high/low/volume/marketCap/...) 또는 보조지표 (rsi14/ma20/ema60/macd/atr14/obv/...) 28+ 디스패치. target='raw' 면 long (KRX 원본 컬럼). apiKey 없음 (기본): HF SSOT. apiKey 명시: KRX OpenAPI 직접. 환경변수 자동 read X.",
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
            "kind": "gather_axis",
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
                        "rank",
                        "rose",
                        "risen",
                        "gainer",
                        "gainers",
                        "recently"
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
            "summary": "KRX 회사별 시계열",
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
            "capabilities": "ECOS(KR) / FRED(US) 거시지표 시계열. 기본 HF 벌크 (apiKey 없음), apiKey 명시 시 ECOS/FRED 직접 API.",
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
            "kind": "gather_axis",
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
            "summary": "거시지표",
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
        },
        "scan.industry_screen": {
            "acceptanceCriteria": {
                "industryUniverse": true,
                "primaryCsv": true,
                "visual": true
            },
            "artifactPolicy": {
                "primaryCsv": true
            },
            "comparisonCompleteness": {
                "mode": "industry_universe_screening"
            },
            "contractId": "scan.industry_screen",
            "evidenceSchema": {
                "basisKeys": [
                    "종목명",
                    "corpName",
                    "공정명",
                    "역할",
                    "위치",
                    "등급"
                ],
                "metricKeys": [
                    "ROE",
                    "ROA",
                    "영업이익률",
                    "순이익률",
                    "공정",
                    "공정명",
                    "등급",
                    "metric"
                ],
                "targetKeys": [
                    "종목코드",
                    "stockCode",
                    "code"
                ],
                "valueKeys": [
                    "ROE",
                    "ROA",
                    "영업이익률",
                    "순이익률",
                    "신뢰도",
                    "value"
                ]
            },
            "kind": "ai_contract",
            "preflightActions": [
                {
                    "argsTemplate": {
                        "industryId": "{industryId}"
                    },
                    "primaryEvidence": true,
                    "tool": "industry"
                },
                {
                    "argsTemplate": {
                        "axis": "profitability",
                        "descending": true,
                        "limit": 50,
                        "sortBy": "ROE"
                    },
                    "primaryEvidence": true,
                    "tool": "scan"
                },
                {
                    "argsTemplate": {
                        "industryId": "{industryId}",
                        "kind": "industry_scan"
                    },
                    "primaryEvidence": true,
                    "tool": "pythonExec"
                }
            ],
            "priority": 97,
            "questionTriggers": {
                "allAny": [
                    [
                        "scan",
                        "screen",
                        "screening",
                        "compare",
                        "comparison",
                        "비교",
                        "스크리닝",
                        "찾아",
                        "좋은",
                        "수익성"
                    ],
                    [
                        "industry",
                        "sector",
                        "업종",
                        "산업",
                        "반도체",
                        "semiconductor"
                    ]
                ]
            },
            "questionTypes": [
                "industry_scan"
            ],
            "requiredEvidence": [
                "industry",
                "universe",
                "target",
                "metric",
                "value"
            ],
            "sourceKey": "scan.industry",
            "summary": "산업 taxonomy universe를 먼저 고정한 뒤 scan으로 같은 축 수익성 evidence를 만든다",
            "tool": "scan",
            "toolArgPolicy": [
                "industry_universe_required",
                "scan_required_for_market_screening"
            ],
            "toolMatch": [
                {
                    "tool": "industry"
                },
                {
                    "tool": "scan"
                },
                {
                    "args": {
                        "kind": "industry_scan"
                    },
                    "tool": "pythonExec"
                }
            ],
            "toolNames": [
                "industry",
                "scan",
                "pythonExec",
                "capabilities"
            ],
            "visualPolicy": {
                "preferredType": "chart",
                "requiredFor": [
                    "industry_scan"
                ]
            }
        },
        "scan.market_screen": {
            "artifactPolicy": {
                "primaryCsv": true
            },
            "comparisonCompleteness": {
                "mode": "full_universe_screening"
            },
            "contractId": "scan.market_screen",
            "evidenceSchema": {
                "basisKeys": [
                    "종목명",
                    "corpName",
                    "등급"
                ],
                "metricKeys": [
                    "ROE",
                    "ROA",
                    "영업이익률",
                    "순이익률",
                    "등급",
                    "metric"
                ],
                "targetKeys": [
                    "종목코드",
                    "stockCode",
                    "code"
                ],
                "valueKeys": [
                    "ROE",
                    "ROA",
                    "영업이익률",
                    "순이익률",
                    "value"
                ]
            },
            "kind": "ai_contract",
            "preflightActions": [
                {
                    "argsTemplate": {
                        "axis": "profitability",
                        "descending": true,
                        "limit": 20,
                        "sortBy": "ROE"
                    },
                    "primaryEvidence": true,
                    "tool": "scan"
                }
            ],
            "priority": 92,
            "questionTriggers": {
                "any": [
                    "scan",
                    "screen",
                    "screening",
                    "profitable stocks",
                    "profitability",
                    "industry",
                    "sector",
                    "업종",
                    "산업",
                    "스크리닝",
                    "종목 발굴",
                    "좋은 종목",
                    "수익성 좋은"
                ]
            },
            "questionTypes": [
                "market_scan"
            ],
            "requiredEvidence": [
                "target",
                "metric",
                "value"
            ],
            "sourceKey": "scan.market",
            "summary": "시장/업종/스크리닝 질문 scan primary evidence 계약",
            "tool": "scan",
            "toolArgPolicy": [
                "scan_required_for_market_screening",
                "no_company_pair_preflight_for_industry_scan"
            ],
            "toolMatch": [
                {
                    "tool": "scan"
                }
            ],
            "toolNames": [
                "scan",
                "pythonExec",
                "capabilities"
            ],
            "visualPolicy": {
                "preferredType": "chart",
                "requiredFor": [
                    "market_scan"
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
        },
        {
            "from": "contract:scan.industry_screen",
            "kind": "usesTool",
            "to": "tool:scan"
        },
        {
            "from": "route:industry_scan",
            "kind": "requiresContract",
            "to": "contract:scan.industry_screen"
        },
        {
            "from": "contract:scan.market_screen",
            "kind": "usesTool",
            "to": "tool:scan"
        },
        {
            "from": "route:market_scan",
            "kind": "requiresContract",
            "to": "contract:scan.market_screen"
        },
        {
            "from": "route:company_compare",
            "kind": "usesProcess",
            "to": "process:company_compare.default"
        },
        {
            "from": "process:company_compare.default",
            "kind": "requiresContract",
            "to": "contract:company.analysis"
        },
        {
            "from": "process:company_compare.default",
            "kind": "requiresContract",
            "to": "contract:comparison.same_axis"
        },
        {
            "from": "process:company_compare.default",
            "kind": "usesTool",
            "to": "tool:analysis"
        },
        {
            "from": "process:company_compare.default",
            "kind": "producesEvidence",
            "to": "evidence:company_compare.default:company.analysis.analysis"
        },
        {
            "from": "process:company_compare.default",
            "kind": "usesTool",
            "to": "tool:show"
        },
        {
            "from": "process:company_compare.default",
            "kind": "producesEvidence",
            "to": "evidence:company_compare.default:company.analysis.show"
        },
        {
            "from": "process:company_compare.default",
            "kind": "usesTool",
            "to": "tool:credit"
        },
        {
            "from": "process:company_compare.default",
            "kind": "producesEvidence",
            "to": "evidence:company_compare.default:company.analysis.credit"
        },
        {
            "from": "process:company_compare.default",
            "kind": "usesTool",
            "to": "tool:pastInsight"
        },
        {
            "from": "process:company_compare.default",
            "kind": "producesEvidence",
            "to": "evidence:company_compare.default:company.analysis.pastInsight"
        },
        {
            "from": "process:company_compare.default",
            "kind": "usesTool",
            "to": "tool:capabilities"
        },
        {
            "from": "process:company_compare.default",
            "kind": "producesEvidence",
            "to": "evidence:company_compare.default:company.analysis.capabilities"
        },
        {
            "from": "process:company_compare.default",
            "kind": "usesTool",
            "to": "tool:analysis"
        },
        {
            "from": "process:company_compare.default",
            "kind": "producesEvidence",
            "to": "evidence:company_compare.default:comparison.same_axis.preflight.1"
        },
        {
            "from": "process:company_compare.default",
            "kind": "usesTool",
            "to": "tool:show"
        },
        {
            "from": "process:company_compare.default",
            "kind": "producesEvidence",
            "to": "evidence:company_compare.default:comparison.same_axis.preflight.2"
        },
        {
            "from": "process:company_compare.default",
            "kind": "producesArtifact",
            "to": "artifact:company_compare.default:primary_csv"
        },
        {
            "from": "process:company_compare.default",
            "kind": "requiresVisual",
            "to": "visual:company_compare.default:primary"
        },
        {
            "from": "process:company_compare.default",
            "kind": "feedsWorkspace",
            "to": "workspace:analysis"
        },
        {
            "from": "route:cashflow",
            "kind": "usesProcess",
            "to": "process:cashflow.default"
        },
        {
            "from": "process:cashflow.default",
            "kind": "requiresContract",
            "to": "contract:company.analysis"
        },
        {
            "from": "process:cashflow.default",
            "kind": "requiresContract",
            "to": "contract:cashflow.primary"
        },
        {
            "from": "process:cashflow.default",
            "kind": "usesTool",
            "to": "tool:analysis"
        },
        {
            "from": "process:cashflow.default",
            "kind": "producesEvidence",
            "to": "evidence:cashflow.default:company.analysis.analysis"
        },
        {
            "from": "process:cashflow.default",
            "kind": "usesTool",
            "to": "tool:show"
        },
        {
            "from": "process:cashflow.default",
            "kind": "producesEvidence",
            "to": "evidence:cashflow.default:company.analysis.show"
        },
        {
            "from": "process:cashflow.default",
            "kind": "usesTool",
            "to": "tool:credit"
        },
        {
            "from": "process:cashflow.default",
            "kind": "producesEvidence",
            "to": "evidence:cashflow.default:company.analysis.credit"
        },
        {
            "from": "process:cashflow.default",
            "kind": "usesTool",
            "to": "tool:pastInsight"
        },
        {
            "from": "process:cashflow.default",
            "kind": "producesEvidence",
            "to": "evidence:cashflow.default:company.analysis.pastInsight"
        },
        {
            "from": "process:cashflow.default",
            "kind": "usesTool",
            "to": "tool:capabilities"
        },
        {
            "from": "process:cashflow.default",
            "kind": "producesEvidence",
            "to": "evidence:cashflow.default:company.analysis.capabilities"
        },
        {
            "from": "process:cashflow.default",
            "kind": "usesTool",
            "to": "tool:analysis"
        },
        {
            "from": "process:cashflow.default",
            "kind": "producesEvidence",
            "to": "evidence:cashflow.default:cashflow.primary.preflight.1"
        },
        {
            "from": "process:cashflow.default",
            "kind": "usesTool",
            "to": "tool:show"
        },
        {
            "from": "process:cashflow.default",
            "kind": "producesEvidence",
            "to": "evidence:cashflow.default:cashflow.primary.preflight.2"
        },
        {
            "from": "process:cashflow.default",
            "kind": "producesArtifact",
            "to": "artifact:cashflow.default:primary_csv"
        },
        {
            "from": "process:cashflow.default",
            "kind": "requiresVisual",
            "to": "visual:cashflow.default:primary"
        },
        {
            "from": "process:cashflow.default",
            "kind": "feedsWorkspace",
            "to": "workspace:analysis"
        },
        {
            "from": "route:meta_help",
            "kind": "usesProcess",
            "to": "process:meta_help.default"
        },
        {
            "from": "process:meta_help.default",
            "kind": "requiresContract",
            "to": "contract:capabilities.valid_key"
        },
        {
            "from": "process:meta_help.default",
            "kind": "usesTool",
            "to": "tool:capabilities"
        },
        {
            "from": "process:meta_help.default",
            "kind": "producesEvidence",
            "to": "evidence:meta_help.default:capabilities.valid_key.capabilities"
        },
        {
            "from": "process:meta_help.default",
            "kind": "usesTool",
            "to": "tool:Read"
        },
        {
            "from": "process:meta_help.default",
            "kind": "producesEvidence",
            "to": "evidence:meta_help.default:capabilities.valid_key.Read"
        },
        {
            "from": "process:meta_help.default",
            "kind": "feedsWorkspace",
            "to": "workspace:analysis"
        },
        {
            "from": "route:disclosure_importance",
            "kind": "usesProcess",
            "to": "process:disclosure_importance.default"
        },
        {
            "from": "process:disclosure_importance.default",
            "kind": "requiresContract",
            "to": "contract:disclosure.importance"
        },
        {
            "from": "process:disclosure_importance.default",
            "kind": "usesTool",
            "to": "tool:disclosure"
        },
        {
            "from": "process:disclosure_importance.default",
            "kind": "producesEvidence",
            "to": "evidence:disclosure_importance.default:disclosure.importance.disclosure"
        },
        {
            "from": "process:disclosure_importance.default",
            "kind": "usesTool",
            "to": "tool:liveFilings"
        },
        {
            "from": "process:disclosure_importance.default",
            "kind": "producesEvidence",
            "to": "evidence:disclosure_importance.default:disclosure.importance.liveFilings"
        },
        {
            "from": "process:disclosure_importance.default",
            "kind": "usesTool",
            "to": "tool:filings"
        },
        {
            "from": "process:disclosure_importance.default",
            "kind": "producesEvidence",
            "to": "evidence:disclosure_importance.default:disclosure.importance.filings"
        },
        {
            "from": "process:disclosure_importance.default",
            "kind": "usesTool",
            "to": "tool:readFiling"
        },
        {
            "from": "process:disclosure_importance.default",
            "kind": "producesEvidence",
            "to": "evidence:disclosure_importance.default:disclosure.importance.readFiling"
        },
        {
            "from": "process:disclosure_importance.default",
            "kind": "usesTool",
            "to": "tool:search"
        },
        {
            "from": "process:disclosure_importance.default",
            "kind": "producesEvidence",
            "to": "evidence:disclosure_importance.default:disclosure.importance.search"
        },
        {
            "from": "process:disclosure_importance.default",
            "kind": "usesTool",
            "to": "tool:capabilities"
        },
        {
            "from": "process:disclosure_importance.default",
            "kind": "producesEvidence",
            "to": "evidence:disclosure_importance.default:disclosure.importance.capabilities"
        },
        {
            "from": "process:disclosure_importance.default",
            "kind": "producesArtifact",
            "to": "artifact:disclosure_importance.default:primary_csv"
        },
        {
            "from": "process:disclosure_importance.default",
            "kind": "requiresVisual",
            "to": "visual:disclosure_importance.default:primary"
        },
        {
            "from": "process:disclosure_importance.default",
            "kind": "feedsWorkspace",
            "to": "workspace:analysis"
        },
        {
            "from": "route:recent_price_mover",
            "kind": "usesProcess",
            "to": "process:recent_price_mover.default"
        },
        {
            "from": "process:recent_price_mover.default",
            "kind": "requiresContract",
            "to": "contract:gather.krx.close"
        },
        {
            "from": "process:recent_price_mover.default",
            "kind": "usesTool",
            "to": "tool:pythonExec"
        },
        {
            "from": "process:recent_price_mover.default",
            "kind": "producesEvidence",
            "to": "evidence:recent_price_mover.default:gather.krx.close.preflight.1"
        },
        {
            "from": "process:recent_price_mover.default",
            "kind": "producesArtifact",
            "to": "artifact:recent_price_mover.default:primary_csv"
        },
        {
            "from": "process:recent_price_mover.default",
            "kind": "requiresVisual",
            "to": "visual:recent_price_mover.default:primary"
        },
        {
            "from": "process:recent_price_mover.default",
            "kind": "feedsWorkspace",
            "to": "workspace:analysis"
        },
        {
            "from": "route:macro_recent",
            "kind": "usesProcess",
            "to": "process:macro_recent.default"
        },
        {
            "from": "process:macro_recent.default",
            "kind": "requiresContract",
            "to": "contract:macro.recent"
        },
        {
            "from": "process:macro_recent.default",
            "kind": "usesTool",
            "to": "tool:gather"
        },
        {
            "from": "process:macro_recent.default",
            "kind": "producesEvidence",
            "to": "evidence:macro_recent.default:macro.recent.gather"
        },
        {
            "from": "process:macro_recent.default",
            "kind": "usesTool",
            "to": "tool:macro"
        },
        {
            "from": "process:macro_recent.default",
            "kind": "producesEvidence",
            "to": "evidence:macro_recent.default:macro.recent.macro"
        },
        {
            "from": "process:macro_recent.default",
            "kind": "usesTool",
            "to": "tool:capabilities"
        },
        {
            "from": "process:macro_recent.default",
            "kind": "producesEvidence",
            "to": "evidence:macro_recent.default:macro.recent.capabilities"
        },
        {
            "from": "process:macro_recent.default",
            "kind": "requiresVisual",
            "to": "visual:macro_recent.default:primary"
        },
        {
            "from": "process:macro_recent.default",
            "kind": "feedsWorkspace",
            "to": "workspace:analysis"
        },
        {
            "from": "route:industry_scan",
            "kind": "usesProcess",
            "to": "process:industry_scan.default"
        },
        {
            "from": "process:industry_scan.default",
            "kind": "requiresContract",
            "to": "contract:scan.industry_screen"
        },
        {
            "from": "process:industry_scan.default",
            "kind": "usesTool",
            "to": "tool:industry"
        },
        {
            "from": "process:industry_scan.default",
            "kind": "producesEvidence",
            "to": "evidence:industry_scan.default:scan.industry_screen.preflight.1"
        },
        {
            "from": "process:industry_scan.default",
            "kind": "usesTool",
            "to": "tool:scan"
        },
        {
            "from": "process:industry_scan.default",
            "kind": "producesEvidence",
            "to": "evidence:industry_scan.default:scan.industry_screen.preflight.2"
        },
        {
            "from": "process:industry_scan.default",
            "kind": "usesTool",
            "to": "tool:pythonExec"
        },
        {
            "from": "process:industry_scan.default",
            "kind": "producesEvidence",
            "to": "evidence:industry_scan.default:scan.industry_screen.preflight.3"
        },
        {
            "from": "process:industry_scan.default",
            "kind": "producesArtifact",
            "to": "artifact:industry_scan.default:primary_csv"
        },
        {
            "from": "process:industry_scan.default",
            "kind": "requiresVisual",
            "to": "visual:industry_scan.default:primary"
        },
        {
            "from": "process:industry_scan.default",
            "kind": "feedsWorkspace",
            "to": "workspace:analysis"
        },
        {
            "from": "route:market_scan",
            "kind": "usesProcess",
            "to": "process:market_scan.default"
        },
        {
            "from": "process:market_scan.default",
            "kind": "requiresContract",
            "to": "contract:scan.market_screen"
        },
        {
            "from": "process:market_scan.default",
            "kind": "usesTool",
            "to": "tool:scan"
        },
        {
            "from": "process:market_scan.default",
            "kind": "producesEvidence",
            "to": "evidence:market_scan.default:scan.market_screen.preflight.1"
        },
        {
            "from": "process:market_scan.default",
            "kind": "producesArtifact",
            "to": "artifact:market_scan.default:primary_csv"
        },
        {
            "from": "process:market_scan.default",
            "kind": "requiresVisual",
            "to": "visual:market_scan.default:primary"
        },
        {
            "from": "process:market_scan.default",
            "kind": "feedsWorkspace",
            "to": "workspace:analysis"
        }
    ],
    "graphVersion": 2,
    "nodes": [
        {
            "id": "contract:company.analysis",
            "kind": "contract",
            "label": "재무제표 완전 분석 — 22축, 단일 종목 심층 (내부 구현).",
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
            "label": "KRX 회사별 시계열",
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
            "label": "거시지표",
            "source": "gather.macro"
        },
        {
            "id": "tool:gather",
            "kind": "tool",
            "label": "gather",
            "source": "gather.macro"
        },
        {
            "id": "contract:scan.industry_screen",
            "kind": "contract",
            "label": "산업 taxonomy universe를 먼저 고정한 뒤 scan으로 같은 축 수익성 evidence를 만든다",
            "source": "scan.industry"
        },
        {
            "id": "tool:scan",
            "kind": "tool",
            "label": "scan",
            "source": "scan.industry"
        },
        {
            "id": "contract:scan.market_screen",
            "kind": "contract",
            "label": "시장/업종/스크리닝 질문 scan primary evidence 계약",
            "source": "scan.market"
        },
        {
            "id": "tool:scan",
            "kind": "tool",
            "label": "scan",
            "source": "scan.market"
        },
        {
            "id": "process:company_compare.default",
            "kind": "process",
            "label": "company_compare analysis process",
            "source": "company_compare"
        },
        {
            "id": "evidence:company_compare.default:company.analysis.analysis",
            "kind": "evidence",
            "label": "company.analysis evidence candidate"
        },
        {
            "id": "evidence:company_compare.default:company.analysis.show",
            "kind": "evidence",
            "label": "company.analysis evidence candidate"
        },
        {
            "id": "evidence:company_compare.default:company.analysis.credit",
            "kind": "evidence",
            "label": "company.analysis evidence candidate"
        },
        {
            "id": "evidence:company_compare.default:company.analysis.pastInsight",
            "kind": "evidence",
            "label": "company.analysis evidence candidate"
        },
        {
            "id": "evidence:company_compare.default:company.analysis.capabilities",
            "kind": "evidence",
            "label": "company.analysis evidence candidate"
        },
        {
            "id": "evidence:company_compare.default:comparison.same_axis.preflight.1",
            "kind": "evidence",
            "label": "comparison.same_axis primary evidence"
        },
        {
            "id": "evidence:company_compare.default:comparison.same_axis.preflight.2",
            "kind": "evidence",
            "label": "comparison.same_axis primary evidence"
        },
        {
            "id": "artifact:company_compare.default:primary_csv",
            "kind": "artifact",
            "label": "primary CSV"
        },
        {
            "id": "visual:company_compare.default:primary",
            "kind": "visual",
            "label": "chart_or_diagram"
        },
        {
            "id": "process:cashflow.default",
            "kind": "process",
            "label": "cashflow analysis process",
            "source": "cashflow"
        },
        {
            "id": "evidence:cashflow.default:company.analysis.analysis",
            "kind": "evidence",
            "label": "company.analysis evidence candidate"
        },
        {
            "id": "evidence:cashflow.default:company.analysis.show",
            "kind": "evidence",
            "label": "company.analysis evidence candidate"
        },
        {
            "id": "evidence:cashflow.default:company.analysis.credit",
            "kind": "evidence",
            "label": "company.analysis evidence candidate"
        },
        {
            "id": "evidence:cashflow.default:company.analysis.pastInsight",
            "kind": "evidence",
            "label": "company.analysis evidence candidate"
        },
        {
            "id": "evidence:cashflow.default:company.analysis.capabilities",
            "kind": "evidence",
            "label": "company.analysis evidence candidate"
        },
        {
            "id": "evidence:cashflow.default:cashflow.primary.preflight.1",
            "kind": "evidence",
            "label": "cashflow.primary primary evidence"
        },
        {
            "id": "evidence:cashflow.default:cashflow.primary.preflight.2",
            "kind": "evidence",
            "label": "cashflow.primary primary evidence"
        },
        {
            "id": "artifact:cashflow.default:primary_csv",
            "kind": "artifact",
            "label": "primary CSV"
        },
        {
            "id": "visual:cashflow.default:primary",
            "kind": "visual",
            "label": "chart"
        },
        {
            "id": "process:meta_help.default",
            "kind": "process",
            "label": "meta_help analysis process",
            "source": "meta_help"
        },
        {
            "id": "evidence:meta_help.default:capabilities.valid_key.capabilities",
            "kind": "evidence",
            "label": "capabilities.valid_key evidence candidate"
        },
        {
            "id": "evidence:meta_help.default:capabilities.valid_key.Read",
            "kind": "evidence",
            "label": "capabilities.valid_key evidence candidate"
        },
        {
            "id": "process:disclosure_importance.default",
            "kind": "process",
            "label": "disclosure_importance analysis process",
            "source": "disclosure_importance"
        },
        {
            "id": "evidence:disclosure_importance.default:disclosure.importance.disclosure",
            "kind": "evidence",
            "label": "disclosure.importance evidence candidate"
        },
        {
            "id": "evidence:disclosure_importance.default:disclosure.importance.liveFilings",
            "kind": "evidence",
            "label": "disclosure.importance evidence candidate"
        },
        {
            "id": "evidence:disclosure_importance.default:disclosure.importance.filings",
            "kind": "evidence",
            "label": "disclosure.importance evidence candidate"
        },
        {
            "id": "evidence:disclosure_importance.default:disclosure.importance.readFiling",
            "kind": "evidence",
            "label": "disclosure.importance evidence candidate"
        },
        {
            "id": "evidence:disclosure_importance.default:disclosure.importance.search",
            "kind": "evidence",
            "label": "disclosure.importance evidence candidate"
        },
        {
            "id": "evidence:disclosure_importance.default:disclosure.importance.capabilities",
            "kind": "evidence",
            "label": "disclosure.importance evidence candidate"
        },
        {
            "id": "artifact:disclosure_importance.default:primary_csv",
            "kind": "artifact",
            "label": "primary CSV"
        },
        {
            "id": "visual:disclosure_importance.default:primary",
            "kind": "visual",
            "label": "diagram"
        },
        {
            "id": "process:recent_price_mover.default",
            "kind": "process",
            "label": "recent_price_mover analysis process",
            "source": "recent_price_mover"
        },
        {
            "id": "evidence:recent_price_mover.default:gather.krx.close.preflight.1",
            "kind": "evidence",
            "label": "gather.krx.close primary evidence"
        },
        {
            "id": "artifact:recent_price_mover.default:primary_csv",
            "kind": "artifact",
            "label": "primary CSV"
        },
        {
            "id": "visual:recent_price_mover.default:primary",
            "kind": "visual",
            "label": "chart"
        },
        {
            "id": "process:macro_recent.default",
            "kind": "process",
            "label": "macro_recent analysis process",
            "source": "macro_recent"
        },
        {
            "id": "evidence:macro_recent.default:macro.recent.gather",
            "kind": "evidence",
            "label": "macro.recent evidence candidate"
        },
        {
            "id": "evidence:macro_recent.default:macro.recent.macro",
            "kind": "evidence",
            "label": "macro.recent evidence candidate"
        },
        {
            "id": "evidence:macro_recent.default:macro.recent.capabilities",
            "kind": "evidence",
            "label": "macro.recent evidence candidate"
        },
        {
            "id": "visual:macro_recent.default:primary",
            "kind": "visual",
            "label": "chart"
        },
        {
            "id": "process:industry_scan.default",
            "kind": "process",
            "label": "industry_scan analysis process",
            "source": "industry_scan"
        },
        {
            "id": "evidence:industry_scan.default:scan.industry_screen.preflight.1",
            "kind": "evidence",
            "label": "scan.industry_screen primary evidence"
        },
        {
            "id": "evidence:industry_scan.default:scan.industry_screen.preflight.2",
            "kind": "evidence",
            "label": "scan.industry_screen primary evidence"
        },
        {
            "id": "evidence:industry_scan.default:scan.industry_screen.preflight.3",
            "kind": "evidence",
            "label": "scan.industry_screen primary evidence"
        },
        {
            "id": "artifact:industry_scan.default:primary_csv",
            "kind": "artifact",
            "label": "primary CSV"
        },
        {
            "id": "visual:industry_scan.default:primary",
            "kind": "visual",
            "label": "chart"
        },
        {
            "id": "process:market_scan.default",
            "kind": "process",
            "label": "market_scan analysis process",
            "source": "market_scan"
        },
        {
            "id": "evidence:market_scan.default:scan.market_screen.preflight.1",
            "kind": "evidence",
            "label": "scan.market_screen primary evidence"
        },
        {
            "id": "artifact:market_scan.default:primary_csv",
            "kind": "artifact",
            "label": "primary CSV"
        },
        {
            "id": "visual:market_scan.default:primary",
            "kind": "visual",
            "label": "chart"
        }
    ],
    "processMaps": {
        "cashflow.default": {
            "acceptanceCriteria": {
                "claimSupportRateMin": 0.9,
                "primaryCsv": true,
                "requiredEvidence": [
                    "target",
                    "metric",
                    "period",
                    "value"
                ],
                "visual": true
            },
            "artifactPolicy": {
                "primaryCsv": true
            },
            "contractIds": [
                "company.analysis",
                "cashflow.primary"
            ],
            "failurePolicy": {
                "onMissingEvidence": "repair_once",
                "onUnsupportedClaim": "disclose_or_repair"
            },
            "freshness": {},
            "id": "cashflow.default",
            "questionType": "cashflow",
            "requiredArtifacts": [
                "primary_csv"
            ],
            "requiredEvidence": [
                "target",
                "metric",
                "period",
                "value"
            ],
            "requiredTools": [
                "analysis",
                "show"
            ],
            "requiredVisuals": [
                "chart"
            ],
            "routeId": "route:cashflow",
            "steps": [
                {
                    "contractId": "company.analysis",
                    "id": "company.analysis.analysis",
                    "primaryEvidence": false,
                    "produces": "evidence",
                    "purpose": "company.analysis evidence candidate",
                    "tool": "analysis"
                },
                {
                    "contractId": "company.analysis",
                    "id": "company.analysis.show",
                    "primaryEvidence": false,
                    "produces": "evidence",
                    "purpose": "company.analysis evidence candidate",
                    "tool": "show"
                },
                {
                    "contractId": "company.analysis",
                    "id": "company.analysis.credit",
                    "primaryEvidence": false,
                    "produces": "evidence",
                    "purpose": "company.analysis evidence candidate",
                    "tool": "credit"
                },
                {
                    "contractId": "company.analysis",
                    "id": "company.analysis.pastInsight",
                    "primaryEvidence": false,
                    "produces": "evidence",
                    "purpose": "company.analysis evidence candidate",
                    "tool": "pastInsight"
                },
                {
                    "contractId": "company.analysis",
                    "id": "company.analysis.capabilities",
                    "primaryEvidence": false,
                    "produces": "evidence",
                    "purpose": "company.analysis evidence candidate",
                    "tool": "capabilities"
                },
                {
                    "argsTemplate": {
                        "axis": "현금흐름"
                    },
                    "contractId": "cashflow.primary",
                    "id": "cashflow.primary.preflight.1",
                    "primaryEvidence": true,
                    "produces": "evidence",
                    "purpose": "cashflow.primary primary evidence",
                    "tool": "analysis"
                },
                {
                    "argsTemplate": {
                        "freq": "Y",
                        "raw": false,
                        "scope": "consolidated",
                        "topic": "CF"
                    },
                    "contractId": "cashflow.primary",
                    "id": "cashflow.primary.preflight.2",
                    "primaryEvidence": true,
                    "produces": "evidence",
                    "purpose": "cashflow.primary primary evidence",
                    "tool": "show"
                }
            ],
            "summary": "cashflow analysis process",
            "toolNames": [
                "analysis",
                "show",
                "credit",
                "pastInsight",
                "capabilities"
            ],
            "visualPolicy": {
                "preferredType": "chart",
                "requiredFor": [
                    "cashflow"
                ]
            }
        },
        "company_compare.default": {
            "acceptanceCriteria": {
                "claimSupportRateMin": 0.9,
                "primaryCsv": true,
                "requiredEvidence": [
                    "target",
                    "metric",
                    "period",
                    "value"
                ],
                "sameAxisComparison": true,
                "visual": true
            },
            "artifactPolicy": {
                "primaryCsv": true
            },
            "contractIds": [
                "company.analysis",
                "comparison.same_axis"
            ],
            "failurePolicy": {
                "onMissingEvidence": "repair_once",
                "onUnsupportedClaim": "disclose_or_repair"
            },
            "freshness": {},
            "id": "company_compare.default",
            "questionType": "company_compare",
            "requiredArtifacts": [
                "primary_csv"
            ],
            "requiredEvidence": [
                "target",
                "metric",
                "period",
                "value"
            ],
            "requiredTools": [
                "analysis",
                "show"
            ],
            "requiredVisuals": [
                "chart_or_diagram"
            ],
            "routeId": "route:company_compare",
            "steps": [
                {
                    "contractId": "company.analysis",
                    "id": "company.analysis.analysis",
                    "primaryEvidence": false,
                    "produces": "evidence",
                    "purpose": "company.analysis evidence candidate",
                    "tool": "analysis"
                },
                {
                    "contractId": "company.analysis",
                    "id": "company.analysis.show",
                    "primaryEvidence": false,
                    "produces": "evidence",
                    "purpose": "company.analysis evidence candidate",
                    "tool": "show"
                },
                {
                    "contractId": "company.analysis",
                    "id": "company.analysis.credit",
                    "primaryEvidence": false,
                    "produces": "evidence",
                    "purpose": "company.analysis evidence candidate",
                    "tool": "credit"
                },
                {
                    "contractId": "company.analysis",
                    "id": "company.analysis.pastInsight",
                    "primaryEvidence": false,
                    "produces": "evidence",
                    "purpose": "company.analysis evidence candidate",
                    "tool": "pastInsight"
                },
                {
                    "contractId": "company.analysis",
                    "id": "company.analysis.capabilities",
                    "primaryEvidence": false,
                    "produces": "evidence",
                    "purpose": "company.analysis evidence candidate",
                    "tool": "capabilities"
                },
                {
                    "argsTemplate": {
                        "axis": "종합평가"
                    },
                    "contractId": "comparison.same_axis",
                    "id": "comparison.same_axis.preflight.1",
                    "primaryEvidence": true,
                    "produces": "evidence",
                    "purpose": "comparison.same_axis primary evidence",
                    "tool": "analysis"
                },
                {
                    "argsTemplate": {
                        "fields": [
                            "매출액",
                            "영업이익"
                        ],
                        "freq": "Y",
                        "raw": false,
                        "scope": "consolidated",
                        "topic": "IS"
                    },
                    "contractId": "comparison.same_axis",
                    "id": "comparison.same_axis.preflight.2",
                    "primaryEvidence": true,
                    "produces": "evidence",
                    "purpose": "comparison.same_axis primary evidence",
                    "tool": "show"
                }
            ],
            "summary": "company_compare analysis process",
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
            "visualPolicy": {
                "preferredType": "chart_or_diagram",
                "requiredFor": [
                    "company_compare"
                ]
            }
        },
        "disclosure_importance.default": {
            "acceptanceCriteria": {
                "claimSupportRateMin": 0.9,
                "primaryCsv": true,
                "requiredEvidence": [
                    "filedAt",
                    "title",
                    "formType",
                    "basis"
                ],
                "visual": true
            },
            "artifactPolicy": {
                "primaryCsv": true
            },
            "contractIds": [
                "disclosure.importance"
            ],
            "failurePolicy": {
                "onMissingEvidence": "repair_once",
                "onUnsupportedClaim": "disclose_or_repair"
            },
            "freshness": {
                "cadence": "filing_date",
                "disclosureRequired": true
            },
            "id": "disclosure_importance.default",
            "questionType": "disclosure_importance",
            "requiredArtifacts": [
                "primary_csv"
            ],
            "requiredEvidence": [
                "filedAt",
                "title",
                "formType",
                "basis"
            ],
            "requiredTools": [],
            "requiredVisuals": [
                "diagram"
            ],
            "routeId": "route:disclosure_importance",
            "steps": [
                {
                    "contractId": "disclosure.importance",
                    "id": "disclosure.importance.disclosure",
                    "primaryEvidence": false,
                    "produces": "evidence",
                    "purpose": "disclosure.importance evidence candidate",
                    "tool": "disclosure"
                },
                {
                    "contractId": "disclosure.importance",
                    "id": "disclosure.importance.liveFilings",
                    "primaryEvidence": false,
                    "produces": "evidence",
                    "purpose": "disclosure.importance evidence candidate",
                    "tool": "liveFilings"
                },
                {
                    "contractId": "disclosure.importance",
                    "id": "disclosure.importance.filings",
                    "primaryEvidence": false,
                    "produces": "evidence",
                    "purpose": "disclosure.importance evidence candidate",
                    "tool": "filings"
                },
                {
                    "contractId": "disclosure.importance",
                    "id": "disclosure.importance.readFiling",
                    "primaryEvidence": false,
                    "produces": "evidence",
                    "purpose": "disclosure.importance evidence candidate",
                    "tool": "readFiling"
                },
                {
                    "contractId": "disclosure.importance",
                    "id": "disclosure.importance.search",
                    "primaryEvidence": false,
                    "produces": "evidence",
                    "purpose": "disclosure.importance evidence candidate",
                    "tool": "search"
                },
                {
                    "contractId": "disclosure.importance",
                    "id": "disclosure.importance.capabilities",
                    "primaryEvidence": false,
                    "produces": "evidence",
                    "purpose": "disclosure.importance evidence candidate",
                    "tool": "capabilities"
                }
            ],
            "summary": "disclosure_importance analysis process",
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
        "industry_scan.default": {
            "acceptanceCriteria": {
                "claimSupportRateMin": 0.9,
                "industryUniverse": true,
                "primaryCsv": true,
                "requiredEvidence": [
                    "industry",
                    "universe",
                    "target",
                    "metric",
                    "value"
                ],
                "sameAxisComparison": true,
                "visual": true
            },
            "artifactPolicy": {
                "primaryCsv": true
            },
            "contractIds": [
                "scan.industry_screen"
            ],
            "failurePolicy": {
                "onMissingEvidence": "repair_once",
                "onUnsupportedClaim": "disclose_or_repair"
            },
            "freshness": {},
            "id": "industry_scan.default",
            "questionType": "industry_scan",
            "requiredArtifacts": [
                "primary_csv"
            ],
            "requiredEvidence": [
                "industry",
                "universe",
                "target",
                "metric",
                "value"
            ],
            "requiredTools": [
                "industry",
                "scan",
                "pythonExec"
            ],
            "requiredVisuals": [
                "chart"
            ],
            "routeId": "route:industry_scan",
            "steps": [
                {
                    "argsTemplate": {
                        "industryId": "{industryId}"
                    },
                    "contractId": "scan.industry_screen",
                    "id": "scan.industry_screen.preflight.1",
                    "primaryEvidence": true,
                    "produces": "evidence",
                    "purpose": "scan.industry_screen primary evidence",
                    "tool": "industry"
                },
                {
                    "argsTemplate": {
                        "axis": "profitability",
                        "descending": true,
                        "limit": 50,
                        "sortBy": "ROE"
                    },
                    "contractId": "scan.industry_screen",
                    "id": "scan.industry_screen.preflight.2",
                    "primaryEvidence": true,
                    "produces": "evidence",
                    "purpose": "scan.industry_screen primary evidence",
                    "tool": "scan"
                },
                {
                    "argsTemplate": {
                        "industryId": "{industryId}",
                        "kind": "industry_scan"
                    },
                    "contractId": "scan.industry_screen",
                    "id": "scan.industry_screen.preflight.3",
                    "primaryEvidence": true,
                    "produces": "evidence",
                    "purpose": "scan.industry_screen primary evidence",
                    "tool": "pythonExec"
                }
            ],
            "summary": "industry_scan analysis process",
            "toolNames": [
                "industry",
                "scan",
                "pythonExec",
                "capabilities"
            ],
            "visualPolicy": {
                "preferredType": "chart",
                "requiredFor": [
                    "industry_scan"
                ]
            }
        },
        "macro_recent.default": {
            "acceptanceCriteria": {
                "claimSupportRateMin": 0.9,
                "requiredEvidence": [
                    "asOf",
                    "metric",
                    "value"
                ],
                "visual": true
            },
            "artifactPolicy": {},
            "contractIds": [
                "macro.recent"
            ],
            "failurePolicy": {
                "onMissingEvidence": "repair_once",
                "onUnsupportedClaim": "disclose_or_repair"
            },
            "freshness": {
                "cadence": "daily_or_policy",
                "discloseMixedAsOf": true,
                "maxStaleBusinessDays": 10
            },
            "id": "macro_recent.default",
            "questionType": "macro_recent",
            "requiredArtifacts": [],
            "requiredEvidence": [
                "asOf",
                "metric",
                "value"
            ],
            "requiredTools": [],
            "requiredVisuals": [
                "chart"
            ],
            "routeId": "route:macro_recent",
            "steps": [
                {
                    "contractId": "macro.recent",
                    "id": "macro.recent.gather",
                    "primaryEvidence": false,
                    "produces": "evidence",
                    "purpose": "macro.recent evidence candidate",
                    "tool": "gather"
                },
                {
                    "contractId": "macro.recent",
                    "id": "macro.recent.macro",
                    "primaryEvidence": false,
                    "produces": "evidence",
                    "purpose": "macro.recent evidence candidate",
                    "tool": "macro"
                },
                {
                    "contractId": "macro.recent",
                    "id": "macro.recent.capabilities",
                    "primaryEvidence": false,
                    "produces": "evidence",
                    "purpose": "macro.recent evidence candidate",
                    "tool": "capabilities"
                }
            ],
            "summary": "macro_recent analysis process",
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
        },
        "market_scan.default": {
            "acceptanceCriteria": {
                "claimSupportRateMin": 0.9,
                "primaryCsv": true,
                "requiredEvidence": [
                    "target",
                    "metric",
                    "value"
                ],
                "sameAxisComparison": true,
                "visual": true
            },
            "artifactPolicy": {
                "primaryCsv": true
            },
            "contractIds": [
                "scan.market_screen"
            ],
            "failurePolicy": {
                "onMissingEvidence": "repair_once",
                "onUnsupportedClaim": "disclose_or_repair"
            },
            "freshness": {},
            "id": "market_scan.default",
            "questionType": "market_scan",
            "requiredArtifacts": [
                "primary_csv"
            ],
            "requiredEvidence": [
                "target",
                "metric",
                "value"
            ],
            "requiredTools": [
                "scan"
            ],
            "requiredVisuals": [
                "chart"
            ],
            "routeId": "route:market_scan",
            "steps": [
                {
                    "argsTemplate": {
                        "axis": "profitability",
                        "descending": true,
                        "limit": 20,
                        "sortBy": "ROE"
                    },
                    "contractId": "scan.market_screen",
                    "id": "scan.market_screen.preflight.1",
                    "primaryEvidence": true,
                    "produces": "evidence",
                    "purpose": "scan.market_screen primary evidence",
                    "tool": "scan"
                }
            ],
            "summary": "market_scan analysis process",
            "toolNames": [
                "scan",
                "pythonExec",
                "capabilities"
            ],
            "visualPolicy": {
                "preferredType": "chart",
                "requiredFor": [
                    "market_scan"
                ]
            }
        },
        "meta_help.default": {
            "acceptanceCriteria": {
                "claimSupportRateMin": 0.9,
                "requiredEvidence": [
                    "valid_key_or_search"
                ]
            },
            "artifactPolicy": {},
            "contractIds": [
                "capabilities.valid_key"
            ],
            "failurePolicy": {
                "onMissingEvidence": "repair_once",
                "onUnsupportedClaim": "disclose_or_repair"
            },
            "freshness": {},
            "id": "meta_help.default",
            "questionType": "meta_help",
            "requiredArtifacts": [],
            "requiredEvidence": [
                "valid_key_or_search"
            ],
            "requiredTools": [],
            "requiredVisuals": [],
            "routeId": "route:meta_help",
            "steps": [
                {
                    "contractId": "capabilities.valid_key",
                    "id": "capabilities.valid_key.capabilities",
                    "primaryEvidence": false,
                    "produces": "evidence",
                    "purpose": "capabilities.valid_key evidence candidate",
                    "tool": "capabilities"
                },
                {
                    "contractId": "capabilities.valid_key",
                    "id": "capabilities.valid_key.Read",
                    "primaryEvidence": false,
                    "produces": "evidence",
                    "purpose": "capabilities.valid_key evidence candidate",
                    "tool": "Read"
                }
            ],
            "summary": "meta_help analysis process",
            "toolNames": [
                "capabilities",
                "Read"
            ],
            "visualPolicy": {}
        },
        "recent_price_mover.default": {
            "acceptanceCriteria": {
                "claimSupportRateMin": 0.9,
                "primaryCsv": true,
                "requiredEvidence": [
                    "asOf",
                    "period",
                    "universe",
                    "metric"
                ],
                "sameAxisComparison": true,
                "visual": true
            },
            "artifactPolicy": {
                "primaryCsv": true
            },
            "contractIds": [
                "gather.krx.close"
            ],
            "failurePolicy": {
                "onMissingEvidence": "repair_once",
                "onUnsupportedClaim": "disclose_or_repair"
            },
            "freshness": {
                "cadence": "daily",
                "maxStaleBusinessDays": 10
            },
            "id": "recent_price_mover.default",
            "questionType": "recent_price_mover",
            "requiredArtifacts": [
                "primary_csv"
            ],
            "requiredEvidence": [
                "asOf",
                "period",
                "universe",
                "metric"
            ],
            "requiredTools": [
                "pythonExec"
            ],
            "requiredVisuals": [
                "chart"
            ],
            "routeId": "route:recent_price_mover",
            "steps": [
                {
                    "argsTemplate": {
                        "kind": "krx_price_mover"
                    },
                    "contractId": "gather.krx.close",
                    "id": "gather.krx.close.preflight.1",
                    "primaryEvidence": true,
                    "produces": "evidence",
                    "purpose": "gather.krx.close primary evidence",
                    "tool": "pythonExec"
                }
            ],
            "summary": "recent_price_mover analysis process",
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
        }
    },
    "routes": [
        {
            "contractIds": [
                "company.analysis",
                "comparison.same_axis"
            ],
            "id": "route:company_compare",
            "processMapIds": [
                "company_compare.default"
            ],
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
            "triggers": {
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
            }
        },
        {
            "contractIds": [
                "company.analysis",
                "cashflow.primary"
            ],
            "id": "route:cashflow",
            "processMapIds": [
                "cashflow.default"
            ],
            "questionType": "cashflow",
            "toolNames": [
                "analysis",
                "show",
                "credit",
                "pastInsight",
                "capabilities"
            ],
            "triggers": {
                "any": [
                    "현금흐름",
                    "cashflow",
                    "cash flow",
                    "fcf",
                    "ocf"
                ]
            }
        },
        {
            "contractIds": [
                "capabilities.valid_key"
            ],
            "id": "route:meta_help",
            "processMapIds": [
                "meta_help.default"
            ],
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
            "processMapIds": [
                "disclosure_importance.default"
            ],
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
            "processMapIds": [
                "recent_price_mover.default"
            ],
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
                        "rank",
                        "rose",
                        "risen",
                        "gainer",
                        "gainers",
                        "recently"
                    ]
                ]
            }
        },
        {
            "contractIds": [
                "macro.recent"
            ],
            "id": "route:macro_recent",
            "processMapIds": [
                "macro_recent.default"
            ],
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
        },
        {
            "contractIds": [
                "scan.industry_screen"
            ],
            "id": "route:industry_scan",
            "processMapIds": [
                "industry_scan.default"
            ],
            "questionType": "industry_scan",
            "toolNames": [
                "industry",
                "scan",
                "pythonExec",
                "capabilities"
            ],
            "triggers": {
                "allAny": [
                    [
                        "scan",
                        "screen",
                        "screening",
                        "compare",
                        "comparison",
                        "비교",
                        "스크리닝",
                        "찾아",
                        "좋은",
                        "수익성"
                    ],
                    [
                        "industry",
                        "sector",
                        "업종",
                        "산업",
                        "반도체",
                        "semiconductor"
                    ]
                ]
            }
        },
        {
            "contractIds": [
                "scan.market_screen"
            ],
            "id": "route:market_scan",
            "processMapIds": [
                "market_scan.default"
            ],
            "questionType": "market_scan",
            "toolNames": [
                "scan",
                "pythonExec",
                "capabilities"
            ],
            "triggers": {
                "any": [
                    "scan",
                    "screen",
                    "screening",
                    "profitable stocks",
                    "profitability",
                    "industry",
                    "sector",
                    "업종",
                    "산업",
                    "스크리닝",
                    "종목 발굴",
                    "좋은 종목",
                    "수익성 좋은"
                ]
            }
        }
    ],
    "sourceHash": "2f423b03135c1715"
}
"""
)
