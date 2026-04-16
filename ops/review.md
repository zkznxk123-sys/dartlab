# Review 엔진 운영 규칙

> review 엔진 = **5엔진(analysis/credit/quant/macro/industry) 결과의 조합·감사 센터**.
> narrate 생성은 부수효과. 본질은 "다양한 관점의 근거를 체계적으로 배치 + 검증 + 보정".

---

## 사상 (Core Philosophy)

1. **보고서 빌더, 해석자 아님** — review 는 근거를 배치한다. 해석은 AI 와 사람의 몫.
2. **11 reportType × 7 template 2축 체계** — 관점(type) × 기업유형(template) 독립 직교.
3. **6막 인과 구조** — 23 섹션이 6막(+ 메타 3 = act 0) 에 명시 매핑 (`SectionMeta.act`).
4. **Damodaran Narrative↔Numbers 6단계 완전 자동화** — 서사가 숫자를 만들고 숫자가 서사를 검증하는 루프.
5. **claim → source 강제 attribution** — 모든 숫자/주장에 evidence (Phase 10 G1).
6. **AI 는 review 를 소비하지 않는 적극적 분석가** — review 를 참고하되 엔진을 직접 호출. review 가 조합하는 모든 정보에 AI 도 동일 접근.

---

## 6막 구조 (Phase 10 F1)

`SectionMeta.act` 필드로 명시. 23 섹션 + 3 메타.

| 막 | 의미 | 섹션 수 | 섹션 |
|---|---|---|---|
| 1 | 이 회사는 뭘 하는가 | 2 | 수익구조, 성장성 |
| 2 | 얼마나 잘 하는가 | 2 | 수익성, 비용구조 |
| 3 | 현금이 실제로 도는가 | 2 | 현금흐름, 이익품질 |
| 4 | 자본 구조는 안전한가 | 2 | 자금조달, 안정성 |
| 5 | 번 돈을 어떻게 쓰는가 | 7 | 자산구조, 효율성, 투자효율, 자본배분, 재무정합성, 종합평가, 신용평가 |
| 6 | 앞으로 어떻게 될 것인가 | 7 | 가치평가, 지배구조, 공시변화, 비교분석, 매출전망, 시장분석, 매크로 |
| 0 | 메타 | 3 | improvementPlan, storyValidation, thesisReport |

---

## 호출 계약 (4엔진 통일 패턴)

```python
c.review()                          # 가이드 (DataFrame)
c.review("재무분석")                 # 단일 섹션
c.review(type="credit")              # 11 reportType 중
c.review(type="full", template="사이클")  # type × template 조합
```

---

## reportType 11 (Phase 10 F4)

모든 타입이 `storyValidation` 포함 — Damodaran 3-test 필수.

| key | sectionOrder 크기 | 용도 |
|---|---|---|
| full | 25 | 전체 6막 |
| executive | 5 | 3분컷 |
| credit | 6 | 채권/여신 |
| valuation | 7 | 가치투자 |
| growth | 8 | 성장투자 |
| crisis | 8 | 위기 진단 |
| audit | 6 | 감사/포렌식 |
| dividend | 6 | 인컴 |
| governance | 5 | 거버넌스 |
| macro | 5 | 탑다운 |
| thesis | 2 | AI 논제 |

---

## Template 7 (기업유형 오버레이)

`emphasize` 오버레이로 동작 (순서 재배열 아님 — 의도적 독립 축):
- 사이클, 프랜차이즈, 턴어라운드, 성장, 자본집약, 지주, 현금부자

**template 자동 감지** (`core/finance/companyType.py::detectTemplates`):
- `_checkCyclical`, `_checkFranchise`, `_checkTurnaround`, `_checkGrowth`, `_checkCapitalIntensive`, `_checkHolding`, `_checkCashRich`

Phase 9 A1 에서 L2→L3 역방향 import 제거 — 이 함수들은 L0 로 이동.

---

## Block 타입 6종 (역할 명확)

| 타입 | 역할 |
|---|---|
| TextBlock | 서술형 텍스트 |
| HeadingBlock | 섹션 제목 |
| TableBlock | DataFrame |
| FlagBlock | 경고/기회 신호 |
| MetricBlock | KPI 라벨:값 |
| ChartBlock | VizSpec |

