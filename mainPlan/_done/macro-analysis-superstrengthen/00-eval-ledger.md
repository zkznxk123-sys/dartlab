# 00. 5분야 전문가 토론 · 적대 평가 원장

> 운영자 goal: "전문 에이전트들과 토론해서 제대로된 PRD를 만든다. mainPlan에 매크로분석 관련 문서를 초강화한다. UI/UX도 모두 고려하고 각 분야 전문가 평가 95점 이상 획득까지 개선한다." 본 원장은 그 과정·점수 이력·ground-truth 교정을 기록한다.

---

## 1. 과정

1. **현상 스카우트(운영자 직접 소스 검증)** — 매크로 엔진 6막 14축 구조, 공개 `macro.json` 13.5KB(엔진 깊이 ~5%만 bake), 빌드 파이프라인(sync `buildMacroCycle.py`가 `analyzeCycle`만 계산→HF→prebuild `buildMacroJson.py` 오프라인 조립)을 직접 확인. → 초강화 = 묻어둔 함수를 sync 풍부화로 배선하는 feasibility 확정.
2. **5분야 전문가 토론(28에이전트 워크플로)** — 경제·퀀트·UX/PM·시각화·데이터아키텍처가 각자 *실제 엔진을 Read*하고 ① 독립 포지션(어느 묻어둔 축을 결정유관성으로 선별) → ② 교차 비평(초강화 vs 과부하 재현 긴장의 안전선 판정) → ③ 종합 PRD.
3. **각 분야 적대 평가 → 95점까지** — 5분야 전문가가 각자 렌즈로 6축 100점 엄격 채점. 95 미만이면 차단 항목을 ground-truth로 정밀 교정 후 재평가.

채점 6축: 분석깊이 /25 · anti-clutter·UX /20 · feasibility /20 · 데이터정직 /15 · 시각화정직 /10 · 사용자가치 /10. 게이트 = **5명 전부 ≥95**(min≥95).

---

## 2. 점수 이력

| 단계 | 경제 | 퀀트 | UX/PM | 시각화 | 데이터아키 | min | 비고 |
|---|---|---|---|---|---|---|---|
| 토론 종합 후 R1 | 92 | 88 | 93 | 92 | 89 | 88 | 호라이즌 혼합·이중계상·agreement 백도어 |
| R2 | 93 | 88 | 93 | 93 | 91 | 88 | 소스 경로 오기·LEI 게이트 계산불가 |
| R3 | 93 | 93 | 95 | 93 | 94 | 93 | GaR 누락·fan 금지 혼동·파이프라인 정밀 |
| **ground-truth 교정(v2)** | **96** | **95** | **95** | **96** | **96** | **95 ✅** | 19차단 전면 교정·blocking 0 |

> 정체 구간(88~93)의 원인은 "설계 약함"이 아니라 에이전트가 EDGE 모듈 경로·forecast result shape·GaR 호출경로를 *기억으로 쓰다 낸 사실 오류*였다(redesign과 동일 패턴). 정공법 = 또 한 번의 에이전트 라운드(환각 반복)가 아니라 **운영자가 소스 ground-truth를 직접 검증해 19차단을 정밀 교정**. 교정 워크플로는 세션 한도로 eval만 실패했으나 첫 revise(교정) 에이전트는 성공해 v2를 transcript에서 복구, 한도 리셋 후 재평가로 5×≥95 통과.

v2 통과 후 퀀트가 권고한 비차단 정밀 흠 3건도 발간 전 반영: totalComponents 11→실측 10(forecast.py L248-278 components dict 10키) · GaR `observations`=shift 후 유효 회귀 표본(len(fci)−horizon) · GaR FCI 입력에 NFCI fallback(summary._addGrowthAtRisk 패턴 복제).

---

## 3. ground-truth 교정 19항 (소스 직접 검증)

