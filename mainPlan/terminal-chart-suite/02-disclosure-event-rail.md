# 02. Disclosure Event Rail — /terminal 공시 위치 찾기 레일

> **참조 규약(분리 후):** 본 문서는 `mainPlan/terminal-chart-suite/`(현재/과거 차트 suite)에 속한다. suite 내부 = 01(차트)/02(레일)/03(백테스팅). **시뮬 PRD 참조(바 번호 05·07·08·09 등)는 `../scenario-simulator/NN`을 가리킨다**(단방향: suite ⟶ 시뮬, 역참조 없음).

상태: PRD v0.2 (메모리 `project_terminal_disclosure_event_rail_prd`에서 repo 이관 — terminal-chart-suite 컴포넌트)
지위: 차트 suite의 이벤트레일 컴포넌트. 통합 시퀀스(시뮬 07 통합로드맵: 지수→**이벤트레일**→백테스팅→시뮬)에서 2번. 본 PRD는 *과거 공시 위치 찾기*만 완결. **미래 공시 마커(예측 정기공시 점선)는 시뮬 코어(미래 캔버스)에 의존 → 시뮬 트랙(4)으로 이관**(시뮬 07 §의존성). ⚠**UI 경로 전수 stale — 기계적 매핑 강행**: 본문의 *모든* `landing/src/lib/terminal/<rest>`(본문 :49-51 `panels/CenterStack`·`charts/PriceChart`·`charts/chartState.svelte.ts`·:60 `panels/RightStack`·:66 `data/workbench.ts`·:68 `panels/ViewerOverlay`·:324·:366 `data/disclosureEvents.ts`·:370 `charts/DisclosureEventRail.svelte` 등)를 `ui/packages/surfaces/src/terminal/<rest>` 로 1:1 치환해 읽는다(터미널 전체 이동, commit ff9099ba0, 04 §3). 포트=`ui/packages/contracts`. 엔진 경로(`src/dartlab/*`)는 불변. `ui/shared/chart/PriceChart.svelte`(별개 SVG)와 혼동 금지.

## 0. 판정과 최종 결론

사용자 요구는 명확하고 타당하다. DartLab의 정체성은 "공시 원천을 구조화해 가격·재무·텍스트와 함께 읽는 것"이므로, 메인 주가차트에 공시 발생일을 얹는 기능은 장식이 아니라 `/terminal`의 핵심 제품 방향이다.

단, 제품 언어는 반드시 **공시 위치 찾기 레일**이어야 한다. 이 기능은 "공시가 주가를 설명한다"가 아니라, 가격 타임라인 위에서 DART 원문 공시의 제출 위치를 찾아주는 도구다. `호재`, `악재`, `영향`, `원인`, `반응`, `이 공시 때문에 올랐다/내렸다` 같은 인과·투자 신호 언어는 UI·툴팁·테스트 fixture·문서 어디에도 쓰지 않는다.

최종 제품 결론:

- 메인 주가차트 하단, x축 바로 아래에 **공시 이벤트 레일**을 둔다.
- 정기공시(`dart/panel/{code}.parquet`)와 비정기공시(`dart/allFilings/recent.parquet`)를 같은 `DisclosureEvent` 계약으로 정규화한다.
- 날짜별로 원을 찍고, 같은 날짜에 여러 공시가 있으면 점 하나에 count 배지를 둔다.
- 호버는 간단한 툴팁만 보여준다.
- 점 클릭은 기본적으로 **우측 공시 패널을 해당 공시로 스크롤 + 하이라이트**한다.
- 같은 날짜 공시가 여러 개면 작은 팝오버를 열고, 항목 선택 시 우측 패널 스크롤 + 하이라이트한다.
- 원문 이동은 팝오버/우측 행의 `↗` 링크가 맡는다. 점 클릭 자체가 외부 링크로 바로 나가면 차트 탐색 흐름이 끊기므로 금지한다.

큰 모달은 기각한다. 이 기능은 "차트에서 날짜 맥락을 잡고 우측 공시 패널로 원문 목록을 찾는" 흐름이어야 한다. 모달은 차트를 가리고, 기존 `ViewerOverlay`와 역할이 겹치며, terminal의 고밀도 3열 구조를 깨뜨린다.

## 1. 제품 목적

### 1.1 사용자 문제

현재 `/terminal`은 메인 차트, 정기공시 목록, 비정기공시 목록을 모두 갖고 있지만, 사용자는 가격 급등락 날짜와 공시 제출일을 직접 눈으로 맞춰야 한다. 공시가 원천인 프로젝트인데, 가격 타임라인과 공시 타임라인이 시각적으로 분리되어 있다.

### 1.2 목표 경험

사용자는 주가차트를 보다가 특정 날짜 아래 점을 보고 "그날 이 회사에 무슨 공시가 있었는지" 즉시 확인한다. 점 위에 마우스를 올리면 공시 제목이 보이고, 클릭하면 우측 패널의 해당 공시 행으로 이동한다. 더 깊게 보고 싶으면 그 행 또는 팝오버에서 DART 원문을 연다.

### 1.3 제품 원칙

