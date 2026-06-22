# 가이드 투어 + 신규기능 안내 — 공유 엔진 PRD

상태: PRD v0.1 (2026-06-14, 전문에이전트 4 렌즈 토론 + 적대검증 + 코드 실측)
범위: 지도(map)·터미널(terminal) 두 surface에 **헤더 버튼으로 켜는 가이드 투어**와 **명확한 신규기능 안내**를 *하나의 공유 엔진*으로 깐다. 사용자가 클릭할 때만 시작(항상 on 금지), 큰 글씨·사용자 유도, 그리고 **공통배선으로 로컬↔퍼블릭 기능차까지 같이 설명**한다.

> ⚠ 본 문서는 *기존 surface 확장* PRD다. 새 제품·새 추상이 아니다. 결정적 실측: **지도엔 이미 완성된 투어가 산다** — `ui/packages/surfaces/src/map/components/TutorialTour.svelte`(606줄: 13스텝·SVG 마스크 하이라이트·"▶ 실제로 해보기" 데모 콜백·키보드·모바일 하단시트·진행바·첫방문 자동시작). 이 작업은 *투어를 발명하는 게 아니라* 그 완성품을 **공유 엔진으로 추출 + 터미널로 확장 + 런타임 인지 주석 배선**이다.

---

## 한 줄 결론

**진짜 가치는 "온보딩 극장"이 아니라 *묻힌 자산의 발견성*이다.** 지도엔 좋은 투어가 이미 있고, 터미널은 밀도가 높아 기능이 묻혀 있다(전체화면 차트·심층 탭·스캔등급·섹션 점프). 그래서 추가할 것은 **헤더 `?` 버튼 1개 + 터미널용 ≤7스텝 투어**고, 박을 것은 **하나의 spotlight 엔진(map+terminal+미래 surface 공유)·런타임 인지 기능차 주석(`env.kind` SSOT)·기능차 표시 원칙(완결성 주장·열등 프레이밍·자동파싱 금지)**이다. 강함은 쌓아서가 아니라 깎아서 — 자동생성·게임화·비디오·텔레메트리·별도 패널은 전부 덕지덕지.

---

## A. 추가할 개념 (새로 넣을 것)

1. **★공유 투어 엔진** — *유일한 진짜 신설.* map의 606줄 `TutorialTour.svelte`를 `_shared/tour/`로 추출: **로직만 든 `TourEngine.svelte` + surface별 콘텐츠 데이터(`*.tour.ts`) + 액션 맵 주입**. map은 얇은 어댑터 뒤에서 기존 동작 100% 유지(landing 계약 무변경=회귀 표면 0), 터미널은 새 엔진 직접 소비. → [01-shared-tour-engine-architecture.md](01-shared-tour-engine-architecture.md).
2. **헤더 `?` 버튼 + ≤7스텝 터미널 투어** — 헤더 `hdrLinks` 군집(AI·토론·이슈 옆)에 진입점 1개. 깊이는 *스텝 수가 아니라 트랙 분기*로(퀵 4 + 챕터 메뉴). cardGuide 39개는 투어가 *가리키기만* 하고 백과사전화 금지. → [00-product-value-and-pedagogy.md](00-product-value-and-pedagogy.md).
3. **신규기능 안내** — *사람 큐레이션* `whatsNew.ts`(CHANGELOG 자동파싱 금지). 단일 키 `seenVersion`, unseen일 때만 뱃지 1개, "신규 없음"·"다 봤음" 단언 금지. 항목 클릭 → 관련 투어 챕터로 점프(투어 스텝 재사용). → [03-whatsnew-feature-announcement.md](03-whatsnew-feature-announcement.md).

## B. 박을 개념 (확정해두는 결정)

