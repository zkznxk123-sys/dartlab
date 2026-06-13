# 터미널 OS 레이어 — "블룸버그식 터미널" 방향 PRD Index

상태: 비전 PRD v0.1 (2026-06-14, 전문에이전트 4 렌즈 토론 + 코드 실측 검증으로 방향 확정)
범위: /terminal 을 "블룸버그식 터미널"로 키우는 방향. **단 분석 깊이를 더 파는 게 아니라, 이미 초과 수준인 수직 분석을 *터미널답게 직조하는 수평 OS 레이어*를 채운다.** **★실제 *신설*은 워치리스트(공시 워치) 단 1 개**(+ 섹션점프 약화 1 겹) — 나머지는 전부 KILL/DEFER 거나 기존 4 PRD 소유다. 따라서 본 PRD 는 "거대한 우산"이 아니라 **워치리스트 단일 원시요소 PRD + 경계 선언**이다(기존 4 PRD scenario-simulator·financial-statement-lab·table-export·ui-platform-refactor 를 claim 하지 않고 monitor 루프로 연결).

---

## 한 줄 결정

**블룸버그를 블룸버그로 만드는 것은 분석 깊이가 아니라 *수평 OS 레이어*(워치리스트·함수문법·워크스페이스·알림·링크·egress)다. dartlab 은 "비싼 절반(수직 분석: FA·GP·CN 을 블룸버그 초과 수준으로)"을 이미 끝냈고, "싼 절반(수평 OS 직조)"을 통째로 비워뒀다.** 따라서 "블룸버그식"이 되는 길은 차트·재무를 더 파는 게 아니라 — 이미 가진 분석들을 **① 워치리스트(우리에겐 *공시 워치*) ② 커맨드바 섹션 점프(약화 함수문법)**로 묶어 *모니터 루프*를 닫는 것이고, 컨센서스·실시간이라는 두 빈칸은 각각 **reverseDCF 읽기**(fin-stmt-lab 소유)와 **EOD-공시-델타**로 *정공법 대체*한다. 절제선은 Koyfin/TIKR: 풀 mnemonic·멀티모니터 Launchpad·트레이딩 데스크·푸시 알림은 버리고, 큐레이션·섹션점프·정직한 재방문 델타는 가진다.

---

## 핵심 결정 요약 (v0.1)

- **진짜 빠진 것 = 수평 OS 레이어, 수직 분석 아님.** 라이브 /terminal(`ui/packages/surfaces/src/terminal/`)은 이미 GO 커맨드바·3 컬럼 보드·증권사급 차트(지표·백테스트·비교·드로잉·볼륨프로파일)·거대한 재무 forensic(IS/CF/BS·배당·자사주·소유·인력·임원보수·지배구조·공급망·R&D)·매크로 쿼드런트·섹터히트맵·통합 스크리너·공시뷰어를 보유. **수직은 손대지 않는다.** → [00-product-vision.md](00-product-vision.md), [01-bloomberg-concept-gap.md](01-bloomberg-concept-gap.md).
- **★이 PRD 의 고유 핵심 = 워치리스트(공시 워치).** 어떤 기존 PRD 도 claim 안 한 단 하나의 미커버 원시요소(코드·PRD grep 0 확인). 사용자 큐레이션 종목 집합 + **기기독립 신선도 배지**(공시 발생일 기준) + **정직 라벨 재방문 델타**(이 기기·마지막 방문 시점 명시). 우리 사용자에겐 *가격 워치가 아니라 공시 워치* — 서버리스·EOD 환경에서 우리만 이길 수 있는 유일한 monitor. → [02-watchlist-disclosure-watch.md](02-watchlist-disclosure-watch.md).
- **함수문법은 *약화*해서만 산다.** 블룸버그식 `005930 FA` mnemonic 백과사전은 리테일 cargo-cult. 정공법 = 기존 GO/suggest 에 **"회사 + 섹션 토큰"**(예: `삼성전자 공급망`, `삼성전자 거버넌스`) 인식 한 겹을 얹어 forensic 뷰로 직행. 별도 함수 디스패처 신설 금지(단 ServicesPort 가 이미 계약·미배선 — 정합 검토). → [03-command-and-architecture.md](03-command-and-architecture.md).
- **알림 = KILL, 재방문 델타 = 정직 한정 생존.** 서버·푸시·계정 0(정적 호스팅 코드 확인)이라 "푸시 알림"은 불가능한 약속. "since-last-visit"도 localStorage 단일이라 *완결성 주장*("다 봤음")은 확신오정렬 위험. → **완결성 주장 금지 + 기기·시점 명시**로만 산다. 이름은 "알림"이 아니라 "재방문 델타 다이제스트". → [02](02-watchlist-disclosure-watch.md) §비목표, [04-killlist-and-non-goals.md](04-killlist-and-non-goals.md).
- **멀티패널 워크스페이스/Launchpad = KILL.** 불가침 구역규칙(좌=네비/중앙=뷰/우=테이블) 정면 파괴 + 리테일 터미널(Koyfin/TIKR)도 안 함 + 전역 `sym`→패널로컬 대공사를 정당화할 실수요 없음 + N 사 비교는 `compare()` verb(fin-stmt-lab)가 이미 소유. → [04](04-killlist-and-non-goals.md).
- **크로스에셋 instrument 타입 = DEFER.** 모든 포트가 `code:string` 키잉, instrument/assetClass 추상 0. 풀 타입체계는 contracts 전반 개정(최대 재발명)이라 별도 깊은 PRD 감. 지수는 scenario-simulator 가 소유. → [03](03-command-and-architecture.md) §경계, [04](04-killlist-and-non-goals.md).
- **경계 — 이 PRD 가 하지 *않는* 것.** JUDGE 분석(reverseDCF·compare 동종백분위) = **financial-statement-lab**. 시뮬레이션·Play·지수·백테스팅·공시 이벤트레일 = **scenario-simulator**. 테이블 egress = **table-export**. 포트 원칙·UI 패키지 경계 = **ui-platform-refactor**. 본 PRD 는 이들을 *연결하는 모니터 루프*만 신설. → [03](03-command-and-architecture.md) §non-encroachment.

