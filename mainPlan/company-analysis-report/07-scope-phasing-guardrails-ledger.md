# 07 · 범위·Phase·경계·롤백·이중평가 + 진행 원장

## 1. Phase 분할

| Phase | 산출 | 화면? | push |
|---|---|---|---|
| **P0** spike + 직렬화 + 품질 | ①`tests/_attempts/storyReportBake/` 30~50사 spike(nonEmptySectionCount/refCount/핵심막 분포 + 관점별 nonEmpty emphasize 충족률→`publishablePerspectives` + breakeven/operatingLeverage coverage + sixAct evidenceFrame 채움율 + **섹션→대표 rcept_no coverage**(간판5) + payload 크기 + macro offline 경로 → reject-gate N/M/K 확정) ②신규 `bakeStoryReport(company)->dict`(**catalog `SectionMeta.act` 사용**·sourceEngine·emphasized·representativeRceptNo·meta·evidenceFrame=sixActScore.asDict() 직접호출·**score→_internalScore 분리**·calcValuationSins/calcPlausibilityBand 조립) + `catalog.BlockMeta.sourceEngine` 정적 필드 ③`reportQuality.py`(reject-gate·7축·claimGuard tests/audit 신규·G1 red테스트·acceptance 페르소나 하니스) | ✗ 엔진 | 자동 가능 |
| **P1** bake CI | `storyReportBake.yml`(valuationSnapshot 동형·macro cached경로·증분·Tier SLA)·featured+워치 우선→전체 weekly. `dataConfig` storyReport 1줄 + `loadStoryReport` + `checkUiDataWiring` 가드 | ✗ bake | 자동 가능 |
| **P2** UI 렌더 | `ReportDialog.svelte` + 보고서 버튼 + 관점 탭 + `buildReportView` 투영 + SummaryCard + **EvidenceStrip(점수 비노출·coverage+evidenceIds)** + 블록 렌더(sourceEngine 배지·KPI델타·severity·ChartRenderer) + **핵심 5막 섹션 헤더→공시뷰어 딥링크**(간판5: `ViewerOverlay` rcept 타깃 prop 신설[현재 code/vs만] + 본문 스크롤. 외부 DART floor 링크는 즉시·인앱 딥링크는 prop 후). publishable 미충족 dim+정직라벨 | ✓ 화면 | **운영자 승인** |
| **P3** polish | `@media print`+`window.print` PDF(차트 스냅·@page footer)·정직스킵 배너·차별 매트릭스·quality 정직라벨(점수 비노출). 전용 라우트(공유링크) | ✓ 화면 | **운영자 승인** |
| **P4** 천장 올리기 | `블록→rcept_no` 풀 회로(builders 100+블록 출처 운반)·nonEmpty 미달 emphasize 블록 calc* 보강 후 해당 관점 활성·governance dossier 소비링크 슬롯 | 혼합 | 별 트랙 |

## 2. 형제 PRD 경계 (침범 금지 — 적대검증 핵심)

| 형제 PRD | 보고서의 선 |
|---|---|
| **카테고리** | `mainPlan/company-analysis-report/` **단일 SSOT**. 신규 terminal-report-egress 등 만들지 않음(두 SSOT 금지). |
| **periodic-report-dossier** | 비재무 팩트(인력/자본배분/소유)·분산스파인 IA = dossier 소유. 보고서는 **소비/링크만**. ★`costBreakdown` SSOT **확정(H6)**: 비율 블록(매출원가율·판관비율·DOL) = story/analysis 소유·보고서 렌더, *비용 성격별 raw 명세*(주석 행) = dossier 소유·**링크만**(동일 숫자 이중경로 금지). governance emphasize(executivePayDivergence 등) = dossier 생성 팩트 → story 재계산 시 경계 위반 → **링크 소비 확정**. |
| **table-export** | 표→.xlsx egress·뷰어 한정·미착수 PRD. 보고서 PDF = 별 artifact, `ExportPort` **개념만** 차용(코드 의존 금지). PDF = window.print 독립. **xlsx 다운로드 버튼 금지**. |
| **financial-statement-lab** | JUDGE(동종백분위/reverseDCF/forensic) = L2. **인용/링크만**, 재계산 fork 금지. 유니버스분위·DCF·forensic 자체계산 금지. ★fin-stmt-lab 은 **미착수 PRD** → valuation 관점 DCF/백분위 닻이 *존재하는 surface 링크*면 링크, **미착수면 죽은 링크 금지 → "JUDGE 미배포 — 가치평가 닻 보류" honest-skip 라벨**. 현재값(PER/PBR)은 인라인 가능(panel 보유). |
| **scenario-simulator** | 미래 리플레이/what-if. 보고서 예측 = 결정론 회귀 + plausibilityBand("추정"). 궤적/what-if = **시뮬 링크**(미착수 PRD 코드 의존 금지). |
| **editorial-card-news** | SNS 카드 = 다른 surface. **Hook Engine 정직게이트 철학만 공유**(reject→7축→pick), story 소스(detectThreads/narrate._classify) 공유 정당. |
| **terminal-improvement** | 수평직조(워치/커맨드바). "since-last-visit 델타" = 워치 소유, 보고서 금지. 공시변화 섹션 = filing-period 자기이력만. |

