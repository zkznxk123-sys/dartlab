# 06 — 진행 원장

## Phase-0 사전점검 probe 결과 (2026-06-23, 실측 — 08 §4.1 SHIP 게이트)

> `/tmp/probe_dossier.py`·`/tmp/probe_cancel.py` (src 미커밋·stdout, polars 직독 `data/dart/scan/report/*.parquet`). 전 ~2,942 filer 측정. **"스키마 존재 ≠ populated" 검증 — SHIP 숫자를 측정값으로 대체.**

| feature | 측정 항목 | 실측 | 판정 |
|---|---|---|---|
| **F1 체이닝** | DPS thstrm 대비 frmtrm/lwfr non-null | frmtrm **91.9%** · lwfr **88.0%** (thstrm 조건부) | ✅ |
| **F1 체이닝** | DPS 종목별 데이터포인트 lift (fy=rcept[:4]−1) | **1.46x** (≥2년 종목 1.43x, 3.8년→5.5년) | ✅ PRD "1.4x" 정확, 간판 유지 |
| **F3 control-shift** | majorHolder ≥2 기간 보유 종목률 | **96.8%** (2,834/2,928, 중앙값 20기간) | ✅ 가장 보편적 |
| **workforce 자기이력** | employee ≥2년 보유 종목률 | **96.1%** (2,799/2,914) | ✅ 보편 |
| **F2 소각(buybackCancel)** | `change_qy_incnr`≠0 종목 (보통주·총계) | **9종목** (필터무관 전체도 30종목) | ❌ 간판 불가 |
| F2 금고(treasuryEnd) | `trmend_qy`≠0 종목 | 158종목 (5.4%) | 보유사만 |

**F2 대안 추적(probe_cancel)**: capitalChange `isu_dcrs_stle`='소각' 명시 = **0종목**. `감자` = 460종목이나 전부 유상/무상감자(자기주식 소각 아님 — 무상감자=손실성, 혼동 시 NEVER-CLAIM 위반). **결론: 자기주식 소각은 한국 시장에서 진짜로 희소(~30종목) = 데이터 부재이지 배선 실패 아님.**

### ★ 정공법 판정 (probe 반영 — 00/02 F2 프레이밍 정정)
- **F2 "소각 vs 금고"를 "3간판"에서 강등** → 자사주 보유사(~158) 한정 appears-when-clean 신호. 95% 종목은 빈상태가 default. 무상감자를 소각 환원으로 둔갑 금지(grep 가드 토큰에 '감자'≠'소각' 추가). zero-fetch라 *살려두되* 간판 expectation 제거.
- **간판 재배치 = 측정 검증된 보편 신호**: F1 체이닝(1.46x) · F3 control-shift(96.8%) · 인력 자기이력(96.1%) · lossPct(전 종목 장부가 존재, 미측정이나 구조상 보편). 이 4개가 Phase 1 무게중심.
- Phase 0(스파인 리본)·workforce·control-shift·lossPct·F1 체이닝은 probe로 **GREEN**. Phase 2(R&D·인적자본 백분위·costByNature)는 미측정(엔진 bake 의존) — slip 유지.

## 상태

- **2026-06-24 ★주석 본문 표면화 (07 F4-CUT 결정 번복 — 운영자 직접 지시)**: 운영자 "panel 파케 주석으로 우측패널에 진짜 정보를 채우자, 원문 링크뿐이면 안 되고 그 자체로 봐야지". doc 07 F4 가 23 주석을 "뷰어 원문 ↗링크 전속(CUT)"으로 잘랐는데, **PRD 00 §26 명제("데이터는 있다·못 쓰는 건 표면화의 얕음→갇힌 계산을 있는 그대로 표면화")와 정면 모순** → 번복. **panel 파케 `contentRaw`(주석 본문)를 우측 패널에 *그 자리* 렌더**(↗링크 아님):
  - contract `ReportNoteBlock` + `ReportPort.notes(code)` 신설. `reportSource.buildReportNotes` — **08 §4.2 정합 hyparquet 2-pass**(period 컬럼→최신기 → period 필터 row-group pruning, panel 13.4MB 전체로드 회피). DuckDB(`loadLiveCompanyPanelExcerpts` 휴면지뢰) 미사용.
  - 토픽 3종 blockLeaf 키워드 매칭(회사별 NT코드 변동에 강건, 08 G1): 관계·종속기업 투자(타법인출자 detail)·특수관계자 거래·우발부채·약정(**§11 "필드 없어 침묵"이라던 담보/보증 — 주석 본문엔 존재**). 연결 우선.
  - UI: 우측 '정기보고서 주석' 패널 — **지연 로드**('본문 보기' 클릭 시에만, panel 대용량 가드·타임아웃·에러·캐시). 뷰어 `CellContent` 재사용(DART XML→sanitize 표/텍스트), 블록 토글, ↗원문 보조. max-height 스크롤로 레일 보호.
  - 검증: contracts·runtime·surfaces·landing tsc/svelte-check **0err** · checkUiDataWiring PASS · dossierVerdictLint PASS · 실데이터 4개사(삼성·기아·동화·셀트리온) 주석 본문 추출 확인(관계기업 장부금액 표·특수관계자 거래·담보/보증/약정 실재). UI push=운영자 눈검수 대기.
  - ⚠ 교훈: AI 가 PRD 명제 안 읽고 07 F4-CUT 그대로 ↗링크만 깔아 "완성" 오판 → 운영자 교정. 잔여=토픽 확장(차입금/사채 등) 여부·자동로드 여부(pruning 실측 후) 운영자 결정.
