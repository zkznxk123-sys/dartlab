# 04. 데이터 레디니스 + EXEMPT 경계 + Kill-List

상태: **v0.3 (2026-06-22)** — R1·R2 정정. "완전히 같이 배선"의 *데이터 현실*을 정직하게 박는다. 미러 가능(데이터 있음)·EXEMPT(없음)·회색지대(호출되나 KR가정)·kill(안 함).

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
| analysis/quant/story | XBRL·yfinance·FRED | ⚠ 표면 미러 / 계산 KR가정(`_revenueSelect.py:110`=정직 None) |
| **credit** | XBRL leverage/cashflow | ⛔ [확인] **침묵 KR-garbage**(market 가드 0, `sector None→_defaultThresholds()` KR → US 숫자 non-None 가짜 등급). Slice1 가드 필수(S1-L4.3) |
| ticker↔CIK 매핑 | `edgar/tickers` [확인] **DATA_RELEASES 미등록** | ⬜ HF publish(S0.2) |
| search (공시 본문) | `edgarPanel` 검색 카탈로그 | [보고] 통합 BM25 live |
| 가격 | C(비활성, Slice 1) / A(`edgar/prices` baked, S2-L0.3 라이선스) | ⬜ Slice 분리 |

## 2. EXEMPT — 영구 (US 동등 데이터 구조적 부재)

| 표면 | EXEMPT 사유 | 정직 처리 |
|---|---|---|
| `industry()` 가치사슬 지도 | KR 운영자 수동 큐레이션 + 한국 산업정의 + KR peer. US 가치사슬 지도 부재. | map surface US면 "미국 시장 미제공". 발명 금지. |
| `sector`/WICS 11분류 | KR 거래소 분류체계. | US 섹터 칩 비활성 or GICS 별도결정(§4). |
| `rank`/섹터내 peer 랭킹 | US peer 유니버스 정의 부재. | US 랭킹 패널 비활성. |
| `network`/계열사 그래프 | 한국 계열사(지배구조) 공시 기반. US 13F는 *개념 상이*. | US 비활성. |
| `topicSummaries` | KR 공시 item 분류 의존. | US 비활성. |
| DART OpenAPI `report` **17 apiType** ([정정] 메서드 `report()`는 미러됨) | SEC 폼 구조 상이(`scan/report/*`). | scan US에서 report 축 비활성. |

**EXEMPT 처리 철학(00 §1.1 재확인)**: EXEMPT는 *배선이 없는 게 아니라*, 배선은 시장 차원을 타되 US 분기에서 *정직하게 빈* 것. "데이터 없음"을 표면화하는 것이 본 PRD의 합격 조건. 가짜 채움 = 전체 실패.

## 3. EXEMPT 2태그 — permanent vs dataWaiting ([정정] 비대칭 baseline 정합)

[확인] `_baselines/providerSymmetry.json` missing 5건 = `executivePay`·`flow`·`notesDetail`·`relatedPartyTx`·`simulate`(EDGAR 메서드 부재). 비대칭 가드(`providerSymmetry.py`)가 이를 태그로 구분해야 파서 구현 시 게이트가 풀린다.

| 항목 | 태그 | 데이터로 가능? | 본 PRD 처리 |
|---|---|---|---|
| `industry`/`sector`/`sectorParams`/`rank`/`network`/`topicSummaries`/report17 | **permanent** | US 동등 데이터 부재(SIC/GICS 유추는 *새 US 엔진*) | **범위 밖**(별도 goal) — "동일 배선"≠"새 US 산업엔진" |
| `executivePay` | **dataWaiting** | [정정] US=**DEF 14A NEO5**(10-K item11 아님)·KR 전원공개와 구조 비동등 | **범위 밖/선택**(파서=기능추가) |
| `relatedPartyTx` | **dataWaiting** | US=10-K notes(ASC 850) | **범위 밖/선택** |
| `notesDetail`·`flow`·`simulate` | **dataWaiting/permanent 혼재** | notesDetail=XBRL 일부 가능·flow/simulate=KR 고유 | **범위 밖** — baseline 명시 유지(strict 0 미래목표) |

**판정 원칙**: 본 PRD는 *배선 통일*이다. EXEMPT를 채우는 것(새 US 데이터 엔진 구축)은 별도 goal. 혼입하면 범위 폭발 → "동일 배선"이 영원히 안 끝남. EXEMPT는 *정직하게 비우는 배선*까지가 본 PRD.

> [정정] **2태그는 현재 코드에 없음** — `providerSymmetry.json`은 평면 `missing[]` + 코드 상수 `_DART_ONLY`(permanent만)/`_EDINET_DEFERRED`뿐. permanent/dataWaiting 구분은 *구현 작업*(baseline JSON에 키 분리 or `_SYMMETRY_MAP` 태그 dict). "설계 의도"이지 "현존 구조" 아님.

### 3.5 ★회색지대 — EXEMPT도 정상도 아닌 제3 분류 ([확인] R2 P0)
analysis/credit/quant/story는 *호출은 되나 계산이 KR 가정*. **EXEMPT(비활성·정직 빈)와 다르다** — 화면에 *뜨는데 틀린다*. 특히 credit은 [확인] 침묵 KR-garbage(§1). Slice1 처리(S1-L4.3): (a) `market!="KR"→None`/EXEMPT 가드 or (b) "계산 미검증·KR기준" 경고 배지. **EXEMPT 카운트와 별개 "계산 미정합" 분류로 노출** — 사용자가 "빈 화면(EXEMPT)"과 "틀린 숫자(회색지대)"를 가리게. credit 가드=필수. **`_DART_ONLY` allowlist가 이 4엔진을 비대칭 검사에서 제외**하므로 symmetry 게이트로 안 잡힘 → 별도 oracle 필요.

## 4. ★sector/GICS 결정 (패널 평가 쟁점)
- "US도 scan에서 섹터별 비교가 되게 하라"는 압력이 있을 수 있으나, GICS는 라이선스(MSCI) 이슈 + WICS와 경제적 비동등. SIC는 공개지만 조악.
- **잠정**: 본 PRD 범위 밖. scan US는 *시장 전체* 백분위(섹터 무관)까지만. 섹터 분류는 별도 PRD. — 패널이 반박하면 재고.

## 5. Kill-List (명시적으로 안 함)
1. **US 가치사슬 지도 발명** — industry 엔진 US 복제(SIC 유추). 별도 goal.
2. **US 섹터/peer 랭킹 발명** — GICS/13F 기반 합성. 별도 goal.
3. **DART report 17종 US 강제 매핑** — 폼 구조 상이로 1:1 불가.
4. **ui/web EDGAR 배선** — 제거 예정.
5. **실시간/장중 US 데이터** — EOD/baked만.
6. **새 HF repo** — `eddmpython/dartlab-data` 단일에 `edgar/...`.
7. **KR 경로 회귀** — market 기본값 KR 불변. US 추가가 KR 변경 0.
8. **EXEMPT 가짜 채움** — US 빈 패널을 KR 데이터·placeholder로 메움.

## 6. 데이터 선결 점검표 (L0 진입 전)
- [ ] `edgar/panel` native payload 보유율 실측(L0.0).
- [ ] `edgar/sections` 커버리지(docsIndex 입력).
- [ ] `sharesOutstanding` XBRL 필드(`dei:EntityCommonStockSharesOutstanding`) 추출 가능성.
- [ ] US 가격 소스 라이선스·갱신주기(옵션 A 채택 시).
- [ ] `edgar/scan/finance.parquet` 종목 커버리지(scan 유니버스 크기).
