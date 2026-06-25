# 00. Product PRD — EDGAR 동일 배선 (KR Parity Wiring)

상태: **v0.4 (2026-06-22)** — R1·R2 패널 + ★운영자 챌린지("없는 데이터 어떻게 해결") 대응. 결측 데이터 항목별 해결책 = `08-missing-data-resolution.md`. 평가기록 07.

> SSOT 폴더: `mainPlan/edgar-parity-wiring/`. 메모리는 포인터만. 본 PRD는 *아래→위* 누적 설계 — 빌드(파케)부터 시작해 scan·라이브러리·계약/런타임·소스·서피스·제품 순으로 한 층씩 쌓는다. 각 층은 아래 층이 완성돼야 진입한다.

---

## 1. 제품 정의 — "동일 배선"의 정확한 의미

**목표 = 미국 EDGAR 종목을 한국 DART 종목과 *완전히 같은 데이터 배선*으로 모든 프론트 제품(터미널·뷰어·스캔·맵·리포트)과 로컬 UI 제품에서 다룬다.** `ui/web`(리액트판)은 제거 예정이라 범위 밖.

"동일 배선"은 **capability 동일(100% 기능 일치)이 아니라 *메커니즘·경로·포트·소스·서피스의 동일*** 을 뜻한다. 정확히:

- **같은 빌드 메커니즘** — `dartlab.pipeline` 동일 stage 구조로 `edgar/...` parquet을 KR `dart/...`/`gov/...`와 같은 형태로 빌드·HF 업로드.
- **같은 라이브러리 표면** — `dartlab.Company(ticker)`가 `Company(code)`와 동일 시그니처. 표면 대부분 미러됨([확인] 비대칭 baseline missing 5건, P-PR 트랙)이나 **계산이 KR 가정인 회색지대(analysis/credit/quant/story)·비대칭 5건 잔존** — "동일 배선"은 *표면·경로*이지 *계산 정합* 아님(03 S1-L4.3). 기존 `project_edgar_dart_parity`(✅)가 L1을 이미 실행 — 본 PRD 신규 = L2~L5 프론트 배선.
- **같은 데이터 포트·소스 코어** — `data/origins/registry` + `data/fetch/request` 공통배선을 그대로 타고, source 레이어가 `market`으로 `dart/...`↔`edgar/...` 경로를 분기.
- **같은 서피스** — terminal/viewer/scan/map 같은 Svelte surface가 KR/US를 모두 렌더. 시장 고유로 데이터가 없는 패널(EXEMPT)은 *있는 그대로 비우거나 숨긴다*(가짜 채움 금지).

### 1.1 ★결측 데이터 처리 원칙 (v0.4: 결측은 *대부분 채운다* — 운영자 챌린지 대응)

[정정 v0.4] v0.3는 결측을 "비운다"로 *회피*만 했으나, 직접 코드검증 결과 **대부분 채울 수 있다**(상세 `08-missing-data-resolution.md`): EDGAR가 KR report 17 중 **14 apiType 이미 추출**(`reportAccessor._SUPPORTED`), SIC·자기주식·executivePay 추출기 보유. 진짜 못 채우는 소수(가치사슬 *엣지*·전임원 보수·GICS·US 가격 라이선스)에만 "비운다" 적용. **"채울 수 있는데 안 채우는 게으름"도 실패**(04 §5).

아래 표는 *구조적으로 다른* 잔여 + 채운 데이터의 라벨 원칙. "100% parity" 주장 금지는 유지:

| 분류 | 항목 | 처리 원칙 |
|---|---|---|
| **채울 수 있음 [정정 v0.4]** (08 상세) | `report` 14 apiType(추출기 有)·`sector`/`rank`(SIC bulk)·`sharesOutstanding`(XBRL ~6col)·`network`(Exhibit21·13D/F)·`relatedPartyTx`(10-K Item13) | **채운다**(Slice 2). US 출처 라벨(SIC-derived·Exhibit21), KR 등가 주장 금지. |
| **진짜 잔여 (D/구조차)** — 비움 | `industry` 가치사슬 *엣지*(공급망)·`executivePay` 전임원(US=NEO5)·GICS sector·US 가격(라이선스) | 채울 수 있는 부분만(분류=SIC, 보수=NEO5) + 커버리지/한계 라벨. 합성·사칭 금지(04 §5). |
| **표면 미러 / 계산 KR가정** | analysis · credit · quant · story | 호출되나 KR 계정명·WICS·KR `industry()` 의존([확인] `_revenueSelect.py:110`; **credit 침묵 KR-garbage**). Slice1 가드 필수(S1-L4.3). |
| **표면+데이터 미러** | panel · finance · **scan-finance(baked)** · macro · search · `report()`·`notes()` | 빌드·소스·서피스 배선만 통일(Slice 1). ⚠ scan 라이브 13축은 Python 전용 → 퍼블릭은 S2 baking 후. |

**따라서 본 PRD의 합격선은 "US가 KR과 같은 기능을 다 한다"가 아니라 "US가 KR과 같은 *배선*을 타고, 없는 것은 명시하고 비운다"이다.** 이 한계 표기 원칙이 깨지면(EXEMPT를 가짜로 채우거나, KR 계산가정으로 US를 계산해 garbage를 "미러"라 부르면) 전체 실패로 본다.

## 2. 사용자 · 사용 맥락

