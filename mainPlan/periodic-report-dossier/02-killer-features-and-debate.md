# 02 — 간판 기능 + 전문가 토론·적대검증 평결

> 13인 토론(도메인 5 + 적대검증 5 + UI/UX 2 + 종합 리드) 산물. 각 섹션은 도메인 전문가의 killer 제안 → 적대검증의 컷/생존 → 최종 기능으로 수렴.

## 기능 세트 (우선순위·데이터준비도·소유근거)

| # | 기능 | P | 데이터 | 새 fetch | 소유 근거 |
|---|---|---|---|---|---|
| F1 | `rcept_no` 도시에 스파인 + as-of 헤더 리본 | **P0** | structured-ready | 0(컬럼추가) | 비재무 정기보고서 출처추적 스파인 — 다른 PRD 미접촉 |
| F2 | 환원 흐름(소각 vs 금고) 주주환원 리프레임 | **P0** | structured-ready | **0** | 자사주 취득/소각/처분 수량 = 밸류업 질문, 타 섹션 미소유 |
| F3 | 타법인출자 lossPct + control-shift 한 줄 | **P1** | structured-ready | **0** | 단일사 소유 웹(industry-lab=섹터 집계만) |
| F4 | 인력 자기이력 프레임 + R&D 집약도 행 + `상세보기` | **P1** | needs-parsing | 0(R&D 제외) | 인적자본 + forward-investment 운영현실 |
| F5 | 인적자본 유니버스-백분위 축(죽은 엔진 배선) | **P2** | structured-ready | CI bake | 기존 백분위 머신에 1축 추가, 단일시점 |
| F6 | 의미층 글로서리(CARD_GUIDE 올라가면/내려가면 리프레임) | **P1** | structured-ready | 0 | 이 PRD 팩트들의 so-what 층 |
| F7 | 가동률·생산설비 원문 발췌(narrative, 미추출 명시) | **P3** | narrative-only | 0(zero추출 한정) | 가장 어려운 갭, 추출 대신 원문만 |

---

## 섹션 1 — 인력·생산성 (F4·F5)

**도메인 killer**: "인적자본 효율 vs 유니버스" — value-added-per-employee(영업이익+급여 proxy) + 급여매출괴리(급여성장 − 매출성장 %p)를 회사의 *유니버스 백분위*로, 자기 3년 궤적과 함께. *새 카드 격자 아님, 종합등급 아님.* 죽은 엔진함수(`scanValueAdded`/`computeSalaryVsRevenue`)를 baked 분위 배열로 배선하는 것이 환원 불가능한 한 수.

**적대검증 평결**:
- ✅ in-code 검증: 엔진함수 전부 존재, `scanRevenuePerEmployee`만 baked, 나머지 dead-wired — 중심 전제 참.
- ⚠️ **분모 천장 더 낮다**: `scanValueAdded` 는 payroll∩employee∩opIncome **교집합**(각 게이트가 회사 탈락, 소형주 먼저). baked 배열은 **글로벌 N 아닌 축별 실제 교집합 N·asOfYear·gate** 를 스키마 필드로 강제 — 전상장사 커버 규칙의 실행화.
- ⚠️ 급여매출괴리 2년·이중게이트(각 연도 ≥500 valid)·±500% clamp → "추세" 아님, 단일 분포 사실로만.
- ❌ **컷**: 백분위 밴드 *안*의 3년 스파크라인(시계열 백분위 = scenario-simulator 경계 침범, cross-universe-percentile/04 가 KILL). 자기이력 궤적은 *물리적으로 분리된* PEOPLE 탭/인라인 lane 에서만.
- ❌ **컷**: 임원/직원 보수배율을 카드/섹션으로 → PEOPLE 디테일 안 한 줄로만(4분기·5억+ sparse 라벨).
- ❌ **컷**: 좋은고용주 등급·인적자본 점수·레이더.

**최종(F4)**: ① 인력 패널에 누락된 `상세보기`(.finFullBtn) 추가 → FinFullscreen PEOPLE. ② `wfLast` 평면을 `wf[]`(이미 메모리) 자기이력 문장으로: "정규직 90%→90% · 근속 +0.6년 vs 3년전 · 인원 +2%(매출 +9% → 1인당 매출 ↑)". ③ R&D 집약도 1행(텍스트 추세 ↑/↓/→, 소스 태그 IS vs SG&A주석, 미공시/해당없음 절대 0 아님). **최종(F5)**: baked 분위 배열{N,asOfYear,gate} → 기존 백분위 머신에 단일시점 1행(부가가치=higher-better+proxy 라벨, 급여매출괴리=DistCurve neutral 그레이핀).

---

## 섹션 2 — 주주환원 (F2)

