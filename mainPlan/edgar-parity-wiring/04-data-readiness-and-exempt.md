# 04. 데이터 레디니스 + EXEMPT 경계 + Kill-List

상태: **v0.4 (2026-06-22)** — ★운영자 챌린지("없는 데이터 어떻게 해결") 대응. v0.3 "영구 EXEMPT" 대부분이 *채울 수 있음*을 코드검증으로 정정 — 상세 해결책 = `08-missing-data-resolution.md`. 미러 가능·해결 가능(08)·회색지대·진짜 빔(소수)·kill.

---

## 1. 미러 가능 (데이터 있음 — 배선만 통일)

| 표면 | US 데이터 출처 | 상태 |
|---|---|---|
| panel (공시 수평화) | `edgar/panel` per-filing | [확인] 빌드경로 ✅ / backfill 로컬(S0.1) |
| finance (XBRL) | `edgar/finance` companyfacts | [보고] baked |
| scan/finance | `edgar/scan/finance.parquet` baked | [확인] baked+deploy(edgarSync) |
| scan 재무축(11 XBRL+account/ratio) | `_edgarDispatch` **라이브 계산**(Python 전용·브라우저 실행경로 0) | [확인] 라이브 — 퍼블릭=baked 통일 결정(S2-L0.1) |
| scan/docsIndex | `buildEdgarDocsIndex` 함수 존재하나 [정정] **EDGAR 비기능**(`panelTextRows` marketNs=kr 고정→dart panel만) | ⬜ marketNs/extractor 주입(4-함수) |
| scan/changes | panel contentRaw 파생 | ⬜ item 경계 개념검증 선행 |
| scan/sharesOutstanding | `dei:` **단일 스냅샷 1값**(KR 17-col 불가) | ⚠ 부분 EXEMPT |
| analysis/quant/story | XBRL·yfinance·FRED | ⚠ 표면 미러 / 계산 KR가정(`_revenueSelect.py:110`=명시 None) |
| **credit** | XBRL leverage/cashflow | ⛔ [확인] **침묵 KR-garbage**(market 가드 0, `sector None→_defaultThresholds()` KR → US 숫자 non-None 가짜 등급). Slice1 가드 필수(S1-L4.3) |
| ticker↔CIK 매핑 | `edgar/tickers` [확인] **DATA_RELEASES 미등록** | ⬜ HF publish(S0.2) |
| search (공시 본문) | `edgarPanel` 검색 카탈로그 | [보고] 통합 BM25 live |
| 가격 | C(비활성, Slice 1) / A(`edgar/prices` baked, S2-L0.3 라이선스) | ⬜ Slice 분리 |

## 2. [대정정 v0.4] "영구 EXEMPT" 대부분 틀림 — 결측 해결책 = 08

★운영자 챌린지("없는 데이터 어떻게 해결") 대응 직접 코드검증: v0.3 "영구 EXEMPT" 항목 대부분이 **채울 수 있다**(상세 `08-missing-data-resolution.md`).

| 표면 | v0.3 | v0.4 실제(08) | 해결 |
|---|---|---|---|
| `report` 17 apiType | 영구 EXEMPT | **[확인] EDGAR 14 추출기 작동**(`reportAccessor._SUPPORTED`) | scan bake + DEF14A 2파서 + 메서드 배선(분류 A 대부분) |
| `sector`/`rank` | 영구 EXEMPT | **[확인] SIC bulk 존재**(`datasetBulk.py:75`) | SIC→US sector crosswalk + peer 계산(B/A). GICS만 라이선스(D) |
| `network` | 영구 EXEMPT | Exhibit 21·13D/G·13F 출처 명확 | 신규 파서 + US-native 재정의(B/C) |
| `industry` 가치사슬 | 영구 EXEMPT | 분류=SIC(B) / **엣지=major-customer 부분(C/D)** | 분류 채움 / 엣지만 부분·비워 둠 ← **유일 진짜 잔여** |
| `sharesOutstanding` | 부분 EXEMPT | **[확인] XBRL ~6col**(authorized/issued/outstanding/treasury/preferred) | XBRL 개념 확장(A/B) |
| `executivePay`/`relatedPartyTx` | missing | executivePay 추출기 有·relatedPartyTx=10-K Item13/ASC850 | 배선+DEF14A(C)/파서(B) |

**→ 진짜 영구 빔(D/불가) = US 가격(라이선스)·가치사슬 *엣지*(부분)·전임원 보수(US=NEO5)뿐. 나머지는 채운다.** 비우는 처리는 이 소수에만 — 가짜 채움 금지는 유지하되 *채울 수 있는데 안 채우는 게으름*도 금지(챌린지 핵심).

**처리 철학(00 §1.1)**: 채운 데이터는 US 출처 라벨(SIC-derived·Exhibit 21·DEF 14A NEO5), KR 등가 주장 금지. 진짜 빈 소수는 커버리지/한계 명시.

## 3. EXEMPT 2태그 — permanent vs dataWaiting ([정정] 비대칭 baseline 정합)

[확인] `_baselines/providerSymmetry.json` missing 5건 = `executivePay`·`flow`·`notesDetail`·`relatedPartyTx`·`simulate`(EDGAR 메서드 부재). 비대칭 가드(`providerSymmetry.py`)가 이를 태그로 구분해야 파서 구현 시 게이트가 풀린다.

