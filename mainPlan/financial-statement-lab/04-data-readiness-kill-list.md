# 04. 데이터 준비도와 킬리스트

상태: 비전 PRD v0.1 (2026-06-13)
목적: 매력적이지만 *데이터에서 죽는* 기능을 명시 차단한다. "나중에 Phase N"으로 흐리지 않고 EXCLUDED/BLOCKED/CONDITIONAL로 박는다. 데이터 없으면 카드 없음.

---

## 1. 데이터 가용성 매트릭스

| 기능 | 소스 | 가용성 | 판정 |
|---|---|---|---|
| 지수 리베이스 | `dart/finance/{code}.parquet` | 완비 | ✅ MUST |
| 기간모드(분기/연간/TTM) | 동 | 완비 | ✅ MUST |
| 운전자본 회전일수 split | 동(채권·재고·매입채무·매출) | 완비 | ✅ MUST |
| 이익품질 플래그(CFO/NI·accruals·tie-out) | 동(IS/BS/CF) | 완비 | ✅ SHOULD |
| 동종 백분위 밴딩 | panel + `compare` | 완비(엔진) | ✅ SHOULD (분포 prebuild) |
| 가격↔기초체력 지수 | `gov/prices/company/{code}` × panel | **2020+ 만** | ⚠ CONDITIONAL |
| PER/PBR 시계열 | 가격 × 발행주식수 × 순익/자본 | **조인 정합 필요** | ⚠ CONDITIONAL (§4) |
| reverseDCF 함축 기대 | reverseDCF 엔진 + panel | 완비(엔진) | ✅ SHOULD (가드레일) |
| 공시 큐레이션 by type | `regular/nonRegularFilingsSource` | 있음 | ✅ SHOULD (경계정리) |
| R&D 추이 | panel 주석 2-tier | 6/10 | ⏳ DEFER (Python 게이트) |
| 세그먼트/지역별 | panel `NT_D871100` 다축 | **2/10 clean** | ⛔ CONDITIONAL-BLOCKED |
| 수출 회사매핑 | 관세청 customs | **전국 집계** | ⛔ EXCLUDED |
| 수주잔고 | 주석 단편 | **정량 표면 부재** | ⛔ BLOCKED |
| 애널리스트 컨센서스·목표주가 | — | **소스 없음** | ⛔ EXCLUDED |
| 금융업 전용 카드(은행/보험/증권) | panel 금융계정 | label drift | ⛔ WON'T(본 PRD) |

---

## 2. EXCLUDED (소스 자체가 없음 — PRD에서 삭제, Phase 아님)

- **애널리스트 컨센서스 / 목표주가 / 실적 추정.** DART·EDGAR·gov 어디에도 없다. "consensus" 카드는 저작권 3자 데이터 스크래핑을 요구 → 환각·법적 리스크. **하드 노.** Butler가 표준처럼 보이게 만들기 때문에 가장 지키기 어려운 선 — *DART/EDGAR/gov에 없으면 화면에 없다, 끝.*
- **수출 회사매핑.** 관세청 customs는 HS코드별 *전국 집계*지 회사 귀속이 아니다(메모리 `project_gather_dataportal_customs_pension`). 회사로 조인하면 우리가 못 접지하는 *추론*. 단, 산업/거시 *맥락*으로 "이 회사 HS 섹터 수출 추이"를 *동종 산업 신호*로 보여주는 건 별개(회사 귀속 주장 안 함) — 그건 macro/industry surface지 재무 카드 아님.

## 3. BLOCKED (표면 부재 — 별도 _attempts 프로젝트 선행 후에만)

- **수주잔고.** 표준 정량 표면 없음. 건설/조선 일부 주석만. 회사 간 일관성 없고 sparse → 카드로 만들면 *조용히 오도*. 메모리 `project_terminal_chart_audit`의 [불가능] 버킷. 파싱 coverage 입증이 *별도* attempts-gate 프로젝트지 이 PRD 라인이 아님.

## 4. CONDITIONAL — PER/PBR 시계열 조인 정합 (핵심 압박)

PER/PBR *시계열*은 매력적이지만 조인이 더럽다:
- **종가**: gov 주가 = T+1·**2020+ 만**, pre-2020은 krx-legacy 잔존(메모리 `project_gov_price_migration`). → 시계열 시작점 2020.
- **발행주식수**: 기간별 주식수가 필요(자사주 차감 정합 포함). `reportSource`의 `OwnershipYear.stockTotal`에 *연 단위*는 있으나 분기 정합·자사주 vintage 정렬이 "확신 오정렬 > 정렬 실패" 위험(panel 룰 경고).
- **순익/자본**: panel에 완비(TTM·BS 시점값).

**판정**: PER/PBR 시계열은 **post-2020·연 단위·주식수 정합 검증된 회사만**, "2020~"·"as-of" 라벨 명시 + coverage 게이트. 분기 단위·pre-2020·주식수 미정합 → 카드 미생성(스냅샷 PER/PBR은 기존 `valuationOf` 유지). **clean 조인 안 되면 카드 없음.**

## 5. CONDITIONAL-BLOCKED — 세그먼트 (2/10)

세그먼트는 panel에 *존재*하나 XBRL 인코딩이 가른다(메모리 `project_segment_rnd_extraction`): **축-태깅 고신뢰 소수(axis-tagged) vs 행-라벨 저신뢰 다수.** clean 2/10. 8/10에서 빈칸·쓰레기를 내면 *신뢰성 킬*. **판정**: 세그먼트 카드는 *확정 산출물 아님* — 별도 `_attempts/segmentRndExtraction` 프로젝트가 축-태깅 경로(2/10)만 부분 출시하거나 인코딩 census 선행. 이 PRD는 세그먼트를 *약속하지 않는다.*

## 6. WON'T(본 PRD) — 금융업 전용 카드

iTooza는 은행/보험/증권에 *별도 card set*을 유지한다 — 계정 라벨이 안 맞아서다. label-drift 유지비 高, audience 小(금융명 소수). v1 제외. *금융명 사용자 pull이 입증되면* 별 트랙으로 재방문. 단, **업종 인지 *필터*(금융명에서 제조형 카드 숨김)는 MUST** — 그건 추가가 아니라 *제거*다.

---

## 7. honest-gap 상태 규칙 (결손 표현 SSOT)

- 카드 전 series null → 자동 제거(`alive`). 사용자에게 빈 카드 안 보임.
- 카드 부분 결손(일부 기간/일부 계정) → **honest-gap**: 해당 점 pen-up(null=선 끊김), "이 구간 공시 부재" 캡션. 0 대체 금지.
- universe 너무 작아 백분위 못 냄(<N사) → 백분위 배지 미표시 + "동종 표본 부족" 라벨.
- CONDITIONAL 기능이 게이트 미통과(예: 주식수 미정합) → 카드 미생성, 토글에 비활성 + 사유.
- 모든 결손은 missing/blocked/partial/notApplicable 중 하나로 *명시* — "왜 비어있나"를 사용자가 안다.
