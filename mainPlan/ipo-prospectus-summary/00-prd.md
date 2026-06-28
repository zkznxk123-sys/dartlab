# IPO 증권신고서 수요예측 요약 — PRD (전문가 토론 + 실측 박제)

> 출처: GitHub Discussion #70 (zias7039, 2026-06-26) "증권신고서 기반 IPO 수요예측 핵심 데이터 요약".
> 기획 방식: 실측(probe1~4) + 전문 에이전트 4인 토론(입장→토론→종합→적대비판→최종).
> 상태: **기획 확정·미착수**. 운영자 결정 5건 대기. order-flow-scan·professional-report-engine 동급 활성.

---

## 0. 결론 먼저

요청자는 IPO 증권신고서(지분증권) 원문에서 **6개 카테고리**(공모개요·공모일정·밸류에이션·유통가능물량·재무3개년·리스크)를 구조화 표 + **원문근거 링크**로 보여달라 함. 우선순위: 공모일정 → 공모가/시총 → 비교기업/PER → 멀티플 → 할인율 → 유통비율 → 최근실적.

**핵심 결정: 새 top-level 엔진을 만들지 않고 검증된 3곳에 분산 배치하며, 데이터는 런타임 SSOT(allFilings content_raw) 직독을 기본·강제로 한다.** 전부 `tests/_attempts/ipo/` 인큐베이터에서 졸업 후 본진(`order-flow-scan` 동형 라이프사이클).

---

## 1. 실측 결과 (실제 DART 데이터, 2026-06-28)

| 측정 | 결과 |
|---|---|
| 증권신고서(지분증권) 분량 | 9개월 531건(전체) / 초판 88건. zip = **단일 XML**(dart4.xsd, 277KB~4.7MB) → 수집기 "largest 1개" 리스크 **없음** |
| 섹션 검출 | 진짜 IPO 1건(기도산업, 62만자·table 1014개)에서 **6개 카테고리 앵커 전부 ✓**. 밸류에이션이 유상증자보다 오히려 풍부(평가 섹션 본격적) |
| 테이블 값 추출 | dart4.xsd `<TABLE>` 라벨셀→인접값셀 매핑으로 실값 추출 성공(모집주식수 17,790,000주·청약기일 2026-07-14). 단 정관 조문 노이즈 혼입, **다중표·라벨충돌("적용 PER" 반복)에서 오추출** |
| flat regex | get_text 평문 정규식 숫자 추출 **전부 실패** → `<TABLE>` 구조인식 파싱 강제 |

### ★ 결정적 정정 — 토론 표본 오류를 실측이 바로잡음

토론 1차는 "초판 67건"을 IPO 모집단으로 가정했으나, **이는 `corpClass="Y"/"K"`(이미 상장된 시장) 필터 결과 = 전부 유상증자/DR**(SK하이닉스 DR·계양전기 주주배정). **진짜 신규상장 IPO는 상장 전이라 `corp_cls="E"(기타)`에 있고, `corp_cls=E`의 21건(스팩 1 + 일반 20)은 전부 `stock_code` 빈값**이었다.

→ **기계 ground-truth 확정**: `corp_cls=="E" AND stock_code==""` = 신규상장 IPO. `corp_cls∈{Y,K}`(stock_code 보유) = 유상증자/DR. **사람 라벨도, KRX 상장마스터 조인도 불필요.** 적대비판이 P0의 가장 약한 고리로 지목한 "판별 게이트 분모 미정" 문제가 이 실측으로 해소됨. (스팩은 `corp_name` "스팩|기업인수목적"으로 별도 태그.)

---

## 2. 동형 선례 (재발명 0)