**도메인 killer**: "환원 흐름 막대" — 연도축으로 취득·소각·처분·배당을 누적하되 핵심 분기는 **소각(영구·짙은색) vs 금고 보유(취득−소각−처분, 옅은 빗금)**. 한 화면에서 'A=매입 90% 소각→주식수 실제 감소' vs 'B=전부 금고 후 일부 재매각=화장 환원·잠재 희석'. `buybackCancel`·`disposalQty`·`buybackQty`·`treasuryEnd` 전 연도 배열이 이미 fetch 되어 **버려지는 중**.

**적대검증 평결**:
- ✅ "새 fetch 0" 문자 그대로 참(`buildShareholderReturn` L207-248 전 배열 fetch, RightStack 은 `srLast` 만 렌더).
- ⚠️ **커버리지 낮음(실측)**: treasury 경로가 `acqs_mth1='총계' AND stock_knd='보통' AND quarter='4분기'` 필터 → 소형주 다수는 4필드 전부 null. **빈상태가 default 렌더('미공시·해당 자사주 거래 없음·연 단위·사업보고서 기준')**, 에러 아님.
- ❌ **컷**: 시총분모 총주주환원율(gov price T+1·2020+, stale·거짓정밀). FCF 분모(returnToFcf)는 적절하나 그건 P3(CF 배선). **CF 배선 전까지 지속가능성 비율 표시 0** — 흐름막대 + 발행주식수 변화%만으로 완결.
- ❌ **컷**: same-year "취득의 X% 소각" 비율(buybackQty=0 인데 buybackCancel>0=전년 매입 소각 케이스에서 undefined) → **누적 취득 대비 누적 소각** 으로 계산.
- ❌ **컷**: `capitalChanges.reduction` 교차검증을 *사용자向* 으로 → 침묵 데이터품질 게이트로만(두 숫자 노출=덕지덕지).
- ❌ **defer**: 섹터 분포 사실("소각하는 회사 X곳") = industry-lab 경계 한 발, v1 제외.

**최종(F2)**: `srLast` 평면 격자 → ① 우측 레일 = 판정 없는 자기정규화 문장 1줄 "취득의 X%가 소각 · 발행주식수 −Y% · N년 연속배당"(각 토큰 non-null 일 때만, 발행주식수%는 `ownership.stockTotal` 있을 때만). ② 환원 흐름 막대(소각/금고/처분 2색+빗금, MiniFinChart SVG)는 **FinFullscreen RETURN 탭**(center-stack, 그래프 합법), 우측 레일 아님. ③ `상세보기` 추가. ④ 배당 streak 정수 1개. ⑤ 빈상태 first-class 디자인.

---

## 섹션 3 — 타법인출자·소유 (F3)

**도메인 killer**: "이 회사 자본이 어디로 흘렀고, 결과가 무엇이며, 누가 지배가 바뀌었나" — `HoldingsDialog` 양방향 관계망(forward 출자 tier + reverse 주주 + 상호출자 ↔)은 이미 세계급. 핵심은 *발견을 한 클릭 앞으로* 당기는 것: lossPct·contribShare·pctOfParentCap·control-shift 가 전부 다이얼로그에 갇혀 있다.

**적대검증 평결**:
- ✅ "전부 이미 계산, 표면화만" in-code 참(0-fetch 진짜).
- ❌ **심각 — `contribShare` 헤드라인 컷(현 제안 그대로)**: 분모 `parentNet=mktcap/PER`(시장함축 순익, 다이얼로그가 이미 hedge). 상시 헤드라인 승격=추정의 prime fact 둔갑(honest-gap 의 역). 보고 `fin.is.net` 재배선 또는 라인 삭제.
- ⚠️ pctOfParentCap **self-gate**: `lookupListed` 가 상장 피출자만 해소 → 비상장 다수 소형주는 null/오해소지. **listed 커버리지 material 일 때만 렌더, 아니면 라인 자체 suppress**(0-fill·null-render 아님). 지주/재벌 모회사(killer use)엔 세계급, 독립 소형주엔 침묵.
- ✅ **lossPct = 가장 강한 생존자**: lossBook/bookTotal, 시장조회 불필요, 전 2,800사 동작(장부가 항상 존재), 판정 없음, 가장 national-salient 포렌식(부실 계열사에 묶인 자본). **항상 켜진 단 하나 앵커.**
- ✅ control-shift = 0-fetch·법인기관 한정(개인 익명 집계). 명시 기간 라벨(YYYYqQ→YYYYqQ)이면 terminal-improvement(visit-delta)·fin-stmt-lab(peer) 경계 안전.
- ❌ **컷**: 출자 장부가합 micro-스파크라인(우측 레일 그래프 금지 + 장식). 상호출자 K건 헤더 배지("순환출자=K" 오독 유발, 다단 미탐지) → 다이얼로그 ↔ 커넥터 안에서만.
- ❌ **헤더 2줄 cap**: 4줄=덕지덕지. lossPct(항상) + {control-shift OR value-gated} 중 1.

