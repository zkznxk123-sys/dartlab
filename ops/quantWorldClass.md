# dartlab quant 세계 최강 — 사상 정합 플랜 (2026-04-25 재작성)

> 이전 버전 (2026-04-24) 은 dartlab 사상 위반 항목 다수 포함 → 전면 재작성. 본 문서가 SSOT.

---

## 0. 사상 정합 — 모든 작업의 기준

ops/architecture.md + ops/api-contract.md + ops/quant.md + ops/skills.md + ops/code.md 정독 결과:

| 원칙 | 출처 | 위반 시 결과 |
|---|---|---|
| **L1 quant** (technical 분석, NumPy-only) — analysis L2 import 금지 | architecture.md §4 | 레이어 구조 붕괴 |
| **L2 review** = analysis + credit + quant + macro + industry **dict 조립자** | architecture.md §2 | 엔진 책임 혼동 |
| **호출 통일**: `dartlab.quant("축", "종목")` / `c.quant("축")` / attr form `c.quant.축()` | api-contract.md §1 | 다중 진입점 = contract 위반 |
| **무인자 호출 = 가이드 DataFrame** | api-contract.md §1 / quant.md §1 | 사용자 헤맴 |
| **`_AXIS_REGISTRY` SSOT** — 새 축은 여기 등록 | quant/__init__.py | 사용자 호출 불가 |
| **spec.py SPEC dict** — AI tool schema 자동 노출 | spec.py | AI 가 tool 못 봄 |
| **9 섹션 docstring** — When/How/Verified/Examples 필수 | code.md §2 / skills.md §4 | merge 반려 |
| **skill = docstring** — 별도 narrative 함수 X | skills.md | 덕지덕지 |
| **횡단면 vs 단일종목 패턴 양쪽 지원** — `quant("순위")` (전종목) / `quant("모멘텀", "005930")` (단일) | quant.md §1 | 사용자 인터페이스 혼동 |
| **review = builders + catalog + registry 4 곳** 동시 갱신 | architecture.md §3 | 블록 활성화 X |

---

## 1. 현상태 객관 진단

### ✅ 검증 통과
- **Phase 2a 12/12 numpy-only 모듈 통과** (tripleBarrier / fracDiff / matrixProfile / almgrenChriss / meanCVaR / blackLitterman / nco / shrinkage / bubbleTest / structuralBreak / johansen / multipleTesting)
- **review/catalog 10 BlockMeta + builders 10 함수 + registry 10 자동 호출** ✅

### ❌ 사상 위반 항목 (2026-04-25 발견)

| # | 위반 | 위치 | 심각도 |
|---|---|---|---|
| **V1** | **신규 22 모듈 모두 `_AXIS_REGISTRY` 미등록** | `quant/__init__.py` | 🚨 critical — 사용자가 `c.quant("altman")` / `c.quant("piotroski")` 호출 못함 |
| **V2** | **`spec.py` SPEC dict 미반영** | `quant/spec.py` | 🚨 critical — AI 가 tool schema 로 못 봄, dartlab 정체성 미실현 |
| **V3** | **`alphas/` 별도 디렉터리** | `quant/alphas/` | ⚠️ 나머지 quant 모듈은 평탄 — 일관성 깨짐 (Simple > Complex 위반) |
| **V4** | **단일 종목 인터페이스 부재** | 9 alpha 함수 | ⚠️ 모두 `(market="KR")` 만 받음 → 단일 종목 호출 X. quant 사상은 단일 + 횡단면 양쪽 |
| **V5** | **8 그룹 분류 미적용** | 22 신규 모듈 | ⚠️ ops/quant.md §3 의 8 그룹 (technical/risk/microstructure/fundamental/text/crossSection/portfolio/Strategy DSL) 어디 속하는지 미명시 |
| **V6** | **9 섹션 docstring 일부 누락** | bab/qFactor/qmj/transformer 모듈 | ⚠️ Verified / SeeAlso / When 섹션 부분 누락 |
| **V7** | **Phase 2b 검증 미완** | 11 데이터 의존 모듈 | ⚠️ 한국 시장 실증 alpha 인지 미증명 |
| **V8** | **review 시장분석 6막 조립 로직 부재** | `review/registry.py` | ⚠️ 신규 10 블록 등록만 됐을 뿐, macro+quant+credit+analysis dict 한 흐름 직조 X |

