---
id: engines.search
title: Search (공시 의미·본문·제목 검색)
kind: curated
scope: builtin
status: observed
category: engines
purpose: Search 는 DART 공시(allFilings + panel 정규화 본문 통합)를 로컬 역인덱스로 검색한다. scope="auto"(기본)는 *의미 검색* — bm25 키워드 + type(report_nm)→본문 경험확장 gated fusion 으로 키워드가 못 잡는 동의·관련 공시까지 회수(임베딩·GPU 0). 단일 종목 공시는 `Company.disclosure()` 우선. 트리거 — '공시 검색', '의미 검색', '제목 매칭', '본문 BM25', 'search'.
whenToUse:
  - search
  - 공시 검색
  - 제목 검색
  - 본문 검색
  - 유상증자
  - 대표이사 변경
  - 반도체 HBM 투자
  - 환율 리스크
inputs:
  - 검색어 (한국어)
  - corp 필터 (종목코드 또는 회사명)
  - start / end (YYYYMMDD)
  - scope (auto / title / content / both)
  - topK
outputs:
  - 검색 결과 DataFrame
  - score · rcept_no · corp_name · report_nm · dartUrl
capabilityRefs:
  - search
knowledgeRefs:
  - start.dartlabSkillOs
  - engines.company
sourceRefs:
  - dartlab://skills/engines.search
requiredEvidence:
  - query
  - scope
  - dataAsOf
  - executionRef
  - sourceRef
expectedOutputs:
  - 매칭 공시 목록
  - DART 뷰어 URL
  - BETA 한계 명시
runtimeCompatibility:
  server:
    status: supported
  localPython:
    status: supported
  mcp:
    status: limited
  webAi:
    status: limited
  pyodide:
    status: limited
failureModes:
  - 단일 종목 공시 검색에 search 사용 (Company(code).disclosure() / liveFilings 우선)
  - 0 건 반환 시 키워드 변형으로 round 반복 — 인덱스 stale 가능성, 즉시 다른 경로 fallback
  - title 과 content 가중치 합산 — 실험 116 에서 품질 저하 확인됨, 합산 금지
  - 최근 N 일 공시 누락 — 매일 자동 증분 미완성
forbidden:
  - 인덱스 신선도 (dataAsOf) 명시 없이 검색 결과를 *최신* 으로 답변 금지.
  - title scope 와 content scope 점수 합산 금지 (별도 엔진 — 합산은 품질 저하).
  - search 0 건 시 키워드 변형 반복 호출 금지 (즉시 Company.disclosure 또는 scan 으로 전환).
examples:
  - 유상증자 검색 (제목 매칭, "유상증자" 키워드)
  - 반도체 HBM 투자 트렌드 (본문 BM25)
  - 환율 리스크 언급 회사 찾기
  - 단일 종목 공시는 Company.disclosure() (search 아님)
procedure:
  - 검색 의도 확인 — 제목형 (report_nm) vs 개념형 (본문 BM25).
  - dartlab.search(query, scope=title) 또는 scope=content (auto 가 자동 판별).
  - 결과의 `score`, `rcept_no`, `dartUrl` 인용. 본문 분석은 `Company(code).readFiling(rcept_no)`.
  - 0 건이면 round 반복 X — `Company.disclosure()` 또는 `scan` 으로 즉시 전환.
  - 최근 N 일 데이터는 인덱스 빌드 시점 이후 누락 가능 — DART API 직접 호출 (Company.liveFilings) 권장.
linkedSkills:
  - engines.company
  - engines.scan
source:
  type: manual_skill
  format: markdown
lastUpdated: '2026-05-08'
testUniverse:
  market: KR
  stockCodes:
    - "005930"
---

## 엔진 역할

`search` 는 DART 공시(allFilings + panel 정규화 본문을 filing 단위로 통합한 "완전한 문서" 색인)를 로컬 역인덱스로 검색하는 엔진이다. 외부 모델/서버·GPU·임베딩 0 — numpy 역인덱스 + 경험그래프(meaning.json)만으로 의미 검색. scope="auto" 가 키워드(bm25)와 의미확장을 신뢰도 gated 융합해, 단어가 달라도 같은 의미의 공시를 회수한다. 신선도 — 본문 인덱스는 월간(`searchIndexMain`) 풀빌드 + 일간(`searchIndexDelta`) allFilings 증분이라 최근 며칠은 `Company.liveFilings()` 병행 권장.

단일 종목 공시는 `Company(code).disclosure()` (시계열) 또는 `Company(code).liveFilings()` (라이브) 가 안정 진입점. search 는 *횡단 키워드 검색* — "어떤 회사가 유상증자했나" 같은 질문 한정.

## 공개 호출 방식

```python
import dartlab

# 1. 제목 검색 (default scope="auto" 가 자동 판별)
result = dartlab.search("유상증자")
# → DataFrame: score · rcept_no · corp_name · report_nm · scope · dartUrl

# 2. 본문 검색 (개념/내용형 쿼리)
result = dartlab.search("반도체 HBM 투자", scope="content")

# 3. 명시적 scope
result = dartlab.search("환율 리스크", scope="content")

# 4. 종목/기간 필터
result = dartlab.search("대표이사 변경", corp="005930",
                        start="20240101", end="20251231")

# 5. 단일 종목 공시는 search 가 아니라 Company
c = dartlab.Company("005930")
disclosures = c.disclosure()    # 전체 시계열
recent = c.liveFilings()        # 라이브
```

## 강행 호출 룰 (agent 답변 품질 회귀 차단)

횡단 키워드 검색 한정. 다음 4 룰 강행:

