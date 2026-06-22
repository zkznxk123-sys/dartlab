# 08. 결측 데이터 해결책 — 항목별 구체 경로 (★운영자 챌린지 대응)

상태: **v0.4 (2026-06-22)** — "없는 데이터는 어떻게 해결할 건가" 챌린지 대응. v0.3가 결측을 "정직하게 빈다"로 *회피*만 한 것을 정정 — **실제 미국 출처를 항목별로 규명**하고, dartlab이 *이미 가진 것*과 *신규 필요*를 코드로 가른다.

> ★핵심 발견(코드 직접 확인): v0.3의 "permanent EXEMPT" 분류가 대부분 **틀렸다**. EDGAR는 KR report 17 apiType 중 **14개를 이미 회사단위로 추출**(`accessor/reportAccessor.py` `_SUPPORTED`)하고, SIC·자기주식·executivePay 추출기가 이미 있다. "없는 데이터"의 진짜 정체 = ① *출처가 다를 뿐 존재*(대부분) ② *추출기는 있는데 scan 빌드/메서드 배선만 안 됨* ③ *구조적으로 다른 소수*(가치사슬 엣지·재벌 계열·전임원 보수). "정직하게 빈다"는 ③에만 적용, ①②는 **실제로 채운다**.

---

## 1. 결측 데이터 4분류 (회피가 아닌 해결)

| 분류 | 의미 | 본 PRD 처리 |
|---|---|---|
| **A. 추출기 있음 — 배선/빌드만** | dartlab이 이미 US 추출 코드 보유, 메서드/scan만 미배선 | **채운다**(코드 있음, 작업=배선·aggregation) |
| **B. US 출처 명확 — 신규 파서** | SEC form/XBRL에 데이터 있으나 dartlab 파서 미작성 | **채운다**(출처 확정, 작업=파서 신설) |
| **C. 구조적 부분/US-native 재정의** | KR과 개념이 달라 1:1 불가, US-native 등가물로 정직 재정의 | **US 버전으로 채운다**(KR이라 주장 안 함) |
| **D. 라이선스/진짜 불가** | 재배포 금지 데이터거나 US에 등가 없음 | **정직하게 빔** or 대체출처 |

## 2. ★항목별 해결 매트릭스 (KR 결측 → 미국 출처 → 해결경로)

### report 17 apiType — [대정정] 영구 EXEMPT 아님
[확인] `accessor/reportAccessor.py` `_SUPPORTED` = **14개 추출기 이미 작동**(dividend·treasuryStock·stockTotal·employee·auditOpinion·corporateBond·executive·majorHolder·executivePay·capitalChange·outsideDirector·minorityHolder·investedCompany·debtSecurities). KR `SCAN_API_TYPES` 17개와 대조:

| KR apiType | EDGAR 현 상태 | 미국 출처 | 분류 |
|---|---|---|---|
| majorHolder(대주주) | ✅ 추출기 `majorHolder.py` | SC 13D/13G + XBRL EntityPublicFloat | **A** |
| minorityHolder(소액주주) | ✅ 추출기 | XBRL/10-K | **A** |
| executive(임원현황) | ✅ 추출기 `executive.py` | 10-K Item 10 / DEF 14A | **A** |
| employee(직원) | ✅ 추출기 `employee.py` | 10-K Item 1(직원수) | **A** |
| outsideDirector(사외이사) | ✅ 추출기 `outsideDirector.py` | DEF 14A 이사회 | **A** |
| auditOpinion(감사의견) | ✅ 추출기 `auditOpinion.py` | 10-K Item 8 auditor report | **A** |
| dividend(배당) | ✅ 추출기 | XBRL `*DividendsDeclared` | **A** |
| treasuryStock(자기주식) | ✅ 추출기 `_extractTreasuryStock` | XBRL `TreasuryStockShares` | **A** |
| capitalChange(자본변동) | ✅ 추출기 `capitalChange.py` | XBRL `StockIssued/Repurchased` | **A** |
| corporateBond(회사채) | ✅ 추출기 `corporateBond.py` | XBRL debt + 10-K | **A** |
| investedCompany(타법인출자) | ✅ 추출기 `investedCompany.py` | XBRL `InvestmentsIn...Subsidiaries` | **A** |
| executivePayAllTotal/Individual(임원보수) | ⚠ 추출기 `executivePay.py`(XBRL 보상 aggregate) | XBRL ShareBasedComp + **DEF 14A Summary Comp Table(NEO5)** | **C**(US=NEO5만, 전임원 불가) |
| auditContract/nonAuditContract(감사보수) | ❌ 미구현 | **DEF 14A** auditor fees(Audit/Non-Audit Fees) | **B**(DEF 14A 파서) |
| shortTermBond/commercialPaper(단기사채·CP) | ⚠ `debtSecurities.py` 근사 | XBRL `CommercialPaper`/`ShortTermBorrowings` | **C**(세분 다름) |