[정정 v0.4] 아래 2태그는 *symmetry baseline missing-5*에만 적용(method 부재 가드). sector/rank/network/report17은 **§2/08에서 해결로 재분류**되어 여기서 빠짐.

| 항목 | 태그 | 데이터로 가능? | 본 PRD 처리 |
|---|---|---|---|
| `executivePay` | **dataWaiting** | US=**DEF 14A NEO5**·XBRL 보상(추출기 有) | **Slice2/3**(배선+DEF14A 보강) |
| `relatedPartyTx` | **dataWaiting** | US=10-K Item13/ASC850 | **Slice2**(파서) |
| `notesDetail` | **dataWaiting** | XBRL 일부 가능 | Slice2 |
| `flow`·`simulate` | **permanent** | KR 고유(공시 흐름·KR 시뮬) | baseline 명시 유지 |

**판정 원칙 [정정 v0.4]**: v0.3은 "EXEMPT 채우기=범위 밖 별도 goal"이라 했으나, *운영자 챌린지로 재판정* — 채울 수 있는 것(report 14·SIC sector·Exhibit21 network·shares XBRL)은 **본 PRD 범위(Slice 2/3)**다. 진짜 별도 goal/빔 = *가치사슬 엣지 합성·전임원 보수·GICS·US 가격 라이선스*뿐(08 분류 D). 범위 폭발 방지는 "발명 금지"로(있는 출처는 채우되 없는 걸 지어내지 않음).

> [정정] **2태그는 현재 코드에 없음** — `providerSymmetry.json`은 평면 `missing[]` + 코드 상수 `_DART_ONLY`(permanent만)/`_EDINET_DEFERRED`뿐. permanent/dataWaiting 구분은 *구현 작업*(baseline JSON에 키 분리 or `_SYMMETRY_MAP` 태그 dict). "설계 의도"이지 "현존 구조" 아님.

### 3.5 ★회색지대 — EXEMPT도 정상도 아닌 제3 분류 ([확인] R2 P0)
analysis/credit/quant/story는 *호출은 되나 계산이 KR 가정*. **EXEMPT(비활성·비워 둠)와 다르다** — 화면에 *뜨는데 틀린다*. 특히 credit은 [확인] 침묵 KR-garbage(§1). Slice1 처리(S1-L4.3): (a) `market!="KR"→None`/EXEMPT 가드 or (b) "계산 미검증·KR기준" 경고 배지. **EXEMPT 카운트와 별개 "계산 미정합" 분류로 노출** — 사용자가 "빈 화면(EXEMPT)"과 "틀린 숫자(회색지대)"를 가리게. credit 가드=필수. **`_DART_ONLY` allowlist가 이 4엔진을 비대칭 검사에서 제외**하므로 symmetry 게이트로 안 잡힘 → 별도 oracle 필요.

## 4. ★sector 결정 [정정 v0.4] — SIC-derived는 범위 안
- [확인] SIC가 EDGAR bulk에 존재(`datasetBulk.py:75`) → **SIC→US sector crosswalk(자체 공개 분류)는 본 PRD Slice2 범위**. rank=그 위 peer 백분위(scan-finance 재사용).
- **GICS만 범위 밖**(MSCI 라이선스, 재배포 불가=분류 D). "GICS 섹터"라 라벨 금지 — "SIC-derived sector"로 라벨.

## 5. Kill-List [정정 v0.4] (진짜 안 하는 것 — 채울 수 있는 건 채운다)
1. **가치사슬 *엣지* 합성** — major-customer 공시 없는데 supplier→customer 관계를 지어냄(FactSet식). 분류=SIC로, 엣지=공시 기반 부분만(저커버리지 라벨).
2. **GICS 섹터 사칭** — SIC-derived를 "GICS"라 라벨. (SIC sector 자체는 채움.)
3. **전임원 보수 사칭** — US=NEO5인데 "전임원"이라 표기. (NEO5는 채움.)
4. **재벌 계열 사칭** — Exhibit 21 자회사를 "한국식 계열사"라 표기. (자회사 네트워크는 채움.)
5. **ui/web EDGAR 배선** — 제거 예정.
6. **실시간/장중** — EOD/baked만.
7. **새 HF repo** — `eddmpython/dartlab-data` 단일.
8. **KR 경로 회귀** — market 기본 KR 불변.
9. **재배포 불가 데이터 baked** — GICS·라이선스 가격소스를 HF 공개.
10. **채울 수 있는데 안 채우는 게으름** [신설] — report 14·SIC sector·Exhibit21·shares XBRL을 "EXEMPT"로 퉁치기(운영자 챌린지 직접 대응).

## 6. 데이터 선결 점검표 (착수 전)
- [ ] `edgar/panel` native payload 보유율 실측(S0.1 ledger).
- [ ] `edgar/sections` 커버리지(docsIndex·changes·Item13 입력).
- [ ] XBRL 주식수 개념(`CommonStockSharesAuthorized/Issued/Outstanding`·`TreasuryStockShares`) companyfacts 실측(shares ~6col 복원 확인).
- [ ] report 14 추출기 실제 데이터 산출률(대표 N종목, apiType별 non-null).
- [ ] SIC 커버리지(전 종목 SIC 보유?) + SIC→sector crosswalk 설계.
- [ ] DEF 14A·Exhibit 21 파싱 PoC(executivePay NEO5·자회사 목록).
- [ ] US EOD 가격 재배포 라이선스 실조사(stooq/tiingo/nasdaq data link ToS).
