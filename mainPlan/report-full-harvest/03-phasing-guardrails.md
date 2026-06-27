# 03 — 페이징 · 통합 패널 설계 · 컷 · 승인 게이트

## 통합 패널 설계 (운영자 지시 정밀 이행) — UX 3렌즈 만장일치

### 「사업보고서 한눈」 단일 패널 (재무제표 표 *바로 아래*)

**적층 블록(탭 아님)** — 데이터 없는 블록은 통째 숨김(empty 클러터 회피, 길이 자동관리):

| 블록 | 글랜스 내용 | 상세(⤢) |
|---|---|---|
| ① 인력 | self 한 줄(총원 YoY·계약직비중 이동) + factGrid 3행(총원/평균급여/**1인당매출**) | FinFullscreen **PEOPLE 탭**(기존) |
| ② 주주환원 | self 한 줄(N년 연속배당·배당성향 이동·소각) + factGrid 3행(DPS/수익률/배당성향) | FinFullscreen **RETURN 탭**(기존) |
| ③ 주석 | 비용·부문 비중 적층 막대 2줄 + top3 칩(현 NOTES 그대로) | **NotesDashboardDialog**(기존, 13MB lazy라 별 모달 유지) |
| ④ 수주(조건부) | 데이터 클린(수주산업)일 때만 — book-to-bill 1줄 + 수치 2개 | (P2 졸업 후) |
| ⑤ R&D(조건부) | acode 태깅 회사만 — R&D÷매출% 1줄 + 금액 | NotesDashboardDialog 섹션 |

**패널 헤더 단일 `상세보기 ▸`** + 블록별 ⤢ 아이콘이 해당 탭 지정.

### 적층(stacked) > 탭 — 근거 (UX critic 정수)
1. **한눈 정체성**: 우측은 스캔하며 훑는 계기판. 탭은 클릭마다 다른 블록을 *숨긴다*(인력 보려고 주주환원 가림).
2. **데이터량 작음**: 각 블록 = self 1줄 + 3행(또는 막대 2줄). 적층해도 세로 과하지 않고, 기존 3패널 헤더·테두리 중복 제거로 **오히려 짧아짐**.
3. **조건부 숨김 = 자동 길이관리**: 빈약한 회사는 ①②만 짧게, 풍부한 회사만 길게. 탭이면 빈 탭 클러터.
4. **깊이는 기존 home 재사용**: 새 패널·새 다이얼로그 0.

### 패널 수 변화: 우측 −3 (WORKFORCE·SHAREHOLDER·NOTES → 1패널). HOLDINGS는 표 밀도 높아 **별도 유지**(통합 부적합).

## 페이징

### P0 — 런타임·무빌드·무승인 (당장)
- **통합 패널 배선**: RightStack의 WORKFORCE·SHAREHOLDER·REPORT NOTES 3패널 → 「사업보고서 한눈」 적층 블록으로 병합. 신규 fetch 0(모든 시리즈 이미 메모리, `reportSelfHistory`로 자기이력 파생).
- **이미-live 의미화**(순수 재집계): 1인당매출(매출÷인원)·총주주환원(배당+자사주매입−처분, **OCF 분모**)·비용 고정비비중(감가+인건비)·부문 매출믹스.
- **부채 만기벽**: `debtProfile`(이미 wired, 2% 검산 게이트) 단기상환벽 — forensic 또는 패널 한 줄.
- 게이트: svelte-check 0·Playwright 실측·공개 surface 눈검수 → 운영자 승인 후 push(UI 게이트).

### P1 — 런타임 XBRL acode 필터 (회사별·무빌드)
- `xbrlCellsFromContent` acode 필터 추가로 Tier A 주석 확장: **리스부채·차입금명세·충당부채·관계기업·매출채권(DSO)·재고(DIO)**.
- 배치: **우측 글랜스엔 안 올림**(증식 차단). **NotesDashboardDialog 안 섹션/탭**으로만.
- 단일축 표만(다축 합성 컷). ACONTEXT 양식(2025-03+) 회사만 최근분기 포착(미태깅=정직 skip).

## ⛔ panel 파싱 아키텍처 가드 — 공통파서 + 선언적 dispatch SSOT (운영자 지시 2026-06-27)

**panel 파케에서 데이터를 가져올 때 노트 종류별 손함수 복붙 = 덕지덕지. 절대 금지.** ([[feedback_always_check_clutter]])

현 구조의 위험: 노트 1종 추가에 ① block 정규식(`COST_BLK`/`SEG_BLK`) ② selector(`costCells`/`segmentCells`) ③ `buildNoteSeries` 분기 — 3개가 노트당 한 벌씩 손으로 늘어남. P1 6종을 이대로 = selector·분기 6벌 복붙.

**강제 구조 (P1 착수 시):**
1. **raw 파서 1개 = `xbrlCellsFromContent`** 가 유일한 ACODE/ACONTEXT 직독 정본. 새 raw 파서 신설 금지.
2. **노트별 손함수(`costCells`류) 신설 금지.** 대신 **선언적 dispatch 레지스트리 1개**:
   ```
   NOTE_SPECS = [
     { key:'cost',    blockRegex:비용성격별, acodeFilter, axisFilter:none,    agg:byAcode },
     { key:'segment', blockRegex:부문정보,   acodeFilter:Revenue, axisFilter:SEG, agg:bySegment },
     { key:'lease',   blockRegex:리스,       acodeFilter:Lease*,  ... },   // ← P1 추가 = 이 한 줄
   ]
   ```
   spec 한 줄 추가 = 노트 확장. **단일 파싱 엔진**(`buildNoteSeries`)이 `NOTE_SPECS` 순회 → `xbrlCellsFromContent` → spec.agg 적용. 기존 cost/segment 도 이 spec 으로 흡수(리팩터 선행).
3. **집계기는 재사용 가능한 소수 primitive** (`byAcode`·`bySegment`·`byAcodeRollup`) 만 — 노트마다 새 집계 함수 누적 금지.
4. 셀렉터 패턴(acode/axis 정규식)은 spec 의 *데이터*지 코드 분기가 아니다. 새 노트 = 데이터 한 줄, 새 코드 0 지향.

**게이트**: P1 PR 에서 노트당 신규 함수 ≥1 개 추가되면 = 덕지덕지 신호 → 중단·레지스트리화. svelte-check 0 + `xbrlCells.test.ts` 회귀.

### P2 — 빌드 = 사전 토론·승인 게이트 ⛔
- **수주 flow scan('orders')**: [[project_order_flow_scan]] _attempts 졸업(value-sanity 가드=병합셀 concatenation 오파싱 차단·정정/해지 reconcile·gather/scan 거처 이동) → scan 빌드. **승인 필요**. 졸업 후 통합 패널 ④블록(수주산업 조건부).
- **Tier A 주석 시장 횡단 scan**: 리스·차입금 분위/이상치 — 브라우저가 3000 panel 동시 못 읽어 scan 빌드 필요. **승인 필요**. _attempts 품질 입증 선행.

## 컷 리스트 (확정 — 재론 금지)

| 컷 | 근거 |
|---|---|
| 사업보고서 narrative **수주잔고(stock)** 직접 긁기 | free-form fragile(5/10). flow(book-to-bill, 810사 ≥90%)가 대체 |
| **가동률** 숫자 | 인벤토리 data 0. dossier에서 이미 컷 |
| **종합점수·등급·레이더** 환산 | NEVER-CLAIM 위반. rcept_no 역추적·정성 라벨만 |
| **시총분모 총주주환원율** | 거짓정밀(dossier 컷). 금액·성향(payout)·OCF분모만 |
| **원재료 매입처·가격추이** 자유서식 | 노이즈. 비용성격별 XBRL 원재료 비중이 같은 통찰 무빌드 제공 |
| **주요계약·파생·위험관리** narrative 全文 | 정량화 불가·1회성. 공시뷰어 원문 열람으로 충분 |
| **부문×지표 다축 합성**(영업이익률 매트릭스) | 행-라벨 인코딩 fragile. 부문 *매출*(단일축)까지만 |
| **금융위험 민감도 횡단비교** | 회사간 가정 시나리오 불일치(±10%/±100bp 제각각) 비교불가. 회사별 정성만 |
| **우발부채·약정 정량화** | acode 일관성 낮음. 충당부채 표로 대체 |
| **법인세 단독 패널** | 재무비율 흡수 적절. 단독 가치 낮음 |
| **새 6번째 통합 레일 신설** | dossier 기각(덕지덕지·FinFullscreen 경쟁). 기존 통합·−3만 |

## 운영자 결정 필요 (open questions)
1. **통합 패널 = 적층 3블록** 확정? (UX 만장일치·운영자 질문서 이미 적층 선호)
2. **P2 수주 flow scan('orders') 빌드 승인** — orderFlowScan 졸업 착수할지(별도 토론).
3. **P2 Tier A 주석 횡단 scan 빌드 승인** — 리스/차입금 시장분위(_attempts 입증 후).
