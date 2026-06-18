# 07 — 심화 팩트 + 시계열 체이닝 (도시에 PRD 확장)

> 사용자 명령(원문): "정기보고서 팩트… 당기 전기와 숫자로 이어서 매칭, panel IS처럼 · 비용의 성격별 분류를 하나로 시계열로 병합 · 재무제표 주석에도 다양한 정보들이 있다 — 터미널에 넣어 강력하게."
>
> **무게중심**: 06 까지의 도시에는 *얕게 표면화*를 고쳤다. 07 은 두 축을 더한다 — (A) **시간**: 사업보고서 당기/전기/전전기 3열을 한 시계열로 이어 기존 카드 x축을 *조용히* 늘림(panel-IS식), (B) **깊이**: 가진 6%-주석 자산 중 *단 하나*(비용 성격별 + 인건비 정합)만 깨끗할 때만 떠오름. **순 패널 변화 = 0**(체이닝=데이터층, 비용성격별=기존 PROFIT 탭 카드 1개).
>
> **#1 위험 = vault-dump.** 80% 수집·0% 표면화의 데이터 성당(cathedral)에서, "주석에 다양한 정보"를 24개 카테고리 카드로 쏟는 본능을 *거부*한다. 강함은 쌓아서가 아니라 깎아서 — 24개 중 23개는 뷰어 원문 전속, 1개만 승격. 6%-thin 팩트는 **깨끗할 때만 나타나고 나머지 94%엔 깨끗하게 사라진다**(0-fill 절대 금지).

---

## 1. 한눈 결정 (TL;DR — doc 06 위 델타)

| # | 기능 | 판정 | 거처(전부 EXISTING) | 새 fetch | 새 패널 |
|---|---|---|---|---|---|
| F1 | **당기/전기 체이닝** (배당 시계열 역연장) | **SHIP P1** | RETURN 탭 기존 카드 x축 연장 | 0 (컬럼 추가만) | 0 |
| F2 | **비용 성격별 % stacked 시계열** | **SHIP P2** | PROFIT 탭 `load` 추가, costStructure 직하 | 1 (note read) | 0 (카드 1) |
| F2b | **인건비↔급여총액 정합 1줄** | **조건부 SHIP P2** | F2 카드 footer, 양변 clean·동일연도만 | 0 (양변 live) | 0 (배지) |
| F3 | **희석 overhang(미전환 전환사채)** | **DEFER (2-gate)** | 백엔드 numerator sink 부재 | — | — |
| F4 | **담보/채무보증/충당부채 등 23 주석** | **CUT (뷰어 전속)** | 헤더 리본 ↗원문 anchor only | 0 | 0 |

- **간판 = F1.** 사용자의 "panel IS처럼 이어서"를 정확히 푼다 — `auditFees` 가 *이미* 당기/전기/전전기를 `relOffset`+`fyOf` 로 체이닝(reportSource.ts L618-665) → 그 검증된 패턴을 배당으로 일반화. 발명 아닌 *생성(generalize)*.
- **정직 다운그레이드**: 적대검증이 헤드라인 2개를 깎음 — (a) 체이닝 이득 = **1.4x(배당 한정)**, "8-12yr·2-3x" 마케팅 금지(workforce/treasury/ownership 파케이는 triplet 미populate = dead code). (b) 희석 % = **이중-내러티브 거짓정밀** → DEFER.
- **순 패널 = 0.** 06 의 −1 위에 07 은 0 을 더한다(체이닝=배열 길이, 비용성격별=PROFIT 탭이 오늘 비어있는 `load` 슬롯 채움).

---

## 2. F1 — 당기/전기 시계열 체이닝 (간판, panel-IS식)

