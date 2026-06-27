# 사업보고서 전 섹션 수확 (Report Full-Harvest) — PRD

> **한 줄 비전**: 한국 기업 사업보고서의 *모든 쓸 수 있는 표*를 — 재무제표 아래 **한 패널의 적층 글랜스**와 **이미 있는 한 다이얼로그**로 — 패널을 늘리지 않고(오히려 줄이고) 흘려보낸다. 새 빌드 없이 *이미 가진 것을 의미화*하는 게 8할.
>
> **무게중심(이번 PRD의 새 발견)**: 토론 7에이전트가 코드를 실측한 결과 — 가치의 대부분은 *신규 추출이 아니라 surface*다. ① Tier B 17종은 `reportSource.ts`에 **이미 전부 런타임 직독 배선**됨(surface 결정만 남음). ② `xbrlCellsFromContent`는 acode 범용 리더라 리스·차입금·충당부채·관계기업·매출채권·재고 주석을 **cost/segment와 동일 무빌드 경로**로 회사별 직독 가능(코드에 `notesDispatch` 레지스트리 일부 이미 존재). ③ 수주는 사업보고서 narrative *수주잔고(stock, fragile 5/10)*가 아니라 수시공시 *신규수주 flow(orderFlowScan, 810사 ≥90% 파싱)*가 신뢰선 → book-to-bill로 대체.

---

## 이 PRD가 푸는 문제

운영자 지시(원문): "수주잔고 등 쓸 수 있는 보고서가 많은데 그것만 얘기하나. panel 분석해서 사업보고서 내용 활용방안을 전부 기획하라. 인력·생산성·주주환원·주석을 재무제표 표 바로 아래 한 패널로 묶고, 상세보기는 한곳(다이얼로그)에 배치하는 방법을 토론해 기획하라."

기존 [[periodic-report-dossier]] PRD가 *비재무 팩트(사람·자본·소유)*를 다뤘다. 본 PRD는 그 **상위집합** — ① 사업보고서 전 섹션 인벤토리(spine taxonomy 실측) ② Tier A 재무주석 XBRL 골드마인(회사당 179~507표) ③ 수주 flow vs stock 결정 ④ 운영자가 새로 지시한 **재무제표 아래 통합 패널 + 단일 상세 home** UX를 한 묶음으로 기획한다.

---

## 인벤토리 3계층 (panel parquet 실측 — `01-section-inventory.md`)

| Tier | 정체 | 추출 현실 | 예 |
|---|---|---|---|
| **A — 재무주석 XBRL** | 회사당 179~507개 note 표가 정부 ACODE 태그(언어무관 acode + 기간/축 ACONTEXT) | 표 레이아웃 파싱 0으로 **런타임 직독**(회사별). 시장 전체 횡단만 scan 빌드(승인) | 비용성격별·부문매출(구현됨)·리스부채·차입금명세·충당부채·관계기업·매출채권·재고·법인세 |
| **B — 이미 추출(keyed scan/report 17종)** | 정형 API → parquet, 전 universe 격자 | **이미 전부 `reportSource.ts` 런타임 직독 배선** + 횡단 scan 보유 | 인력·배당·자사주·타법인출자·주주·임원보수·감사·사채/CP·자금조달·이사회 |
| **C — II.사업의 내용 자유서식** | XBRL 태그 0, 업종마다 레이아웃 상이 | 휴리스틱·노이즈. 품질 _attempts 입증 후 승인 | 제품·원재료·생산설비·**수주잔고**·R&D·주요계약·위험관리 |

---

## 한눈 결정 (TL;DR)

