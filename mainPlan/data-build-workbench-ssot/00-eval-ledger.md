# 00. 전문가 토론 · 적대 평가 원장

> 운영자 goal: "전문가토론으로 공공[공동]작업대 데이터배선까지 확립하라. PRD는 데이터 전부까지다." 본 원장은 그 과정·점수·ground-truth 정정을 기록한다.

---

## 1. 과정

1. **현상 스카우트(2 read-only 에이전트 병렬)** — (a) UI 공통배선(consume): macro.json이 `dartlabData.ts loadJson()` 단일 진입(landingJson arm·dual-SSOT sibling)으로 이미 SSOT 준수·`checkUiDataWiring` 위반 0·regime 편승. (b) 공동작업대(build): 엔진 위임 청결(별도빌드 0)이나 오케스트레이션이 `.github/scripts`에 산재.
2. **인벤토리 직접 실측** — `.github/scripts/{sync,prebuild}` 42개 `.py`(sync 31+prebuild 11). pipeline stage **MIXED**: in-library 흡수(edgar/allFilings/dartZip/edgarPanel/reconcile) vs subprocess 미흡수(macro/krx/news/dart). → "흩어진 스크립트 흡수"는 *부분 완료*·macro는 laggard. data-workbench-ssot(`_done`)는 consume(UI)만·build측 흡수 PRD 부재.
3. **전문가 토론 워크플로**(`wf_eb2f5103-20c`·8에이전트) — 5 포지션(공동작업대 아키텍트·online/offline+CI·반-스코프크리프 회의론자·consume-seam·데이터엔지니어, **edgar in-library 실패턴을 직접 Read**) → 종합 PRD(자기충족) → 적대 평가 2인(데이터 아키텍트·회의론자/PM).
4. **ground-truth 정정** — 평가 blocker를 *또 한 번의 에이전트 라운드가 아니라* 소스 직접 검증으로 교정([[behavior]] 패턴).

---

## 2. 점수

| 평가자 | 점수 | 판정 | 핵심 blocker |
|---|---|---|---|
| 데이터 플랫폼 아키텍트 | 88 | **SHIP** | ① offline AST 가드 = glob 확장 불가(`_findMainFunc`가 `main`만 매칭) ② macro.json byte 동등 비결정(`asOf=date.today()`) |
| 반-스코프크리프 회의론자/PM | 88 | **SHIP** | ③ full-folder 업로드 의미 미단언(`uploadCategoryToHf` 증분 fallback) ④ commit_message 동등대상 오해 소지 |

둘 다 SHIP — 핵심 설계(in-library 흡수·edgar 템플릿·macro 첫 증명·artifact/seam 불변·스코프 절제)는 합격. blocker 4종은 전부 *PRD 테스트/게이트 정밀도*(자기충족성)이지 설계 결함 아님.

---

## 3. ground-truth 4정정 (소스 직접 검증 후 PRD 교정)

| # | 평가 지적 | 소스 ground-truth(직접 Read) | PRD 교정 |
|---|---|---|---|
| 1 | offline 가드 "PREBUILD_DIR glob 확장"이면 됨 | `test_prebuild_offline.py:55-59` `_findMainFunc`는 `node.name=="main"`만 찾고 `:99`에서 `assert mainFunc is not None` → `runMacroJson`(=`main` 아님)은 **FAIL(no-op 아님)** | §4.1·§7.2·§8.2-3: glob 확장 폐기 → **신규 평행 테스트** `test_inlibrary_prebuild_offline.py`(stage `run`* finder + 기존 헬퍼 `_firstNonDocstringStmt`/`_callsEnforceOffline`/`_collectImports` 재사용). 기존 테스트 불변(`main` 계약 유지) |
| 2 | macro.json "전 필드 byte 동등" 불가 | `buildMacroJson.py:271` `asOf=date.today().isoformat()`·regime `computedAt` = 실행 시각 비결정 | §8.2-1·§12-2·§12-7·§7.3: "byte 동등"→**"구조 동등"**(타임스탬프 `asOf`/`computedAt` 정규화 제외 후 deep-equal + parquet schema/정렬/dtype) |
| 3 | full-folder 업로드 의미 미단언 | `hfUpload.py:86` `uploadCategoryToHf`=changed 매니페스트 우선·부재 시 full fallback. macro는 `changed_macroFred.txt` 미생성→full | §7.3·§8.2-5: **changed 매니페스트 부재 단언**(full-folder fallback=`upload_folder` 의미 동등) + 흡수 후 매니페스트 도입 금지(silent drift 차단) |
| 4 | commit_message 동등대상 오해 | 스크립트 `"build: macro {subdir}..."` vs `uploadCategoryToHf` 표준 메시지 = 메타데이터 | §7.3: commit_message는 **동등 대상 아님(메타)** 명기(거짓실패 방지) |

(정정은 추측이 아니라 `test_prebuild_offline.py`·`buildMacroJson.py`·`hfUpload.py` 실측 근거.)

---

## 4. 최종 판정

전문가 5인 종합 PRD가 적대 평가 2인 SHIP(88/88), 핵심 설계 합격. blocker 4종은 소스 ground-truth 직접 검증으로 PRD에 정밀 교정 반영(자기충족성 닫음). PRD는 이제 "이 문서만 보고 재조사 없이 구현 가능"(plan-deep) 기준 충족. 착수 = 운영자 go.