### 2.1 무엇이 갇혀 있나 (실측)
- `buildShareholderReturn`(reportSource.ts L207) 이 배당을 `read('dividend', code, ['se','stock_knd','thstrm'])` 로 읽고 **`thstrm`(당기)만** 채택, `frmtrm`(전기)·`lwfr`(전전기)·`rcept_no` 는 SELECT 조차 안 함. 키는 raw `str(r.year)`.
- 결과: 각 사업보고서가 *고립* — 터미널은 최신 3년 창만 본다. 2024 공시는 2024/2023/2022 를, 2021 공시는 2021/2020/2019 를 담고 있는데 이어붙이지 않음.
- **검증된 체이닝 선례**: `buildAuditFees`(L630-665) 가 *이미* 한 보고서의 당기/전기/전전기 행을 `relOffset`(당기/전기/전전기→0/1/2, L621-627) + `fyOf`(stlm_dt 연도 − offset, L639-645) 로 풀어 연도별 최신 접수 우선(`rc > cur.rc`)으로 시계열을 만든다. **이 메커니즘 = F1 그대로**, 단지 thin 섹션(감사보수)에서 간판 팩트(배당)로 일반화.

### 2.2 메커니즘 — `chainTriplet()` 단일 헬퍼 (reportSource.ts 내부 closure)
4 단계 결정론:
1. **EXPLODE**: 각 4분기(사업보고서) 행에서 세 관측 emit — `{fy: thstrm, fy-1: frmtrm, fy-2: lwfr}`. **fy 앵커 = `Number(rcept_no.slice(0,4)) - 1`** (auditTrail L558 검증 패턴). raw `year` 컬럼 금지(L551 가 기수 라벨 오염 명시).
2. **STITCH + RECONCILE**(load-bearing): rcept_no 오름차순 정렬. 각 fy 는 최대 3개 독립 관측(자기 thstrm·다음해 frmtrm·다다음해 lwfr)으로 재진술됨. 재조정 = 기존 **debt-ladder 2% tolerance**(financeSource L468-475 `Math.abs(a-b)/b<=0.02`) 화폐/수량, **절대 0.5pp** 비율(payoutPct/yieldPct — 0.3% 수익률에 2% 상대밴드는 무의미). 2% 내 합치 → canonical = thstrm-origin(원공시값). 초과 충돌 → **최신 rcept_no 승**(`latestRcept` L252-256 재사용) + `restated:true` + `originalValue`/`restatedValue` 양쪽 보존.
3. **RESTATEMENT HONESTY**: chained point = `{fy, value, restated, sources:[rcept_no...], originalValue?, proxy?}`. **절대 평균/블렌딩 안 함**(아무도 보고 안 한 제3의 수 날조). thstrm 없이 frmtrm/lwfr만 있는 해(공시창 밖) → `proxy:'전기재현'` 라벨(1차공시 아닌 이웃공시 복원).
4. **EMIT**: 기존 `ShareholderReturnYear[]` 배열에 fold. 포트 시그니처 불변, 다운스트림(finTabs.ts) 컴파일 무변경.

### 2.3 UX — RETURN 탭 기존 카드, 1픽셀만 신규
- 거처 = `shareholderReport`(finTabs.ts L58-107)가 이미 빌드하는 `divYield`/`perShare` 카드. **x축만 길어짐**. 새 카드·새 차트 0.
- `ShareholderReturnYear` 에 additive optional `prov?: { restated; sources[]; originalValue?; proxy? }`. 오늘 모든 레코드 prov=undefined → 동일 렌더.
- `FinSeries` 에 additive optional `mark?: ('restated'|'proxy'|null)[]` (data[] 평행). MiniFinChart `<rect>` 루프(L341/348/356)가 `s.mark?.[i]` 읽어 fill 전환 — `url(#hatch)`(정정·빗금) 또는 hollow stroke+50% opacity(전기재현). **새 `<pattern>` def 1개 = 전 기능 유일 신규 픽셀.**
- 3가지 정직 표시: (a) 정정해=빗금막대, hover 시 기존 tooltip(L366-398)에 '원공시 X→정정 Y · rcept …' 1줄 + ↗딥링크. (b) proxy해=hollow+'○ 전기재현' 라벨. (c) clean 체이닝해=완전 일반 막대(90% 무마커). 탭 `note` 에 1절 추가: '배당 시계열은 사업보고서 당기·전기·전전기 3열 연결 — 빗금=정정 반영, ○=전기재현'.

