# 06 · Progress Ledger

> 재개 = 아래 **NEXT** 부터. 커밋 규약 `거시시뮬(Phase-N): ...`. 착수 전 운영자 go.

## 상태

- **2026-06-24 · v0.1 설계 초안** — PRD 7문서 작성(README·00~06). 거시 엔진 실측 audit(forecast/scenario/transmission/macroBacktest/pipeline) 후 "빠진 forward 층" 정의. scenario-simulator 중복 0 확인(그쪽 정직척추="거시 미래경로 부재, preset 으로 받음" → 본 엔진이 상류 구멍 메움, 단방향 브리지). 착수 전 운영자 go 대기.

## NEXT

1. **운영자 go** + 1차 청중 확정(00 §3: 분석가용 fan/IRF/국면경로 = 기본 채택. 포트폴리오 MC 는 비-목표).
2. **Phase 0 개념검증** — `tests/_attempts/macroSimEngine/` 에서 US 5변수 BVAR 데모 → IRF 부호·held-out coverage·결정론 AC(05 §1) 측정. go/no-go.
3. go 면 **Phase 1**(국면경로, Hamilton 재사용) → sim JSON `regimePath` + 패널 1줄 + 다이얼로그 3a.

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
