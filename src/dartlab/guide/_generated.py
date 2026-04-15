"""런타임 capabilities 카탈로그 (자동 생성).

이 파일은 scripts/build/generateSpec.py가 자동 생성합니다. 직접 수정 금지.
"""

CAPABILITIES: dict[str, dict] = {
    "ChartResult": {
        "kind": "class",
        "summary": "chart() 반환 객체 — 시각화 + 렌더링."
    },
    "Company": {
        "aicontext": "개별 종목 분석의 시작점. explore/finance/analysis 수퍼툴이 이 객체를 소비.\n\"삼성전자 분석해줘\" → Company(\"005930\") 생성 → briefing → LLM 해석.",
        "capabilities": "종목코드 (\"005930\"), 회사명 (\"삼성전자\"), 영문 ticker (\"AAPL\") 모두 지원\ncanHandle() 체인: provider priority 순 자동 라우팅 (DART → EDGAR)\n새 국가 추가 시 이 파일 수정 불필요 — provider 패키지만 추가\n핵심 인터페이스: show(topic) / index / trace(topic) / diff()\nnamespace: docs (원문) / finance (숫자) / report (정형공시) / profile (merge)\n바로가기: BS/IS/CF/CIS, ratios, ratioSeries, timeseries\n메타: sections, topics, filings(), market, currency",
        "guide": "\"삼성전자 재무제표\" -> c = Company(\"005930\"); c.IS\n\"사업 개요 보여줘\" -> c.show(\"businessOverview\")\n\"어떤 데이터 있어?\" -> c.index 또는 c.topics\n\"출처 추적\" -> c.trace(\"revenue\")\n\"기간 변화\" -> c.diff()\n\"종합평가\" -> c.analysis(\"financial\", \"종합평가\")\n\"리뷰 보고서\" -> c.review()\n\"Apple 분석\" -> Company(\"AAPL\") (자동 EDGAR 라우팅)",
        "kind": "function",
        "requires": "DART: 사전 다운로드 데이터 (dartlab.downloadAll() 또는 자동 다운로드).\nEDGAR: 인터넷 연결 (On-demand 수집).",
        "seeAlso": "search: 종목 검색 (종목코드 모를 때)\nscan: 전종목 횡단분석 (기업 비교)\nanalysis: 14축 전략분석\ngather: 주가/수급/거시 데이터",
        "summary": "종목코드/회사명/ticker → 적절한 Company 인스턴스 생성."
    },
    "Company.analysis": {
        "kind": "property",
        "summary": "재무제표 완전 분석 — dual access (api-contract)."
    },
    "Company.ask": {
        "aicontext": "AI가 분석 전 과정을 주도. dartlab 엔진(analysis, scan, gather 등)을\n도구로 호출하여 데이터 수집, 계산, 판단, 해석을 수행.",
        "capabilities": "엔진 계산 결과를 컨텍스트로 조립하여 LLM에 전달\n질문 분류 기반 분석 패키지 자동 선택 (financial, valuation, risk 등)\n멀티 provider 지원 (openai, ollama, codex 등)\n스트리밍 응답 지원",
        "guide": "\"영업이익률 분석해줘\" → c.ask(\"영업이익률 추세는?\")\n\"AI한테 질문하고 싶어\" → c.ask(\"질문\")\n\"스트리밍으로 답변받기\" → c.ask(\"질문\", stream=True)",
        "kind": "method",
        "requires": "API 키: LLM provider API 키 (OPENAI_API_KEY 등)",
        "seeAlso": "chat: 에이전트 모드 (tool calling 기반 심화 분석)\nreviewer: 구조화된 AI 보고서 (자유 질문이 아닌 섹션별)\nreview: AI 없는 데이터 검토서",
        "summary": "LLM에게 이 기업에 대해 질문."
    },
    "Company.audit": {
        "aicontext": "감사 리스크 종합 평가 — 투자 의사결정의 핵심 안전장치\n감사의견 변경, 계속기업 불확실성은 최고 경고 수준",
        "capabilities": "감사의견 추이 (적정/한정/부적정/의견거절)\n감사인 변경 이력 + 사유\n계속기업 불확실성 플래그\n핵심감사사항 (KAM) 추출\n내부회계관리제도 검토의견",
        "guide": "\"감사의견 확인\" → c.audit()\n\"감사인 바뀌었어?\" → c.audit()[\"auditorChanges\"]\n\"계속기업 의문은?\" → c.audit()[\"goingConcern\"]",
        "kind": "method",
        "requires": "데이터: docs + report (자동 다운로드)",
        "seeAlso": "governance: 지배구조 분석 (감사위원회 구성 포함)\ninsights: 종합 등급 (감사 리스크도 반영)\nreview: 재무정합성 섹션에서 감사 결과 활용",
        "summary": "감사 리스크 종합 분석."
    },
    "Company.canHandle": {
        "kind": "method",
        "summary": "DART 종목코드(6자) 또는 한글 회사명이면 처리 가능."
    },
    "Company.capital": {
        "aicontext": "주주환원 정책 평가 — 배당수익률/성향/자사주 정량 데이터\n시장 횡단 비교로 상대적 환원 수준 판단",
        "capabilities": "배당수익률 + 배당성향 추이\n자사주 매입/소각 이력\n총주주환원율 (배당 + 자사주)\n시장 전체 주주환원 횡단 비교",
        "guide": "\"배당 정보\" → c.capital() 또는 c.show(\"dividend\")\n\"주주환원율은?\" → c.capital()\n\"전체 상장사 배당 비교\" → c.capital(\"all\")",
        "kind": "method",
        "requires": "데이터: DART 정기보고서 (자동 수집)",
        "seeAlso": "show: c.show(\"dividend\")로 docs 기반 배당 상세\nsceMatrix: 자본변동표 (배당/자사주가 자본에 미치는 영향)\ndebt: 부채 구조 (자본 정책의 다른 면)",
        "summary": "주주환원 분석 (배당, 자사주, 총환원율)."
    },
    "Company.codeName": {
        "kind": "method",
        "summary": "종목코드 → 회사명 변환."
    },
    "Company.contextSlices": {
        "aicontext": "ask()/chat()의 시스템 프롬프트에 직접 주입되는 데이터\nLLM이 소비하는 최종 형태의 컨텍스트",
        "capabilities": "retrievalBlocks를 LLM 컨텍스트 윈도우에 맞게 슬라이싱\n토큰 예산 내에서 최대한 많은 관련 정보를 담는 압축 포맷\ntopic/period 기준 우선순위 정렬",
        "guide": "\"LLM에 들어가는 컨텍스트\" → c.contextSlices\n\"AI가 보는 데이터\" → c.contextSlices",
        "kind": "property",
        "requires": "데이터: docs (자동 다운로드)",
        "seeAlso": "retrievalBlocks: 슬라이싱 전 전체 retrieval 블록\nask: contextSlices를 내부적으로 소비하는 AI 질문 인터페이스",
        "summary": "LLM 투입용 context slice DataFrame."
    },
    "Company.credit": {
        "kind": "property",
        "summary": "독립 신용평가 — dual access."
    },
    "Company.currency": {
        "kind": "property",
        "seeAlso": "market: 시장 코드",
        "summary": "통화 코드 (DART 제공자는 항상 KRW)."
    },
    "Company.debt": {
        "aicontext": "부채 구조/건전성 정량 평가 — 차입금 의존도, 만기 구조\n시장 횡단 비교로 상대적 재무 안정성 판단",
        "capabilities": "총차입금 + 순차입금 규모\n부채비율 + 차입금의존도\n단기/장기 차입금 비율\n시장 전체 부채 구조 횡단 비교",
        "guide": "\"부채 구조 분석\" → c.debt()\n\"부채비율은?\" → c.debt() 또는 c.ratios\n\"전체 상장사 부채 비교\" → c.debt(\"all\")",
        "kind": "method",
        "requires": "데이터: DART 정기보고서 (자동 수집)",
        "seeAlso": "BS: 재무상태표 (부채 원본 데이터)\nratios: 재무비율 (부채비율 포함)\ncapital: 주주환원 (자본 정책의 다른 면)",
        "summary": "부채 구조 분석 (차입금, 부채비율, 만기 구조)."
    },
    "Company.diff": {
        "aicontext": "기간간 공시 변경 감지 — 사업 방향 전환, 리스크 요인 변화 탐지\nwatch()보다 세밀한 줄 단위 변경 추적",
        "capabilities": "전체 topic 변경 요약 (변경량 스코어링)\n특정 topic 기간별 변경 이력\n두 기간 줄 단위 diff (추가/삭제/변경)",
        "guide": "\"공시에서 뭐가 바뀌었어?\" → c.diff()\n\"사업개요 변경 이력\" → c.diff(\"businessOverview\")\n\"2023 vs 2024 차이\" → c.diff(\"businessOverview\", \"2023\", \"2024\")",
        "kind": "method",
        "requires": "데이터: docs (2개 이상 기간 필요)",
        "seeAlso": "watch: 변화 중요도 스코어링 (diff보다 요약적)\nkeywordTrend: 키워드 ��도 추이 (텍스트 변화의 다른 관점)\nshow: 특정 기간 원문 조회",
        "summary": "기간간 텍스트 변경 비교."
    },
    "Company.disclosure": {
        "aicontext": "특정 유형 공시 존재 여부 확인 → 분석 범위 동적 결정\n최근 공시 빈도/유형 패턴으로 기업 이벤트 감지",
        "capabilities": "전체 공시유형 조회 (정기, 주요사항, 발행, 지분, 외부감사 등)\n기간, 유형, 키워드 필터링\n최종보고서만 필터 (정정 이전 제외)",
        "guide": "\"최근 공시 뭐 나왔어?\" → c.disclosure(days=30)\n\"주요사항 공시 있어?\" → c.disclosure(type=\"B\")\n\"사업보고서 언제 나왔어?\" → c.disclosure(keyword=\"사업보고서\")",
        "kind": "method",
        "requires": "API 키: DART_API_KEY",
        "seeAlso": "liveFilings: 실시간 최신 공시 (정규화된 포맷)\nreadFiling: 공시 원문 텍스트 읽기\nfilings: 로컬 보유 공시 목록",
        "summary": "OpenDART 전체 공시 목록 조회."
    },
    "Company.facts": {
        "kind": "property",
        "summary": "topic × period 형태의 통합 facts 테이블 (sections + finance + report merge)."
    },
    "Company.filings": {
        "aicontext": "어떤 공시가 보유돼 있는지 확인하여 분석 범위 결정에 활용",
        "capabilities": "로컬에 보유한 공시 문서 목록\n기간별, 문서유형별 정리\nDART 뷰어 링크 포함",
        "guide": "\"이 회사 공시 목록 보여줘\" → c.filings()\n\"어떤 보고서가 있어?\" → c.filings()로 보유 문서 확인",
        "kind": "method",
        "requires": "데이터: docs (자동 다운로드)",
        "seeAlso": "disclosure: OpenDART API 기반 실시간 공시 목록 (로컬 보유가 아닌 전체)\nliveFilings: 최신 공시 실시간 조회\nupdate: 누락 공시 증분 수집",
        "summary": "공시 문서 목록 + DART 뷰어 링크."
    },
    "Company.fiscalYearEnd": {
        "kind": "property",
        "summary": "회계연도 종료 월-일 (한국 종목은 12-31 표준)."
    },
    "Company.gather": {
        "aicontext": "ask()/chat()에서 주가/수급/거시 데이터를 컨텍스트로 주입\n기업 분석 시 시장 데이터 보충 자료로 활용",
        "capabilities": "price: OHLCV 주가 시계열 (KR Naver / US Yahoo)\nflow: 외국인/기관 수급 동향 (KR 전용)\nmacro: ECOS(KR) / FRED(US) 거시지표 시계열\nnews: Google News RSS 뉴스 수집\n자동 fallback 체인, circuit breaker, TTL 캐시",
        "guide": "\"주가 데이터\" → c.gather(\"price\")\n\"외국인/기관 수급\" → c.gather(\"flow\")\n\"거시경제 지표\" → c.gather(\"macro\")\n\"뉴스 수집\" → c.gather(\"news\") 또는 c.news()",
        "kind": "method",
        "requires": "price/flow/news: 없음 (공개 API)\nmacro: API 키 -- ECOS_API_KEY (KR) 또는 FRED_API_KEY (US)",
        "seeAlso": "news: 뉴스 전용 단축 메서드\nask: gather 데이터를 컨텍스트로 활용한 AI 분석",
        "summary": "외부 시장 데이터 수집 — 4축 (price/flow/macro/news)."
    },
    "Company.governance": {
        "aicontext": "지배구조 리스크 평가 — 사외이사/감사위원/최대주주 정량 데이터\n시장 횡단 비교로 상대적 거버넌스 수준 판단",
        "capabilities": "사외이사 비율 + 감사위원회 구성\n최대주주 지분율 + 특수관계인\n시장 전체 거버넌스 횡단 비교",
        "guide": "\"지배구조 분석\" → c.governance()\n\"사외이사 비율은?\" → c.governance()\n\"전체 상장사 거버넌스 비교\" → c.governance(\"all\")",
        "kind": "method",
        "requires": "데이터: DART 정기보고서 (자동 수집)",
        "seeAlso": "network: 출자/계열사 관계 (거버넌스의 다른 관점)\naudit: 감사 리스크 (감사위원회와 연관)",
        "summary": "지배구조 분석 (이사회, 감사위원, 최대주주)."
    },
    "Company.index": {
        "aicontext": "LLM이 Company 전체 구조를 파악하는 핵심 진입점\nask()에서 어떤 데이터를 참조할지 결정하는 기초 정보",
        "capabilities": "docs sections + finance + report 전체를 하나의 목차로 통합\n각 항목의 chapter, topic, label, kind, source, periods, shape, preview 제공\nsections 메타데이터 + 존재 확인만으로 구성 (파서 미호출, lazy)\nviewer/렌더러가 소비하는 메타데이터 원천",
        "guide": "\"전체 목차 보여줘\" → c.index\n\"어떤 데이터가 있는지 구조적으로\" → c.index",
        "kind": "property",
        "requires": "데이터: docs/finance/report 중 하나 이상 (자동 다운로드)",
        "seeAlso": "topics: topic 단위 요약 (index보다 간결)\nsections: 전체 sections 지도 (index의 원본)\nprofile: 통합 프로필 접근자",
        "summary": "현재 공개 Company 구조 인덱스 DataFrame -- 전체 데이터 목차."
    },
    "Company.industry": {
        "kind": "method",
        "summary": "이 회사의 밸류체인 산업 내 위치를 분석한다."
    },
    "Company.keywordTrend": {
        "aicontext": "공시 텍스트의 키워드 빈도 변화로 전략 방향 전환 감지\nAI, ESG, 탄소중립 등 트렌드 키워드 모니터링",
        "capabilities": "공시 텍스트에서 키워드 빈도 추이 분석\n54개 내장 키워드 세트 (AI, ESG, 탄소중립 등)\ntopic별 x 기간별 빈도 매트릭스\n복수 키워드 동시 검색",
        "guide": "\"AI 언급 추이\" → c.keywordTrend(\"AI\")\n\"ESG 관련 변화\" → c.keywordTrend(\"ESG\")\n\"전체 키워드 트렌드\" → c.keywordTrend()",
        "kind": "method",
        "requires": "데이터: docs (자동 다운로드)",
        "seeAlso": "diff: 텍스트 줄 단위 변경 비교 (키워드가 아닌 전체 변경)\nwatch: 변화 중요도 스코어링",
        "summary": "공시 텍스트 키워드 빈도 추이 (topic x period x keyword)."
    },
    "Company.listing": {
        "capabilities": "KOSPI + KOSDAQ 전체 상장법인\n종목코드, 종목명, 시장구분, 업종",
        "kind": "method",
        "requires": "데이터: listing (자동 다운로드)",
        "summary": "KRX 전체 상장법인 목록 (KIND 기준)."
    },
    "Company.liveFilings": {
        "aicontext": "최신 공시 모니터링으로 기업 이벤트(배당, 유증, 합병 등) 실시간 감지\nreadFiling()과 조합하여 최신 공시 원문 분석",
        "capabilities": "OpenDART API 실시간 공시 조회\n기간, 건수, 키워드 필터링\n정규화된 컬럼 (docId, filedAt, title, formType 등)",
        "guide": "\"최근 공시 확인해줘\" → c.liveFilings()\n\"이번 주 공시 있어?\" → c.liveFilings(days=7)\n\"배당 관련 공시\" → c.liveFilings(keyword=\"배당\")",
        "kind": "method",
        "requires": "API 키: DART_API_KEY",
        "seeAlso": "disclosure: 과거 전체 공시 이력 조회\nreadFiling: 공시 원문 텍스트 읽기\nwatch: 공시 변화 중요도 스코어링",
        "summary": "OpenDART 기준 실시간 공시 목록 조회."
    },
    "Company.market": {
        "kind": "property",
        "seeAlso": "currency: 통화 코드",
        "summary": "시장 코드 (DART 제공자는 항상 KR)."
    },
    "Company.network": {
        "aicontext": "그룹 계열사/출자 구조 파악 — 지배구조 분석의 기초 데이터\n순환출자 탐지로 거버넌스 리스크 감지",
        "capabilities": "그룹 계열사 목록 (members)\n출자/피출자 연결 + 지분율 (edges)\n순환출자 경로 탐지 (cycles)\nego 서브그래프 (peers)\n인터랙티브 네트워크 시각화 (브라우저)",
        "guide": "\"계열사 관계도\" → c.network() 또는 c.network().show()\n\"같은 그룹 계열사\" → c.network(\"members\")\n\"출자/지분 구조\" → c.network(\"edges\")\n\"순환출자 있어?\" → c.network(\"cycles\")",
        "kind": "method",
        "requires": "데이터: DART 대량보유/임원 공시 (자동 수집)",
        "seeAlso": "governance: 이사회/감사위원/최대주주 분석\ncapital: 주주환원 분석",
        "summary": "관계 네트워크 (지분출자 + 그룹 계열사 지도)."
    },
    "Company.news": {
        "aicontext": "최근 뉴스로 시장 반응, 이슈, 이벤트 파악\nask()/chat()에서 정성적 시장 맥락 보충",
        "capabilities": "Google News RSS 기반 뉴스 수집\n제목, 날짜, 소스, 링크\n기간 조절 가능",
        "guide": "\"최근 뉴스 보여줘\" → c.news()\n\"이번 주 뉴스\" → c.news(days=7)",
        "kind": "method",
        "requires": "없음 (공개 RSS)",
        "seeAlso": "liveFilings: 최신 공시 (뉴스가 아닌 공식 공시)\ngather: 뉴스 포함 4축 외부 데이터 수집",
        "summary": "최근 뉴스 수집."
    },
    "Company.priority": {
        "kind": "method",
        "summary": "낮을수록 먼저 시도. DART=10 (기본 provider)."
    },
    "Company.quant": {
        "kind": "method",
        "summary": "주가 기술적 분석 — self-discovery 패턴."
    },
    "Company.rank": {
        "aicontext": "시장/섹터 내 상대 위치 파악 — 피어 비교 분석의 기초\nsizeClass로 대형/중형/소형주 분류",
        "capabilities": "전체 시장 내 매출/자산 순위\n섹터 내 상대 순위\n매출 성장률 기반 규모 분류 (large/mid/small)",
        "guide": "\"이 회사 순위는?\" → c.rank\n\"시장에서 몇 등이야?\" → c.rank.revenueRank\n\"대형주야?\" → c.rank.sizeClass",
        "kind": "property",
        "requires": "데이터: buildSnapshot() 사전 실행 필요",
        "seeAlso": "sector: 섹터 분류 (rank의 기준 그룹)\ninsights: 종합 등급 평가",
        "summary": "전체 시장 + 섹터 내 규모 순위 (매출/자산/성장률)."
    },
    "Company.rawDocs": {
        "aicontext": "원본 데이터 구조 파악 — 파싱 전 상태로 디버깅/검증에 활용",
        "capabilities": "HuggingFace docs 카테고리 원본 데이터 직접 접근\n가공/정규화 이전 상태 그대로 반환",
        "guide": "\"원본 공시 데이터 보여줘\" → c.rawDocs\n\"가공 전 데이터 확인\" → c.rawDocs",
        "kind": "property",
        "requires": "데이터: HuggingFace docs parquet (자동 다운로드)",
        "seeAlso": "sections: docs 가공 후 topic x period 통합 지도\nrawFinance: 재무제표 원본 데이터\nrawReport: 정기보고서 원본 데이터",
        "summary": "공시 문서 원본 parquet 전체 (가공 전)."
    },
    "Company.rawFinance": {
        "aicontext": "XBRL 정규화 전 원본 구조 파악 — 매핑 검증에 활용",
        "capabilities": "HuggingFace finance 카테고리 원본 데이터 직접 접근\nXBRL 정규화 이전 상태 그대로 반환",
        "guide": "\"원본 재무 데이터 보여줘\" → c.rawFinance\n\"XBRL 원본 확인\" → c.rawFinance",
        "kind": "property",
        "requires": "데이터: HuggingFace finance parquet (자동 다운로드)",
        "seeAlso": "BS: 가공된 재무상태표\nIS: 가공된 손익계산서\nrawDocs: 공시 문서 원본",
        "summary": "재무제표 원본 parquet 전체 (가공 전)."
    },
    "Company.rawReport": {
        "aicontext": "정기보고서 API 원본 확인 — report topic 매핑 검증에 활용",
        "capabilities": "HuggingFace report 카테고리 원본 데이터 직접 접근\n정기보고서 API 데이터 가공 이전 상태 반환",
        "guide": "\"원본 보고서 데이터 보여줘\" → c.rawReport\n\"정기보고서 원본 확인\" → c.rawReport",
        "kind": "property",
        "requires": "데이터: HuggingFace report parquet (자동 다운로드)",
        "seeAlso": "rawDocs: 공시 문서 원본\nrawFinance: 재무제표 원본\nshow: 가공된 topic 데이터 조회",
        "summary": "정기보고서 원본 parquet 전체 (가공 전)."
    },
    "Company.readFiling": {
        "aicontext": "공시 원문 텍스트를 LLM 컨텍스트에 주입하여 심층 분석 수행\nsections=True로 구조화하면 특정 섹션만 선택적 분석 가능",
        "capabilities": "접수번호(str) 직접 지정 또는 DataFrame row 자동 파싱\n전문 텍스트 또는 ZIP 기반 구조화 섹션 반환\n텍스트 길이 제한 (truncation) 지원",
        "guide": "\"이 공시 내용 보여줘\" → c.readFiling(접수번호)\n\"공시 원문 분석해줘\" → c.readFiling()으로 원문 확보 후 ask()로 분석",
        "kind": "method",
        "requires": "API 키: DART_API_KEY",
        "seeAlso": "liveFilings: 최신 공시 목록에서 접수번호 확인\ndisclosure: 과거 공시 목록에서 접수번호 확인",
        "summary": "접수번호 또는 liveFilings row로 공시 원문을 읽는다."
    },
    "Company.resolve": {
        "kind": "method",
        "summary": "종목코드 또는 회사명 → 종목코드 변환."
    },
    "Company.retrievalBlocks": {
        "aicontext": "ask()/chat()에서 원문 기반 답변 생성 시 소스로 사용\nretrieval 기반 컨텍스트 주입의 원천 데이터",
        "capabilities": "docs 원문을 markdown 형태 그대로 보존한 검색용 블록\n각 블록은 topic/subtopic/period 단위로 분할\nRAG, 벡터 검색, 원문 참조에 최적화된 포맷",
        "guide": "\"원문 검색용 블록\" → c.retrievalBlocks\n\"RAG용 데이터\" → c.retrievalBlocks",
        "kind": "property",
        "requires": "데이터: docs (자동 다운로드)",
        "seeAlso": "contextSlices: retrievalBlocks를 LLM 윈도우에 맞게 슬라이싱한 결과\nsections: 구조화된 데이터 지도 (retrievalBlocks의 원본)",
        "summary": "원문 markdown 보존 retrieval block DataFrame."
    },
    "Company.review": {
        "kind": "property",
        "summary": "재무제표 구조화 보고서 — dual access."
    },
    "Company.search": {
        "kind": "method",
        "summary": "회사명 부분 검색 (KIND 목록 기준)."
    },
    "Company.sections": {
        "aicontext": "전체 지도가 필요할 때만 사용. 개별 topic은 show(topic) 추천\n메모리 부하가 크므로 AI 코드에서 직접 접근 지양",
        "capabilities": "topic × period 수평화 통합 DataFrame\ndocs/finance/report 3-source 병합\nshow(topic)/trace(topic)/diff() 의 근간 데이터",
        "guide": "\"이 회사 전체 데이터 지도\" → c.sections\n\"어떤 topic이 있어?\" → c.topics (경량)",
        "kind": "property",
        "requires": "데이터: docs (필수), finance/report (선택, 자동 다운로드)",
        "seeAlso": "topics: sections 기반 topic 요약 (더 간결)\nshow: 특정 topic 데이터 조회\nindex: 전체 구조 메타데이터 목차",
        "summary": "sections — docs + finance + report 통합 지도."
    },
    "Company.sector": {
        "aicontext": "섹터 분류 결과로 동종업계 비교, 섹터 파라미터 자동 선택\nanalysis/valuation에서 섹터별 벤치마크 기준으로 활용",
        "capabilities": "WICS 11대 섹터 + 하위 산업그룹 자동 분류\nKIND 업종명 + 주요제품 키워드 기반 매칭\noverride 테이블 우선 → 키워드 → 업종명 순 fallback",
        "guide": "\"이 회사 어떤 섹터야?\" → c.sector\n\"업종 분류\" → c.sector",
        "kind": "property",
        "requires": "데이터: KIND 상장사 목록 (자동 로드)",
        "seeAlso": "sectorParams: 섹터별 밸���에이션 파라미터 (할인율, PER 등)\nrank: 섹�� 내 규모 순위\ninsights: 섹터 기준 등급 평가",
        "summary": "WICS 투자 섹터 분류 (KIND 업종 + 키워드 기반)."
    },
    "Company.sectorParams": {
        "aicontext": "valuation()에서 DCF 할인율, 성장률 자동 적용\n섹터 특성 반영된 밸류에이션 파라미터",
        "capabilities": "섹터별 할인율, 성장률, PER 멀티플 제공\n섹터 분류 결과에 연동된 파라미터 자동 선택",
        "guide": "\"이 섹터 할인율은?\" → c.sectorParams.discountRate\n\"PER 멀티플\" → c.sectorParams.perMultiple",
        "kind": "property",
        "requires": "데이터: sector 분류 결과 (자동 연산)",
        "seeAlso": "sector: 섹터 분류 정보 (sectorParams의 기반)\nvaluation: 밸류에이션 (sectorParams를 내부적으로 소비)",
        "summary": "현재 종목의 섹터별 밸류에이션 파라미터."
    },
    "Company.select": {
        "kind": "property",
        "summary": "show() 결과에서 행/열 필터 — dual access."
    },
    "Company.show": {
        "kind": "property",
        "summary": "topic 의 데이터를 반환 — 사용자 단일 진입점 (api-contract dual access)."
    },
    "Company.sources": {
        "aicontext": "데이터 가용성 사전 점검 — 분석 가능 범위 판단의 기초",
        "capabilities": "3개 데이터 source(docs, finance, report) 존재 여부/규모 한눈에 확인\n각 source의 row/col 수와 shape 문자열 제공\n데이터 로드 전 가용성 사전 점검",
        "guide": "\"데이터 뭐가 있어?\" → c.sources\n\"docs/finance/report 상태\" → c.sources",
        "kind": "property",
        "requires": "없음 (메타데이터만 조회, 데이터 파싱 불필요)",
        "seeAlso": "topics: topic 단위 상세 데이터 지도\ntrace: 특정 topic의 출처 추적",
        "summary": "docs/finance/report 3개 source의 가용 현황 요약."
    },
    "Company.status": {
        "capabilities": "로컬 데이터 현황 (종목별 docs/finance/report 보유 여부)\n최종 업데이트 일시",
        "kind": "method",
        "summary": "로컬에 보유한 전체 종목 인덱스."
    },
    "Company.table": {
        "aicontext": "docs 원문 테이블을 구조화하여 정량 분석에 활용\nnumeric=True로 금액 문자열을 수치화하면 계산 가능",
        "capabilities": "docs 원문의 markdown table을 Polars DataFrame으로 변환\nsubtopic 지정으로 특정 표만 추출\nnumeric 모드로 금액 문자열을 float 변환\nperiod 필터로 특정 기간 컬럼만 선택",
        "guide": "\"직원 현황 테이블\" → c.table(\"employee\")\n\"표 데이터를 숫자로\" → c.table(topic, numeric=True)",
        "kind": "method",
        "requires": "데이터: docs (자동 다운로드)",
        "seeAlso": "show: topic 전체 데이터 (table은 subtopic 단위 파싱)\nselect: show() 결과에서 행/열 필터",
        "summary": "subtopic wide 셀의 markdown table을 구조화 DataFrame으로 파싱."
    },
    "Company.topicSummaries": {
        "kind": "method",
        "summary": "토픽별 요약 dict — AI가 경로 탐색에 사용."
    },
    "Company.topics": {
        "aicontext": "LLM이 가용 topic 목록을 파악하는 데 사용\n분석 범위 결정 시 참조",
        "capabilities": "docs/finance/report 모든 source의 topic을 하나의 DataFrame으로 통합\nchapter 순서대로 정렬, 각 topic의 블록 수/기간 수/최신 기간 표시\n어떤 데이터가 있는지 한눈에 파악",
        "guide": "\"어떤 데이터가 있어?\" → c.topics\n\"topic 목록\" → c.topics",
        "kind": "property",
        "requires": "데이터: docs/finance/report 중 하나 이상 (자동 다운로드)",
        "seeAlso": "show: 특정 topic 데이터 조회\nsections: topic x period 전체 지도 (topics보다 상세)\nindex: 전체 구조 메타데이터 목차",
        "summary": "topic별 요약 DataFrame -- 전체 데이터 지도."
    },
    "Company.trace": {
        "aicontext": "데이터 출처 신뢰도 판단 — finance > report > docs 우선순위 확인\n분석 결과의 근거 투명성 확보",
        "capabilities": "topic별 데이터 출처 확인 (docs, finance, report)\n출처 선택 이유 (우선순위, fallback 경로)\n각 출처별 데이터 행 수, 기간 수, 커버리지",
        "guide": "\"이 데이터 어디서 온 거야?\" → c.trace(\"BS\")\n\"데이터 출처 확인\" → c.trace(topic)",
        "kind": "method",
        "requires": "데이터: docs + finance + report (보유한 것만 추적)",
        "seeAlso": "show: topic 데이터 조회 (trace로 출처 확인 후 열람)\nsources: 3개 source 전체 가용 현황",
        "summary": "topic 데이터의 출처(docs/finance/report)와 선택 근거 추적."
    },
    "Company.update": {
        "aicontext": "데이터 최신성 유지에 활용 — 분석 전 자동 갱신 트리거 가능",
        "capabilities": "DART API로 최신 공시 확인 후 누락분만 수집\n카테고리별 선택 수집",
        "guide": "\"최신 공시 반영해줘\" → c.update()\n\"데이터 업데이트\" → c.update()로 증분 수집",
        "kind": "method",
        "requires": "API 키: DART_API_KEY",
        "seeAlso": "filings: 현재 보유 공시 목록 확인\ndisclosure: OpenDART 전체 공시 조회",
        "summary": "누락된 최신 공시를 증분 수집."
    },
    "Company.view": {
        "aicontext": "시각적 탐색 인터페이스 — 사용자가 브라우저에서 직접 데이터 탐색",
        "capabilities": "로컬 서버 기반 공시 뷰어 실행\n브라우저에서 sections/index 탐색",
        "guide": "\"공시 뷰어 열어줘\" → c.view()\n\"브라우저에서 보기\" → c.view()",
        "kind": "method",
        "requires": "데이터: HuggingFace docs parquet (자동 다운로드)",
        "seeAlso": "index: 뷰어가 소비하는 메타데이터 (프로그래밍 접근)\nsections: 뷰어의 원본 데��터",
        "summary": "브라우저에서 공시 뷰어를 엽니다."
    },
    "Company.watch": {
        "aicontext": "공시 변화 중요도 자동 평가 — 분석 우선순위 결정에 활용\n텍스트 변화량 + 재무 영향 통합 스코어",
        "capabilities": "전체 topic 변화 중요도 스코어링\n텍스트 변화량 + 재무 영향 통합 평가\n특정 topic 상세 변화 내역",
        "guide": "\"뭐가 크게 바뀌었어?\" → c.watch()\n\"리스크 관련 변화\" → c.watch(\"riskManagement\")",
        "kind": "method",
        "requires": "데이터: docs (자동 다운로드)",
        "seeAlso": "diff: 줄 단위 상세 변경 비교 (watch보다 세밀)\nkeywordTrend: 키워드 빈도 추이",
        "summary": "공시 변화 감지 — 중요도 스코어링 기반 변화 요약."
    },
    "Company.workforce": {
        "aicontext": "인력 효율성/근무환경 정량 평가 — 1인당 매출, 급여 수준 비교\n시장 횡단 비교로 인적자원 경쟁력 판단",
        "capabilities": "직원수 + 정규직/비정규직 비율\n평균 급여 + 1인당 매출\n평균 근속연수\n시장 전체 인력 횡단 비교",
        "guide": "\"직원 현황\" → c.workforce()\n\"평균 급여는?\" → c.workforce()\n\"전체 상장사 인력 비교\" → c.workforce(\"all\")",
        "kind": "method",
        "requires": "데이터: DART 정기보고서 (자동 수집)",
        "seeAlso": "governance: 이사회/감사위원 구성 (인력의 다른 관점)\nshow: c.show(\"employee\")로 docs 기반 직원 상세",
        "summary": "인력/급여 분석 (직원수, 평균급여, 근속연수)."
    },
    "Fred": {
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
    "Review": {
        "aicontext": "review 수퍼툴이 이 클래스의 기능을 AI에게 노출.\nblocks action으로 블록 카탈로그, section으로 섹션별 리뷰.",
        "capabilities": "buildReview(company): 템플릿 기반 전체 리뷰 자동 생성 (2부 14축)\nReview([blocks...]): 블록 자유 조립 (맞춤 보고서)\nReview(stockCode=..., sections=[...]): 직접 구성\nrender(fmt): rich/html/markdown/json 4종 렌더링\ntoHtml(), toMarkdown(), toJson() 편의 메서드\nJupyter/Colab/Marimo 자동 HTML 렌더링 (_repr_html_)",
        "guide": "\"분석 보고서 보여줘\" -> c.review() 또는 buildReview(company)\n\"수익구조만 보고 싶어\" -> c.review(\"수익구조\")\n\"HTML로 내보내기\" -> review.toHtml()\n\"블록 목록 보여줘\" -> blocks(company) (카탈로그 테이블)\n\"매출 성장률 블록만\" -> b = blocks(c); b[\"growth\"]",
        "kind": "class",
        "requires": "Company 객체 (buildReview 사용 시) 또는 Block 리스트.",
        "seeAlso": "analysis: 14축 전략분석 엔진 (Review의 데이터 공급원)\nblocks: 블록 사전 (한글/영문/tab-complete)\nCompany.review: Company에서 바로 호출",
        "summary": "분석 리뷰 — 14축 전략분석 결과를 구조화 보고서로 렌더링."
    },
    "SelectResult": {
        "kind": "class",
        "summary": "select() 반환 객체 — DataFrame 위임 + 체이닝."
    },
    "analysis": {
        "kind": "module",
        "summary": "Analysis 엔진 — L2 분석 모듈 통합."
    },
    "ask": {
        "capabilities": "자연어로 기업/시장 분석 (종목은 질문 텍스트에서 AI 가 자동 감지)\n스트리밍 출력 (기본) / 배치 반환 / Generator 직접 제어\n원본 검증 · 가정 조정 · 업종 비교 전부 AI 자율",
        "guide": "\"삼성전자 수익성 분석\" -> dartlab.ask(\"삼성전자 수익성 분석해줘\")\n\"삼성 vs SK하이닉스\" -> dartlab.ask(\"삼성전자와 SK하이닉스 비교\")\n\"반도체 업황\" -> dartlab.ask(\"반도체 업황 어때\")  (종목 불필요)",
        "kind": "function",
        "requires": "AI: provider 설정 (dartlab.setup() 참조)",
        "seeAlso": "Company: 원본 데이터 조회 (show/select)\nscan: 전종목 비교 (프로그래밍)",
        "summary": "AI 에게 질문. AI 가 모든 엔진(analysis/scan/macro/credit/gather/search)을 tool 로 다룬다."
    },
    "capabilities": {
        "aicontext": "AI가 \"dartlab에 뭐가 있는지\" 모를 때 탐색용.\ncapabilities() → 목차 확인 → capabilities(\"analysis\") → 상세 확인 → execute_code.\ncapabilities(search=\"재무건전성\") → 질문 관련 API 검색 → 코드 생성.",
        "capabilities": "CAPABILITIES dict에서 부분 조회 가능.\nkey 없이 호출 시 전체 키 목록(summary 포함) 반환.\nkey 지정 시 해당 항목의 상세(guide, capabilities, seeAlso 등) 반환.\nsearch 지정 시 자연어 질문 기반 관련 API 검색 (상위 10개).",
        "guide": "\"dartlab 뭐 할 수 있어?\" -> capabilities()\n\"분석 기능 뭐 있어?\" -> capabilities(\"analysis\")\n\"scan 어떻게 써?\" -> capabilities(\"scan\")\n\"재무건전성 관련 API?\" -> capabilities(search=\"재무건전성\")",
        "kind": "function",
        "requires": "없음",
        "seeAlso": "ask: AI 질문 (capabilities로 기능 파악 후 ask로 분석)\nsetup: AI provider 설정 (capabilities 확인 후 설정)",
        "summary": "dartlab 전체 기능 카탈로그 조회."
    },
    "codeToName": {
        "kind": "function",
        "summary": "종목코드 → 회사명."
    },
    "collect": {
        "aicontext": "사용자가 특정 종목의 최신 데이터를 직접 수집할 때 사용.",
        "capabilities": "종목별 DART 공시 데이터 직접 수집 (finance, docs, report)\n멀티키 병렬 수집 (DART_API_KEYS 쉼표 구분)\n증분 수집 — 이미 있는 데이터는 건너뜀\n카테고리별 선택 수집",
        "guide": "\"데이터 수집해줘\" -> DART_API_KEY 필요. dartlab.setup(\"dart-key\", \"YOUR_KEY\")로 설정 안내\n\"삼성전자 재무 데이터 수집\" -> collect(\"005930\", categories=[\"finance\"])\n보안: 키는 로컬 .env에만 저장, 외부 전송 절대 없음",
        "kind": "function",
        "requires": "API 키: DART_API_KEY",
        "seeAlso": "Company: 수집된 데이터로 Company 생성하여 분석\nsearch: 종목코드 모를 때 먼저 검색",
        "summary": "지정 종목 DART 데이터 수집 (OpenAPI)."
    },
    "collectAll": {
        "capabilities": "전체 상장종목 DART 공시 데이터 일괄 수집\n미수집 종목만 선별 수집 (mode=\"new\") 또는 전체 재수집 (mode=\"all\")\n멀티키 병렬 수집 (DART_API_KEYS 쉼표 구분)\n카테고리별 선택 (finance, docs, report)",
        "guide": "\"전종목 데이터 수집\" -> collectAll() 안내. DART_API_KEY 필요\n\"재무 데이터만 수집\" -> collectAll(categories=[\"finance\"])\n보안: 키는 로컬 .env에만 저장, 외부 전송 절대 없음",
        "kind": "function",
        "requires": "API 키: DART_API_KEY",
        "seeAlso": "collect: 특정 종목만 수집\ndownloadAll: HuggingFace 사전구축 데이터 (API 키 불필요, 더 빠름)",
        "summary": "전체 상장종목 DART 데이터 일괄 수집."
    },
    "config": {
        "kind": "module",
        "summary": "dartlab 전역 설정."
    },
    "credit": {
        "kind": "function",
        "summary": "신용등급 산출 단일 진입점."
    },
    "dataDir": {
        "kind": "module",
        "summary": "str(object='') -> str"
    },
    "downloadAll": {
        "capabilities": "HuggingFace 사전 구축 데이터 일괄 다운로드\nfinance (~600MB, 2700+종목), docs (~8GB, 2500+종목), report (~320MB, 2700+종목)\n이어받기/병렬 다운로드 지원 (huggingface_hub)\n전사 분석(scanAccount, governance, digest 등)에 필요한 데이터 사전 준비",
        "guide": "\"데이터 어떻게 받아?\" -> downloadAll(\"finance\") 안내. API 키 불필요\n\"scan 쓰려면?\" -> downloadAll(\"finance\") + downloadAll(\"report\") 필요\nfinance 먼저 (600MB), report 다음 (320MB), docs는 대용량 주의 (8GB)",
        "kind": "function",
        "requires": "없음 (HuggingFace 공개 데이터셋)",
        "seeAlso": "scan: 다운로드된 데이터로 전종목 비교\ncollect: DART API로 직접 수집 (최신 데이터, API 키 필요)",
        "summary": "HuggingFace에서 전체 시장 데이터 다운로드."
    },
    "gather": {
        "aicontext": "ask()/chat()에서 주가/수급/거시 데이터를 컨텍스트로 주입 가능\n기업 분석 시 시장 데이터 보충 자료로 활용",
        "capabilities": "price: OHLCV 시계열 (KR Naver/US Yahoo, 기본 1년, 최대 6000거래일)\nflow: 외국인/기관 수급 동향 (KR 전용, Naver)\nmacro: ECOS(KR 12개) / FRED(US 25개) 거시지표 시계열\nnews: Google News RSS 뉴스 수집 (최근 30일)\nsector: 업종 분류 (KR KIND+Naver)\ninsider: 내부자 거래 (KR DART)\nownership: 기관/외국인 지분 보유 (KR Naver)\npeers: 동종업종 피어 종목 (시총 포함, KR Naver)\n자동 fallback 체인, circuit breaker, TTL 캐시",
        "guide": "\"주가 추이 보여줘\" -> gather(\"price\", \"005930\")\n\"외국인 매매 동향\" -> gather(\"flow\", \"005930\")\n\"금리 추이 알려줘\" -> gather(\"macro\", \"BASE_RATE\") 또는 gather(\"macro\", \"FEDFUNDS\")\n\"최근 뉴스 찾아줘\" -> gather(\"news\", \"삼성전자\")\n\"업종 알려줘\" -> gather(\"sector\", \"005930\")\n\"내부자 거래 보여줘\" -> gather(\"insider\", \"005930\")\n\"지분 보유 현황\" -> gather(\"ownership\", \"005930\")\n\"동종업종 비교\" -> gather(\"peers\", \"005930\")\n\"미국 거시지표 전체\" -> gather(\"macro\", market=\"US\") 또는 gather(\"US\")\n주가+수급은 scan과 다름. scan은 재무 기반 횡단, gather는 시장 실시간.",
        "kind": "function",
        "requires": "price/flow/news: 없음 (공개 API)\nmacro: API 키 — ECOS_API_KEY (KR) 또는 FRED_API_KEY (US)",
        "seeAlso": "scan: 재무 기반 전종목 횡단분석 (거버넌스, 현금흐름 등)\nCompany: 개별 종목 공시/재무 데이터\nanalysis: 14축 전략분석 (재무비율, 수익구조 등)",
        "summary": "외부 시장 데이터 통합 수집 — 8축, 전부 Polars DataFrame."
    },
    "gather.flow": {
        "capabilities": "외국인/기관 매매 동향 (KR 전용)",
        "kind": "gather_axis",
        "summary": "수급"
    },
    "gather.insider": {
        "capabilities": "임원/주요주주 주식 거래 — KR(DART) / US(Yahoo)",
        "kind": "gather_axis",
        "summary": "내부자거래"
    },
    "gather.macro": {
        "capabilities": "ECOS(KR 12개) / FRED(US 25개) 거시 시계열",
        "kind": "gather_axis",
        "summary": "거시지표"
    },
    "gather.news": {
        "capabilities": "Google News RSS — 최근 30일",
        "kind": "gather_axis",
        "summary": "뉴스"
    },
    "gather.ownership": {
        "capabilities": "기관/외국인 보유 현황",
        "kind": "gather_axis",
        "summary": "지분"
    },
    "gather.peers": {
        "capabilities": "같은 업종 내 피어 종목 목록 (시총 포함)",
        "kind": "gather_axis",
        "summary": "피어"
    },
    "gather.price": {
        "capabilities": "OHLCV 시계열 (기본 1년) — Naver/Yahoo/FMP fallback",
        "kind": "gather_axis",
        "summary": "주가"
    },
    "gather.sector": {
        "capabilities": "업종 분류 — KR(KIND+Naver) / US(Yahoo)",
        "kind": "gather_axis",
        "summary": "업종"
    },
    "industry": {
        "kind": "function",
        "summary": "산업 매퍼엔진 진입점."
    },
    "listing": {
        "kind": "function",
        "summary": "목록 조회 단일 진입점."
    },
    "macro": {
        "kind": "function",
        "summary": "시장 레벨 매크로 분석 엔진 — 6막 인과 서사."
    },
    "macro.assets": {
        "capabilities": "5대 자산 심층 해석 + Cu/Au + BEI 4분면",
        "kind": "macro_axis",
        "summary": "자산"
    },
    "macro.corporate": {
        "capabilities": "전종목 이익사이클 + Ponzi비율 + 레버리지",
        "kind": "macro_axis",
        "summary": "기��집계"
    },
    "macro.crisis": {
        "capabilities": "Credit-to-GDP gap + GHS + Minsky + 역사적 맥락",
        "kind": "macro_axis",
        "summary": "위기"
    },
    "macro.cycle": {
        "capabilities": "경제 사이클 4국면 ��별 + 전환 시퀀스 감지",
        "kind": "macro_axis",
        "summary": "사이클"
    },
    "macro.forecast": {
        "capabilities": "LEI + Cleveland Fed 침체확률 + Sahm + Hamilton RS + GaR",
        "kind": "macro_axis",
        "summary": "예측"
    },
    "macro.inventory": {
        "capabilities": "ISM 재고순환 4국면 + 자산���분 바로미터",
        "kind": "macro_axis",
        "summary": "��고"
    },
    "macro.liquidity": {
        "capabilities": "M2 + 연준 B/S + NFCI + 자체 FCI",
        "kind": "macro_axis",
        "summary": "��동성"
    },
    "macro.rates": {
        "capabilities": "금리 방향 + 고용/물가 + 수익률곡선 + 기간프리미엄",
        "kind": "macro_axis",
        "summary": "금리"
    },
    "macro.scenario": {
        "capabilities": "역사적 충격 재현 + 유형별 스트레스 (110개 프리셋)",
        "kind": "macro_axis",
        "summary": "시��리오"
    },
    "macro.sentiment": {
        "capabilities": "공포탐욕 근사 + VIX 구간 + JLN 실물 불확실���",
        "kind": "macro_axis",
        "summary": "심���"
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
        "summary": "회사명 → 종목코드. 정확히 일치하는 첫 번째 결과."
    },
    "pastInsight": {
        "kind": "function",
        "summary": "특정 회사의 과거 분석 서사 조회."
    },
    "quant": {
        "kind": "function",
        "summary": "종목 레벨 정량분석 엔진 — 30축 7그룹."
    },
    "scan": {
        "kind": "function",
        "summary": "시장 전체 횡단분석 통합 엔트리포인트."
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
        "aicontext": "공시를 찾을 때 사용. 공시 유형명으로 찾으면 제목 검색, 내용으로 찾으면 본문 검색.\nscope 지정 없이 자동 판별.",
        "capabilities": "제목 검색: 공시 유형명/섹션 제목에서 매칭 (\"유상증자\", \"대표이사 변경\")\n본문 검색: 사업보고서 등 본문에서 개념 매칭 (\"반도체 HBM 투자\", \"환율 리스크\")\n종목/기간 필터 지원\nDART 공시 뷰어 링크 포함 (dartUrl 컬럼)",
        "guide": "\"유상증자 한 회사?\" -> search(\"유상증자\")\n\"반도체 투자 트렌드?\" -> search(\"반도체 HBM 투자\")",
        "kind": "function",
        "requires": "데이터: stemIndex (scope=title) + contentIndex (scope=content)",
        "seeAlso": "Company: 종목코드/회사명으로 Company 생성\nlisting: 전체 상장법인 목록",
        "summary": "공시 검색. *(alpha)*"
    },
    "searchName": {
        "kind": "function",
        "summary": "종목명/코드로 종목 찾기 (KR + US)."
    },
    "sectorInsights": {
        "kind": "function",
        "summary": "동종 업계 과거 분석 서사 목록 (교차 학습)."
    },
    "setup": {
        "aicontext": "AI 분석 기능 사용 전 provider 설정 상태 확인\n미설정 provider 감지 시 setup() 안내로 연결\n설정 완료 여부를 프로그래밍 방식으로 체크 가능",
        "capabilities": "전체 AI provider 설정 현황 테이블 표시\nprovider별 대화형 설정 (키 입력 → .env 저장)\nChatGPT OAuth 브라우저 로그인\nOpenAI/Gemini/Groq/Cerebras/Mistral API 키 설정\nOllama 로컬 LLM 설치 안내",
        "guide": "\"AI 설정 어떻게 해?\" -> setup()으로 전체 현황 확인\n\"ChatGPT 연결하고 싶어\" -> setup(\"chatgpt\")\n\"OpenAI 키 등록\" -> setup(\"openai\")\n\"Ollama 어떻게 써?\" -> setup(\"ollama\")",
        "kind": "function",
        "requires": "없음",
        "seeAlso": "ask: AI 질문 (setup 완료 후 사용)\nchat: AI 대화 (setup 완료 후 사용)\nllm.configure: 프로그래밍 방식 provider 설정",
        "summary": "AI provider 설정 안내 + 인터랙티브 설정."
    },
    "topdown": {
        "kind": "function",
        "summary": "`dartlab.topdown(...)` 를 callable로 노출."
    },
    "verbose": {
        "kind": "module",
        "summary": "bool(x) -> bool"
    }
}
