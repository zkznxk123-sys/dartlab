# 매크로분석 초강화 (Macro Analysis Super-Strengthen)

> 상태: **PRD 확정 (2026-06-20) · 각 분야 전문가 평가 5/5 전부 ≥95** (경제 96 · 퀀트 95 · UX/PM 95 · 시각화 96 · 데이터아키텍처 96, min 95). 착수 = 운영자 go (UI·파이프라인 변경이므로 push는 명시 승인 후).
> 거처: `ui/packages/surfaces/src/terminal/panels/MacroLensDialog.svelte` EXTEND + 데이터층 `.github/scripts/sync/buildMacroRegime.py`(신규) → HF `macro/regime/{kr,us}.json` → `prebuild/buildMacroJson.py` 조립 확장 → `macro.json` `regime` 키 → `macroLens.ts`.

---

## 한 줄 결론

매크로 엔진은 6막 14축의 세계급 깊이(Hamilton regime-switching · growth-at-risk · Cleveland Fed 침체확률 probit · Sahm rule · Conference Board LEI · 수익률곡선 · 위기 detectors)를 가졌지만, 공개 `macro.json`은 그 **~5%만 bake**(phase/quadrant/transmission/tailwind)한 채 나머지를 *만들어 묻어뒀다*. 초강화 = 새 메커니즘을 쌓는 게 아니라 **묻어둔 전향(前向) 축을 단일 점수로 붕괴시키지 않고 정직하게 배선**하는 것 — "Foresight, not Verdict". [[project_industry_analysis_lab]]와 동형(묻어둔 함수 배선) 패턴.

**표면화 4축(결정유관성으로 가차없이 선별):** forecast 침체 confluence(probit·Sahm·LEI·Hamilton, 각자 다른 호라이즌·합산 0) · GaR 4분기 전향 조건부 분포 · 수익률곡선 형태 · quadrant 방향 + transition 전향 추적기. **의도적 제외:** liquidity·sentiment·crisis·assets·corporate·trade·inventory·narrative·nowcast·summary(단일 macro score=verdict 엔진 쌍둥이, grep 봉인).

**핵심 설계 결정:** 첫 화면 4블록 계기판(재설계 96점)은 **픽셀 불가침**. 깊이는 단 하나의 진입점 — A블록 Phase Strip 클릭 → 인라인 `<details>` 1개 "국면 렌즈(Regime Lens)" — 에만 흘려보낸다(progressive disclosure). 새 탭·라우트·상주 패널 0. 첫 화면 유일 증분 = transition 전향 분수 1줄.

---

## 문서 지도

1. [01-superstrengthen-prd.md](01-superstrengthen-prd.md) — **완전 PRD**(비전·묻어둔 엔진 진단·표면화 축 선별·데이터 파이프라인 강화[sync→HF→prebuild]·UI progressive disclosure·시각화 정직·정직 가드·영향 파일/함수·테스트/롤백·Phase·이중평가·성공/실패 기준). 자기충족적.
2. [00-eval-ledger.md](00-eval-ledger.md) — 5분야 전문가 토론·적대 평가 과정과 점수 이력(88→93→95), ground-truth 교정 19항 기록.

---

## 기존 매크로 문서와의 관계

| 문서 | 역할 | 본 초강화와의 관계 |
|---|---|---|
| [`macro-lens-dialog/`](../macro-lens-dialog/) | 엔진(transmission)·데이터 계약·시각화 조사·정직 원칙 SSOT | **계승** — 엔진 산출 형태(읽기만)·analyzeTransmission·sectorTailwind 그대로 소비 |
| [`macro-lens-redesign/`](../macro-lens-redesign/) | 다이얼로그 시각 재설계(verdict 13섹션 폐기→4블록 계기판, 96점) | **불변 토대** — 4블록 IA·시각 토큰·면적 게이트·`buildExposureMatrixRows`/`pickFocusCell`을 그대로 위에 쌓음. **선행 게이트**(재설계 머지 후 착수) |
| **`macro-analysis-superstrengthen/`** (본 폴더) | 묻어둔 분석 *깊이*를 정직하게 배선 | 재설계 위에 progressive disclosure로 깊이만 추가. 새 메커니즘·verdict·단일 macro score·13섹션 과부하 절대 금지 |

즉 세 문서는 한 줄로 이어진다: **macro-lens-dialog(엔진·데이터)= 무엇을 가졌나 → macro-lens-redesign(UI)= 어떻게 깨끗이 보이나 → macro-analysis-superstrengthen(깊이)= 묻어둔 것을 어디까지 정직하게 끌어올리나.**