1. 차트는 가격과 이벤트의 시간 위치를 보여준다.
2. 우측 패널은 공시 목록 탐색과 원문 링크를 책임진다.
3. 공시 이벤트는 투자 신호가 아니라 원천 데이터의 발생 위치다.
4. 가격축을 왜곡하지 않는다. 공시 점은 별도 레일에 표시한다.
5. 정기공시와 비정기공시는 같은 점 체계로 보이되, 색·라벨로 구분한다.
6. 같은 날짜 다중 공시는 점 여러 개가 아니라 count 배지 하나로 접는다.
7. 없는 데이터를 포장하지 않는다. allFilings recent 범위 밖은 "최근 비정기공시 범위"로 정직하게 표시한다.

## 2. 현재 자산과 구현 경계

### 2.1 이미 있는 자산

- 중앙 차트:
  - `landing/src/lib/terminal/panels/CenterStack.svelte`
  - `landing/src/lib/terminal/charts/PriceChart.svelte`
  - `landing/src/lib/terminal/charts/chartState.svelte.ts`
- 차트 표시 설정:
  - `ChartCtl.showEvents`
  - `ChartMenus.svelte`의 "표시 > 마커 > 실적 발표"
  - `ChartRibbon.svelte`의 `실적(EARN)` 토글
- 기존 이벤트 overlay:
  - `PriceChart.svelte`의 `events?: { date: string; label: string }[]`
  - 실적 발표/증자·감자 이벤트를 `simpleAnnotation`으로 캔들 고가에 표시
- 우측 공시 패널:
  - `landing/src/lib/terminal/panels/RightStack.svelte`
  - 정기공시 섹션 `regFilings`
  - 비정기공시 섹션 `nonRegFilings`
- 공시 로더:
  - `landing/src/lib/data/companyFilingsRuntime.ts`
  - `landing/src/lib/data/companyNonRegularFilings.ts`
  - `landing/src/lib/terminal/data/workbench.ts`
- 공시뷰어 오버레이:
  - `landing/src/lib/terminal/panels/ViewerOverlay.svelte`
  - 정기공시 패널의 `⤢` 버튼이 viewer를 연다.

### 2.2 중요한 판정

기존 `PriceChart.events`는 유지하되 이번 기능의 본체로 쓰지 않는다. 기존 이벤트는 캔들 위 `simpleAnnotation`이고, 재무 실적/증자 이벤트 성격이다. 이번 기능은 가격축과 분리된 **하단 공시 레일**이므로 별도 타입과 렌더러가 필요하다. `simpleAnnotation` 재사용은 금지한다. 정기공시+allFilings를 고가 위치 텍스트 라벨로 뿌리면 캔들을 가리고, 가격축 의미를 흐린다.

기존 `showEvents`는 "실적 발표 마커" 의미로 남긴다. 새 기능은 `showDisclosureEvents` 또는 `showFilings` 성격의 독립 상태로 둔다. 하나의 토글에 실적·정기공시·수시공시를 전부 섞으면 메뉴 의미가 무너진다.

## 3. 데이터 계약

### 3.1 정규화 타입

구현 세션은 다음 타입을 starting point로 삼는다.

```ts
export type DisclosureEventKind = 'regular' | 'nonRegular';

export interface DisclosureEvent {
  eventId: string;       // `dart:${rceptNo}`
  stockCode: string;     // 6자리 문자열, 레일 매칭 1차 키
  corpCode?: string;     // 보조 감사 키, join 키 아님
  corpName?: string;     // 표시/검증용, join 키 아님
  rceptNo: string;
  rceptDate: string;      // YYYY-MM-DD
  dateKey: string;        // YYYYMMDD
  eventDate: string;      // 차트 좌표용 거래일 YYYYMMDD
  kind: DisclosureEventKind;
  title: string;          // reportType 또는 reportNm
  reportNm: string;
  subtitle?: string;      // year, filer, source hint
  filer?: string;
  year?: string;
  url: string;
  source: 'panel' | 'allFilings';
  sourceDataset: `dart/panel/${string}.parquet` | 'dart/allFilings/recent.parquet';
  sourceRef: {
    path: string;
    rceptNo: string;
    stockCode: string;
    latestAsOf?: string;
    etag?: string;
    hfCommit?: string;
  };
}

export interface DisclosureEventGroup {
  dateKey: string;        // 원 접수일 YYYYMMDD
  rceptDate: string;      // YYYY-MM-DD
  xDateKey: string;       // 차트 좌표에 매핑된 거래일 YYYYMMDD
  events: DisclosureEvent[];
  regularCount: number;
  nonRegularCount: number;
}
```

필수 규칙:

- `rceptNo` 없는 이벤트는 레일에 표시하지 않는다.
- `eventId`는 항상 `dart:${rceptNo}`다.
- `period`, `stlm_dt`, 재무제표 분기축은 사업기간이지 이벤트 날짜가 아니다.
- `sourceRef.latestAsOf`는 가능하면 남긴다. 비정기공시는 `recent.parquet` 내부 `max(rcept_dt)` 또는 sidecar/build metadata, 가격은 최신 캔들일, panel은 `max(rceptDate)` 또는 HF ref를 사용한다.

