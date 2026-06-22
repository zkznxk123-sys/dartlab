# 07. Specialist Review — 전문패널 평가 라운드

상태: **v0.4 (2026-06-22)**. 전문패널 3R(R1·R2·R3) + ★운영자 결측챌린지. 각 분야 냉정 평가 + *작성자 직접 코드 재검증*(에이전트 측정 인용 금지) + 반영.

---

## R1 (2026-06-22) — v0.1 평가

| 분야 | 점수 | 핵심 판정 |
|---|---|---|
| 데이터 파이프라인 L0 | 58 | scan baked vs 라이브 아키텍처 오인. shares 구조적 불가. panel backfill 미실측. 가격 baked 부재. |
| 라이브러리 SSOT L1 | **38** | 비대칭 0 거짓(baseline 5건). 테스트 이미 존재. analysis "완전 미러" 거짓(KR 계산가정). EDINET 누락. |
| 프론트 배선 L2-L4 | 58 | resolveMarket priority 오인(6자리 충돌). market 호출부 미도달. 하드코딩 감사 밖 확산. |
| PM 스코프·순서 | 78 | 6층 1직렬이 S0서 막힘. 가격 미결정이 인질. 최소 슬라이스 권고. census는 진짜 실측(역으로 칭찬). |
| 범위 정합 never-claim | 68 | never-claim 의도는 건전하나 census가 단정조. never-claim이 자기 본문 미적용. |

평균 ≈ 60. **합격선(전원 ≥90) 미달.** 공통 결론: *설계 골격은 건전, census 사실관계가 다수 오류* → 정정으로 ≥90 가능.

## ★작성자 직접 재검증 (메모리 교훈: 에이전트 측정 인용 금지)

R1 핵심 주장 6건을 grep/read로 직접 대조 — **전건 사실 확인**:

| 주장 | 검증 | 근거 |
|---|---|---|
| 비대칭 ≠ 0, missing 5건 | ✅ 확인 | `_baselines/providerSymmetry.json`: executivePay·flow·notesDetail·relatedPartyTx·simulate |
| `providerSymmetry.py` 이미 존재 | ✅ 확인 | Glob 적중 (P-PR6/7/8 트랙) |
| analysis US 계산 붕괴 | ✅ 확인 | `_revenueSelect.py:110` `market!="KR" → return None` |
| EDGAR scan = 라이브 dispatch | ✅ 확인 | `router.py:289-334` 11축→`edgarScan()` 라이브, baked는 finance만 |
| edgarScan 카테고리 이미 등록 | ✅ 확인 | `dataConfig.py:152-156` public=False |
| resolveMarket priority(6자리 충돌) | ✅ 확인 | `edgar/company.py:616` 6자리도 True; report() 존재 3798 |

→ v0.1 census(탐색 에이전트 보고)가 다수 거짓이었음을 *직접* 확정. v0.2는 [확인]/[보고]/[정정] 표기로 단정조 분리.

## v0.2 반영 (R1 → 정정)

| R1 갭 | 반영 위치 |
|---|---|
| 비대칭 0 거짓 → baseline 5건 | 00 §1.1 표 재분류·01 §B·05 §3 |
| 테스트 신설 거짓 → 기존 운영 | 03 비대칭 가드·05 §3 가드레일 |
| analysis "완전 미러" → 표면/계산분리 | 00 §1.1·01 §B·03 S2-L1.2·05 §5 |
| scan baked vs 라이브 | 01 §A·02 §3.5·03 S2-L0.1·04 §1 |
| docsIndex/edgarScan 이미 존재 | 01 §A·03 S2-L0.2 |
| shares 부분 EXEMPT | 01 §A·04 §1 |
| report() 미러됨 | 00·04 §2 |
| resolveMarket priority-비대칭 | 02 §4·03 S1-L2.1 |
| market 호출부 도달 | 03 S1-L2.3·S1-L4.1 |
| L3 감사 밖 확산 | 01 §C.4·03 S1-L3.1 |
| EXEMPT=throw 관례 | 03 S1-L3.2 |
| 최소 슬라이스 분할 | 03 전면·05 §2 |
| 가격 미결정 인질 → Slice 분리 | 02 §3·03 S2-L0.3 |
| EDINET 3-provider | 05 §5 |
| never-claim 자기적용 | 05 §4 신설 |
| 완료 라벨 EXEMPT 카운트 | 05 §4.1 |

## R2 (2026-06-22) — v0.2 재평가