### 📊 코드 통계 (현재)

- 기존 quant 모듈 30 + 신규 22 = 52 모듈 (디렉터리 + 평탄 혼재)
- `_AXIS_REGISTRY` 등록 = 30 (신규 22 미등록)
- review 블록 = 기존 + 신규 10 = 정상
- 검증: 12/22 = 54% pass (Phase 2a only, Phase 2b 진행 중)

---

## 2. 사상 정합 플랜 — 8 단계

### Step 1: V3 정정 — 디렉터리 평탄화 (1시간)

`quant/alphas/{altman, piotroski, beneish, accruals, qFactor, qmj, bab, earningsSurprise, fundamentalMomentum}.py` → 기존 quant 모듈처럼 **평탄화**.

**옵션 A** (선택): 평탄으로 이동 — `quant/{altman.py, piotroski.py, beneish.py, ...}` (나머지 quant 모듈과 일관)

**옵션 B**: alphas/ 유지 — 사상 일관성을 위해 8 그룹별 디렉터리화 (technical/risk/fundamental/...) 같이 도입 (큰 리팩토링)

→ **A 채택** (작은 변경, 일관). 9 신규 모듈 → 평탄으로 이동. import path 정정.

### Step 2: V4 정정 — 단일 종목 인터페이스 추가 (2~3시간)

각 9 alpha 함수에 `stockCode` 인자 추가:

```python
def calcAltman(stockCode: str | None = None, *, market: str = "auto", **kwargs) -> dict:
    """Altman Z-Score — 단일 종목 또는 시장 횡단면.

    stockCode 있으면: 단일 종목 Z + zone (1968 또는 Z'')
    stockCode 없으면: 시장 횡단면 (universe 분포 + topSafe/topDistress)
    """
```

이게 quant 표준 패턴 (`quant("순위")` 횡단면, `quant("모멘텀", "005930")` 단일).

함수명 변경: `calcAltmanFactor` → `calcAltman` (factor suffix = 시장 횡단면 의미였는데, 단일 + 횡단면 분기로 통합).

### Step 3: V1 정정 — `_AXIS_REGISTRY` 등록 (1시간)

`quant/__init__.py::_AXIS_REGISTRY` 에 신규 9 alpha + 13 utility 모듈 등록. 8 그룹 분류 적용:

| 모듈 | 축 키 | 그룹 | label | 단일/횡단면 |
|---|---|---|---|---|
| altman | "altman" | fundamental | "Altman Z" | 둘 다 |
| piotroski | "piotroski" | fundamental | "Piotroski F" | 둘 다 |
| beneish | "beneish" | fundamental | "Beneish M" | 둘 다 |
| accruals | "accruals" | fundamental | "Sloan Accrual" | 둘 다 |
| qFactor | "qfactor" | fundamental | "q-factor" | 횡단면 |
| qmj | "qmj" | fundamental | "QMJ" | 횡단면 |
| bab | "bab" | risk | "BAB 저변동성" | 횡단면 |
| earningsSurprise | "surprise" | fundamental | "이익서프라이즈" | 둘 다 |
| fundamentalMomentum | "fundmom" | fundamental | "펀더-가격 모멘텀" | 둘 다 |
| ─── ML 인프라 (utility, 축 등록 X — 직접 import) ─── | | | | |
| labels/tripleBarrier | — | utility | — | — |
| transforms/fracDiff | — | utility | — | — |
| transforms/matrixProfile | — | utility | — | — |
| transactionCost | — | utility | — | — |
| ─── Portfolio (멀티종목) ─── | | | | |
| meanCVaR | "meancvar" | portfolio | "Mean-CVaR" | 멀티 |
| blackLitterman | "bl" | portfolio | "Black-Litterman" | 멀티 |
| nco | "nco" | portfolio | "NCO" | 멀티 |
| shrinkage | — | utility | — | — (cov 입력 받음) |
| ─── Risk 통계 ─── | | | | |
| bubbleTest | "bubble" | risk | "버블 (SADF)" | 단일 |
| structuralBreak | "break" | risk | "구조변화" | 단일 |
| johansen | "johansen" | crossSection | "공적분 (k≥3)" | 멀티 |
| ─── 거버넌스 ─── | | | | |
| multipleTesting | — | utility | — | — |
| eventStudy | "event" | text | "Event Study CAR/BHAR" | 단일 |
| textComposite | "textcomp" | text | "텍스트 합성" | 단일 |