- **2026-06-24**: **Phase 1b 완료**(killer 리프레임 잔여) — 커밋 대기(UI surface = 운영자 push 게이트). 구현:
  - **상세보기 크로스패널 네비 완성**: `finFullEntry.svelte.ts`(requestFinFull pulse, viewerEntry 동형) → CenterStack 이 pulse 구독·`finFullTab` → `FinFullscreen initialTab` 으로 PEOPLE/RETURN 탭 직열기(최초 마운트만 untrack 적용, 회사전환=종합 리셋). 인력 상세보기→PEOPLE·주주환원 상세보기→RETURN.
  - **인력 자기이력 문장**(`reportSelfHistory.ts::workforceTrend`): 총원 궤적(YYYY→YYYY ±%)+계약직 비중 이동. 새 fetch 0(wf[] 이미 메모리). 백분위/1인당부가가치는 Phase 2 baked(여기 미포함).
  - **주주환원 자기이력 문장**(`returnTrend`): 최근 연속 배당 연수(가용 window 내, 꼬리 미발표 null skip — 실측 005010)+배당성향 이동+소각(appears-when-clean). 새 fetch 0(srs[]).
  - **CARD_GUIDE convention**: 비재무 지표 올라가면/내려가면 리프레임 규약 + verdict 금지 주석(cardGuide.ts 상단).
  - **G3 NEVER-CLAIM grep 게이트 신규**(`tests/audit/dossierVerdictLint.py`, lint 게이트 배선): 회사별 verdict 합성형(우량주·주주친화·매수의견·비중확대 등)만 ban — bare 우량/매수/저평가(교육·백테스터·밸류에이션 정당 중첩)·부정형 면책문 미탐지(allowlist 휴리스틱 불요). 41 surface PASS.
  - 검증: surfaces svelte-check **0 error**·checkUiDataWiring PASS·reportSelfHistory 단위 11/11(데모 게이트 다년/무배당/첫배당/중간중단/당해미발표/소각)·실데이터 probe(DPS≥2년 42% 커버리지 측정, streak 버그 1건 적발·수정)·ruff·camelcase·audit-self OK.
- **2026-06-23**: Phase-0 probe 완료(위) → Phase 0 스파인 착수(정공법 구현 goal).
- **2026-06-19**: PRD v0.1 작성(13인 토론 `wf_c20526bc-bed`) → 확장 v0.2(07, 11인 `wf_c62ab765-ea5`) → **경화 v0.3(08, 4인 `wf_c451d741-93f`)**. 착수 대기(운영자 go).
- **구현 코드 1건(perf 버그 수정, commit `e801f42f0`)**: 정기보고서 팩트 패널 멈춤 = DuckDB→hyparquet 이관(실측 수십초→4.3초·svelte-check 0err·시각변화 없음). 나머지 feature 구현 0.
- **경화 평결**: "조건부 강함 — 강한 제품, 약한 기반". SHIP 전 정정 필수 6갭(08 §2): F2 도달불가(→NEEDS-PARSING)·F5 경로·grep가드 신규·lossPct lift·공개로컬 패리티·−1 4팩트 드롭. **Phase-0 사전점검 probe**(체이닝 1.4x·6%·shard0 대표성 측정)가 새 SHIP 게이트.

## NEXT (재개 포인터)