## 3. 4계층 경계

story = L3, 분석엔진 = L2. 보고서 UI 는 story(L3) 출력만 소비, **L2 직접호출 위반**. bake 가 `sixActScore`/`calcValuationSins`/`calcPlausibilityBand` 를 호출하는 것은 이들이 company facade 를 안전 조회하는 story-내부 패턴이므로 정합(L3 bake 가 L3 자산 호출). UI 는 origins 단일 진입(`loadHfJson`).

## 4. 롤백

- **엔진**: `bakeStoryReport`/`reportQuality.py` = 신규 모듈 → 삭제로 원복. `buildStory`/`renderJson` 시그니처 불변(renderJson 은 dict 확장이라 기존 5키 보존, 기존 소비자 무영향). `catalog.BlockMeta.sourceEngine` = 필드 추가(기본값 빈 문자열 → 기존 무영향). sixAct.py 무변경.
- **CI**: `storyReportBake.yml` = 격리 워크플로 → 실패 시 이전 HF 본 유지·dataPrebuild 무영향, disable 로 원복.
- **클라**: `dataConfig` 1줄·`loadStoryReport`·`companyReport.ts`·`ReportDialog`·`EvidenceStrip` = 신규 → 버튼 1줄 + 다이얼로그 제거로 원복, 기존 패널 무변경. `@media print` = `.rptDoc` 스코프(다른 화면 인쇄 무영향).
- **honest-skip**: `_skipped.json` 미생성 = 404 = 기존과 동일 무해. `publishablePerspectives` 빈 집합 = 전 관점 dim = 미발행 = 기존과 동일.
- **UI push**: 운영자 승인 게이트 → 시각 회귀 시 미push 상태로 롤백.

## 5. 이중평가

- **전문 개발자**: 아키텍처 수렴 정확(payload 1벌 bake + 정적 클라투영 + window.print = 정공법, 12배폭발/jspdf 한글깨짐 회피). ★2라운드 코드 재검증 정정 완료 — 1차(F1~F4: bake sixActScore 직접호출·EvidenceStrip 신규·점수 비노출·sourceEngine 정적 catalog 필드) + 2차(H1~H7: F1 재정정=catalog `SectionMeta.act` 사용[partId.split 버그 폐기]·payload 실데이터·blockKey manifest 기존자산 재계상·관점 11 통일·asDict score 분리·costBreakdown SSOT 확정·간판5 딥링크). 리스크 = P0 spike 가 모든 정량의 선결(임계·발행가능 관점·payload 크기·rcept coverage 전부 spike 산출). 신규 LoC 정직 계상(per-company 직렬화·EvidenceStrip·reportQuality·claimGuard·딥링크 배선) — 단 catalog act/keys 는 기존 자산이라 신규작업 *감소*.
- **PM**: 90점 = 근거완전성(22)이 무게중심인데 1차 천장을 0 이 아닌 부분 실재회로(evidenceIds + sourceEngine) 위에서 정직 비례로 올림 — 사상과 정합. 발행가능 관점 수 = spike 확정으로 "12 양산" 적대지점 선제 차단. ROI 높음(story = 묻어둔 자산, UI 배선만으로 "못 쓰던 정보" 화면화). 차별 = 모든 단정 측정값+분위+출처 + 관점 명시 + 정직 한계 = 일반 AI 리포트가 깎이는 지점 선제 차단.

## 6. 진행 원장

| 날짜 | 상태 |
|---|---|
| 2026-06-19 | PRD 1차 작성. 14인 워크플로(`wf_5da6bc28-697`, 설계5+비평5+종합+심판2R, 88/83) + **코드 직접 재검증으로 4 FATAL 정정** + 8문서 실작성(C-2 표·payload 스키마·의사코드·spike 절차·sourceEngine 메커니즘). |
| 2026-06-19 | **2차 적대검증**(작성 문서 대상 3인 독립: PRD 84·보고서 88·코드 9/10) → 7건 추가 정정(02 §6 H1~H7): F1 재정정(catalog `SectionMeta.act` 사용, partId.split 버그 폐기) · payload partId 실데이터 교정 · blockKey manifest 기존자산 정직 재계상 · 관점 수 11 통일 · asDict score 분리 · costBreakdown SSOT 확정 · **간판5 섹션→공시뷰어 딥링크 신설**(보고서 90 레버). |
| 2026-06-19 | **2차-2 재채점**(동일 심판 재검증, PRD 92·보고서 89) → 마무리 2건(02 §6 H8~H9): 04 §2 매핑표 `partId.split` 잔재 교정 · 간판5 "배선만" 과장 정직 재계상(ViewerOverlay rcept prop 신설=신규배선·valuation 닻 honest-skip). 착수 = 운영자 go 대기. |

**재개 NEXT**: 운영자 go → **P0 ① spike**(`tests/_attempts/storyReportBake/` 30~50사 bake, 03문서 §6 측정표대로 → reject-gate N/M/K + publishablePerspectives + 섹션→대표 rcept_no coverage 확정). spike 전 어떤 정량도 박지 말 것. costBreakdown SSOT = 확정됨(04 H6, story 비율 블록 / dossier raw 명세 링크).
