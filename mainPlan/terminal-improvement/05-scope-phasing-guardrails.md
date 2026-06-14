# 05. 범위 · Phase · 가드레일

상태: 비전 PRD v0.2
범위: Phase 시퀀스(각 완결·검증·푸시), 정직 가드, 성공기준, 착수 게이트.

---

## 1. Phase 시퀀스 (각 단계 완결·검증·푸시 후 다음)

본 PRD 는 *현재/과거* 모니터 루프만 신설(미래·시뮬은 scenario-simulator). 워치리스트를 정직성 위험이 낮은 층부터 쌓는다.

| Phase | 내용 | 의존 | ★정량 수용기준(AC) |
|---|---|---|---|
| **0** | 워치리스트 Tier 0 — 큐레이션 종목집합(`LeftRail` 패널 + 헤더 ☆ + `terminal.watchlist` 상태). | 없음(raw localStorage 또는 StoragePort) | ① ☆ 토글로 추가/제거 후 reload 시 워치 집합 유지(localStorage e2e) ② 헤더 ☆ 상태 = 현 종목의 워치 포함여부 반영 ③ svelte-check 0·콘솔 0·스크린샷 눈검수 |
| **1** | 워치리스트 Tier 1 — *절대시간* 신선도 배지("최근 N 일 신규 N 건"). 정렬 토글. | Phase 0 + **신규 `allFilings/recent.parquet` cross-company 리더 포트(02 §5)** | ① **워치 30 사 신선도 로드 시 공시 fetch ≤ 1 회**(cross-company 단일 파일, per-company N 회 아님) ② 배지 카운트 = `rceptDate ≥ now−N일` 행수와 일치(골든) ③ "최근 신규" 정렬 시 신규공시 보유사 상단 |
| **2** | 섹션 점프 — GO/suggest "회사+섹션 토큰". *선결: forensic 패널 `data-section` id 부여*(03 §1). | 토큰→타깃 매핑표(03 §1) + 식별자 부여 | ① 토큰 4 종(공급망·거버넌스·손익·자사주) → 정확한 패널 scroll/탭 activate/전체화면 e2e ② 모호 토큰(손익) 기본=RightStack IS·⇧=전체화면 규칙 적용 ③ 구역규칙 무위반(점프가 중앙↔우측 경계 안 깸) |
| **3** | 워치리스트 Tier 2 — 정직 라벨 재방문 델타. 가격 보조컬럼. | Phase 1 + StoragePort 타임스탬프 | ① **DOM 에 "알림"·"notification"·"푸시" 문자열 0**(정직 가드 자동 게이트) ② "이 기기 · 마지막 방문 {ts}" 배지가 델타 옆 *항상* 렌더 e2e ③ 델타 = `rceptDate > lastVisit` 행수와 일치(골든)·완결성 문구("다 봤음" 등) 0 |
| **(정합)** | StoragePort 배선 정합 — `terminal.watchlist` 를 StoragePort 경유로(ui-platform-refactor 단계-4a-3 과 한 묶음). raw localStorage 선출시분 이관. | ui-platform-refactor 진척 | 포트 required·silent fallback 0·raw `dlTerm.watch` 잔존 0 |

**의존 주의**: Tier 0/1(Phase 0-1)은 raw localStorage(현 패턴)로 *선행 가능*하나, ⚠이는 *다섯 번째 raw 키를 늘리는 부채*라 ui-platform-refactor 의 raw 청산·port required 방향과 역행한다 — **단계-4a-3(StoragePort 주입)이 임박했다면 raw 선출시를 건너뛰고 StoragePort 를 기다리는 게 정합**(선출시 여부 = 4a-3 진척과 1 회 정합 확인 후 결정, 06 NEXT). Tier 2(Phase 3)부터 StoragePort 정합이 자연스럽다. 섹션 점프(Phase 2)는 워치리스트와 독립이라 순서 유연하나, 루프를 닫는 핵심(워치리스트)이 먼저다.

---

## 2. 정직 가드 (출시 차단 항목)

- **완결성 주장 금지** — "다 봤음"·"신규 없음" 등 완결 진술 0. "이 fetch 에서 신규 N 건"만(02 §3).
- **기기·시점 명시** — "이 기기 기준 · 마지막 방문 {ts}" 항상 노출. 동기화 불가 숨김 금지.
- **"알림" 단어 금지** — "재방문 델타"·"신선도"·"마지막 방문 이후"만.
- **컨센서스·목표주가 단정 금지** — reverseDCF 연결 시 fin-stmt-lab 가드레일 계승("읽기"지 "X 원" 아님).
- **공개 터미널 무중단** — 로컬 프리뷰 격리·미배선 커밋·완결 단위만 push. landing + ui/web 둘 다 무중단(feedback_ui_rules).
- **푸시 전 스크린샷 전수 눈검수** — 정량 PASS 가 디자인·문구 디테일을 못 본다(feedback_ui_rules). 특히 정직 문구는 픽셀 검수.

---

## 3. 성공기준 (차트수·기능수 아님)

블룸버그는 30,000 함수가 아니라 *워크플로 루프*로 측정된다. 본 PRD 도:

- ✅ **재방문 이유가 생겼는가** — 사용자가 "내 회사들"을 만들고, 재방문 시 *그동안 뭐가 바뀌었나*를 5 초에 보는가(00 §3 ①WATCH·②SURFACE 끊김 해소).
- ✅ **루프가 닫혔는가** — WATCH→SURFACE 에서 기존 DIG(③)·JUDGE(④, fin-stmt-lab)·RECORD(⑤, table-export)로 끊김 없이 흐르는가.
- ✅ **정직한가** — 서버 없음·기기종속을 *숨기지 않고* 노출하면서도 가치를 주는가.
- ❌ **반-성공기준**: 패널 수·함수 수·차트 종류 증가는 성공이 *아니다*. 워치리스트 1 개가 기존 자산을 루프로 묶는 게 성공. 새 패널 누적은 덕지덕지 신호.

---

## 4. 착수 게이트

- **코딩 아님** — 본 PRD 는 *방향* 확정 문서. 착수는 다음 후:
  1. mainPlan(ui/packages 승격) 완료 — 터미널이 `ui/packages/surfaces` 에 정착(이미 이관됨, 잔여 정합은 ui-platform-refactor 07-progress-ledger).
  2. **운영자 go.**
- **선행 가능 부분** — Tier 0(큐레이션)은 mainPlan 무관·raw localStorage 로 선행 가능(scenario-simulator 지수차트가 선행 가능한 것과 동급). 단 운영자 go 후.
- **충돌 시** — 기존 4 PRD(scenario-simulator·fin-stmt-lab·table-export·ui-platform-refactor)가 정본. 본 PRD 는 연결 레이어로서 양보.