### 3.2 정기공시 소스

소스:

- `loadCompanyRegularFilings(code, limit)`
- 내부 입력: `dart/panel/{code}.parquet`
- 읽는 컬럼: `period`, `rceptNo`
- 날짜: `rceptNo.slice(0, 8)`에서 파생
- 제목: `period`에서 `사업보고서`, `반기보고서`, `분기보고서`로 매핑
- 원문 URL: `https://dart.fss.or.kr/dsaf001/main.do?rcpNo=${rceptNo}`

정기공시는 panel이 가진 기간 전체를 대상으로 한다. `RightStack`에서는 500개까지 이미 로드한다. 차트 레일도 같은 로더를 쓰되, 차트 표시 범위와 교집합만 렌더링한다.

### 3.3 비정기공시 소스

소스:

- `loadCompanyNonRegularFilings(code, { limit })`
- 내부 입력: `dart/allFilings/recent.parquet`
- 필터: `stock_code == code`
- 읽는 컬럼: `stock_code`, `rcept_dt`, `report_nm`, `rcept_no`, `flr_nm`
- 날짜: `rcept_dt`를 `YYYY-MM-DD`로 포맷
- 제목: `report_nm`
- 원문 URL: `https://dart.fss.or.kr/dsaf001/main.do?rcpNo=${rceptNo}`

현재 recent는 최근 통합 롤링 파일이다. PRD 1차 구현은 이 범위를 그대로 쓴다. 과거 전체 allFilings 백필을 차트 표시를 위해 새로 읽는 것은 1차 범위 밖이다.

### 3.4 중복 제거

정규화 후 `rceptNo`가 전역 식별자다.

규칙:

- 정기공시와 비정기공시 사이 중복은 `rceptNo` 기준 1개만 남긴다.
- 정기공시가 우선이다. 이유: panel 기반 정기공시는 viewer와 기간 정보가 더 안정적이다.
- 동일 `rceptNo`가 여러 period row에서 반복되면 첫 정규화 결과만 남긴다.
- 같은 날짜의 서로 다른 `rceptNo`는 그룹으로 묶는다.

### 3.5 날짜와 차트 좌표 매핑

공시 접수일은 달력일이고, 주가 캔들은 거래일이다. 별도 휴장일 달력을 만들지 말고, 현재 로드된 가격 캔들 `Candle.t` 배열을 거래일 캘린더로 쓴다.

표시 원칙:

- 이벤트 원 날짜는 `rceptDate/dateKey`로 보존한다.
- 차트 x좌표는 `xDateKey`로 매핑한다.
- `dateKey`가 거래일이면 그대로 쓴다.
- 휴장일이면 다음 거래일로 매핑한다.
- 매핑 함수명은 `nextTradingDateOnOrAfter(dateKey, candleDateKeys)`처럼 명시한다. 현재 `PriceChart`의 기존 이벤트 overlay가 쓰는 nearest snap 방식은 이 기능에 부적합하다.
- 이벤트가 캔들 마지막 날짜 이후면 렌더하지 않는다.
- 이벤트가 캔들 첫 날짜 이전이면 현재 차트 범위에서는 렌더하지 않는다.

왜 다음 거래일인가:

- 공시는 정보 발생일이고, 가격 반영을 눈으로 보려면 다음 실제 거래일 위치가 사용자에게 더 자연스럽다.
- 단, 툴팁에는 반드시 원 접수일과 매핑 거래일이 다르면 둘 다 표시한다.

주의:

- 장중/장후 시각 데이터는 현재 계약에 없다. `rcept_dt`만으로 장전/장후 판단하지 않는다.
- `rceptNo`나 `rceptDate`에서 접수 시각을 추정하지 않는다.
- 미래에 `rceptTimeKst`가 생기면 optional 필드로 추가하고, 값이 있을 때만 장후/장전 정책을 다룬다.
- 백테스트 신호로 쓰지 않는다. 투자/전략 이벤트가 아니라 정보 표시다.

### 3.6 회사 매칭

상장 terminal의 1차 join 키는 6자리 `stockCode`다.

- allFilings recent의 `stock_code`는 6자리로 정규화된 값을 사용한다.
- 가격 데이터의 `A005930`/`005930` 혼재는 6자리 canonical로 맞춘다.
- `corpCode`는 법인 식별/감사용 보조 키다.
- `corpName`은 표시/검증용이며 join 키로 쓰지 않는다.

### 3.7 정정공시

정정공시는 별도 `rceptNo`면 보존한다. 데이터 계약에서 삭제하지 않는다.

UI에서는 필요하면 같은 날짜 또는 같은 `amendGroupKey`로 접을 수 있다. 단 1차 구현은 `rceptNo` 보존 + 날짜 그룹 count가 정공법이다. `(stockCode, reportNm, rceptDate)`로 dedupe하면 정정공시와 같은 날 복수 공시가 사라질 수 있으므로 금지한다.

## 4. UX 설계

### 4.1 위치

공시 이벤트 레일은 `PriceChart`의 `chartHost` 아래, `chartSrc` 위 또는 x축 하단과 출처 띠 사이에 둔다.

권장 구조:

