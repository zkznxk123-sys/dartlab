# dartlab Capabilities

> v0.10.3 기준 자동 생성. 직접 수정 금지.  
> `uv run python src/dartlab/skills/generateSpec.py`로 재생성.


---

## Python API (31개)

`import dartlab` 후 사용 가능한 공개 API.

| 이름 | 종류 | 설명 |
|------|------|------|
| `Company` | function | **사람의 최상위 관문** — 종목 하나의 모든 엔진에 접근하는 파사드. |
| `Fred` | class | FRED 경제지표 facade. |
| `OpenDart` | class | OpenDART API 통합 클라이언트. |
| `OpenEdgar` | class | SEC public API facade. |
| `config` | module | dartlab 전역 설정. |
| `ask` | function | LLM 에게 dartlab 컨텍스트로 질문 — dartlab.ai.kernel.ask wrapper. |
| `help` | function | dartlab 공개 API 검색 — 자연어 query 매칭 9 섹션 docstring (T10-4). |
| `setup` | function | AI provider 설정 안내 + 인터랙티브 설정. |
| `search` | function | 공시 검색. **⚠ BETA — AI 사용 비권장**. |
| `listing` | function | 목록 조회 단일 진입점. |
| `collect` | function | 지정 종목 DART 데이터 수집 (OpenAPI). |
| `collectAll` | function | 전체 상장종목 DART 데이터 일괄 수집. |
| `downloadAll` | function | HuggingFace에서 전체 시장 데이터 다운로드. |
| `scan` | function | 시장 전체 횡단분석 통합 엔트리포인트 — L1.5 횡단 엔진. |
| `analysis` | function | Analysis 엔진 — L2 분석 모듈 통합. |
| `gather` | function | 외부 시장 데이터 통합 수집 — 8축, 전부 Polars DataFrame. |
| `quant` | function | 종목 레벨 정량분석 엔진 — 31축 7그룹. |
| `credit` | function | 신용등급 산출 단일 진입점. |
| `macro` | function | 시장 레벨 매크로 분석 엔진 — 6막 인과 서사. |
| `industry` | function | 산업 매퍼엔진 — 데이터 주도 산업지도. |
| `verbose` | module | bool(x) -> bool |
| `dataDir` | module | str(object='') -> str |
| `codeToName` | function | 종목코드 → 회사명. |
| `nameToCode` | function | 회사명 → 종목코드. 정확히 일치하는 첫 번째 결과. |
| `searchName` | function | 종목명/코드로 종목 찾기 (KR + US). |
| `pastInsight` | function | 종목별 과거 분석 인사이트 조회. |
| `sectorInsights` | function | 섹터별 과거 분석 인사이트 조회. |
| `Story` | class | 보고서 조합기 — 6 엔진 블록을 조합하여 6막 구조화 보고서 생성. |
| `SelectResult` | class | select() 반환 객체 — DataFrame 위임 + 체이닝. |
| `ChartResult` | class | chart() 반환 객체 — 시각화 + 렌더링. |
| `capabilities` | function | dartlab 전체 기능 카탈로그 조회. |

### Python API 상세

#### Company
**Capabilities:** 종목 파사드 하나로 엔진 전수 접근: analysis · credit · quant · macro ·
industry · gather · show. 엔진 이름만 기억하면 됨.
종목코드 ("005930"), 회사명 ("삼성전자"), 영문 ticker ("AAPL") 모두 지원
canHandle() 체인: provider priority 순 자동 라우팅 (DART → EDGAR)
새 국가 추가 시 이 파일 수정 불필요 — provider 패키지만 추가
핵심 인터페이스: show(topic) / index / trace(topic) / diff() / select()
모든 데이터 접근은 ``c.show(topic)`` 으로 통합 — finance topic
(BS·IS·CF·CIS·SCE·ratios) 도 ``c.show("BS")`` · ``c.show("IS", freq="Y")``
처럼 호출. 별도 namespace property 나 바로가기는 사용하지 않는다
(``c.docs / c.finance / c.report / c.profile`` · ``c.BS / c.IS / c.CF /
c.CIS / c.ratios / c.timeseries`` 는 Plan v10 에서 제거).
메타: sections, topics, filings(), market, currency
**Requires:** DART: 사전 다운로드 데이터 (dartlab.downloadAll() 또는 자동 다운로드).
EDGAR: 인터넷 연결 (On-demand 수집).
**AIContext:** AI 는 `dartlab.ask()` 로 접근 (Company 를 직접 생성하지 않음).
사람은 Company 객체 하나로 노트북·스크립트에서 모든 엔진 호출.
엔진은 사람의 분석엔진이자 AI 의 skill (docstring SSOT) — 한 파일 두 역할.
**Guide:** AI 역할: AI는 Company를 단일 종목 분석의 라우터로 보고 대상 식별, 사용 가능한 topic, 하위 엔진 선택을 정한다.
데이터 기본기: Company 경로는 target, provider(DART/EDGAR), topic,
source, period 를 먼저 고정하고, 이 원자료 ref 를 analysis · credit ·
story 같은 응용 엔진으로 넘긴다.
Handoff: 최신 주가/뉴스/거시 원자료가 필요하면 gather 로 보강하고,
peer/rank/universe 비교가 필요하면 scan 으로 넘어간다.
"삼성전자 재무제표" -> c = Company("005930"); c.show("IS")
"사업 개요 보여줘" -> c.show("businessOverview")
"어떤 데이터 있어?" -> c.index 또는 c.topics
"출처 추적" -> c.trace("revenue")
"기간 변화" -> c.diff()
"종합평가" -> c.analysis("financial", "종합평가")
"스토리 보고서" -> c.story()
"Apple 분석" -> Company("AAPL") (자동 EDGAR 라우팅)
**SeeAlso:** dartlab.ask: AI 대화 (투톱 다른 관문)
search: 종목 검색 (종목코드 모를 때)
scan: 전종목 횡단분석 (Company-독립)
macro: 시장 레벨 거시 (Company-독립)
industry: 섹터 밸류체인 (Company-독립)

#### help
**Capabilities:** dartlab.__all__ 안 모든 심볼의 docstring 첫 줄 + 이름을 자연어 query 토큰
과 substring 매칭하여 관련 API 5 개 (또는 limit) 를 score 순서로 반환.
**Requires:** dartlab 패키지가 import 가능해야 한다. lazy import 패턴이라 순환 import
회피.
**AIContext:** 외부 LLM / 신규 사용자의 *어디서 시작?* 질문에 답하는 진입점. T8-2 의
핵심. README "세 가지 시작점" 의 3 분기 중 자연어 진입을 보강.
**Guide:** 결과가 0 이면 query 토큰을 줄여 재시도. 정확한 API 모를 때는
``dartlab.help("")`` 로 전체 ``__all__`` 둘러보기 가능. CLI 등가 명령:
``dartlab help <query>``.
**SeeAlso:** dartlab.ask: 자연어 질문 → AI 워크벤치 답변 + ref
dartlab.plugins.listPlugins: 외부 plugin 목록 (T5-5)
dartlab.skills.readSkill: Skill OS 257 노드 검색

#### setup
**Capabilities:** 전체 AI provider 설정 현황 테이블 표시
provider별 대화형 설정 (키 입력 → .env 저장)
ChatGPT OAuth 브라우저 로그인
OpenAI/Gemini/Groq/Cerebras/Mistral API 키 설정
Ollama 로컬 LLM 설치 안내
**Requires:** 없음
**AIContext:** AI 분석 기능 사용 전 provider 설정 상태 확인
미설정 provider 감지 시 setup() 안내로 연결
설정 완료 여부를 프로그래밍 방식으로 체크 가능
**Guide:** "AI 설정 어떻게 해?" -> setup()으로 전체 현황 확인
"ChatGPT 연결하고 싶어" -> setup("chatgpt")
"OpenAI 키 등록" -> setup("openai")
"Ollama 어떻게 써?" -> setup("ollama")
**SeeAlso:** ask: AI 질문 (setup 완료 후 사용)
chat: AI 대화 (setup 완료 후 사용)
llm.configure: 프로그래밍 방식 provider 설정

#### search
**Capabilities:** 제목 검색: 공시 유형명/섹션 제목에서 매칭 ("유상증자", "대표이사 변경")
본문 검색: 사업보고서 등 본문에서 개념 매칭 ("반도체 HBM 투자", "환율 리스크")
종목/기간 필터 지원
DART 공시 뷰어 링크 포함 (dartUrl 컬럼)
**Requires:** 데이터: stemIndex (scope=title) + contentIndex (scope=content)
**AIContext:** BETA — 우선 사용 비권장. 단일 종목 공시는 Company.disclosure/liveFilings 우선.
search 호출 후 0건이면 즉시 fallback (재호출/키워드 변형 round 낭비 금지).
**Guide:** "유상증자 한 회사?" -> search("유상증자") [BETA, 0건이면 stop]
"반도체 투자 트렌드?" -> search("반도체 HBM 투자") [BETA, 0건이면 stop]
"삼성전자 최근 공시" -> Company("005930").disclosure() (search 아님)
**SeeAlso:** Company: 종목코드/회사명으로 Company 생성
listing: 전체 상장법인 목록

#### collect
**Capabilities:** 종목별 DART 공시 데이터 직접 수집 (finance, docs, report)
멀티키 병렬 수집 (DART_API_KEYS 쉼표 구분)
증분 수집 — 이미 있는 데이터는 건너뜀
카테고리별 선택 수집
**Requires:** API 키: DART_API_KEY
**AIContext:** 사용자가 특정 종목의 최신 데이터를 직접 수집할 때 사용.
**Guide:** "데이터 수집해줘" -> DART_API_KEY 필요. dartlab.setup("dart-key", "YOUR_KEY")로 설정 안내
"삼성전자 재무 데이터 수집" -> collect("005930", categories=["finance"])
보안: 키는 로컬 .env에만 저장, 외부 전송 절대 없음
**SeeAlso:** Company: 수집된 데이터로 Company 생성하여 분석
search: 종목코드 모를 때 먼저 검색

#### collectAll
**Capabilities:** 전체 상장종목 DART 공시 데이터 일괄 수집
미수집 종목만 선별 수집 (mode="new") 또는 전체 재수집 (mode="all")
멀티키 병렬 수집 (DART_API_KEYS 쉼표 구분)
카테고리별 선택 (finance, docs, report)
**Requires:** API 키: DART_API_KEY
**Guide:** "전종목 데이터 수집" -> collectAll() 안내. DART_API_KEY 필요
"재무 데이터만 수집" -> collectAll(categories=["finance"])
보안: 키는 로컬 .env에만 저장, 외부 전송 절대 없음
**SeeAlso:** collect: 특정 종목만 수집
downloadAll: HuggingFace 사전구축 데이터 (API 키 불필요, 더 빠름)

#### downloadAll
**Capabilities:** HuggingFace 사전 구축 데이터 일괄 다운로드
finance (~600MB), docs (~8GB), report (~320MB) — 전 상장사 범위
이어받기/병렬 다운로드 지원 (huggingface_hub)
전사 분석(scanAccount, governance, digest 등)에 필요한 데이터 사전 준비
**Requires:** 없음 (HuggingFace 공개 데이터셋)
**Guide:** "데이터 어떻게 받아?" -> downloadAll("finance") 안내. API 키 불필요
"scan 쓰려면?" -> downloadAll("finance") + downloadAll("report") 필요
finance 먼저 (600MB), report 다음 (320MB), docs는 대용량 주의 (8GB)
**SeeAlso:** scan: 다운로드된 데이터로 전종목 비교
collect: DART API로 직접 수집 (최신 데이터, API 키 필요)

#### analysis
**Guide:** AI 역할: AI는 analysis를 단일 기업 재무·가치·리스크 해석 엔진으로 보고 axis/subaxis와 필요한 재무 evidence를 선택한다.

진입점 패턴: ``Company.analysis(axis)`` 또는 sub-module (``analysis.financial`` ·
``analysis.valuation`` 등) 직접 import.

#### gather
**Capabilities:** price: OHLCV 시계열 (KR Naver/US Yahoo, 기본 1년, 최대 6000거래일)
flow: 외국인/기관 수급 동향 (KR 전용, Naver)
macro: ECOS(KR) / FRED(US) 거시지표 시계열 (기본 HF 벌크)
news: Google News RSS 뉴스 수집 (최근 30일)
sector: 업종 분류 (KR KIND+Naver)
insider: 내부자 거래 (KR DART)
ownership: 기관/외국인 지분 보유 (KR Naver)
peers: 동종업종 피어 종목 (시총 포함, KR Naver)
자동 fallback 체인, circuit breaker, TTL 캐시
**Requires:** price/flow/news: 없음 (공개 API)
macro: 불필요 — apiKey 명시 시 ECOS/FRED 직접 API 호출
**AIContext:** ask()/chat()에서 주가/수급/거시 데이터를 컨텍스트로 주입 가능
기업 분석 시 시장 데이터 보충 자료로 활용
**Guide:** "주가 추이 보여줘" -> gather("price", "005930")
"외국인 매매 동향" -> gather("flow", "005930")
"금리 추이 알려줘" -> gather("macro", "BASE_RATE") 또는 gather("macro", "FEDFUNDS")
"최근 뉴스 찾아줘" -> gather("news", "삼성전자")
"업종 알려줘" -> gather("sector", "005930")
"내부자 거래 보여줘" -> gather("insider", "005930")
"지분 보유 현황" -> gather("ownership", "005930")
"동종업종 비교" -> gather("peers", "005930")
"미국 거시지표 전체" -> gather("macro", market="US") 또는 gather("US")
주가+수급은 scan과 다름. scan은 재무 기반 횡단, gather는 시장 실시간.
**SeeAlso:** scan: 재무 기반 전종목 횡단분석 (거버넌스, 현금흐름 등)
Company: 개별 종목 공시/재무 데이터
analysis: 14축 전략분석 (재무비율, 수익구조 등)

