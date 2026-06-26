# 01 · 현상태 감사 — 두 시스템 + 능력 원장

> 출처: 매핑 에이전트 3종(랜딩 문법·Python story·소비 그래프) + 능력 검증가 + 밸류에이션 직독. 코드 증거 기반.

## 1. 두 개의 "리포트"가 따로 산다

| | Python `story` 엔진 | 랜딩 `/report` (TS) |
|---|---|---|
| 위치 | `src/dartlab/story/` (~130 파일, L3 조합기) | `landing/src/lib/report/` (독립 TS) |
| 개념 | "6막 인과" + 13섹션 catalog + sixAct 레이더 + 11 reportType×7 template | **5관점**(수익성·재무안정성·주주환원·시장평가·지배구조) |
| 런타임 | CLI·blog(死)·AI 추천만 | ssr=false, 브라우저가 HF parquet 직독, 베이크 0 |
| thesis | summaryCard(grades) | **정규식으로 긁은 기계 문장** (`build.ts` OverviewModel.thesis) |
| 상태 | 군더더기 ~1,250 LOC, 라이브 미소비 | 검증됨(`project_company_analysis_report` _done)이나 *측정 요약*이지 전문 리포트 아님 |

**핵심**: 랜딩 /report 는 Python story 를 **1바이트도 안 쓴다**. 완전 독립. 옛 baked story JSON 은 이미 폐기("정적 story JSON 폐기, 사전 bake 없음").

## 2. story 군더더기 — 폐기 목록 (P2, 03 아키텍처 에이전트 코드검증 정정)

**진짜 死코드 (삭제 ~2,834 LOC):**

| 모듈 | LOC | 증거 | 처리 |
|---|---|---|---|
| `story/macro/` 서브트리(`macroReport` 등) | 1,823 | importer 0 | 삭제 |
| `publisher.py`(blog markdown) | 327 | 호출처 0, blog 는 `<CompanyFinancials>` SSOT 이주(`0f6a6f2f7`) | 삭제 |
| `sixAct.py` 6축 레이더 | 268 | story 미배선, landing 차트 script 만. macro 축 `return None` 스텁 | 삭제 |
| `dashboard.py` | 121 | 미인스턴스화 | 삭제 |
| `sections/`(빈) | 1 | — | 삭제 |

**死코드 아님 — 라이브지만 갈아엎기로 *대체*(삭제 아님):**

| 모듈 | LOC | 사실 정정 |
|---|---|---|
| `reportTypes.py` · `templates.py` | 334·791 | `registry.py:15,1550,1571,1610,1630` 가 *실제 import* — buildStory 의 라이브 의존. 군더더기 아님. 새 emitter `buildReportModel` 이 buildStory 를 대체하며 함께 은퇴 |
| "6막 인과" framing(`catalog.py` act 필드) | — | 표시용. 5관점→아크 emitter 로 대체 |
| MCP `companyStory` | — | 0.10 에서 이미 제거(확인만) |

소비자 중 살아있는 것: CLI `dartlab story`(메서드 유지 + `dartlab report` 추가), 테스트 ~277(대부분 무변·`test_r31.py` ~3 함수만), AI `storyTemplate.py`(섹션키 literal list — 엔진 import 0, 결합 없음). → **갈아엎기 near-zero breakage.**

## 3. 능력 원장 — 아마추어 실측 (P1 격상 대상)

검증가가 코드 직독으로 실측. 🟢 라이브 강함 / 🟡 존재하나 아마추어·미배선 / 🔴 미보유.

| 능력 | 판정 | SSOT(찾을 곳) | 아마추어 격차 |
|---|---|---|---|
| 수익성·마진브리지·현금전환·CCC·자본배분 | 🟢 라이브 | `landing/.../build.ts` + analysis | 그대로 아크에 |
| Peer 백분위·지배구조·이익품질 | 🟢 라이브 | build.ts + industry | 그대로 |
| **밸류에이션(DCF)** | 🟡 | `analysis/valuation/` | **아래 §4 — 4대 결함** |
| **포워드 전망** | 🟡 | analysis forecast + `story/builders/forecast.py` | 과거 CAGR 외삽. 백테스트 없음 |
| **세그먼트 경제성** | 🟡 | revenue segment 추출(axisPath) | 매출만, 마진은 공시 의존(도출 미구현) |
| **신용 dCR 20등급 + forward PD** | 🟡 | `credit/` (79사 검증) | 엔진은 강한데 **라이브 미배선** — 최고 ROI |
| **per-company 매크로 민감도** | 🟡→🔴 | `macroExposure.py` | n≈3-5 얕음, 자동 차단 빈번 |
| **경쟁/해자(정량 moat)** | 🔴 | (탐색 필요 — ROIC지속성·마진안정성 시계열) | 정성 엔진 부재. 정량 moat 빌드 가능성 = D 조사 |

## 4. 밸류에이션 엔진 4대 결함 (코드 증거)

`src/dartlab/analysis/valuation/dcf.py` + `_dcfHelpers.py` 직독:

1. **성장률 = 매출 3Y CAGR clamp [-5%,15%]** (`dcf.py:455-460`) — 과거를 미래로 베끼는 순진한 외삽. 15% clamp 임의값.
2. **WACC = 섹터 디폴트 한 숫자** (`dcf.py:429`, `sectorParams.discountRate`) — DCF 최대 레버를 뭉갬. 회사별 아님.
3. **성장에 재투자 안 묶임** (`dcf.py:194-197` marginPath 받고 `pass`) — 재투자 0 으로 FCF 를 키워 *무에서 가치 창조*. Damodaran 1번 규칙(g=재투자율×ROIC) 위반 → 성장주 구조적 과대평가.
4. **Terminal fade 없음** (`dcf.py:465`) — 초과수익(ROIC>WACC) 영원 가정. 경쟁 수렴 fade 누락 → 영구가치 과대. verdict 는 0.8/1.2 밴드 + 3모델 단순평균(`dcf.py:586-615`).

→ "정직하게 스킵"이 아니라 **모델이 틀렸다.** 격상 = §02·A.

## 5. 깨면 안 되는 것 (이미 강함 — 회귀 금지)

정직 스킵 렌더(빈칸 시각화)·이상치 clip-mark·독립 verdict(합성점수 없음)·sparkline 표·A4 라이트/다크·⌘K 검색·관점탭·provenance strip·인쇄·모바일 엣지투엣지·단일 data-fetch SSOT(`dataCore.requestParquetRows`)·MiniFinChart 차트 SSOT. **이건 능력이지 결함이 아님 — 아크/문법에 흡수.**
