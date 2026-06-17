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

구현 선택지(택1, 운영자 결정):
- **(A) Python AST-lite census** — `tests/architecture/*` 패턴 미러. `ui/packages/runtime/src/adapters/**/sources/*.ts` 를 정규식/간이 파서로 스캔(파이썬 생태계·기존 preflight 게이트와 동일 진입). CLAUDE.md 테스트 SSOT(`tests/run.py`)에 등록 쉬움.
- **(B) TS 노드 스캐너** — `tests/audit/checkUiDataWiring.ts`(ts-morph/간이 정규식). UI 생태계 친화. 단 CI 게이트에 node 스텝 추가 필요.

가드 규칙(baseline 부채원장 = 신규 위반·증가만 fail, 회귀가드 원칙):
1. `adapters/**/sources/*.ts` 에서 **raw `fetch(` 직접 호출 금지** — 코어/게이트 경유만.
2. source 에서 **HF/워커 URL 문자열 직접 구성 금지**(`huggingface`·`workers.dev`·`https://` 리터럴) — 오리진 레지스트리 경유.
3. source 에서 **모듈 레벨 `new Map(` 캐시 신설 금지** — 코어 캐시 사용(이관 완료 source 한정 적용).
4. **공개 어댑터에서 `localApi`/`/api` 참조 금지**(로컬 전용 누수 차단).
5. `RuntimeCache`/`RequestDedup` **인스턴스화 ≥1**(죽은 작업대 재발 방지 — 0 이면 fail).

baseline: P4 시점의 잔존 위반을 원장에 기록 → 이후 *증가 0* 강제. 이관 완료 source 부터 위반 0 으로 끌어내림.

## 3. CLAUDE.md 연동(선택)

- 본 가드가 안정되면 CLAUDE.md 강행규칙에 한 줄(예: "UI 데이터 호출은 data/fetch 단일 진입점·오리진 레지스트리 경유. source raw fetch·직접 URL·자체 캐시 금지 — `tests/audit/checkUiDataWiring` 강제") 추가 검토. 단 CLAUDE.md 는 ≤60줄·즉시손상 가드만 — 본 규칙이 "즉시 시스템 손상"급인지 판단 후(아니면 operation 문서로 충분).

## 4. 메모리 연동

- `feedback_terminal_hf_ssot_local_compute` 규칙5(공통배선 default·dev=퍼블릭)가 본 PRD 의 사상 뿌리. operation/ui.md 박제는 그 규칙의 *공개 SSOT 화*(외부 기여자가 읽는 객관 규칙). memory=운영자↔AI, operation=공개 — 3층 경계 준수.

## 5. 완료 정의 (이 문서 기준)

- `operation/ui.md` 데이터층 섹션 머지 + lintSkill 통과 + generateSkills 동기화.
- `tests/audit/checkUiDataWiring` CI 등록 + baseline 원장 커밋.
- 가드 5규칙 중 1·2·4·5 는 즉시 green(전면), 3 은 이관 완료 source 부터 점진.