### 2.4 정직 천장
- 커버리지: 성공 연차 보유 대형/중형주만 ~1.4x(3-5yr→5-7yr). 1공시 소형주 = 정확히 오늘(3막대), proxy 패딩 금지. 무배당 소형주 = 카드 미렌더(기존 null-skip). **appears-only-when-clean 을 시간축에 적용** — ≥2 사업보고서 + triplet populate 시에만 발현.
- NEVER-CLAIM: 감사된 연속 기록 주장 금지(중첩 자기보고 stitch). 정정값을 '진실'이라 주장 금지('최신 공시는 Y 보고'까지). proxy해를 primary 와 동일 시각 가중 금지. 연결/별도·K-IFRS 전환 break 가로질러 연속 주장 금지(scope 플래그로 break 가시화). **충돌 평균 절대 금지.**
- 위험: 단위/스케일 drift(백만원↔원)가 2% gate 를 1e6× 거짓 정정으로 트리거 — **정규화는 chaining 前**(totalDividend ×1e6 이 L227 read 시점에 선행, reconcile 은 정규화값만). 비-12월 결산은 `rcept_no.slice(0,4)-1` 깨짐 — auditTrail 이 *이미* 안고 가는 기존 도시에 한계(신규 부채 아님), 카드 가이드에 명시.

---

## 3. F2 — 비용 성격별 % stacked 시계열 (제조업 ~6% 한정 정직승리)

### 3.1 무엇이 갇혀 있나
- `calcCostByNatureAnalysis`(_costStructureDeep.py L22-220)가 **이미** 원재료/인건비/감가/외주/기타의 연도별 `{amount,ratio,direction}` + `insight` 자동생성. 단위스케일 `_inferNoteUnitScale`(costStructure.py L406-418) 해결. **단 계산 엔진은 `fetchNotesDetail`(L92-98)로 note-cell(Python L2 panel)을 읽는다 — 공개 터미널은 Python·note-cell 접근 0** ⚠(08 G1): "백엔드 0·reportSource read"는 *오류*. 공개 경로 = CI가 `report/costByNature.parquet`를 bake(엔진 출력 per-company 직렬화)하고 reportSource가 그 parquet를 read. bake 전 공개 불가(F4 rndIntensity와 동급).
- PROFIT 탭(FS_TABS[0])은 `finKey:'profitability'`만 있고 **`load` 슬롯이 비어있다** → `load: profitReport` 추가가 깨끗한 additive. FinFullscreen 렌더경로가 finCards+reportList 병합 → 기존 costStructure(기능별: 매출원가/판관비) *직하* 에 nature-view(왜 원가가 움직였나) 배치 = '무엇' 다음 '왜', 설계상 인접.

### 3.2 메커니즘 + 필수 신규 가드 2개
- 본체 = `report.costByNature(code)` (유일 신규 포트, 엔진 래핑만) → ≤1 TabCard(100% stacked %). NT_D834300 None(94%) → [] → 기존 `alive` 필터(finTabs L25) 카드 vanish. **financeSource None-skip 패턴 재사용.**
- direction 은 `insight` 1줄(백엔드 직출력, UI 재합성 금지)로만 — 6칩 풀덤프 거부.
- **신규 가드 1 — "기타" 우세**(적대검증이 잡은 미설계 결함): `_CATEGORY_KEYWORDS`(L142-146)가 무매칭 라인을 무조건 "기타"로 던짐 → 다각화 제조사는 최대막대가 의미불명 기타가 되어 카드 약속("원가율 상승 원인 분해")이 깨짐. **기타 ratio >40% → '성격별 입자도 낮음' 라벨 또는 미렌더.** 이 가드 없이는 honest-gap 위반.
- **신규 가드 2 — 단위/주기 정합**(F2b 배지): `_inferNoteUnitScale` 을 ratio 前 적용(1000× 거짓괴리 방지), 배지는 note period == salary year 정확 일치 시에만.

