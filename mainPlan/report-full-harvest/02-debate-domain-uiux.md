# 02 — 7에이전트 토론 정수 (도메인 4 + UX 3)

> 워크플로 `wf_138893c3` (8에이전트·750k 토큰·85 tool use). 에이전트들이 코드를 실측(notesDispatch·scanBonds·reportSource·segmentRnd/orderFlowScan _attempts)해 도출. 합성 에이전트(8번째)는 placeholder 반환 실패 → 본 정수·페이징은 메인 저자가 7렌즈 raw에서 직접 합성.

## 4렌즈 교차 합의 (강한 신호)
1. **가치의 8할은 surface, 2할이 추출**. Tier B 17종은 `reportSource.ts`에 *이미 전부 런타임 직독 배선*. noteSeries(비용·부문) live.
2. **`xbrlCellsFromContent`는 범용 acode 리더** → Tier A 주석은 cost/segment와 동일 무빌드 경로. 코드에 `notesDispatch` 레지스트리(borrowings·lease·provisions·affiliates·receivables·inventory) **일부 이미 wired** — 신용 렌즈가 발견.
3. **수주: flow > stock**. narrative 수주잔고 fragile(5/10) → [[project_order_flow_scan]] flow(810사·≥90%·book-to-bill)가 신뢰선.
4. **통합 IA**: 재무표 아래 한 패널 + 기존 다이얼로그 재사용. 새 레일·새 다이얼로그 0.

## 도메인 picks (P0/P1 핵심만)

**가치투자**: 부문매출믹스(P0,live)·비용 고정비비중(P0,live 재집계)·총주주환원 OCF분모(P0,live)·리스부채 조정레버리지(P1,acode)·CAPEX집약도(P1)·R&D÷매출(P1,태깅회사)·1인당생산성(P1,live). **수주=book-to-bill(P1, flow)**.
**신용·포렌식**(가장 잘 준비됨): 차입금 단기상환커버리지(P0,wired)·사채단기비중(P0,scanBonds)·리스 off-BS레버리지(P0,wired)·충당부채 추이(P1,wired)·감사의견/KAM(P1,scan)·관계기업 지분법손실(P1,wired)·매출채권 DSO(P2)·재고 DIO(P2).
**산업·운영**: 수주 flow book-to-bill(P1)·부채만기사다리(P0,debtProfile)·부문매출(P0)·비용체질(P0)·인력 1인당생산성(P0)·주주환원+희석(P0)·종업원급여 적립비율(P2,단일표)·타법인출자(P1).
**계량·횡단**: Tier B는 *이미 전 universe 격자*(employee 160K·dividend 638K·majorHolder 436K rows) → 횡단 분위·이상치 신규빌드 0. Tier A 횡단(차입금 D822400·재무위험 D822380)은 scan 빌드 필요(승인).

## 도메인 만장일치 컷
수주잔고 narrative·가동률(data 0)·종합점수/등급·시총분모 환원율·원재료 매입처 자유서식·주요계약 narrative·부문×지표 다축 합성(fragile)·금융위험 민감도 횡단비교·우발부채 정량화·법인세 단독패널.

## UX 3렌즈 (rail·detail·critic) 합의

- **rail 설계자**: 재무제표 바로 아래 단일 패널, 인력·주주환원·주석(+조건부 출자·수주·R&D). 글랜스=수치·비율바·self 한 줄, 깊은 시계열은 중앙/다이얼로그.
- **detail 설계자**: FinFullscreen(이미 종합·수익성·현금·재무체력·**주주환원**·**인력**·가격 7탭)으로 흡수. ①인력⤢→PEOPLE, ②주주환원⤢→RETURN, ③주석⤢→NotesDashboardDialog(13MB lazy라 별 모달 예외). **새 다이얼로그 신설 금지**. 수주·R&D center-stack 탭 승격은 _attempts 졸업 게이트 후.
- **critic(안티클러터)**: 우측 이미 15+ 패널 과적. Tier A 12종을 각각 패널化 = **전부 컷**(글랜스엔 비용·부문 막대만, 나머지 NotesDashboardDialog로). 자유서식 노이즈를 공개 화면에 = _attempts ≥90% + 클린 회사 조건부만. **적층 3블록 > 탭**(탭은 한눈 죽임·빈 탭 클러터).

**UX verdict(critic)**: "재무 표 바로 아래 '사업보고서 한눈' 단일 패널로 인력·주주환원·주석을 적층 3블록(+수주·R&D 조건부)으로 묶어 우측 3패널→1패널로 줄이고, 깊은 시계열·표·자유서식 raw는 새 다이얼로그 없이 기존 FinFullscreen PEOPLE/RETURN 탭과 NotesDashboardDialog로만 — 패널·다이얼로그 증식 0, 종합점수 0, 노이즈 공개 0."

## 정직한 약점 (honest risks)
- Tier A 무빌드 직독은 **ACONTEXT 양식(2025-03+) 회사·최근분기 한정** — 과거 시계열은 짧다.
- Tier C(수주·R&D 자유서식)는 **데이터벽이 실재** — 시장 횡단은 입증 전 불가, 회사별·클린업종 우선.
- 다축 합성(부문 마진 등)은 인코딩 fragility로 **구조적 천장** — 단일축까지만.
- 통합 패널은 공개 surface = **눈검수 필수**, 운영자 승인 후 push.
