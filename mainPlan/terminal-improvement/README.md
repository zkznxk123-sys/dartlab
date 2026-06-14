# 기존 터미널 개선 — 추가할 개념 + 박을 개념 (블룸버그식 방향)

상태: 비전 PRD v0.2 (2026-06-14, 전문에이전트 4 렌즈 토론 + 코드 실측 + 레드팀 검증 / v0.2 = "OS" 프레이밍 제거·로컬/퍼블릭 2 타깃 정정)
범위: **지금 있는 /terminal 을 개선**한다 — 새 제품·새 추상이 아니다. "블룸버그식"으로 한 단계 가기 위해 *추가해야 할 개념*과 *박아둘(확정할) 개념*을 정한다. 수직 분석(차트·재무·forensic)은 이미 초과 수준이라 손대지 않고, **비어 있는 것만 채운다.**

> ⚠ 본 문서는 *기존 터미널 개선* PRD다. "터미널 OS 레이어"라는 옛 프레이밍(v0.1)은 *새 걸 짓는다*처럼 과장돼 폐기 — 진단 통찰("빠진 건 분석이 아니라 *분석들을 묶는 수평적 개념들*")은 유지하되, 실제 작업은 **기존 surface(`ui/packages/surfaces/src/terminal`) 확장**이다. 진짜 신설은 워치리스트 1 개뿐.

---

## 한 줄 결론

**개선의 핵심은 분석을 더 파는 게 아니라, 이미 가진 분석들을 *묶는 수평적 개념*을 채우는 것이다.** 블룸버그가 깊은 분석 도구들과 다른 점은 분석 깊이가 아니라 *워치리스트·커맨드·모니터 루프*로 그것들을 묶는 데 있다 — dartlab 터미널은 분석(FA·GP·CN)은 블룸버그 초과인데 이 *묶는 층*이 비어 "깊은 분석 웹앱이지 내 터미널"이 아니다. 그래서 **추가할 개념 = 워치리스트(우리에겐 *공시 워치*) + 커맨드바 섹션 점프** 둘, **박을 개념 = 무엇을 안 할지(KILL)·경계(기존 PRD 소유)·정직 모델(서버 없음/EOD)·로컬↔퍼블릭 2 타깃**이다.

---

## A. 추가할 개념 (기존 터미널에 *새로* 넣을 것)

> 4 렌즈 토론 + 적대검증이 블룸버그 원시요소 7 후보를 *깎아* 남긴 것. 강함은 쌓아서 아니라 깎아서.

1. **★워치리스트 = 공시 워치** — *유일한 진짜 신설.* 기존 `LeftRail`(스크리너·히트맵 옆)에 "내 회사들" 패널. 어떤 기존 PRD 도 미claim(grep 0). 가격 워치가 아니라 *공시 델타*를 지켜본다 — 우리 데이터(공시)·우리 사용자(forensic)·우리 제약(EOD)에 맞는 유일한 monitor. 3 층(큐레이션 → 기기독립 신선도 → 정직 라벨 재방문 델타). → [02-watchlist-disclosure-watch.md](02-watchlist-disclosure-watch.md).
2. **커맨드바 섹션 점프** — 기존 `‹GO›`(현 종목검색 전용)에 "회사 + 섹션 토큰"(예: `삼성전자 공급망`) 인식 *한 겹*. 기능은 이미 다 있고 점프 문법만 없음. 풀 mnemonic 백과사전은 cargo-cult — *검색의 자연 확장*으로만. → [03-command-and-architecture.md](03-command-and-architecture.md) §1.

## B. 박을 개념 (확정해두는 결정 — 안 할 것·경계·모델)