### 3.3 F2b — 인건비↔급여총액 정합 (조건부 1줄, 한국 DART 고유)
- 두 독립 표 교차: 주석 인건비(NT_D834300 종업원급여+퇴직+복리후생) vs employee parquet `fyer_salary_totamt`(직원급여만, reportSource buildWorkforce L100-126, q4 게이트로 부분연도 차단). **self-vs-self 2-table, peer/섹터 아님.**
- 배지 = scope *기술*만(귀속 금지): '주석 인건비(임원·복리후생·생산직 노무비 포함) X조 vs 직원급여총액(직원만) Y조 — 집계범위 다름'. **"왜 큰가"의 인과 귀속(외주/자본화/임원보수) 삭제** — honestyCeiling 이 금지한 단정, 비전문가가 사실로 오독.
- **proxy 라벨 필수**(적대검증 CRACK): `scanWorkforceSalary`(scanner.py L185-227)가 `fyer_salary_totamt` 결측 시 `sm×jan_salary_am`(직원수×평균) fallback + 반기 ×2 외삽 → 그 slice 는 '괴리'가 추정오차일 뿐. fallback 발화 시 배지 = **'근사 정합'**(bare '정합' 금지). 단일-최신년 only(salary 시계열 없음 — 다년 정합은 F1 의존 follow-on, '백엔드 0' 청구 금지).
- **조건부 강등**: F2b 는 *항상 붙는 둘째 겹* 아님 — 인건비 카테고리가 '기타'에 안 먹히고 깨끗 분리 + q4 사업보고서 해 + 단위정규화 동시 충족 시에만 1줄. 아니면 사라짐(F2 본체는 단독 렌더). 두 질문 영구 용접 금지.

### 3.4 정직 천장
- 커버리지 ~6%(173사, 제조업 편중). 부제 고정 라벨 '제조업 등 주석 공시사 한정(~6%)'. 금융/REIT/지주 = 구조적 미공시 → 카드 자체 사라짐(— 아님). NEVER-CLAIM: 전상장사 비용구조 주장 금지·점수/등급/radar 금지·동종백분위 금지(industry-lab/fin-stmt-lab 경계)·시계열 백분위 금지·gap 의 인과귀속 단정 금지.

---

## 4. F3 — 희석 overhang: DEFER (2-gate, 명시 블로커)

- **이미 surfaced(재제안 금지)**: capitalChange 전환권행사/신주인수권행사 = 실현된 희석이력, RETURN 탭 `DilutionYear` 카드(reportSource L506-547). 만기 사다리도 surfaced(finTabs L281, instrument-type 구분없어 convertible 분리 불가).
- **신규 후보 = 미전환 전환사채 잔량(예고된 희석)** — 그러나 **데이터층 BLOCKED**: reportSource.ts(adapters/public/sources)는 report parquet만 읽고 **note-cell 접근 0**. NT_D822450 carrying value 는 Python L2 엔진에만 존재 → 엔진콜/신규 parquet sink 필요 = 'no-backend' 금지와 충돌. 게다가 noteTaxonomyData.py 가 일반사채·전환사채·BW 를 **같은 코드 NT_D822450** 에 매핑 → numerator 를 일반사채와 분리 불가(본문파싱 필요, 거부). 희석률 % = 이중-내러티브(convertible-vs-bond split 미구조 + 전환가 미구조) = **거짓정밀**.
- **2-gate 로드맵**: GATE 1(백엔드, 이 PRD 밖) = per-company convertible carrying-value sink, NT_D822450 의 convertible/BW/EB 라인을 일반사채와 disambiguate(세그먼트를 막은 *동일* XBRL 축-vs-행라벨 문제). GATE 2(GATE 1 후) = **잔액(원)만, % 절대 금지**, 기존 희석이력 카드 footer, latestRcept 추적, appears-only-when-clean. 실현 커버리지는 segments-grade(2/10) 추정 → DEFER 강화. **정직한 부재 > 거짓 12%.** 코리아디스카운트 거버넌스 가치는 진짜라 로드맵 유지.