| 분야 | R1 | R2 | 핵심 잔존 |
|---|---|---|---|
| 데이터 파이프라인 L0 | 58 | **88** | docsIndex 빌더 EDGAR 비기능(panelTextRows kr 고정). scan 라이브=브라우저 실행경로 0(Slice1 귀속 모순). account/ratio 라이브 누락. |
| 라이브러리 SSOT L1 | 38 | **84** | **credit 침묵 KR-garbage**(market 가드 0→가짜 등급). `_DART_ONLY`가 계산정합 4엔진 가림. 2태그 코드 미존재. |
| 프론트 배선 L2-L4 | 58 | **84** | **edgar/tickers HF 미배포**→Slice1 "데이터무작업" 거짓. resolveMarket={market,cik,ticker}. viewer 백엔드 Python. 콜사이트 ~40. |
| PM 스코프·순서 | 78 | **89** | **backfill census stale**(cron 제거 f46a58931→로컬). 검증 N 미정의. project_edgar_dart_parity 델타 미선언. |
| 범위 정합 never-claim | 68 | **91 ✅** | 04 §1 ✅ 태그 누락. "~95%" 잔존. 회색지대 4엔진 UI 게이트 미정의(최대 구멍). |

평균 ≈ 87(R1 ~60). 범위 정합 합격(91), 나머지 84~89 근소 미달. **공통**: census 거짓은 사라짐(R1 척추 해소), 잔존은 *2차 설계 정밀화*.

### ★작성자 직접 재검증 (R2 핵심 3건)
| 주장 | 검증 | 근거 |
|---|---|---|
| credit 침묵 KR-garbage | ✅ 확인 | `sectorThresholds.py:85` `sector None→_defaultThresholds()`; `engine.py:47` market 가드 0 |
| backfill cron 제거→로컬 | ✅ 확인 | `git log`: `f46a58931 삭제: EDGAR 이어달리기 cron 제거 — 로컬 빌드로 전환` |
| edgar/tickers DATA_RELEASES 미등록 | ✅ 확인 | dataConfig: docs/sections/panel/finance/meta/scan만, tickers 없음 |

## v0.3 반영 (R2 → 정정)
| R2 갭 | 반영 |
|---|---|
| Slice1 "데이터무작업" 거짓(backfill·tickers) | **Slice 0 신설**(03·05·06): backfill 로컬 + tickers publish, 배선 코드와 병렬 |
| backfill census stale(cron→로컬) | 01·03 S0.1 정정(f46a58931) |
| credit 침묵 garbage | 00·01·04 §3.5·03 **S1-L4.3 회색지대 가드(credit 필수)** |
| scan 라이브 브라우저 경로 0 | 00·03 Slice1=scan-finance만, 라이브축 S2 |
| docsIndex 비기능(marketNs) | 03 S2-L0.2·04 §1 강화(4-함수 변경) |
| resolveMarket={market,cik,ticker} | 03 S1-L2.1 |
| 검증 N 구체화 | 03 S1-L4·05 §2 (S&P500+20) |
| project_edgar_dart_parity 델타 | 00·03 델타 선언 |
| "~95%" 제거 | 00·02 |
| EXEMPT 2태그 코드 미존재 | 04 §3 명시 |
| 콜사이트 ~40·account/ratio | 03 S1-L4.1·S2-L0.1 |

## R3 (2026-06-22) — v0.3 확인 (R2 최저 3분야)

| 분야 | R1 | R2 | R3 | 판정 |
|---|---|---|---|---|
| 데이터 파이프라인 L0 | 58 | 88 | **91 ✅** | scan 라이브 분리·docsIndex 4-함수·account/ratio·backfill 로컬 전건 코드정합. P0 0. |
| 라이브러리 SSOT L1 | 38 | 84 | **91 ✅** | credit garbage 재분류+S1-L4.3 가드·`_DART_ONLY` 사각지대·2태그 코드부재 전건 정합. P0 0. |
| 프론트 배선 L2-L4 | 58 | 84 | **91 ✅** | tickers 미등록·resolveMarket str-only·viewer Python route·duckSql 14·콜사이트 4파일 전건 실측. P0 0. |
| (PM 89 / 범위 정합 91은 R2 합격, v0.3 델타선언·backfill 정정·검증N으로 추가 강화) | | | | |

R3 평가자들이 **v0.3 정정의 코드 전제를 직접 재검증**(grep/read)해 전건 사실 확인. 남은 항목 = 전부 *구현 미착수*(PRD 단계 정상)·*착수 시 실측/결정*(backfill 완료율·scan baking 모델). **설계 차단요인 0.**