```text
chartWrap
  chartHost
  disclosureEventRail
  chartSrc
  BacktestStrip (BT active)
```

원칙:

- 캔들 캔버스 내부에 점을 찍지 않는다.
- 가격 y축과 보조지표 페인을 건드리지 않는다.
- `chartSrc` 출처 띠와 겹치지 않는다.
- BT strip이 켜져도 레일은 사라지지 않는다. 단, 세로 공간이 부족하면 높이를 14~18px로 압축한다.

### 4.2 시각 문법

기본:

- 정기공시: amber 계열 작은 원.
- 비정기공시: cyan 또는 violet 계열 작은 원.
- 같은 날짜 혼합: 원 테두리 2색 또는 split fill보다 count 배지 + 툴팁에서 구분을 우선한다.
- 1건: 5~6px 원.
- 2건 이상: 7~8px 원 + `2`, `3`, `9+` 배지.

금지:

- 가격 급등락처럼 빨강/초록을 쓰지 않는다.
- 공시 중요도를 색으로 추정하지 않는다.
- 보고서명을 차트 위에 상시 텍스트로 뿌리지 않는다.
- 모든 공시를 캔들 고가에 annotation으로 올리지 않는다.

### 4.3 호버

호버 툴팁 내용:

- 날짜: `2026-03-18`
- 요약: `정기 1 · 수시 2`
- 상위 3개 제목
- 4개 이상이면 `외 N건`
- 휴장일 매핑이면 `접수일 2026-03-15 · 차트 위치 2026-03-16`

툴팁은 pointer를 가로막지 않아야 한다. 차트 크로스헤어와 충돌하면 레일 영역에서만 자체 툴팁을 띄우고, 캔들 영역 hover는 기존 klinecharts tooltip을 우선한다.

### 4.4 클릭

점/항목 클릭의 1차 의미는 항상 "해당 공시 위치로 이동"이다. 사용자가 차트 타임라인에서 공시 점을 눌렀다면, 별도 버튼을 한 번 더 누르게 하지 않는다.

클릭 동작:

1. 그룹에 이벤트가 1개면 `onDisclosurePick(rceptNo)` 호출.
2. 그룹에 이벤트가 2개 이상이면 레일 위 작은 팝오버를 연다.
3. 팝오버 항목 클릭 시 `onDisclosurePick(rceptNo)` 호출.
4. 팝오버 항목의 `↗` 클릭은 DART 원문을 새 탭으로 연다.

`onDisclosurePick`의 기본 효과:

- 일반 모드에서는 우측 `RightStack`의 해당 공시 행으로 스크롤한다.
- 전체화면에서는 전체화면을 닫은 뒤 우측 `RightStack`의 해당 공시 행으로 스크롤한다.
- 해당 행에 1.5~2초 하이라이트를 준다.
- 정기/비정기 패널이 화면 밖이면 우측 컬럼 내부 스크롤까지 이동한다.
- 행을 찾지 못하면 작은 notice로 `현재 우측 목록 범위에 없음`을 표시한다.

호버와 클릭은 다르게 다룬다.

- hover = 임시 포커스. 가능하면 우측 행을 가볍게 preview highlight한다.
- click = 고정 선택. 우측 행으로 스크롤하고 일정 시간 강조한다.
- 우측 행 hover/click도 차트 레일의 해당 날짜 점을 highlight할 수 있다. 단 1차 필수는 click sync다.

### 4.5 팝오버

팝오버는 작은 리스트다.

구성:

- 헤더: 날짜 + 총 개수
- 항목: kind chip, title, subtitle/date, 원문 링크
- 최대 8개 표시. 초과는 스크롤.

금지:

- 전체화면 모달 금지.
- ViewerOverlay 자동 오픈 금지.
- 점 클릭 즉시 외부 링크 이동 금지.

### 4.6 우측 패널 동기화

`RightStack`의 기존 공시 행에 다음 기능을 붙인다.

- `data-rcept-no={f.rceptNo}`
- 선택된 rceptNo와 일치하면 `.filingRow.hit` 또는 `.filingRow.focused`
- 외부에서 focus 요청을 받을 수 있는 callback 또는 store

권장 계약:

```ts
export interface DisclosureFocusRequest {
  rceptNo: string;
  source?: 'chartRail' | 'rightPanel' | 'popover';
  mode?: 'hover' | 'select';
}
```

구현 방식은 둘 중 하나를 선택한다.

- 상위 `Terminal.svelte`에 `focusedRceptNo`/`selectedDisclosureEvent` 상태를 두고 `CenterStack -> PriceChart`와 `RightStack`에 prop/callback을 관통.
- 또는 `landing/src/lib/terminal/data/disclosureFocus.svelte.ts` 같은 작은 모듈 store를 둔다.

선호는 상위 상태 관통이다. 이유: `CenterStack`과 `RightStack`은 `Terminal.svelte`의 형제이므로 선택 상태를 각자 로컬로 두면 동기화가 깨진다. 전역 DOM 이벤트 버스는 금지한다. prop drilling이 과해지면 terminal 전용 Svelte store를 허용하되, public 전역 이벤트로 만들지 않는다.

### 4.7 전체화면