#### credit
**Capabilities:** DART/EDGAR 공시 재무제표만으로 dCR 독립 신용등급을 산출하는 단일 진입점. 무인자 호출 시
가이드, stockCode 만 호출 시 종합 등급, axis 지정 시 해당 축만 반환. 79 개사 검증 대기업
87% / 중대형 82% 정확도. 외부 API 키 불필요.
**Requires:** L1 raw: DART 정기보고서 (자동 다운로드) 또는 EDGAR 10-K/10-Q
L1.5 frame: 재무제표 가공 frame
**AIContext:** AI 가 회사 부도 위험 / 재무 건전성 평가 진입점. axes 7 개 score 와 grade 종합 인용.
시점 단정보다 "정기보고서 마감 후 30~45 일 시차" 단서 권장.

Parameters
stockCode : str | None
종목코드 또는 ticker. None이면 7축 가이드 DataFrame 반환.
axis : str | None
축 이름 ("등급" → 종합, "채무상환"/"자본구조"/"유동성"/"현금흐름"/
"사업안정성"/"재무신뢰성"/"공시리스크" → 해당 축만).
영문 alias("repayment", "leverage" 등)도 지원.
detail : bool
True이면 7축 상세 + 모든 지표 시계열 + 서사(narrative) 포함.
basePeriod : str | None
분석 기준 기간 (예: "2024"). None이면 최신.
**Guide:** AI 역할: AI는 credit을 상환능력·재무건전성 판단 엔진으로 보고 부채, 현금흐름, 이자보상, 만기 근거를 요구한다.
When: 종목의 부도 위험·재무 건전성을 독립 평가할 때.
How: credit 단독으로 종합 등급 확인 → analysis(안정성, 현금흐름) 와 함께 심층 진단.
story credit 타입이 credit + analysis(안정성) + analysis(현금흐름) + analysis(자금조달) 순서로 조합.
Verified:
credit 단독 → dCR 등급 + 7축 위험점수 + PD 추정 (observed via ai-ask, 2026-04-25 — 정식 Phase P 판정 아님)
credit + analysis(안정성,현금흐름) → 부도 위험 종합 진단 (observed via ai-ask, 2026-04-25 — 정식 Phase P 판정 아님)
**SeeAlso:** analysis : 재무 심층 분석 — 안정성·현금흐름 축이 credit 과 상호 보완.
scan : 전종목 재무건전성 비교.

#### codeToName
**Requires:** ``getKindList()`` 캐시 가용 — 첫 호출 시 KIND HTTP fetch.
**SeeAlso:** nameToCode : 역방향 — 회사명 → 코드.
resolver.codeToName : Protocol 위임 진입점.

#### nameToCode
**Requires:** ``getKindList()`` 캐시 가용 + 사용자 입력이 KIND 목록과 *정확* 일치.
**SeeAlso:** codeToName : 역방향 — 코드 → 회사명.
fuzzy.searchName : 부분 일치 + 자모 분해 검색.
resolver.nameToCode : Protocol 위임 진입점.

#### pastInsight
**Guide:** AI 답변 루프는 generated spec 검색 후 engine_call을 통해 호출한다.
**SeeAlso:** sectorInsights

#### sectorInsights
**Guide:** AI 답변 루프는 generated spec 검색 후 engine_call을 통해 호출한다.
**SeeAlso:** pastInsight

#### Story
**Guide:** AI 역할: AI는 story를 검증된 engine output을 보고서 섹션으로 조립하는 엔진으로 보고 원자료 없이 새 claim을 만들지 않는다.
When: 종목의 종합 분석 보고서가 필요할 때.
How: 11 타입 중 선택 — full(전체), executive(경영진 요약), credit(신용),
valuation(가치평가), growth(성장), crisis(위기), audit(감사),
dividend(배당), governance(지배구조), macro(매크로), thesis(투자논제).
Verified:
credit 타입 → credit + analysis(안정성,현금흐름,자금조달) 조합 (observed via ai-ask, 2026-04-25 — 정식 Phase P 판정 아님)
audit 타입 → analysis(이익품질,재무정합성) + 감사의견 (observed via ai-ask, 2026-04-25 — 정식 Phase P 판정 아님)
governance 타입 → analysis(지배구조,공시변화) (observed via ai-ask, 2026-04-25 — 정식 Phase P 판정 아님)
dividend 타입 → analysis(수익구조,현금흐름,자본배분) (observed via ai-ask, 2026-04-25 — 정식 Phase P 판정 아님)
valuation 타입 → analysis(가치평가) + quant (observed via ai-ask, 2026-04-25 — 정식 Phase P 판정 아님)
thesis 타입 → macro + analysis 복합 근거 수집 (observed via ai-ask, 2026-04-25 — 정식 Phase P 판정 아님)
**SeeAlso:** analysis : 재무 심층 분석 — story 의 주요 데이터 공급원.
credit : 신용 분석 — story credit 타입의 핵심 엔진.
scan : 전종목 비교 — 동종업계 비교 블록 제공.
quant : 기술적 분석 — 가격 기반 신호 블록 제공.
macro : 거시 분석 — 매크로 환경 블록 제공.

#### ChartResult
**Guide:** AI 역할: AI는 ChartResult/viz를 이미 검증된 표를 시각 설명으로 바꾸는 엔진으로 보고 단일값·무근거 차트를 만들지 않는다.
When: SelectResult나 DataFrame 기반 근거를 차트로 설명해야 할 때.
How: 표의 기간/series/value 근거가 충분한지 먼저 확인하고, chart() 결과의 spec을 최종 답변 ref와 연결한다.

#### capabilities
**Capabilities:** CAPABILITIES dict에서 부분 조회 가능.
key 없이 호출 시 전체 키 목록(summary 포함) 반환.
key 지정 시 해당 항목의 상세(guide, capabilities, seeAlso 등) 반환.
search 지정 시 자연어 질문 기반 관련 API 검색 (상위 10개).
**Requires:** 없음
**AIContext:** AI가 "dartlab에 뭐가 있는지" 모를 때 탐색용.
capabilities() → 목차 확인 → capabilities("analysis") → 상세 확인 → execute_code.
capabilities(search="재무건전성") → 질문 관련 API 검색 → 코드 생성.
**Guide:** "dartlab 뭐 할 수 있어?" -> capabilities()
"분석 기능 뭐 있어?" -> capabilities("analysis")
"scan 어떻게 써?" -> capabilities("scan")
"재무건전성 관련 API?" -> capabilities(search="재무건전성")
**SeeAlso:** ask: AI 질문 (capabilities로 기능 파악 후 ask로 분석)
setup: AI provider 설정 (capabilities 확인 후 설정)

---

## CLI (18개 명령)

`dartlab <command>` 형태로 사용.

| 명령 | 설명 |
|------|------|
| `show` | topic 기반 데이터 조회 |
| `search` | 종목코드/회사명 검색 |
| `statement` | 재무제표 출력 (BS/IS/CIS/CF/SCE) |
| `sections` | docs 수평화 sections 출력 |
| `profile` | Company index/facts 출력 |
| `modules` | 사용 가능한 데이터 모듈 목록 |
| `ask` | 자연어 원스톱 분석 |
| `report` | Markdown 분석 보고서 생성 |
| `excel` | 기업 데이터 Excel 내보내기 |
| `story` | 기업 분석 스토리 (사람이 읽는 보고서) |
| `collect` | DART/EDGAR 데이터 수집 |
| `update` | 로컬 데이터를 HuggingFace 최신으로 갱신 |
| `ai` | 분석 웹 인터페이스 실행 |
| `channel` | 외부 공유 채널 (DevTunnels 기본, 모바일 호환) |
| `status` | 모델 연결 상태 확인 |
| `setup` | 모델 provider/API 키 설정 |
| `mcp` | MCP 서버 실행 (stdio) |
| `plugin` | 플러그인 관리 (list/create) |

---

## Server API (98개 엔드포인트)

FastAPI `/api/*` 엔드포인트. 모든 클라이언트의 단일 소비 경로.

| Method | Path | 설명 |
|--------|------|------|
| POST | `/runs` | Run the DartLab research agent through the public AG-UI event stream. |
| GET | `/api/status` | LLM provider 상태 확인 (설치/인증/모델 포함). |
| GET | `/api/suggest` | 회사 데이터 상태에 맞는 추천 질문 목록을 반환한다. |
| POST | `/api/provider/validate` | LLM provider 검증. 전역 상태는 변경하지 않는다. |
| POST | `/api/configure` | 구버전 alias. 현재는 provider 검증만 수행한다. |
| GET | `/api/ai/profile` | 공통 AI profile + provider catalog 반환. |
| PUT | `/api/ai/profile` | 공통 AI profile 갱신. |
| POST | `/api/ai/profile/secrets` | provider secret 저장/삭제. |
| POST | `/api/openapi/dart-key/validate` | OpenDART API 키 유효성만 검증한다. |
| PUT | `/api/openapi/dart-key` | 프로젝트 .env에 OpenDART API 키를 저장한다. |
| DELETE | `/api/openapi/dart-key` | 프로젝트 .env의 OpenDART API 키를 제거한다. |
| POST | `/api/channels/{platform}/start` | 외부 채널 어댑터 시작. |
| POST | `/api/channels/{platform}/stop` | 외부 채널 어댑터 정지. |
| GET | `/api/channel` | DevTunnels 모바일 접속 채널 상태를 반환한다. |
| POST | `/api/channel/start` | 현재 Web UI를 모바일에서 열 수 있는 DevTunnels 채널을 시작한다. |
| POST | `/api/channel/stop` | DevTunnels 채널을 종료한다. |
| GET | `/api/ai/profile/events` | profile 변경 SSE 스트림. |
| GET | `/api/models/{provider}` | Provider별 사용 가능한 모델 목록 — SDK/API 자동 조회, 실패시 fallback. |
| POST | `/api/codex/logout` | Codex CLI에 저장된 계정 인증을 제거한다. |
| GET | `/api/oauth/authorize` | ChatGPT OAuth 인증 시작 — 브라우저 로그인 URL 반환 + 로컬 콜백 서버 시작. |
| GET | `/api/oauth/status` | OAuth 인증 완료 여부 폴링. |
| POST | `/api/oauth/logout` | OAuth 토큰 제거. |
| POST | `/api/ollama/pull` | Ollama 모델 다운로드 (SSE 스트리밍 진행률). |
| GET | `/api/company/{code}/diff` | Company sections 전체 diff 요약. |
| GET | `/api/company/{code}/diff/matrix` | topic × period 변화 매트릭스 + 히트맵 스펙. |
| GET | `/api/company/{code}/diff/{topic}/summary` | 뷰어용 diff 요약 — changeRate + 최신 변경의 added/removed 미리보기. |
| GET | `/api/company/{code}/diff/{topic}` | Company 특정 topic의 두 기간 줄+글자 단위 diff. |
| GET | `/api/company/{code}/bridge/{topic}` | 텍스트-재무 숫자 교차 참조. |
| GET | `/api/company/{code}/topics/graph` | topic간 상호 참조 그래프. |
| GET | `/api/company/{code}/search` | 현재 회사의 sections 전체 텍스트에서 substring 검색. |
| GET | `/api/company/{code}/searchIndex` | MiniSearch 인덱스용 flat document list. |
| GET | `/api/company/{code}/modules` | 기업의 사용 가능한 데이터 모듈 목록. |
| POST | `/api/ask` | LLM 질문 — AI가 질문 의도를 자율 판단하고 종목/매크로/비교를 결정한다. |
| POST | `/api/company/{stockCode}/copilot` | landing/company 인라인 Copilot dock — citation-first 답변. |
| GET | `/api/ask/artifacts/{day}/{filename}` | AI tool_result 에서 생성된 CSV/JSON/JSONL 아티팩트를 내려준다. |
| GET | `/api/search` | 종목 검색 — 회사명 substring + KIND 주요제품 substring 합집합. 둘 다 0 이면 fuzzy. |
| GET | `/api/company/{code}/meta` | 회사 헤더 확장 메타 — corpName + 시장 + 섹터 + 제품 + 블로그 글. |
| GET | `/api/company/{code}` | 종목 기본 정보 + 사용 가능 API surface 목록. |
| GET | `/api/company/{code}/index` | 회사 데이터 구조 인덱스 DataFrame. |
| GET | `/api/company/{code}/sections` | merged topic x period 수평화 테이블. |
| GET | `/api/company/{code}/sections/raw` | raw XML 원본 — 모든 DART 태그 보존. viewer / parser 룰 변경 입력. |
| GET | `/api/company/{code}/init` | SPA 초기 로드용 번들 — toc + 첫 topic viewer + (옵션) diff 요약. |
| GET | `/api/company/{code}/toc` | 목차(TOC) — chapter/topic 트리 구조. |
| GET | `/api/company/{code}/viewer/{topic}` | 단일 topic의 viewer 데이터 — sections 블록 + 텍스트 문서. |
| GET | `/api/company/{code}/viewer2/{topic}` | sections 기반 신구대조 뷰어 — viewer() dict 반환. |
| POST | `/api/company/{code}/viewer/batch` | 여러 topic의 viewer 데이터를 한 번에 반환 — chapter 확장 시 N+1 제거. |
| GET | `/api/company/{code}/show/{topic}/all` | topic의 전 기간 viewer 블록 일괄 반환. |
| POST | `/api/company/{code}/show/{topic}/{block_idx}/parse` | 원문 테이블 블록을 구조화 DataFrame으로 파싱. |
| GET | `/api/company/{code}/show/{topic}` | topic payload 조회 — show(topic) API 대응. |
| GET | `/api/company/{code}/trace/{topic}` | source provenance 조회 — trace(topic) API 대응. |
| GET | `/api/company/{code}/summary/{topic}` | topic 데이터를 LLM으로 요약하여 SSE 스트리밍 반환. |
| GET | `/api/company/{code}/insights` | 7영역 인사이트 등급 (A~F) + 이상 징후. |
| GET | `/api/company/{code}/network` | 관계사 네트워크 그래프 — ego 중심 N-hop. |
| GET | `/api/company/{code}/scan/{axis}` | 6-Axis 스캔 단일 축 결과 + 시장 내 위치. |
| GET | `/api/company/{code}/scan/position` | 6-Axis 전체 포지션 요약 — 사전 빌드 스냅샷 기반. |
| GET | `/api/company/{code}/insights/unified` | 통합 인사이트 — 등급 + 스캔 + 피어 결합. |
| GET | `/filings` | 공시 목록 — HF 데이터 기반. |
| GET | `/company/{corp}` | 기업 기본 정보 — HF 데이터 기반. |
| GET | `/finance/{corp}` | 재무제표 — HF parquet 즉시 반환. |
| GET | `/show/{corp}/{topic}` | 공시 토픽 데이터 — HF parquet 즉시 반환. |
| GET | `/report/{corp}/{category}` | 보고서 (배당, 직원, 임원 등) — HF parquet 즉시 반환. |
| GET | `/scan/{axis}` | 전종목 횡단분석 — 프리빌드 parquet 즉시 반환. |
| GET | `/search` | 공시 원문 검색 — stemIndex 즉시 반환. |
| GET | `/listing` | 상장 종목/공시 목록. |
| GET | `/api/data/sources/{code}` | 경량 데이터 소스 목록 — registry 메타 + 파일 존재 여부만 확인 (빠름). |
| GET | `/api/data/preview/{code}/{module}` | 데이터 미리보기 — 모듈 데이터를 JSON으로 반환 (테이블/텍스트). |
| GET | `/api/data/stats` | 로컬 데이터 현황 — 문서/재무 파일 수, dartlab 버전. |
| GET | `/api/spec` | 시스템 스펙 조회 — LLM/MCP/외부 클라이언트용 (deprecated). |
| GET | `/api/export/modules/{code}` | Excel 내보내기 가능한 모듈 목록. |
| GET | `/api/export/sources/{code}` | 데이터 소스 디스커버리 — registry 기반 전체 소스 트리. |
| GET | `/api/export/templates` | 저장된 템플릿 목록 (프리셋 포함). |
| GET | `/api/export/templates/{template_id}` | 단일 템플릿 조회. |
| POST | `/api/export/templates` | 템플릿 저장 (신규 or 업데이트). |
| DELETE | `/api/export/templates/{template_id}` | 템플릿 삭제. |
| GET | `/api/export/excel/{code}` | Excel 파일 내보내기 — .xlsx 다운로드. |
| POST | `/call` | Capability dispatch — JSON-safe 직렬화 강행. |
| GET | `/capabilities` | Capability catalogue — registry 의 모든 public capability 명단. |
| GET | `/api/fred/series/{series_id}` | FRED 시계열 조회 + 변환. |
| GET | `/api/fred/search` | FRED 시리즈 검색. |
| GET | `/api/fred/compare` | 복수 시계열 비교. |
| GET | `/api/fred/catalog` | 주요 경제지표 카탈로그. |
| GET | `/api/fred/correlation` | 시계열 상관분석 + 선행/후행. |
| GET | `/price-events` | OHLCV + 일자별 events (disclosure + RSS news + GDELT news) + shocks + regime band. |
| POST | `/api/room/join` | 룸 참여 — member_id + 현재 상태 반환. |
| POST | `/api/room/leave` | 룸 퇴장. |
| POST | `/api/room/heartbeat` | 프레즌스 유지. |
| GET | `/api/room/state` | 현재 룸 상태. |
| GET | `/api/room/stream` | SSE 스트림 — 브로드캐스트 수신. |
| POST | `/api/room/ask` | 질문 → 전체 브로드캐스트. |
| POST | `/api/room/navigate` | 네비게이션 동기화. |
| POST | `/api/room/chat` | 채팅 메시지. |
| POST | `/api/room/react` | 이모지 반응. |
| GET | `/api/viz/catalog` | 등록된 카드 카탈로그 메타. |
| GET | `/api/viz/dashboard/{stockCode}` | 대시보드 카드 일괄 빌드 → recharts spec list. |
| GET | `/api/viz/tab/{tab}/{stockCode}` | 탭별 카드 일괄 빌드. financial 외 7 탭은 placeholder 또는 시계열 proxy. |
| GET | `/api/viz/spec/{cardKey}/{stockCode}` | 단일 카드 lazy 호출 — 회사 전환 시 일부 카드 refresh 용. |
| GET | `/api/viz/layout/{tab}/{stockCode}` | 탭 + 7 방법론 view → 12-col bento packed grid + 각 카드 spec. |
| GET | `/api/viz/layout-stream/{tab}/{stockCode}` | NDJSON streaming. layout → 완성 카드 순차 emit → done. |

