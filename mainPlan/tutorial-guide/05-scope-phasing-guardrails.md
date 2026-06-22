# 05 — 범위 단계화 + 가드레일

## 1. Phase (싼 것 먼저, 자동시작·추출은 나중)

각 Phase 완결·검증·푸시 후 다음. UI 변경이라 자동 push 금지 — commit까지 자율, push는 운영자 명시 승인("푸시해"·"올려"·"발간해") 후(feedback_ui_rules·git_rules).

| Phase | 내용 | 성공기준 (스텝 수 아님) |
|---|---|---|
| **0 — 공유 엔진 추출 + 터미널 `?` 투어** | ① map `TutorialTour.svelte` → `_shared/tour/TourEngine.svelte` 추출(로직만), localStorage 키 파라미터화, map은 얇은 어댑터로 축소(landing 계약 무변경). ② `map.tour.ts` 콘텐츠 분리. ③ `Panel.svelte`에 `tourId` prop. ④ 터미널 `terminal.tour.ts`(퀵4+챕터, ≤7 핵심) + 헤더 `?` 버튼. 데모는 *비파괴 하이라이트*만. 카피=사람 큐레이션. | ① `?` 클릭→투어 열림·Esc/건너뛰기 e2e ② 데모가 회사 상태 영구 변경 0(닫으면 원복) ③ **map 시각 회귀 0**(13스텝 스크린샷 눈검수) ④ svelte-check 0·콘솔 0 ⑤ 터미널 투어 스크린샷 눈검수(큰 글씨·안내 문구) |
| **1 — 첫방문 코치마크 (조건부)** | `?sym` 딥링크 *없는* 순수 진입 + `tour.done` 미설정에 헤더 `?` 펄스 말풍선(자동 모달 아님). map `!focus && !cmp` 가드 차용. | ① `?sym=` 진입 시 코치마크 안 뜸(블로그 임베드 침입 0) e2e ② reload 후 재노출 0(코치마크 seen 키) ③ DOM에 "푸시"·완결성 문구 0 |
| **2 — 로컬/퍼블릭 주석 + 신규기능 안내** | ① `TourStep.requires`+`publicNote`, 엔진 `evalStep`(env.kind 분기). 터미널 AI 챕터에 localOnly 스텝. ② `whatsNew.ts` 큐레이션 소수 + `seenVersion` 단일 키 + 뱃지 1개 + `tourTrack` 점프. | ① 퍼블릭에서 localOnly 스텝이 포트 touch 0·정적 `publicNote`만(throw 0) e2e ② "퍼블릭 열등" 프레이밍 0(눈검수) ③ **CHANGELOG import 0**(자동 grep 게이트) ④ "곧 출시"·미머지 기능 언급 0 ⑤ 뱃지: unseen 0이면 미표시(="신규 없음" 문구 0) |

> Phase 0이 추출을 *포함*하는 이유: 터미널을 복제로 만들면 600줄 2벌 = 사용자가 거부한 "유지보수 지옥". 추출의 회귀 위험은 "map을 얇은 어댑터 뒤로, 스크린샷 눈검수"로 흡수([01](01-shared-tour-engine-architecture.md) §4). 즉 *추출과 터미널 투어는 한 Phase의 양면*이다.

## 2. 성공기준 / 반-성공기준

**성공(긍정)**:
1. 신규/재방문자가 *묻힌 기능 1개 이상을 발견해 쓰는가*(발견성).
2. 투어 종료 후 *재방문 이유가 생기는가*(map 투어가 닫는 루프와 동형).
3. 기능차를 있는 그대로 표시하는가(서버없음·기기종속·로컬/퍼블릭 차이 노출).
4. 유지보수: 새 surface 투어 추가 = `*.tour.ts` 데이터 1파일 + actionMap. 엔진 코드 0줄 수정.

**반-성공(이걸 성공으로 착각 금지)**: 스텝 수·투어 화려함·"완주율"·신규기능 뱃지 개수·게임화 지표. `?` 버튼 1개가 묻힌 자산을 *연결*하는 게 성공이지 투어 분량이 아니다.

## 3. 회귀 가드 (자동/수동)

- **CHANGELOG import 0** — Phase 2 자동 grep 게이트(투어 코드가 CHANGELOG.md를 import/fetch 하면 실패).
- **엔진 단방향** — `_shared/tour/`는 surface 폴더(terminal/map) import 금지(콘텐츠가 엔진을 import, 역방향 금지). PR 리뷰 + 가능하면 lint-imports 계약.
- **anchor drift** — dev 런타임 가드(console.warn) + 투어 e2e 하이라이트 존재 assert([01](01-shared-tour-engine-architecture.md) §2.3).
- **map 시각 회귀 0** — 추출 후 13스텝 스크린샷 눈검수(feedback_ui_rules).
- **별도 엔진/그래프 신설 reject** — no-graph-regression 동형. PR 리뷰 체크.

## 4. localStorage 키 예산

surface별 키 상한 — 초과 시 *설계 재검토 트리거*(SSOT 분열 방지):

| 키 | Phase | 의미 |
|---|---|---|
| `dartlab.{surface}.tour.done` | 0 | 투어 완료(1회) — map 기존 키 파라미터화 |
| `dartlab.{surface}.tour.seenVersion` | 2 | 신규기능 마지막 본 버전 |
| `dartlab.{surface}.tour.coachmark` | 1 (조건부) | 코치마크 노출 여부 — done과 분리 필요해 *유일한 예외*, 도입 시 정당화 동행 |

핵심 2키(`done`·`seenVersion`)가 기본. 코치마크 키는 Phase 1 채택 시에만, 그 추가가 "재검토"의 명시적 대상. 이상은 reject. ui-platform-refactor StoragePort 배선 시 raw localStorage → port로 함께 이관.

## 5. 착수 게이트

- **코딩 아님** — 방향 확정 문서. 착수 = ① terminal/map이 `ui/packages/surfaces` 정착(완료) ② **운영자 go**.
- **선행 가능** — Phase 0의 *추출+map 어댑터화*는 mainPlan 무관하게 선행 가능(raw localStorage 1키, 시각 회귀만 눈검수). 단 터미널 콘텐츠 카피·로컬/퍼블릭 주석은 운영자 go 후.
- **충돌 시** — 기존 5 PRD가 정본, 투어는 *연결 레이어*로 양보([04](04-killlist-and-boundaries.md) §3).
- **UI 작업이라 push는 운영자 명시 승인 후** — commit까지 자율, 그 전엔 "검사 대기" 한 줄(git_rules UI 예외).