전체화면에서도 레일을 보인다. 전체화면에서는 우측 패널이 보이지 않지만, 사용자가 공시 점 또는 팝오버 항목을 클릭해 특정 공시를 선택한 순간에는 전체화면을 자동으로 닫고 우측 공시 행으로 이동한다. 점 클릭의 의미가 화면 모드에 따라 달라지면 직관성이 깨지므로, "공시 선택 = 해당 공시 위치로 이동"을 유지한다.

차이:

- 리본에 `공시` 토글을 추가한다.
- 일반 모드 `표시 > 마커`에는 `공시` 항목을 추가한다.
- 전체화면에서는 팝오버가 리본이나 DrawToolbar 아래로 가려지지 않아야 한다.
- `?` 도움말에 `공시 점 클릭 = 우측 공시 패널 이동`을 추가한다.
- 전체화면에서 단일 공시 점 클릭은 전체화면을 닫고 우측 행으로 바로 스크롤한다.
- 전체화면에서 다중 공시 점 클릭은 차트 내 작은 팝오버로 항목을 고르게 하고, 항목 클릭 시 전체화면을 닫고 우측 행으로 스크롤한다.
- 팝오버에는 `원문 ↗`만 별도 보조 액션으로 둔다. `찾기`류 버튼은 두지 않는다.

주의:

- 전체화면 상태에서 숨은 우측 패널만 스크롤하면 사용자는 못 본다. 그러므로 `onDisclosurePick`은 먼저 전체화면을 닫고, 다음 프레임에서 우측 행 스크롤을 실행한다.
- 전체화면 자동 닫힘은 공시가 명확히 선택된 순간에만 발생한다. 다중 공시 점의 첫 클릭은 아직 공시가 특정되지 않았으므로 팝오버만 연다.
- 전체화면 위에 기존 `RightStack`을 그대로 띄우는 안은 기각한다.

### 4.8 모바일

현재 terminal은 데스크톱 3열 구조가 기본이며, 진짜 모바일 1열 제품으로 완성되어 있지 않다. 이 기능의 모바일 목표는 데스크톱 3열 동등 구현이 아니다.

모바일 기준:

- 차트 우선.
- 레일 점 클릭은 바텀시트 또는 화면 안 팝오버로 공시 목록을 보여준다.
- 우측 패널 스크롤 동기화는 모바일 1차 필수값이 아니다.
- 원문 링크와 제목이 화면 밖으로 나가지 않아야 한다.
- 390x844에서 레일, 출처, 팝오버, 차트 툴바가 겹치면 실패다.

## 5. 정보 구조와 컴포넌트 제안

### 5.1 신규/변경 파일 후보

신규 후보:

- `landing/src/lib/terminal/data/disclosureEvents.ts`
  - 정기/비정기 로더 합성
  - 타입 정의
  - dedupe/group/date mapping helper
- `landing/src/lib/terminal/charts/DisclosureEventRail.svelte`
  - 레일 렌더링
  - hover tooltip
  - multi-event popover
- 필요 시 `landing/src/lib/terminal/data/disclosureFocus.svelte.ts`
  - terminal 전용 focus request store

변경 후보:

- `landing/src/lib/terminal/data/workbench.ts`
  - `disclosureEvents(code)` 추가 또는 `regularFilings/nonRegularFilings` 조합 helper export
- `landing/src/lib/terminal/panels/CenterStack.svelte`
  - 공시 이벤트 로드 후 `PriceChart disclosureEvents={...}` 전달
- `landing/src/lib/terminal/charts/PriceChart.svelte`
  - `disclosureEvents?: DisclosureEvent[]`
  - 레일 컴포넌트 mount
  - x좌표 mapping을 위해 display series 또는 `toMs`/visible domain 제공
- `landing/src/lib/terminal/charts/chartState.svelte.ts`
  - `showDisclosureEvents = true` 기본값 권장
  - persist whitelist에 포함
- `landing/src/lib/terminal/charts/ChartMenus.svelte`
  - 표시 > 마커에 `공시` 토글 추가
- `landing/src/lib/terminal/charts/ChartRibbon.svelte`
  - Row1에 `공시` 토글 추가
- `landing/src/lib/terminal/panels/RightStack.svelte`
  - 공시 행 focus/highlight/scroll
- `ui/web/src/features/terminalSvelte/localTerminalData.ts`
  - ui/web 임베드 어댑터가 terminal local adapter를 쓰는 경우 optional method 동형 지원
- `landing/src/lib/terminal/terminal.css`
  - 레일, 툴팁, 팝오버, 하이라이트 스타일
- `landing/src/lib/terminal/data/localAdapter.ts`
  - 로컬 어댑터가 필요하면 `disclosureEvents?` 추가. 1차에서는 기존 regular/nonRegular만으로 충분하다.

### 5.2 레일 렌더 방식

권장 구현:

- DOM/SVG overlay로 구현한다.
- `chartHost` 아래의 별도 absolute layer 또는 normal block으로 둔다.
- klinecharts overlay로 만들지 않는다. 이유: 이 레일은 가격 좌표가 아니라 x축 날짜 좌표만 쓰며, 팝오버/툴팁 DOM이 필요하다.