→ **report = 14/17 추출기 작동(분류 A), 2개 DEF 14A 파서 신설(B), 1개 NEO5 구조차(C). "영구 EXEMPT" 0개.** 갭 = ① `executivePay()` 등 일부 메서드 미배선 ② **scan 단위 `edgar/scan/report/*` cross-sectional bake**(추출기를 전종목 aggregate — 신규 build, 데이터는 있음).

### sharesOutstanding 17-col — [정정] 1값 아님
[확인] `capitalChange.py`가 `CommonStockSharesIssued`/`TreasuryStockSharesAcquired`, `majorHolder.py`가 `CommonStockSharesOutstanding`/`EntityPublicFloat` 파싱. XBRL us-gaap 보유 개념: `CommonStockSharesAuthorized`(수권)·`Issued`(발행)·`Outstanding`(유통)·`TreasuryStockShares`(자기주식)·`PreferredStockShares*`(우선주). → KR 17-col 중 **authorized/issued/outstanding/treasury/preferred ~6-8col 복원 가능**(분류 A/B). "1값 부분 EXEMPT"는 과소평가였음 — 진짜 불가는 KR 고유 세부분류(액면·종류주 세분) 소수.

### sector / rank — [정정] SIC 있음
[확인] `bulk/datasetBulk.py:75 "sic": pl.Utf8` — **SIC 코드가 EDGAR bulk에 이미 존재**(SEC submissions 헤더, 전 종목 무료). 해결: **SIC(4자리)→DartLab US sector crosswalk**(공개 SIC division/major-group 기반 자체 분류, GICS 라이선스 회피) 구축 → sector 채움(B). rank = sector 확정 후 scan 데이터로 peer 백분위 계산(A, scan-finance 재사용). **GICS는 라이선스(D)라 안 씀 — SIC-derived 정직 라벨.**

### network(계열사) — [정정] US-native 재정의
[확인] `company.py:4571 network()` placeholder(None)이나 docstring이 "SEC ownership/Form 13F 향후"라 자인. US 출처:
- **Exhibit 21(Subsidiaries of the Registrant)** — 거의 모든 10-K 첨부, 자회사 목록(법인명·관할). dartlab 미파싱 → **신규 파서(B)**. = 모회사→자회사 트리.
- **SC 13D/13G**(5%+ 보유), **13F**(기관 보유), **Form 3/4/5**(내부자 지분) — 보유 네트워크(B).
- 정직 한계(C): 한국 *재벌 계열*(순환출자·교차지분)은 US에 구조 부재 → "계열사"가 아니라 **"자회사(Exhibit 21)+주요 보유자(13D/G/13F)" US-native 네트워크**로 재정의. KR이라 주장 안 함.

### industry(가치사슬 지도) — ★유일하게 진짜 어려운 항목 (C/D 경계)
KR은 운영자 수동 큐레이션(공급망 엣지). US 분해:
- **산업 *분류*** = SIC/NAICS로 즉시(B, 위 sector와 동일 소스).
- **가치사슬 *엣지*(공급사→고객)** = US에 깔끔한 무료 데이터 없음. 경로 후보: ① 10-K **major customer 공시(ASC 280, 매출 10%+ 고객명)** 텍스트 파싱 ② segment 공시 ③ 10-K Item 1 "Competition" NLP. **신뢰도 낮음·커버리지 부분**(D 경계).
- **정직 처리**: US industry는 *분류·peer 격자*(SIC 기반)까지 채우고, *공급망 엣지*는 "major-customer 공시 기반 부분 그래프(저커버리지 명시)" 또는 비활성. **여기가 "정직하게 빈다"가 진짜 적용되는 소수 지점.** 발명(FactSet식 합성) 금지.

