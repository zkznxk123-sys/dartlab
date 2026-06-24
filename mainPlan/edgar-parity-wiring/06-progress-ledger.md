# 06. Progress Ledger

상태: **v0.3 (2026-06-22)**.

> 실행 진행 + PRD 개선 라운드 기록. NEXT 포인터로 재개.

---

## PRD 개선 라운드 (전문에이전트 평가 수렴 — 상세 07)
| 라운드 | 일자 | 결과 | 반영 |
|---|---|---|---|
| 초안 v0.1 | 2026-06-22 | 3 census 기반 6층 PRD | — |
| R1 | 2026-06-22 | 58/38/58/78/68 (평균≈60). census 다수 거짓 적발 → 작성자 직접 재검증 전건 확인 | **v0.2** 전면 정정 |
| R2 | 2026-06-22 | 88/84/84/89/**91✅** (평균≈87). census 거짓 해소, 2차 정밀화 잔존(credit garbage·tickers publish·backfill 로컬) | **v0.3** 정정(Slice0 신설·회색지대 가드·census 재정정) |
| R3 | 2026-06-22 | L0/L1/L2-L4 = **91/91/91 ✅**(R2 최저 3분야 확인, 코드 전건 정합). PM 89·범위 정합 91 합격 유지 | **수렴 PASS** — 설계 차단요인 0, 잔존은 구현·실측 |
| ★결측챌린지 | 2026-06-22 | 운영자 "없는 데이터 어떻게 해결?" → 직접 코드검증: v0.3 "영구 EXEMPT 7항목"이 **대부분 채울 수 있음**(report 14 추출기·SIC bulk·XBRL shares·Exhibit21). 진짜 빔=가치사슬엣지·NEO5·GICS·가격라이선스 소수 | **v0.4** — `08` 신설(항목별 US 출처·해결경로)·04 §2 대정정·03 Slice2 결측채움+Slice3 잔여·00/05 정합 |

## 구현 진행 (착수 = 운영자 go) — [정정 v0.4] Slice 0/1/2/3
| 슬라이스 | 단계 | 상태 | 비고 |
|---|---|---|---|
| **Slice 0** (선결, 배선과 병렬) | S0.1 panel backfill(로컬) · S0.2 edgar/tickers publish | 🔄 | S0.1 ~79%(run4)·CIK robust ✅·**S0.2 ✅ publish 실측** |
| **Slice 1** (배선 코드) | S1-L2 resolveMarket+계약 · L3 소스 · L4 서피스+회색지대 가드 · L5 스위처 | 🔄 | **L2.1 resolveMarket ✅·L4.3 credit 가드 ✅**·나머지 L2.3/L3/L4/L5 |
| **Slice 2** (미빌드+★결측 채움) | S2-L0 scan baking·docsIndex · **S2-L0.4 결측 채움(report 14 bake·SIC sector·shares XBRL·relatedPartyTx)** · S2-L1 dispatch+계산정합 | ⬜ | 08 상세. 출처 있는 건 채움 |
| **Slice 3** (진짜 잔여) | network(Exhibit21)·가치사슬 엣지(부분)·executivePay NEO5·US 가격(라이선스) | ⬜ | 한계 라벨·최후순위 |

## ★실집행 로그 (2026-06-23~24, 운영자 goal "정공법 완전 구현")
| 항목 | 커밋 | 검증 | 비고 |
|---|---|---|---|
| **S0.1 CIK robust** — `resolveCik` browse-edgar fallback | `d5444b6ed` push | unit 4종·CTRA→858470·HOLX→859737 실측 | company_tickers.json 누락 filer(Coterra·Hologic) SEC browse-edgar 인덱스로 실해소. CIK 실패→매 run 재시도 회귀 차단 |
| **S0.1 backfill** — 로컬 resumable rebuild | (데이터, HF) | run1+2+3 누적 1,108→**6,018/7,645=78.7%**, run4 진행 | run 당 12h deadline·resumable. ⚠ COFS OverflowError(float inf→int) 1종 isolated(후속) |
| **S1-L2.1 resolveMarket** SSOT | `6aee54a8e` push | vitest 7종 | 식별자→{market,code/ticker/cik} priority-비대칭. 6자리=KR∩CIK 모양충돌→명시 override·기본 KR(무회귀). 산재 `/^\d{6}$/?KR:US` 정본 대체 |
| **S1-L4.3 credit 가드** — 비-KR None | `63e61d8ce` push | unit 2종 | evaluateCompany market!='KR'→None. KR-garbage 가짜등급(확신오정렬) 차단·`_revenueSelect` 정직 None 과 대칭화 |
| **S0.2 edgar/tickers publish** | `b0c11c9c2` (push 대기 — ci-fast) | HF HEAD 200·177KB·unit 2종 | DATA_RELEASES edgarTickers 등록 + rebuild publish + 1회 즉시. 브라우저 ticker↔CIK 언블록 |

### ★회색지대 4엔진 — 직접검증 정정 (S1-L4.3 범위)
- **credit = 유일 *uniform 침묵오염*** → 블랭킷 가드 정답(✅). sectorThresholds KR 기본임계를 US-GAAP 에 먹여 non-None 가짜등급.
- **quant ≠ 블랭킷 가드** — `__init__` dispatch 가 axis별 market 분기("KR Naver / US Yahoo Finance"), momentum/beta 는 *실제 US 지원*. 블랭킷 None=working 축 파괴 over-reach. → 가드 안 함.
- **analysis/story 계산정합 = Slice 2(S2-L1.2 census)** 명시 분류 — KR 계정명/WICS 의존. Slice 1 라이브러리 가드 대상 아님(surface 배지 + Slice2 캘리브).
- **결론**: S1-L4.3 *라이브러리* 필수 가드 = credit 단일로 완결. 나머지 회색지대 = surface 배지(S1-L4 프론트, UI push 승인)·Slice2.

### ★★census 대정정 (2026-06-24, "터미널서 AAPL 검색하면 도나?" 직접검증)
HF 실측(`list_repo_files`): **`edgar/finance/` = 0 파일** (dart/finance/ 3,141 대비). **PRD 03/01 의 "Slice1 = 이미 baked 된 finance" 가정이 틀림** — US 회사별 재무제표는 HF 미발행(EdgarCompany 는 SEC companyfacts API *직다운로드*라 백엔드만 작동, 브라우저=불가). `edgar/scan/finance.parquet`(집계 1파일)만 200. **즉 AAPL 미동작은 2겹**: ① **배선**(source 전부 `dart/` 하드코딩·resolveMarket 소비자 0: financeSource:59·regularFilingsSource:22·reportSource:725/736·annual:184·annual:181 `!/^\d{6}$/→null`) ② **데이터**(edgar/finance 0파일). panel(공시)만 데이터 준비(`edgar/panel/AAPL.parquet` 200·6,294파일). **정정된 슬라이싱**: Slice1 = panel/filings 배선(데이터 OK) / **finance 는 Slice2 로 강등**(2차 백필 발행 = edgar/finance/{cik}.parquet, dart/finance 미러) / price = Slice3(라이선스). "그대로 완전 동작"엔 finance 발행 백필이 선결.

## NEXT (운영자 go 받아 실집행 중 — 2026-06-24)
1. **S0.1 backfill 완주** — run4~ resumable, 잔여 ~1,627 → 100% (자율 진행).
2. **S1-L2.3 6포트 market 차원** — [재검토] 블랭킷 `market?` 전포트 추가는 over-engineering 가능. 실라우팅은 L3 source 의 resolveMarket(code). 최소 = 필요 포트만 + source 라우팅. 착수 전 granularity 결정.
3. **S1-L3/L4/L5 surface 배선** — US 렌더·EXEMPT 카운트·회색지대 배지(analysis/quant/story). **UI push=운영자 명시 승인** + backfill 완주 후 S&P500+20 렌더 검증.
4. Slice2 착수 전 §6 점검표(report 14 산출률·SIC 커버리지·DEF14A/Exhibit21 PoC).

## 미해결 쟁점 (결측챌린지 후)
- ✅ 결측 데이터 해결: 대부분 채움(08) — report 14·SIC sector·shares XBRL·network·relatedPartyTx.
- ✅ 진짜 빔(소수): 가치사슬 엣지(부분)·NEO5·GICS·US 가격(라이선스).
- ⬜ scan baking 모델 통일 — S2-L0.1 결정(착수 시).
- ⬜ panel backfill 현 완료율 · report 14 apiType 실제 산출률 · SIC 커버리지 — 착수 전 실측(04 §6).
- ⬜ US 가격 재배포 라이선스 실조사(stooq/tiingo/nasdaq ToS) — Slice3.
- ⬜ docsIndex marketNs 비기능 정정 범위 — S2-L0.2.