좌표 계산:

- `displaySeries()`의 candle list를 기준으로 `xDateKey -> index` map을 만든다.
- 현재 차트의 실제 visible range를 반영할 수 있으면 좋지만 1차는 전체 chart width에 현재 적용 데이터 기준으로 균등 위치를 둔다.
- klinecharts의 coordinate 변환 API를 안정적으로 쓸 수 있으면 `timestamp -> x coordinate`를 사용한다. 단, API 호출 실패 시 index 기반 fallback을 둔다.
- 리플레이 중에는 `displaySeries()`가 절단되므로 미래 공시 점이 보이면 안 된다.
- pan/zoom 때 DOM 점을 무제한 전량 재생성하지 않는다. 그룹 수 기준으로 렌더하고, 필요하면 visible range만 계산한다.

### 5.3 표시 기본값

기본 ON을 권장한다. 이유:

- DartLab 정체성 기능이다.
- 점 레일은 가격축을 가리지 않는다.
- 사용자가 발견하지 못하면 가치가 사라진다.

단, 사용자가 끄면 localStorage에 저장한다.

## 6. 상태 매트릭스

| State | Rail | Tooltip | Click | RightStack | Note |
| --- | --- | --- | --- | --- | --- |
| loading filings | skeleton 금지, 얇은 dim line | none | disabled | 기존 패널 loading | 로딩 텍스트 추가 금지 |
| no filings | rail hidden 또는 dim baseline | none | none | 기존 empty | 차트 공간 낭비 금지 |
| one event day | dot | title 1개 | right row focus | scroll+highlight | 원문 새 탭 아님 |
| multi event day | count dot | top 3 + count | popover | item 선택 후 focus | popover max height |
| right row focused | same dot highlighted | optional | row click 원문 | row highlight | chart dot도 pulse 가능 |
| fullscreen | rail visible | single=exit fullscreen+row focus, multi=popover | hidden right scroll 금지 | unchanged | 공시 특정 후 자동 이동 |
| mobile | rail visible compact | bottom sheet/popover | no forced right scroll | optional | 3열 동등 구현 목표 아님 |
| replay | cut date까지만 | cut range only | cut range only | unchanged | 미래 공시 노출 금지 |
| BT active | rail compressed | same | same | same | BT strip과 겹침 금지 |
| weekly/monthly tf | grouped by mapped xDate | original date retained | same | same | 날짜 정확성 툴팁 필수 |

## 7. 성능 계약

목표:

- 추가 네트워크는 이미 있는 정기/비정기 로더 2개를 재사용한다.
- 회사 전환 시 중복 fetch를 만들지 않는다.
- 레일 렌더링은 최대 수백 이벤트까지 O(n) DOM으로 충분하다.

규칙:

- `RightStack`과 `CenterStack`이 각각 `loadCompanyRegularFilings`/`loadCompanyNonRegularFilings`를 중복 호출하면 캐시 또는 workbench 합성으로 묶는다.
- 비정기공시는 `recent.parquet`의 per-code row-group filter를 유지한다.
- 과거 월별 allFilings 전체를 차트 때문에 새로 스캔하지 않는다.
- 점 수가 많으면 날짜 그룹 기준으로 렌더한다. 이벤트 개수만큼 원을 만들지 않는다.

## 8. 테스트와 검증

### 8.1 단위 테스트 후보

대상:

- `disclosureEvents.ts`

케이스:

- 정기/비정기 합성 후 `rceptNo` 중복 제거.
- 같은 날짜 그룹화.
- 휴장일 이벤트가 다음 거래일로 매핑.
- 캔들 범위 밖 이벤트 제거.
- `rceptDate` invalid 행 제거.
- recent 범위 한계가 result metadata에 남음.
- `nearest`가 아니라 `nextTradingDateOnOrAfter`로 매핑.
- 정정공시가 별도 `rceptNo`면 삭제되지 않음.
- `sourceRef.latestAsOf`가 가능한 경로에서 채워짐.

### 8.2 브라우저 검증

대상 화면:

- `/lab/terminal-dev`에서 먼저 검증.
- 이후 본진 `/terminal`.

필수 시나리오:

- 삼성전자 `005930`: 정기공시 점 표시, 호버 툴팁, 클릭 시 우측 정기공시 행 하이라이트.
- 최근 비정기공시가 있는 종목 1개: 비정기 점 표시, 클릭 시 우측 비정기공시 행 하이라이트.
- 같은 날짜 다중 공시 종목 1개: count dot, 팝오버, 항목 선택.
- 전체화면: 단일 공시 점 클릭 시 전체화면을 닫고 우측 행 하이라이트, 다중 공시 항목 선택 시 동일 동작.
- 리플레이: replay cut 이후 공시 점 미표시.
- BT active: BacktestStrip과 레일 겹침 없음.
- 모바일 390x844: 텍스트/팝오버/버튼 겹침 없음.

필수 판정:

- 콘솔 에러 0.
- Svelte error 0.
- 차트 canvas nonblank.
- 레일 점 count가 데이터 그룹 count와 일치.
- 우측 패널 스크롤 후 해당 row가 viewport 안에 있고 highlight class가 붙음.
- DART 원문 링크가 `rcpNo`를 정확히 가진다.