3. **KILL — 안 할 것을 박는다.** 멀티패널 워크스페이스/Launchpad(불가침 구역규칙 파괴·cargo-cult)·푸시 알림(퍼블릭 서버 0)·reverseDCF→`IMP` 함수승격(라벨갈이)·멀티심볼 보드(compare()가 소유). **DEFER:** 크로스에셋 instrument 타입(모든 포트 `code:string`, contracts 전반 개정=최대 재발명). → [04-killlist-and-non-goals.md](04-killlist-and-non-goals.md).
4. **경계 — 기존 PRD 소유를 침범 안 한다.** JUDGE 분석(reverseDCF·compare 동종백분위·가격↔기초체력 오버레이) = **financial-statement-lab**. 시뮬·Play·지수·백테스팅·공시 이벤트레일 = **scenario-simulator**. egress = **table-export**. 포트 원칙 = **ui-platform-refactor**. 개선은 이들을 *연결*만 하지 재발명 안 한다. → [03](03-command-and-architecture.md) §4.
5. **정직 모델 — 못 하는 것을 숨기지 않는다.** 알림 푸시·크로스기기 동기화는 *퍼블릭에선 불가*(정적 호스팅). "재방문 델타"는 완결성 주장 금지·기기/시점 명시. 컨센서스·목표주가 단정 금지. → [02](02-watchlist-disclosure-watch.md) §3, [05-scope-phasing-guardrails.md](05-scope-phasing-guardrails.md) §2.
6. **★로컬 ↔ 퍼블릭 2 타깃 — 같은 surface, 다른 런타임.** 개선 대상 터미널은 *하나의 공유 컴포넌트*가 두 배포(퍼블릭 landing + 로컬 ui/apps/local)에 다른 런타임으로 주입된다. 퍼블릭=정적·HF·포트 미배선(floor), 로컬=백엔드 :8400·포트 배선됨(headroom). **개선은 퍼블릭 floor 에 설계하고, 로컬의 배선된 포트가 같은 코드로 bonus 를 켠다**(local-only 기능 금지·열화 UX 숨김 금지). → [03](03-command-and-architecture.md) §7.

---

## 문서 지도

1. [00-product-vision.md](00-product-vision.md) — 왜 *묶는 개념*이 빠진 것인가·사용자 monitor 루프 5 단계·"공시 워치 ≠ 가격 워치"·왜 지금 ROI 가 높은가.
2. [01-bloomberg-concept-gap.md](01-bloomberg-concept-gap.md) — 블룸버그 원시요소 카탈로그(중심성·보유여부)·"묶는 층 vs 분석" 분리·현대 리테일(Koyfin/TIKR) 절제선.
3. [02-watchlist-disclosure-watch.md](02-watchlist-disclosure-watch.md) — ★핵심 추가 개념. 워치리스트(공시 워치)·3 층·정직 가드·storage 계약·거처·비목표.
4. [03-command-and-architecture.md](03-command-and-architecture.md) — 섹션 점프·아키텍처 거처·포트 실태(로컬 배선/퍼블릭 미배선)·non-encroachment·instrument DEFER·★로컬/퍼블릭 2 타깃.
5. [04-killlist-and-non-goals.md](04-killlist-and-non-goals.md) — KILL/DEFER 판정표·정체성 가드·덕지덕지 차단.
6. [05-scope-phasing-guardrails.md](05-scope-phasing-guardrails.md) — Phase·정직 가드·성공기준(차트수 아님)·착수 게이트.
7. [06-progress-ledger.md](06-progress-ledger.md) — 결정·토론 기록·문서 상태·NEXT·착수=운영자 go.

---

## 정직 척추 (전 문서 관통)

- **기존 터미널 개선이다.** 새 제품·새 추상 아님. 모든 제안이 기존 surface 확장. 수직 분석은 손대지 않는다.
- **퍼블릭이 floor, 로컬이 headroom.** 못 하는 것(푸시·동기화)은 *퍼블릭에서* 불가 — 숨기지 않고 명시. 로컬 백엔드는 같은 포트로 bonus 지 local-only 기능이 아니다.
- **완결성 주장 금지.** "다 봤음"·"신규 없음" 금지(상태 기기로컬). "이 기기 · 마지막 방문 06-12 이후"만.
- **컨센서스·목표주가 흉내 금지.** reverseDCF 는 "가격이 요구하는 것의 읽기"(fin-stmt-lab 가드레일 계승).
- **claim 안 한다.** 기존 4 PRD 소유를 재발명·재명명 안 함. 충돌 시 기존 PRD 정본.
- **코딩 아님.** 방향 확정 문서. 착수는 mainPlan 정착 + 운영자 go 후.