**utility = `_AXIS_REGISTRY` 미등록**, 직접 import 만. (사용자가 `c.quant()` 가이드에서 보지 않을 함수.)

→ **신규 axis 등록 = 12** (9 alpha + meanCVaR + bl + nco + bubble + break + johansen + event + textComp = 14)

### Step 4: V2 정정 — `spec.py` 갱신 (30분)

신규 14 axis 의 SPEC dict 항목 추가 → AI tool schema 자동 수집.

### Step 5: V5 정정 — ops/quant.md 8 그룹 표 갱신 (30분)

§3 의 8 그룹 표에 신규 14 axis 추가. fundamental 9, risk 4, portfolio 3, crossSection 1, text 2 (event + textComp).

### Step 6: V6 정정 — 9 섹션 docstring 완성 (2시간)

22 신규 모듈 전수. 누락된 Verified / SeeAlso / When / How / Examples 보강. AI 가 tool schema 로 정확 narrative 생성하도록.

### Step 7: V8 정정 — review 6막 조립 로직 (3~4시간)

`review/registry.py` 시장분석 섹션에 **6막 인과 조립자 함수** 신설:

```python
def assemble6막Narrative(
    macro: dict, sector: dict, fundamentals: dict,
    quant: dict, distress: dict
) -> list[Block]:
    """6막 인과 자동 직조 — macro→sector→company→financial→valuation→quant.

    review (L2) 책임 — 5 dict 받아 한 흐름 narrative 조립.
    """
```

distress 필터 (Altman + Beneish red flag 종목 제외 list) 도 review 가 dict 받아 portfolio 블록에서 자동 표시.

### Step 8: V7 정정 — Phase 2b 검증 + universe 확정 (대기 중)

Phase 2b (validatePhase2b.py 격리 subprocess) 결과 → 통과 alpha 만 default universe 편입. 통과 못한 alpha 는 quant 사용은 가능하되 default 추천 X.

---

## 3. Step 별 산출물

| Step | 산출 | 시간 |
|---|---|---|
| 1 | 9 alpha 평탄 이동 (alphas/ 폐기), import 정정 | 1h |
| 2 | 단일/횡단면 양쪽 지원 함수 시그니처 통일 | 2~3h |
| 3 | `_AXIS_REGISTRY` 등록 14 axis | 1h |
| 4 | `spec.py` SPEC dict 갱신 | 0.5h |
| 5 | `ops/quant.md` 8 그룹 표 + §11 review 매핑 갱신 | 0.5h |
| 6 | docstring 9 섹션 완성 22 모듈 | 2h |
| 7 | `review/registry.py` 6막 조립자 + distress 필터 | 3~4h |
| 8 | Phase 2b 결과 → universe 확정 + memory 갱신 | 진행 중 |

**총 10~13 시간** — 사상 정합 + AI 통합 + review 조립 완성.

---

## 4. 8 단계 후 달성 상태