---

## Data Modules (69개)

`core/registry.py` DataEntry 기반. 모듈 추가 = 한 줄 → 7곳 자동 반영.

### 시계열 재무제표 (finance)

| name | label | dataType | description |
|------|-------|----------|-------------|
| `annual.IS` | 손익계산서(연도별) | `timeseries` | 연도별 손익계산서 시계열. 매출액, 영업이익, 순이익 등 전체 계정. |
| `annual.BS` | 재무상태표(연도별) | `timeseries` | 연도별 재무상태표 시계열. 자산, 부채, 자본 전체 계정. |
| `annual.CF` | 현금흐름표(연도별) | `timeseries` | 연도별 현금흐름표 시계열. 영업/투자/재무활동 현금흐름. |
| `timeseries.IS` | 손익계산서(분기별) | `timeseries` | 분기별 손익계산서 standalone 시계열. |
| `timeseries.BS` | 재무상태표(분기별) | `timeseries` | 분기별 재무상태표 시점잔액 시계열. |
| `timeseries.CF` | 현금흐름표(분기별) | `timeseries` | 분기별 현금흐름표 standalone 시계열. |

### 공시 파싱 모듈 (report)

| name | label | dataType | description |
|------|-------|----------|-------------|
| `BS` | 재무상태표 | `dataframe` | K-IFRS 연결 재무상태표. finance XBRL 정규화(snakeId) 기반, 회사간 비교 가능. finance 없으면 docs fallback. |
| `IS` | 손익계산서 | `dataframe` | K-IFRS 연결 손익계산서. finance XBRL 정규화 기반. 매출액, 영업이익, 순이익 등 전체 계정 포함. |
| `CF` | 현금흐름표 | `dataframe` | K-IFRS 연결 현금흐름표. finance XBRL 정규화 기반. 영업/투자/재무활동 현금흐름. |
| `fsSummary` | 요약재무정보 | `dataframe` | DART 공시 요약재무정보. 다년간 주요 재무지표 비교. |
| `segments` | 부문정보 | `dataframe` | 사업부문별 매출·이익 데이터. 부문간 수익성 비교 가능. |
| `tangibleAsset` | 유형자산 | `dataframe` | 유형자산 변동표. 취득/처분/감가상각 내역. |
| `costByNature` | 비용성격별분류 | `dataframe` | 비용을 성격별로 분류한 시계열. 원재료비, 인건비, 감가상각비 등. |
| `dividend` | 배당 | `dataframe` | 배당 시계열. 연도별 DPS, 배당총액, 배당성향, 배당수익률. |
| `majorHolder` | 최대주주 | `dataframe` | 최대주주 지분율 시계열. 지분 변동은 경영권 안정성의 핵심 지표. |
| `employee` | 직원현황 | `dataframe` | 직원 수, 평균 근속연수, 평균 연봉 시계열. |
| `subsidiary` | 자회사투자 | `dataframe` | 종속회사 투자 시계열. 지분율, 장부가액 변동. |
| `bond` | 채무증권 | `dataframe` | 사채, CP 등 채무증권 발행·상환 시계열. |
| `shareCapital` | 주식현황 | `dataframe` | 발행주식수, 자기주식, 유통주식수 시계열. |
| `executive` | 임원현황 | `dataframe` | 등기임원 구성 시계열. 사내이사/사외이사/비상무이사 구분. |
| `executivePay` | 임원보수 | `dataframe` | 임원 유형별 보수 시계열. 등기이사/사외이사/감사 구분. |
| `audit` | 감사의견 | `dataframe` | 외부감사인의 감사의견과 감사보수 시계열. 적정 외 의견은 중대 위험 신호. |
| `boardOfDirectors` | 이사회 | `dataframe` | 이사회 구성 및 활동 시계열. 개최횟수, 출석률 포함. |
| `capitalChange` | 자본변동 | `dataframe` | 자본금 변동 시계열. 보통주/우선주 주식수·액면 변동. |
| `contingentLiability` | 우발부채 | `dataframe` | 채무보증, 소송 현황. 잠재적 재무 리스크 지표. |
| `internalControl` | 내부통제 | `dataframe` | 내부회계관리제도 감사의견 시계열. |
| `relatedPartyTx` | 관계자거래 | `dataframe` | 대주주 등과의 매출·매입 거래 시계열. 이전가격 리스크 확인. |
| `rnd` | R&D | `dataframe` | 연구개발비용 시계열. 기술 투자 강도 판단. |
| `sanction` | 제재현황 | `dataframe` | 행정제재, 과징금, 영업정지 등 규제 조치 이력. |
| `affiliateGroup` | 계열사 | `dataframe` | 기업집단 소속 계열회사 현황. 상장/비상장 구분. |
| `fundraising` | 증자감자 | `dataframe` | 유상증자, 무상증자, 감자 이력. |
| `productService` | 주요제품 | `dataframe` | 주요 제품/서비스별 매출액과 비중. |
| `salesOrder` | 매출수주 | `dataframe` | 매출실적 및 수주 현황. |
| `riskDerivative` | 위험관리 | `dataframe` | 환율·이자율·상품가격 리스크 관리. 파생상품 보유 현황. |
| `articlesOfIncorporation` | 정관 | `dataframe` | 정관 변경 이력. 사업목적 추가·변경으로 신사업 진출 파악. |
| `otherFinance` | 기타재무 | `dataframe` | 대손충당금, 재고자산 관련 기타 재무 데이터. |
| `companyHistory` | 연혁 | `dataframe` | 회사 주요 연혁 이벤트 목록. |
| `shareholderMeeting` | 주주총회 | `dataframe` | 주주총회 안건 및 의결 결과. |
| `auditSystem` | 감사제도 | `dataframe` | 감사위원회 구성 및 활동 현황. |
| `affiliate` | 관계기업투자 | `dataframe` | 관계기업/공동기업 투자 변동 시계열. 지분법손익, 기초/기말 장부가 포함. |
| `investmentInOther` | 타법인출자 | `dataframe` | 타법인 출자 현황. 투자목적, 지분율, 장부가 등. |
| `companyOverviewDetail` | 회사개요 | `dict` | 설립일, 상장일, 대표이사, 주소, 주요사업 등 기본 정보. |
| `holderOverview` | 주주현황 | `custom` | 5% 이상 주주, 소액주주 현황, 의결권 현황. majorHolder보다 상세한 주주 구성. |

### 서술형 공시 (disclosure)

| name | label | dataType | description |
|------|-------|----------|-------------|
| `business` | 사업의내용 | `text` | 사업보고서 '사업의 내용' 서술. 사업 구조와 현황 파악. |
| `companyOverview` | 회사개요정량 | `dict` | 공시 기반 회사 정량 개요 데이터. |
| `mdna` | MD&A | `text` | 이사의 경영진단 및 분석의견. 경영진 시각의 실적 평가와 전망. |
| `rawMaterial` | 원재료설비 | `dict` | 원재료 매입, 유형자산 현황, 시설투자 데이터. |
| `sections` | 사업보고서섹션 | `dataframe` | 사업보고서 전체 섹션 텍스트를 topic(행) × period(열) DataFrame으로 구조화. leaf title 기준 수평 비교 가능. 연간+분기+반기 전 기간 포함. |

### K-IFRS 주석 (notes)

| name | label | dataType | description |
|------|-------|----------|-------------|
| `notes.receivables` | 매출채권 | `dataframe` | K-IFRS 매출채권 주석. 채권 잔액 및 대손충당금 내역. |
| `notes.inventory` | 재고자산 | `dataframe` | K-IFRS 재고자산 주석. 원재료/재공품/제품 내역별 금액. |
| `notes.tangibleAsset` | 유형자산(주석) | `dataframe` | K-IFRS 유형자산 변동 주석. 토지, 건물, 기계 등 항목별 변동. |
| `notes.intangibleAsset` | 무형자산 | `dataframe` | K-IFRS 무형자산 주석. 영업권, 개발비 등 항목별 변동. |
| `notes.investmentProperty` | 투자부동산 | `dataframe` | K-IFRS 투자부동산 주석. 공정가치 및 변동 내역. |
| `notes.affiliates` | 관계기업(주석) | `dataframe` | K-IFRS 관계기업 투자 주석. 지분법 적용 내역. |
| `notes.borrowings` | 차입금 | `dataframe` | K-IFRS 차입금 주석. 단기/장기 차입 잔액 및 이자율. |
| `notes.provisions` | 충당부채 | `dataframe` | K-IFRS 충당부채 주석. 판매보증, 소송, 복구 등. |
| `notes.eps` | 주당이익 | `dataframe` | K-IFRS 주당이익 주석. 기본/희석 EPS 계산 내역. |
| `notes.lease` | 리스 | `dataframe` | K-IFRS 리스 주석. 사용권자산, 리스부채 내역. |
| `notes.segments` | 부문정보(주석) | `dataframe` | K-IFRS 부문정보 주석. 사업부문별 상세 데이터. |
| `notes.costByNature` | 비용의성격별분류(주석) | `dataframe` | K-IFRS 비용의 성격별 분류 주석. |