**최종(F3)**: 타법인출자 패널 헤더(5컬럼 표 불변, →HoldingsDialog 깊은 층): ① 항상 lossPct "적자 피출자사 = 출자 장부가의 M%". ② control-shift "최대주주측 42%→51%(’21→’24) · 신규 법인주주 K" (`controlShiftSummary(periods)` 순수 helper). ③ pctOfParentCap 은 self-gate 통과 시만. contribShare 는 보고순익 재배선 시만, lossPct 아래 altitude.

---

## 섹션 4 — 생산·설비·R&D·세그먼트 (F4 R&D · F7 가동률)

**도메인 killer(데이터 한계 명시)**: 이 영토는 *가장 얇다*. 생산능력/가동률=구조화 컬럼 0(narrative). 세그먼트=4.6%만 clean. R&D=59.7% 유일한 진짜 승. → killer = R&D 집약도 1행(인력 패널), + 가동률은 원문 발췌만.

**적대검증 평결**:
- ❌ **제안 오류 정정**: "`calcRndExpense` 를 graduate" = FALSE. *이미 완성 엔진*(9섹션·@memoizedCalc·available-flag). 진짜 일 = CI-baked rndIntensity parquet + reportSource 5번째 hyparquet read + `report.rndIntensity(code)` 포트. **엔진 재구축 금지.**
- ⚠️ **공개 배선이 hand-wave**: R&D 는 어떤 scan/report parquet 에도 없음(IS라인+주석). 공개 터미널(HF·Python 없음)=consolidation/CI 에서 rndIntensity 컬럼 bake 필수. 로컬은 `calcRndExpense` live 가능하나 **동일 parquet fallback**(공통배선, 로컬전용 금지).
- ❌ **industry-lab 경계 실재**: `recipes/industry/rdIntensityTrend.md` 가 이미 섹터 백분위·peer cross-section 소유. 이 카드는 **회사 자기 숫자+자기 추세만**, 섹터 밴드는 industry-lab **소비**(재계산 금지, n=·'of disclosing peers' 라벨).
- ❌ **컷**: 5-10yr 스파크라인 → 텍스트 추세(↑/↓/→ + 전년 Δ). 우측 레일 그래프 금지.
- ❌ **컷**: 범용 세그먼트 카드(4.6%→95% 쓰레기), 가동률 숫자·차트(날조), 원재료 가격패널, 운영건강 등급.
- ⚠️ F7(가동률 원문 발췌): **zero 추출일 때만 ship**(뷰어가 이미 섹션 텍스트 렌더 → anchor+label). 새 파싱 필요하면 컷.

---

## 섹션 5 — 정기보고서 팩트 스파인 (F1·통합)

**도메인 killer**: 모든 팩트를 `rcept_no` 로 출처 공시에 바인딩, 비재무 스택을 **하나의 날짜 박힌 도시에**로. 평면 `DART 정기보고서 팩트` 패널 → as-of/기간/출처추적 리본(N/6 공시·약 N개월 전·↗원문). 28개 흩어진 덤프 → 하나의 읽히는·탐색 가능한 사업보고서. **강함=빼기**(중복 평면 패널 흡수).

**적대검증 평결**:
- ✅ in-code 참: `companyLive.ts L281-322` 가 `rcept_no` 안 SELECT, parquet 행엔 존재. `viewerUrl()`+`openFiling` 딥링크 이미 양 런타임 동작. **P0 = 줄단위 언락**.
- ⚠️ **딥링크 mis-route 정정**: `rt.viewer.urlForCompany`(설계상 null) 아님 → `viewerUrl(marketForCode(code), rceptNo)`.
- ✅ **순 패널 DOWN**: dividend/treasury 가 평면 패널 + 주주환원 패널 중복 → 리본 흡수=진짜 빼기.
- ❌ **컷**: '스파인' 깃발 아래 밀반입된 ~3 신규 분석 카드(총주주환원율·payout-vs-CFO·dilution-net + 새 capitalChanges fetch). 이건 *더하기*. 밸류업 read 는 주주환원 섹션 안 **한 줄**로(카드 아님). capitalChanges 새 fetch = v2 로 defer.
- ✅ **honesty 계약(폴리시 아닌 필수)**: 섹션별 N/6 커버리지 + '미공시(해당 항목 없음)' + '약 N개월 전' staleness 라벨. 데모는 3/6 소형주 필수(삼성 아님).

**최종(F1)**: `rcept_no`+`stlm_dt` 를 6 SELECT + `LiveCompanyReportFact` contract 에 추가; 평면 팩트 패널 → 도시에 헤더 리본 "사업보고서 {stlm_dt} · 접수 {rceptDate} · N/6 공시 · 약 N개월 전 · ↗원문"; 4 섹션 패널을 도시에 섹션으로(각자 ↗ + 자기이력 Δ). 리본이 as-of 를 전역 1회 스탬프 → 숫자별 날짜 각주 불요(섹션 sub 는 자기 연도 유지).
