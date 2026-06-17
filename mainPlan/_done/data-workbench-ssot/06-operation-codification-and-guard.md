# 06. 운영문서 박제 + 기계 가드

상태: 강제 PRD v0.1. "앞으로 별도 패치 없이"의 핵심 — 사상(operation 문서) + 강제(가드 테스트) 둘 다. 문서만으론 회귀한다.

---

## 1. operation 문서 박제

위치: `src/dartlab/skills/specs/operation/ui.md` 에 새 섹션 추가(현 `ui.md` 는 빌드/SPA/env 만 — 데이터층 섹션 부재). Skill OS 절차(skill-os-add: lintSkill 강제섹션 + capabilityRefs + readSkill/generateSkills 동기화) 준수.

박을 본문(요지):

```
## UI 런타임 데이터층 — 단일 작업대 SSOT + 공통배선

### 단일 작업대
- 모든 데이터 호출은 data/fetch.request() 한 진입점을 통과한다. source 는 fetch·URL 문자열·자체 캐시 Map 을
  직접 갖지 않는다(무엇을·어느 오리진·캐시정책만 선언).
- 오리진은 data/origins 레지스트리에 명명 항목으로만 추가한다(HF·range·CF프록시·news/naver 워커·localApi·duckdbHf·landingJson).
- 캐시/dedup 은 어댑터당 RuntimeCache·RequestDedup 단일 인스턴스를 코어가 만들어 주입한다. 전역 싱글턴 금지.

### 공통배선 default (= feedback_terminal_hf_ssot_local_compute 규칙5)
- 터미널/공유 surface 는 무조건 공개·로컬 공통배선이다. 로컬은 *명시적 로컬 전용*이 아니면 공개 HF source 를 재사용한다.
- dev(로컬 앱)는 :8400 백엔드 없이 정적 HF 로 떠야 정상. /api(localApi 오리진)는 진짜 로컬 전용
  (라이브 provider·AI SSE·공시뷰어 격자)만. 로컬 전용 호출은 adapters/local/api 게이트 한 곳에만 둔다.

### 정직 캐시
- 오리진별 TTL 차등. 신선도 데이터(recent.parquet·naver fresh tail)는 짧은/무 TTL. 일괄 캐시 금지.

### 신규 추가 규칙 (ad-hoc 패치 금지)
- 새 데이터 소스 = source 에 request() 호출 한 함수. 새 오리진 = 레지스트리 항목 1개. 새 로컬 엔드포인트 = api 게이트 카탈로그 1줄.
- source 안에서 raw fetch·직접 URL·new Map 캐시 신설 금지(가드가 차단).
```

- `runtime/cacheStrategy.md` 가 이미 있으면 교차링크(중복 금지, 포인터). 데이터층 SSOT 는 `ui.md` 가 정본.
- 주체 중립 기술체(1인칭·모델명·도구명 금지) — 공개 artifact 규칙.

## 2. 기계 가드 — `tests/audit/checkUiDataWiring`

현 상태: UI 용 import/패턴 가드 0(Python `tests/architecture/*` 만 AST census). TS 소스 대상 가드 신설.

**구현 = 정공법 확정(2026-06-17): TS AST 가드.** 정규식 스캔(Python AST-lite)은 TS 를 못 파싱해 false positive/negative(문자열·주석 속 `fetch`·정당한 `new Map`)가 불가피 — 가드의 신뢰를 깬다. 가드 대상이 TypeScript 이므로 *진짜 TS 파서로* 검사하는 게 정공법이다.
- 위치: `tests/audit/checkUiDataWiring.mjs`(또는 `.ts`) — CLAUDE.md 도메인 폴더 규칙(`tests/audit/`)·기존 audit 스크립트 문화(`noScriptsDir.py`·`docstring4Section.py`)와 정합.
- 파서: **`typescript` 컴파일러 API**(이미 svelte-check/tsc 로 toolchain 에 존재 — 신규 무거운 의존 0). `ts.createSourceFile` → AST walk 로 `CallExpression`(fetch)·`NewExpression`(Map)·URL 문자열 리터럴·import 경로를 *의미 기반* 검출. (ts-morph 같은 추가 의존은 불필요 — 컴파일러 API 로 충분.)
- 실행: runtime 패키지 npm script `check:data-wiring` + CI 게이트(기존 svelte-check 가 이미 node 스텝이라 toolchain 부담 0). `tests/run.py` preflight 가 UI 체크를 포함하면 거기에, 아니면 UI CI 잡에 동행.
- baseline 부채원장: 회귀가드 철학(`operation.testing`)과 동일 — 착수 시점 잔존 위반을 `tests/audit/uiDataWiring.baseline.json` 에 기록, 이후 *증가 0* 강제. 이관 완료 source 부터 위반을 baseline 에서 제거(0 으로 수렴).

