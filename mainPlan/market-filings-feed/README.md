# 시장 공시 피드 (Market Filings Feed) — PRD

> **무게중심**: 우측 공시는 *한 회사*(선택 종목 전이력)다. 새 좌측 피드는 **전상장사 2,659종목의 최근 3개월 수시공시를 rcept_dt 시간순으로** 흘려보내며 주가영향 카테고리(지분·내부자 / 자기주식 / 증자·사채 / 최대주주·경영권 / 실적·계약)로 거른다 — **"지금 시장에서 주가 움직일 일이 어디서 터졌나"**.
>
> **한 줄 비전**: 좌측 패널에서 한국 시장 전체의 수시공시를 한 흐름으로 읽는다 — 누가 5%를 넘겼고(세력), 자사주를 사고, 증자로 희석하고, 최대주주가 바뀌고, 잠정실적·공급계약이 터졌는지. 모든 행은 회사명 1순위·클릭=회사 점프·↗=DART 원문, *결코 호재/악재로 판정하지 않는다*.

---

## 이 PRD가 푸는 문제

운영자 명령(원문): *"우측 공시는 기업 한 개 개념인데, 좌측 패널 산업쪽 높이 조금 줄이고 그 아래에 공시 최근 3개월꺼 리스트업. 이건 전체상장사고 카테고리별 탭을 세부적으로 — 특히 자기거래·내부자거래·연금·기관·주주변경 등 주가영향 공시."*

진단(실측): dartlab은 전상장사 수시공시를 `dart/allFilings/recent.parquet`(210,963행)으로 **이미 갖고 있으나**, 우측 패널이 *단일기업*으로만 소비한다. 시장 전체를 시간순으로 보는 표면이 없다. 그리고 기존 `classifyFiling`은 임원소유와 5% 대량보유를 한 `equity` 바구니에, 자기주식을 major에, 최대주주·공급계약·실적을 exchange에 **뭉개** 주가영향 신호를 가린다.

해법: 새 수집 0. **이미 빌드되는 parquet에서 rcept_dt 정렬 슬림 파일을 CI bake**(빌드 편승)하고, 좌측에 시간순 피드 + 주가영향 6탭 + 기관 보조칩(범위 라벨)을 신설한다.

---

## 작업 산출 (4문서)

| 파일 | 내용 |
|---|---|
| [00-product-prd.md](00-product-prd.md) | 제품 정본 — 무게중심·데이터층 결정(옵션B)·6탭·IA경계·UI/UX·killList·Phase 0~4·영향파일/테스트/롤백·열린결정 |
| [01-current-state-audit.md](01-current-state-audit.md) | 현 상태 실측 — 데이터 정렬 제약(stock_code→날짜pruning 불가)·카테고리 분포·연금기관 식별 9.5%·UI 구조·재사용 자산 |
| [02-debate-and-verification.md](02-debate-and-verification.md) | 전문에이전트 토론 정본 — 5 설계 + 4 적대검증 must-fix + 종합 수렴 표 (`wf_9f54e359-0c8`) |
| [03-progress-ledger.md](03-progress-ledger.md) | 진행 원장 + 재개 NEXT 포인터 |

---

## 한눈 결정 (TL;DR)

- **데이터층 = 옵션 B**(CI bake `market_recent.parquet`, rcept_dt desc·3개월·656KB → 브라우저 단일 whole-file GET). govRecent 1:1 선례·새 추상 0. 옵션A(1.89MB 전체읽기)는 stock_code 정렬이라 날짜순 자체가 안 나옴(11 rg 전부 dt 동일).
- **카테고리 = 6탭 + 보조칩**: 전체 / 지분·내부자 / 자기주식 / 증자·사채 / 최대주주·경영권 / 실적·계약. 12탭 kill(과세분화). 사용자 5요구 전부 수용.
- **연금/기관 = 독립탭 kill**: report_nm '연금' 0건·flr_nm 식별 **9.5%**·개인 오너 혼재. '지분·내부자' 탭 내 보조 [기관] 칩 + '제출자=기관(부분식별·약10%)' 범위 라벨로만.
- **IA = 멘탈모델 3분리**: 시장전체(새 피드) / 워치종목(기존 WATCH 탭) / 선택회사(우측 단일기업). 코드 read경로·정렬키·범위 전부 달라 중복 0.
- **레이아웃**: 산업 스윕 swNote/swMore 축약(~24px·ScatterMap 불변) + 그 아래 eMarketFeed 고정높이 섹션. **fillCol 2분점 금지**(eQuant 단독 유지).
- **제외 컷**: 호재/악재·종합점수·buy/sell 금지 · top-N 침묵 절단 금지(200cap+카운트 라벨) · content_raw 없으니 본문영향 추정 금지 · category 빌드 bake 금지(클라 분류, SSOT drift 회피).
- **순 패널 +1** · 새 cron 0 · 새 fetch 최소(빌드 편승 파일 1개).
- **착수 = 운영자 go · UI push = 운영자 명시 승인**(공개 터미널 화면, CLAUDE.md ⛔).

---

## ★ 직전 PRD 교훈 적용

직전 정기보고서 PRD 맹점("데이터경로·로드상태 추적 없이 주장")을 차단하기 위해 **데이터층을 토론 1순위로 박고 모든 feasibility를 코드 실측에 대조**했다. 종합이 *스스로* 자기 주장을 두 번 정정 — 옵션A 기각의 'falldown 메커니즘' 오류, worker.js `endsWith('recent.parquet')` 파일명 함정(`marketRecent.parquet`은 false). 설계 초안의 "0.3MB·한 줄·falldown" 낙관치는 전부 656KB·~15줄·실측 근거로 교체됐다.

## 출처

전문에이전트 10인(5 도메인 설계 + 4 적대검증 + 종합 리드, `wf_9f54e359-0c8`, 2026-06-19, 1.13M 토큰) + 세션 코드 실측(recent.parquet pyarrow 측정 · worker.js · classifyFiling · build() · govPriceSource · request.ts · hfRange.ts). 토론 정본은 02에 박제.