- **1차 타깃**: 한국 종목을 dartlab 터미널/뷰어/스캔/맵으로 분석하던 사용자가 *동일한 화면·동일한 조작*으로 미국 종목(AAPL·MSFT 등)을 분석. 새 제품을 배우지 않는다 — 같은 제품에 시장 스위치만.
- **2차 타깃**: 미국 종목만 보는 사용자. KR 제품의 성숙도를 그대로 US에 적용받음(공시 수평화 panel·재무 scan·신용·퀀트).
- **로컬 사용자**: `ui/apps/local`(:5174) + `:8400` Python API로 무거운 EDGAR 계산(전종목 scan·companyfacts 벌크)을 로컬에서. 퍼블릭(`landing`)은 HF baked parquet 직독으로 floor 보장.
- **사용 맥락**: landing/`:5173`(퍼블릭 셸)·ui/apps/local/`:5174`(로컬 셸) 둘 다 동일 surface 호스팅. 시장 선택은 `RuntimeEnvironment.marketDefault`(이미 `'KR'|'US'` 타입 존재, 현재 항상 `'KR'`) + 종목 식별자(6자리코드↔ticker)로 결정.

## 3. 목표 종착 (전체 그림 — 단계는 여기로 진입)

1. **빌드 동등**: `edgar/panel`(빌드경로 완성·backfill 실측 선결) + scan **baking 모델 통일 결정**([확인] KR=baked / EDGAR=라이브 → 퍼블릭 floor 위해 baked 통일) + 가능한 보조축(docsIndex 재배선·changes 개념검증·shares 부분 EXEMPT). US 가격 baked 소스(라이선스 선결).
2. **라이브러리 동등**: 모든 엔진이 `market="us"`/ticker 입력을 받거나 EXEMPT로 *명시 선언*. [확인] 비대칭 baseline(`providerSymmetry.py`) 무증가 — 현 missing 5건, strict 0은 미래목표. 회색지대 4엔진은 계산정합 별도 트랙(Slice1 가드 선제).
3. **계약/런타임 시장 차원**: `CompanyPort`·`PricePort`·`FinancePort`·`FilingPort`·`ScanPort`·`ReportPort`에 `market` 차원 추가(이미 IndexPort·MacroPort에 있는 패턴 확장). `marketDefault` 스위처 활성.
4. **소스 분기**: 각 `adapters/*/sources/*`가 `market`으로 `dart/...`↔`edgar/...` HF 경로를 분기. origins registry는 무변경(둘 다 `hf`/`hfRange` 오리진).
5. **서피스 시장 인지**: terminal/viewer/scan/map이 KR/US를 모두 렌더. EXEMPT 패널 명시 표기. 식별자(ticker/CIK vs 6자리코드) 분기.
6. **제품 배선**: landing + ui/apps/local에 시장 스위처. 모든 프론트·로컬 제품이 EDGAR도 동일하게 동작.

## 4. 성공 지표 (KPI 수가 아니라 배선·한계 검증)

- **배선 동일성**: 동일 사용자 조작(예: 종목 진입→panel→finance→scan)이 KR/US에서 *같은 포트·같은 source 코어·같은 캐시 경로*를 탄다. `checkUiDataWiring.mjs`류 감사가 US 경로 추가 후에도 위반 0.
- **한계 표기 0 위반**: EXEMPT(industry/sector/rank/network) 패널이 US에서 *가짜로 채워지지 않는다*. grep 게이트로 "US industry map"·"US peer rank" 같은 발명 표면 0건.
- **빌드 parity**: `edgar/scan/*` 산출물이 KR과 동일 형태(스키마·갱신 주기)로 HF에 존재. 자동 freshness 추적.
- **비대칭 baseline 무증가 → strict 축소**: [확인] `providerSymmetry.py` baseline 원장에 현재 missing 5건(P-PR 트랙). 합격=baseline 무증가 + missing을 파서 구현/명시 EXEMPT로 축소(P-PR8 종료=strict 0). 신규 KR 기능 추가 시 US 미러 or EXEMPT 강제. **"비대칭 0"은 현재 사실이 아님 — 미래 목표.**
- **제품 무회귀**: US 배선 추가가 KR 제품을 회귀시키지 않는다(KR이 기본값이라 default 경로 불변).
- **로컬↔퍼블릭 동등**: US도 KR처럼 퍼블릭(`:8400` 없이)에서 baked parquet floor가 뜨고, 로컬은 상위집합.

## 5. 비목표 (명시 제외)

- **`ui/web`(리액트판) EDGAR 배선** — 제거 예정. 손대지 않는다.
- **[정정 v0.4] 데이터 합성·사칭** — *발명*(없는 가치사슬 엣지 지어냄)·*사칭*(SIC를 "GICS", NEO5를 "전임원", Exhibit21을 "재벌 계열"이라 라벨)만 금지. **출처가 있는 건 채운다**(report 14·SIC sector·Exhibit21·shares XBRL = Slice 2, 08). v0.3의 "EXEMPT=별도 goal" 회피는 챌린지로 철회.
- **실시간/장중 데이터** — US도 KR과 같이 EOD/baked 기준.
- **DART OpenAPI report 17종 *전부* 1:1** — EDGAR가 14 apiType 이미 추출(08), 나머지 3(auditContract 등)은 DEF14A 파서로 보강. 구조 다른 소수만 부분.
- **"세계 최초/기관급/완전 동일" 무수식 표현** — 한계 항목이 있으므로 parity는 *배선* 한정. never-claim §05.
- **새 데이터셋 repo 신설** — `eddmpython/dartlab-data` 단일 HF에 `edgar/...` 그대로(이미 존재).