### 원본 데이터 (raw)

| name | label | dataType | description |
|------|-------|----------|-------------|
| `rawDocs` | 공시 원본 | `dataframe` | 공시 문서 원본 parquet. 가공 전 전체 테이블과 텍스트. |
| `rawFinance` | XBRL 원본 | `dataframe` | XBRL 재무제표 원본 parquet. 매핑/정규화 전 원본 데이터. |
| `rawReport` | 보고서 원본 | `dataframe` | 정기보고서 API 원본 parquet. 파싱 전 원본 데이터. |

### 분석 엔진 (analysis)

| name | label | dataType | description |
|------|-------|----------|-------------|
| `ratios` | 재무비율 | `ratios` | financeEngine이 자동계산한 수익성·안정성·밸류에이션 비율. |
| `insight` | 인사이트 | `custom` | 7영역 A~F 등급 분석 (실적, 수익성, 건전성, 현금흐름, 지배구조, 리스크, 기회). |
| `sector` | 섹터분류 | `custom` | WICS 11대 섹터 분류. 대분류/중분류 + 섹터별 파라미터. |
| `rank` | 시장순위 | `custom` | 전체 시장 및 섹터 내 매출/자산/성장률 순위. |
| `keywordTrend` | 키워드 트렌드 | `dataframe` | 공시 텍스트 키워드 빈도 추이 (topic × period × keyword). 54개 내장 키워드 또는 사용자 지정. |
| `news` | 뉴스 | `dataframe` | 최근 뉴스 수집 (KR: Google News 한국어, US: Google News 영어). 날짜/제목/출처/URL. |

---

## AI Tools (0개)

LLM 에이전트가 tool calling으로 사용하는 도구. priority 내림차순.

---


---

## Gather Axis (13개 축)

`dartlab.gather(axis, target)` 형태로 외부 시장 데이터 수집.

| 축 | 한글 | 설명 | target 필수 |
|----|------|------|------------|
| `price` | 주가 | OHLCV 시계열 (수정주가). KR: Naver, US: Yahoo. 기본 1년, 최대 6000거래일. 시장 지수 (KOSPI/KOSDAQ/KPI200) 도 자동 인식. | O |
| `flow` | 수급 | 외국인/기관 순매수 시계열 (KR 전용, Naver). | O |
| `macro` | 거시지표 | ECOS(KR) / FRED(US) 거시지표 시계열. 기본 HF 벌크 (apiKey 없음), apiKey 명시 시 ECOS/FRED 직접 API. | - |
| `news` | 뉴스 | Google News RSS 뉴스 수집 (기본 최근 30일). | O |
| `sector` | 업종 | 업종 분류 (KR KIND+Naver / US sectorCode). | O |
| `insider` | 내부자거래 | 내부자 (임원·주요주주) 거래 (KR DART · DART_API_KEY 필요). | O |
| `ownership` | 지분 보유 | 기관/외국인 지분 보유 현황 (KR Naver). | O |
| `peers` | 피어 | 동종업종 피어 종목 목록 (종목코드+시총). KR: KRX/네이버 | O |
| `krx` | KRX 회사별 시계열 | KOSPI/KOSDAQ 전종목 wide pivot — 행=stockCode+corpName, 열=일자. target (positional) 으로 raw OHLCV (close/open/high/low/volume/marketCap/...) 또는 보조지표 (rsi14/ma20/ema60/macd/atr14/obv/...) 28+ 디스패치. target='raw' 면 long (KRX 원본 컬럼). apiKey 없음 (기본): HF SSOT. apiKey 명시: KRX OpenAPI 직접. 환경변수 자동 read X. | - |
| `krxIndex` | KRX 지수 일별 매매현황 (시장군별 전체 지수 패키지) | KRX/KOSPI/KOSDAQ 시장군의 모든 지수 (종합/200/100/섹터/스타일/사이즈/ESG/테마) OHLCV + 거래량 + 시가총액. target=close/open/high/low/volume/marketCap/raw. indexFilter=[지수명] 으로 특정 지수 (예: 코스피 200 + 보조지표 자동). apiKey 없음 (기본): HF SSOT. apiKey 명시: KRX idx OpenAPI 직접. 직접 호출 시 idx 카테고리 권한 별도 신청 (sto 종목 키와 분리). | - |
| `narrative` | 뉴스 내러티브 archive | Phase A/B/C/D 통합 archive (RSS + GDELT) 진입. target 분기: None/'raw'=원본 archive, 'pulse'=date×topic 격자, 'score'=12 번째 macro 축 dict, 'topics'=top topic 랭킹, 6자리 코드=종목명 keyword 필터, 그 외 문자열=키워드 필터. days kwarg 기본 30 (start/end 미명시 시 today-days~today). asof PIT-safe. | - |
| `dartDoc` | DART 공시 원문 | 14자리 rcept_no 만으로 DART 공시 viewer 의 원문 본문 fetch (무인증). 공시 인덱스 페이지에서 sub-doc 목차를 받고 각 섹션 HTML 을 텍스트 (테이블 마크다운 보존) 로 변환. API key 불필요 — providers/dart/openapi (key 기반 OpenDART) 와 분리된 viewer 단건 fetch 진입점. | O |
| `calendar` | catalyst 일정 | 다가오는 정기공시 (사업/반기/분기보고서) due date 추론. 한국 fiscal cycle (FY=calendar year) 가정 + DART disclosure 시계열에서 last 보고서 → next due. P0: KR 정기공시만. AGM·만기·컨센서스·EDGAR 8-K 미포함 (P1+). API 키: DART_API_KEY (Company.disclosure 사용). | O |

**사용법:**

```python
import dartlab

dartlab.gather("price", "005930")   # 삼성전자 주가
dartlab.gather("flow", "005930")     # 수급 동향
dartlab.gather("macro")              # KR 거시지표 전체
dartlab.gather("news", "삼성전자")    # 뉴스
```

---


---

## Company (통합 facade)

입력을 자동 판별하여 DART 또는 EDGAR 시장 전용 Company를 생성한다.
현재 DART Company의 공개 진입점은 **index -> show(topic) -> trace(topic)** 이다.

```python
import dartlab

kr = dartlab.Company("005930")
kr = dartlab.Company("삼성전자")
us = dartlab.Company("AAPL")

kr.market                    # "KR"
us.market                    # "US"
```

### 판별 규칙

| 입력 | 결과 | 예시 |
|------|------|------|
| 6자리 숫자 | DART Company | `Company("005930")` |
| 한글 포함 | DART Company | `Company("삼성전자")` |
| 영문 1~5자리 | EDGAR Company | `Company("AAPL")` |


### Company 메서드/프로퍼티

DartCompany에서 동적 추출 (69개).

| 이름 | 종류 | 설명 |
|------|------|------|
| `analysis` | property | 재무제표 완전 분석 — 22축 (5 group), 6막 인과 구조. dual access (api-contract). |
| `ask` | method | LLM에게 이 기업에 대해 질문. |
| `audit` | method | 감사 리스크 종합 분석. |
| `calendar` | method | 다가오는 정기공시 catalyst 일정 추론 (Korea 시장). |
| `canHandle` | method | DART 종목코드(6자) 또는 한글 회사명이면 처리 가능. |
| `capital` | method | 주주환원 분석 (배당, 자사주, 총환원율). |
| `causalWeights` | method | 6막 인과 가중치 — 수익구조→수익성→현금흐름→자금조달→자산배치→가치평가 amplify/dampen/neutral. |
| `cleanupCache` | method | BoundedCache 전체 evict + cleanupBetweenCompanies 실행. |
| `codeName` | method | 종목코드 → 회사명 변환. |
| `contextSlices` | property | LLM 투입용 context slice DataFrame. |
| `credit` | property | dartlab 독립 신용평가 (dCR-AAA~D). 7축 — 채무상환/자본구조/유동성/현금흐름/사업안정성/재무신뢰성/공시리스크. |
| `currency` | property | 통화 코드 (DART 제공자는 항상 KRW). |
| `debt` | method | 부채 구조 분석 (차입금, 부채비율, 만기 구조). |
| `diff` | method | 기간간 텍스트 변경 비교. |
| `disclosure` | method | **[단일 종목 전용]** OpenDART 공시 목록 조회. **stockCode 필수**. |
| `executivePay` | method | 임원 보수 ≥ 5억 원 individual 공개 (자본시장법 §159, 2013-11-29 시행). |
| `facts` | property | topic × period 형태의 통합 facts 테이블 (sections + finance + report merge). |
| `filings` | method | 공시 문서 목록 + DART 뷰어 링크. |
| `fiscalYearEnd` | property | 회계연도 종료 월-일 (한국 종목은 12-31 표준). |
| `flow` | method | KRX 외국인/기관 일별 net-buy (Company.gather("flow") wrapper). |
| `gather` | method | 외부 시장 데이터 수집 — 4축 (price/flow/macro/news). |
| `governance` | method | 지배구조 분석 (이사회, 감사위원, 최대주주). |
| `index` | property | 현재 공개 Company 구조 인덱스 DataFrame -- 전체 데이터 목차. |
| `industry` | method | 이 회사의 밸류체인 산업 내 위치를 분석한다. |
| `keywordTrend` | method | 공시 텍스트 키워드 빈도 추이 (topic x period x keyword). |
| `listing` | method | KRX 전체 상장법인 목록 (KIND 기준). |
| `liveFilings` | method | OpenDART 기준 실시간 공시 목록 조회. |
| `macro` | method | 시장 매크로 (6막 인과 — 사이클/재고/기업/정책/유동성/심리/시나리오). KR 자동 위임. |
| `market` | property | 시장 코드 (DART 제공자는 항상 KR). |
| `memorySnapshot` | method | 캐시 size + 현 RSS snapshot. |
| `narrativeDiff` | method | 각 claim 제거 시 dFV 변화 — Thought Anchors 기반 정량 기여도. |
| `network` | method | 관계 네트워크 (지분출자 + 그룹 계열사 지도). |
| `news` | method | 최근 뉴스 수집. |
| `notesDetail` | method | K-IFRS 주석 세부항목 (리스 약정 · 우발채무 · 퇴직급여 가정 · 파생 등) 추출. |
| `priority` | method | 낮을수록 먼저 시도. DART=10 (기본 provider). |
| `quant` | property | 주가 기술적 분석 (31축). 기술지표/벤치마크/팩터/감성/최적화. dual access. |
| `rank` | property | 전체 시장 + 섹터 내 규모 순위 (매출/자산/성장률). |
| `rawDocs` | property | 공시 문서 원본 parquet 전체 (가공 전). |
| `rawFinance` | property | 재무제표 원본 parquet 전체 (가공 전). |
| `rawReport` | property | 정기보고서 원본 parquet 전체 (가공 전). |
| `readFiling` | method | 접수번호 또는 liveFilings row로 공시 원문을 읽는다. |
| `relatedPartyTx` | method | 관계자 거래 (RPT) — 공정거래법 §26 chaebol disclosure 100억 원 threshold (2024-01-01 시행). |
| `resolve` | method | 종목코드 또는 회사명 → 종목코드 변환. |
| `retrievalBlocks` | property | 원문 markdown 보존 retrieval block DataFrame. |
| `search` | method | 회사명 부분 검색 (KIND 목록 기준). |
| `sections` | property | sections — docs + finance + report 통합 지도. |
| `sectionsAs` | method | sections wide DataFrame — stripTags 파라미터로 cell value 양식 선택. |
| `sectionsLazy` | method | sections artifact LazyFrame — 메모리 한 자리 MB 달성 path. |
| `sectionsLong` | method | sections artifact long format read — period-sharded mmap parquet 직접 노출. |
| `sectionsRaw` | method | sections artifact mixed (모든 태그 + ALIGN/VALIGN 보존) wide DataFrame — viewer 전용. |
| `sectionsTables` | method | sections artifact ``content_table_struct`` 컬럼만 read — HTML 표 구조 SSOT. |
| `sector` | property | WICS 투자 섹터 분류 (KIND 업종 + 키워드 기반). |
| `sectorParams` | property | 현재 종목의 섹터별 밸류에이션 파라미터. |
| `select` | property | ``show()`` 결과에서 행/열 필터 — dual access proxy. |
| `show` | property | 원본 데이터 단일 진입점 — 재무제표 (BS/IS/CF/CIS) / 주석 / 공시 DataFrame. |
| `sources` | property | docs/finance/report 3개 source의 가용 현황 요약. |
| `status` | method | 로컬에 보유한 전체 종목 인덱스. |
| `story` | property | 5엔진 결과 조립 보고서 — 11 reportType × 7 template. 느림(60~80초). dual access. |
| `storyTree` | method | Damodaran 3P — possible(낙관)/plausible(중도)/probable(보수) 3 DCF + 민감도. |
| `table` | method | subtopic wide 셀의 markdown table을 구조화 DataFrame으로 파싱. |
| `topicSummaries` | method | 토픽별 요약 dict — AI가 경로 탐색에 사용. |
| `topics` | property | topic별 요약 DataFrame -- 전체 데이터 지도. |
| `trace` | method | topic 데이터의 출처 (docs/finance/report) 와 선택 근거 추적. |
| `update` | method | 누락된 최신 공시를 증분 수집. |
| `validateStory` | method | Damodaran 스토리 검증 — Possible / Plausible / Probable 3 테스트 통합. |
| `valuationImpact` | method | 인과 체인에서 DCF override 힌트 — narrative → 숫자 피드백. |
| `view` | method | 브라우저에서 공시 뷰어를 엽니다. |
| `watch` | method | 공시 변화 감지 — 중요도 스코어링 기반 변화 요약. |
| `workforce` | method | 인력/급여 분석 (직원수, 평균급여, 근속연수). |