### 8.3 시각 검수

UI 변경이므로 push 전 운영자 검수 게이트 대상이다.

사전 스크린샷:

- 일반 모드 차트 + 레일.
- 호버 툴팁.
- 다중 공시 팝오버.
- 우측 row highlight.
- 전체화면 + 레일.
- 모바일.

정량 PASS만으로 완료 처리 금지. 레일이 x축/출처/BT strip과 겹치면 실패다.

## 9. 구현 순서

### Phase 0 - PRD 확정

완료 기준:

- 이 문서가 memory에 존재한다.
- `MEMORY.md` 프로젝트 인덱스에 연결된다.
- 구현 세션은 이 문서를 정본으로 삼는다.

### Phase 1 - 데이터 감사와 밀도 판정

범위:

- 20개 대표 종목을 대상으로 1년 공시 수, 정기/비정기/정정 비율, 동일일 중복, 비거래일 비율을 산출한다.
- 점 밀도가 너무 높으면 UI 구현 전에 클러스터링/필터 기본값을 재조정한다.

완료 기준:

- 1년 차트에서 점 표시 일자가 전체 거래일의 20%를 넘는 종목이 있는지 확인한다.
- 동일 일자 3건 초과 사례를 확인한다.
- 최근 allFilings 범위의 한계를 문서화한다.
- 데이터 감사 결과를 stdout 또는 테스트 산출로 확인하고, repo stray 파일을 남기지 않는다.

### Phase 2 - 데이터 계약과 dev 격리

범위:

- `DisclosureEvent` 타입과 합성 helper 작성.
- `/lab/terminal-dev`에서만 레일을 붙여 실측.
- 본진 연결 금지.

완료 기준:

- 정기/비정기 합성 fixture 또는 unit test.
- dedupe/group/date mapping test.
- dev 화면에서 점 표시.

### Phase 3 - 차트 레일 렌더링

범위:

- `DisclosureEventRail.svelte` 구현.
- `PriceChart`에 mount.
- 호버 툴팁과 다중 팝오버.

완료 기준:

- 차트 리사이즈/기간변경/봉주기/리플레이에 점 위치가 따라간다.
- 가격축 왜곡 없음.
- 출처 띠와 겹침 없음.

### Phase 4 - 우측 패널 동기화

범위:

- `RightStack` 공시 행에 focus target 부여.
- 점/팝오버 클릭 -> 우측 row scroll+highlight.
- 정기/비정기 모두 지원.

완료 기준:

- 단일 공시 클릭은 바로 row focus.
- 다중 공시 클릭은 팝오버 후 row focus.
- 못 찾는 경우 notice.

### Phase 5 - 본진 승격

범위:

- `ChartMenus`, `ChartRibbon`, `ChartCtl`에 공시 토글 추가.
- `/terminal` 본진 연결.
- 브라우저 검증과 운영자 검수.

완료 기준:

- svelte-check 0 error.
- landing build 통과.
- Playwright/Browser 시나리오 통과.
- 운영자 검수 후 commit/push.

## 10. Acceptance Criteria

기능:

- 메인 주가차트 x축 아래에 공시 이벤트 점이 보인다.
- 정기공시와 비정기공시가 모두 포함된다.
- 같은 날짜 다중 공시는 count dot으로 그룹화된다.
- 호버는 공시 요약 툴팁을 보여준다.
- 단일 공시 점 클릭은 우측 공시 패널 해당 행으로 스크롤하고 하이라이트한다.
- 다중 공시 점 클릭은 작은 팝오버를 열고, 항목 클릭 시 우측 행으로 이동한다.
- 팝오버/우측 행의 원문 링크는 DART 원문을 새 탭으로 연다.

정확성:

- `rceptNo` 중복이 없다.
- `rceptDate`는 원 접수일을 보존한다.
- 휴장일은 다음 거래일 위치에 매핑되며 툴팁에 원 접수일을 표시한다.
- allFilings recent 범위 밖 비정기공시를 있는 척하지 않는다.
- 리플레이 cut 이후 공시는 표시하지 않는다.

디자인:

- 레일이 차트, x축, 출처, BT strip, 전체화면 리본과 겹치지 않는다.
- 차트 가격축이 바뀌지 않는다.
- 공시 점 색이 주가 상승/하락 신호처럼 보이지 않는다.
- 모바일에서 팝오버가 화면 밖으로 나가지 않는다.
- 1년 차트에서 표시 일자의 20% 초과가 점으로 덮이면 기본 필터/클러스터링을 재검토한다.

성능:

- 회사 전환 시 추가 로더 중복이 bounded다.
- 점 렌더는 날짜 그룹 기준이다.
- 대량 공시 회사에서도 UI freeze가 없다.

## 11. 금지사항

