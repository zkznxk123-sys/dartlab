# 02c · 세그먼트 경제성 — 도출형 부문 마진 + SOTP 격상 스펙

> **위치**: 능력 엔진 P1 트랙 (밸류에이션 02a → 전망 02b → **세그먼트 02c** → moat → 신용).
> **사상**: 정직 스킵 = 능력부족. 부문 매출은 공시되는데 부문 영업이익이 없다고 *스킵*하는 것이 현재의 게으름이다. 프로는 *도출*한다 — 매출믹스 × 배분비용 × peer-segment 벤치마크로, "도출 추정 + 방법 + 범위" 라벨을 달아서. **금지 = 날조**(근거 0 의 임의 마진). 투명한 배분식 + peer 벤치가 붙은 도출 마진은 *분석*이다. SSOT 개선, 병렬 빌드 금지.

---

## 1. SSOT 지도 (file:line)

| 역할 | 위치 | 핵심 |
|---|---|---|
| 부문 매출/영업이익 calc 본체 | `src/dartlab/analysis/financial/_revenueSegment.py:127` `calcSegmentComposition` · `:237` `calcSegmentTrend` · `:350` `calcBreakdown` | segments dict + `hasOpIncome` 게이트 |
| 부문 시계열 select (도출 진입점) | `src/dartlab/analysis/financial/_revenueSelect.py:91` `_segmentSeriesFromNote` · `:160` `_selectDocsRevenue` · `:173` `_selectDocsOpIncome` | 부문 매출/영업이익 시계열 추출 SSOT |
| axisPath 부문 파싱 SSOT (L1) | `src/dartlab/providers/dart/panel/cell.py:224` `_segNameFromAxis` · `:246` `_isRevenueLabel` · `:253` `segmentRevenueExposure` · `:160` `_noteCellsFromPanel` | NT_D871100 주석 셀 → 부문 멤버 토큰 |
| 집중도/성장기여 | `src/dartlab/analysis/financial/_revenueGrowth.py:102` `calcConcentration` · `:185` `calcGrowthContribution` | HHI + 부문 성장 기여 분해 |
| 비용 성격별 분류 (배분 입력) | `src/dartlab/analysis/financial/_costStructureDeep.py:23` `calcCostByNatureAnalysis` | 원재료/인건비/감가상각 비중 (공통비 배분 베이스) |
| story 빌더 | `src/dartlab/story/builders/revenue.py:39` `segmentCompositionBlock` · `:97` `segmentTrendBlock` · `:459` `segmentForecastBlock` | calc → 블록 |
| SOTP NAV (지주사) | `src/dartlab/analysis/valuation/sotp.py:20` `calcSotpNav` · `:239` `calcHoldingDFV` | 자회사 장부가 NAV — *book-value*, 사업부문 SOTP 아님 |
| SOTP 표 (영업복합기업) | `src/dartlab/synth/damodaranL15.py:1242` `_sumOfPartsTable` | **현재 `deferredWithBlocker` 스텁** — 본 스펙의 표적 |
| peer 추출 | `src/dartlab/industry/calcs/peers.py:87` `industryPeers` | 동종 매출 상위 N — peer-segment 벤치 입력 |
| 부문 노출% (peer 벤치 입력) | `src/dartlab/providers/dart/panel/cell.py:253` `segmentRevenueExposure` · `src/dartlab/industry/themes.py:79` `themeRevenueExposure` | 부문토큰별 상대 노출% |
| SOTP recipe (계약·falsifier) | `src/dartlab/skills/specs/recipes/fundamental/valuation/damodaran/sumOfParts.md` | `forbidden: 세그먼트 근거 없이 임의 SOTP 금지` |

---

## 2. 오늘 추출하는 것 + 갭