### relatedPartyTx(특수관계자) — B
미국 출처: **10-K/DEF 14A Item 13 + 재무제표 주석 ASC 850**(RelatedPartyTransaction XBRL 멤버). [확인] `docs/sections`가 10-K item 파싱하므로 Item 13 추출 가능 → 신규 파서(B). 단 EDGAR 메서드 미존재(baseline missing).

### scan changes(공시 변화) — B
KR=panel 본문 YoY 텍스트 diff. US=`edgar/sections`(10-K item content_plain) YoY diff. [확인] sections 존재 → item 경계 기준 diff 신규(B, 03 S2-L0.2).

### credit sector thresholds — A
[확인] `credit/features/sectorThresholds.py` KR WICS 임계. US 해결: **SIC-derived sector(위) 확정 후 US 종목 scan 데이터로 sector 중앙값 재캘리브** → `_usDefaultThresholds()`. 데이터는 scan-finance에 이미 있음(A). credit 침묵 garbage(S1-L4.3) 가드와 함께 정합.

### US 가격 baked — D(라이선스 조사 필요)
재배포 가능 무료 EOD 후보: **stooq**(EOD 무료, 재배포 회색)·**Tiingo/Alpha Vantage**(API 무료티어, 재배포 제약)·**Nasdaq Data Link**·SEC(가격 미제공). [확인] dartlab엔 baked 부재(라이브 yahoo/fmp만). **착수 시 각 소스 ToS 실조사 필수**(S2-L0.3). 합법 재배포 소스 없으면 옵션 C(가격 US 비활성) 정직 유지.

## 3. 종합 — "없는 데이터" 재분류 결과

| 원 분류(v0.3) | 항목 | v0.4 실제 | 해결 |
|---|---|---|---|
| permanent EXEMPT | report 17 | **A 대부분**(14 추출기 작동) | scan bake + DEF14A 2파서 + 메서드 배선 |
| permanent EXEMPT | sector/rank | **B/A**(SIC 있음) | SIC→sector crosswalk + peer 계산 |
| permanent EXEMPT | network | **B/C**(Exhibit21·13D/F) | 파서 + US-native 재정의 |
| permanent EXEMPT | industry | **B + C/D 경계** | 분류=SIC 채움 / 가치사슬 엣지=부분·정직 빈 |
| missing | executivePay | **C**(추출기 有, NEO5 한계) | 배선 + DEF14A 보강 |
| missing | relatedPartyTx | **B** | 10-K Item13/ASC850 파서 |
| 부분 EXEMPT | sharesOutstanding | **A/B**(XBRL ~6col) | XBRL 개념 확장 |
| 회색지대 | credit thresholds | **A** | US sector 재캘리브 |
| 갭 | scan changes | **B** | sections YoY diff |
| 미결정 | US 가격 | **D** | 라이선스 조사(불가 시 비활성) |

**→ 진짜 "정직하게 빈다"(D/불가) = US 가격(라이선스 의존) + 가치사슬 엣지(부분만) + 전임원 보수(NEO5 한계)뿐.** 나머지는 전부 *채울 수 있고, 대부분 추출기가 이미 있다*. v0.3의 "permanent EXEMPT 7항목"은 **1-2개로 축소**.

## 4. 단계 편입 (03 로드맵에)
- **Slice 1**: A분류(이미 추출기) 중 회사단위 표면(report 14·shares·credit 재캘리브) 배선 — 데이터 작업 적음.
- **Slice 2**: B분류 신규 파서(DEF 14A·Exhibit 21·relatedPartyTx·sections diff) + scan/report cross-sectional bake + SIC sector crosswalk + rank. 빌드부터.
- **Slice 3(신설)**: C/D 잔여 — industry 가치사슬 엣지(major-customer 부분 그래프)·US 가격(라이선스) — 정직 한계 명시, 최후순위.

## 5. 정직 경계 (05 §4 정합)
- 채운 데이터는 **US 출처를 라벨**(예: "sector: SIC-derived", "network: Exhibit 21 subsidiaries", "exec pay: DEF 14A NEO5"). KR 등가라 주장 금지.
- 가치사슬 엣지·전임원 보수는 **커버리지/한계 명시 표면**(저커버리지 부분 그래프 = "부분"이라 라벨, 비어도 정직).
- never-claim: "US 가치사슬 지도 완성"·"전임원 보수" 금지(구조적 부분만 가능).
