# 정기보고서 도시에 (Periodic-Report Dossier) — PRD

> **무게중심**: 비(非)재무 사업보고서 실체 — dartlab 이 *이미 네 번이나* fetch 하면서도 얕게·출처 없이 흘려보내는 사람·자본배분·소유 팩트 — 를 **하나의 날짜 박힌, 출처추적되는, 자기이력 프레임의 도시에(dossier)** 로 묶는다. 그 결과 **패널 수는 오히려 줄고**(−1) 가독성·정직성은 올라간다.
>
> **한 줄 비전**: 한국 기업의 사업보고서를 *하나의 날짜 박힌 클릭 가능한 문서*로 읽는다 — 누가 일하는지, 주주가 실제로 무엇을 받는지(소각 vs 금고), 자본이 어디로 흘렀고 누가 지배하는지 — 모든 숫자는 그 DART 공시로 역추적되고, 자기이력 + 유니버스 순위로 프레임되며, *결코 판정으로 환산되지 않는다*.

---

## 이 PRD 가 푸는 문제

사용자 명령(원문): "정기보고서 팩트부터 그아래 인력, 생산성 등 주주환원까지 타법인 출자 위까지 더 강화 … 우리는 강력한 정보들이 있다 그걸 다 못쓰고 있다."

진단(실측): 정기보고서 28개 구조화 API 중 14개만 차트화. 노출된 것조차 **얕다** — 직원=급여 상위3명, 배당=수익률만, 자사주=취득/처분 raw(소각 `buybackCancel` 은 fetch 후 버림). 같은 parquet 가 `DART 정기보고서 팩트` 평면 패널 + `주주환원`/`인력`/`타법인출자` 패널 + FinFullscreen 탭 + HoldingsDialog 로 **중복 표면화**되면서도 **출처(`rcept_no`)·자기이력·정직 라벨** 이 없다.

해법: 새 카드·새 레일을 더하지 않는다. **이미 메모리에 fetch 된 배열을 의미화**하고, 평면 중복 패널을 **출처 박힌 도시에 헤더 리본**으로 접고, 갇힌 계산(소각비율·lossPct·control-shift·인적자본 효율)을 **한 클릭 앞·판정 없는 한 문장**으로 당긴다.

---

## 작업 산출 (8문서)

| 파일 | 내용 |
|---|---|
| [00-product-prd.md](00-product-prd.md) | 비전·문제·무게중심·차별화·NEVER-CLAIM (제품 정본) |
| [01-current-state-audit.md](01-current-state-audit.md) | 가진 것 vs 표면화한 것의 갭 (실측 file:line) |
| [02-killer-features-and-debate.md](02-killer-features-and-debate.md) | 7개 기능 + 섹션별 전문가 토론·적대검증 평결 |
| [03-information-architecture-and-ux.md](03-information-architecture-and-ux.md) | 분산+스파인 IA · 의미층(올라가면/내려가면) · 목업 · 재사용 지도 |
| [04-data-readiness-and-killlist.md](04-data-readiness-and-killlist.md) | 데이터 준비도 4분류 · NEVER-CLAIM · 컷 목록 |
| [05-scope-phasing-guardrails.md](05-scope-phasing-guardrails.md) | Phase 0~3 · 경계(다른 PRD 소유권) · 게이트 |
| [06-progress-ledger.md](06-progress-ledger.md) | 진행 원장 + 재개 NEXT 포인터 |

---

## 한눈 결정 (TL;DR)

- **IA**: 분산(distributed) + 스파인(spined). 통합 "기업 실체" 6번째 레일 = **기각**(덕지덕지·중복 fetch·FinFullscreen 와 경쟁). 기존 우측 패널들을 *도시에 섹션* 으로, 평면 팩트 패널을 *날짜 리본* 으로.
- **간판 기능 3 (전부 새 fetch 0)**: ① `rcept_no` 도시에 스파인 + as-of 리본 ② 환원 흐름(소각 vs 금고) 주주환원 리프레임 ③ 타법인출자 lossPct + control-shift 한 줄.
- **엔진 배선 2 (Phase 2, CI bake)**: 인적자본 유니버스 백분위(죽은 엔진함수 배선) · R&D 집약도 행(`calcRndExpense` 는 *이미 완성 엔진*).
- **정직 컷**: 세그먼트 카드(4.6%만 clean)·가동률 숫자(데이터 0)·시총분모 총주주환원율(거짓정밀)·모든 종합점수/레이더 = **금지**.
- **순 패널 변화 = −1**. 강함은 더하기가 아니라 *갇힌 계산의 정직한 표면화*.
- **착수** = 운영자 go. **UI push = 운영자 명시 승인**(공개 터미널 화면 작업, CLAUDE.md ⛔).

---

## 출처

전문에이전트 13인 2라운드 토론(도메인 5 + 적대검증 5 + UI/UX 2 + 종합 리드, `wf_c20526bc-bed`, 2026-06-19) + 이번 세션 실측 인벤토리(터미널 surface · 데이터 엔진 · 경계 PRD). 토론 정본은 본 문서들에 박제.