4. **★기능차 안내 SSOT = `runtime.env.kind`** — services descriptor 아님(퍼블릭에서 getter throw·`localOnly` emit 0개). 2층: 콘텐츠 데이터 `scope:'both'|'localOnly'` × `env.kind` *한 번* 매핑. → [02-local-public-common-wiring.md](02-local-public-common-wiring.md).
5. **기능차 표시 원칙** — "다 배웠음"·"신규 없음"·"퍼블릭 열등" 3금지. 로컬 전용 스텝은 *숨기지도 광고하지도* 않고 비활성+이유+설치 CTA(막다른 길 금지). 큰 글씨·"유도"는 가독성이지 다크패턴 아님(탈출 자유 패리티). → [02](02-local-public-common-wiring.md) §2, [04-killlist-and-boundaries.md](04-killlist-and-boundaries.md) §4.
6. **경계 — 5 PRD 소유 침범 금지.** 투어는 워치리스트(terminal-improvement)·reverseDCF/compare(financial-statement-lab)·시뮬/이벤트레일(scenario-simulator)·등급 다이얼로그(scan-grade-explainer)·내보내기(table-export)를 *가리키기만* 한다. 미머지 기능 "곧 출시" 광고 금지(투어는 진실의 후행 지표). → [04](04-killlist-and-boundaries.md) §3.

---

## 문서 지도

1. [00-product-value-and-pedagogy.md](00-product-value-and-pedagogy.md) — 왜 발견성인가·최소가치코어·청중 분리(투어=신규/신규기능=재방문)·트랙형 깊이·cardGuide 가리키기·큰 글씨 카피 스펙·첫방문 코치마크.
2. [01-shared-tour-engine-architecture.md](01-shared-tour-engine-architecture.md) — ★핵심. `_shared/tour/` 추출·`TourStep` 스키마·actionId 결합 끊기·`Panel.svelte` `tourId` 앵커 SSOT·타입 union + drift 가드·map 무중단 마이그레이션·과잉추상 KILL.
3. [02-local-public-common-wiring.md](02-local-public-common-wiring.md) — 기능차 SSOT(`env.kind`)·2층 모델·`publicNote` 명시 카피·floor/headroom 프레이밍·미배선 포트 touch 금지·미래 services 수렴.
4. [03-whatsnew-feature-announcement.md](03-whatsnew-feature-announcement.md) — `whatsNew.ts` 큐레이션·seenVersion 단일 키·tourTrack 재사용·뱃지 명시(숨김≠"없음")·실재 기능만.
5. [04-killlist-and-boundaries.md](04-killlist-and-boundaries.md) — KILL/DEFER/KEEP 판정표·5 PRD 경계·미머지 광고 함정·다크패턴 차단·안내 가드.
6. [05-scope-phasing-guardrails.md](05-scope-phasing-guardrails.md) — Phase 0/1/2/(추출)·성공기준(스텝 수 아님)·localStorage 키 상한·회귀 가드·착수 게이트.
7. [06-progress-ledger.md](06-progress-ledger.md) — 결정·4 렌즈 토론 기록·추출 vs 복제 적대 해소·문서 상태·NEXT·착수=운영자 go.

---

## 한계 표기 척추 (전 문서 관통)

- **기존 surface 확장이다.** map 투어(606줄)·cardGuide(39카드)는 이미 프로덕션급. 신규는 "추출 + 터미널 콘텐츠 + 런타임 주석" 셋뿐.
- **공유 엔진은 `Step[] + spotlight 1컴포넌트`에서 못 벗어난다.** 그래프/커널/디스패처/노드 시스템 신설 = reject(no-graph-regression 동형).
- **기능차의 진실원천은 `env.kind` 한 줄.** services descriptor는 퍼블릭에서 throw이고 차이를 안 담아 SSOT가 못 된다. 미배선 포트는 *접근만 해도* throw — localOnly 스텝의 퍼블릭 렌더는 포트를 절대 touch 안 한다.
- **퍼블릭이 floor, 로컬이 headroom.** 데이터(price/finance/macro/company)는 양쪽 HF 공유로 *동일* — 가짜 차이 날조 금지. 차이는 AI·storage·navigation·services 4개에만.
- **완결성·미래 약속 금지.** "다 봤음"·"신규 없음" 0. 투어/신규기능은 *현재 머지돼 화면에 실재하는 기능만* 가리킨다(기능 PR과 같은 커밋에서 스텝 갱신).
- **자동생성 카피 금지.** cardGuide 원칙("환각 0, 큐레이션 텍스트만") 계승. CHANGELOG·git tag 파싱 0.
- **코딩 아님.** 방향 확정 문서. 착수는 mainPlan 정착 + 운영자 go 후.