가드 규칙(baseline 부채원장 = 신규 위반·증가만 fail, 회귀가드 원칙):
1. `adapters/**/sources/*.ts` 에서 **raw `fetch(` 직접 호출 금지** — 코어/게이트 경유만.
2. source 에서 **HF/워커 URL 문자열 직접 구성 금지**(`huggingface`·`workers.dev`·`https://` 리터럴) — 오리진 레지스트리 경유.
3. source 에서 **모듈 레벨 `new Map(` 캐시 신설 금지** — 코어 캐시 사용(이관 완료 source 한정 적용).
4. **공개 어댑터에서 `localApi`/`/api` 참조 금지**(로컬 전용 누수 차단).
5. `RuntimeCache`/`RequestDedup` **인스턴스화 ≥1**(죽은 작업대 재발 방지 — 0 이면 fail).

baseline: P4 시점의 잔존 위반을 원장에 기록 → 이후 *증가 0* 강제. 이관 완료 source 부터 위반 0 으로 끌어내림.

## 3. CLAUDE.md 강행규칙 — 추가 확정(2026-06-17)

판단: 본 규칙은 *아키텍처 무결성 가드*다. 위반(source 가 제멋대로 fetch/URL/Map)이 즉시 크래시는 아니나, **dev=퍼블릭 공통배선 위반은 이미 이번 세션에 실제 회귀를 냈고**(dev 가 :8400 없이 안 뜸), "퍼블릭 서버 0 floor" 위반(예: remote functions)은 아키텍처 손상급이다. 기존 CLAUDE.md 의 "4계층 단방향 import"·"sync/prebuild 책임경계"와 같은 *기계 강제 아키텍처 가드* 계열 → **추가한다.** 단 ≤60줄 예산이라 한 줄, 본문은 operation/가드로 위임.

추가할 한 줄(강행규칙 섹션):
```
## ⛔ UI 데이터 호출 — 단일 작업대 SSOT·공통배선
모든 데이터 호출은 `data/fetch` 단일 진입점 + `data/origins` 레지스트리 경유. source 의 raw fetch·직접 URL·자체 캐시 Map 금지. 터미널/공유 surface 는 무조건 공개·로컬 공통배선(dev=퍼블릭 기준, :8400 없이 떠야 정상). 로컬 전용(/api)은 `adapters/local/api` 게이트 한곳. `tests/audit/checkUiDataWiring` 강제. → `operation.ui` 데이터층 + [memory/feedback_terminal_hf_ssot_local_compute.md]
```
- 가드(§2)가 green 으로 안정된 뒤 추가(가드 없는 규칙은 회귀). 즉 P4 완료 동행.

## 4. 메모리 연동

- `feedback_terminal_hf_ssot_local_compute` 규칙5(공통배선 default·dev=퍼블릭)가 본 PRD 의 사상 뿌리. operation/ui.md 박제는 그 규칙의 *공개 SSOT 화*(외부 기여자가 읽는 객관 규칙). memory=운영자↔AI, operation=공개 — 3층 경계 준수.

## 5. 완료 정의 (이 문서 기준)

- `operation/ui.md` 데이터층 섹션 머지 + lintSkill 통과 + generateSkills 동기화.
- `tests/audit/checkUiDataWiring` CI 등록 + baseline 원장 커밋.
- 가드 5규칙 중 1·2·4·5 는 즉시 green(전면), 3 은 이관 완료 source 부터 점진.
