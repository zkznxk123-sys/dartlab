# 02. 아래→위 아키텍처 — 6층 누적 배선 모델

상태: **v0.3 (2026-06-22)** — R1·R2 정정. "순서대로 아래부터 쌓아나가는" 설계 골격. 각 층은 *아래 층의 산출물에만 의존*, 위 층은 아래 검증 전 진입 금지.

---

## 1. 누적 의존 그래프 (왜 이 순서인가)

```
L5 제품 배선        landing · ui/apps/local 시장 스위처
     ▲ (서피스가 시장 인지해야 제품이 스위치 가능)
L4 서피스 인지      terminal · viewer · scan · map  (US 렌더 + EXEMPT 정직)
     ▲ (포트가 US 데이터를 줘야 서피스가 그릴 게 있음)
L3 소스 분기        adapters/*/sources/*  (market → dart|edgar 경로)
     ▲ (계약에 market 차원이 있어야 소스가 분기 시그니처를 가짐)
L2 계약/런타임      contracts 6포트 + runtime marketDefault 스위처
     ▲ (라이브러리가 US를 계산해야 포트가 부를 게 있음)
L1 라이브러리 미러   dartlab.Company(ticker) 전 엔진 + 비대칭 baseline 가드(missing 5)
     ▲ (parquet이 있어야 라이브러리가 읽을 게 있음)
L0 빌드 (파케)      edgar/panel(backfill 로컬) + edgar/scan baking 결정 + tickers publish + US price(S2)
```

**불변식**: 위 층은 아래 층의 *검증된 산출물*만 소비한다. L3 소스가 `edgar/scan/changes.parquet`를 읽으려면 L0가 먼저 그 parquet을 HF에 올려야 한다. 따라서 빌드가 *맨 먼저*, 제품이 *맨 나중*. 이게 "아래부터 쌓는다"의 강제 구조다.

## 2. 재사용 우선 — 발명 금지

각 층은 *이미 있는 KR 메커니즘을 미러*하지 새로 발명하지 않는다(CLAUDE.md "데이터 빌드 = 공동작업대만, 별도빌드 금지" + "기존 자산 확인" 강행규칙).

| 층 | 재사용 대상 (KR SSOT) | 미러 방식 |
|---|---|---|
| L0 | `pipeline.stages.dartZip`·`buildScan`(kr) | `pipeline.stages.edgarPanel`(존재) + `scan/builders/edgar/*`(신설은 kr builder 미러) |
| L1 | `dartlab.Company` facade | `EdgarCompany`(존재, 표면 대부분 미러·비대칭 missing 5) — 갭·회색지대만 |
| L2 | `contracts/indexPort.ts`·`macro.ts`의 `market` 패턴 | 같은 패턴을 company/price/finance/filing/scan/report에 확장 |
| L3 | `data/origins/registry`·`data/fetch/request` | **무변경 재사용**. source만 market 분기(둘 다 `hf`/`hfRange`) |
| L4 | `runtimeContext`·surface 컴포넌트 | 시장 prop/context만 추가, 컴포넌트 골격 재사용 |
| L5 | `RuntimeEnvironment.marketDefault` | 이미 타입 존재 — 값 토글 + UI 스위처 |

## 3. ★L0 가격 소스 결정 (빈 구간 — 별도 설계 필요)

KR은 `gov/prices`(공공데이터 KOGL)를 baked parquet로 빌드해 퍼블릭 floor를 만든다. US는 현재 `gather("price","AAPL")`가 **라이브 yfinance**만 — baked 미빌드라 퍼블릭 셸에 가격 floor가 없다. 옵션:

| 옵션 | 설명 | 장 | 단 |
|---|---|---|---|
| **A. US baked 가격 빌드** | `edgar/prices/...` parquet을 CI에서 빌드(yfinance/stooq 등) → HF | KR과 완전 동형 배선(퍼블릭 floor) | 라이선스·소스 안정성 검토 필요. 새 워크플로 |
| **B. 워커 프록시 라이브** | news/naver처럼 CF 워커로 가격 라이브 fetch | 빌드 0 | 퍼블릭 floor 약함(라이브 의존)·KR과 비동형 |
| **C. 가격 패널 US 미지원** | 터미널 가격 차트만 US에서 비활성, 나머지(panel/finance/scan) 배선 | 범위 축소 | "동일 배선" 목표 미달 |