1. ~~**Phase 0 (스파인)**~~ ✅ `b3dec2ff8` — rcept_no/stlm_dt + 헤더 리본 + 팩트별 ↗.
2. ~~**Phase 1a (lossPct+control-shift)**~~ ✅ `f73cda8ea`.
3. ~~**Phase 1b (인력·주주환원 자기이력 + 상세보기 네비 + CARD_GUIDE convention + G3 verdict 게이트)**~~ ✅ `e3da75d07`(커밋·UI push 운영자 대기). **= Phase 1 MVP 완료**(스파인+zero-fetch 리프레임 = 컷라인).
4. **F1 (당기/전기 시계열 체이닝, 사용자 명시 요청 "panel IS처럼 이어서", doc 07 간판)** — ★**SHIP-게이트 정정 reconciliation probe 통과(2026-06-24)**: 7,433 (code,fy) 셀 · thstrm 1차공시 67.1%·proxy(frmtrm/lwfr만) 32.9% · 재수록 ≥2 셀 4,936 중 **2% 내 합치 96.5%**(canonical 명확)·**정정 3.5%**(마커 필요 입증·과설계 아님) · ★002200 DPS 80↔800(10x)=07 §2.4 스케일/데이터 드리프트 실재(단위정규화 선행·latest-wins+원본보존). **설계 견고 검증.** 구현 스코프(다음 단위, UI-visual): `buildShareholderReturn` dividend SELECT +frmtrm/lwfr/rcept_no/stlm_dt + `chainTriplet`(EXPLODE fy/fy-1/fy-2·reconcile 2%money·0.5pp ratio·canonical=thstrm-agree[clean 96.5% 기존값 보존]·정정=latest-wins+restated[3.5%]·proxy='전기재현'[32.9%]). 회귀안전=clean 연차 기존값 불변. **honesty=proxy/restated 마커 필수**(proxy 1/3·정정 3.5% 무표시=오해 → MiniFinChart 마킹+contract `prov`/`FinSeries.mark` 필요=UI-visual, 운영자 눈검수). 08 §3.4 마커=glyph+상시범례(hatch 6px 비가시 기각).
5. **Phase 2 (엔진 bake)**: 인적자본 분위 배열 + rndIntensity/costByNature CI parquet(08 G1 NEEDS-PARSING/CI-bake). slip 허용.
6. **Phase 3 (선택)**: 가동률 원문 발췌(zero 추출 한정).

> Phase 1b 하드닝(08 §3 상태기계): ✅ **facts 패널 'error' 상태 + 8s 타임아웃 race + ↻다시 시도 + role=status** 완료(영원히 '불러오는 중' 멈춤=원래 hang 버그 클래스 차단·reloadToken effect 재발화). 형제 패널(workforce/shareholder/investments)은 `guarded()` 로 이미 graceful degrade(hang→null→패널 부재, spinner 없음). 잔여 폴리시=형제 error-distinct 4-state·고정높이 스켈레톤·prefers-reduced-motion(별도 단위). UI=운영자 눈검수 대기.

## 열린 결정 (착수 전 확인 가능)

1. **R&D 스파크라인 vs 텍스트 추세**: 적대검증 합의=텍스트(↑/↓/→ + 전년 Δ), 레일 그래프 금지. 인라인 스파크라인 primitive 도입 안 함 확인.
2. **R&D 소스 태그 의미**: IS라인(정규화 비용) vs SG&A주석(총지출, 자본화 포함) = 다른 개념 → UI 가 회사별 소스 표시(절대 혼합 금지).
3. **Phase 2 slip 시**: Phase 1 단독 ship(R&D 행·백분위 축 부재로 우아하게 degrade, 깨진 빈 행 아님) 확인.
4. **`controlShiftSummary` 기간 선택**: earliest-vs-latest(큰 지배 이야기) vs latest-two(최신). 명시 YYYYqQ→YYYYqQ 라벨 어느 쪽이든.
5. **pctOfParentCap self-gate 임계**: 'material' listed 커버리지 기준(listed ≥1 AND listedStakeSum ≥ bookTotal 의 일정 비율)? 독립 소형주에 오해소지 작은 % 대신 자기 suppress 하도록 구체 cutoff.
6. **가동률 원문 블록(P3)**: 뷰어가 이미 rawMaterial 섹션 텍스트 렌더하는지(=anchor+label ship) vs 새 추출 필요(=컷) — feasibility 체크.

## 메모리 포인터

`MEMORY.md` §6.2 에 `[[project_terminal_periodic_report_dossier]]` 등록(포인터만, SSOT=본 폴더).