---

## 5. F4 — 23 주석 카테고리: CUT (뷰어 원문 전속)

- 사용자 "주석에 다양한 정보"를 **정확히 1개**(F2/F2b 인건비 정합)로 honor, 나머지 **23개 거부**: 담보제공자산·채무보증·충당부채 movement·특수관계자거래·우발부채·리스·파생·스톡옵션 outstanding.
- 거부 근거 2축: (1) **narrative-only** — `relatedPartyTx`/`notesDetail`(company.py)이 구조화 파싱 명시적 은퇴, wide raw/본문만 반환. (2) **cross-company 축 깨짐** — noteTaxonomyData.py 가 같은 제목→다른 NT 코드 회사별 매핑(담보제공자산 = NT_D822320 OR NT_D827580, 우발부채 827580/822320/822470 분산). dossier 카드로 올리면 '비교가능'이라는 거짓 신뢰.
- 거처 = **헤더 리본 ↗원문 anchor only**(03 §5 / 05 Phase 0 의 ↗ 재사용). 카드/섹션/리본 줄 0. 04 line 33(담보 BLOCKED)을 NEVER-CLAIM 으로 확장·grep 가드.

---

## 6. 데이터 준비도 (07 델타 — 04 위)

| 데이터 | 분류 | 커버리지 | 진짜 작업 |
|---|---|---|---|
| 배당 frmtrm/lwfr/rcept_no | **structured-ready** | 4분기 배당 공시사 | dividend SELECT 에 3컬럼 추가 + chainTriplet. workforce/treasury/ownership 파케이 = triplet 미populate(dead code, 미배선) |
| 비용 성격별(NT_D834300) | **NEEDS-PARSING/CI-bake** ⚠(08 G1 정정 — 옛 'structured-ready'는 오류) | ~6%(173사, 제조업, Phase-0 probe로 재측정) | `calcCostByNatureAnalysis`는 note-cell(`fetchNotesDetail` Python L2)을 읽어 공개 터미널 도달 불가 — F3 희석과 *동일 벽*. CI가 `report/costByNature.parquet` bake → reportSource가 *그 parquet* read(엔진 아님). F4 rndIntensity와 단일 bake 의존 |
| 인건비 정합(주석 vs fyer_salary) | **structured-ready** | F2 ∩ payroll, 단일-최신년 | 양변 live. proxy/단위/주기 가드. 다년=F1 의존 |
| 미전환 전환사채 carrying(NT_D822450) | **BLOCKED** | segments-grade(~2/10) | reportSource note-cell 접근 0 + convertible/bond 동일코드. GATE 1 sink 선결 |
| 23 주석(담보/보증/충당부채/RPT/...) | **narrative-only / 축깨짐** | varies | 뷰어 원문 ↗ only. dossier 비승격 |

---

## 7. NEVER-CLAIM 확장 (04 §3 위, grep 가드 신규 토큰)

- "8-12yr"·"2-3x 시계열"·"12년" 배지 = 차단(실이득 1.4x 배당한정).
- 충돌 정정 평균/블렌딩 = 금지(아무도 보고 안 한 수 날조).
- 정정값 '진실'·proxy해 primary 동일가중 = 금지.
- gap 인과귀속('외주/자본화/임원보수 추정') = 금지(scope 기술까지).
- 희석 % 단정·전환가 추정 환산 = 금지(DEFER).
- 23 주석 '구조화 비교가능' = 금지(축 깨짐).
- 비용구조/인건비 gap → 점수/등급/radar/buy-sell = 금지.