- **`src/dartlab/scan/orders.py`** (신규수주 book-to-bill): allFilings `report_nm` 필터 → content_raw 직독 파싱(fetch 0) → 집계, **베이크 없음 런타임 직독**. 룰 완전 준수 선례.
- **`src/dartlab/providers/dart/eventDisclosure.py`**: 수시공시 본문 파서 — `EVENT_SCHEMAS` 선언 레지스트리(라벨패턴→필드), `htmlTableParser.flattenTableCells`+`parseAmount` 위임. IPO 파서의 형제 위치. **단 KRX 폼은 "라벨 고정 채워넣기 폼"이라 선언 1엔트리로 끝나지만, 증권신고서는 자유서식이라 그대로 복사하면 실패**(아래 D1·hiddenAssumption 참조).
- **`core/dataConfig.py` line 55-61 `brokerageReports`**: "본문 0 — 제목·URL·발간일·종목만 public publish, 링크아웃". **퍼블릭 publish 합법성의 진짜 선례**(finance 동형 아님).
- **professional-report-engine**: story를 `ReportModel`(TypedDict) SSOT로 대개조 중. 계약 `ui/packages/contracts/src/reportModel.ts`, 18블록 어휘. **단 Python `buildReportModel` emitter는 src/에 아직 미존재(현재 TS만, P1a만 완료).**

---

## 3. 결정 D1–D5 (최종)

### D1 — 엔진 신설 기각, 3곳 분산
새 `src/dartlab/ipo/` top-level 엔진 **신설 금지**(engine-add 5게이트 비용·import 복잡화·find-SSOT-improve 위반=사본 엔진).
- **(a) 단건 파서 + IPO 판별기 = `src/dartlab/providers/dart/securitiesRegistration.py`** (eventDisclosure 형제, L1). `IPO_SECTION_SCHEMAS` 6카테고리 선언. **`_extractField` 단순 라벨→인접셀 그대로 복사 금지** — 다중표·라벨충돌에서 오추출(실측 확인). **2단 구조**: 6섹션 경계 앵커링 → 섹션 내부 표만 파싱 + **반복 라벨은 표 단위 그룹핑**(비교기업 "적용 PER" N회 대응). ★섹션 분할은 라벨충돌의 *필요조건이지 충분조건 아님*(`_extractField`가 first-match 휴리스틱이라 섹션 좁혀도 동일 라벨 N개 잔존).
- **(b) 횡단 소비(2차) = `src/dartlab/scan/ipo.py`(scanIpo)** — orders.py 동형, `scan/router.py` `_AxisEntry` 1엔트리 "ipo" 등록, 공개 `dartlab.scan("ipo")`. **1차 아님** — 단건 deep(6카테고리 표)이 scan의 wide 1행/사 격자와 본질 불일치. 횡단 출력 스키마 미정의 → **실수요 확인 후 착수(필수 아님)**.
- **(c) 단건 리포트 조립 = story builder(L3, 최종 phase, 조건부)** — D3.

공개 verb: 단건 = providers/Company, 횡단 = `scan("ipo")`.

### D2 — 2단 SSOT, publish는 brokerageReports 동형
- **1단(기본·강제) = 런타임 직독.** orders.py 패턴 — `loadDay` 순회 → `report_nm "증권신고서"` + `corp_cls="E"` 필터 → content_raw 직독 → 파서 위임 → 집계. **별도 ipo.parquet 베이크 0.** content_raw 원문은 PRIVATE HF 유지. src/Python·MCP·터미널 소비는 전부 여기.
- **2단(조건부·후행) = brokerageReports 동형 메타 publish.** 합법 경로는 finance 동형이 아니라 **본문 절대 제외·메타만·링크아웃**.
  - **PUBLIC 대상 = 카테고리1·2(공모개요 확정수치·공모일정)뿐** — 발행사가 확정 기재한 사실 메타(공모가밴드·주식수·청약/납입/상장일). rceptNo 링크아웃 동반.
  - **PUBLIC 영구 제외 = 카테고리3(밸류 적용PER·비교기업·할인율)·6(리스크 투자위험 excerpt)** — 본문성 데이터(원문 수치/문장). 터미널 PRIVATE 직독 + `scan("ipo")` 공개계약에만.
  - 카테고리4·5(유통물량·재무3개년)는 파싱 졸업 후 재평가.