- 공시 중요도를 자동 점수화하지 않는다.
- 공시 점을 매수/매도 신호처럼 표현하지 않는다.
- 주가 급등락과 공시 사이 인과를 자동 문구로 쓰지 않는다.
- `호재`, `악재`, `영향`, `원인`, `반응` 같은 해석 문구를 레일 기본 UI에 쓰지 않는다.
- 뉴스/RSS/GDELT/shock/regime을 Phase 1 레일에 섞지 않는다.
- 점 클릭을 외부 DART 링크 즉시 이동으로 만들지 않는다.
- 전체화면 큰 다이얼로그를 띄우지 않는다.
- 캔들 위 annotation으로 모든 공시명을 상시 표시하지 않는다.
- allFilings 전체 월별 parquet를 프론트에서 무작정 스캔하지 않는다.
- 정기/비정기 공시 로더를 새로 복붙하지 않는다. 기존 `workbench`/로더를 재사용한다.
- `/terminal` 본진에 미검증 WIP를 바로 연결하지 않는다.

## 12. Out of Scope

1차 범위 제외:

- 공시 본문 요약 자동 생성.
- 공시 중요도/영향도 분류.
- 이벤트 전후 수익률 통계.
- 뉴스와 공시 동시 타임라인.
- allFilings 전체 과거 월별 백필을 브라우저에서 직접 조회.
- 공시 기반 백테스트 신호.
- 장전/장후 판정.
- 공시 원문 iframe 내장.
- EDGAR 이벤트 레일. KR DART 먼저 완성 후 별도 PRD.
- 기존 `analysis.$code.events`식 뉴스·shock·regime 통합 이벤트 차트 복제.

후속 가능:

- 클릭한 공시를 `ViewerOverlay`의 해당 period/doc으로 여는 deep link.
- 공시 이벤트 전후 가격 반응 리포트.
- 이벤트 필터: 정기/비정기/주요사항/지분/증자/소송 등.
- allFilings 전체 이력 per-company shard 신설.
- 공시와 뉴스 타임라인 융합.

## 13. 실패 기준

다음 중 하나라도 있으면 실패다.

- 레일이 차트를 덮거나 가격 읽기를 방해한다.
- 점을 눌렀는데 우측 어디로 갔는지 사용자가 모른다.
- 공시가 많은 날짜에 점/텍스트가 난잡하게 폭발한다.
- 단일 일자 3건 초과를 개별 점으로 표시한다.
- 정기공시와 비정기공시 중 하나만 연결된다.
- 휴장일 공시가 잘못된 날짜처럼 보인다.
- 전체화면에서 클릭이 숨은 우측 패널 스크롤만 일으키거나, 사용자가 추가 `찾기` 버튼을 눌러야 이동한다.
- 공시 점이 투자 신호처럼 보인다.
- UI/tooltip/테스트 fixture/문서에 "이 공시 때문에 올랐다/내렸다" 류 문구가 있다.
- 기존 실적 마커 토글과 의미가 섞인다.
- 구현이 `RightStack` 로더와 `CenterStack` 로더를 중복·복붙해 캐시 경계를 흐린다.

## 14. 전문 검토 합의

전문 관점별 합의:

- UX 관점: 핵심 흐름은 `차트 점 -> 우측 공시 행`이다. 팝오버는 다중 공시 날짜의 선택 장치일 뿐, 주 표면이 아니다.
- 데이터 관점: `rceptNo`가 유일 식별자이고, `rceptDate` 원 날짜와 `eventDate/xDateKey` 차트 거래일을 분리해야 한다. 매핑은 `nextTradingDateOnOrAfter`이며, 현재 `nearest` 스냅 방식은 이 기능에 부적합하다.
- 프론트 아키텍처 관점: 기존 `PriceChart.events`를 과확장하지 말고 별도 `DisclosureEventRail`로 분리한다. 우측 패널 동기화는 `Terminal.svelte` 부모 상태 또는 typed terminal store로 명시한다. 전역 DOM 이벤트 버스는 금지한다.
- 품질 심판 관점: 공시 이벤트는 인과·추천·중요도 판단이 아니다. 색상·문구·클릭 동작이 투자 신호처럼 보이면 실패다. Phase 1은 DART 공시 전용이며 뉴스·shock·regime 통합은 제외한다.

## 15. 다음 세션 시작 지침

다음 세션은 이 순서로 시작한다.

1. `CLAUDE.md`, `MEMORY.md`, 본 문서, `project_terminal_lab_overhaul`, `project_terminal_round3_overhaul`, `feedback_ui_rules`를 읽는다.
2. `CenterStack.svelte`, `PriceChart.svelte`, `RightStack.svelte`, `workbench.ts`, `companyFilingsRuntime.ts`, `companyNonRegularFilings.ts`, `chartState.svelte.ts`를 확인한다.
3. Phase 1 데이터 감사(20개 종목, 1년 밀도, 동일일 중복, 비거래일 비율)를 먼저 한다.
4. `/lab/terminal-dev`에서 `DisclosureEventRail`을 붙인다. 본진 연결 금지.
5. `Terminal.svelte` 부모 상태로 `CenterStack/PriceChart`와 `RightStack` 동기화 계약을 잡는다.
6. 데이터 helper unit test를 먼저 만든다.
7. 일반/전체화면/모바일/BT active/리플레이를 브라우저로 확인한다.
8. 운영자 검수 후 본진 `/terminal`로 승격한다.