| 영역 | 잘못된 서술 | 소스 ground-truth | 검증 위치 |
|---|---|---|---|
| 함수 경로 | clevelandProbit·LEI·sahm·hamilton을 forecast.py | cycles/_regimeSwitchingLei.py(probit·LEI·_LEI_WEIGHTS·sahm) · cycles/_regimeSwitchingHamilton.py(hamilton) · 공개 import cycles.regimeSwitching | grep 실측 |
| LEI 게이트 | Σweight(가중질량) ≥0.5 | result에 per-component dict·weight 미노출 → 계산 불가. availableComponents/totalComponents 개수 게이트로 대체 | forecast.py L287-288 |
| GaR 누락 | §3.6서 crisis 통째 배제로 GaR 침묵 제외 | growthAtRisk(fci,gdp,horizon=4)=진짜 5분위 분포+skewness, forecast 경로 주입(summary._addGrowthAtRisk), 4Q 전향(crisis lag 아님) → 표면화 4축에 포함 | crisis/growthAtRisk.py · summary.py |
| fan chart 금지 | 전면 금지 | 분포 미산출 모델(probit 점확률·nowcast 점추정)에 한함. GaR 5분위 분포는 fan/분위 정당(ABG Vulnerable Growth 표준) | growthAtRisk.py |
| 호라이즌 | 4모델 단일 '12M·확률' | probit 12M선행·Sahm 실시간동행·LEI 6~9M선행·Hamilton 동행회고·GaR 4Q전향 — 타일별 독립 라벨 | forecast.py |
| 이중계상 | probit·yieldCurve 독립 신호 | 동일 T10Y3M 파생(yieldCurve에 spread 필드 없음→probit.spread 재사용) → agreement 1표 | rates.py · forecast.py |
| agreement | 다수결 zone 압축 | verdict 백도어 → ordinal/score/badge 금지·불일치 모델명 동반·유효<2 '교차 불가' | (설계) |
| regime band | smoothedProbs 미표면화 | result는 contractionProb 스칼라만(배열 드롭) → sync가 hamiltonRegime 직접 호출해 smoothedProbs[-24:,1] | forecast.py L359-371 |
| Hamilton 임계 | regimeLabels[1]=='contraction'(죽은 가드) | mu-swap 구조적 보장 → separation=(mu_exp−mu_con)/maxσ≥0.5(Cohen's d 중간효과). KR 단위 parity 미확정→US-primary | _regimeSwitchingHamilton.py |
| 파이프라인 | runMacro·실패집계·dead path | rc1/rc2 구조·실패 msg data:{rc1}/cycle:{rc2}·rc3 추가·rc2↔rc3 독립·sahm None 단일분기·CPU 예산 분리 | stages/macro.py |
| 파일명 | buildMacroData.yml | .github/workflows/macroData.yml | glob 실측 |
| transition | L1791 % 누출 | L1754 함수·L1757 `${tr.progress}%` | macroLens.ts |

(추가: 타일 내부 px 위계·LEI contributors top2·_FORBIDDEN_IMPORTS 문구·artifact 측정값·sahm dead-path 명세 등 — 총 19항.)

---

## 4. 최종 판정

5분야 전부 ≥95(경제 96·퀀트 95·UX/PM 95·시각화 96·데이터아키 96), blocking 0, min 95 통과. 모든 인용 경로·필드·줄번호를 5명이 소스와 직접 대조해 정합 확인. 퀀트 권고 3건도 반영해 완전 소스 정합.

---

## 5. as-built 냉정평가 (2026-06-21 · 99점 게이트)

재설계 base 위 초강화(Regime Lens) 구현 완료 후, **구현본(as-built)** 을 5렌즈 냉정 워크플로로 **99점 게이트**까지 9라운드 반복(소스 직접 검증 교정). Regime Lens 양언어화가 주변 표면의 EN 누출을 층층이 드러냄 → 전층 폐쇄(빌더 lang 주입·결정론 EN 매핑·재귀 Hangul 스캔). **R9 최종: 5렌즈 전부 99 · confirmed defect 0**(vitest 43/43·svelte-check 0err). 상세 = [../macro-lens-redesign/02-impl-map.md](../macro-lens-redesign/02-impl-map.md) §7. 잔여 = deploy-state(§4.5 — live macro.json regime 키는 운영자 배포단계 주입)·주관 taste뿐.