- ✅ `c.quant("altman", "005930")` 단일 종목 호출
- ✅ `c.quant("altman")` 시장 횡단면 호출
- ✅ `c.quant.altman("005930")` attr form
- ✅ `dartlab.quant()` 가이드 DataFrame 에 신규 14 axis 자동 표시
- ✅ AI 가 tool schema 로 신규 axis 자동 인지 + narrative 자동 생성
- ✅ review 6막 인과 자동 직조 (macro+quant+credit+analysis 조립)
- ✅ Phase 2b 검증 통과 alpha 만 default universe (universe 자동 갱신 게이트)
- ✅ ops/quant.md 8 그룹 30 → 8 그룹 44 axis 갱신
- ✅ 22 신규 모듈 docstring 9 섹션 완성

---

## 5. 진정 부족한 항목 (Step 1~8 후 남는 갭)

### 데이터 인프라 (사용자 액션 필요)
- KRX idx 카테고리 키 활성화 → `gather/krxIndex.py` (코드 준비됨)
- KOSPI200 옵션 endpoint → `quant/options/{ivSurface, putCallSkew, vkospi, rnd}.py` (수집 인프라 신설 필요)
- 공매도/대차/수급/프로그램매매 → `gather/{shortInterest, secLending, investorFlow, programTrade}.py`
- 1995~2009 데이터 → 별도 source (KRX 정보데이터시스템 유료)

### 학술 확장 (별도 트랙)
- WorldQuant Formulaic Alphas 101 (대규모 1~2주, +50축)
- EGARCH / GJR-GARCH / MS-GARCH / DCC-GARCH (likelihood 최적화 필요, 3일)
- Deep Hedging (RL portfolio, 별도)

### Live tracking
- 매월 forward test 자동 누적 → IR 시간 검증 (out-of-sample)

### 글로벌 (US)
- US 시총/펀더멘털 정합성 추가 → 9 alpha US 적용
- EDGAR companyfacts 와 KRX 동등 SSOT

---

## 6. 즉시 착수 (Step 1~3 = 4시간)

가장 큰 사상 위반 (V1/V3/V4) 부터 정정. 4시간 작업으로 사용자가 `c.quant("altman", "005930")` 호출 가능 + AI 가 자동 인지하는 상태 도달.

Step 4~7 은 그 다음 세션. Step 8 (Phase 2b) 은 백그라운드 진행 후 결과 받으면 자동 진행.

---

## 7. 관련 문서

- `ops/architecture.md` §2-§4 (L0~L3 레이어 + 6 엔진 + import 방향)
- `ops/api-contract.md` §1-§3 (Dual Access, 단일 진입점, 파라미터 표준)
- `ops/quant.md` §1-§3 (호출 계약, 8 그룹 30 axis, numpy-only)
- `ops/skills.md` (skill = docstring SSOT)
- `ops/code.md` §2 (9 섹션 docstring, Returns 단위)
- `ops/review.md` (review 블록 catalog/builders/registry/narrate 4 곳)
- memory `quantGap.md` (Sprint 1~7 진행 사실)

---

## 명제 7 줄 요약

1. quant 는 **L1** — analysis L2 import 금지, NumPy-only.
2. 신규 22 모듈 중 14 가 axis (8 그룹 분류) + 8 이 utility (직접 import).
3. 호출 통일: `c.quant("축")` 가이드 / `c.quant("축", "종목")` 단일 / `c.quant("축")` 횡단면 (인자 없으면).
4. **`_AXIS_REGISTRY` + `spec.py` 등록이 정체성 표현** — 등록 안 하면 dartlab 사상 미실현.
5. **review (L2) 가 dict 조립자** — quant 결과 + macro + credit + analysis 받아 6막 인과 직조.
6. **skill = docstring** — 9 섹션 완성하면 AI 가 자동 narrative.
7. Phase 2b 결과로 universe 자동 갱신 게이트 — 통과 못한 alpha 는 default 에서 빠짐.
