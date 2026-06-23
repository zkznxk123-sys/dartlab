# 공동작업대 데이터빌드 SSOT 확립 (Data-Build Workbench SSOT)

> ✅ **완료 (2026-06-21): MUST(macro 첫 증명) 흡수 구현·검증·푸시 완료.** macro sync(`runMacroData/Cycle/Regime`) + prebuild(`runMacroJson`) in-library 흡수 + 4스크립트 thin shim화(로직 중복 0) + registry + 가드 테스트 3종. master commit `4345453f8`(흡수)·`86ff3c4ad`(테스트)·`0e33bd293`(operation.architecture 박제) — 전부 origin/master 푸시 완료. 검증: ruff 클린·구조 동등(asOf/computedAt 제외)·architecture+pipeline 53 green·적대 SHIP 10/10.
> ⏭ **SHOULD(dart/news/gov)는 본 PRD 범위 밖 — 별개 후속 웨이브**(각 도메인 audit 선행·세션당 1개·44개 일괄 금지). 동일 흡수 템플릿 적용.
> 이전 상태: PRD 확정 (2026-06-20) · 전문가 토론(5 포지션) + 적대 평가 2인 SHIP(88/88) · ground-truth 4정정 반영. 백엔드/파이프라인이라 UI push 승인 회로 무관(operator CI dry-run 1회는 선택).
> 거처: `src/dartlab/pipeline/stages/macro.py`(흡수) + `stages/prebuild.py`(신규) + `registry.py` + 신규 테스트 2종. 흡수 대상 = `.github/scripts/sync/buildMacro{Data,Cycle,Regime}.py` · `prebuild/buildMacroJson.py`.

---

## 한 줄 결론

**공동작업대(in-library `dartlab.pipeline`)가 모든 데이터 빌드의 정본 오케스트레이션이며, `.github/scripts/{sync,prebuild}`에 흩어진 빌드 로직을 stage 모듈로 흡수한다 — 단 빌드 *재구현*은 이미 0(전부 gather/scan 위임)이라 옮기는 것은 "오케스트레이션 위치"뿐이다.** 범위 = 데이터 전부(모든 도메인), 실행 = phased(macro 첫 증명).

운영자 goal "전문가토론으로 공공[공동]작업대 데이터배선까지 확립하라 / PRD는 데이터 전부까지다"의 산출물. 조사로 드러난 실상:
- **공통배선(UI consume): 이미 SSOT 준수** — macro.json은 `dartlabData.ts loadJson()` 단일 진입(landingJson arm·dual-SSOT), HF-first·zero-cache, `checkUiDataWiring` 위반 0. regime 키는 macro.json 편승=새 배선 0. → 문서화만(변경 0).
- **공동작업대(build): MIXED** — `edgar/allFilings/dartZip/edgarPanel/reconcile`은 이미 in-library 흡수(증명된 패턴), `macro/krx/news/dart`는 `runScript()` subprocess로 미흡수. macro가 흡수 비용 최소(빌드 100% L2 위임)인 *이상적 첫 증명 인스턴스*.

---

## 핵심 설계 결정

1. **edgar/allFilings = 증명된 흡수 템플릿**(5규칙: lazy import·공개함수 직접호출·per-item 예외격리·HF push stage 내부 token 인자·StageResult 반환). macro는 build+push 둘 다라 allFilings 모델 직접 적용.
2. **거처 = `stages/macro.py` 인라인**(별도 `dartlab.macro.build` 신설 안 함 — 빌드가 이미 L2 위임이라 추출할 gather/compute가 없고, 직렬화·HF push는 L4 책임). prebuild는 신규 `stages/prebuild.py`.
3. **불변 3종**(byte/구조): HF artifact shape · HF 경로(`macro/{fred,ecos,customs,cycle,regime}`·`landing/dashboards/macro.json`) · UI consume seam. churn 최소(스크립트 보존=dead entrypoint·yml 무변경·UI 무변경).
4. **secret 경계 = CI only**(`_resolveHfToken` 인자>env>.env·gather 진입점 `os.environ`). 흡수해도 push 진입점은 CI(`dartlab.pipeline macro`)·로컬 token=None→`report.fail` 격리.
5. **데이터 전부 = 범위지만 실행은 phased** — MUST=macro 흡수+원칙 박제, SHOULD=dart/news/gov, WONT=44개 일괄·truly-CI-glue 강제흡수·artifact 변경.

---

## 문서 지도

1. [00-prd.md](00-prd.md) — **완전 PRD**(자기충족·plan-deep): 비전·현상진단(stage MIXED 표·42 스크립트 인벤토리 분류·별도빌드 audit)·SSOT 원칙·흡수 설계(edgar 패턴 추출→macro 4함수 상세→krx/news/dart 일반화)·online/offline+CI 경계·consume seam 불변 계약·영향 파일/함수·테스트/가드·롤백·Phase·이중평가·성공/실패 기준·부록 ground-truth 인덱스.
2. [00-eval-ledger.md](00-eval-ledger.md) — 전문가 토론·적대 평가 과정·점수(88/88 SHIP)·ground-truth 4정정 기록.

---

## 기존 데이터 문서와의 관계

| 문서 | 역할 | 본 PRD와의 관계 |
|---|---|---|
| `_done/data-workbench-ssot/` | **UI consume SSOT(공통배선)** — `data/fetch`+`data/origins`+landingJson arm. 완료. | **계승·문서화만** — consume 끝단(이미 준수). 본 PRD는 그 반대편(build side). |
| pipeline `edgar/allFilings/dartZip` stage | 이미 in-library 흡수된 빌드 | **증명된 템플릿** — macro 흡수가 이 패턴 복제. |
| `mainPlan/macro-analysis-superstrengthen/` | macro regime 데이터 *생성*(buildMacroRegime sync) | **흡수 대상** — 본 PRD가 그 sync 스크립트를 stage로 흡수(데이터 전부의 첫 인스턴스). |

즉: **무엇이 소비되나(공통배선·done) ← 무엇이 빌드되나(공동작업대·본 PRD) — macro를 첫 증명으로 전 도메인 흡수 패턴 확립.**