- content_raw 원문 전체 퍼블릭 베이크 절대 금지(SSOT 우회 + PRIVATE 누출). 미검증 상태 publish 금지.

### D3 — 같은 ReportModel chassis, 다른 builder, 다른 데이터원
- 별도 report MODEL 신설 기각(사본·find-SSOT-improve 위반). 6카테고리→18블록 매핑 검증: 밸류=`valuationBridge`+`table`, 유통/오버행=`flags`+`table`, 재무3개년=`table`+`bars`/`line`, 고저평가=`verdict`, 리스크태그=`flags`, **원문근거링크 = 기존 `excerpt` 블록(rceptNo+sourceType:'dart') — #70 "원문근거 링크" 요건 슬롯 이미 존재.**
- ★제약: **Python `buildReportModel` emitter 미존재**(현재 TS만) → **결합 착수는 Python `story/report.py` 안착 후(최종 phase, 조건부)**. 파서 출력 dict를 18블록에 맞춰 처음부터 설계(이중매핑 회피).
- IPO는 perspective(같은 회사 다른 렌즈) 아니라 다른 report TYPE — **상장 전 발행사는 finance 시계열 패널 없음**(재무3개년은 신고서 본문 표에서만).

### D4 — 새 report type "ipo", PUBLIC은 메타 카테고리만
- /report 5관점(earningsPower·liquidity·…)은 finance-lens 시계열 전용(landing build.ts에 excerpt/rceptNo/content_raw 참조 0건) → IPO는 새 perspective 아님, **새 report type "ipo".**
- PUBLIC 노출 = D2대로 **카테고리1·2 메타만**(brokerageReports 동형, 브라우저 직독 ssr=false, pyodide 불필요). 밸류·리스크는 "정밀판은 터미널" 정직표기 + 터미널 링크아웃.
- ★시의성 리스크: IPO 수요예측은 청약일 전 며칠이 가치 — cron publish 주기가 못 따라갈 수 있음 → **P5 착수 전 "터미널 PRIVATE 직독만으로 충분한가" 실측 선행.** 퍼블릭 publish가 불필요로 판명될 수 있음.

### D5 — 5 phase, IPO판별을 파싱 앞에, 게이트는 기계 ground-truth
전부 `tests/_attempts/ipo/`에서 개념확립→실측→모듈화→데모→9섹션 docstring 확정 후 src/ 본진. **측정 안 된 점수로 다음 단계 진입 금지(planScore≠시그니처).**

---

## 4. Phasing (졸업게이트 정량지표)

**P0 — IPO 판별기 (providers, _attempts/ipo). garbage-in 0번 게이트.**
- deliverable: `securitiesRegistration.classifyIpo()` — **1차 신호 = `corp_cls=="E" AND stock_code==""`**(실측 확정, 사람 라벨 불필요), 스팩 별도 태그. 보조 = 신주인수권증서/주주배정 본문 마커.
- 게이트: corp_cls 기계 ground-truth 대비 일치 — corp_cls E 21건 전수 IPO 판정·corp_cls Y/K 67건 전수 비-IPO 판정에서 **오분류 0**(SK하이닉스·계양전기 자동 비-IPO). 경계 케이스(코넥스→코스닥 이전상장·재상장)만 운영자 소수 라벨.

**P1 — 6섹션 경계 앵커링 (providers, _attempts/ipo).**
- deliverable: 섹션 앵커 검출기 + dart4.xsd 단일 XML 섹션경계 추출.
- 게이트: IPO 통과분에서 6섹션 앵커 검출률≥0.95, 섹션밖 노이즈(정관조문) 혼입 0. ★앵커 사전 크기 모니터(제목 변형 "공모개요"vs"공모의 개요"로 비대해지면 덕지덕지 신호).