### 2.1 진짜로 하는 것 (날조 아님)
- **부문 매출 시계열**: `_segmentSeriesFromNote(company, "revenue")` 가 NT_D871100(부문별정보) 주석 셀의 `axisPath` 부문 멤버(`OperatingSegmentsMember` 하위)를 매출행만 골라 연도별로 피벗. 축-태깅 DART 회사만 (`cell.py:234` 게이트). 단위 추론은 `_revenueSelect.py:61` `_inferSegUnitScale` 가 IS 총매출 대비 magnitude(1/천/백만)로 결정 — 진짜 공시값.
- **부문 영업이익 (공시될 때만)**: `_selectDocsOpIncome` (`_revenueSelect.py:173`) 가 동일 주석에서 label 에 "영업이익"/"영업손익" 포함 행만 추출. **부문별 OI 를 별도 공시한 회사만** 매칭.
- **마진 계산**: `_revenueSegment.py:195` `opMargin = opIncome / rev * 100 if opIncome is not None`. OI 없으면 `opMargin = None`.

### 2.2 갭 (정직 스킵 = 게으름)
- `_revenueSegment.py:213` `hasOp = any(s["opIncome"] is not None for s in segments)`. 이 `hasOpIncome` 불리언이 게이트다. **False 면 마진 컬럼이 통째로 사라진다** — `revenue.py:55` `if hasOp and seg.get("opIncome") is not None:` 가 영업이익·이익률 컬럼을 *조건부로만* 붙임.
- 즉 **KR 대부분 회사처럼 부문 매출은 공시하나 부문 OI 는 안 하면** → 매출 비중표만 나오고 *수익 구조 편중(어느 부문이 돈 버나)* 은 빈칸. 헬퍼 docstring(`:155`)이 "이익률로 수익 구조 편중을 본다" 라고 약속하는데 정작 그 입력이 없을 때 **도출하지 않고 침묵**한다.
- `_sumOfPartsTable` (`damodaranL15.py:1249`) 도 `segmentDisclosure: status=deferredWithBlocker` 로 영업복합기업 SOTP 를 *영구 보류*. 자회사 장부가 SOTP(`sotp.py`)는 지주사 전용이라 *영업부문*(삼성전자 DS/DX, LG화학 석유화학/첨단소재 등)을 못 다룬다.

**한 줄**: 부문 매출은 진짜 추출 → 그러나 OI 미공시 시 마진을 *도출하지 않고 스킵*. 이 스킵이 갭.

---

## 3. 도출 방법 (배분 알고리즘 + 데이터 소스 + peer 벤치)

부문 매출 `R_i` (Σ=R, 공시) 는 있고 부문 OI 가 없을 때, **연결 영업이익 `OI_total`(IS 공시) 을 부문에 배분**해 `OIhat_i` 범위를 도출한다. 세 추정자의 *합의 범위*를 낸다 — 단일 점추정 금지.

### 3.1 배분 추정자 (3종)

**(a) 매출가중 배분 — 하한(floor) / 균일 마진 가정**
> 모든 부문이 연결 평균 마진과 같다고 가정. `OIhat_i^rw = OI_total × (R_i / R)`. 결과 마진은 전부 동일(=연결 마진). *정보가 0 인 귀무가설*이라 floor·sanity 기준으로만. 단독 사용 금지.

**(b) peer-segment 벤치마크 — 핵심 추정자**
> 같은 부문을 *별도 회사로* 영위하거나, 그 부문 OI 를 공시하는 동종사의 마진을 외부 앵커로 쓴다.
> - 후보 풀: `industryPeers(stockCode, n)` (`peers.py:87`) → 각 peer 의 `_selectDocsOpIncome` 가 OI 공시 부문이면 그 `opMargin`, pure-play 면 연결 영업이익률.
> - 부문 ↔ peer 매칭: `segmentRevenueExposure` (`cell.py:253`) 의 부문토큰 + `themes.json` segmentKeywords(`themes.py`) 로 부문을 테마/산업그룹에 사상 → 그 산업그룹의 peer 마진 분포(중앙값·p25·p75).
> - 부문 마진 prior: `m_i^peer = median(peerMargins[segmentGroup_i])`. 범위 = `[p25, p75]`.
> - **합 제약 정규화(reconcile)**: peer 마진을 그대로 쓰면 `Σ R_i·m_i^peer ≠ OI_total`. 비례 스케일 `k = OI_total / Σ(R_i·m_i^peer)` 를 곱해 **연결 OI 와 일치시킴** (`OIhat_i^peer = k·R_i·m_i^peer`). 이게 "peer 가 알려주는 *상대* 마진 구조를 회사의 *실제* 연결 OI 에 묶는" 핵심 단계 — 상대구조는 외부, 절대총합은 공시.

