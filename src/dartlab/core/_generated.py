"""런타임 capabilities 카탈로그 (자동 생성).

이 파일은 scripts/build/generateSpec.py가 자동 생성합니다. 직접 수정 금지.
"""

import json

CAPABILITIES: dict[str, dict] = json.loads(
    r"""
{
    "ChartResult": {
        "kind": "class",
        "summary": "chart() 반환 객체 — 시각화 + 렌더링."
    },
    "Company": {
        "aicontext": "AI 는 `dartlab.ask()` 로 접근 (Company 를 직접 생성하지 않음).\n사람은 Company 객체 하나로 노트북·스크립트에서 모든 엔진 호출.\n엔진은 사람의 분석엔진이자 AI 의 skill (docstring SSOT) — 한 파일 두 역할.",
        "args": "codeOrName: 종목코드, 회사명, 또는 영문 ticker.",
        "capabilities": "종목 파사드 하나로 엔진 전수 접근: analysis · credit · quant · macro ·\nindustry · gather · show. 엔진 이름만 기억하면 됨.\n종목코드 (\"005930\"), 회사명 (\"삼성전자\"), 영문 ticker (\"AAPL\") 모두 지원\ncanHandle() 체인: provider priority 순 자동 라우팅 (DART → EDGAR)\n새 국가 추가 시 이 파일 수정 불필요 — provider 패키지만 추가\n핵심 인터페이스: show(topic) / index / trace(topic) / diff() / select()\n모든 데이터 접근은 ``c.show(topic)`` 으로 통합 — finance topic\n(BS·IS·CF·CIS·SCE·ratios) 도 ``c.show(\"BS\")`` · ``c.show(\"IS\", freq=\"Y\")``\n처럼 호출. 별도 namespace property 나 바로가기는 사용하지 않는다\n(``c.docs / c.finance / c.report / c.profile`` · ``c.BS / c.IS / c.CF /\nc.CIS / c.ratios / c.timeseries`` 는 Plan v10 에서 제거).\n메타: sections, topics, filings(), market, currency",
        "example": "import dartlab\n\n# 사람의 만능 관문 — 한 객체로 전 엔진\nc = dartlab.Company(\"005930\")     # 삼성전자 (DART)\nc.story()                         # 분석 스토리 (보고서)\nc.analysis(\"financial\", \"수익성\") # 재무 분석\nc.credit()                        # 신용\nc.quant()                         # 주가\nc.show(\"businessOverview\")        # 원본 사업 개요\n\n# 글로벌 (EDGAR 자동 라우팅)\nc = dartlab.Company(\"AAPL\")\nc.analysis(\"financial\", \"valuation\")\n\n# module-level 엔진도 `stockCode=` 로 호출 가능 (일관성 규약)\ndartlab.analysis.financial(\"수익성\", stockCode=\"005930\")\ndartlab.credit(stockCode=\"005930\")",
        "guide": "\"삼성전자 재무제표\" -> c = Company(\"005930\"); c.show(\"IS\")\n\"사업 개요 보여줘\" -> c.show(\"businessOverview\")\n\"어떤 데이터 있어?\" -> c.index 또는 c.topics\n\"출처 추적\" -> c.trace(\"revenue\")\n\"기간 변화\" -> c.diff()\n\"종합평가\" -> c.analysis(\"financial\", \"종합평가\")\n\"스토리 보고서\" -> c.story()\n\"Apple 분석\" -> Company(\"AAPL\") (자동 EDGAR 라우팅)",
        "kind": "function",
        "requires": "DART: 사전 다운로드 데이터 (dartlab.downloadAll() 또는 자동 다운로드).\nEDGAR: 인터넷 연결 (On-demand 수집).",
        "returns": "CompanyProtocol — DART 또는 EDGAR Company 인스턴스 (파사드).",
        "seeAlso": "dartlab.ask: AI 대화 (투톱 다른 관문)\nsearch: 종목 검색 (종목코드 모를 때)\nscan: 전종목 횡단분석 (Company-독립)\nmacro: 시장 레벨 거시 (Company-독립)\nindustry: 섹터 밸류체인 (Company-독립)",
        "summary": "**사람의 최상위 관문** — 종목 하나의 모든 엔진에 접근하는 파사드."
    },
    "Company.analysis": {
        "aicontext": "ask()/chat()에서 분석 결과를 컨텍스트로 주입\nstory가 내부적으로 analysis 결과를 소비",
        "args": "axis: 그룹 이름 (\"financial\", \"valuation\", \"forecast\") 또는 축 이름. None이면 가이드 반환.\nsub: 그룹 내 하위 축 이름 (\"수익성\", \"가치평가\", \"매출전망\" 등).\n**kwargs: 축별 추가 옵션.",
        "artifactPolicy": {
            "primaryCsv": true
        },
        "capabilities": "14축 분석: 수익구조, 자금조달, 자산구조, 현금흐름, 수익성, 성장성, 안정성, 효율성, 종합평가, 이익품질, 비용구조, 자본배분, 투자효율, 재무정합성\n축 없이 호출 시 14축 가이드 반환\n개별 축 분석 시 Company 바인딩 (self 자동 전달)\n2-level 호출: c.analysis(\"financial\", \"수익성\"), c.analysis(\"valuation\", \"가치평가\")",
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
        "example": "c = Company(\"005930\")\nc.analysis()                            # 전체 가이드\nc.analysis(\"financial\", \"수익구조\")       # 수익구조 분석\nc.analysis(\"valuation\", \"가치평가\")       # 가치평가\nc.analysis(\"forecast\", \"매출전망\")        # 매출전망",
        "guide": "When: 특정 종목의 재무 심층 분석이 필요할 때.\nHow: axis 로 분석 영역, sub 로 세부 축 지정.\n\"14축 분석 뭐가 있어?\" → c.analysis() (가이드 반환)\n\"수익구조 분석해줘\" → c.analysis(\"financial\", \"수익구조\")\n\"안정성 분석\" → c.analysis(\"financial\", \"안정성\")\n\"가치평가 해줘\" → c.analysis(\"valuation\", \"가치평가\")\n\"매출전망\" → c.analysis(\"forecast\", \"매출전망\")\nVerified:\n수익성 단독 → 마진 시계열 + 전환점 + 반도체 사이클 인과 (observed via ai-ask, 2026-04-25 — 정식 Phase P 판정 아님)\n이익품질 + 재무정합성 → 분식회계 가능성 판정 (observed via ai-ask, 2026-04-25 — 정식 Phase P 판정 아님)\n가치평가 → 적정주가 범위 + 현재가 대비 판정 (observed via ai-ask, 2026-04-25 — 정식 Phase P 판정 아님)\n자본배분 + 현금흐름 → 배당 매력 종합 판단 (observed via ai-ask, 2026-04-25 — 정식 Phase P 판정 아님)\n지배구조 → 이사회 독립성 + 지배력 집중 점검 (observed via ai-ask, 2026-04-25 — 정식 Phase P 판정 아님)",
        "kind": "property",
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
        "returns": "pl.DataFrame | dict — axis=None이면 가이드 DataFrame (axis/label/description/example/group/items).\naxis 지정 시 dict:\n{calcName} : dict — 축별 계산 결과\nhistory : list[dict] — 시계열 ({period, ...지표})\ndisplayHints : dict — core 컬럼 목록\nturningPoints : list — 전환점 (있으면)\n{calcName}Flags : list[str] — 경고 플래그\ndataAsOf : dict — latestPeriod, retrievedAt\n_summary (autoEnrich 자동 주입) — 핵심 지표 요약 + [엔진가정] 블록.\nassumptions — 엔진 가정 (overrides 재호출용).",
        "seeAlso": "story: 14축 분석을 14개 섹션 보고서로 조합\ninsights: 7영역 등급 요약 (analysis보다 요약적)\nratios: 재무비율 시계열 (analysis의 입력 데이터)",
        "summary": "재무제표 완전 분석 — 14축, 단일 종목 심층 (내부 구현).",
        "tool": "analysis"
    },
    "Company.ask": {
        "aicontext": "AI가 분석 전 과정을 주도. dartlab 엔진(analysis, scan, gather 등)을\n도구로 호출하여 데이터 수집, 계산, 판단, 해석을 수행.",
        "args": "question: 질문 텍스트.\ninclude: 포함할 분석 패키지 목록. None이면 자동 선택.\nexclude: 제외할 분석 패키지 목록.\nprovider: LLM provider 이름 (openai, ollama, codex 등). None이면 기본값.\nmodel: 모델명. None이면 provider 기본값.\nstream: True면 스트리밍 제너레이터 반환.\nreflect: True면 답변 후 자기 평가 수행.\n**kwargs: provider별 추가 옵션.",
        "capabilities": "엔진 계산 결과를 컨텍스트로 조립하여 LLM에 전달\n질문 분류 기반 분석 패키지 자동 선택 (financial, valuation, risk 등)\n멀티 provider 지원 (openai, ollama, codex 등)\n스트리밍 응답 지원",
        "example": "c = Company(\"005930\")\nc.ask(\"영업이익률 추세는?\")\nc.ask(\"핵심 리스크 3가지\", provider=\"codex\")\n\n# 스트리밍\nfor chunk in c.ask(\"배당 분석해줘\", stream=True):\nprint(chunk, end=\"\")",
        "guide": "\"영업이익률 분석해줘\" → c.ask(\"영업이익률 추세는?\")\n\"AI한테 질문하고 싶어\" → c.ask(\"질문\")\n\"스트리밍으로 답변받기\" → c.ask(\"질문\", stream=True)",
        "kind": "method",
        "requires": "API 키: LLM provider API 키 (OPENAI_API_KEY 등)",
        "returns": "str -- LLM 응답 텍스트. stream=True면 Generator[str].",
        "seeAlso": "chat: 에이전트 모드 (tool calling 기반 심화 분석)\nask: AI 종합 분석 (자연어 대화)\nstory: AI 없는 데이터 검토서",
        "summary": "LLM에게 이 기업에 대해 질문."
    },
    "Company.audit": {
        "aicontext": "감사 리스크 종합 평가 — 투자 의사결정의 핵심 안전장치\n감사의견 변경, 계속기업 불확실성은 최고 경고 수준",
        "args": "없음 (self 바인딩).",
        "capabilities": "감사의견 추이 (적정/한정/부적정/의견거절)\n감사인 변경 이력 + 사유\n계속기업 불확실성 플래그\n핵심감사사항 (KAM) 추출\n내부회계관리제도 검토의견",
        "example": "c = Company(\"005930\")\nc.audit()",
        "guide": "\"감사의견 확인\" → c.audit()\n\"감사인 바뀌었어?\" → c.audit()[\"auditorChanges\"]\n\"계속기업 의문은?\" → c.audit()[\"goingConcern\"]",
        "kind": "method",
        "requires": "데이터: docs + report (자동 다운로드)",
        "returns": "dict\nopinion : str — 감사의견 (\"적정\", \"한정\", \"부적정\", \"의견거절\")\nauditorChanges : list[dict] — 감사인 변경 이력 (year, from, to, reason)\ngoingConcern : bool — 계속기업 불확실성 존재 여부\nkam : list[str] — 핵심감사사항 목록\ninternalControl : str — 내부회계관리제도 검토의견",
        "seeAlso": "governance: 지배구조 분석 (감사위원회 구성 포함)\ninsights: 종합 등급 (감사 리스크도 반영)\nstory: 재무정합성 섹션에서 감사 결과 활용",
        "summary": "감사 리스크 종합 분석."
    },
    "Company.canHandle": {
        "kind": "method",
        "returns": "bool\nTrue 면 DART provider 로 처리. 6자리 alphanumeric (KR 종목코드)\n또는 한글 포함 문자열이면 True.",
        "summary": "DART 종목코드(6자) 또는 한글 회사명이면 처리 가능."
    },
    "Company.capital": {
        "aicontext": "주주환원 정책 평가 — 배당수익률/성향/자사주 정량 데이터\n시장 횡단 비교로 상대적 환원 수준 판단",
        "args": "view: None → 이 회사 행, \"all\" → 전체, \"market\" → 시장별 요약.",
        "capabilities": "배당수익률 + 배당성향 추이\n자사주 매입/소각 이력\n총주주환원율 (배당 + 자사주)\n시장 전체 주주환원 횡단 비교",
        "example": "c = Company(\"005930\")\nc.capital()              # 삼성전자 주주환원\nc.capital(\"all\")         # 전체 상장사",
        "guide": "\"배당 정보\" → c.capital() 또는 c.show(\"dividend\")\n\"주주환원율은?\" → c.capital()\n\"전체 상장사 배당 비교\" → c.capital(\"all\")",
        "kind": "method",
        "requires": "데이터: DART 정기보고서 (자동 수집)",
        "returns": "pl.DataFrame | None\n종목코드 : str — 6자리 종목코드\n종목명 : str — 회사명\n배당수익률 : float — 배당수익률 (%)\n배당성향 : float — 배당성향 (%)\n자사주매입 : int — 자사주 매입 주수\n총환원율 : float — (배당 + 자사주) / 시가총액 (%)\n분류 : str — 환원형/중립/희석형\n데이터 없으면 None.",
        "seeAlso": "show: c.show(\"dividend\")로 docs 기반 배당 상세\nsceMatrix: 자본변동표 (배당/자사주가 자본에 미치는 영향)\ndebt: 부채 구조 (자본 정책의 다른 면)",
        "summary": "주주환원 분석 (배당, 자사주, 총환원율)."
    },
    "Company.causalWeights": {
        "guide": "\"인과 체인\" → c.causalWeights()\n\"어느 막이 약해\" → 결과의 direction='dampen' 필터",
        "kind": "method",
        "returns": "list[dict] — from_act/to_act/metric_from/metric_to/delta_from/delta_to/weight/direction",
        "summary": "6막 인과 가중치 — 수익구조→수익성→현금흐름→자금조달→자산배치→가치평가 amplify/dampen/neutral."
    },
    "Company.codeName": {
        "args": "stockCode: 6자리 종목코드.",
        "kind": "method",
        "returns": "str | None — 회사명. 못 찾으면 None.",
        "summary": "종목코드 → 회사명 변환."
    },
    "Company.contextSlices": {
        "aicontext": "ask()/chat()의 시스템 프롬프트에 직접 주입되는 데이터\nLLM이 소비하는 최종 형태의 컨텍스트",
        "capabilities": "retrievalBlocks를 LLM 컨텍스트 윈도우에 맞게 슬라이싱\n토큰 예산 내에서 최대한 많은 관련 정보를 담는 압축 포맷\ntopic/period 기준 우선순위 정렬",
        "example": "c = Company(\"005930\")\nc.contextSlices            # LLM용 context 슬라이스",
        "guide": "\"LLM에 들어가는 컨텍스트\" → c.contextSlices\n\"AI가 보는 데이터\" → c.contextSlices",
        "kind": "property",
        "requires": "데이터: docs (자동 다운로드)",
        "returns": "pl.DataFrame | None -- 슬라이싱된 context 블록. docs 없으면 None.",
        "seeAlso": "retrievalBlocks: 슬라이싱 전 전체 retrieval 블록\nask: contextSlices를 내부적으로 소비하는 AI 질문 인터페이스",
        "summary": "LLM 투입용 context slice DataFrame."
    },
    "Company.credit": {
        "args": "axis: 축 이름 (\"채무상환\", \"자본구조\" 등). None이면 등급 종합.\ndetail: True이면 7축 상세 + 지표 시계열 포함.\nbasePeriod: 분석 기준 기간. None이면 최신.\noverrides: AI/사용자가 엔진 계산 가정을 직접 교체하는 dict.\n키: debtRatio, interestCoverage, currentRatio, quickRatio, ocfToDebt,\nfcfToDebt, scenarioStress. 상세: core/overrides.py.",
        "example": "c.credit()              # → {\"grade\": \"dCR-AA\", \"score\": 6.6, ...}\nc.credit(\"채무상환\")     # → {\"axis\": \"채무상환능력\", \"score\": 2.7, ...}\nc.credit(detail=True)   # → 7축 상세 + metricsHistory\nc.credit(overrides={\"debtRatio\": 150, \"interestCoverage\": 2.5})  # 스트레스 시나리오",
        "guide": "When: 부도 위험·신용등급·채무상환능력 판단이 필요할 때.\nHow: 무인자 호출로 종합 등급, axis 로 개별 축, detail=True 로 시계열.\nVerified:\ncredit 단독 → dCR 등급 + 7축 위험점수 분해 + PD 추정 (observed via ai-ask, 2026-04-25 — 정식 Phase P 판정 아님)\ncredit + analysis(안정성,현금흐름) → 부도 위험 종합 진단 (observed via ai-ask, 2026-04-25 — 정식 Phase P 판정 아님)",
        "kind": "property",
        "returns": "dict | None: 등급 결과. axis 지정 시 해당 축만.",
        "seeAlso": "story(\"신용평가\"): 보고서 형식으로 렌더링\nanalysis(\"financial\", \"신용평가\"): analysis 축으로 접근",
        "summary": "독립 신용평가 — dCR 20단계 등급 (내부 구현)."
    },
    "Company.currency": {
        "example": "c = Company(\"005930\")\nc.currency  # \"KRW\"",
        "kind": "property",
        "returns": "str — \"KRW\".",
        "seeAlso": "market: 시장 코드",
        "summary": "통화 코드 (DART 제공자는 항상 KRW)."
    },
    "Company.debt": {
        "aicontext": "부채 구조/건전성 정량 평가 — 차입금 의존도, 만기 구조\n시장 횡단 비교로 상대적 재무 안정성 판단",
        "args": "view: None → 이 회사 행, \"all\" → 전체, \"market\" → 시장별 요약.",
        "capabilities": "총차입금 + 순차입금 규모\n부채비율 + 차입금의존도\n단기/장기 차입금 비율\n시장 전체 부채 구조 횡단 비교",
        "example": "c = Company(\"005930\")\nc.debt()                 # 삼성전자 부채 구조\nc.debt(\"all\")            # 전체 상장사",
        "guide": "\"부채 구조 분석\" → c.debt()\n\"부채비율은?\" → c.debt() 또는 c.show(\"ratios\")\n\"전체 상장사 부채 비교\" → c.debt(\"all\")",
        "kind": "method",
        "requires": "데이터: DART 정기보고서 (자동 수집)",
        "returns": "pl.DataFrame | None\n종목코드 : str — 6자리 종목코드\n종목명 : str — 회사명\n부채비율 : float — 부채비율 (%)\n차입금의존도 : float — 차입금의존도 (%)\nICR : float — 이자보상배율 (배)\n위험등급 : str — 안전/주의/경고/위험\n데이터 없으면 None.",
        "seeAlso": "BS: 재무상태표 (부채 원본 데이터)\nratios: 재무비율 (부채비율 포함)\ncapital: 주주환원 (자본 정책의 다른 면)",
        "summary": "부채 구조 분석 (차입금, 부채비율, 만기 구조)."
    },
    "Company.diff": {
        "aicontext": "기간간 공시 변경 감지 — 사업 방향 전환, 리스크 요인 변화 탐지\nwatch()보다 세밀한 줄 단위 변경 추적",
        "args": "topic: topic 이름. None이면 전체 변경 요약.\nfromPeriod: 비교 시작 기간 (\"2023\").\ntoPeriod: 비교 끝 기간 (\"2024\").",
        "capabilities": "전체 topic 변경 요약 (변경량 스코어링)\n특정 topic 기간별 변경 이력\n두 기간 줄 단위 diff (추가/삭제/변경)",
        "example": "c.diff()                                    # 전체 변경 요약\nc.diff(\"businessOverview\")                  # 사업개요 변경 이력\nc.diff(\"businessOverview\", \"2023\", \"2024\")  # 줄 단위 diff",
        "guide": "\"공시에서 뭐가 바뀌었어?\" → c.diff()\n\"사업개요 변경 이력\" → c.diff(\"businessOverview\")\n\"2023 vs 2024 차이\" → c.diff(\"businessOverview\", \"2023\", \"2024\")",
        "kind": "method",
        "requires": "데이터: docs (2개 이상 기간 필요)",
        "returns": "pl.DataFrame | None — 변경 요약, 히스토리, 또는 줄 단위 diff.",
        "seeAlso": "watch: 변화 중요도 스코어링 (diff보다 요약적)\nkeywordTrend: 키워드 빈도 추이 (텍스트 변화의 다른 관점)\nshow: 특정 기간 원문 조회",
        "summary": "기간간 텍스트 변경 비교."
    },
    "Company.disclosure": {
        "aicontext": "특정 종목의 공시 빈도/유형 패턴 → 이벤트 감지\n단일 종목 분석 시 최근 공시 컨텍스트 보강용",
        "args": "start: 조회 시작일 (YYYYMMDD 또는 YYYY-MM-DD). None이면 최근 days일.\nend: 조회 종료일. None이면 오늘.\ndays: start/end 없을 때 최근 일수. 기본 365.\ntype: 공시유형 필터 (A=정기, B=주요사항, C=발행, D=지분, E=기타, F=외부감사). None이면 전체.\nkeyword: 제목/회사명 키워드 필터.\nfinalOnly: True면 최종보고서만 (정정 이전 제외).",
        "capabilities": "전체 공시유형 조회 (정기, 주요사항, 발행, 지분, 외부감사 등)\n기간, 유형, 키워드 필터링\n최종보고서만 필터 (정정 이전 제외)",
        "example": "c = Company(\"005930\")\nc.disclosure()                  # 최근 1년 전체 공시\nc.disclosure(days=30)           # 최근 30일\nc.disclosure(type=\"A\")          # 정기공시만\nc.disclosure(keyword=\"사업보고서\")",
        "guide": "단일 종목: \"삼성전자 최근 공시 뭐 나왔어?\" → c.disclosure(days=30)\n전종목: \"최근 어떤 회사들이 자사주 매입했어?\" → dartlab.search(\"자기주식 취득\")",
        "kind": "method",
        "requires": "API 키: DART_API_KEY",
        "returns": "pl.DataFrame -- docId, filedAt, title, formType 등 공시 목록 (이 종목 한정).",
        "seeAlso": "dartlab.search: **전종목 공시 검색 — 키워드 기반 (이 함수 대안)**\nliveFilings: 실시간 최신 공시 (정규화된 포맷, 단일 종목)\nreadFiling: 공시 원문 텍스트 읽기\nfilings: 로컬 보유 공시 목록 (단일 종목)",
        "summary": "**[단일 종목 전용]** OpenDART 공시 목록 조회. **stockCode 필수**."
    },
    "Company.facts": {
        "kind": "property",
        "returns": "pl.DataFrame | None\ntopic : str — 데이터 소스 topic\nperiod : str — 기간 (예: \"2025Q4\")\nvalue : str — 해당 topic/period 의 텍스트 또는 숫자 요약\n데이터 없으면 None.",
        "summary": "topic × period 형태의 통합 facts 테이블 (sections + finance + report merge)."
    },
    "Company.filings": {
        "aicontext": "어떤 공시가 보유돼 있는지 확인하여 분석 범위 결정에 활용",
        "capabilities": "로컬에 보유한 공시 문서 목록\n기간별, 문서유형별 정리\nDART 뷰어 링크 포함",
        "guide": "\"이 회사 공시 목록 보여줘\" → c.filings()\n\"어떤 보고서가 있어?\" → c.filings()로 보유 문서 확인",
        "kind": "method",
        "requires": "데이터: docs (자동 다운로드)",
        "returns": "pl.DataFrame | None — year, rceptDate, rceptNo, reportNm, viewerUrl 등.",
        "seeAlso": "disclosure: OpenDART API 기반 실시간 공시 목록 (로컬 보유가 아닌 전체)\nliveFilings: 최신 공시 실시간 조회\nupdate: 누락 공시 증분 수집",
        "summary": "공시 문서 목록 + DART 뷰어 링크."
    },
    "Company.fiscalYearEnd": {
        "kind": "property",
        "returns": "\"12-31\".",
        "summary": "회계연도 종료 월-일 (한국 종목은 12-31 표준)."
    },
    "Company.gather": {
        "aicontext": "ask()/chat()에서 주가/수급/거시 데이터를 컨텍스트로 주입\n기업 분석 시 시장 데이터 보충 자료로 활용",
        "args": "axis: 축 이름 (\"price\", \"flow\", \"macro\", \"news\"). None이면 가이드 반환.\n**kwargs: market, start, end, days 등 축별 옵션.",
        "capabilities": "price: OHLCV 주가 시계열 (KR Naver / US Yahoo)\nflow: 외국인/기관 수급 동향 (KR 전용)\nmacro: ECOS(KR) / FRED(US) 거시지표 시계열 (기본 HF 벌크)\nnews: Google News RSS 뉴스 수집\n자동 fallback 체인, circuit breaker, TTL 캐시",
        "example": "c = Company(\"005930\")\nc.gather()                 # 4축 가이드\nc.gather(\"price\")          # 주가 시계열\nc.gather(\"news\")           # 뉴스",
        "guide": "When: 주가·수급·거시지표·뉴스 원본 데이터가 필요할 때.\nHow: axis 로 데이터 종류 지정. 무인자 = 가이드.\n\"주가 데이터\" → c.gather(\"price\")\n\"외국인/기관 수급\" → c.gather(\"flow\")\n\"거시경제 지표\" → c.gather(\"macro\")\n\"뉴스 수집\" → c.gather(\"news\") 또는 c.news()\nVerified:\ngather(\"news\") → 뉴스 목록 + 헤드라인 해석 (observed via ai-ask, 2026-04-25 — 정식 Phase P 판정 아님)",
        "kind": "method",
        "requires": "price/flow/news: 없음 (공개 API)\nmacro: 불필요 -- apiKey 명시 시 ECOS/FRED 직접 API 호출",
        "returns": "pl.DataFrame | None\naxis=None (가이드):\naxis : str — 축 이름\nlabel : str — 한글 레이블\ndescription : str — 설명\nexample : str — 사용 예시\naxis=\"price\":\ndate : date — 날짜\nopen : float — 시가 (원)\nhigh : float — 고가 (원)\nlow : float — 저가 (원)\nclose : float — 종가 (원)\nvolume : int — 거래량\naxis=\"flow\":\ndate : date — 날짜\n외국인순매수 : int — 외국인 순매수량\n기관순매수 : int — 기관 순매수량\n(KR 전용. EDGAR ticker는 None 반환)\naxis=\"macro\":\ndate : date — 날짜\n지표별 컬럼 : float — ECOS/FRED 거시지표 값\naxis=\"news\":\ntitle : str — 뉴스 제목\nlink : str — 기사 URL\npubDate : str — 발행일\n데이터 없으면 None.",
        "seeAlso": "news: 뉴스 전용 단축 메서드\nask: gather 데이터를 컨텍스트로 활용한 AI 분석",
        "summary": "외부 시장 데이터 수집 — 4축 (price/flow/macro/news)."
    },
    "Company.governance": {
        "aicontext": "지배구조 리스크 평가 — 사외이사/감사위원/최대주주 정량 데이터\n시장 횡단 비교로 상대적 거버넌스 수준 판단",
        "args": "view: None → 이 회사 행, \"all\" → 전체, \"market\" → 시장별 요약.",
        "capabilities": "사외이사 비율 + 감사위원회 구성\n최대주주 지분율 + 특수관계인\n시장 전체 거버넌스 횡단 비교",
        "example": "c = Company(\"005930\")\nc.governance()           # 삼성전자 거버넌스\nc.governance(\"all\")      # 전체 상장사",
        "guide": "\"지배구조 분석\" → c.governance()\n\"사외이사 비율은?\" → c.governance()\n\"전체 상장사 거버넌스 비교\" → c.governance(\"all\")",
        "kind": "method",
        "requires": "데이터: DART 정기보고서 (자동 수집)",
        "returns": "pl.DataFrame | None\n종목코드 : str — 6자리 종목코드\n종목명 : str — 회사명\n최대주주지분율 : float — 최대주주 + 특수관계인 지분율 (%)\n사외이사비율 : float — 사외이사 비율 (%)\n감사위원회 : str — 감사위원회 설치 여부\n종합점수 : float — 거버넌스 종합 점수 (100점 만점)\n등급 : str — A/B/C/D/E 등급\n데이터 없으면 None.",
        "seeAlso": "network: 출자/계열사 관계 (거버넌스의 다른 관점)\naudit: 감사 리스크 (감사위원회와 연관)",
        "summary": "지배구조 분석 (이사회, 감사위원, 최대주주)."
    },
    "Company.index": {
        "aicontext": "LLM이 Company 전체 구조를 파악하는 핵심 진입점\nask()에서 어떤 데이터를 참조할지 결정하는 기초 정보",
        "capabilities": "docs sections + finance + report 전체를 하나의 목차로 통합\n각 항목의 chapter, topic, label, kind, source, periods, shape, preview 제공\nsections 메타데이터 + 존재 확인만으로 구성 (파서 미호출, lazy)\nviewer/렌더러가 소비하는 메타데이터 원천",
        "example": "c = Company(\"005930\")\nc.index                    # 전체 구조 목차\nc.index.filter(pl.col(\"source\") == \"docs\")  # docs 항목만",
        "guide": "\"전체 목차 보여줘\" → c.index\n\"어떤 데이터가 있는지 구조적으로\" → c.index",
        "kind": "property",
        "requires": "데이터: docs/finance/report 중 하나 이상 (자동 다운로드)",
        "returns": "pl.DataFrame -- 컬럼: chapter, topic, label, kind, source, periods, shape, preview",
        "seeAlso": "topics: topic 단위 요약 (index보다 간결)\nsections: 전체 sections 지도 (index의 원본)\nprofile: 통합 프로필 접근자",
        "summary": "현재 공개 Company 구조 인덱스 DataFrame -- 전체 데이터 목차."
    },
    "Company.industry": {
        "example": "c = Company(\"005930\")\npos = c.industry()\n# {'chainId': 'semiconductor', 'stage': 'fab', 'stageLabel': '전공정(FAB)', ...}",
        "kind": "method",
        "returns": "dict | None: 산업 내 위치 정보.\nchainId, chainName, stage, stageLabel, confidence, matches, products, peers.\n매칭 실패 시 None.",
        "summary": "이 회사의 밸류체인 산업 내 위치를 분석한다."
    },
    "Company.keywordTrend": {
        "aicontext": "공시 텍스트의 키워드 빈도 변화로 전략 방향 전환 감지\nAI, ESG, 탄소중립 등 트렌드 키워드 모니터링",
        "args": "keyword: 단일 키워드. None이면 내장 키워드 전체.\nkeywords: 복수 키워드 리스트.",
        "capabilities": "공시 텍스트에서 키워드 빈도 추이 분석\n54개 내장 키워드 세트 (AI, ESG, 탄소중립 등)\ntopic별 x 기간별 빈도 매트릭스\n복수 키워드 동시 검색",
        "example": "c.keywordTrend(\"AI\")\nc.keywordTrend(keywords=[\"AI\", \"ESG\"])\nc.keywordTrend()                  # 54개 내장 키워드 전체",
        "guide": "\"AI 언급 추이\" → c.keywordTrend(\"AI\")\n\"ESG 관련 변화\" → c.keywordTrend(\"ESG\")\n\"전체 키워드 트렌드\" → c.keywordTrend()",
        "kind": "method",
        "requires": "데이터: docs (자동 다운로드)",
        "returns": "pl.DataFrame | None — topic x period x keyword 빈도.",
        "seeAlso": "diff: 텍스트 줄 단위 변경 비교 (키워드가 아닌 전체 변경)\nwatch: 변화 중요도 스코어링",
        "summary": "공시 텍스트 키워드 빈도 추이 (topic x period x keyword)."
    },
    "Company.listing": {
        "args": "forceRefresh: True면 캐시 무시, KIND에서 재다운로드.",
        "capabilities": "KOSPI + KOSDAQ 전체 상장법인\n종목코드, 종목명, 시장구분, 업종",
        "kind": "method",
        "requires": "데이터: listing (자동 다운로드)",
        "returns": "pl.DataFrame — code, name, market, sector 등.",
        "summary": "KRX 전체 상장법인 목록 (KIND 기준)."
    },
    "Company.liveFilings": {
        "aicontext": "최신 공시 모니터링으로 기업 이벤트(배당, 유증, 합병 등) 실시간 감지\nreadFiling()과 조합하여 최신 공시 원문 분석",
        "args": "start: 조회 시작일 (YYYYMMDD 또는 YYYY-MM-DD). None이면 최근 days일.\nend: 조회 종료일. None이면 오늘.\ndays: start/end 없을 때 최근 일수. None이면 기본값 적용.\nlimit: 최대 반환 건수. 기본 20.\nkeyword: 제목/회사명 키워드 필터.\nforms: 미사용 (DART는 forms 개념 없음).\nfinalOnly: True면 최종보고서만 (정정 이전 제외).",
        "capabilities": "OpenDART API 실시간 공시 조회\n기간, 건수, 키워드 필터링\n정규화된 컬럼 (docId, filedAt, title, formType 등)",
        "example": "c = Company(\"005930\")\nc.liveFilings()                 # 최근 공시 20건\nc.liveFilings(days=7)           # 최근 7일\nc.liveFilings(keyword=\"배당\")   # 키워드 필터",
        "guide": "\"최근 공시 확인해줘\" → c.liveFilings()\n\"이번 주 공시 있어?\" → c.liveFilings(days=7)\n\"배당 관련 공시\" → c.liveFilings(keyword=\"배당\")",
        "kind": "method",
        "requires": "API 키: DART_API_KEY",
        "returns": "pl.DataFrame -- docId, filedAt, title, formType, docUrl, viewerUrl 등 정규화된 공시 목록.",
        "seeAlso": "disclosure: 과거 전체 공시 이력 조회\nreadFiling: 공시 원문 텍스트 읽기\nwatch: 공시 변화 중요도 스코어링",
        "summary": "OpenDART 기준 실시간 공시 목록 조회."
    },
    "Company.macro": {
        "guide": "When: 거시경제 환경·사이클 판단이 필요할 때.\nHow: axis 로 분석 영역 지정. 무인자 = 가이드.\n\"매크로\" → c.macro()\n\"경기 사이클\" → c.macro(\"사이클\")\n\"위기 진단\" → c.macro(\"위기\")\n\"2008 시나리오\" → c.macro(\"시나리오\", \"2008 금융위기\")\nVerified:\nmacro(\"사이클\") → CLI + 사분면 + 금리 + 유동성 + 심리 6축 (observed via ai-ask, 2026-04-25 — 정식 Phase P 판정 아님)\nmacro + analysis → 경제 고려한 종목 분석 (observed via thesis ai-ask, 2026-04-25 — 정식 Phase P 판정 아님)",
        "kind": "method",
        "returns": "pl.DataFrame | dict\naxis=None: 가이드 DataFrame (axis/label/description/example/group).\naxis 지정: dict — 축별 매크로 분석 결과 (indicators, narrative 포함).",
        "summary": "시장 매크로 (6막 인과 — 사이클/재고/기업/정책/유동성/심리/시나리오). KR 자동 위임."
    },
    "Company.market": {
        "example": "c = Company(\"005930\")\nc.market  # \"KR\"",
        "kind": "property",
        "returns": "str — \"KR\".",
        "seeAlso": "currency: 통화 코드",
        "summary": "시장 코드 (DART 제공자는 항상 KR)."
    },
    "Company.narrativeDiff": {
        "guide": "\"가치 기여도\" → c.narrativeDiff()\n\"낮은WACC 기여 몇%\" → 결과 필터 claim='낮은WACC'",
        "kind": "method",
        "returns": "list[dict] — claim/dFV_neutral/delta_abs/delta_pct/contribution",
        "summary": "각 claim 제거 시 dFV 변화 — Thought Anchors 기반 정량 기여도."
    },
    "Company.network": {
        "aicontext": "그룹 계열사/출자 구조 파악 — 지배구조 분석의 기초 데이터\n순환출자 탐지로 거버넌스 리스크 감지",
        "args": "view: None이면 시각화(NetworkView), \"members\"/\"edges\"/\"cycles\"/\"peers\"이면 DataFrame.\nhops: peers/시각화 뷰에서 홉 수.",
        "capabilities": "그룹 계열사 목록 (members)\n출자/피출자 연결 + 지분율 (edges)\n순환출자 경로 탐지 (cycles)\nego 서브그래프 (peers)\n인터랙티브 네트워크 시각화 (브라우저)",
        "example": "c = Company(\"005930\")\nc.network()              # → NetworkView (.show()로 브라우저)\nc.network().show()       # 브라우저 오픈\nc.network(\"members\")     # 같은 그룹 계열사 DataFrame\nc.network(\"edges\")       # 출자/지분 연결 DataFrame\nc.network(\"cycles\")      # 순환출자 경로 DataFrame\nc.network(\"peers\")       # 이 회사 중심 서브그래프 DataFrame",
        "guide": "\"계열사 관계도\" → c.network() 또는 c.network().show()\n\"같은 그룹 계열사\" → c.network(\"members\")\n\"출자/지분 구조\" → c.network(\"edges\")\n\"순환출자 있어?\" → c.network(\"cycles\")",
        "kind": "method",
        "requires": "데이터: DART 대량보유/임원 공시 (자동 수집)",
        "returns": "NetworkView (view=None) 또는 DataFrame (view 지정 시). 데이터 없으면 None.",
        "seeAlso": "governance: 이사회/감사위원/최대주주 분석\ncapital: 주주환원 분석",
        "summary": "관계 네트워크 (지분출자 + 그룹 계열사 지도)."
    },
    "Company.news": {
        "aicontext": "최근 뉴스로 시장 반응, 이슈, 이벤트 파악\nask()/chat()에서 정성적 시장 맥락 보충",
        "args": "days: 최근 N일. 기본 30.",
        "capabilities": "Google News RSS 기반 뉴스 수집\n제목, 날짜, 소스, 링크\n기간 조절 가능",
        "example": "c.news()           # 최근 30일\nc.news(days=7)     # 최근 7일",
        "guide": "\"최근 뉴스 보여줘\" → c.news()\n\"이번 주 뉴스\" → c.news(days=7)",
        "kind": "method",
        "requires": "없음 (공개 RSS)",
        "returns": "pl.DataFrame — title, date, source, link.",
        "seeAlso": "liveFilings: 최신 공시 (뉴스가 아닌 공식 공시)\ngather: 뉴스 포함 4축 외부 데이터 수집",
        "summary": "최근 뉴스 수집."
    },
    "Company.priority": {
        "kind": "method",
        "returns": "int\nprovider 우선순위. DART 는 10 — EDGAR (20) 보다 먼저 시도.",
        "summary": "낮을수록 먼저 시도. DART=10 (기본 provider)."
    },
    "Company.quant": {
        "args": "axis: 축 이름. None이면 30축 가이드 DataFrame.\n(Phase 8 A1: 기존 `metric=` 은 호환 alias)\noverrides: 기술 분석 파라미터 교체. 키: window/threshold/period/benchmark.\n**kwargs: 축별 추가 파라미터.",
        "guide": "When: 주가 기반 기술적 판단이 필요할 때.\nHow: axis 로 분석 영역 지정. 무인자 = 가이드.\nVerified:\nquant(\"판단\") → RSI/ADX/MACD/볼린저/상대강도 + 종합 판정 (observed via ai-ask, 2026-04-25 — 정식 Phase P 판정 아님)",
        "kind": "property",
        "returns": "axis=None → DataFrame (30축 가이드)\naxis=\"종합\" → dict (verdict, RSI, ADX, SMA 등)\naxis=\"지표\" → DataFrame (45개 지표)",
        "summary": "주가 기술적 분석 — 30축 (내부 구현)."
    },
    "Company.rank": {
        "aicontext": "시장/섹터 내 상대 위치 파악 — 피어 비교 분석의 기초\nsizeClass로 대형/중형/소형주 분류",
        "capabilities": "전체 시장 내 매출/자산 순위\n섹터 내 상대 순위\n매출 성장률 기반 규모 분류 (large/mid/small)",
        "example": "from dartlab.analysis.financial.insight import buildSnapshot\nbuildSnapshot()\n\nc = Company(\"005930\")\nc.rank                    # RankInfo(삼성전자, 매출 2/2192, 섹터 2/467, large)\nc.rank.revenueRank        # 2\nc.rank.revenueRankInSector # 2\nc.rank.sizeClass          # \"large\"",
        "guide": "\"이 회사 순위는?\" → c.rank\n\"시장에서 몇 등이야?\" → c.rank.revenueRank\n\"대형주야?\" → c.rank.sizeClass",
        "kind": "property",
        "requires": "데이터: buildSnapshot() 사전 실행 필요",
        "returns": "RankInfo 또는 스냅샷 미빌드 시 None.",
        "seeAlso": "sector: 섹터 분류 (rank의 기준 그룹)\ninsights: 종합 등급 평가",
        "summary": "전체 시장 + 섹터 내 규모 순위 (매출/자산/성장률)."
    },
    "Company.rawDocs": {
        "aicontext": "원본 데이터 구조 파악 — 파싱 전 상태로 디버깅/검증에 활용",
        "capabilities": "HuggingFace docs 카테고리 원본 데이터 직접 접근\n가공/정규화 이전 상태 그대로 반환",
        "example": "c = Company(\"005930\")\nc.rawDocs              # 삼성전자 공시 문서 원본\nc.rawDocs.columns      # 컬럼 목록 확인",
        "guide": "\"원본 공시 데이터 보여줘\" → c.rawDocs\n\"가공 전 데이터 확인\" → c.rawDocs",
        "kind": "property",
        "requires": "데이터: HuggingFace docs parquet (자동 다운로드)",
        "returns": "pl.DataFrame | None -- 원본 docs parquet. 데이터 없으면 None.",
        "seeAlso": "sections: docs 가공 후 topic x period 통합 지도\nrawFinance: 재무제표 원본 데이터\nrawReport: 정기보고서 원본 데이터",
        "summary": "공시 문서 원본 parquet 전체 (가공 전)."
    },
    "Company.rawFinance": {
        "aicontext": "XBRL 정규화 전 원본 구조 파악 — 매핑 검증에 활용",
        "capabilities": "HuggingFace finance 카테고리 원본 데이터 직접 접근\nXBRL 정규화 이전 상태 그대로 반환",
        "example": "c = Company(\"005930\")\nc.rawFinance           # 삼성전자 재무제표 원본\nc.rawFinance.columns   # 컬럼 목록 확인",
        "guide": "\"원본 재무 데이터 보여줘\" → c.rawFinance\n\"XBRL 원본 확인\" → c.rawFinance",
        "kind": "property",
        "requires": "데이터: HuggingFace finance parquet (자동 다운로드)",
        "returns": "pl.DataFrame | None -- 원본 finance parquet. 데이터 없으면 None.",
        "seeAlso": "BS: 가공된 재무상태표\nIS: 가공된 손익계산서\nrawDocs: 공시 문서 원본",
        "summary": "재무제표 원본 parquet 전체 (가공 전)."
    },
    "Company.rawReport": {
        "aicontext": "정기보고서 API 원본 확인 — report topic 매핑 검증에 활용",
        "capabilities": "HuggingFace report 카테고리 원본 데이터 직접 접근\n정기보고서 API 데이터 가공 이전 상태 반환",
        "example": "c = Company(\"005930\")\nc.rawReport            # 삼성전자 정기보고서 원본\nc.rawReport.columns    # 컬럼 목록 확인",
        "guide": "\"원본 보고서 데이터 보여줘\" → c.rawReport\n\"정기보고서 원본 확인\" → c.rawReport",
        "kind": "property",
        "requires": "데이터: HuggingFace report parquet (자동 다운로드)",
        "returns": "pl.DataFrame | None -- 원본 report parquet. 데이터 없으면 None.",
        "seeAlso": "rawDocs: 공시 문서 원본\nrawFinance: 재무제표 원본\nshow: 가공된 topic 데이터 조회",
        "summary": "정기보고서 원본 parquet 전체 (가공 전)."
    },
    "Company.readFiling": {
        "aicontext": "공시 원문 텍스트를 LLM 컨텍스트에 주입하여 심층 분석 수행\nsections=True로 구조화하면 특정 섹션만 선택적 분석 가능",
        "args": "filing: 접수번호(str) 또는 disclosure()/liveFilings() row.\nmaxChars: 텍스트 최대 길이 (sections=False일 때만 적용).\nsections: True면 ZIP 기반 구조화된 섹션 목록 반환.",
        "capabilities": "접수번호(str) 직접 지정 또는 DataFrame row 자동 파싱\n전문 텍스트 또는 ZIP 기반 구조화 섹션 반환\n텍스트 길이 제한 (truncation) 지원",
        "example": "c = Company(\"005930\")\nresult = c.readFiling(\"20240315000123\")\nresult = c.readFiling(\"20240315000123\", sections=True)",
        "guide": "\"이 공시 내용 보여줘\" → c.readFiling(접수번호)\n\"공시 원문 분석해줘\" → c.readFiling()으로 원문 확보 후 ask()로 분석",
        "kind": "method",
        "requires": "API 키: DART_API_KEY",
        "returns": "dict -- rceptNo, viewerUrl, text/sections 등 원문 정보.",
        "seeAlso": "liveFilings: 최신 공시 목록에서 접수번호 확인\ndisclosure: 과거 공시 목록에서 접수번호 확인",
        "summary": "접수번호 또는 liveFilings row로 공시 원문을 읽는다."
    },
    "Company.resolve": {
        "args": "codeOrName: 종목코드 (\"005930\") 또는 종목명 (\"삼성전자\").",
        "kind": "method",
        "returns": "str | None — 6자리 종목코드. 못 찾으면 None.",
        "summary": "종목코드 또는 회사명 → 종목코드 변환."
    },
    "Company.retrievalBlocks": {
        "aicontext": "ask()/chat()에서 원문 기반 답변 생성 시 소스로 사용\nretrieval 기반 컨텍스트 주입의 원천 데이터",
        "capabilities": "docs 원문을 markdown 형태 그대로 보존한 검색용 블록\n각 블록은 topic/subtopic/period 단위로 분할\nRAG, 벡터 검색, 원문 참조에 최적화된 포맷",
        "example": "c = Company(\"005930\")\nc.retrievalBlocks          # 전체 retrieval 블록",
        "guide": "\"원문 검색용 블록\" → c.retrievalBlocks\n\"RAG용 데이터\" → c.retrievalBlocks",
        "kind": "property",
        "requires": "데이터: docs (자동 다운로드)",
        "returns": "pl.DataFrame | None -- 컬럼: topic, subtopic, period, content 등. docs 없으면 None.",
        "seeAlso": "contextSlices: retrievalBlocks를 LLM 윈도우에 맞게 슬라이싱한 결과\nsections: 구조화된 데이터 지도 (retrievalBlocks의 원본)",
        "summary": "원문 markdown 보존 retrieval block DataFrame."
    },
    "Company.search": {
        "args": "keyword: 검색어 (부분 일치).",
        "kind": "method",
        "returns": "pl.DataFrame — 매칭 종목 목록.",
        "summary": "회사명 부분 검색 (KIND 목록 기준)."
    },
    "Company.sections": {
        "aicontext": "전체 지도가 필요할 때만 사용. 개별 topic은 show(topic) 추천\n메모리 부하가 크므로 AI 코드에서 직접 접근 지양",
        "capabilities": "topic × period 수평화 통합 DataFrame\ndocs/finance/report 3-source 병합\nshow(topic)/trace(topic)/diff() 의 근간 데이터",
        "example": "c = Company(\"005930\")\nc.sections  # 전체 sections 지도",
        "guide": "\"이 회사 전체 데이터 지도\" → c.sections\n\"어떤 topic이 있어?\" → c.topics (경량)",
        "kind": "property",
        "requires": "데이터: docs (필수), finance/report (선택, 자동 다운로드)",
        "returns": "pl.DataFrame — chapter | topic | period | source | ... 또는 None.",
        "seeAlso": "topics: sections 기반 topic 요약 (더 간결)\nshow: 특정 topic 데이터 조회\nindex: 전체 구조 메타데이터 목차",
        "summary": "sections — docs + finance + report 통합 지도."
    },
    "Company.sector": {
        "aicontext": "섹터 분류 결과로 동종업계 비교, 섹터 파라미터 자동 선택\nanalysis/valuation에서 섹터별 벤치마크 기준으로 활용",
        "capabilities": "WICS 11대 섹터 + 하위 산업그룹 자동 분류\nKIND 업종명 + 주요제품 키워드 기반 매칭\noverride 테이블 우선 → 키워드 → 업종명 순 fallback",
        "example": "c = Company(\"005930\")\nc.sector              # SectorInfo(IT/반도체와반도체장비, conf=1.00, src=override)\nc.sector.sector       # Sector.IT\nc.sector.industryGroup  # IndustryGroup.SEMICONDUCTOR",
        "guide": "\"이 회사 어떤 섹터야?\" → c.sector\n\"업종 분류\" → c.sector",
        "kind": "property",
        "requires": "데이터: KIND 상장사 목록 (자동 로드)",
        "returns": "SectorInfo (sector, industryGroup, confidence, source).",
        "seeAlso": "sectorParams: 섹터별 밸류에이션 파라미터 (할인율, PER 등)\nrank: 섹터 내 규모 순위\ninsights: 섹터 기준 등급 평가",
        "summary": "WICS 투자 섹터 분류 (KIND 업종 + 키워드 기반)."
    },
    "Company.sectorParams": {
        "aicontext": "valuation()에서 DCF 할인율, 성장률 자동 적용\n섹터 특성 반영된 밸류에이션 파라미터",
        "capabilities": "섹터별 할인율, 성장률, PER 멀티플 제공\n섹터 분류 결과에 연동된 파라미터 자동 선택",
        "example": "c = Company(\"005930\")\nc.sectorParams.perMultiple   # 15\nc.sectorParams.discountRate  # 13.0",
        "guide": "\"이 섹터 할인율은?\" → c.sectorParams.discountRate\n\"PER 멀티플\" → c.sectorParams.perMultiple",
        "kind": "property",
        "requires": "데이터: sector 분류 결과 (자동 연산)",
        "returns": "SectorParams (discountRate, growthRate, perMultiple, ...).",
        "seeAlso": "sector: 섹터 분류 정보 (sectorParams의 기반)\nvaluation: 밸류에이션 (sectorParams를 내부적으로 소비)",
        "summary": "현재 종목의 섹터별 밸류에이션 파라미터."
    },
    "Company.select": {
        "args": "topic: IS, BS, CF, CIS, SCE 또는 docs topic.\nindList: 행 필터. 한글 항목/snakeId/항목명. 단일 str 도 가능.\ncolList: 열(기간) 필터. 단일 str 도 가능.\nfreq: 시계열 주기 — ``\"Q\"`` (분기, 기본) / ``\"Y\"`` (연간) / ``\"YTD\"`` (누적).\nscope: 재무제표 범위 — ``\"consolidated\"`` (연결, 기본) / ``\"separate\"`` (별도).",
        "example": "c.select(\"IS\", [\"매출액\", \"영업이익\"])\nc.select(\"IS\", [\"매출액\"], freq=\"Y\")              # 연간 매출\nc.select(\"BS\", [\"자본총계\"], scope=\"separate\")    # 별도 자본\nc.select(\"IS\", [\"매출액\"]).chart()",
        "kind": "property",
        "returns": "SelectResult\nshow()와 동일 컬럼 구조에서 indList/colList로 필터된 행/열.\n.chart() 체이닝으로 시각화 가능.\n내부 DataFrame 접근: result.df (pl.DataFrame).\nfinance topic 예시 (c.select(\"IS\", [\"매출액\"])):\nsnakeId : str — 계정 식별자\n항목 : str — 계정명\n2025Q4, 2025Q3, ... : float — 분기별 값 (원 단위)\n행 매칭 실패 시 ValueError.",
        "summary": "show() 결과에서 행(indList) + 열(colList) 필터 — 내부 구현."
    },
    "Company.show": {
        "aicontext": "120+ topic 단일 접근점 — LLM 이 데이터 조회 핵심 도구\nfinance topic 은 freq/scope 토글로 분기/연간/연결/별도 자유 전환",
        "args": "topic: topic 이름. ``\"BS\"`` ``\"IS\"`` ``\"CF\"`` ``\"CIS\"`` ``\"SCE\"`` ``\"ratios\"``\n같은 finance topic 또는 ``\"dividend\"`` ``\"companyOverview\"`` 같은 docs/report\ntopic. 전체 목록은 ``c.topics``.\nblock: 블록 인덱스. None 이면 블록 목차 (1개면 바로 데이터).\nperiod: 단일 기간 필터 (``\"2023\"``, ``\"2024Q2\"``) 또는 리스트 (세로 비교 뷰).\nfreq: 시계열 주기 — ``\"Q\"`` (분기, 기본) / ``\"Y\"`` (연간 strict 합) /\n``\"YTD\"`` (year-to-date 누적). pandas 관용 코드. **finance topic 한정**.\nscope: 재무제표 범위 — ``\"consolidated\"`` (연결, 기본) / ``\"separate\"`` (별도).\n**finance topic 한정**.\nraw: True 면 원본 그대로 (정제 없이).",
        "capabilities": "120+ topic 접근 (재무제표, 사업내용, 지배구조, 임원현황 등)\n기간 / 주기 / 범위 / 블록 / 세로뷰 모두 파라미터 토글\ndocs / finance / report 3 source 자동 통합",
        "example": "c = dartlab.Company(\"005930\")\nc.show(\"IS\")                              # 분기 연결 (기본)\nc.show(\"IS\", freq=\"Y\")                    # 연간 연결\nc.show(\"IS\", scope=\"separate\")            # 분기 별도\nc.show(\"IS\", freq=\"Y\", scope=\"separate\")  # 연간 별도\nc.show(\"IS\", period=\"2023\")               # 2023년 필터\nc.show(\"dividend\")                        # 배당",
        "guide": "\"분기 손익\" → ``c.show(\"IS\")``\n\"연간 손익\" → ``c.show(\"IS\", freq=\"Y\")``\n\"별도 재무상태표\" → ``c.show(\"BS\", scope=\"separate\")``\n\"2023년 손익\" → ``c.show(\"IS\", period=\"2023\")``\n\"배당 정보\" → ``c.show(\"dividend\")``",
        "kind": "property",
        "requires": "데이터: docs (자동 다운로드). finance topic 은 finance parquet 도 필요.",
        "returns": "pl.DataFrame | None\nfinance topic (IS/BS/CF/CIS/SCE):\nsnakeId : str — 계정 식별자 (영문 snake_case)\n항목 : str — 계정명 (한글)\n2025Q4, 2025Q3, ... : float — 분기별 값 (원 단위, freq=\"Q\" 기본)\n2025, 2024, ... : float — 연간 합산 값 (원 단위, freq=\"Y\")\nratios topic:\n항목 : str — 비율명\n2025Q4, 2025Q3, ... : float — 비율값 (%, 배)\nnotes topic (inventory, borrowings 등):\n항목 : str — 세부 항목명\n당기, 전기 또는 연도 컬럼 : float — 금액 (원 단위)\ndocs/report topic (dividend, employee 등):\ntopic별 컬럼 구조 — c.show(topic) 실행으로 확인\n블록 미지정 + 멀티블록 topic:\nblock : int — 블록 번호\ntitle : str — 블록 제목\n데이터 없으면 None.",
        "seeAlso": "select: show() 결과에서 행/열 필터 + 차트\ntrace: 데이터 출처 추적\ntopics: 사용 가능한 topic 전체 목록",
        "summary": "topic 의 데이터를 반환 — 내부 구현 (사용자는 ``c.show`` 호출)."
    },
    "Company.sources": {
        "aicontext": "데이터 가용성 사전 점검 — 분석 가능 범위 판단의 기초",
        "capabilities": "3개 데이터 source(docs, finance, report) 존재 여부/규모 한눈에 확인\n각 source의 row/col 수와 shape 문자열 제공\n데이터 로드 전 가용성 사전 점검",
        "example": "c = Company(\"005930\")\nc.sources                  # 3행 DataFrame",
        "guide": "\"데이터 뭐가 있어?\" → c.sources\n\"docs/finance/report 상태\" → c.sources",
        "kind": "property",
        "requires": "없음 (메타데이터만 조회, 데이터 파싱 불필요)",
        "returns": "pl.DataFrame -- 컬럼: source, available, rows, cols, shape",
        "seeAlso": "topics: topic 단위 상세 데이터 지도\ntrace: 특정 topic의 출처 추적",
        "summary": "docs/finance/report 3개 source의 가용 현황 요약."
    },
    "Company.status": {
        "capabilities": "로컬 데이터 현황 (종목별 docs/finance/report 보유 여부)\n최종 업데이트 일시",
        "kind": "method",
        "returns": "pl.DataFrame — 종목코드, 회사명, docs/finance/report 유무, 최종일시.",
        "summary": "로컬에 보유한 전체 종목 인덱스."
    },
    "Company.story": {
        "aicontext": "ask() (dartlab.ask) 가 이 결과를 tool 로 소비해 AI 해석 생성\nask()에서 재무분석 컨텍스트로 활용",
        "args": "section: 섹션명 (\"수익구조\" 등). None이면 전체.\nlayout: StoryLayout 커스텀. None이면 기본.\nhelper: True면 해석 힌트 텍스트 포함. None이면 자동.\npreset: 프리셋명 (\"executive\"/\"audit\"/\"credit\"/\"growth\"/\"valuation\"). None이면 전체.\ntemplate: 스토리 템플릿 (\"성장\"/\"자본집약\"/\"지주\" 등). \"auto\"면 자동 판별.\ndetail: True면 전체 블록, False면 섹션 요약만. None이면 preset 기본값 또는 True.",
        "capabilities": "14개 섹션 전체 보고서 (수익구조~재무정합성)\n단일 섹션 지정 가능\n4개 출력 형식 (rich, html, markdown, json)\n섹션간 순환 서사 자동 감지\n프리셋 지원 (executive/audit/credit/growth/valuation)\n스토리 템플릿 (사이클/프랜차이즈/턴어라운드/성장/자본집약/지주/현금부자)\ndetail=False로 요약만 표시\n레이아웃 커스텀",
        "example": "c.story()                        # 전체 검토서\nc.story(\"수익구조\")                # 특정 섹션\nc.story(preset=\"audit\")          # 감사/회계 검토용\nc.story(template=\"auto\")         # 스토리 자동 판별\nc.story(template=\"성장\")          # 성장 템플릿 적용\nc.story(detail=False)            # 전 섹션 요약만",
        "guide": "When: 구조화된 보고서가 필요할 때. 사용자가 \"보고서\" 명시 시에만.\nHow: 무인자 = 전체 보고서. section 으로 개별 섹션. type 으로 보고서 타입.\n\"재무 검토서 만들어줘\" -> c.story()\n\"수익구조 분석\" -> c.story(\"수익구조\")\n\"감사용 리뷰\" -> c.story(preset=\"audit\")\n\"이 회사 스토리는?\" -> c.story(template=\"auto\")\n\"요약만 보여줘\" -> c.story(detail=False)\n\"AI 가 해석한 보고서\" -> dartlab.ask(\"005930 보고서 작성해줘\") (AI 가 story tool 호출)\nVerified:\ncredit 타입 → 신용 종합 보고서 (observed via credit ai-ask, 2026-04-25 — 정식 Phase P 판정 아님)\naudit 타입 → 분식회계 가능성 판정 보고서 (observed via ai-ask, 2026-04-25 — 정식 Phase P 판정 아님)\ngovernance 타입 → 지배구조 점검 보고서 (observed via ai-ask, 2026-04-25 — 정식 Phase P 판정 아님)\ndividend 타입 → 배당 매력 종합 보고서 (observed via ai-ask, 2026-04-25 — 정식 Phase P 판정 아님)",
        "kind": "property",
        "requires": "데이터: finance + report (자동 다운로드)",
        "returns": "Story — 구조화 보고서.",
        "seeAlso": "dartlab.ask: AI 자율 분석 (분석 질문은 여기로)\nanalysis: 14축 개별 분석 (story가 내부적으로 소비)\ninsights: 7영역 등급 + 이상치 요약",
        "summary": "재무제표 구조화 보고서 — 기업이야기꾼의 대본 (내부 구현)."
    },
    "Company.storyTree": {
        "guide": "\"3 시나리오 가치\" → c.storyTree()\n\"서사 민감도\" → c.storyTree()['summary']['spreadPct']",
        "kind": "method",
        "returns": "dict — possible/plausible/probable + summary {min/max/spread/spreadPct/mean}",
        "summary": "Damodaran 3P — possible(낙관)/plausible(중도)/probable(보수) 3 DCF + 민감도."
    },
    "Company.table": {
        "aicontext": "docs 원문 테이블을 구조화하여 정량 분석에 활용\nnumeric=True로 금액 문자열을 수치화하면 계산 가능",
        "args": "topic: docs topic 이름\nsubtopic: 파싱할 subtopic 이름 (None이면 첫 번째 subtopic)\nnumeric: True이면 금액 문자열을 float로 변환\nperiod: 기간 필터 (예: \"2024\")",
        "capabilities": "docs 원문의 markdown table을 Polars DataFrame으로 변환\nsubtopic 지정으로 특정 표만 추출\nnumeric 모드로 금액 문자열을 float 변환\nperiod 필터로 특정 기간 컬럼만 선택",
        "example": "c.table(\"employee\")                    # 첫 번째 subtopic\nc.table(\"employee\", \"직원현황\")         # 특정 subtopic\nc.table(\"employee\", numeric=True)       # 숫자 변환",
        "guide": "\"직원 현황 테이블\" → c.table(\"employee\")\n\"표 데이터를 숫자로\" → c.table(topic, numeric=True)",
        "kind": "method",
        "requires": "데이터: docs (자동 다운로드)",
        "returns": "ParsedSubtopicTable (df, subtopic, columns) 또는 파싱 불가 시 None",
        "seeAlso": "show: topic 전체 데이터 (table은 subtopic 단위 파싱)\nselect: show() 결과에서 행/열 필터",
        "summary": "subtopic wide 셀의 markdown table을 구조화 DataFrame으로 파싱."
    },
    "Company.topicSummaries": {
        "kind": "method",
        "returns": "dict[str, str]\n키 = topic 이름 (예: \"BS\", \"IS\", \"dividend\", \"companyOverview\")\n값 = 200자 요약 텍스트",
        "summary": "토픽별 요약 dict — AI가 경로 탐색에 사용."
    },
    "Company.topics": {
        "aicontext": "LLM이 가용 topic 목록을 파악하는 데 사용\n분석 범위 결정 시 참조",
        "capabilities": "docs/finance/report 모든 source의 topic을 하나의 DataFrame으로 통합\nchapter 순서대로 정렬, 각 topic의 블록 수/기간 수/최신 기간 표시\n어떤 데이터가 있는지 한눈에 파악",
        "example": "c = Company(\"005930\")\nc.topics                   # 전체 topic 요약\nc.topics.filter(pl.col(\"source\") == \"finance\")  # finance만",
        "guide": "\"어떤 데이터가 있어?\" → c.topics\n\"topic 목록\" → c.topics",
        "kind": "property",
        "requires": "데이터: docs/finance/report 중 하나 이상 (자동 다운로드)",
        "returns": "pl.DataFrame -- 컬럼: order, chapter, topic, source, blocks, periods, latestPeriod",
        "seeAlso": "show: 특정 topic 데이터 조회\nsections: topic x period 전체 지도 (topics보다 상세)\nindex: 전체 구조 메타데이터 목차",
        "summary": "topic별 요약 DataFrame -- 전체 데이터 지도."
    },
    "Company.trace": {
        "aicontext": "데이터 출처 신뢰도 판단 — finance > report > docs 우선순위 확인\n분석 결과의 근거 투명성 확보",
        "args": "topic: topic 이름.\nperiod: 특정 기간. None이면 전체.",
        "capabilities": "topic별 데이터 출처 확인 (docs, finance, report)\n출처 선택 이유 (우선순위, fallback 경로)\n각 출처별 데이터 행 수, 기간 수, 커버리지",
        "example": "c.trace(\"BS\")           # 재무상태표 출처\nc.trace(\"dividend\")     # 배당 데이터 출처",
        "guide": "\"이 데이터 어디서 온 거야?\" → c.trace(\"BS\")\n\"데이터 출처 확인\" → c.trace(topic)",
        "kind": "method",
        "requires": "데이터: docs + finance + report (보유한 것만 추적)",
        "returns": "dict — primarySource, fallbackSources, whySelected, availableSources 등.",
        "seeAlso": "show: topic 데이터 조회 (trace로 출처 확인 후 열람)\nsources: 3개 source 전체 가용 현황",
        "summary": "topic 데이터의 출처(docs/finance/report)와 선택 근거 추적."
    },
    "Company.update": {
        "aicontext": "데이터 최신성 유지에 활용 — 분석 전 자동 갱신 트리거 가능",
        "args": "categories: [\"finance\", \"docs\", \"report\"]. None이면 전체.",
        "capabilities": "DART API로 최신 공시 확인 후 누락분만 수집\n카테고리별 선택 수집",
        "guide": "\"최신 공시 반영해줘\" → c.update()\n\"데이터 업데이트\" → c.update()로 증분 수집",
        "kind": "method",
        "requires": "API 키: DART_API_KEY",
        "returns": "dict — {카테고리: 수집 건수}.",
        "seeAlso": "filings: 현재 보유 공시 목록 확인\ndisclosure: OpenDART 전체 공시 조회",
        "summary": "누락된 최신 공시를 증분 수집."
    },
    "Company.validateStory": {
        "args": "overrides: 검증 기준 조율 (VALUATION_KEYS).",
        "capabilities": "calcStoryPrecedents (scan peer + KnowledgeDB insights)\ncalcPlausibilityBand (섹터 피어 분포 percentile)\ncalcValuationSins (정합성 규칙 위반)\noverrides 로 AI 개입 (lifeCyclePhase, terminalGrowth 등)",
        "example": "c = Company(\"005930\")\nr = c.validateStory()\nfor f in r[\"rules\"][\"flags\"]:\nprint(f['severity'], f['reason'])",
        "kind": "method",
        "returns": "dict\nprecedents : dict — Possible Test 결과\nplausibility : dict — Plausible Test 결과\nrules : dict — Probable Test 결과\noverall : str — \"info\" | \"warn\" | \"critical\"",
        "summary": "Damodaran 스토리 검증 — Possible / Plausible / Probable 3 테스트 통합."
    },
    "Company.valuationImpact": {
        "guide": "\"WACC 조정 어떻게\" → c.valuationImpact()['waccAdj']\n\"override 근거\" → c.valuationImpact()['narrative']",
        "kind": "method",
        "returns": "dict — terminalGrowthAdj/waccAdj/narrative/overrides",
        "summary": "인과 체인에서 DCF override 힌트 — narrative → 숫자 피드백."
    },
    "Company.view": {
        "aicontext": "시각적 탐색 인터페이스 — 사용자가 브라우저에서 직접 데이터 탐색",
        "args": "port: 로컬 서버 포트. 기본 8400.",
        "capabilities": "로컬 서버 기반 공시 뷰어 실행\n브라우저에서 sections/index 탐색",
        "example": "c = Company(\"005930\")\nc.view()",
        "guide": "\"공시 뷰어 열어줘\" → c.view()\n\"브라우저에서 보기\" → c.view()",
        "kind": "method",
        "requires": "데이터: HuggingFace docs parquet (자동 다운로드)",
        "returns": "None",
        "seeAlso": "index: 뷰어가 소비하는 메타데이터 (프로그래밍 접근)\nsections: 뷰어의 원본 데이터",
        "summary": "브라우저에서 공시 뷰어를 엽니다."
    },
    "Company.watch": {
        "aicontext": "공시 변화 중요도 자동 평가 — 분석 우선순위 결정에 활용\n텍스트 변화량 + 재무 영향 통합 스코어",
        "args": "topic: topic 이름. None이면 전체 중요도 순 요약.",
        "capabilities": "전체 topic 변화 중요도 스코어링\n텍스트 변화량 + 재무 영향 통합 평가\n특정 topic 상세 변화 내역",
        "example": "c.watch()                    # 전체 중요도 순\nc.watch(\"riskManagement\")    # 특정 topic",
        "guide": "\"뭐가 크게 바뀌었어?\" → c.watch()\n\"리스크 관련 변화\" → c.watch(\"riskManagement\")",
        "kind": "method",
        "requires": "데이터: docs (자동 다운로드)",
        "returns": "pl.DataFrame | None — topic, score, changeType, details 등.",
        "seeAlso": "diff: 줄 단위 상세 변경 비교 (watch보다 세밀)\nkeywordTrend: 키워드 빈도 추이",
        "summary": "공시 변화 감지 — 중요도 스코어링 기반 변화 요약."
    },
    "Company.workforce": {
        "aicontext": "인력 효율성/근무환경 정량 평가 — 1인당 매출, 급여 수준 비교\n시장 횡단 비교로 인적자원 경쟁력 판단",
        "args": "view: None → 이 회사 행, \"all\" → 전체, \"market\" → 시장별 요약.",
        "capabilities": "직원수 + 정규직/비정규직 비율\n평균 급여 + 1인당 매출\n평균 근속연수\n시장 전체 인력 횡단 비교",
        "example": "c = Company(\"005930\")\nc.workforce()            # 삼성전자 인력 현황\nc.workforce(\"all\")       # 전체 상장사",
        "guide": "\"직원 현황\" → c.workforce()\n\"평균 급여는?\" → c.workforce()\n\"전체 상장사 인력 비교\" → c.workforce(\"all\")",
        "kind": "method",
        "requires": "데이터: DART 정기보고서 (자동 수집)",
        "returns": "DataFrame 또는 데이터 없으면 None.",
        "seeAlso": "governance: 이사회/감사위원 구성 (인력의 다른 관점)\nshow: c.show(\"employee\")로 docs 기반 직원 상세",
        "summary": "인력/급여 분석 (직원수, 평균급여, 근속연수)."
    },
    "Fred": {
        "args": "api_key: FRED API 키. None이면 ``FRED_API_KEY`` 환경변수 사용.",
        "example": "f = Fred()\ngdp = f.series(\"GDP\")\nf.compare([\"GDP\", \"UNRATE\"], start=\"2020-01-01\")\nf.correlation([\"GDP\", \"UNRATE\", \"FEDFUNDS\"])",
        "kind": "class",
        "summary": "FRED 경제지표 facade."
    },
    "OpenDart": {
        "kind": "class",
        "summary": "OpenDART API 통합 클라이언트."
    },
    "OpenEdgar": {
        "kind": "class",
        "summary": "SEC public API facade."
    },
    "SelectResult": {
        "kind": "class",
        "summary": "select() 반환 객체 — DataFrame 위임 + 체이닝."
    },
    "Story": {
        "guide": "When: 종목의 종합 분석 보고서가 필요할 때.\nHow: 11 타입 중 선택 — full(전체), executive(경영진 요약), credit(신용),\nvaluation(가치평가), growth(성장), crisis(위기), audit(감사),\ndividend(배당), governance(지배구조), macro(매크로), thesis(투자논제).\nVerified:\ncredit 타입 → credit + analysis(안정성,현금흐름,자금조달) 조합 (observed via ai-ask, 2026-04-25 — 정식 Phase P 판정 아님)\naudit 타입 → analysis(이익품질,재무정합성) + 감사의견 (observed via ai-ask, 2026-04-25 — 정식 Phase P 판정 아님)\ngovernance 타입 → analysis(지배구조,공시변화) (observed via ai-ask, 2026-04-25 — 정식 Phase P 판정 아님)\ndividend 타입 → analysis(수익구조,현금흐름,자본배분) (observed via ai-ask, 2026-04-25 — 정식 Phase P 판정 아님)\nvaluation 타입 → analysis(가치평가) + quant (observed via ai-ask, 2026-04-25 — 정식 Phase P 판정 아님)\nthesis 타입 → macro + analysis 복합 근거 수집 (observed via ai-ask, 2026-04-25 — 정식 Phase P 판정 아님)\n\nSee Also\nanalysis : 재무 심층 분석 — story 의 주요 데이터 공급원.\ncredit : 신용 분석 — story credit 타입의 핵심 엔진.\nscan : 전종목 비교 — 동종업계 비교 블록 제공.\nquant : 기술적 분석 — 가격 기반 신호 블록 제공.\nmacro : 거시 분석 — 매크로 환경 블록 제공.",
        "kind": "class",
        "returns": "Story\n보고서 인스턴스. 주요 속성/메서드:\nsections : list[Section] — 6막별 섹션 목록\nrender(fmt) : str — 렌더링 (\"rich\"/\"html\"/\"markdown\"/\"json\")\ntoHtml() : str — HTML 출력\ntoMarkdown() : str — Markdown 출력\nsummaryCard : SummaryCard — 최상단 요약 카드\n\nRaises\nValueError\n보고서 타입이 등록되지 않은 경우.\nRuntimeError\nCompany 데이터 로드 실패 시.\n\nExamples\n>>> c.story()                              # 전체 보고서\n>>> c.story(\"수익구조\")                     # 수익구조 섹션만\n>>> c.story(reportType=\"credit\")           # 신용분석 보고서\n>>> from dartlab.story import blocks, Story\n>>> b = blocks(c)\n>>> Story([b[\"growth\"], b[\"margin\"]])       # 자유 조립\n\nNotes\n사람의 진입점은 c.story() (Company 메서드). AI 는 dartlab.ask() 경유.\n4 출력 형식: rich(터미널), html, markdown, json.\nJupyter/Colab/Marimo 에서 _repr_html_ 자동 렌더링.",
        "summary": "보고서 조합기 — 6 엔진 블록을 조합하여 6막 구조화 보고서 생성."
    },
    "aiContract.capabilities.valid_key": {
        "contractId": "capabilities.valid_key",
        "kind": "ai_contract",
        "priority": 70,
        "questionTypes": [
            "meta_help"
        ],
        "requiredEvidence": [
            "valid_key_or_search"
        ],
        "summary": "capabilities key 오염 방지 계약",
        "tool": "capabilities",
        "toolArgPolicy": [
            "reject_polluted_capabilities_key"
        ]
    },
    "aiContract.cashflow.primary": {
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
        "questionTypes": [
            "cashflow"
        ],
        "requiredEvidence": [
            "target",
            "metric",
            "period",
            "value"
        ],
        "summary": "현금흐름 질문 primary evidence 계약",
        "visualPolicy": {
            "preferredType": "chart",
            "requiredFor": [
                "cashflow"
            ]
        }
    },
    "aiContract.comparison.same_axis": {
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
        "questionTypes": [
            "company_compare"
        ],
        "requiredEvidence": [
            "target",
            "metric",
            "period",
            "value"
        ],
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
        "visualPolicy": {
            "preferredType": "chart_or_diagram",
            "requiredFor": [
                "company_compare"
            ]
        }
    },
    "aiContract.disclosure.importance": {
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
        "questionTypes": [
            "disclosure_importance"
        ],
        "requiredEvidence": [
            "filedAt",
            "title",
            "formType",
            "basis"
        ],
        "summary": "공시 중요도 분석 근거 깊이 계약",
        "tool": "disclosure",
        "toolArgPolicy": [
            "title_only_scope_must_not_be_presented_as_body_analysis",
            "sections_false",
            "max_chars_4000"
        ],
        "visualPolicy": {
            "preferredType": "diagram",
            "requiredFor": [
                "disclosure_importance"
            ]
        }
    },
    "analysis": {
        "kind": "module",
        "summary": "Analysis 엔진 — L2 분석 모듈 통합."
    },
    "ask": {
        "args": "question: 자연어 질문.\nstockCode: UI/서버가 현재 화면 종목코드를 힌트로 전달 (선택).\nprovider: LLM provider.\nstream: True 면 실시간 스트리밍 출력 (기본). False 면 조용히 전체 텍스트 반환.\nraw: True 면 Generator 를 직접 반환 (커스텀 UI 용).",
        "capabilities": "자연어로 기업/시장 분석 (종목은 질문 텍스트에서 AI 가 자동 감지)\n스트리밍 출력 (기본) / 배치 반환 / Generator 직접 제어\n원본 검증 · 가정 조정 · 업종 비교 전부 AI 자율",
        "example": "import dartlab\ndartlab.ask(\"삼성전자 수익성 분석해줘\")\ndartlab.ask(\"삼성전자 분석\", stream=False)  # 조용히 전체 텍스트",
        "guide": "\"삼성전자 수익성 분석\" -> dartlab.ask(\"삼성전자 수익성 분석해줘\")\n\"삼성 vs SK하이닉스\" -> dartlab.ask(\"삼성전자와 SK하이닉스 비교\")\n\"반도체 업황\" -> dartlab.ask(\"반도체 업황 어때\")  (종목 불필요)",
        "kind": "function",
        "requires": "AI: provider 설정 (dartlab.setup() 참조)",
        "returns": "str | None: 전체 답변 텍스트. 설정 오류 시 None. (raw=True 일 때만 Generator[str])",
        "seeAlso": "Company: 원본 데이터 조회 (show/select)\nscan: 전종목 비교 (프로그래밍)",
        "summary": "AI 에게 질문. AI 가 모든 엔진(analysis/scan/macro/credit/gather/search)을 tool 로 다룬다."
    },
    "capabilities": {
        "aicontext": "AI가 \"dartlab에 뭐가 있는지\" 모를 때 탐색용.\ncapabilities() → 목차 확인 → capabilities(\"analysis\") → 상세 확인 → execute_code.\ncapabilities(search=\"재무건전성\") → 질문 관련 API 검색 → 코드 생성.",
        "args": "key: 조회할 기능 키. None이면 전체 목차.\nsearch: 자연어 질문 기반 검색. key와 동시 사용 불가.",
        "capabilities": "CAPABILITIES dict에서 부분 조회 가능.\nkey 없이 호출 시 전체 키 목록(summary 포함) 반환.\nkey 지정 시 해당 항목의 상세(guide, capabilities, seeAlso 등) 반환.\nsearch 지정 시 자연어 질문 기반 관련 API 검색 (상위 10개).",
        "example": "dartlab.capabilities()                       # 전체 목차\ndartlab.capabilities(\"analysis\")             # analysis 상세 (guide, capabilities)\ndartlab.capabilities(\"Company.analysis\")     # Company.analysis 상세\ndartlab.capabilities(\"scan\")                 # scan 상세\ndartlab.capabilities(search=\"재무건전성\")     # 질문 기반 검색 → 상위 10개",
        "guide": "\"dartlab 뭐 할 수 있어?\" -> capabilities()\n\"분석 기능 뭐 있어?\" -> capabilities(\"analysis\")\n\"scan 어떻게 써?\" -> capabilities(\"scan\")\n\"재무건전성 관련 API?\" -> capabilities(search=\"재무건전성\")",
        "kind": "function",
        "requires": "없음",
        "returns": "dict | list[str] — key 있으면 해당 항목 dict, 없으면 키+summary 목록.",
        "seeAlso": "ask: AI 질문 (capabilities로 기능 파악 후 ask로 분석)\nsetup: AI provider 설정 (capabilities 확인 후 설정)",
        "summary": "dartlab 전체 기능 카탈로그 조회."
    },
    "codeToName": {
        "kind": "function",
        "returns": "str | None\n회사명. 못 찾으면 None.",
        "summary": "종목코드 → 회사명."
    },
    "collect": {
        "aicontext": "사용자가 특정 종목의 최신 데이터를 직접 수집할 때 사용.",
        "args": "*codes: 종목코드 1개 이상 (\"005930\", \"000660\").\ncategories: 수집 카테고리 [\"finance\", \"docs\", \"report\"]. None이면 전체.\nincremental: True면 증분 수집 (기본). False면 전체 재수집.",
        "capabilities": "종목별 DART 공시 데이터 직접 수집 (finance, docs, report)\n멀티키 병렬 수집 (DART_API_KEYS 쉼표 구분)\n증분 수집 — 이미 있는 데이터는 건너뜀\n카테고리별 선택 수집",
        "example": "import dartlab\ndartlab.collect(\"005930\")                              # 삼성전자 전체\ndartlab.collect(\"005930\", \"000660\", categories=[\"finance\"])  # 재무만",
        "guide": "\"데이터 수집해줘\" -> DART_API_KEY 필요. dartlab.setup(\"dart-key\", \"YOUR_KEY\")로 설정 안내\n\"삼성전자 재무 데이터 수집\" -> collect(\"005930\", categories=[\"finance\"])\n보안: 키는 로컬 .env에만 저장, 외부 전송 절대 없음",
        "kind": "function",
        "requires": "API 키: DART_API_KEY",
        "returns": "dict — 종목코드별 카테고리별 수집 건수.",
        "seeAlso": "Company: 수집된 데이터로 Company 생성하여 분석\nsearch: 종목코드 모를 때 먼저 검색",
        "summary": "지정 종목 DART 데이터 수집 (OpenAPI)."
    },
    "collectAll": {
        "args": "categories: 수집 카테고리 [\"finance\", \"docs\", \"report\"]. None이면 전체.\nmode: \"new\" (미수집만, 기본) 또는 \"all\" (전체 재수집).\nmaxWorkers: 병렬 워커 수. None이면 키 수에 따라 자동.\nincremental: True면 증분 수집. False면 전체 재수집.",
        "capabilities": "전체 상장종목 DART 공시 데이터 일괄 수집\n미수집 종목만 선별 수집 (mode=\"new\") 또는 전체 재수집 (mode=\"all\")\n멀티키 병렬 수집 (DART_API_KEYS 쉼표 구분)\n카테고리별 선택 (finance, docs, report)",
        "example": "import dartlab\ndartlab.collectAll()                          # 전체 미수집 종목\ndartlab.collectAll(categories=[\"finance\"])    # 재무만\ndartlab.collectAll(mode=\"all\")                # 기수집 포함 전체",
        "guide": "\"전종목 데이터 수집\" -> collectAll() 안내. DART_API_KEY 필요\n\"재무 데이터만 수집\" -> collectAll(categories=[\"finance\"])\n보안: 키는 로컬 .env에만 저장, 외부 전송 절대 없음",
        "kind": "function",
        "requires": "API 키: DART_API_KEY",
        "returns": "dict — 종목코드별 카테고리별 수집 건수.",
        "seeAlso": "collect: 특정 종목만 수집\ndownloadAll: HuggingFace 사전구축 데이터 (API 키 불필요, 더 빠름)",
        "summary": "전체 상장종목 DART 데이터 일괄 수집."
    },
    "config": {
        "kind": "module",
        "summary": "dartlab 전역 설정."
    },
    "credit": {
        "guide": "When: 종목의 부도 위험·재무 건전성을 독립 평가할 때.\nHow: credit 단독으로 종합 등급 확인 → analysis(안정성, 현금흐름) 와 함께 심층 진단.\nstory credit 타입이 credit + analysis(안정성) + analysis(현금흐름) + analysis(자금조달) 순서로 조합.\nVerified:\ncredit 단독 → dCR 등급 + 7축 위험점수 + PD 추정 (observed via ai-ask, 2026-04-25 — 정식 Phase P 판정 아님)\ncredit + analysis(안정성,현금흐름) → 부도 위험 종합 진단 (observed via ai-ask, 2026-04-25 — 정식 Phase P 판정 아님)\n\nSee Also\nanalysis : 재무 심층 분석 — 안정성·현금흐름 축이 credit 과 상호 보완.\nscan : 전종목 재무건전성 비교.",
        "kind": "function",
        "returns": "DataFrame | dict | None\nstockCode=None → 가이드 DataFrame (axis, label, description, example, group)\naxis=\"등급\" 또는 None+stockCode → 종합 등급 dict\n\ngrade : str — dCR 등급 (예: \"dCR-AA+\")\nscore : float — 위험 점수 (0=최우량, 100=최위험) (점)\nhealthScore : float — 건전성 점수 (100-score) (점)\naxes : list[dict] — 7축 상세 (name, score, weight, metrics)\neCR : str | None — 현금흐름등급\noutlook : str — 전망 (\"안정적\"/\"긍정적\"/\"부정적\")\n\naxis=축이름 → 해당 축 dict\n\naxis : str — 축 풀네임\nscore : float — 해당 축 위험 점수 (점)\nweight : int — 가중치 (%)\nmetrics : list[dict] — 개별 지표 (name, value, score)\n\nExamples\n>>> import dartlab\n>>> dartlab.credit(\"005930\")                # 삼성전자 종합\n>>> dartlab.credit(\"005930\", \"채무상환\")     # 채무상환 축만\n>>> dartlab.credit()                        # 가이드 DataFrame\n\nRaises\nValueError\n축 이름이 등록되지 않은 경우.\n\nNotes\n3-Track 모델(일반/금융/지주) + Notch Adjustment + CHS 시장 보정.\n79개사 검증: 대기업 87%, 중대형 82%. DART 공시 기반, API 키 불필요.",
        "summary": "신용등급 산출 단일 진입점."
    },
    "dataDir": {
        "kind": "module",
        "summary": "str(object='') -> str"
    },
    "downloadAll": {
        "args": "category: \"finance\" (재무 ~600MB), \"docs\" (공시 ~8GB), \"report\" (보고서 ~320MB).\nforceUpdate: True면 이미 있는 파일도 최신으로 갱신.",
        "capabilities": "HuggingFace 사전 구축 데이터 일괄 다운로드\nfinance (~600MB), docs (~8GB), report (~320MB) — 전 상장사 범위\n이어받기/병렬 다운로드 지원 (huggingface_hub)\n전사 분석(scanAccount, governance, digest 등)에 필요한 데이터 사전 준비",
        "example": "import dartlab\ndartlab.downloadAll(\"finance\")   # 재무 전체 — scanAccount/scanRatio 등에 필요\ndartlab.downloadAll(\"report\")    # 보고서 전체 — governance/workforce/capital/debt에 필요\ndartlab.downloadAll(\"docs\")      # 공시 전체 — digest에 필요 (대용량 ~8GB)",
        "guide": "\"데이터 어떻게 받아?\" -> downloadAll(\"finance\") 안내. API 키 불필요\n\"scan 쓰려면?\" -> downloadAll(\"finance\") + downloadAll(\"report\") 필요\nfinance 먼저 (600MB), report 다음 (320MB), docs는 대용량 주의 (8GB)",
        "kind": "function",
        "requires": "없음 (HuggingFace 공개 데이터셋)",
        "returns": "None.",
        "seeAlso": "scan: 다운로드된 데이터로 전종목 비교\ncollect: DART API로 직접 수집 (최신 데이터, API 키 필요)",
        "summary": "HuggingFace에서 전체 시장 데이터 다운로드."
    },
    "gather": {
        "guide": "When: 분석 엔진에 필요한 외부 데이터를 수집할 때.\nHow: gather → analysis/quant 파이프라인. gather(\"price\") 는 quant 의 데이터 원천.\ngather(\"macro\") 는 macro 엔진과 상호 보완 (raw 데이터 vs 분석 결과).\nVerified:\ngather(\"news\") → 뉴스 목록 + 헤드라인 해석 (observed via ai-ask, 2026-04-25 — 정식 Phase P 판정 아님)\n\nSee Also\nquant : 주가 기반 정량 분석 — gather(\"price\") 데이터 소비.\nmacro : 거시 분석 — gather(\"macro\") raw 데이터의 분석 결과.\nscan : 전종목 비교 — 사전 빌드 데이터와 gather 실시간 데이터 상호 보완.",
        "kind": "function",
        "returns": "pl.DataFrame\naxis=None (가이드):\naxis : str — 축 이름\nlabel : str — 한글 레이블\ndescription : str — 설명\nexample : str — 사용 예시\naxis=\"price\":\ndate : date — 날짜\nopen : float — 시가\nhigh : float — 고가\nlow : float — 저가\nclose : float — 종가\nvolume : int — 거래량\naxis=\"flow\":\ndate : date — 날짜\n외국인순매수 : int — 외국인 순매수량\n기관순매수 : int — 기관 순매수량\naxis=\"macro\":\ndate : date — 날짜\n지표별 컬럼 : float — ECOS/FRED 거시지표 값\naxis=\"news\":\ntitle : str — 뉴스 제목\nlink : str — 기사 URL\npubDate : str — 발행일\naxis=\"sector\":\nsectorCode : str — 업종코드\nsectorName : str — 업종명\nindustryCode : str — 산업코드\nindustryName : str — 산업명\nmarket : str — 시장 (KR/US)\naxis=\"insider\":\ndate : str — 거래일\nname : str — 거래자명\nposition : str — 직위\ntradeType : str — 거래유형\nchangeShares : int — 변동 주수\n\nRaises\nValueError\n축 이름이 등록되지 않은 경우.\ntarget 필수 축에서 target 누락 시.\n\nExamples\n>>> dartlab.gather()                              # 가이드\n>>> dartlab.gather(\"price\", \"005930\")              # KR OHLCV\n>>> dartlab.gather(\"price\", \"AAPL\", market=\"US\")   # US 주가\n>>> dartlab.gather(\"macro\", \"FEDFUNDS\")            # 미국 기준금리\n>>> dartlab.gather(\"news\", \"삼성전자\")              # Google News\n\nNotes\nNaver(KR)/Yahoo(US)/FRED/ECOS/Google News 경유. API 키 불필요.\n결과는 Polars DataFrame — 분석 엔진 입력으로 바로 사용 가능.",
        "summary": "외부 시장 데이터 수집 — 주가·수급·거시지표·뉴스 4 축."
    },
    "gather.flow": {
        "capabilities": "외국인/기관 순매수 동향 (KR 전용, 네이버 금융). US는 미지원 → None",
        "kind": "gather_axis",
        "summary": "수급"
    },
    "gather.insider": {
        "capabilities": "임원/주요주주 주식 거래 내역. KR: DART API (API 키: DART_API_KEY)",
        "kind": "gather_axis",
        "summary": "내부자거래"
    },
    "gather.krx": {
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
        "questionTypes": [
            "recent_price_mover"
        ],
        "requiredEvidence": [
            "asOf",
            "period",
            "universe",
            "metric"
        ],
        "summary": "KRX 회사별 시계열",
        "tool": "gather",
        "toolArgPolicy": [
            "start_lte_end",
            "end_not_future",
            "target_close_for_price_returns"
        ],
        "visualPolicy": {
            "preferredType": "chart",
            "requiredFor": [
                "recent_price_mover"
            ]
        }
    },
    "gather.krxIndex": {
        "capabilities": "KRX/KOSPI/KOSDAQ 시장군의 모든 지수 (종합/200/100/섹터/스타일/사이즈/ESG/테마) OHLCV + 거래량 + 시가총액. target=close/open/high/low/volume/marketCap/raw. indexFilter=[지수명] 으로 특정 지수 (예: KOSPI200 + 보조지표 자동). apiKey 명시 필수 — idx 카테고리 권한 별도 신청 (sto 종목 키와 분리).",
        "kind": "gather_axis",
        "summary": "KRX 지수 일별 매매현황 (시장군별 전체 지수 패키지)"
    },
    "gather.macro": {
        "capabilities": "KR: ECOS 한국은행, US: FRED 거시지표. 기본은 HF 벌크 데이터셋이라 API 키 불필요. apiKey 명시 시 직접 API 호출. 지표 미지정 시 전체 반환.",
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
        "questionTypes": [
            "macro_recent"
        ],
        "requiredEvidence": [
            "asOf",
            "metric",
            "value"
        ],
        "summary": "거시지표",
        "tool": "gather",
        "visualPolicy": {
            "preferredType": "chart",
            "requiredFor": [
                "macro_recent"
            ]
        }
    },
    "gather.news": {
        "capabilities": "Google News RSS 최근 30일. API 키 불필요. 한글/영문 검색어 모두 지원",
        "kind": "gather_axis",
        "summary": "뉴스"
    },
    "gather.ownership": {
        "capabilities": "기관/외국인 보유 현황 (비율+주수). KR: 네이버 금융",
        "kind": "gather_axis",
        "summary": "지분"
    },
    "gather.peers": {
        "capabilities": "동종업종 피어 종목 목록 (종목코드+시총). KR: KRX/네이버",
        "kind": "gather_axis",
        "summary": "피어"
    },
    "gather.price": {
        "capabilities": "OHLCV 시계열 (수정주가). KR: 네이버 차트 API (최대 12년 일봉, API 키 불필요). US/해외: Yahoo v8 → 네이버 글로벌 자동 fallback. 시장 지수도 가능: gather('price', 'KOSPI')",
        "kind": "gather_axis",
        "summary": "주가"
    },
    "gather.sector": {
        "capabilities": "업종 분류 + 동종업종 PER. KR: KRX KIND + 네이버 금융",
        "kind": "gather_axis",
        "summary": "업종"
    },
    "industry": {
        "kind": "function",
        "returns": "pl.DataFrame\nindustryId=None (가이드):\n산업ID : str — 산업 식별자\n산업명 : str — 한글 산업명\n공정수 : int — 해당 산업의 공정 단계 수\nindustryId 지정:\n공정 : str — 공정 단계명\n종목코드 : str — 6자리 코드\n종목명 : str — 회사명\nsummary=True:\n공정 : str — 공정명\n매출합계 : float — 공정별 매출 합산 (원)\n영업이익합계 : float — 공정별 영업이익 합산 (원)",
        "summary": "산업지도를 조회한다."
    },
    "listing": {
        "args": "kind: 조회 종류. \"companies\"(기본), \"filings\", \"topics\", \"dartlist\".\n한글 alias 지원: \"기업\", \"공시\", \"토픽\", \"법인\", \"dart\".\ncorp: 종목코드 또는 ticker. filings/topics에 필수.\nmarket: \"KR\" 또는 \"US\". companies에서만 사용.",
        "example": "import dartlab\ndartlab.listing()                              # 전 종목 (기존 호환)\ndartlab.listing(\"dartlist\")                    # DART 전체 법인 (비상장 포함, corp_code)\ndartlab.listing(market=\"US\")                   # EDGAR 종목\ndartlab.listing(\"filings\", corp=\"005930\")      # DART 공시 메타\ndartlab.listing(\"filings\", corp=\"AAPL\")        # EDGAR 공시 메타\ndartlab.listing(\"topics\", corp=\"005930\")       # 토픽 목록",
        "kind": "function",
        "returns": "pl.DataFrame\nkind=\"companies\" (기본):\n종목코드 : str — 6자리 종목코드\n종목명 : str — 회사명\n시장 : str — 유가/코스닥/코넥스\n업종 : str — 업종명\nkind=\"filings\":\nid : str — 공시 접수번호\ndate : str — 접수일\ntitle : str — 공시 제목\nurl : str — 공시 URL\nkind=\"topics\":\ntopic : str — topic 이름\nsource : str — 데이터 출처 (docs/finance/report)\nperiods : str — 사용 가능 기간\nkind=\"dartlist\":\ncorp_code : str — DART 법인코드 (8자리)\ncorp_name : str — 법인명\nstock_code : str | None — 종목코드 (비상장이면 None)\n\nRaises:\nValueError: 지원하지 않는 kind, 또는 필수 인자 누락.",
        "summary": "목록 조회 단일 진입점."
    },
    "macro": {
        "guide": "When: 종목 분석 전 경제 환경을 먼저 파악할 때. Company 없이 사용 가능.\nHow: 6막 인과의 최상위 — macro(사이클) → scan(업종) → analysis(기업) 순서.\nstory macro/crisis 타입이 macro 종합 → analysis(안정성, 현금흐름) 순서로 조합.\nVerified:\nmacro(\"사이클\") → CLI + 사분면 + 금리 + 유동성 + 심리 (observed via ai-ask, 2026-04-25 — 정식 Phase P 판정 아님)\nmacro + analysis 조합 → 경제 고려한 논제 검증 (observed via ai-ask, 2026-04-25 — 정식 Phase P 판정 아님)\n\nSee Also\nscan : 전종목 횡단 — macro 사이클에 따른 업종별 영향 비교.\nquant : 시장 심리·변동성 — macro 사이클과 교차 분석.\nanalysis : 개별 기업 재무 — macro 환경 하에서 기업 건전성 판단.",
        "kind": "function",
        "returns": "pl.DataFrame | dict\naxis=None (가이드): DataFrame (axis/label/description/example/group 컬럼)\naxis 지정: dict — 축별 분석 결과.\ncycle: {phase, label, confidence, indicators[{name, value, signal}]}\nsummary: {indicators[], narrative}\nrates/liquidity/trade/...: {지표별 dict, narrative}\n_summary (autoEnrich 자동) — 핵심 요약 + [엔진가정].\n\nRaises\nValueError\nmarket 이 \"US\"/\"KR\" 이 아닌 경우.\n축 이름이 등록되지 않은 경우.\n\nExamples\n>>> dartlab.macro()                          # 가이드\n>>> dartlab.macro(\"사이클\")                   # 경기 4국면 판별\n>>> dartlab.macro(\"금리\")                     # 금리 + 수익률곡선\n>>> dartlab.macro(\"예측\")                     # 침체확률 + GDP Nowcast\n>>> dartlab.macro(\"종합\")                     # 매크로 종합 + 투자전략\n>>> dartlab.macro(\"시나리오\", \"2008 금융위기\")  # 역사적 시나리오\n\nNotes\nFRED 데이터 기반. API 키 불필요 (공개 API).\nHamilton EM, Kalman DFM, Nelson-Siegel, Cleveland Fed 프로빗 등 numpy 직접 구현.",
        "summary": "매크로 분석 실행."
    },
    "macro.assets": {
        "capabilities": "5대 자산 심층 해석 + Cu/Au + BEI 4분면",
        "kind": "macro_axis",
        "summary": "자산"
    },
    "macro.corporate": {
        "capabilities": "전종목 이익사이클 + Ponzi비율 + 레버리지",
        "kind": "macro_axis",
        "summary": "기업집계"
    },
    "macro.crisis": {
        "capabilities": "Credit-to-GDP gap + GHS + Minsky + 역사적 맥락",
        "kind": "macro_axis",
        "summary": "위기"
    },
    "macro.cycle": {
        "capabilities": "경제 사이클 4국면 식별 + 전환 시퀀스 감지",
        "kind": "macro_axis",
        "summary": "사이클"
    },
    "macro.forecast": {
        "capabilities": "LEI + Cleveland Fed 침체확률 + Sahm + Hamilton RS + GaR",
        "kind": "macro_axis",
        "summary": "예측"
    },
    "macro.inventory": {
        "capabilities": "ISM 재고순환 4국면 + 자산배분 바로미터",
        "kind": "macro_axis",
        "summary": "재고"
    },
    "macro.liquidity": {
        "capabilities": "M2 + 연준 B/S + NFCI + 자체 FCI",
        "kind": "macro_axis",
        "summary": "유동성"
    },
    "macro.rates": {
        "capabilities": "금리 방향 + 고용/물가 + 수익률곡선 + 기간프리미엄",
        "kind": "macro_axis",
        "summary": "금리"
    },
    "macro.scenario": {
        "capabilities": "역사적 충격 재현 + 유형별 스트레스 (~146개 프리셋)",
        "kind": "macro_axis",
        "summary": "시나리오"
    },
    "macro.sentiment": {
        "capabilities": "공포탐욕 근사 + VIX 구간 + JLN 실물 불확실성",
        "kind": "macro_axis",
        "summary": "심리"
    },
    "macro.summary": {
        "capabilities": "6막 전체 종합 — 점수 + 자산배분 + 40개 투자전략",
        "kind": "macro_axis",
        "summary": "종합"
    },
    "macro.trade": {
        "capabilities": "교역조건 + 수출이익 선행 + 양국 선행지수",
        "kind": "macro_axis",
        "summary": "교역"
    },
    "nameToCode": {
        "kind": "function",
        "returns": "str | None\n6자리 종목코드. 못 찾으면 None.",
        "summary": "회사명 → 종목코드. 정확히 일치하는 첫 번째 결과."
    },
    "pastInsight": {
        "args": "stockCode: 종목코드 (예: '005930', 'AAPL')",
        "kind": "function",
        "returns": "dict — narrative / strengths / weaknesses / keyMetrics / dataAsOf / source.\nNone — 과거 분석 없음.",
        "summary": "특정 회사의 과거 분석 서사 조회."
    },
    "quant": {
        "guide": "When: 주가 기반 기술적 신호·팩터·리스크를 정량 분석할 때.\nHow: quant(\"판단\") 으로 종합 신호 확인 → 세부 축으로 근거 파악.\nanalysis(재무) + quant(기술) 조합이 story full/valuation 타입의 핵심.\ncredit 과 함께 사용 시 altman/piotroski 로 부도 위험 교차 검증.\nVerified:\nquant(\"판단\") → RSI/ADX/MACD/볼린저/상대강도 + 종합 판정 (observed via ai-ask, 2026-04-25 — 정식 Phase P 판정 아님)\n\nSee Also\nanalysis : 재무 인과 분석 — quant 기술 + analysis 재무 조합.\ngather : 주가·수급 데이터 수집 — quant 의 데이터 원천.\nscan : 전종목 횡단 비교.",
        "kind": "function",
        "returns": "dict\n종목 지정 시 축별 분석 결과:\nverdict(판단): signal, confidence, indicators (매수/매도/중립)\nmomentum(모멘텀): returns, rsi, macd, moving_averages\nvolatility(변동성): realized, garch, regime\nvaluation(가치평가): multiples, peerRank, impliedReturn (배, %)\nsimulation(시뮬레이션): paths, expectedReturn, var (%)\naltman: zScore, zone (safe/grey/distress)\npiotroski: fScore (0~9점)\npl.DataFrame\naxis=None: 가이드 — 축 목록 + 설명 + 예시.\n횡단면 축 (market=\"KR\"): 전종목 DataFrame.\n\nRaises\nValueError\n축 이름이 등록되지 않은 경우.\n종목 필수 축에서 stockCode 누락 시.\nTypeError\naxis 에 list 전달 시.\n\nExamples\n>>> c.quant()                          # 가이드\n>>> c.quant(\"판단\")                     # 종합 매수/매도 판단\n>>> c.quant(\"모멘텀\")                   # 모멘텀 지표\n>>> dartlab.quant(\"altman\", \"005930\")   # Altman Z-Score\n>>> dartlab.quant(\"piotroski\", \"005930\")  # Piotroski F-Score\n\nNotes\n주가 데이터는 gather(\"price\") 경유 자동 수집. API 키 불필요 (Naver/Yahoo).",
        "summary": "가격 기반 정량 분석 — 8 그룹 30+ 축 (기술·리스크·팩터·백테스트·알파)."
    },
    "scan": {
        "guide": "When: 특정 종목 심층 분석 전, 업종·시장 내 상대 위치를 파악할 때.\nHow: scan 으로 전체 분포를 보고 → analysis 로 개별 종목 심층 분석.\nstory credit/governance/audit 타입에서 scan 데이터를 동종업계 비교로 활용.\nVerified:\nscan(\"재무건전성\") → 업종 비교 테이블, 해석 약간 부족 (observed weak via ai-ask, 2026-04-25 — 정식 Phase 판정 아님)\n\nSee Also\nanalysis : 개별 종목 재무 심층 분석.\nquant : 가격 기반 정량 신호.\ncredit : 개별 종목 신용 분석.",
        "kind": "function",
        "returns": "pl.DataFrame\naxis=None (가이드):\naxis : str — 축 이름\nlabel : str — 한글 레이블\ndescription : str — 설명\nexample : str — 사용 예시\naxis=\"profitability\":\n종목코드 : str — 6자리 종목코드\n종목명 : str — 회사명\n영업이익률 : float — 영업이익률 (%)\n순이익률 : float — 순이익률 (%)\nROE : float — 자기자본이익률 (%)\nROA : float — 총자산이익률 (%)\n등급 : str — 수익성 등급\naxis=\"account\" (target=\"매출액\"):\n종목코드 : str — 6자리 종목코드\n종목명 : str — 회사명\n2024, 2023, ... : float — 연도별 값 (원 단위)\naxis=\"ratio\" (target=\"roe\"):\n종목코드 : str — 6자리 종목코드\n종목명 : str — 회사명\n2024, 2023, ... : float — 연도별 비율값 (%, 배)\n기타 축: 종목코드 + 종목명 + 축별 지표 컬럼\n\nRaises\nValueError\naxis 또는 target 이 등록되지 않은 경우.\n그룹 호출 시 target 이 해당 그룹에 속하지 않는 경우.\n\nExamples\n>>> dartlab.scan()                              # 전체 축 가이드\n>>> dartlab.scan(\"profitability\")               # 전종목 수익성\n>>> dartlab.scan(\"account\", \"매출액\")            # 전종목 매출액 시계열\n>>> dartlab.scan(\"ratio\", \"roe\")                # 전종목 ROE 시계열\n>>> dartlab.scan(\"financial\")                   # 재무 8축 가이드\n>>> dartlab.scan(\"financial\", \"수익성\")          # 재무 그룹 내 수익성\n\nNotes\n사전 빌드 parquet 기반. 첫 호출 시 HuggingFace 에서 자동 다운로드.\n전종목 데이터를 한 번에 로드하므로 메모리 ~200MB 소비.",
        "summary": "축(axis)별 전종목 횡단분석."
    },
    "scan.account": {
        "capabilities": "전종목 단일 계정 시계열 (매출액, 영업이익 등)",
        "kind": "scan_axis",
        "summary": "계정"
    },
    "scan.audit": {
        "capabilities": "감사의견, 감사인변경, 특기사항, 감사독립성비율",
        "kind": "scan_axis",
        "summary": "감사리스크"
    },
    "scan.capital": {
        "capabilities": "배당, 자사주(취득/처분/소각), 증자/감자, 환원 분류",
        "kind": "scan_axis",
        "summary": "주주환원"
    },
    "scan.cashflow": {
        "capabilities": "OCF/ICF/FCF + 현금흐름 패턴 분류 (8종)",
        "kind": "scan_axis",
        "summary": "현금흐름"
    },
    "scan.debt": {
        "capabilities": "사채만기, 부채비율, ICR, 위험등급",
        "kind": "scan_axis",
        "summary": "부채구조"
    },
    "scan.disclosureRisk": {
        "capabilities": "공시 변화 기반 선행 리스크 (우발부채, 감사변경, 계열변화, 사업전환)",
        "kind": "scan_axis",
        "summary": "공시리스크"
    },
    "scan.dividendTrend": {
        "capabilities": "DPS 3개년 시계열 + 패턴 분류 (연속증가/안정/감소/시작/중단)",
        "kind": "scan_axis",
        "summary": "배당추이"
    },
    "scan.efficiency": {
        "capabilities": "자산/재고/매출채권 회전율 + CCC(현금전환주기) + 등급",
        "kind": "scan_axis",
        "summary": "효율성"
    },
    "scan.governance": {
        "capabilities": "지배구조 (지분율, 사외이사, 보수비율, 감사의견, 소액주주 분산)",
        "kind": "scan_axis",
        "summary": "거버넌스"
    },
    "scan.growth": {
        "capabilities": "매출/영업이익/순이익 CAGR + 성장 패턴 분류 (6종)",
        "kind": "scan_axis",
        "summary": "성장성"
    },
    "scan.insider": {
        "capabilities": "최대주주 지분변동, 자기주식 현황, 경영권 안정성",
        "kind": "scan_axis",
        "summary": "내부자지분"
    },
    "scan.liquidity": {
        "capabilities": "유동비율 + 당좌비율 — 단기 지급능력",
        "kind": "scan_axis",
        "summary": "유동성"
    },
    "scan.macroBeta": {
        "capabilities": "전종목 GDP/금리/환율 베타 횡단면 (OLS 회귀). 사전 수집: Ecos().series('GDP', enrich=True)",
        "kind": "scan_axis",
        "summary": "거시베타"
    },
    "scan.network": {
        "capabilities": "상장사 관계 네트워크 (출자/지분/계열)",
        "kind": "scan_axis",
        "summary": "네트워크"
    },
    "scan.profitability": {
        "capabilities": "영업이익률/순이익률/ROE/ROA + 등급",
        "kind": "scan_axis",
        "summary": "수익성"
    },
    "scan.quality": {
        "capabilities": "Accrual Ratio + CF/NI 비율 — 이익이 현금 뒷받침되는지",
        "kind": "scan_axis",
        "summary": "이익의 질"
    },
    "scan.ratio": {
        "capabilities": "전종목 단일 재무비율 시계열 (ROE, 부채비율 등)",
        "kind": "scan_axis",
        "summary": "비율"
    },
    "scan.screen": {
        "capabilities": "멀티팩터 스크리닝 (value/dividend/growth/risk/quality 프리셋)",
        "kind": "scan_axis",
        "summary": "스크리닝"
    },
    "scan.valuation": {
        "capabilities": "PER/PBR/PSR + 시가총액 + 등급 (네이버 실시간)",
        "kind": "scan_axis",
        "summary": "밸류에이션"
    },
    "scan.workforce": {
        "capabilities": "직원수, 평균급여, 인건비율, 1인당부가가치, 성장률, 고액보수",
        "kind": "scan_axis",
        "summary": "인력/급여"
    },
    "search": {
        "aicontext": "BETA — 우선 사용 비권장. 단일 종목 공시는 Company.disclosure/liveFilings 우선.\nsearch 호출 후 0건이면 즉시 fallback (재호출/키워드 변형 round 낭비 금지).",
        "args": "query: 검색어 (한국어). \"유상증자\", \"반도체 HBM 투자\" 등.\ncorp: 종목 필터 (종목코드 \"005930\" 또는 회사명 \"삼성전자\").\nstart: 시작일 (YYYYMMDD).\nend: 종료일 (YYYYMMDD).\ntopK: 반환 건수 (기본 10).\nscope: ``\"auto\"`` (기본), ``\"title\"``, ``\"content\"``, ``\"both\"``.",
        "capabilities": "제목 검색: 공시 유형명/섹션 제목에서 매칭 (\"유상증자\", \"대표이사 변경\")\n본문 검색: 사업보고서 등 본문에서 개념 매칭 (\"반도체 HBM 투자\", \"환율 리스크\")\n종목/기간 필터 지원\nDART 공시 뷰어 링크 포함 (dartUrl 컬럼)",
        "example": "import dartlab\ndartlab.search(\"유상증자\")                                # 제목 매칭\ndartlab.search(\"반도체 HBM 투자\")                          # 본문 자동 매칭\ndartlab.search(\"환율 리스크\", scope=\"content\")              # 본문 강제\ndartlab.search(\"대표이사 변경\", corp=\"005930\")              # 종목 필터",
        "guide": "\"유상증자 한 회사?\" -> search(\"유상증자\") [BETA, 0건이면 stop]\n\"반도체 투자 트렌드?\" -> search(\"반도체 HBM 투자\") [BETA, 0건이면 stop]\n\"삼성전자 최근 공시\" -> Company(\"005930\").disclosure() (search 아님)",
        "kind": "function",
        "requires": "데이터: stemIndex (scope=title) + contentIndex (scope=content)",
        "returns": "pl.DataFrame\nscore : float — 매칭 점수\nrcept_no : str — 접수번호 (DART 고유 ID)\ncorp_name : str — 회사명\nreport_nm : str — 공시 유형명\nscope : str — 검색 소스 (\"title\" 또는 \"content\", auto/both 모드)\ndartUrl : str — DART 공시 뷰어 URL",
        "seeAlso": "Company: 종목코드/회사명으로 Company 생성\nlisting: 전체 상장법인 목록",
        "summary": "공시 검색. **⚠ BETA — AI 사용 비권장**."
    },
    "searchName": {
        "args": "keyword: 종목명, 종목코드, 또는 ticker.",
        "example": "dartlab.searchName(\"삼성전자\")\ndartlab.searchName(\"AAPL\")",
        "kind": "function",
        "returns": "pl.DataFrame — 종목 검색 결과.",
        "summary": "종목명/코드로 종목 찾기 (KR + US)."
    },
    "sectorInsights": {
        "args": "sector: 업종명 (예: '반도체', '식품')\nlimit: 상위 N개 (기본 3)",
        "kind": "function",
        "returns": "list — 각 항목: narrative / strengths / weaknesses / keyMetrics / stockCode / corpName.",
        "summary": "동종 업계 과거 분석 서사 목록 (교차 학습)."
    },
    "setup": {
        "aicontext": "AI 분석 기능 사용 전 provider 설정 상태 확인\n미설정 provider 감지 시 setup() 안내로 연결\n설정 완료 여부를 프로그래밍 방식으로 체크 가능",
        "args": "provider: provider명 또는 alias. None이면 전체 현황 표시.\n지원: \"chatgpt\", \"openai\", \"gemini\", \"groq\", \"cerebras\",\n\"mistral\", \"ollama\", \"codex\", \"custom\".",
        "capabilities": "전체 AI provider 설정 현황 테이블 표시\nprovider별 대화형 설정 (키 입력 → .env 저장)\nChatGPT OAuth 브라우저 로그인\nOpenAI/Gemini/Groq/Cerebras/Mistral API 키 설정\nOllama 로컬 LLM 설치 안내",
        "example": "import dartlab\ndartlab.setup()              # 전체 provider 현황\ndartlab.setup(\"chatgpt\")     # ChatGPT OAuth 브라우저 로그인\ndartlab.setup(\"openai\")      # OpenAI API 키 설정\ndartlab.setup(\"ollama\")      # Ollama 설치 안내",
        "guide": "\"AI 설정 어떻게 해?\" -> setup()으로 전체 현황 확인\n\"ChatGPT 연결하고 싶어\" -> setup(\"chatgpt\")\n\"OpenAI 키 등록\" -> setup(\"openai\")\n\"Ollama 어떻게 써?\" -> setup(\"ollama\")",
        "kind": "function",
        "requires": "없음",
        "returns": "None (터미널/노트북에 안내 출력).",
        "seeAlso": "ask: AI 질문 (setup 완료 후 사용)\nchat: AI 대화 (setup 완료 후 사용)\nllm.configure: 프로그래밍 방식 provider 설정",
        "summary": "AI provider 설정 안내 + 인터랙티브 설정."
    },
    "topdown": {
        "args": "market: \"KR\" | \"US\"\nsectors: 특정 섹터만 지정. None이면 사이클 국면 자동 매핑.\ntopN: 섹터당 추천 종목 수\nas_of: 백테스트용 기준일",
        "kind": "function",
        "returns": "dict: {\n\"cycle\": {phase, label, confidence, ...},\n\"transition\": {...} | None,\n\"recommendedSectors\": [...],\n\"screens\": {sector: [{stockCode, name, signals, ...}, ...]},\n\"narrative\": \"사이클 → 섹터 → 종목 인과 사슬 문장\"\n}",
        "summary": "탑다운 분석 — 시장 → 섹터 → 종목."
    },
    "verbose": {
        "kind": "module",
        "summary": "bool(x) -> bool"
    }
}
"""
)