### Company 메서드 상세

#### Company.analysis
**Capabilities:** 5 그룹 22 축 (financial 14 + valuation 1 + governance 3 + forecast 2 + macro 2) 개별
분석 dispatch dual-access. axis 미지정 시 카탈로그. self 자동 바인딩.
**Requires:** dartlab
polars
**AIContext:** workbench 분석 도구 entry — 축 미지정 호출로 capability 확인 후 정확 dispatch.
**Guide:** "분석해줘" → c.analysis() (가이드 반환)
"수익성" → c.analysis("financial", "수익성")
"가치평가" → c.analysis("valuation", "가치평가")
"override 재계산" → c.analysis("가치평가", overrides={"wacc": 9.0})

실제 동작은 ``_analysisImpl`` 참조.
**SeeAlso:** ``_analysisImpl`` — 실 dispatch (22 축 5 group).
``story`` — analysis 결과를 보고서로 합산.
``dartlab.analysis.financial.Analysis`` — backend SSOT.

#### Company.ask
**Capabilities:** 엔진 계산 결과를 컨텍스트로 조립하여 LLM에 전달
질문 분류 기반 분석 패키지 자동 선택 (financial, valuation, risk 등)
멀티 provider 지원 (openai, ollama, codex 등)
스트리밍 응답 지원
**Requires:** API 키: LLM provider API 키 (``OPENAI_API_KEY`` 등).
**AIContext:** AI가 분석 전 과정을 주도. dartlab 엔진(analysis, scan, gather 등)을
도구로 호출하여 데이터 수집, 계산, 판단, 해석을 수행.
**Guide:** "영업이익률 분석해줘" → c.ask("영업이익률 추세는?")
"AI한테 질문하고 싶어" → c.ask("질문")
"스트리밍으로 답변받기" → c.ask("질문", stream=True)
**SeeAlso:** chat: 에이전트 모드 (tool calling 기반 심화 분석)
ask: AI 종합 분석 (자연어 대화)
story: AI 없는 데이터 검토서

#### Company.audit
**Capabilities:** 감사의견 추이 (적정/한정/부적정/의견거절)
감사인 변경 이력 + 사유
계속기업 불확실성 플래그
핵심감사사항 (KAM) 추출
내부회계관리제도 검토의견
**Requires:** 데이터: docs + report (자동 다운로드)
**AIContext:** 감사 리스크 종합 평가 — 투자 의사결정의 핵심 안전장치
감사의견 변경, 계속기업 불확실성은 최고 경고 수준
**Guide:** "감사의견 확인" → c.audit()
"감사인 바뀌었어?" → c.audit()["auditorChanges"]
"계속기업 의문은?" → c.audit()["goingConcern"]
**SeeAlso:** governance: 지배구조 분석 (감사위원회 구성 포함)
insights: 종합 등급 (감사 리스크도 반영)
story: 재무정합성 섹션에서 감사 결과 활용

#### Company.calendar
**Capabilities:** 본 회사 disclosure history (최근 400 일 정기공시) → predictCalendar 위임 → 정기보고서
cycle 추론 (분기/반기/사업보고서 패턴). horizonDays 내 예상 공시일 리스트.
**Requires:** dartlab
polars
**AIContext:** AI 가 "다음 공시 catalyst" 답변 시 본 함수 결과 인용. 예상일 ± 며칠 명시 의무.
**Guide:** "다음 정기공시 언제" → 본 함수.
**SeeAlso:** ``dartlab.providers.dart.ops.calendar.predictCalendar`` — backend cycle 추론.
``edgar.Company.calendar`` — US 패리티 (현재 미구현 stub).

#### Company.canHandle
**Capabilities:** 6 자리 alphanumeric (KR stockCode) 또는 한글 (회사명) 매칭. EDGAR 의 5 자리 영문 ticker
와 disjoint — 라우터 정확 dispatch.
**Requires:** dartlab
polars
**AIContext:** Company 팩토리 내부. AI 가 직접 호출 X — Company() 가 자동 dispatch.
**Guide:** "DART 처리 가능 코드냐" → 본 함수.
**SeeAlso:** ``edgar.Company.canHandle`` — US ticker 패리티.
``priority`` — 라우터 정렬 SSOT.

#### Company.capital
**Capabilities:** 배당수익률 + 배당성향 추이
자사주 매입/소각 이력
총주주환원율 (배당 + 자사주)
시장 전체 주주환원 횡단 비교
**Requires:** 데이터: DART 정기보고서 (자동 수집)
**AIContext:** 주주환원 정책 평가 — 배당수익률/성향/자사주 정량 데이터
시장 횡단 비교로 상대적 환원 수준 판단
**Guide:** "배당 정보" → c.capital() 또는 c.show("dividend")
"주주환원율은?" → c.capital()
"전체 상장사 배당 비교" → c.capital("all")
**SeeAlso:** show: c.show("dividend")로 docs 기반 배당 상세
sceMatrix: 자본변동표 (배당/자사주가 자본에 미치는 영향)
debt: 부채 구조 (자본 정책의 다른 면)

#### Company.causalWeights
**Capabilities:** 6 막 (수익구조→수익성→현금흐름→자금조달→자산배치→가치평가) 의 인과 가중치 (amplify/
dampen/neutral) 계산. 매 막 출발/도착 지표 + delta + weight + direction.
**Requires:** dartlab
polars
**AIContext:** AI 가 "이 회사 핵심 인과 chain" 답변 시 본 함수 결과 인용 — 단일 지표가 아닌 chain 구조.
**Guide:** "인과 체인" → c.causalWeights()
"어느 막이 약해" → 결과의 direction='dampen' 필터
**SeeAlso:** ``valuationImpact`` — 본 가중치를 DCF override 로 변환.
``storyTree`` — 본 가중치 적용한 3 trajectory.
``dartlab.story.narrative.buildCausalWeights`` — implementation.

#### Company.cleanupCache
**Capabilities:** 인스턴스 ``self._cache`` (BoundedCache) 의 모든 entry evict + Polars 네이티브 힙
``cleanupBetweenCompanies`` 호출. KR multi-company loop 사이 회수.
**Requires:** dartlab
polars
**AIContext:** AI 가 다종목 batch (50+ 종목 분석) 안 본 함수 의무 호출. 누락 시 Rust heap 누적 OOM.
**Guide:** "다음 종목 진입 전 메모리 회수" → 본 함수 또는 ``with Company(c):`` 컨텍스트.
**SeeAlso:** ``memorySnapshot`` — 호출 전/후 RSS 비교.
``__exit__`` — context manager 종료 시 본 함수 자동 호출.
``dartlab.core.memory.cleanupBetweenCompanies`` — Polars Rust heap 회수.

#### Company.contextSlices
**Capabilities:** retrievalBlocks를 LLM 컨텍스트 윈도우에 맞게 슬라이싱
토큰 예산 내에서 최대한 많은 관련 정보를 담는 압축 포맷
topic/period 기준 우선순위 정렬
**Requires:** 데이터: docs (자동 다운로드)
**AIContext:** ask()/chat()의 시스템 프롬프트에 직접 주입되는 데이터
LLM이 소비하는 최종 형태의 컨텍스트
**Guide:** "LLM에 들어가는 컨텍스트" → c.contextSlices
"AI가 보는 데이터" → c.contextSlices
**SeeAlso:** retrievalBlocks: 슬라이싱 전 전체 retrieval 블록
ask: contextSlices를 내부적으로 소비하는 AI 질문 인터페이스

#### Company.credit
**Capabilities:** dartlab 독립 dCR 등급 (AAA→D 20 단계) dual-access. 7 축 (채무상환/자본구조/유동성/
현금흐름/사업안정성/재무신뢰성/공시리스크) 정량 합산. KIS/NICE 외부 등급과 비교 가능.
**Requires:** dartlab
polars
**AIContext:** 외부 신용평가 미상장 회사도 동일 척도. AI 가 부도위험 답변 시 본 결과 + analysis 결합.
**Guide:** "신용등급" → c.credit("등급")
"채무 감당되나" → c.credit("채무상환")
"전체 평가" → c.credit(detail=True)
"속성 접근" → c.credit.유동성()

실제 동작은 ``_creditImpl`` 참조.
**SeeAlso:** ``_creditImpl`` — 실 구현 (dCR 20 단계 + 7 축).
``analysis("financial", "안정성")`` — credit 보완 입력.
``story(preset="credit")`` — credit 결과 보고서 합성.

#### Company.debt
**Capabilities:** 총차입금 + 순차입금 규모
부채비율 + 차입금의존도
단기/장기 차입금 비율
시장 전체 부채 구조 횡단 비교
**Requires:** 데이터: DART 정기보고서 (자동 수집)
**AIContext:** 부채 구조/건전성 정량 평가 — 차입금 의존도, 만기 구조
시장 횡단 비교로 상대적 재무 안정성 판단
**Guide:** "부채 구조 분석" → c.debt()
"부채비율은?" → c.debt() 또는 c.show("ratios")
"전체 상장사 부채 비교" → c.debt("all")
**SeeAlso:** BS: 재무상태표 (부채 원본 데이터)
ratios: 재무비율 (부채비율 포함)
capital: 주주환원 (자본 정책의 다른 면)

#### Company.diff
**Capabilities:** 전체 topic 변경 요약 (변경량 스코어링)
특정 topic 기간별 변경 이력
두 기간 줄 단위 diff (추가/삭제/변경)
**Requires:** 데이터: docs (2개 이상 기간 필요)
**AIContext:** 기간간 공시 변경 감지 — 사업 방향 전환, 리스크 요인 변화 탐지
watch()보다 세밀한 줄 단위 변경 추적
**Guide:** "공시에서 뭐가 바뀌었어?" → c.diff()
"사업개요 변경 이력" → c.diff("businessOverview")
"2023 vs 2024 차이" → c.diff("businessOverview", "2023", "2024")
**SeeAlso:** watch: 변화 중요도 스코어링 (diff보다 요약적)
keywordTrend: 키워드 빈도 추이 (텍스트 변화의 다른 관점)
show: 특정 기간 원문 조회

Raises:
없음.

#### Company.disclosure
**Capabilities:** 전체 공시유형 조회 (정기, 주요사항, 발행, 지분, 외부감사 등)
기간, 유형, 키워드 필터링
최종보고서만 필터 (정정 이전 제외)
**Requires:** API 키: DART_API_KEY
**AIContext:** 특정 종목의 공시 빈도/유형 패턴 → 이벤트 감지
단일 종목 분석 시 최근 공시 컨텍스트 보강용
**Guide:** 단일 종목: "삼성전자 최근 공시 뭐 나왔어?" → c.disclosure(days=30)
전종목: "최근 어떤 회사들이 자사주 매입했어?" → dartlab.search("자기주식 취득")
**SeeAlso:** dartlab.search: **전종목 공시 검색 — 키워드 기반 (이 함수 대안)**
liveFilings: 실시간 최신 공시 (정규화된 포맷, 단일 종목)
readFiling: 공시 원문 텍스트 읽기
filings: 로컬 보유 공시 목록 (단일 종목)

#### Company.executivePay
**Capabilities:** 임원 보수 ≥ 5억 원 individual 공개 추출 (US proxy NEO-5 와 달리 *전원* 공개)
등기/미등기/퇴직 분리
급여/상여/주식매수선택권 행사이익/기타 근로소득/퇴직소득 분해
회사별 상위 보수 임원 list
**Requires:** DART 사업보고서 본문 (executivePay 섹션 자동 파싱).
**AIContext:** 한국 unique disclosure — US proxy 가 숨기는 미등기/퇴직 임원 보수 노출
산정기준 narrative 가 보수 메커니즘 추적 가능 (스톡옵션 행사 timing 등)
회사별 보수 top 1~3 의 직위 변경 = 인사 리스크 신호
**Guide:** "삼성전자 임원 보수" → c.executivePay()
"5억 이상 임원 명단" → c.executivePay().topPay
"퇴직 임원 보수" → c.executivePay().payByType.filter(구분="퇴직")
**SeeAlso:** governance: 이사회 구성 + 사외이사 비율
relatedPartyTx: 관계자 거래 (executive 와 회사 사이 거래)

#### Company.filings
**Capabilities:** 로컬에 보유한 공시 문서 목록
기간별, 문서유형별 정리
DART 뷰어 링크 포함
**Requires:** 데이터: docs (자동 다운로드)
**AIContext:** 어떤 공시가 보유돼 있는지 확인하여 분석 범위 결정에 활용
**Guide:** "이 회사 공시 목록 보여줘" → c.filings()
"어떤 보고서가 있어?" → c.filings()로 보유 문서 확인
**SeeAlso:** disclosure: OpenDART API 기반 실시간 공시 목록 (로컬 보유가 아닌 전체)
liveFilings: 최신 공시 실시간 조회
update: 누락 공시 증분 수집