**(c) 자산/CapEx 집약도 가중 (부문 자산 공시 시)**
> NT_D871100 에 부문별 자산(`_isRevenueLabel` 의 음판 — "자산" 라벨 행)이 있으면, 자본집약 부문일수록 감가상각·금융비용 부담이 커 마진이 낮다는 사전(prior). `weight_i = (R_i/R) / (Asset_i/Asset)` 로 매출가중을 자산집약도로 보정. 부문 자산 미공시면 skip(가산 정보 없음, 침묵 아님 — (b)로 충분).

### 3.2 합성 → 범위
- 점추정: `OIhat_i = OIhat_i^peer` (peer-reconciled 가 주). (a)는 floor, (c)는 tilt.
- **범위**: peer p25/p75 를 reconcile 스케일 `k` 로 함께 변환 → `[OIhat_i^low, OIhat_i^high]`, 마진 범위 `[m_i^low, m_i^high]`.
- **라벨**: 모든 도출 마진은 `derived=True`, `method="peerReconciled"`, `marginRange=[lo,hi]`, `peerN`, `reconcileK` 를 달고 나온다. UI 는 공시 마진과 *다른 시각 토큰*(점선/회색/"도출" 배지)으로 렌더. `_fmtEstimate`/`[추정]` 접두 관례(`revenue.py:417`) 재사용.

### 3.3 정직 경계 (모델하되 날조 금지)
- 부문 매출 자체가 0 (`_selectDocsRevenue → None`): 도출 불가. 연결 단일로 fallback + "부문 미공시" 명시. **여기선 도출 안 함** (분모가 없으면 배분 무의미).
- peer 풀이 비거나(`industryPeers → []`) 매칭 부문 0: (b) 불가 → (a) 매출가중 floor 만, `confidence="low"`, "peer 벤치 부재" 경고. 점추정 단정 금지, 범위만.
- **핵심 계약**: 부문 매출이 *공시되면* 도출한다. 스킵하지 않는다. 부문 매출이 *전혀 없으면* 정직하게 연결로 내려간다.

---

## 4. SOTP 연계 (밸류에이션 02a)

영업복합기업(삼성전자·LG화학·SK이노베이션류)·지주사 두 경로를 분리하되 한 emitter 로 수렴.

### 4.1 영업부문 SOTP (신규 — `_sumOfPartsTable` 스텁 격상)
- `damodaranL15.py:1242` `_sumOfPartsTable` 의 `deferredWithBlocker` 를 *실제 도출*로 교체:
  1. `calcSegmentEconomics(company)` (신규 §5) → 부문별 `{revenue, OIhat, marginRange}`.
  2. 부문별 peer 배수: 매칭 산업그룹 peer 의 EV/EBIT 또는 EV/Sales 중앙값 (`industryPeers` + `industry/sectorParams.json:131` `industryGroupParams`).
  3. 부문가치 `EV_i = OIhat_i × (EV/EBIT)_peer` (OI 신뢰 낮으면 `R_i × (EV/Sales)_peer`).
  4. `EV_sotp = Σ EV_i` → net debt 차감(`damodaranL15` panel `debt`) → equity → perShare.
  5. **vs 연결 DCF 교차검증**: `EV_sotp / EV_dcf` 괴리 + conglomerate discount 시사. (a)/(b)/(c) 마진 불확실성 → SOTP perShare 범위.
- 결과 status: `singleSegmentFallback`(부문<2) | `derivedSegmentSotp`(도출) | `disclosedSegmentSotp`(부문 OI 공시). recipe `sumOfParts.md` 의 `expectedNovelty: sumOfPartsRoute` 충족, `forbidden`(근거 없는 임의 SOTP) 는 peer 벤치 근거로 회피.

### 4.2 지주사 SOTP (기존 유지·보강)
- `sotp.py:20` `calcSotpNav` 는 자회사 *장부가* NAV — 영업부문 SOTP 와 별개 트랙. 보강: `bookValue` 만 쓰는 상장자회사(`listingFlag=="상장"`)는 *시가총액 × 지분율*로 mark-to-market 가능하면 교체(`sotp.py:113` listing_flag 분기 활용), 비상장만 장부가. 이건 별도 P 항목으로 분리(본 스펙 핵심 아님).