---

## 8. 영향 파일 (구현 착수 시)

**F1(브라우저, P1)**:
- `reportSource.ts` buildShareholderReturn — dividend SELECT `['se','stock_knd','thstrm','frmtrm','lwfr','rcept_no']` + `chainTriplet()` closure(~40 LOC, latestRcept 형제). 다른 5빌더 불변.
- `contracts/finance.ts`·`report.ts` — `FinSeries.mark?` + `ShareholderReturnYear.prov?` (additive optional).
- `MiniFinChart.svelte` — `<pattern id="hatch">` 1개 + `s.mark?.[i]` 분기 + tooltip prov 1줄.
- `finTabs.ts` shareholderReport `note` 1절 + cardGuide 빗금/hollow 범례.

**F2/F2b(엔진+브라우저, P2)**:
- `report.costByNature(code)` 포트 — ⚠ 엔진 직접 래핑 아님(08 G1): CI-baked `report/costByNature.parquet`를 reportSource가 read(F4 rndIntensity와 단일 bake 작업). 엔진은 bake 시점에만 호출.
- `finTabs.ts` FS_TABS[0]에 `load: profitReport` + `profitReport` 빌더(100% stacked, 기타>40% 가드, F2b 조건부 배지).
- `_inferNoteUnitScale` ratio 前 적용 확인.

**테스트/가드**:
- F1: clean 삼성 2018-2024(체이닝 길이>raw, 마커0) + 정정 케이스(빗금1, tooltip 양값, canonical=최신). 단위-drift 거짓정정 가드.
- F2: None→미렌더, 기타>40% 라벨, F2b proxy→'근사 정합', 단위 1000× 가드.
- NEVER-CLAIM grep 확장.

---

## 9. 평가 (개발자 + PM 렌즈)

**개발자**: 최대 위험 = ① **체이닝 정정 reconciliation**(happy-path 아닌 진짜 위험) — naive frmtrm_N vs thstrm_{N-1} 는 K-IFRS 전환/정정공시에서 거짓말. report-fact 용 overlap 탐지 부재 → 2%/0.5pp gate + latestRcept + 빗금 정직성이 게이트(polish 아님). reconcile 없으면 긴 x축=날조. ② **fy 앵커** raw year(기수 오염) 금지, rcept-derived 강제 — 단일 오앵커가 전 시계열 silent 오stitch. ③ **단위-drift** 정규화 chaining 前. ④ **"기타" 우세** >40% 가드(신규 필수, restatement 다음 최고확률 silent 실패). ⑤ **proxy denominator** sm×salary fallback 이 forensic 괴리로 위장 → '근사 정합'. ⑥ note-cell 은 reportSource 도달불가(F3 BLOCKED 정직 인정). 재사용 지도 정밀(새 셸 0, 검증된 패턴 5종 합성).

**PM**: 사용자 양대 명령("당기/전기 이어서 panel IS처럼" + "비용 성격별 시계열 병합") 정확 대응. ROI 탁월 — F1 은 *데이터층 1.4x*(새 fetch 0, 검증된 auditFees 패턴 일반화), F2 는 *완성 엔진 배선*(백엔드 0), 둘 다 순 패널 0. **컷라인**: F1(체이닝, MVP 간판) + F2(비용성격별, 제조업 thin-but-clean). F2b 는 조건부(양변 clean 시만). **F3 DEFER**(numerator sink 선결, 거짓 % 금지). **F4 CUT**(23주석 뷰어 전속). 정직 다운그레이드 수용 — "8-12yr·2-3x" 헤드라인 거부가 PM 강제 정직계약. 데모 게이트 = 정정 케이스 + 제조업(F2 점등) + 은행(F2 깨끗한 부재) + 소형주(체이닝 degrade=현행). 경계 소비만(fin-stmt-lab 이익품질/diluted-EPS, industry-lab 섹터, cross-universe 단일시점). UI push 운영자 게이트.
