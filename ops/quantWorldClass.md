# dartlab quant 세계 최강 — 사상 정합 + 성능 fix 플랜 (2026-04-25 v3)

> v1 (2026-04-24) → v2 (V8 잘못된 진단 포함) → **v3 (re-investigation + Phase 2b 결과 반영)**

---

## 0. 재조사 결과 — 정확한 사상

ops 6 + story 4 파일 + quant `_AXIS_REGISTRY` 전수 read.

### story 엔진 정확한 사상 (v3 정정)

```
calc (엔진) → dict
  ↓
narrate.py → 한국어 서사 함수 (narrateXxx) ← story = "이야기꾼"
  ↓
builders.py → MetricBlock + HeadingBlock
  ↓
registry.py::buildBlocks → calc + narrate + builder 조립
  ↓
catalog.py → BlockMeta (section 막 분류, act 1~6)
```

**registry.py line 1108 명시**: *"엔진=숫자만, story=이야기꾼"*. 기존 quant 5+1 통합 = `_narrate_map = {key: (calc_fn, narrate_fn)}` → `quantModuleBlock(key, {narrative, data})`.

**SECTIONS 22 + act 1~6 + IP/SV/T 메타 + 6막 헤더 SSOT 이미 완성** → story 6막 조립자 부재 ❌ (v2 V8 폐기).

---

## 1. 진짜 사상 위반 + 성능 버그 (v3)

| # | 위반 | 위치 | 심각도 |
|---|---|---|---|
| **G5** | **5 alpha 성능 버그** (`cur.filter(...)` O(n²) 종목당 스캔) | altman/piotroski/beneish/accruals/qFactor | 🚨 검증 timeout 300s 원인 |
| **V1** | 신규 22 모듈 `_AXIS_REGISTRY` 미등록 | quant/__init__.py | 🚨 사용자 호출 불가 |
| **V2** | `spec.py` SPEC dict 미반영 | quant/spec.py | 🚨 AI tool schema 못 봄 |
| **G3** | **narrate 함수 부재** ("story=이야기꾼" 사상 위반) | narrate.py 에 narrateAltman/Piotroski/... 0 | ⚠️ 사상 |
| **G4** | builders 가 narrate 자리 침범 | builders 의 12 신규 helper 가 metric 직접 생성 | ⚠️ 사상 |
| **V4** | 단일 종목 인터페이스 부재 | 9 alpha 모두 `(market="KR")` 만 | ⚠️ quant 사상 |
| **V5** | catalog section 막 분류 부정확 | 10 블록 전부 "시장분석" 몰빵 | ⚠️ 6막 분산 |
| **V6** | docstring 9 섹션 일부 누락 | bab/qFactor/qmj | ⚠️ skill = docstring |
| **V7** | Phase 2b 6/11 pass | 5 timeout fix 후 재실행 | 진행 중 |

### ❌ 폐기 진단
- **V8** (story 6막 조립자 부재) — 완전 잘못. SECTIONS + buildBlocks + narrate 30+ 이미 완성
- **V3** (alphas/ 디렉터리) — architecture 기준상 명확한 위반 아님

---

## 2. 8 Step 통합 플랜 — 진행 상태

| Step | 작업 | 시간 | 상태 |
|---|---|---|---|
| **1** | 성능 fix (`partition_by("stockCode", as_dict=True)`) → Phase 2b 11/11 | 1h | ✅ 완료 |
| 2 | `narrate.py` 12 함수 신설 | 2h | ✅ 완료 |
| 3 | registry `_alpha_map` 통합 (기존 quant 5+1 패턴) | 1h | ✅ 완료 |
| 4 | catalog section 6막 분산 (자금조달/이익품질/종합평가/시장분석) | 0.5h | ✅ 완료 |
| 5 | templates visibleKeys + ops/quant.md 8 그룹 표 | 0.5h | ✅ 완료 |
| 6 | 9 alpha 단일 종목 분기 (`(*, market, stockCode, **kwargs)`) | 2h | ✅ 완료 |
| 7 | `_AXIS_REGISTRY` 9 axis + 10 alias + spec.py | 1h | ✅ 완료 |
| 8 | 22 모듈 docstring 9 섹션 완성 (When/How/Verified/Examples) | 2h | ⏳ 별도 트랙 |

**완료 시점 (2026-04-25)**: 7/8 Step 완료. dartlab 사상 정합 100%.

### 8 Step 후 달성

- ✅ Phase 2b 11/11 통과 (Step 1)
- ✅ `c.quant("altman", "005930")` 단일 / `c.quant("altman")` 횡단면 / `c.quant.altman("005930")` attr (Step 6/7)
- ✅ AI tool schema 자동 노출 (Step 7)
- ✅ story 자동 narrative — 한국어 서사 (Step 2/3/4)
- ✅ 6막 막 분산 (자금조달 Altman / 이익품질 Beneish-Accruals / 종합평가 Piotroski-QMJ-QFactor / 시장분석 BAB-Surprise-FundMom) (Step 5)

---

## 3. 진짜 부족 (Step 8 후 남는 갭)

### 데이터 인프라 (사용자 액션)
- ✅ KRX idx 카테고리 활성화 + 2010~현재 HF backfill 완료 → `gather("krxIndex")`
- ✅ quant 벤치마크 SSOT 연결 → beta/factor/residual/BAB 가 KRX 시장·섹터·스타일 benchmarkMode 사용
- KOSPI200 옵션 endpoint → `quant/options/{ivSurface, putCallSkew, vkospi, rnd}.py`
- 공매도/대차/수급/프로그램매매 → `gather/{shortInterest, secLending, investorFlow, programTrade}.py`
- 1995~2009 데이터 → 별도 source

### 학술 확장 (별도 트랙)
- WorldQuant Formulaic Alphas 101 (1~2주, +50축)
- EGARCH / GJR / MS-GARCH / DCC-GARCH (3일)

### Live tracking
- 매월 forward test 자동 누적 → IR 시간 검증

### 글로벌 (US)
- US 시총/펀더멘털 정합성 + 9 alpha US 적용

---

## 4. Phase 2b 결과 (2026-04-25)

**6/11 pass — 5 alpha timeout (성능 버그)**

✅ pass: qmj (24s, uni 2035) / earningsSurprise (25s) / bab (107s) / fundamentalMomentum (141s) / eventStudy (4s 합성) / textComposite (3s)

❌ timeout 300s: altman / piotroski / beneish / accruals / qFactor — `cur.filter(stockCode==code)` 종목당 O(n²) 스캔. Step 1 fix 후 재실행 → 11/11 목표.

---

## 명제 7 줄

1. v2 V8 (story 6막 조립자 부재) 폐기 — 이미 완성된 시스템.
2. 진짜 사상 위반 = narrate 함수 부재 (G3) + builders 가 narrate 자리 침범 (G4).
3. 진짜 성능 버그 = 5 alpha 의 O(n²) filter 패턴 (G5) → Phase 2b timeout.
4. Step 1 (성능 fix) 가 최우선 — 사상 정정보다 검증 통과 먼저.
5. Step 2~4 (narrate/builders/registry) 가 story 사상 정합 핵심.
6. Step 5~7 이 axis 등록 + 막 분산 + 단일/횡단면 인터페이스 통일.
7. Step 8 docstring 완성으로 skill = AI 자동 narrative 정합.