---

## 5. 구체 격상 (함수)

### 5.1 신규 — `_segmentEconomics.py` (배분 도출 SSOT)
`src/dartlab/analysis/financial/_segmentEconomics.py` (신규, L2). `_revenueSelect` 재사용, 병렬 빌드 0.

```
def deriveSegmentMargins(company, segData, opData, yCols, *, basePeriod=None) -> dict | None
    # segData(공시 매출) + opData(공시 OI, 부분/전무) → 부문별 도출 마진 범위
    # 반환: {부문: {revenue, opDisclosed, opDerived, marginRange:[lo,hi],
    #              method, peerN, reconcileK, confidence}}
```
- 배분 (a)/(b)/(c) + reconcile + 범위. peer 벤치는 `_peerSegmentBenchmark(company, segName)` 내부 헬퍼가 `industryPeers` + `themeRevenueExposure` 로 산출.

### 5.2 기존 격상 — `calcSegmentComposition` (`_revenueSegment.py:127`)
- `opData = _selectDocsOpIncome(...)` 직후, **공시 OI 가 비거나 일부만이면** `deriveSegmentMargins` 호출해 빈 부문을 도출 마진으로 채움.
- segments dict 에 `opMarginDerived`, `marginRange`, `marginSource ∈ {disclosed, derived}` 추가.
- `hasOpIncome` 게이트(`:213`)를 `marginCoverage ∈ {none, derived, disclosed, mixed}` 로 확장 — 불리언 1개로 마진을 *끄던* 로직 제거.

### 5.3 기존 격상 — `segmentCompositionBlock` (`revenue.py:39`)
- `:55` `if hasOp and ...` → `marginSource` 별 컬럼 렌더. 도출 마진은 `이익률(도출)` 컬럼 + 범위 `12~18%` 표기 + 방법 helper("연결 OI 를 peer 마진 구조로 배분").
- `_fmtEstimate`/`[추정]` 시각 토큰 재사용 — 공시와 도출을 *눈으로* 구분.

### 5.4 신규 — `calcSegmentContribution` 보강 (`_revenueGrowth.py:185` 인접)
- 기존 `calcGrowthContribution`(매출 성장 기여)에 **마진 믹스 효과** 추가: 연결 마진 변화 중 *어느 부문 믹스/마진이* 끌었나 (도출 마진 기반이라도 *방향*은 가치 있음). `mixEffect_i = ΔR_i/R × (m_i − m̄)`.

### 5.5 신규 — `calcSegmentSotp` (`damodaranL15._sumOfPartsTable` 호출)
- `analysis/valuation/sotp.py` 에 `calcOperatingSegmentSotp(company)` 신설 (지주 `calcSotpNav` 와 같은 파일, 명확 분리). §4.1 알고리즘.

---

## 6. 백테스트 / 졸업 게이트

**졸업 조건(operator 사상 4)**: 부문 OI 를 *공시하는* 회사들로 도출법이 실제 마진을 복원하는지 백테스트. 통과해야 도출 마진을 리포트에 올린다.

### 6.1 백테스트 설계 (`tests/_attempts/segmentEconomics/`)
- **진실셋**: `_selectDocsOpIncome` 가 부문 OI 를 반환하는 KR 회사 N (삼성전자 005930·LG화학 051910·SK하이닉스 등 축-태깅 다부문사). 이들은 부문 마진 *정답*이 공시돼 있다.
- **절차**: 각 회사의 공시 부문 OI 를 *가린 채* `deriveSegmentMargins` 로 도출 → 도출 마진 `m_i^hat` vs 공시 마진 `m_i^true` 비교.
- **지표**:
  - MAE(부문 마진) `mean(|m_i^hat − m_i^true|)` ≤ **tolerance(목표 ≤ 5%p)**.
  - 커버리지: 공시 마진이 도출 `marginRange` 안에 드는 비율 ≥ **80%**.
  - 순위 보존: 부문 마진 *순위*(어느 부문이 고마진) 의 Spearman ρ ≥ **0.6** — 점추정 틀려도 *방향*(SOTP·믹스 스토리의 핵심)은 맞아야.