#### Company.flow
**Capabilities:** 외국인 net-buy 일별
기관 net-buy 일별
개인 net-buy 일별
**Requires:** Naver flow API (KR 시장 한정). 외 시장 빈 결과.
**AIContext:** KOSPI/KOSDAQ 외국인 수급의 가장 중요한 daily signal
외국인 net-buy 누적 추세 + 기관 동조/역행 패턴이 단기 시세 driver
한국 unique — 외국인/기관/개인 종목별 일별 net-buy 가 공개 (US 시장은 없음)
**Guide:** "삼성전자 외국인 매수세" → c.flow()
"005930 기관 vs 외국인 추세" → c.flow()
"외국인 순매수 누적" → c.flow() + cumsum
**SeeAlso:** gather("flow") : 동일 본체 — flow axis 직접 호출
krx : KRX 시장 전체 axis (시장 평균과 비교)

#### Company.gather
**Capabilities:** price: OHLCV 주가 시계열 (KR Naver / US Yahoo)
flow: 외국인/기관 수급 동향 (KR 전용)
macro: ECOS(KR) / FRED(US) 거시지표 시계열 (기본 HF 벌크)
news: Google News RSS 뉴스 수집
자동 fallback 체인, circuit breaker, TTL 캐시
**Requires:** price/flow/news: 없음 (공개 API)
macro: 불필요 -- apiKey 명시 시 ECOS/FRED 직접 API 호출
**AIContext:** ask()/chat()에서 주가/수급/거시 데이터를 컨텍스트로 주입
기업 분석 시 시장 데이터 보충 자료로 활용
**Guide:** When: 주가·수급·거시지표·뉴스 원본 데이터가 필요할 때.
How: axis 로 데이터 종류 지정. 무인자 = 가이드.
"주가 데이터" → c.gather("price")
"외국인/기관 수급" → c.gather("flow")
"거시경제 지표" → c.gather("macro")
"뉴스 수집" → c.gather("news") 또는 c.news()
Verified:
gather("news") → 뉴스 목록 + 헤드라인 해석 (observed via ai-ask, 2026-04-25 — 정식 Phase P 판정 아님)
**SeeAlso:** news: 뉴스 전용 단축 메서드
ask: gather 데이터를 컨텍스트로 활용한 AI 분석

#### Company.governance
**Capabilities:** 사외이사 비율 + 감사위원회 구성
최대주주 지분율 + 특수관계인
시장 전체 거버넌스 횡단 비교
**Requires:** 데이터: DART 정기보고서 (자동 수집)
**AIContext:** 지배구조 리스크 평가 — 사외이사/감사위원/최대주주 정량 데이터
시장 횡단 비교로 상대적 거버넌스 수준 판단
**Guide:** "지배구조 분석" → c.governance()
"사외이사 비율은?" → c.governance()
"전체 상장사 거버넌스 비교" → c.governance("all")
**SeeAlso:** network: 출자/계열사 관계 (거버넌스의 다른 관점)
audit: 감사 리스크 (감사위원회와 연관)

#### Company.index
**Capabilities:** docs sections + finance + report 전체를 하나의 목차로 통합
각 항목의 chapter, topic, label, kind, source, periods, shape, preview 제공
sections 메타데이터 + 존재 확인만으로 구성 (파서 미호출, lazy)
viewer/렌더러가 소비하는 메타데이터 원천
**Requires:** 데이터: docs/finance/report 중 하나 이상 (자동 다운로드).
**AIContext:** LLM이 Company 전체 구조를 파악하는 핵심 진입점
ask()에서 어떤 데이터를 참조할지 결정하는 기초 정보
**Guide:** "전체 목차 보여줘" → c.index
"어떤 데이터가 있는지 구조적으로" → c.index
**SeeAlso:** topics: topic 단위 요약 (index보다 간결)
sections: 전체 sections 지도 (index의 원본)
profile: 통합 프로필 접근자

#### Company.industry
**Capabilities:** 회사의 산업 밸류체인 내 위치 (upstream/midstream/downstream/fab/equipment 등) 분류 +
같은 stage peer 종목코드 list 반환. sector vs industry 분리 — 후자는 가치사슬 차원.
**Requires:** dartlab
polars
**AIContext:** 동종 비교 시 sector (11 대) 보다 chain stage 가 더 정밀 — AI 가 peer 선정에 본 함수 활용.
**Guide:** "이 회사 가치사슬 어디" → 본 함수.
"같은 stage peer" → result["peers"].
**SeeAlso:** ``sector`` — WICS 11 대 섹터 분류 (industry 와 다른 차원).
``sectorParams`` — 섹터별 valuation 파라미터.
``dartlab.industry.calcs.companyCalcs.calcChainPosition`` — 본 함수 backend.

#### Company.keywordTrend
**Capabilities:** 공시 텍스트에서 키워드 빈도 추이 분석
54개 내장 키워드 세트 (AI, ESG, 탄소중립 등)
topic별 x 기간별 빈도 매트릭스
복수 키워드 동시 검색
**Requires:** 데이터: docs (자동 다운로드)
**AIContext:** 공시 텍스트의 키워드 빈도 변화로 전략 방향 전환 감지
AI, ESG, 탄소중립 등 트렌드 키워드 모니터링
**Guide:** "AI 언급 추이" → c.keywordTrend("AI")
"ESG 관련 변화" → c.keywordTrend("ESG")
"전체 키워드 트렌드" → c.keywordTrend()
**SeeAlso:** diff: 텍스트 줄 단위 변경 비교 (키워드가 아닌 전체 변경)
watch: 변화 중요도 스코어링

Raises:
없음.

#### Company.listing
**Capabilities:** KOSPI + KOSDAQ 전체 상장법인
종목코드, 종목명, 시장구분, 업종
**Requires:** 데이터: listing (자동 다운로드)

Raises:
없음.

#### Company.liveFilings
**Capabilities:** OpenDART API 실시간 공시 조회
기간, 건수, 키워드 필터링
정규화된 컬럼 (docId, filedAt, title, formType 등)
**Requires:** API 키: DART_API_KEY
**AIContext:** 최신 공시 모니터링으로 기업 이벤트(배당, 유증, 합병 등) 실시간 감지
readFiling()과 조합하여 최신 공시 원문 분석
**Guide:** "최근 공시 확인해줘" → c.liveFilings()
"이번 주 공시 있어?" → c.liveFilings(days=7)
"배당 관련 공시" → c.liveFilings(keyword="배당")
**SeeAlso:** disclosure: 과거 전체 공시 이력 조회
readFiling: 공시 원문 텍스트 읽기
watch: 공시 변화 중요도 스코어링

#### Company.macro
**Capabilities:** KR 시장 매크로 (ECOS + KRX 데이터) 자동 위임. market="KR" 자동 주입. KR 회사 매크로 영향
분석 entry — US 회사는 edgar.macro 별도.
**Requires:** dartlab
polars
**AIContext:** 거시환경 회사 영향 답변 시 본 함수. axis 미지정 시 가이드 반환 — AI 가 카탈로그 먼저 확인.
**Guide:** When: 거시경제 환경·사이클 판단이 필요할 때.
How: axis 로 분석 영역 지정. 무인자 = 가이드.
"매크로" → c.macro()
"경기 사이클" → c.macro("사이클")
"위기 진단" → c.macro("위기")
"2008 시나리오" → c.macro("시나리오", "2008 금융위기")
Verified:
macro("사이클") → CLI + 사분면 + 금리 + 유동성 + 심리 6축 (observed via ai-ask, 2026-04-25 — 정식 Phase P 판정 아님)
macro + analysis → 경제 고려한 종목 분석 (observed via thesis ai-ask, 2026-04-25 — 정식 Phase P 판정 아님)
**SeeAlso:** ``dartlab.macro.Macro`` — 매크로 backend SSOT.
``edgar.Company.macro`` — US 패리티.

#### Company.memorySnapshot
**Capabilities:** ``self._cache`` entry 수 + 현 프로세스 RSS (MB) dict 합산. MemorySafeProvider Protocol entry.
**Requires:** dartlab
polars
**AIContext:** OOM tripwire 발동 직전 본 함수로 회사별 메모리 분포 보고 + AI 가 cleanup 결정.
**Guide:** "이 회사가 메모리 얼마 쓰나" → 본 함수.
"cleanupCache 효과 확인" → 호출 전/후 비교.
**SeeAlso:** ``cleanupCache`` — 본 함수가 보여준 RSS 회수.
``dartlab.core.memory.getMemoryMb`` — psutil 기반 RSS.

#### Company.narrativeDiff
**Capabilities:** 각 claim 제거 후 FV 재계산 → contribution 측정. Thought Anchors 기반 정량 기여도.
**Requires:** dartlab
polars
**AIContext:** AI 가 "이 valuation 핵심 가정" 답변 시 본 함수 결과 contribution 큰 순 인용.
**Guide:** "가치 기여도" → c.narrativeDiff()
"낮은WACC 기여 몇%" → 결과 필터 claim='낮은WACC'
**SeeAlso:** ``storyTree`` — base trajectory.
``causalWeights`` — claim 가중치.
``dartlab.story.narrativeDiff.computeImpact`` — implementation.

#### Company.network
**Capabilities:** 그룹 계열사 목록 (members)
출자/피출자 연결 + 지분율 (edges)
순환출자 경로 탐지 (cycles)
ego 서브그래프 (peers)
인터랙티브 네트워크 시각화 (브라우저)
**Requires:** 데이터: DART 대량보유/임원 공시 (자동 수집)
**AIContext:** 그룹 계열사/출자 구조 파악 — 지배구조 분석의 기초 데이터
순환출자 탐지로 거버넌스 리스크 감지
**Guide:** "계열사 관계도" → c.network() 또는 c.network().show()
"같은 그룹 계열사" → c.network("members")
"출자/지분 구조" → c.network("edges")
"순환출자 있어?" → c.network("cycles")
**SeeAlso:** governance: 이사회/감사위원/최대주주 분석
capital: 주주환원 분석

#### Company.news
**Capabilities:** Google News RSS 기반 뉴스 수집
제목, 날짜, 소스, 링크
기간 조절 가능
**Requires:** 없음 (공개 RSS)
**AIContext:** 최근 뉴스로 시장 반응, 이슈, 이벤트 파악
ask()/chat()에서 정성적 시장 맥락 보충
**Guide:** "최근 뉴스 보여줘" → c.news()
"이번 주 뉴스" → c.news(days=7)
**SeeAlso:** liveFilings: 최신 공시 (뉴스가 아닌 공식 공시)
gather: 뉴스 포함 4축 외부 데이터 수집

Raises:
없음.

#### Company.notesDetail
**Capabilities:** K-IFRS 주석 표 본문 파싱 (NOTES_KEYWORDS 23 종 — 리스/우발/퇴직/파생/금융자산 등)
연간/분기/반기 분기
최근 5 년 historical panel
audit-grade citation 의 핵심 evidence layer
**Requires:** DART 정기보고서 docs (주석 본문 자동 파싱).
**AIContext:** footnote-grade Q&A 의 raw 데이터 (Bloomberg/FactSet 미보유 영역)
"LG energy 의 리스 약정 중 중국 비중" 같은 질문은 본 method 의 답 source
주석 양식이 분기별로 미세 변경 — narrative 비교 시 변경 가능성 인지
**Guide:** "삼성전자 리스 약정" → c.notesDetail("리스")
"셀트리온 우발채무" → c.notesDetail("우발")
"LG화학 퇴직급여 가정" → c.notesDetail("퇴직급여")
"현대차 파생금융상품" → c.notesDetail("파생")
**SeeAlso:** audit: 감사보고서 (KAM 와 주석은 보완)
governance: 지배구조 본문

#### Company.quant
**Capabilities:** 31 축 기술 분석 (기술지표/벤치마크/팩터/감성/최적화) dual-access. self.stockCode
자동 바인딩. axis 미지정 시 카탈로그 + 한글 axis 한정.
**Requires:** dartlab
polars
**AIContext:** 주가 기반 기술 판단 entry — 재무 (analysis) 와 분리. ``c.quant("판단")`` 종합 verdict.
**Guide:** "차트 판단" → c.quant("판단")
"모멘텀" → c.quant("모멘텀")
"지표 DF" → c.quant("지표")
"베타" → c.quant("베타")
"섹터 베타" → c.quant("베타", benchmarkMode="sector")

실제 동작은 ``_quantImpl`` 참조.
**SeeAlso:** ``_quantImpl`` — 실 구현 (31 축 dispatch).
``dartlab.quant.Quant`` — backend SSOT.
``edgar.Company.quant`` — US 패리티 (Naver vs Yahoo origin 차이).

#### Company.rank
**Capabilities:** 전체 시장 내 매출/자산 순위
섹터 내 상대 순위
매출 성장률 기반 규모 분류 (large/mid/small)
**Requires:** 데이터: buildSnapshot() 사전 실행 필요
**AIContext:** 시장/섹터 내 상대 위치 파악 — 피어 비교 분석의 기초
sizeClass로 대형/중형/소형주 분류
**Guide:** "이 회사 순위는?" → c.rank
"시장에서 몇 등이야?" → c.rank.revenueRank
"대형주야?" → c.rank.sizeClass
**SeeAlso:** sector: 섹터 분류 (rank의 기준 그룹)
insights: 종합 등급 평가

#### Company.rawDocs
**Capabilities:** HuggingFace docs 카테고리 원본 데이터 직접 접근
가공/정규화 이전 상태 그대로 반환
**Requires:** 데이터: HuggingFace docs parquet (자동 다운로드)
**AIContext:** 원본 데이터 구조 파악 — 파싱 전 상태로 디버깅/검증에 활용
**Guide:** "원본 공시 데이터 보여줘" → c.rawDocs
"가공 전 데이터 확인" → c.rawDocs
**SeeAlso:** sections: docs 가공 후 topic x period 통합 지도
rawFinance: 재무제표 원본 데이터
rawReport: 정기보고서 원본 데이터