---

## 인과 체인 (Phase 9 B2+B3)

`review/narrative.py`:

- `detectThreads(company, blockMap, sections)` — 7 인과 패턴 감지
- `buildActTransitions(company, blockMap)` — 6막 전환 문장 (5 전환)
- `buildCausalWeights(company, blockMap)` — **정량 가중치** (5단계 amplify/dampen/neutral)
- `buildValuationImpact(chains)` — **narrative→숫자 피드백** (terminalGrowth/WACC 조정 힌트)

AI 가 `buildValuationImpact` 결과를 `overrides` 로 주입 → narrative 가 숫자를 바꾸는 구조.

---

## 불변량 검증 20개 (Phase 10 F2)

`review/validators/validators.py::_INVARIANTS` — 경제학적 항상 참 불변량.

Identity: FCF = OCF - Capex / 영업이익 decomp / ROIC = NOPAT/IC / ROE / WC / Market Cap  
Ratio: Debt/EBITDA ≤ 3 / Goodwill/TA ≤ 30% / Tax Rate 5-40%  
Combo: 부채300% + IC<2 / ROE<0 + 배당 / NI>0 but OCF<0 / ROIC<WACC  
Operational: DSO ≤ 120 / DIO ≤ 180 / CCC ≤ 200

Damodaran 3-test (History/Experience/CommonSense) + 20 불변량 = audit 기반.

---

## 레이어 규칙 (강행)

- L3 review 는 L0(core)/L1(providers, gather)/L1.5(scan)/L2(analysis/credit/quant/macro/industry) 모두 소비 가능
- **L2 → L3 역방향 import 금지** (Phase 9 A1 에서 0건 달성)
- **L2 상호 import 금지** (Phase 9 A2 에서 0건 달성)
- narrate 함수는 dict → str. 계산 로직 금지 (dict/숫자는 L2 엔진에서 이미 계산)

---

## AI 연동 원칙

- AI 는 `review()` 를 **직접 호출 안 함** (83초 타임아웃 회피).
- AI 는 review 의 **스키마** (type enum, section order, emphasize) 는 자동 인식.
- AI 는 review 가 조합하는 **1차 정보** (analysis/credit/quant/macro/industry) 에 동일 접근.
- AI 는 review 의 **2차 가공** (causalWeights/valuationImpact/storyTree) 도 tool 로 접근 가능해야 함 (Phase 10 H2 목표).

---

## Phase 10 진행 상태

| Part | 내용 | 상태 |
|---|---|---|
| F1 | SectionMeta.act 필드 + 6막 매핑 | ✅ |
| F2 | 불변량 5→20 | ✅ |
| F3 | template sectionOrder | design-as-intended |
| F4 | storyValidation 11 전체 | ✅ |
| F5 | executive 요약 narrative | TBD |
| F6 | 고아 narrate 바인딩 | 이미 바인딩됨 |
| I1 | narrate boilerplate | _classify/_detectTrend 이미 분해 |
| I2 | 임계값 SSOT | 도메인 분리 — skip |
| I3 | ops/review.md | ✅ (본 문서) |
| G1 | EvidenceGraph | TBD |
| G2 | StoryTree | TBD |
| G3 | NarrativeDiff | TBD |
| G4-G8 | 혁신 마무리 | TBD |
| H1-H5 | AI 동기화 | TBD |

---

## 테스트

```bash
bash scripts/dev/test-lock.sh tests/test_engineConsistency.py \
    tests/test_damodaranAbsorption.py tests/test_damodaranPhase3.py \
    tests/test_damodaranPhase5.py tests/test_protocol.py -m unit --tb=short
```

---

## 참조

- `src/dartlab/review/README.md` — 사용자 문서 (호출 계약 + 예제)
- `src/dartlab/review/narrative.py` — 인과 체인 모듈
- `src/dartlab/review/catalog.py` — Section/Block 카탈로그 (SSOT)
- `src/dartlab/review/reportTypes.py` — 11 reportType 정의
- `src/dartlab/review/templates.py` — 7 template 정의
- `src/dartlab/review/validators/validators.py` — 불변량 20 + 3-test
- `src/dartlab/core/finance/companyType.py` — 기업유형 판별 (Phase 9 A1)
