# 06 — 진행 원장 (결정·토론·NEXT)

## 문서 상태

| 문서 | 상태 |
|---|---|
| README | ✅ v0.1 |
| 00 제품가치·페다고지 | ✅ v0.1 |
| 01 공유 엔진 아키텍처 (★핵심) | ✅ v0.1 |
| 02 로컬/퍼블릭 공통배선 | ✅ v0.1 |
| 03 신규기능 안내 | ✅ v0.1 |
| 04 KILL·경계 | ✅ v0.1 |
| 05 범위·가드레일 | ✅ v0.1 |
| 06 진행 원장 | ✅ v0.1 (본 문서) |

## 작성 경위

2026-06-14. 운영자 요구: "튜토리얼 기능 — map 진입 시 화면 보이며 안내, 터미널은 복잡하니 더 자세히, 항상 on 금지·헤더 버튼 클릭 시작, 최근 신규기능 안내, 큰 글씨·사용자 유도, 혁신적·유지보수 편리, 공통배선으로 로컬/퍼블릭 기능차도 설명. 전문에이전트 토론으로 PRD."

방법: 코드 실측 3 병렬(터미널 헤더·지도/온보딩 자산·로컬/퍼블릭 배선) → 전문에이전트 4 렌즈 토론(UX·아키텍처·런타임·레드팀) 병렬 + 적대검증.

## 핵심 실측 발견 (PRD를 재방향한 것)

1. **★지도엔 이미 완성된 투어가 산다** — `ui/packages/surfaces/src/map/components/TutorialTour.svelte`(606줄: 13스텝·SVG 마스크·데모 콜백·키보드·모바일 하단시트·진행바·첫방문 자동시작, localStorage `dartlab.map.tour.done`). → 이 작업은 *발명이 아니라 추출+확장*.
2. **터미널엔 투어 0** — `grep tour|Tour|튜토리얼|onboard` → `terminal/` 0건. 헤더 `hdrLinks`(AI·토론·이슈)에 버튼 자리 있음.
3. **로컬/퍼블릭 분기는 이미 라이브** — `TerminalSurface.svelte` `allowTerminalAsk = runtime.env.kind === 'local'`. "공통배선으로 기능차 설명"은 *발명이 아니라 이미 존재하는 분기를 말로 옮기는 것*.
4. **capability 타입(`ServiceAvailability='localOnly'`+`upgradeHint`)은 존재하나 소비 0·퍼블릭에서 throw·`localOnly` emit 0개** — 기능차 SSOT가 못 됨. → SSOT=`env.kind` 확정.
5. **모든 터미널 패널이 `Panel.svelte` 단일 래퍼 통과** — `tourId` prop 1개로 전 패널 앵커 가능(39개 일일이 부착 불필요).
6. **`cardGuide.ts`(39 재무카드 what/good/bad)** = "환각 0, 큐레이션만" 패턴 — `whatsNew.ts` 설계의 본보기.

## 주요 결정

| # | 결정 | 근거 |
|---|---|---|
| D1 | **공유 엔진 추출**(복제 아님) | 사용자 "유지보수 편리·공통배선" 명시. 600줄 2벌 복제는 정반대. |
| D2 | 거처 = `_shared/tour/`(새 패키지 아님) | 투어는 내부 부품. exports 증식 과잉. |
| D3 | **기능차 SSOT = `runtime.env.kind`**(services 아님) | services 퍼블릭 throw·`localOnly` emit 0·선례가 env.kind. |
| D4 | anchor = `Panel.svelte` `tourId` 1 prop + 타입 union + dev 가드 | 전 패널 1곳 수렴·빌드/런타임 2중 drift 검출. |
| D5 | 신규기능 = `whatsNew.ts` 큐레이션(CHANGELOG 파싱 아님) | 자동생성 금지 문화·개발자 언어 노이즈. |
| D6 | 깊이 = 트랙 분기(퀵4+챕터), 스텝 수 아님 | 14패널 선형 강제 = 완주율 붕괴. |
| D7 | 첫방문 = 코치마크(자동 모달 아님), Phase 1 | "항상 on 금지" + 발견성 역설 절충. |
| D8 | localStorage 키 상한(done·seenVersion 2 + 코치마크 예외) | SSOT 분열·마이그레이션 부채 차단. |

## 적대 해소 기록

**추출 vs 복제** ([01](01-shared-tour-engine-architecture.md) §0): 아키텍처 렌즈는 "지금 추출", 레드팀은 "복제 후 추출(섣부른 추상 금지)". → **추출하되 레드팀 가드 전부 박음**: 엔진은 `Step[]+spotlight 1컴포넌트` 상한(그래프/커널 reject), map은 얇은 어댑터 뒤로 회귀 표면 0, 키 상한·CHANGELOG 파싱 금지·실재 기능만. 사용자 명시 요구("혁신적·유지보수 편리")가 추출을 강제하고, 레드팀 우려(과추상화)는 하드 가드로 흡수 → 두 렌즈 모두 만족.

**4 렌즈 수렴점**: 4 렌즈가 독립적으로 동일 결론 도달 — ① 재발명 금지(기존 자산 추출) ② SSOT=env.kind ③ 자동파싱·게임화·비디오·텔레메트리·별도 패널 KILL ④ 기능차 표시 원칙(완결성·열등 프레이밍 금지) ⑤ 경계(5 PRD 가리키기만, 미머지 광고 금지).

## v0.1 트림 (2026-06-14, 운영자 "깎자")

폴더 트리 덕지덕지 self-check([[feedback_always_check_clutter]]) 결과 3건 정리:
1. **`tourStore.svelte.ts` 제거** — `?` 버튼·오버레이가 같은 surface 컴포넌트라 module store 불필요(YAGNI). open 상태는 surface 로컬 `$state`(map 기존 패턴). cross-component 트리거 생기면 그때 추가. → `_shared/tour/` 5→4파일([01](01-shared-tour-engine-architecture.md) §1.1).
2. **`content/` 폴더 평탄화** — `map/content/map.tour.ts` → `map/map.tour.ts`, `terminal/content/{…}` → `terminal/{…}`. 파일 1개 위해 폴더 파지 않음.
3. **`whatsNew.ts`는 `tour/` 유지** — 폴더 하나 더 파는 게 오히려 덕지덕지(규모 작음). 재검토 보류.
핵심 골격(엔진/콘텐츠/배선 3분리·Panel tourId 1 prop·env.kind SSOT)은 *순감산*이라 무변경.

## NEXT

1. 운영자 PRD 리뷰 → v0.1 확정 또는 보강 지시.
2. 착수 = 운영자 go. 선행 가능 = Phase 0 추출+map 어댑터화([05](05-scope-phasing-guardrails.md) §5).
3. 착수 시 첫 단계: `_shared/tour/TourEngine.svelte` 추출 + map 어댑터화 + 13스텝 시각 회귀 0 검증(터미널 손대기 전).

## 미해결 (착수 전 결정 불요, 구현 중 정공법)

- 투어 z-index 토큰값(터미널 `.scrimWrap=200` 위 배치) — 구현 시 실측.
- (해소) `tourStore` 모듈 신설 안 함 — open 상태는 surface 로컬 `$state`. `?` 키 바인딩도 surface별 소유(한 페이지 1 surface라 충돌 없음). v0.1 트림 § 참조.
- 터미널 챕터 카피 큐레이션(퀵4 + 4챕터 본문) — Phase 0 착수 시 사람 작성.

## 착수 게이트

코딩 아님(방향 문서). 착수 = mainPlan 정착 + **운영자 go**. UI 작업이라 push는 운영자 명시 승인 후(commit까지 자율).