**P2 — 카테고리별 파서 (providers, _attempts/ipo).**
- deliverable: `securitiesRegistration.parseIpoProspectus()` + **폼 고정성 실측 docstring** + README.
- ★게이트(폼 고정성 실측 선행, 숫자 placeholder): 먼저 orderFlowScan식 표본 측정으로 밸류·유통·리스크가 fixed-form인가 free-form인가 실측. flat regex 실패 → `<TABLE>` 구조파싱 강제. **truth = self-redundancy 교차검증(공모가×주식수≈예상시총, `_applySanity` 동형) 1차** + 소수 사람 스폿체크. 공모개요·일정 ≥0.95 목표 박제 가능, 밸류·유통·리스크 목표는 **폼 고정성 실측 후 박제(0.85는 미박제 placeholder)**. 전수(통과분 전체) 검증 필수(바스켓이 숨기는 concatenation garbage 가드).

**P3 — scan("ipo") 횡단 + src 본진 졸업 (scan L1.5, 조건부).**
- 게이트: orders 동형 데모 + 9섹션 docstring 5점 + dartlabGuard l0-l15 신규위반 0 + publicApiCoverage(`publicApiScenarios.yml` 등록) + structureMirror. **횡단 출력 스키마 실수요 확인 후 — 필수 아님.**

**P4 — story builder 결합 (story L3, 조건부).**
- **Python ReportModel emitter(story/report.py) 안착 후에만** `builders/ipo.py`. excerpt 블록으로 원문근거링크. no-graph: emitter는 함수, 고정노드/5패스 금지.
- 게이트: P2 선행 + story/report.py 존재(현재 미존재, professional-report-engine 진도 종속) + checkAgentBoundary 회귀 0 + 렌더 눈검수.

**P5 — 퍼블릭 publish + /report 메타노출 (별도 운영자 결정).**
- **카테고리1·2(공모개요·일정 메타)만** brokerageReports 동형 PUBLIC publish. 밸류·리스크 PUBLIC 영구 제외. landing ipo report type, ssr=false.
- 게이트: 운영자 명시 승인 + **시의성 실측 선행** + 카테고리1·2만 + content_raw 본문 퍼블릭 베이크 0 + 푸시 전 스크린샷 전수 눈검수. **현시점 코드/커밋 0이면 룰 위반 아님.**

---

## 5. 운영자 결정 필요사항 (착수 전)

1. **[P0 신호 정밀화]** `corp_cls=="E" + stock_code==""` 기계 ground-truth가 실측 확정 — 코넥스→코스닥 이전상장·재상장·스팩합병 경계 케이스를 어떻게 다룰지(소수 운영자 라벨 vs 규칙 추가)만 결정.
2. **[퍼블릭 publish 시의성]** P5 자체의 필요성 — 청약일 전 시의성을 cron publish가 만족하나, 아니면 터미널 PRIVATE 직독만으로 충분(P5 영구 보류)? P3 완료 시점 실측으로 판단.
3. **[story 대개조 줄세우기]** P4 착수 타이밍 — Python story/report.py emitter는 professional-report-engine 대개조 진행 중(P1a만 TS 완료). IPO builder를 그 우선순위 대비 어디에 줄세울지.
4. **[scan("ipo") 실수요]** P3 착수 여부 — 단건 deep가 1차라 횡단 scan은 필수 아님. "이번달 IPO 후보 횡단" 실수요·출력 스키마 정의 시 착수.
5. **[P2 폼 고정성 표본]** 밸류·유통·리스크 정확도 게이트 숫자 박제 전 측정 표본 규모(IPO 통과분 중 N건, 표본 규모 vs 신뢰구간 trade-off).

---

## 6. 토론·실측 산물 위치
- 실측 스크립트: 세션 scratchpad `ipo_probe{1,2,3,4}.py` (probe4가 corp_cls 정정 확정본).
- 토론 전문(4인 입장→토론→종합→비판→최종): 워크플로 `wf_7031498e-34d` 출력.
- 인큐베이터 착수 시: `tests/_attempts/ipo/` (orderFlowScan 구조 동형 — eventSchemas/parser/probe/outputs/README).