---

## 문서 지도

1. [00-product-vision.md](00-product-vision.md) — 비전·사용자 문제·monitor 루프 5 단계(WATCH→SURFACE→DIG→JUDGE→RECORD)·"공시 워치 ≠ 가격 워치"·우리 사용자 정의·왜 지금 ROI 가 비정상적으로 높은가.
2. [01-bloomberg-concept-gap.md](01-bloomberg-concept-gap.md) — 블룸버그식 터미널의 *개념적 원시요소* 카탈로그(중심성 등급·dartlab 보유여부)·"OS 레이어 vs 분석" 분리 가설·현대 리테일(Koyfin/TIKR/Finchat) 절제선.
3. [02-watchlist-disclosure-watch.md](02-watchlist-disclosure-watch.md) — ★핵심 새 원시요소. 워치리스트(공시 워치)·기기독립 신선도·정직 재방문 델타·storage 계약·LeftRail 거처·비목표(알림/푸시/동기화).
4. [03-command-and-architecture.md](03-command-and-architecture.md) — 커맨드바 섹션 점프(약화 함수문법)·아키텍처 거처·포트 실태(services/storage/navigation 계약 실재·미배선·터미널 미소비)·재사용·non-encroachment map·instrument DEFER.
5. [04-killlist-and-non-goals.md](04-killlist-and-non-goals.md) — KILL/DEFER 리스트(근거)·정체성 가드 비목표·데이터/실현가능성 차단·덕지덕지 위험.
6. [05-scope-phasing-guardrails.md](05-scope-phasing-guardrails.md) — Phase 시퀀스·정직 가드·성공기준(차트수·기능수 아님)·착수 게이트.
7. [06-progress-ledger.md](06-progress-ledger.md) — 결정·전문에이전트 토론 기록·문서 상태·NEXT·착수=운영자 go.

---

## 정직 척추 (전 문서 관통)

- **수직 분석은 손대지 않는다.** 이미 초과 수준. 비어 있는 *수평 루프*만 닫는다("강함은 쌓아서 아니라 깎아서").
- **서버 없음을 *정직하게* 노출한다.** 푸시 알림·크로스기기 동기화·협업 워크스페이스는 정적 호스팅에서 *불가능* — 흉내내면 깨진 약속. localStorage 한계(기기종속·시크릿모드 0)를 UI 에서 명시.
- **완결성 주장 금지.** "다 봤음"·"신규 없음" 같은 *완결* 진술 금지(상태가 기기로컬이라 거짓일 수 있음). "이 기기 · 마지막 방문 06-12 이후"처럼 *측정 시점*만 진술.
- **컨센서스·목표주가 흉내 금지.** reverseDCF 는 "가격이 요구하는 것의 읽기"지 "적정주가 X 원"이 아니다(fin-stmt-lab 가드레일 계승).
- **claim 하지 않는다.** 기존 4 PRD 가 소유한 것을 재발명·재배선·재명명하지 않는다. 충돌 시 기존 PRD 가 정본.
- **코딩 아님.** 본 PRD 는 *방향* 확정 문서다. 착수는 mainPlan(터미널 ui/packages 정착) 완료 + 운영자 go 후.