- **민감도**: peer N(5/10/20), reconcile 유무, (c) 자산가중 on/off 별 MAE 격자.

### 6.2 게이트 판정
- MAE ≤ 5%p **and** 커버리지 ≥ 80% **and** ρ ≥ 0.6 → 도출 마진 *값* 리포트 노출 허용.
- 미달이면 **마진 *값* 숨기고 *순위/방향*만** 노출(ρ만 통과 시) 또는 매출 믹스만(전부 미달). 미검증 점추정 단정 금지(`feedback_plan_score_not_signature`).
- 게이트 결과는 docstring + `_attempts/segmentEconomics/README.md` 에 실측 박제 후에만 `src/dartlab/**` 본진 배치(`feedback_attempts_graduation_gate` 8단계).

---

## 7. 통합 (사업구조 + 밸류에이션 섹션)

- **사업구조(business-structure) 섹션**: `segmentCompositionBlock` 이 도출 마진 컬럼 + 범위 렌더. `calcSegmentContribution` 마진 믹스 효과 한 줄("연결 마진 하락은 X 부문 믹스 확대 + Y 부문 마진 압축"). HHI(`calcConcentration`)·성장기여와 같은 박스.
- **밸류에이션(02a) 섹션**: `calcOperatingSegmentSotp` → SOTP perShare 범위 + 연결 DCF 와 교차(conglomerate discount). 지주사는 `calcSotpNav` NAV 와 한 표에 병치(영업부문 SOTP vs 자회사 NAV 가 보완).
- **랜딩 `/report` (P3)**: Python 미실행 환경이므로 *문법 계약*만 공유. ReportModel 에 `segmentEconomics{segments[], marginCoverage, sotp{range, method}}` 필드 추가, TS 가 동일 스키마로 HF parquet 직독 재현(베이크 0). drift parity 테스트로 Python/TS 상수 일치 강제.
- **AI 답변**: `calcSegmentComposition` AIContext 갱신 — "사업부 수익 구조" 답변 시 *도출* 마진이면 method+range 함께 인용, 공시면 그대로.

---

## 8. 리스크

| # | 리스크 | 완화 |
|---|---|---|
| R1 | **날조로 미끄러짐** — 도출 마진을 공시처럼 단정 | `marginSource=derived` 강제 라벨 + 시각 토큰 분리 + 게이트(§6) 통과 전 *값* 미노출. AIContext 인용 시 method 동반 의무 |
| R2 | **peer 매칭 오류** — 부문토큰(XBRL 멤버명 "DxDivision")↔산업그룹 사상 실패 | `themes.json` segmentKeywords 큐레이션 SSOT 재사용. 매칭 실패 부문은 (a) floor + low confidence, 단정 금지 |
| R3 | **reconcile 왜곡** — `k` 스케일이 음수 OI(적자 부문) 에서 부호 뒤집음 | 적자 부문(`m_i^peer<0`)은 reconcile 분모에서 분리 처리, sanity clamp. 테스트에 적자부문 회사 포함 |
| R4 | **단위/scope 혼재** — `_inferSegUnitScale` 오추론, 별도/연결 섞임 | 기존 `scope=="consolidated"` 필터(`_revenueSelect.py:129`) + 단위 추론(`:61`) 재사용, 신규 경로 없음 |
| R5 | **peer 풀 빈약** — 산업그룹 단독/소수 종목 | `industryPeers` n 확대 + 같은 sector(상위) fallback. 그래도 부족하면 도출 안 하고 매출 믹스만(정직 경계 §3.3) |
| R6 | **graph 회귀 유혹** — "통일 SOTP 파이프라인" 고정노드화 | 모두 단일 calc 함수. 고정 다단 노드·companyStory 부활 금지(`no-graph-regression`, `checkAgentBoundary.py`) |
| R7 | **L 계층 위반** — L2 analysis 가 L2 industry 직접 import | `industryPeers`(L2 industry) 호출은 DI/공개계약 경유. peer 벤치 헬퍼를 L2 내 cross-import 아닌 story(L3) 조립단에서 주입하는 안도 검토(아키텍처 확정 02 종합 시) |