**[정정] 결정 = 슬라이스로 분리.** A(baked)가 *동일 배선* 목표엔 정합이나 라이선스(yfinance ToS 재배포 회색·stooq EOD)+새 워크플로로 **L0 최난도 미결정** → S0를 인질로 잡음. 따라서 **Slice 1 = 옵션 C(가격 US 비활성, 정직 빈)로 출발**, A(가격 baked)는 **Slice 2 S2-L0.3**에서 라이선스 실조사 후. 03 슬라이스 구조 참조.

## 3.5. ★scan baking 모델 — KR(baked) vs EDGAR(라이브) [정정]

[확인] KR scan은 `dart/scan/*`에 **사전계산 baked parquet**(`scan/builders/kr/core.py`), EDGAR scan은 `_edgarDispatch`(`router.py:289-334`)가 11 XBRL축을 **호출시점 라이브 계산**(baked는 `edgar/scan/finance.parquet` 1종뿐). v0.1 "scan 1/8 미러"는 *아키텍처 오인* — 두 모델이 다르다. 퍼블릭 셸이 HF 직독(`:8400` 없이)이면 브라우저가 per-CIK parquet 수백 개를 라이브 계산하기 불가 → **퍼블릭 floor를 지키려면 EDGAR scan도 baked로 통일**이 사실상 강제. 이 결정(S2-L0.1)이 라이브러리 dispatch 코드 변경 범위(라이브→parquet read)까지 정한다.

## 4. ★시장 라우팅의 단일 진입점 (priority-비대칭, [정정])

**[확인] 라이브러리 라우팅은 식별자 *모양*이 아니라 provider *priority* 기반이다.** `edgar/company.py:616` canHandle은 `s.isdigit() and len(s)<=10`이면 True → 6자리 KR코드도 EDGAR가 True를 반환하고, 분기는 priority(dart<edgar=20)가 결정(docstring이 "6자리도 True, dart가 먼저 매칭 의무"라 자인). 따라서 프론트가 *순수 식별자 함수* `resolveMarket(id):'KR'|'US'`로 미러하면 6자리 숫자 CIK(예 Apple=320193)와 KR 6자리코드를 모양만으로 못 가른다 → 오라우팅.

- **resolveMarket = priority-비대칭 규칙**: ① **명시 market override 1순위**(사용자/`marketDefault`). ② 자동판정: 6자리 숫자→KR, 영문 ticker 1-5자→US, **숫자 CIK는 명시 market 필수**(KR코드와 모양 충돌). 라이브러리를 "베끼지" 말고 라우팅 *계약*을 L1 SSOT(상수/codegen)로 import해 drift 차단.
- 한 곳(`runtime`/`contracts`)에 두고 모든 source/surface가 호출. **resolveMarket은 L2 계약 1순위 산출물.**

## 5. 캐시·dedup·origins 무변경 증명

[확인] L3 소스가 `edgar/...` 경로를 `request({origin:'hfRange', path:'edgar/finance/...'})`로 부르면, `data/fetch/request.ts`의 캐시 버킷(`${origin}:${path}` 키)·dedup·fetchResilient가 *그대로* 동작하고, origins `hf`/`hfRange`(`hfUrl`/`hfRangeUrl`)는 base URL만 resolve하므로 `edgar/...` prefix를 추가 등록 없이 처리한다. `checkUiDataWiring.mjs`도 상대경로 `edgar/...`는 URL 리터럴이 아니라 미트리거. **즉 공통배선 코어는 시장 추가에 손댈 필요가 없다 — "동일 배선"이 구조적으로 성립하는 근거.** 손대는 건 source의 *경로 조립*과 계약 *시그니처*뿐.

**[정정] 단, 두 예외**: ① map의 `industryPoolSource`는 origins가 아니라 `loadJson`(dartlabData) **별도 sibling arm**(registry.ts:5-7 명시) → origins 무변경 증명 범위 밖, map US=비호출이 맞음. ② viewer 로컬 panel은 `/api/company/{code}/panel` **Python 백엔드 라우트** → 백엔드도 market 인지 필요(L3 범위 확장).

## 6. 무회귀 원칙 (KR = 기본값)

모든 층에서 `market` 미지정 시 기본값 `'KR'`. 따라서 US 배선을 *추가*해도 KR 호출 경로는 바이트 단위 불변. 회귀 가드:
- L2~L4 각 포트/소스/서피스에 "market 기본 KR" 단위 테스트.
- `checkUiDataWiring.mjs` baseline 무증가(US source 추가가 raw fetch·하드코딩 URL 신설 0).
- KR 제품 시각 회귀 = 운영자 눈검수(UI push 승인 게이트).
