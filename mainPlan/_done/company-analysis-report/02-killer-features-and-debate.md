# 02 · 간판 4기능 + 전문가 토론 + 적대검증 평결

> 14인 워크플로(설계 5 lens + 적대 비평 5 + 종합 리드 + 적대 PRD 심판 2라운드, `wf_5da6bc28-697`). 비평 점수: story-architect 62 · UI 58 · data-bake 72 · honesty 58 · **PM/quality 38(약함)**. 심판 2라운드: prdScore 88 / sampleReportScore 83(미달). 심판이 짚은 **4 FATAL + 3 자기충족 갭**을 코드 재검증으로 정정해 본 PRD 에 박제(§5).

---

## 간판 1 — 단일 reportPayload bake + 발행가능 관점 결정론 클라 투영

**무엇.** story 엔진이 회사당 **1개의 풍부한 payload**(`buildStory(company, type='full', detail=True)` 기반, 전 섹션 full detail)를 HF `dart/storyReport/{code}.json` 에 굽는다. **11 관점은 그 payload 위 정적 config 투영**이다 — `manifest.reportTypes[type]` 의 `sectionOrder`(필터+정렬) · `emphasize`(★ 강조) · `focusQuestions`(상단 칩)는 *이미 baked·배포됨*. 클라가 재fetch 0 으로 관점 전환.

**왜 1배인가.** 관점 차이 = `sectionOrder + emphasize + focusQuestions + detail` **4개 정적 config 뿐**. 블록 *계산*은 type 무관(같은 100+ 블록 풀). 따라서 12배 bake 폭발을 회피하고 payload 1벌로 11 관점 전부 렌더. 선례 = `buildStoryManifest.py` 가 reportTypes 를 이미 굽는다.

**발행가능 관점의 진짜 기준.** ★emphasize 리스트와 registry 배선은 **12 관점 전부 baked**(reportTypes.py 36-248 전 관점 emphasize 채움; registry.py 에 beneishMScore·dividendSustainability·executivePayDivergence·companyCyclePosition 블록 builder 전부 wired). 갭은 "블록이 리스트에 있는가"가 아니라 **"그 블록의 `calc*` 함수가 실제 회사에서 nonEmpty output 을 내는가"** = 단일회사 bake 실행으로만 답함. → `payload.meta.publishablePerspectives` = **P0 spike 가 실측한, emphasize 블록이 nonEmpty 를 낸 관점 집합**. PRD 는 "관점 N개 발행가능"을 박지 않는다(NEVER-CLAIM).

**신규 fetch.** 0. 클라 origin 추가 = `dataConfig` DATA_RELEASES 에 `storyReport` 1줄 + 기존 `loadHfJson` 재사용.

---

## 간판 2 — sixActScore evidenceIds **신규 표면화** (EvidenceStrip)

