# 06 · Progress Ledger

> 재개 = 아래 **NEXT** 부터. 커밋 규약 `거시시뮬(Phase-N): ...`. 착수 전 운영자 go.

## 상태

- **2026-06-24 · v0.1 설계 초안** — PRD 7문서 작성. 거시 엔진 audit 후 "빠진 forward 층" 정의. scenario-simulator 중복 0.
- **2026-06-25 · 구현 (운영자 go: "정공법·클린코드·덕지덕지 금지로 완성")** — Phase 0~2 본진 완료. Phase 3~4 의도적 후순위.

### ✅ Phase 0 — 개념검증 (`tests/_attempts/macroSimEngine/`, gitignore 스크래치)
- 자연켤레 Minnesota BVAR(dummy-obs) + forward fan + Cholesky IRF. 졸업 AC 3종 PASS:
  결정론(seed byte-동일)·held-out 80% coverage **0.85**(US 5변수 1986~)·IRF 안정(companion eig 0.997<1).
- 정직 발견 박제: ① 재귀식별 IRF *방향부호*는 표본/식별 취약(price/output puzzle) → fan/regimePath 척추·IRF caveat.
  ② HY스프레드 로컬이력 부족(2023-06~) → 원유로 대체(물가퍼즐 해소+장기이력)·HY 백필 후 편입.

### ✅ Phase 1+2 — 본진 엔진 + 빌드 + UI (커밋)
- **엔진** `src/dartlab/macro/simulate/`(`afO`): bvar·fan·irf·regimePath·calibration·_panel·_types·simulate.
  공개 verb `dartlab.macro('시뮬레이션', market=)`. US/KR 양시장 fan 작동(US nObs483·KR 315).
  regimePath = Hamilton 전이행렬 forward Markov(약분리/표본부족 시 fail-closed "표시 보류" — 정직).
  IRF caveat="recursive-identification·illustrative". 결정론·안정성 게이트·look-ahead 차단.
- **보정 척추** `calibration.py::fanCalibration` — held-out coverage **US 0.84 calibrated**(probe 재현). measureCoverage 순수·테스트.
- **빌드** `pipeline/stages/macro.py::runMacroSim` → `macro/sim/{kr,us}.json`(15-17KB) → HF. runMacro 독립 합류 + StageSpec.
- **UI** 거시 다이얼로그 **현황|전망 토글** + BVAR 팬 2×2(과거 실선+미래 밴드, MiniFinChart SSOT, 원유 control 제외)
  + 국면경로 연속 SVG(조건부) + 정직 footer. 배선 `rt.macro.getSim`→`macro/sim` JSON(loadHfJson 단일진입). 무스크롤.
- **테스트**: 엔진 9 unit + macroLens vitest 53 + architecture/camelCase/svelte-check 0err/tsc 0. 시각 눈검수(KR/US 전망 팬 렌더 확인).

### 게이트 (운영자 승인 대기)
- **UI git push 보류** — 공개 터미널이라 운영자 시각 눈검수 후 push("푸시해"). 커밋만 완료(엔진/빌드/UI 스택).
- **sim 데이터 HF publish 보류** — auto-mode 가 "공개 기능 활성화"로 차단. 운영자 승인("발간해") 후 publish → dev/공개 전망뷰 라이브.
  (그 전엔 getSim null → 피처게이트로 섹션 미렌더 = 무해.)

## NEXT (Phase 3~4 — 후순위, PRD 05 가 명시한 선택/후순위)

1. **운영자 시각 눈검수** → UI push + sim 데이터 publish 승인.
2. **Phase 3 — 시나리오 조건부 forward**(`scenarioPath.py`): runScenario 프리셋→충격경로 어댑터 → 조건부 fan + 다이얼로그 overlay.
3. **Phase 4 — transmission 브리지**(선택): IRF→섹터/기업 타격 + scenario-simulator 외생축 격상. 데이터벽 held-out 측정 후 점진.
4. (데이터) HY스프레드 전이력 백필 → 신용축 5→6변수 편입 + 재보정.

## 결정 로그

- 엔진 거처 = `src/dartlab/macro/simulate/`(L2 macro 내부, scenario-simulator `src/dartlab/simulate/` 와 별개·단방향 브리지). (03)
- 모델 = reduced-form BVAR + Minnesota prior + MC propagation. DSGE·naive bootstrap·포트폴리오 MC 기각. (02·05)
- 검증 척추(보정) = 기능보다 먼저. macroBacktest walk-forward 확장(coverage/CRPS/PIT). (02 §6)
- 배선 = `runMacroSim` → `macro/sim/{kr,us}.json` → HF → `rt.macro.getSim` → macroLens 뷰모델 → 패널/다이얼로그(신규 surface 0). (03·04)
- 결정론 = `np.random.default_rng(SEED)` 로컬. 정직 = fail-closed·넓은밴드·scenario≠forecast·미보정 배지. (05 §7)

## 미결 OQ (착수 시 결정)

- OQ1: BVAR 변수셋 5개 고정 vs 시장별 가변(KR 교역 추가 등). → Phase 0 데모로 coverage 최적 셋 확정.
- OQ2: sim 빌드 cadence — regime 와 동일 주기(sync cron) vs 분기(GDP revision 후만). → 분기 GDP 의존 축은 분기, regimePath 는 regime 주기.
- OQ3: 인터랙티브 커스텀 충격(사용자 슬라이더) pyodide 클라이언트 forward — Phase 3 후 별 트랙(계수 ship 필요). v1 프리셋 discrete.
- OQ4: KR 보정 미달 시 KR fan 영구 holdback vs 단변량 축소. → Phase 0 측정 후.