#### Company.rawFinance
**Capabilities:** HuggingFace finance 카테고리 원본 데이터 직접 접근
XBRL 정규화 이전 상태 그대로 반환
**Requires:** 데이터: HuggingFace finance parquet (자동 다운로드)
**AIContext:** XBRL 정규화 전 원본 구조 파악 — 매핑 검증에 활용
**Guide:** "원본 재무 데이터 보여줘" → c.rawFinance
"XBRL 원본 확인" → c.rawFinance
**SeeAlso:** BS: 가공된 재무상태표
IS: 가공된 손익계산서
rawDocs: 공시 문서 원본

#### Company.rawReport
**Capabilities:** HuggingFace report 카테고리 원본 데이터 직접 접근
정기보고서 API 데이터 가공 이전 상태 반환
**Requires:** 데이터: HuggingFace report parquet (자동 다운로드)
**AIContext:** 정기보고서 API 원본 확인 — report topic 매핑 검증에 활용
**Guide:** "원본 보고서 데이터 보여줘" → c.rawReport
"정기보고서 원본 확인" → c.rawReport
**SeeAlso:** rawDocs: 공시 문서 원본
rawFinance: 재무제표 원본
show: 가공된 topic 데이터 조회

#### Company.readFiling
**Capabilities:** 접수번호(str) 직접 지정 또는 DataFrame row 자동 파싱
전문 텍스트 또는 ZIP 기반 구조화 섹션 반환
텍스트 길이 제한 (truncation) 지원
**Requires:** API 키: DART_API_KEY
**AIContext:** 공시 원문 텍스트를 LLM 컨텍스트에 주입하여 심층 분석 수행
sections=True로 구조화하면 특정 섹션만 선택적 분석 가능
**Guide:** "이 공시 내용 보여줘" → c.readFiling(접수번호)
"공시 원문 분석해줘" → c.readFiling()으로 원문 확보 후 ask()로 분석
**SeeAlso:** liveFilings: 최신 공시 목록에서 접수번호 확인
disclosure: 과거 공시 목록에서 접수번호 확인

#### Company.relatedPartyTx
**Capabilities:** K-IFRS 1024 footnote 의 특수관계자 거래 line-item 추출
공정거래법 §26 의 대규모기업집단현황공시 100억 원 threshold rows
보증/대여/매출/매입/자산 양수도 분류
chaebol inter-affiliate 거래 graph 의 raw input
**Requires:** DART 사업보고서 본문 (관계자거래 섹션 자동 파싱).
**AIContext:** 2024-01-01 부터 threshold 100억 원 (이전 10억 원 X — 룰 변경 주의)
2025 FTC 데이터: top-10 chaebol = 193 조 원 = 전체 disclosed RPT 의 70%
chaebol RPT graph 구축 시 affiliateGroup 와 join 필수 (회사 단독 X)
**Guide:** "삼성전자 관계자 거래" → c.relatedPartyTx()
"삼성그룹 RPT 흐름" → affiliateGroup × relatedPartyTx 모든 계열사 join
"100억 이상 RPT" → 본 method 의 결과 자체 (threshold 이상만 disclosed)
**SeeAlso:** governance: 이사회 의결 RPT (board-approved)
executivePay: 임원 개인 보수 (RPT 와 별도)

#### Company.resolve
**Capabilities:** 입력이 6 자리 alphanumeric 이면 그대로 (대문자화), 한국어 회사명이면 nameToCode 위임.
사용자 입력 표준화 entry — KR 종목코드 또는 회사명 양쪽 받는 헬퍼.
**Requires:** dartlab
polars
**AIContext:** AI 가 사용자 발화 "삼성전자" / "005930" 모두 처리 — 일관 stockCode 반환.
**Guide:** "사용자 모호 입력 → 표준 종목코드" → 본 함수.
**SeeAlso:** ``codeName`` — 반대 (code → name).
``nameToCode`` — module-level 등가.

#### Company.retrievalBlocks
**Capabilities:** docs 원문을 markdown 형태 그대로 보존한 검색용 블록
각 블록은 topic/subtopic/period 단위로 분할
RAG, 벡터 검색, 원문 참조에 최적화된 포맷
**Requires:** 데이터: docs (자동 다운로드)
**AIContext:** ask()/chat()에서 원문 기반 답변 생성 시 소스로 사용
retrieval 기반 컨텍스트 주입의 원천 데이터
**Guide:** "원문 검색용 블록" → c.retrievalBlocks
"RAG용 데이터" → c.retrievalBlocks
**SeeAlso:** contextSlices: retrievalBlocks를 LLM 윈도우에 맞게 슬라이싱한 결과
sections: 구조화된 데이터 지도 (retrievalBlocks의 원본)

#### Company.sections
**Capabilities:** topic × period 수평화 통합 DataFrame
docs/finance/report 3-source 병합
show(topic)/trace(topic)/diff() 의 근간 데이터
**Requires:** 데이터: docs (필수), finance/report (선택, 자동 다운로드)
**AIContext:** 전체 지도가 필요할 때만 사용. 개별 topic은 show(topic) 추천
메모리 부하가 크므로 AI 코드에서 직접 접근 지양
**Guide:** "이 회사 전체 데이터 지도" → c.sections
"어떤 topic이 있어?" → c.topics (경량)
**SeeAlso:** topics: sections 기반 topic 요약 (더 간결)
show: 특정 topic 데이터 조회
index: 전체 구조 메타데이터 목차

#### Company.sector
**Capabilities:** WICS 11대 섹터 + 하위 산업그룹 자동 분류
KIND 업종명 + 주요제품 키워드 기반 매칭
override 테이블 우선 → 키워드 → 업종명 순 fallback
**Requires:** 데이터: KIND 상장사 목록 (자동 로드)
**AIContext:** 섹터 분류 결과로 동종업계 비교, 섹터 파라미터 자동 선택
analysis/valuation에서 섹터별 벤치마크 기준으로 활용
**Guide:** "이 회사 어떤 섹터야?" → c.sector
"업종 분류" → c.sector
**SeeAlso:** sectorParams: 섹터별 밸류에이션 파라미터 (할인율, PER 등)
rank: 섹터 내 규모 순위
insights: 섹터 기준 등급 평가

#### Company.sectorParams
**Capabilities:** 섹터별 할인율, 성장률, PER 멀티플 제공
섹터 분류 결과에 연동된 파라미터 자동 선택
**Requires:** 데이터: sector 분류 결과 (자동 연산)
**AIContext:** valuation()에서 DCF 할인율, 성장률 자동 적용
섹터 특성 반영된 밸류에이션 파라미터
**Guide:** "이 섹터 할인율은?" → c.sectorParams.discountRate
"PER 멀티플" → c.sectorParams.perMultiple
**SeeAlso:** sector: 섹터 분류 정보 (sectorParams의 기반)
valuation: 밸류에이션 (sectorParams를 내부적으로 소비)

Raises:
없음.

#### Company.select
**Capabilities:** show() 결과의 indList (행/계정) × colList (열/기간) 동시 필터. SelectResult 로 감싸
``.chart()`` 체이닝 + export. strict=True 시 매치 0 면 ValueError.
**Requires:** dartlab
polars
**AIContext:** show() 전체 노출 비용 회피 — 필요 행/열만 정밀 추출 후 LLM 컨텍스트 주입.
**Guide:** "매출액만 2024" → ``c.select("IS", "매출액", "2024")``.
"여러 계정 + 여러 연도" → ``c.select("IS", ["매출액", "당기순이익"], ["2024", "2023"])``.
**SeeAlso:** ``_selectImpl`` — 실제 필터 구현.
``show`` — 본 함수의 입력 source.
``dartlab.frame.select.SelectResult`` — 반환 객체 + ``.chart()`` 체이닝.

#### Company.show
**Capabilities:** finance + docs + report 3 source 의 120+ topic 통합 dispatch entry. call (c.show("BS"))
+ attr (c.show.BS()) dual access. freq/scope/period/block 4 토글로 view 변환.
**Requires:** dartlab
polars
**AIContext:** workbench 의 핵심 단일 진입점 — 모든 topic 데이터 조회가 본 함수를 통과.
**Guide:** "손익계산서" → ``c.show("IS")``
"재무상태" → ``c.show("BS")``
"현금흐름" → ``c.show("CF")``
"사업 개요" → ``c.show("businessOverview")``
"주요 제품" → ``c.show("mainProduct")``
"주요주주/최대주주" → ``c.show("majorHolder")`` (``majorShareholder`` 아님)
"차입금" → ``c.show("borrowings")``
**SeeAlso:** ``_showImpl`` — 실제 구현 + 120+ topic dispatch.
``select`` / ``trace`` — show 결과 필터 / origin 추적.
``topics`` — 사용 가능 topic 카탈로그.

#### Company.sources
**Capabilities:** 3개 데이터 source(docs, finance, report) 존재 여부/규모 한눈에 확인
각 source의 row/col 수와 shape 문자열 제공
데이터 로드 전 가용성 사전 점검
**Requires:** 없음 (메타데이터만 조회, 데이터 파싱 불필요)
**AIContext:** 데이터 가용성 사전 점검 — 분석 가능 범위 판단의 기초
**Guide:** "데이터 뭐가 있어?" → c.sources
"docs/finance/report 상태" → c.sources
**SeeAlso:** topics: topic 단위 상세 데이터 지도
trace: 특정 topic의 출처 추적

#### Company.status
**Capabilities:** 로컬 데이터 현황 (종목별 docs/finance/report 보유 여부)
최종 업데이트 일시

#### Company.story
**Capabilities:** 14 섹션 (수익구조~재무정합성) 통합 보고서 dual-access proxy. preset 5 종 + template 7 종
조합으로 톤/관점 조절. call + attr 양식 모두 backend dispatch.
**Requires:** dartlab
polars
**AIContext:** ``ask`` 가 본 함수 결과를 tool 결과로 받아 AI 답변 합성. 단일 섹션 호출이 토큰 효율.
**Guide:** "보고서" → c.story()
"신용 보고서" → c.story(type="credit")
"수익성 블록만" → c.story("수익성")
"사이클 관점" → c.story(type="full", template="사이클")

실제 동작은 ``_storyImpl`` 참조.
**SeeAlso:** ``_storyImpl`` — 실제 구현 + 14 섹션 + preset/template 옵션.
``analysis`` — 14축 raw 분석 (story 가 합산).
``dartlab.story.registry.buildStory`` — backend SSOT.

#### Company.storyTree
**Capabilities:** possible (낙관) / plausible (중도) / probable (보수) 3 DCF 계산 + spread/mean 요약.
Damodaran 3P 방법론.
**Requires:** dartlab
polars
**AIContext:** AI 가 "이 회사 가치 시나리오" 답변 시 본 함수 3 trajectory 인용. 단일 값 X.
**Guide:** "3 시나리오 가치" → c.storyTree()
"서사 민감도" → c.storyTree()['summary']['spreadPct']
**SeeAlso:** ``causalWeights`` / ``valuationImpact`` — 본 함수의 입력 시나리오.
``validateStory`` — 본 결과의 plausibility 검증.

#### Company.table
**Capabilities:** docs 원문의 markdown table을 Polars DataFrame으로 변환
subtopic 지정으로 특정 표만 추출
numeric 모드로 금액 문자열을 float 변환
period 필터로 특정 기간 컬럼만 선택
**Requires:** 데이터: docs (자동 다운로드)
**AIContext:** docs 원문 테이블을 구조화하여 정량 분석에 활용
numeric=True로 금액 문자열을 수치화하면 계산 가능
**Guide:** "직원 현황 테이블" → c.table("employee")
"표 데이터를 숫자로" → c.table(topic, numeric=True)
**SeeAlso:** show: topic 전체 데이터 (table은 subtopic 단위 파싱)
select: show() 결과에서 행/열 필터

Raises:
없음.

#### Company.topicSummaries
**Capabilities:** finance 6 topic 은 고정 한국어 설명 + docs topic 은 최신 사업보고서 첫 200 자 요약 합산.
AI 가 topic 라우팅 결정 시 (어느 topic 사용자 질문에 해당?) 의 origin.
**Requires:** dartlab
polars
**AIContext:** workbench query routing — 사용자 자연어 → topic 선택 시 본 dict 으로 후보 좁힘.
**Guide:** "이 회사 어떤 데이터 어떤 내용 담고 있나" → 본 함수.
**SeeAlso:** ``topics`` — DataFrame 카탈로그.
``index`` — topic 메타 보드.
``mapSectionTitle`` — sections title 정규화 매핑.

#### Company.topics
**Capabilities:** docs/finance/report 모든 source의 topic을 하나의 DataFrame으로 통합
chapter 순서대로 정렬, 각 topic의 블록 수/기간 수/최신 기간 표시
어떤 데이터가 있는지 한눈에 파악
**Requires:** 데이터: docs/finance/report 중 하나 이상 (자동 다운로드)
**AIContext:** LLM이 가용 topic 목록을 파악하는 데 사용
분석 범위 결정 시 참조
**Guide:** "어떤 데이터가 있어?" → c.topics
"topic 목록" → c.topics
**SeeAlso:** show: 특정 topic 데이터 조회
sections: topic x period 전체 지도 (topics보다 상세)
index: 전체 구조 메타데이터 목차

#### Company.trace
**Capabilities:** topic 별 데이터 출처 확인 (docs, finance, report)
출처 선택 이유 (우선순위, fallback 경로)
각 출처별 데이터 행 수, 기간 수, 커버리지
**Requires:** 데이터: docs + finance + report (보유한 것만 추적)
**AIContext:** 데이터 출처 신뢰도 판단 — finance > report > docs 우선순위 확인
분석 결과의 근거 투명성 확보
**Guide:** "이 데이터 어디서 온 거야?" → c.trace("BS")
"데이터 출처 확인" → c.trace(topic)
**SeeAlso:** show: topic 데이터 조회 (trace로 출처 확인 후 열람)
sources: 3개 source 전체 가용 현황