**무엇.** [`sixAct.py:44`](../../src/dartlab/story/sixAct.py#L44) `SixActScore.evidence: dict[axis, list[evidenceIds]]` 와 `coverage: dict[axis, str]`(ready/missing) 를 bake 가 `sixActScore(company).asDict()` 로 직렬화 → `payload.evidenceFrame`. 보고서 `EvidenceStrip` 이 6축 옆에 evidenceIds(예: `analysis:insights:grades`·`credit:distress`·`industry:position`·`quant:valuation`)를 **칩으로 첫 렌더**한다.

**★F3/F4 정정(코드 실측).** (a) "landing EvidencePanel 이 이미 join → 재사용"은 **거짓**(터미널/landing 에 EvidencePanel 컴포넌트 부재, 01문서 F3). EvidenceStrip 은 **신규 구축**. (b) `SixActScore` 6축 score 는 **종합점수 레이더**(01문서 F4) → NEVER-CLAIM 준수 위해 **점수는 노출하지 않는다.** EvidenceStrip 노출 = 축별 `coverage`(ready/missing) + `evidenceIds` 칩만. (macro 축은 [`sixAct.py:204`](../../src/dartlab/story/sixAct.py#L204) 근방 미구현 → `coverage='missing'` 라벨.)

**역할.** 근거완전성(품질 루브릭 축②)의 1차 천장. 풀 `블록→rcept_no` 회로 부재 하에서, **이 evidenceIds 표면화율 + 블록 sourceEngine 도달율**이 근거 신뢰의 측정 가능한 토대.

**신규 fetch.** 0. sixActScore 는 in-repo 계산. bake 가 직접 호출(F2) + 직렬화만.

---

## 간판 3 — honest-skip reject-gate (Hook Engine 의 bake화)

**무엇.** bake 단계 `_reportQualifies(payload)` 게이트: (1) `buildStory` 예외 없이 완료 (2) `summaryCard.conclusion` 비어있지 않음 (3) `nonEmptySectionCount ≥ N` (4) 핵심막(수익구조·수익성·현금흐름·안정성·가치평가) 중 ≥ M 개 블록 보유 (5) `evidenceFrame` 비어있지 않음(sixAct 축 ≥ K 개 `coverage='ready'`). 미달 → **파일 안 굽고** `_skipped.json` 에 `{code, reason}` 누적 → 클라 404 → "데이터 부족 — 보고서 미생성(사유)".

**임계.** N/M/K 은 **P0 spike(30~50사 분포 실측)로 확정**(03문서 §spike). "권장값" 박지 않음.

**철학.** "약한 발행 < 발행 거부"(editorial Hook Engine 공유). 인공 점수 신설 0 — 빈 섹션 카운트는 *이미 있는 신호*(NEVER-CLAIM 종합점수 금지 준수).

---

## 간판 4 — `@media print` + `window.print()` zero-dep PDF

**무엇.** jspdf/html2canvas **금지**(번들 무겁고 한글 폰트 깨짐). 단일 `@media print` 스타일시트가 `.dlTerm` 다크 토큰을 라이트 A4 문서로 재바인딩(`--dl-bg-base→#fff`, `--dl-ink→#1a1a1a`, 인쇄 채도↓ 상승 `#c0392b`/하락 `#1f5fc0`), `.rptTabs/topBar/print버튼 display:none`, `.rptSection break-inside:avoid`.

**★명시된 실패모드.** (a) klinecharts 캔버스는 print 시 빈 캔버스 위험 → ChartBlock 은 인쇄용 정적 SVG 사전 스냅 또는 인쇄 시 표 대체. (b) running header/footer 는 CSS `::after`(1회 출력) 불가 → `@page` margin box(`@bottom-center`) 사용. (c) 모달 scrim 오염 방지 → 인쇄 타깃은 `.rptDoc` 본문만, 그 외 `display:none`.

**경계.** table-export `ExportPort` 는 *개념만* 차용(미착수 PRD, 코드 의존 금지). 문서 PDF 는 window.print 독립. xlsx 다운로드 버튼 금지(table-export 소유).

---

## 간판 5 — 섹션→공시뷰어 딥링크 (근거 마지막 한 홉 · 90점 레버)

**무엇.** 핵심 5막(수익구조·수익성·현금흐름·안정성·가치평가) 섹션 헤더/EvidenceStrip 에 **"원문 보기" 딥링크**를 단다. 클릭 → 터미널에 **이미 존재하는** `ViewerOverlay`(공시뷰어) 또는 `FilingSearchDialog` 로 점프, 해당 섹션의 **대표 `rcept_no`**(예: 최신 사업/분기보고서) 원문을 연다.

**왜 90점인가.** 적대검증(보고서 품질 심판, sampleReportScore 88)이 짚은 *유일한 90 미달 원인* = 신용/포렌식 독자의 "측정값을 원문 공시 줄로 데려가달라"는 마지막 요구. `sourceEngine` 라벨은 "계산 엔진"이지 "공시 출처"가 아니다(03 §4 한계 명시). 그 한 홉을 **블록당 rcept 역배선(P4, 100+ 블록)이 아니라 섹션당 대표 rcept_no 1개 매핑**으로 메운다 — 신용심사역의 "어느 줄"이 "한 클릭 안의 원문"으로 바뀐다(88→90+).

**범위.** 블록당이 아니라 **섹션당 대표 rcept_no 1개**(P0 spike 측정 항목에 "섹션→대표 rcept_no coverage" 1행 추가). 품질 루브릭 축⑦(실행가능성)을 보조 8점에서 *핵심 5막의 필수 닻*으로 격상. **블록당 rcept(어느 주석 행)는 P4 천장** — 섹션당은 신용 독자의 방향성 요구를 메우되 포렌식의 "어느 줄"까지는 honest-skip 라벨로 cap(은폐 0).

**★범위 재계상(2차 적대검증 H7').** "배선만·신규 0"은 과장이었다 — 실측: `ViewerOverlay.svelte` 는 `code`/`vs`(비교종목)만 받아 **회사 단위**로 열고 *rcept 타깃 prop 이 없다*. `FilingSearchDialog` 의 기존 행클릭은 인앱 딥링크가 아니라 **외부 DART 링크**(코드 자백 "본문 직행 불가"). 따라서 *진짜 한 홉*(인앱 뷰어가 그 rcept 본문으로 스크롤) = **`ViewerOverlay` 에 rcept 타깃 prop + 본문 스크롤 = 작지만 신규 배선**(P2 필수 산출물). 신규 *엔진* 0(데이터·뷰어 본체 재사용), 신규 *배선* = 1 prop + 스크롤.

**신규 fetch.** 0. payload 에 섹션별 `representativeRceptNo` 1필드 추가(panel `rceptNo` 셀 보유, period 최신 rceptNo 유도). 외부 floor(DART 링크)는 즉시 가능, 인앱 딥링크는 P2 ViewerOverlay prop 신설 후.

---

## §5 · 심판 7갭 → 해소 (정본 박제)

| # | 심판 갭 (FATAL/gap) | 코드 재검증 | 해소 |
|---|---|---|---|
| G1 | killer2 가 "landing EvidencePanel 재사용"에 걸려있으나 컴포넌트 **부재** | `EvidencePanel` grep = viz spec 레이어만, 터미널 컴포넌트 0 | killer2 → **신규 구축**으로 재기술(01 F3). 축② 천장 = 신규 구축 후 표면화율 |
| G2 | "Section.act 읽어 직렬화" 검증 | 런타임 Section 엔 act 없으나 **`SectionMeta`(catalog) `act` 실재 + manifest 이미 bake**(01 F1 재정정) | 6막 헤더 = `getSectionMeta(key).act`→ACT_HEADERS (기존 catalog 필드, `partId.split` 폐기·버그) |
| G3 | "sixActScore registry 호출됨" provenance **거짓** | grep = 정의+buildCompanyCharts.py:125 뿐, registry 0(01 F2) | bake **직접 호출**(sixAct.py:234, L3 정합) |
| G4 | `SixActScore` 6축 score = 레이더 = **NEVER-CLAIM 자기위반**(노출/비노출 모순) | sixAct.py:1-15 "0~100 점수·hero radar"(01 F4) | EvidenceStrip = **점수 비노출**, coverage+evidenceIds 칩만 확정 |
| G5 | 8문서 0개 = **자기충족성 미달**(C-2 표·spike 절차·payload 스키마·의사코드 약속만) | 디렉터리 file count 0 | 본 8문서 실작성: C-2 표 행 단위(04) · spike 측정→임계 절차(03) · payload JSON 완전 예시(03) · buildReportView 의사코드(03) |
| G6 | sourceEngine 태깅 **메커니즘 미정의**(blocks.py 필드 없음, registry 출처 미운반) | blocks.py 6 dataclass 에 sourceEngine 0(01 §3.5) | **정적 catalog 필드 + bake 직렬화기 walk**(03 §sourceEngine) — 100+ 호출부 태깅 회피 |
| G7 | conclusion 1줄도 narrate 판정어휘 톤일 수 있음(C-2 와 충돌) | narrate.py 26/58/90 '양호/충분' 생산 | **conclusion 1줄도 C-2 변환 통과**(04 §C-2 §conclusion) |

이 7건 해소로 1차 심판이 명시한 95/90 도달 경로를 닫는다.

## §6 · 2차 적대검증(작성된 문서 대상) → 추가 정정 (정본 박제)

작성된 8문서를 **3인 독립 적대 심판**(PRD 엄정성 84 · 보고서 품질 88 · 코드사실 9/10 TRUE)이 재검증. 1차 청사진이 아닌 *실제 문서*를 코드로 대조해 다음을 추가 정정:

| # | 2차 갭 | 코드 재검증 | 해소 |
|---|---|---|---|
| H1 | ★F1 정정 자체가 오류 — `partId.split` 처방이 메타섹션(IP/SV/T)에서 버그, `SectionMeta.act` 실재 무시 | catalog.py:38 `SectionMeta.act` 실재 + manifest 이미 bake | F1 재정정: `getSectionMeta(key).act`→ACT_HEADERS (기존 필드·신규작업 감소) — 01 F1 / 02 G2 갱신 |
| H2 | payload 예시 `partId:"1-1"` 날조 (실제 "1") | catalog `SectionMeta("수익구조","1",...)` | 03 payload 실데이터("1", act 정수)로 교정 |
| H3 | 섹션→blockKey 골격이 manifest 에 이미 baked인데 신규작업 과대계상 | buildStoryManifest.py:102-104 per-section keys/act bake | 01 §5 / 03 §4 범위 재계상(bake 는 회사별 present 블록만 신규) |
| H4 | 관점 수 불일치 ("11" vs 12 entry vs 10 나열) | reportTypes.py 12 entry | "11 정적 투영가능(full 포함, thesis 제외)" 통일 — README/00/04 |
| H5 | `SixActScore.asDict()` 가 `score` 노출 → "점수 비노출"과 모순 | sixAct.py:55 `score:{axis:value}` | bake 가 asDict `score` 를 `_internalScore`(숨김)로 **분리**, axes 엔 coverage+evidenceIds만 — 03 명시 |
| H6 | costBreakdown SSOT(dossier dual) 미결·"P0 중 결정" 유예 | — | **본 PRD 에서 확정**: 비율 블록 = story/analysis 소유, 성격별 raw 명세 = dossier 소유·링크 — 04/07 |
| H7 | 신용/포렌식 90 미달 = 측정값→원문 공시 줄 마지막 한 홉 | ViewerOverlay/FilingSearchDialog 존재(단 H9 참조) | **간판 5 신설**(섹션→공시뷰어 딥링크, 섹션당 대표 rcept_no) |

### 2차-2 라운드(정정 문서 재검증, PRD 92 / 보고서 89) → 마무리 정정

| # | 갭 | 해소 |
|---|---|---|
| H8 | 04 §2 매핑표 1셀에 폐기한 `partId.split` 공식이 "신규 파생"으로 잔존(F1 재정정 미전파) | 04 §2 → `getSectionMeta(key).act`→ACT_HEADERS "기존 필드"로 교정 |
| H9 | 간판5 "배선만·신규 0" 과장 — 실측 `ViewerOverlay` 는 code/vs만(rcept 타깃 prop 없음), `FilingSearchDialog` 한클릭=외부 DART 링크("본문 직행 불가") | 범위 재계상: 신규 *엔진* 0, 신규 *배선* = ViewerOverlay rcept prop 1개+본문 스크롤(P2 필수). valuation 닻=fin-stmt-lab 미착수 시 honest-skip(죽은 링크 금지) — 00/02/06/07 갱신 |

2차 정정 후 자기평가: PRD 범위 정합·자기충족성 회복(신규작업 *감소* 방향 + 잔재 0), 보고서 90 레버(간판5)를 *범위 재계상*으로 확보(과장 제거가 오히려 신뢰↑).
