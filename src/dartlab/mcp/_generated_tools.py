"""MCP 도구 정의 — 자동 생성.

수정하지 마세요. scripts/build/generateSpec.py 를 실행하세요.
"""

# fmt: off

_STOCK = {"type": "string", "description": "종목코드 (005930) 또는 회사명 (삼성전자)"}

TOOLS: list[dict] = [
    {"name": 'companyInsights', "description": '[먼저 사용] 7영역 등급 (A~F) + 투자 프로파일 + 핵심 서사.', "params": {'stockCode': '_STOCK'}, "required": ['stockCode']},
    {"name": 'searchCompany', "description": '한국 상장기업 검색. 종목코드(005930), 회사명(삼성전자), 부분검색(삼성) 가능.', "params": {'query': {'type': 'string', 'description': '검색어'}}, "required": ['query']},
    {"name": 'companyFinancials', "description": '재무제표 원본 조회. IS(손익), BS(재무상태), CF(현금흐름), CIS(포괄손익), SCE(자본변동).', "params": {'stockCode': '_STOCK', 'statement': {'type': 'string', 'enum': ['IS', 'BS', 'CF', 'CIS', 'SCE']}}, "required": ['stockCode', 'statement']},
    {"name": 'companyRatios', "description": '재무비율 55개 시계열. ROE, ROA, 부채비율, 영업이익률, PER, PBR 등.', "params": {'stockCode': '_STOCK'}, "required": ['stockCode']},
    {"name": 'companyAnalysis', "description": '14축 재무 심층 분석. 축: 수익구조, 안정성, 성장성, 현금흐름, 자금조달, 자산구조, 수익성, 효율성, 이익품질, 비용구조, 자본배분, 투자효율, 재무정합성, 종합평가', "params": {'stockCode': '_STOCK', 'axis': {'type': 'string', 'enum': ['수익구조', '안정성', '성장성', '현금흐름', '자금조달', '자산구조', '수익성', '효율성', '이익품질', '비용구조', '자본배분', '투자효율', '재무정합성', '종합평가', 'financial', 'valuation', 'forecast'], 'description': '축명 (단축형) 또는 그룹명'}, 'sub': {'type': 'string', 'description': '그룹 내 하위 축 (예: financial→수익성, valuation→가치평가)'}}, "required": ['stockCode']},
    {"name": 'companyValuation', "description": '종합 밸류에이션 (DCF + DDM + 상대가치 + RIM).', "params": {'stockCode': '_STOCK'}, "required": ['stockCode']},
    {"name": 'companyForecast', "description": '매출 예측 (Base/Bull/Bear 시나리오).', "params": {'stockCode': '_STOCK'}, "required": ['stockCode']},
    {"name": 'companyShow', "description": '공시 토픽 원문 조회. companyTopics로 목록 확인.', "params": {'stockCode': '_STOCK', 'topic': {'type': 'string', 'description': '토픽명'}}, "required": ['stockCode', 'topic']},
    {"name": 'companyTopics', "description": '이 기업에서 조회 가능한 공시 토픽 목록.', "params": {'stockCode': '_STOCK'}, "required": ['stockCode']},
    {"name": 'companyDiff', "description": '기간간 공시 텍스트 변경 비교.', "params": {'stockCode': '_STOCK', 'topic': {'type': 'string', 'description': '토픽명 (생략 시 전체)'}}, "required": ['stockCode']},
    {"name": 'companyGovernance', "description": '지배구조 분석 (사외이사, 감사위원, 최대주주 지분율).', "params": {'stockCode': '_STOCK'}, "required": ['stockCode']},
    {"name": 'companyAudit', "description": '감사 리스크 (감사의견, 감사인 변경, 계속기업 불확실성).', "params": {'stockCode': '_STOCK'}, "required": ['stockCode']},
    {"name": 'companyProfile', "description": '기업 기본 정보 (회사명, 업종, 시장, 대표자).', "params": {'stockCode': '_STOCK'}, "required": ['stockCode']},
    {"name": 'companySections', "description": '전체 데이터 구조 지도 (topic x period).', "params": {'stockCode': '_STOCK'}, "required": ['stockCode']},
    {"name": 'companyReview', "description": '정리된 종합 보고서 (11 reportType). 섹션: 수익구조, 안정성, 성장성, 현금흐름, 자금조달, 자산구조, 수익성, 효율성, 이익품질, 비용구조, 자본배분, 투자효율, 재무정합성, 종합평가, 가치평가, 지배구조, 공시변화, 비교분석, 매출전망', "params": {'stockCode': '_STOCK', 'section': {'type': 'string', 'enum': ['수익구조', '안정성', '성장성', '현금흐름', '자금조달', '자산구조', '수익성', '효율성', '이익품질', '비용구조', '자본배분', '투자효율', '재무정합성', '종합평가', '가치평가', '지배구조', '공시변화', '비교분석', '매출전망'], 'description': '특정 섹션만 (생략 시 전체 보고서)'}, 'type': {'type': 'string', 'enum': ['full', 'executive', 'credit', 'valuation', 'growth', 'crisis', 'audit', 'dividend', 'governance', 'macro', 'thesis'], 'description': 'reportType (생략 시 full)'}}, "required": ['stockCode']},
    {"name": 'companyCredit', "description": '독립 신용등급 분석 (7축). 채무상환, 자본구조, 유동성, 현금흐름, 사업안정성, 재무신뢰성, 공시리스크.', "params": {'stockCode': '_STOCK', 'axis': {'type': 'string', 'enum': ['등급', '채무상환', '자본구조', '유동성', '현금흐름', '사업안정성', '재무신뢰성', '공시리스크', 'grade', 'repayment', 'leverage', 'liquidity', 'cashflow', 'business', 'reliability', 'disclosure'], 'description': '축명 (생략 시 종합 등급)'}}, "required": ['stockCode']},
    {"name": 'companyGather', "description": '종목별 시장 데이터. 주가(price), 수급(flow), 뉴스(news).', "params": {'stockCode': '_STOCK', 'axis': {'type': 'string', 'enum': ['price', 'flow', 'news']}}, "required": ['stockCode', 'axis']},
    {"name": 'companyQuant', "description": '종목 기술적 분석. 축: indicators, signals, verdict, momentum, volatility, regime, pattern, beta...', "params": {'stockCode': '_STOCK', 'metric': {'type': 'string', 'description': '분석 축'}}, "required": ['stockCode']},
    {"name": 'companyFilings', "description": '개별 종목 공시 목록.', "params": {'stockCode': '_STOCK', 'topK': {'type': 'integer', 'description': '최대 건수 (기본 10)'}}, "required": ['stockCode']},
    {"name": 'marketScan', "description": '전종목 횡단분석. 20축: governance, workforce, capital, debt, account, ratio, network, cashflow...', "params": {'axis': {'type': 'string', 'enum': ['governance', 'workforce', 'capital', 'debt', 'account', 'ratio', 'network', 'cashflow', 'audit', 'insider', 'quality', 'liquidity', 'growth', 'profitability', 'efficiency', 'valuation', 'dividendTrend', 'macroBeta', 'screen', 'disclosureRisk'], 'description': '분석 축'}}, "required": ['axis']},
    {"name": 'macroAnalysis', "description": '경제 거시분석 (Company 불필요). 11축: cycle(사이클), rates(금리), assets(자산), sentiment(심리), liquidity(유동성), forecast(예측), crisis(위기), inventory(재고), corporate(기업집계), trade(교역), summary(종합)', "params": {'axis': {'type': 'string', 'enum': ['cycle', 'rates', 'assets', 'sentiment', 'liquidity', 'forecast', 'crisis', 'inventory', 'corporate', 'trade', 'summary'], 'description': '분석 축'}}, "required": []},
    {"name": 'gatherData', "description": '외부 시장 데이터 수집. 8축: price, flow, macro, news, sector, insider, ownership, peers', "params": {'axis': {'type': 'string', 'enum': ['price', 'flow', 'macro', 'news', 'sector', 'insider', 'ownership', 'peers'], 'description': '데이터 축'}, 'target': {'type': 'string', 'description': '종목코드 또는 지표명'}}, "required": []},
    {"name": 'quantAnalysis', "description": '기술적/정량 분석. 29축.', "params": {'stockCode': '_STOCK', 'metric': {'type': 'string', 'enum': ['indicators', 'signals', 'verdict', 'momentum', 'volatility', 'regime', 'pattern', 'beta', 'factor', 'tailrisk', 'residual', 'liquidity', 'flow', 'volume', 'divergence', 'quality', 'value', 'earnings', 'sentiment', 'toneChange', 'eventSignal', 'riskText', 'governanceQuant', 'ranking', 'pairs', 'screen', 'meanvar', 'riskparity', 'allocation'], 'description': '분석 축'}}, "required": ['stockCode']},
    {"name": 'topdownScreen', "description": '사이클 → 추천 섹터 → 종목 후보 자동 선별.', "params": {'market': {'type': 'string', 'enum': ['KR', 'US']}, 'topN': {'type': 'integer', 'description': '섹터당 종목 수 (기본 5)'}}, "required": []},
    {"name": 'dartlabSearch', "description": '공시 원문 검색 (stem ID 역인덱스).', "params": {'query': {'type': 'string', 'description': '검색어'}, 'corp': {'type': 'string', 'description': '종목코드 필터'}}, "required": ['query']},
    {"name": 'dartlabListing', "description": '상장 종목, 공시 목록, 토픽 목록 조회.', "params": {'kind': {'type': 'string', 'enum': ['companies', 'filings', 'topics']}, 'corp': {'type': 'string', 'description': 'filings 시 종목코드 필터'}}, "required": ['kind']},
    {"name": 'pastInsight', "description": '종목별 과거 분석 서사 조회 (블로그 + AI 응답 누적). strengths/weaknesses/direction/archetype 포함.', "params": {'stockCode': '_STOCK'}, "required": ['stockCode']},
    {"name": 'sectorInsights', "description": '섹터/산업 과거 분석 누적 — 산업별 인사이트, peer 비교 단서.', "params": {'sector': {'type': 'string', 'description': '섹터/산업 이름 (예: 반도체, semiconductor)'}}, "required": ['sector']},
    {"name": 'industryMap', "description": '산업지도 조회 — 34개 산업 × 공정 노드/엣지. 종목 없이 산업 단위 분석 가능.', "params": {'industry': {'type': 'string', 'description': '산업 ID (semiconductor, battery, auto 등). 생략 시 전체 가이드'}, 'stage': {'type': 'string', 'description': '공정 단계 (design, fab, equipment 등 — 산업별 상이)'}}, "required": []},
    {"name": 'capabilities', "description": "dartlab 자체 기능 안내 — '뭐야', '어떻게 써'. path 주면 특정 API 상세.", "params": {'path': {'type': 'string', 'description': "API 경로 (예: 'Company.show', 'dartlab.scan'). 생략 시 전체 목록"}}, "required": []},
]

TOOL_FEATURE_MAP: dict[str, str] = {
    "companyInsights": "ai",
    "searchCompany": "data",
    "companyFinancials": "data",
    "companyRatios": "data",
    "companyAnalysis": "data",
    "companyValuation": "data",
    "companyForecast": "data",
    "companyShow": "data",
    "companyTopics": "data",
    "companyDiff": "data",
    "companyGovernance": "data",
    "companyAudit": "data",
    "companyProfile": "data",
    "companySections": "data",
    "companyReview": "ai",
    "companyCredit": "data",
    "companyGather": "data",
    "companyQuant": "data",
    "companyFilings": "data",
    "marketScan": "data",
    "macroAnalysis": "data",
    "gatherData": "data",
    "quantAnalysis": "data",
    "topdownScreen": "data",
    "dartlabSearch": "data",
    "dartlabListing": "data",
    "pastInsight": "ai",
    "sectorInsights": "ai",
    "industryMap": "data",
    "capabilities": "meta",
    "listDartlabApi": "meta",
    "searchDartlabApi": "meta",
    "verifyDartlabApi": "meta",
}

# fmt: on