#### Company.update
**Capabilities:** DART API로 최신 공시 확인 후 누락분만 수집
카테고리별 선택 수집
**Requires:** API 키: DART_API_KEY
**AIContext:** 데이터 최신성 유지에 활용 — 분석 전 자동 갱신 트리거 가능
**Guide:** "최신 공시 반영해줘" → c.update()
"데이터 업데이트" → c.update()로 증분 수집
**SeeAlso:** filings: 현재 보유 공시 목록 확인
disclosure: OpenDART 전체 공시 조회

#### Company.validateStory
**Capabilities:** calcStoryPrecedents (scan peer + KnowledgeDB insights)
calcPlausibilityBand (섹터 피어 분포 percentile)
calcValuationSins (정합성 규칙 위반)
overrides 로 AI 개입 (lifeCyclePhase, terminalGrowth 등)
**Requires:** dartlab
polars
**AIContext:** AI 가 사용자 valuation 가정 reality check 시 본 함수. critical 이면 강한 경고 의무.
**Guide:** "이 가정 그럴듯하나" → 본 함수 결과 plausibility band.
"valuation 의 위험 신호" → result["rules"] severity = "critical".
**SeeAlso:** ``storyTree`` / ``causalWeights`` — 검증 대상 story.
``dartlab.analysis.financial.storyValidation`` — 3 테스트 backend.

#### Company.valuationImpact
**Capabilities:** causalWeights chain → DCF 파라미터 (terminalGrowth/WACC) 가산 + narrative 근거.
narrative → 숫자 피드백 — AI 가 직접 override 적용 가능한 hint dict.
**Requires:** dartlab
polars
**AIContext:** narrative 가 valuation 어떻게 바꾸나 답변 시 본 함수. base/adjusted 비교 의무.
**Guide:** "WACC 조정 어떻게" → c.valuationImpact()['waccAdj']
"override 근거" → c.valuationImpact()['narrative']
**SeeAlso:** ``causalWeights`` — 본 함수의 입력 chain.
``storyTree`` — 본 override 적용 3 시나리오.
``analysis("valuation")`` — 본 overrides 직접 주입 가능.

#### Company.view
**Capabilities:** 로컬 서버 기반 공시 뷰어 실행
브라우저에서 sections/index 탐색
**Requires:** 데이터: HuggingFace docs parquet (자동 다운로드)
**AIContext:** 시각적 탐색 인터페이스 — 사용자가 브라우저에서 직접 데이터 탐색
**Guide:** "공시 뷰어 열어줘" → c.view()
"브라우저에서 보기" → c.view()
**SeeAlso:** index: 뷰어가 소비하는 메타데이터 (프로그래밍 접근)
sections: 뷰어의 원본 데이터

Raises:
없음.

#### Company.watch
**Capabilities:** 전체 topic 변화 중요도 스코어링
텍스트 변화량 + 재무 영향 통합 평가
특정 topic 상세 변화 내역
**Requires:** 데이터: docs (자동 다운로드)
**AIContext:** 공시 변화 중요도 자동 평가 — 분석 우선순위 결정에 활용
텍스트 변화량 + 재무 영향 통합 스코어
**Guide:** "뭐가 크게 바뀌었어?" → c.watch()
"리스크 관련 변화" → c.watch("riskManagement")
**SeeAlso:** diff: 줄 단위 상세 변경 비교 (watch보다 세밀)
keywordTrend: 키워드 빈도 추이

Raises:
없음.

#### Company.workforce
**Capabilities:** 직원수 + 정규직/비정규직 비율
평균 급여 + 1인당 매출
평균 근속연수
시장 전체 인력 횡단 비교
**Requires:** 데이터: DART 정기보고서 (자동 수집)
**AIContext:** 인력 효율성/근무환경 정량 평가 — 1인당 매출, 급여 수준 비교
시장 횡단 비교로 인적자원 경쟁력 판단
**Guide:** "직원 현황" → c.workforce()
"평균 급여는?" → c.workforce()
"전체 상장사 인력 비교" → c.workforce("all")
**SeeAlso:** governance: 이사회/감사위원 구성 (인력의 다른 관점)
show: c.show("employee")로 docs 기반 직원 상세

---

## 주요 데이터 타입

### RatioResult

비율 계산 결과 (최신 단일 시점).

| 필드 | 타입 | 기본값 |
|------|------|--------|
| `revenueTTM` | `float | None` | None |
| `operatingIncomeTTM` | `float | None` | None |
| `netIncomeTTM` | `float | None` | None |
| `operatingCashflowTTM` | `float | None` | None |
| `investingCashflowTTM` | `float | None` | None |
| `totalAssets` | `float | None` | None |
| `totalEquity` | `float | None` | None |
| `ownersEquity` | `float | None` | None |
| `totalLiabilities` | `float | None` | None |
| `currentAssets` | `float | None` | None |
| `currentLiabilities` | `float | None` | None |
| `cash` | `float | None` | None |
| `shortTermBorrowings` | `float | None` | None |
| `longTermBorrowings` | `float | None` | None |
| `bonds` | `float | None` | None |
| `grossProfit` | `float | None` | None |
| `costOfSales` | `float | None` | None |
| `sga` | `float | None` | None |
| `inventories` | `float | None` | None |
| `receivables` | `float | None` | None |
| `payables` | `float | None` | None |
| `tangibleAssets` | `float | None` | None |
| `intangibleAssets` | `float | None` | None |
| `retainedEarnings` | `float | None` | None |
| `profitBeforeTax` | `float | None` | None |
| `incomeTaxExpense` | `float | None` | None |
| `financeIncome` | `float | None` | None |
| `financeCosts` | `float | None` | None |
| `capex` | `float | None` | None |
| `dividendsPaid` | `float | None` | None |
| `depreciationExpense` | `float | None` | None |
| `noncurrentAssets` | `float | None` | None |
| `noncurrentLiabilities` | `float | None` | None |
| `roe` | `float | None` | None |
| `roa` | `float | None` | None |
| `roce` | `float | None` | None |
| `operatingMargin` | `float | None` | None |
| `netMargin` | `float | None` | None |
| `preTaxMargin` | `float | None` | None |
| `grossMargin` | `float | None` | None |
| `ebitdaMargin` | `float | None` | None |
| `costOfSalesRatio` | `float | None` | None |
| `sgaRatio` | `float | None` | None |
| `effectiveTaxRate` | `float | None` | None |
| `incomeQualityRatio` | `float | None` | None |
| `debtRatio` | `float | None` | None |
| `currentRatio` | `float | None` | None |
| `quickRatio` | `float | None` | None |
| `cashRatio` | `float | None` | None |
| `equityRatio` | `float | None` | None |
| `interestCoverage` | `float | None` | None |
| `netDebt` | `float | None` | None |
| `netDebtRatio` | `float | None` | None |
| `noncurrentRatio` | `float | None` | None |
| `workingCapital` | `float | None` | None |
| `revenueGrowth` | `float | None` | None |
| `operatingProfitGrowth` | `float | None` | None |
| `netProfitGrowth` | `float | None` | None |
| `assetGrowth` | `float | None` | None |
| `equityGrowthRate` | `float | None` | None |
| `revenueGrowth3Y` | `float | None` | None |
| `totalAssetTurnover` | `float | None` | None |
| `fixedAssetTurnover` | `float | None` | None |
| `inventoryTurnover` | `float | None` | None |
| `receivablesTurnover` | `float | None` | None |
| `payablesTurnover` | `float | None` | None |
| `operatingCycle` | `float | None` | None |
| `fcf` | `float | None` | None |
| `operatingCfMargin` | `float | None` | None |
| `operatingCfToNetIncome` | `float | None` | None |
| `operatingCfToCurrentLiab` | `float | None` | None |
| `capexRatio` | `float | None` | None |
| `dividendPayoutRatio` | `float | None` | None |
| `fcfToOcfRatio` | `float | None` | None |
| `roic` | `float | None` | None |
| `dupontMargin` | `float | None` | None |
| `dupontTurnover` | `float | None` | None |
| `dupontLeverage` | `float | None` | None |
| `debtToEbitda` | `float | None` | None |
| `ccc` | `float | None` | None |
| `dso` | `float | None` | None |
| `dio` | `float | None` | None |
| `dpo` | `float | None` | None |
| `piotroskiFScore` | `int | None` | None |
| `piotroskiMaxScore` | `int` | 9 |
| `altmanZScore` | `float | None` | None |
| `beneishMScore` | `float | None` | None |
| `sloanAccrualRatio` | `float | None` | None |
| `ohlsonOScore` | `float | None` | None |
| `ohlsonProbability` | `float | None` | None |
| `altmanZppScore` | `float | None` | None |
| `springateSScore` | `float | None` | None |
| `zmijewskiXScore` | `float | None` | None |
| `eps` | `float | None` | None |
| `bps` | `float | None` | None |
| `dps` | `float | None` | None |
| `per` | `float | None` | None |
| `pbr` | `float | None` | None |
| `psr` | `float | None` | None |
| `evEbitda` | `float | None` | None |
| `marketCap` | `float | None` | None |
| `sharesOutstanding` | `int | None` | None |
| `ebitdaEstimated` | `bool` | True |
| `currency` | `str` | KRW |
| `warnings` | `list` | [] |

### InsightResult

단일 영역 분석 결과.

| 필드 | 타입 | 기본값 |
|------|------|--------|
| `grade` | `str` |  |
| `summary` | `str` |  |
| `details` | `list` | [] |
| `risks` | `list` | [] |
| `opportunities` | `list` | [] |

### Anomaly

이상치 탐지 결과.

| 필드 | 타입 | 기본값 |
|------|------|--------|
| `severity` | `str` |  |
| `category` | `str` |  |
| `text` | `str` |  |
| `value` | `Optional` | None |

### Flag

리스크/기회 플래그.

| 필드 | 타입 | 기본값 |
|------|------|--------|
| `level` | `str` |  |
| `category` | `str` |  |
| `text` | `str` |  |

### AnalysisResult

종합 분석 결과.

| 필드 | 타입 | 기본값 |
|------|------|--------|
| `corpName` | `str` |  |
| `stockCode` | `str` |  |
| `isFinancial` | `bool` |  |
| `performance` | `InsightResult` |  |
| `profitability` | `InsightResult` |  |
| `health` | `InsightResult` |  |
| `cashflow` | `InsightResult` |  |
| `governance` | `InsightResult` |  |
| `risk` | `InsightResult` |  |
| `opportunity` | `InsightResult` |  |
| `predictability` | `Optional` | None |
| `uncertainty` | `Optional` | None |
| `coreEarnings` | `Optional` | None |
| `anomalies` | `list` | [] |
| `distress` | `Optional` | None |
| `summary` | `str` |  |
| `profile` | `str` |  |

### SectorInfo

SectorInfo — TODO 한국어 클래스 설명.

| 필드 | 타입 | 기본값 |
|------|------|--------|
| `sector` | `Sector` |  |
| `industryGroup` | `IndustryGroup` |  |
| `confidence` | `float` |  |
| `source` | `str` |  |

### SectorParams

SectorParams — TODO 한국어 클래스 설명.

| 필드 | 타입 | 기본값 |
|------|------|--------|
| `discountRate` | `float` | 10.0 |
| `growthRate` | `float` | 3.0 |
| `perMultiple` | `float` | 15 |
| `pbrMultiple` | `float` | 1.2 |
| `evEbitdaMultiple` | `float` | 8 |
| `beta` | `float` | 1.0 |
| `exitMultiple` | `float` | 8.0 |
| `label` | `str` |  |

### RankInfo

단일 종목의 랭크 정보.

    Attributes
    ----------
    stockCode : str — 종목코드
    corpName : str — 회사명
    sector : str — 섹터
    industryGroup : str — 산업군
    revenue : float | None — 매출 TTM (원)
    totalAssets : float | None — 총자산 (원)
    revenueGrowth3Y : float | None — 매출 3년 성장률 (%)
    revenueRank : int | None — 전체 매출 순위
    revenueTotal : int — 매출 집계 종목 수
    revenueRankInSector : int | None — 섹터 내 매출 순위
    revenueSectorTotal : int — 섹터 내 종목 수
    assetRank : int | None — 전체 자산 순위
    assetTotal : int — 자산 집계 종목 수
    assetRankInSector : int | None — 섹터 내 자산 순위
    assetSectorTotal : int — 섹터 내 종목 수
    growthRank : int | None — 전체 성장 순위
    growthTotal : int — 성장 집계 종목 수
    growthRankInSector : int | None — 섹터 내 성장 순위
    growthSectorTotal : int — 섹터 내 종목 수
    sizeClass : str — 규모 분류 (large/mid/small)

| 필드 | 타입 | 기본값 |
|------|------|--------|
| `stockCode` | `str` |  |
| `corpName` | `str` |  |
| `sector` | `str` |  |
| `industryGroup` | `str` |  |
| `revenue` | `float | None` | None |
| `totalAssets` | `float | None` | None |
| `revenueGrowth3Y` | `float | None` | None |
| `revenueRank` | `int | None` | None |
| `revenueTotal` | `int` | 0 |
| `revenueRankInSector` | `int | None` | None |
| `revenueSectorTotal` | `int` | 0 |
| `assetRank` | `int | None` | None |
| `assetTotal` | `int` | 0 |
| `assetRankInSector` | `int | None` | None |
| `assetSectorTotal` | `int` | 0 |
| `growthRank` | `int | None` | None |
| `growthTotal` | `int` | 0 |
| `growthRankInSector` | `int | None` | None |
| `growthSectorTotal` | `int` | 0 |
| `sizeClass` | `str` |  |