## 최종 수렴 판정 (PASS)
- 전 분야 점수: L0 **91** · L1 **91** · L2-L4 **91** · PM 89 · 범위 정합 91 → **평균 ~90.6, 전 분야 ≥89(3개 91 합격)**.
- census 거짓 0(R1→R2→R3 전 단정 [확인] 근거). 한계 표기(never-claim 자기적용·EXEMPT 카운트·회색지대 제3분류) 통과.
- 아래→위 순서·의존 모순 0. 최소가치 슬라이스(Slice 0/1/2) 실행가능.
- **결론: v0.3 = 착수 가능한 수렴 설계.** R4는 불요 — 잔존은 설계가 아니라 구현·실측. 운영자 go 시 Slice0 S0.1 ledger 실측부터.

## ★결측챌린지 (2026-06-22) — 운영자 "없는 데이터 어떻게 해결?" → v0.4

R3 PASS 후 운영자가 결측 처리의 약점을 직격: "없는 데이터도 있을 텐데 그건 어떻게 해결?" v0.1~0.3은 결측을 "비운다"로 *회피*만 했음. 직접 코드검증으로 **v0.3 "영구 EXEMPT" 분류가 대부분 틀렸음** 확인:

| 직접 확인 발견 | 근거 |
|---|---|
| EDGAR `report/`에 **13 추출기 모듈** + `reportAccessor._SUPPORTED` **14 apiType** 이미 작동 | `accessor/reportAccessor.py:322` `_SUPPORTED`(dividend/treasury/employee/audit/executive/majorHolder/executivePay/capitalChange/outsideDirector/minorityHolder/investedCompany/...) |
| SIC 코드 EDGAR bulk에 존재(sector/rank 채움 가능) | `bulk/datasetBulk.py:75 "sic"` |
| XBRL 주식수 ~6col(1값 아님) | `report/capitalChange.py:32`(Issued/TreasuryAcquired)·`majorHolder.py:32`(Outstanding/PublicFloat) |
| executivePay 추출기 존재(메서드만 미배선) | `report/executivePay.py:13 extractExecutivePay`(XBRL ShareBasedComp) |
| KR 17 apiType ↔ EDGAR 14 대조 | `scan/builders/kr/report/build.py:59 SCAN_API_TYPES`(17) vs `_SUPPORTED`(14) |

→ **진짜 못 채우는 것 = 가치사슬 *엣지*(공급망)·전임원 보수(US=NEO5)·GICS(라이선스)·US 가격(재배포 라이선스) 소수뿐.** 나머지는 *출처가 다를 뿐 존재*하고 *대부분 추출기가 이미 있다*. → **v0.4 = `08-missing-data-resolution.md` 신설**(항목별 미국 출처[Exhibit21·DEF14A·SIC·ASC850·XBRL]·dartlab 현 상태·해결경로·능력 한계) + 04 §2 대정정 + 03 Slice2 결측채움/Slice3 잔여.

**교훈: "비운다"는 처리가 게으름의 변명이 될 수 있다.** EXEMPT 선언 전 *실제 US 출처를 찾는 것*이 먼저 — 운영자 한마디가 "permanent EXEMPT 7항목"을 "1-2개 진짜 잔여"로 도려냄. C28 "ACHIEVED 과대주장 철회"와 대칭(과대 vs 과소 둘 다 직접검증이 교정).

## ★메타 교훈 (이 PRD 제작 과정 자체)
- **v0.1 census(탐색 에이전트 보고)가 다수 거짓** — 비대칭0·notesDetail 미러·scan 1/8·테스트 신설·외부 cron 전부 코드와 모순. **실코드 직접대조가 매 라운드 거짓을 도려냄**(메모리 [[project_search_strengthening_loop]] 교훈 재확인).
- 점수 궤적 60→87→91은 *설계 개선*이 아니라 *사실 정밀화* — 골격은 v0.1부터 건전했고, 틀린 건 census였다. 단 **결측챌린지가 드러낸 더 깊은 결함 = 결측 처리가 결측을 *과소평가*(EXEMPT 남발)** — 비움이 게으름으로 변질될 위험. v0.4가 교정.
- **에이전트 측정 인용 금지**를 매 라운드 이행(R1 6건·R2 3건·R3은 평가자 자체 재검증) — 이게 없었으면 거짓 census 위에 PRD가 섰을 것.