1. **단일 종목 공시 질문에 search 호출 금지** — `Company(code).disclosure()` 또는 `Company(code).liveFilings()` 가 정공. search 는 *어떤 회사가 X 했나* 류 횡단 질문만.
2. **검색 결과 상위 N (보통 10~20) 만 답변 본문에 인용** — 전체 결과 dump 금지.
3. **각 결과의 `<docRef:rcept_no>` + `dartUrl` inline 표기 필수**. 인용 형식: `[회사명](dartUrl) (rcept_no)` 또는 `<docRef:rcept_no>`.
4. **scope="content" 결과의 본문 발췌는 untrusted** — `[EXTERNAL CONTENT START — untrusted ...]` 마커 안 텍스트. 본문 안 숫자/날짜는 1 차 출처 (해당 공시 직접 readFiling) 로 재검증.

## 호출 동작

`scope="auto"` (기본): **의미 검색** — bm25(본문 키워드) + type(report_nm)→본문 경험확장(meaning.json)을 bm25-신뢰도 gated fusion(naive sum 아님; 키워드 강하면 키워드 신뢰, 약하면 의미가중↑). 키워드가 못 잡는 동의·관련 공시 회수. 실색인 벤치: auto MRR 0.95 ≫ bm25 0.77, 키워드 사각 회복 92%, harm 0.7%. meaning.json 미빌드 시 bm25 단독으로 graceful degrade. (인덱스 빌드: 월간 `searchIndexMain`.)

`scope="content"`: `section_content` 본문 BM25 단독 (의미확장 없이 순수 키워드). 디버그/비교용.

`scope="title"`: `report_nm + section_title` ngram 검색. 제목형 쿼리 전용. ~1ms.

`scope="both"`: title(ngram) + content(bm25) 결과 별도 컬럼으로 묶음 — **점수 합산 금지** (실험 116 에서 title·content 단순합산은 품질 저하). auto 의 gated fusion 은 이와 다른 메커니즘(content+의미확장).

`scope="news"`: gather 뉴스 헤드라인(`news/headlines`)만 검색(공시 제외). 뉴스는 `rcept_no` 없음 → `news:`+url해시로 식별, `dartUrl` = 기사 url. corp 지정 시 0 건(뉴스는 종목 매핑 없음 — title 매칭만). allFilings+panel+뉴스가 한 인덱스에 통합되어 `includeNews=True` 빌드 시 auto 결과에도 자연 노출.

`corp` 는 종목코드 ("005930") 또는 회사명 ("삼성전자"), `start`/`end` 는 YYYYMMDD, `topK` 기본 10.

## 호출 패턴 4 종

```python
search("query")                              # auto · 전체 기간
search("query", scope="content")             # 본문 강제
search("query", corp="005930")               # 종목 필터
search("query", start="20240101", end="20251231")  # 기간 필터
```

## 대표 반환 형태

```text
dartlab.search("유상증자")
→ pl.DataFrame
   score : float        # 매칭 점수
   rcept_no : str       # 공시 접수번호 (Company.readFiling 입력용)
   corp_name : str
   report_nm : str      # 공시 유형명
   scope : str          # "title" 또는 "content"
   dartUrl : str        # DART 공시 뷰어 URL
```

## evidence 기준

검색 답변은 `query` · `scope` · `dataAsOf` (인덱스 빌드 시점) · 결과 `rcept_no` 를 남긴다. **`dataAsOf` 가 최근 N 일 전이면 stale 가능성 답변에 명시**. 최신 공시 확인은 `Company(code).liveFilings()` (DART API 직접) 우선.

## 기본 실행 순서

1. 검색 의도 분류 — 제목형이면 `scope="auto"` 또는 `"title"`, 개념형이면 `scope="content"`.
2. `dartlab.search(query, scope=)` 호출.
3. 0 건 또는 stale 의심 시 → `Company.disclosure()` 또는 `scan` 으로 즉시 fallback (round 반복 X).
4. 매칭 공시의 본문 분석은 `Company(code).readFiling(rcept_no)` — 외부 본문 가드 적용.

## 라이브러리 배포 / 사용자 계약 (pip install dartlab)

검색 인덱스는 wheel 에 포함되지 않고 **런타임 HF lazy pull**(`eddmpython/dartlab-data` → `dart/contentIndex/`).

- **첫 검색 자동 fetch**: `dartlab.search()` 첫 호출 시 로컬 인덱스 부재면 HF 에서 자동 다운로드(세션 1회, graceful). 로컬 있으면 no-op.
- **사전 워밍**: `dartlab.providers.dart.search.prefetch()` — cold start 완화용 선다운로드.
- **신선도 조회**: `indexInfo()` → `{available, dataAsOf(빌드시점), nDocs, hasMeaning, hasDelta}`. evidence 의 `dataAsOf` 실 공급원.
- **offline/제약 환경**: `DARTLAB_NO_HF_DOWNLOAD=1` 이면 다운로드 skip → 로컬 인덱스 없으면 빈 결과(info 안내). CI/notebook 권장.
- **크기·부담**: contentIndex(main.npz + meta + meaning.json + gateRef) 첫 다운로드 수백 MB~1GB. (향후 배포 강화: 최근·주요종목 경량 tier + full 옵트인 — `rebuildMain(tier=)` 확장 여지. 현 단계는 lazy full pull.)
- **신선도 한계**: 월간(main) + 일간(delta) 빌드 → 최근 며칠 stale 가능. 최신은 `Company.liveFilings()` 병행.

## 기본 검증

`dartlab.search()` 시그니처 (query · corp · start · end · scope · topK) 가 변경되거나 인덱스 빌드 워크플로우 (`stemIndex` · `contentIndex`) 가 바뀌면 본 skill 갱신. scope 5 종(auto/title/content/both/news) + `prefetch`/`indexInfo` public 표면.