- **IA = 패널 −3, 다이얼로그 +0**: 재무제표 표 *바로 아래* 단일 **「사업보고서 한눈」** 패널로 WORKFORCE·SHAREHOLDER·NOTES 3패널을 **적층 블록**으로 흡수(탭 아님). HOLDINGS는 표 밀도가 높아 별도 유지. 깊이는 **기존** FinFullscreen PEOPLE/RETURN 탭 + NotesDashboardDialog로만 — **새 패널·새 다이얼로그 0**.
- **적층(stacked) > 탭** (UX 3렌즈 만장일치): 탭은 클릭마다 다른 블록을 숨겨 계기판 스캔성을 죽인다. 적층 + 데이터 없으면 통째 숨김 = 길이 자동관리. 빈약한 회사는 2블록으로 짧고 풍부한 회사만 길어짐.
- **간판 = 새 추출 0의 의미화**: 인당생산성(매출÷인원), 총주주환원(배당+자사주, **OCF 분모**), 비용 고정비비중, 부문 매출믹스 — 전부 이미 메모리에 있는 시리즈의 순수 재집계.
- **Tier A 확장 = 무빌드 acode 필터**(P1): 리스부채·차입금명세·충당부채·관계기업·매출채권(DSO)·재고(DIO) — 우측 글랜스엔 안 올리고 **NotesDashboardDialog 안 섹션**으로만.
- **수주 = flow(book-to-bill)**, stock-backlog는 컷. flow scan('orders') 졸업은 **승인 게이트**(P2).
- **컷 확정**(`03` §컷): 수주잔고 narrative, 가동률(data 0), 종합점수/등급/레이더, 시총분모 총주주환원율, 원재료 매입처 자유서식, 주요계약 narrative, 부문×지표 다축 합성, 금융위험 민감도 횡단비교.

---

## 페이징 (상세 `03-phasing-guardrails.md`)

| Phase | 게이트 | 내용 |
|---|---|---|
| **P0** | 런타임·무빌드·무승인 | 통합 패널(적층 3블록) + 단일 상세 home 배선. 이미-live 시리즈의 의미화(인당생산성·총주주환원·고정비비중·부문믹스·부채만기). **우측 4패널→1패널.** |
| **P1** | 런타임 XBRL acode 필터(회사별·무빌드) | Tier A 주석 확장(리스·차입금·충당부채·관계기업·매출채권·재고) → NotesDashboardDialog 섹션. R&D집약도(태깅 회사만). |
| **P2** | **빌드 = 사전 토론·승인 게이트** | 수주 flow scan('orders') 졸업(orderFlowScan _attempts → value-sanity 가드·reconcile → scan 빌드). Tier A 주석 시장 횡단 scan(리스/차입금 분위). |

---

## 작업 산출 (문서)

| 파일 | 내용 |
|---|---|
| [00-product-prd.md](00-product-prd.md) | 비전·문제·무게중심·차별화·NEVER-CLAIM |
| [01-section-inventory.md](01-section-inventory.md) | spine taxonomy 전수 → Tier A/B/C 매핑 + 추출 현실(실측) |
| [02-debate-domain-uiux.md](02-debate-domain-uiux.md) | 7에이전트 토론 정수 — 도메인 4렌즈 picks·컷 + UX 3렌즈 통합·다이얼로그 설계 |
| [03-phasing-guardrails.md](03-phasing-guardrails.md) | P0~P2 + 승인 게이트 + 컷 리스트 + 통합 패널 설계 스펙 |
| [04-progress-ledger.md](04-progress-ledger.md) | 진행 원장 + 재개 NEXT |

> **합성 출처 정직**: 토론 워크플로(`wf_138893c3`, 8에이전트·750k 토큰)의 도메인 4 + UX 3 렌즈는 코드를 실측해 풍부한 결과를 냈으나, 8번째 합성 에이전트는 placeholder를 반환(스키마 실패). 그래서 **최종 합성·페이징은 본 저자(메인)가 7렌즈 raw에서 직접** 수행했다. 점수 인플레·미빌드 가치 과장 0.

---

## NEVER-CLAIM (불변)

종합점수·자본배분 등급·주주친화도·인적효율 등급·레이더 환산 **일절 금지**. 모든 숫자는 그 공시(`rcept_no`) 역추적 + self-vs-self 추세 라벨 + 정성 라벨만. [[periodic-report-dossier]] 결정 계승.
