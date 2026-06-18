# 08. 매크로 대시보드 시각화 조사

상태: 조사 반영 v0.3
범위: Macro Lens 첫 화면을 텍스트 리포트가 아니라 전문가형 증거 상태판으로 만들기 위한 공식 매크로 대시보드 시각화 패턴.

---

## 1. 결론

공식 매크로 대시보드의 공통점은 결론문이 아니라 **시계열, 분해, 비교, 기준일, 출처, 품질 상태**를 전면에 둔다는 점이다. 따라서 Macro Lens 첫 화면은 "판단을 내려주는 화면"이 아니라 `driver -> channel -> evidence gate`를 한눈에 보는 노출 상태판이어야 한다.

Macro Lens가 강해지려면 사용자가 다섯 질문을 10초 안에 읽어야 한다.

| 질문 | 화면 답 |
|---|---|
| 지금 무엇이 움직였나? | driver pulse strip, latest/asOf/source |
| 그 움직임이 회사 어디에 닿나? | exposure matrix, channel rail |
| 증거가 실제 데이터인가, 템플릿인가? | evidence gate, OBS/PRIOR/TPL/LOCK |
| 정량으로 말해도 되나? | quality lock, nObs/R2/window/coverage |
| 무엇이 나오면 해석을 철회하나? | falsifier/release calendar/source drawer |

현재 제품에 채택할 핵심 패턴은 여덟 가지다.

| 패턴 | 참고 사례 | Macro Lens 적용 |
|---|---|---|
| 지표 펄스 스트립 | FRED dashboard, OECD STI dashboard | 핵심 driver 5~7개를 최신값, 변화, sparkline으로 압축 |
| 매트릭스/히트맵 | OECD dashboard, IMF/ECB 비교 UI | driver x 재무 channel 노출 여부를 셀로 표시 |
| 기준일·출처 고정 | FRED, World Bank DataBank, BIS Data Portal | 모든 값에 asOf/source lineage 노출 |
| 구성요소 분해 | Atlanta Fed GDPNow | driver가 어느 line을 흔드는지 chain으로 분해 |
| pressure index | NY Fed GSCPI | 복합 압력을 단일 방향성 대신 상태 변화로 표시 |
| release/vintage rail | FRED, GDPNow, OECD release dates | 발표일, 업데이트일, 데이터 빈도를 해석 옆에 고정 |
| comparator view | OECD, IMF DataMapper, ECB regional chart | 국가/업종/peer 비교를 별도 탭에서 제공 |
| evidence packet | World Bank DataBank, BIS dashboard | 차트 아래 표, 메타데이터, 다운로드, sourceRef를 묶음 제공 |

---

## 2. 참고한 외부 패턴

### FRED Dashboard

- graph, data table, single value, data list, notes, saved map 같은 widget을 조합한다.
- observation range를 고정하거나 최신 관측치 기준으로 움직이게 설정할 수 있다.
- 제품 적용: Macro Lens는 큰 설명문보다 작은 driver tile과 sparkline을 우선한다.
- 출처:
  - <https://fredhelp.stlouisfed.org/fred/account/dashboard-features/new-dashboard/>
  - <https://fredhelp.stlouisfed.org/fred/account/dashboard-features/add-widget/>

### OECD Short-Term Indicators Dashboard

- G20 및 지역 aggregate를 대상으로 단기 macro development를 interactive chart/table로 추적한다.
- 월 2회 업데이트 일정, codebook, source, original dataset link, frequency, unit, coverage를 함께 제공한다.
- 제품 적용: driver를 카드 나열로 흩뜨리지 않고 exposure matrix 행으로 고정한다.
- 출처: <https://www.oecd.org/en/data/dashboards/oecd-short-term-indicators-dashboard.html>

### Atlanta Fed GDPNow

- running estimate를 표시하되 official forecast가 아니며 판단 조정이 없다는 한계를 명시한다.
- subcomponent contribution과 update history로 숫자 변화를 분해한다.
- 제품 적용: headline thesis 대신 driver별 전파 component와 update 기준일을 둔다. 정량 claim은 model basis와 lock 조건이 없으면 차단한다.
- 출처: <https://www.atlantafed.org/research-and-data/data/gdpnow>

### NY Fed Global Supply Chain Pressure Index

- global supply chain pressure를 포착하는 composite index를 만들고, inflation 설명력은 별도 방법론으로 검증한다.
- 제품 적용: `pressure`를 투자 방향으로 쓰지 않고 증거 gate와 결손 사유로 번역한다.
- 출처:
  - <https://www.newyorkfed.org/research/policy/gscpi>
  - <https://www.newyorkfed.org/research/staff_reports/sr1017>

### World Bank DataBank

- time series collection에서 query를 만들고 table, chart, map을 생성·저장·공유한다.
- 제품 적용: 모든 숫자는 `value + unit + asOf + source` 없이 단독 노출하지 않는다.
- 출처: <https://databank.worldbank.org/>

### BIS Data Portal

- 국제 은행, credit, liquidity, exchange rate, CPI 등 금융안정 분석용 통계를 topic별 dashboard로 제공한다.
- credit dashboard는 국가/글로벌 전개를 빠르게 보고 data story를 만들 수 있게 한다.
- 제품 적용: macro driver를 "경제 전반"이 아니라 `credit`, `liquidity`, `FX`, `prices` 같은 전파 모듈로 분리한다.
- 출처:
  - <https://data.bis.org/>
  - <https://data.bis.org/topics/TOTAL_CREDIT/tables-and-dashboards>

### IMF DataMapper / ECB Data Portal

- IMF DataMapper는 map/list/chart를 통해 country/indicator 비교를 제공한다.
- ECB dashboard help는 regional chart로 국가 간 indicator 비교와 hover data point를 제공한다.
- 제품 적용: 첫 화면에는 map을 넣지 않는다. 다만 macro driver가 국가·통화권 비교를 요구할 때 drill-down 탭으로 제공한다.
- 출처:
  - <https://www.imf.org/external/datamapper/index.php>
  - <https://data.ecb.europa.eu/help/selecting-indicators-visualise-dashboard>

---

## 3. 시각화 방식 카탈로그

조사한 방식은 차트 종류가 아니라 **질문 처리 방식**으로 나눠야 한다. Macro Lens에 필요한 것은 예쁜 chart set이 아니라 `무엇이 움직였고`, `어디로 전파되고`, `근거가 충분한지`, `언제 다시 확인할지`를 빠르게 고정하는 구조다.

| 방식 계열 | 대표 시각화 | 답하는 질문 | 필요한 입력 계약 | 첫 화면 |
|---|---|---|---|---|
| 상태 위젯형 | single value, sparkline, latest delta, note | 지금 driver가 움직였나 | `value/unit/asOf/frequency/sourceSeriesId` | 채택 |
| 시계열형 | line, recession band, release marker | 움직임이 추세인가 일시 잡음인가 | `history/window/transform/vintage` | 채택 |
| 매트릭스형 | driver x channel heatmap | 이 지표가 회사 어디에 닿나 | `driverId/channel/evidenceLabel/blockedReason` | 채택 |
| 기여도 분해형 | contribution bar, waterfall | 숫자 변화의 원인은 무엇인가 | `component/contribution/updateDate/sourceRef` | 상세 탭 |
| 업데이트 경로형 | vintage path, update log | 새 발표 후 해석이 어떻게 바뀌었나 | `releaseDate/prev/current/delta/source` | 상세 탭 |
| 압력 지수형 | normalized index, z-score band | 복수 지표 압력이 평균 대비 어디인가 | `zScore/components/methodology/limit` | 일부 채택 |
| 비교형 | country/region/peer comparator | 이 시장만 다른가, 전 세계 현상인가 | `market/region/peer/value/rank/coverage` | 상세 탭 |
| 불확실성형 | probability band, fan chart | 모델 숫자의 오차 범위는 어디까지인가 | `pointEstimate/bands/modelBasis/sample` | 후순위 |
| 반증형 | falsifier rail, release calendar | 무엇이 나오면 이 해석을 버리나 | `condition/requiredData/nextReleaseDate` | 채택 |
| 원천 패킷형 | table, metadata drawer, download link | 이 숫자는 어디서 왔고 재현 가능한가 | `sourceRef/artifactPath/rawRows/codebook` | 채택 |

제품 언어로 번역하면 첫 화면에는 `상태 위젯형 + 시계열형 + 매트릭스형 + 반증형 + 원천 패킷형`만 둔다. `기여도 분해`, `업데이트 경로`, `비교`, `불확실성`은 셀 클릭 후 들어가는 상세 탭이 맞다. 첫 화면에 모든 것을 올리면 강해지는 것이 아니라 읽는 순서가 깨진다.

### 3.0 방식별 채택·기각 기준

| 채택 | 이유 |
|---|---|
| sparkline + latest stamp | FRED/OECD류의 작은 위젯 구조를 따라 driver 상태를 압축한다. |
| exposure matrix | macro driver를 회사 손익·현금흐름·밸류 channel로 연결하는 가장 빠른 표면이다. |
| evidence gate rail | 누가 결론을 내려주는 문제가 아니라 데이터 상태가 열렸는지/잠겼는지를 보여준다. |
| update path | GDPNow처럼 새 데이터가 들어올 때 숫자가 왜 움직였는지 추적한다. |
| source drawer | World Bank/BIS처럼 표·메타데이터·다운로드 가능한 원천을 붙인다. |

| 기각 또는 후순위 | 이유 |
|---|---|
| donut/gauge | 원인, 기준일, 결손을 숨기고 단일 점수처럼 읽힌다. |
| 지도 첫 화면 | 국가 비교에는 좋지만 종목 다이얼로그의 전파 경로를 느리게 만든다. |
| 뉴스 카드 wall | 데이터 lineage 없이 서사를 늘린다. |
| fan chart 첫 화면 | 모델 분포 계약이 없으면 신뢰도 높은 그림처럼 오해된다. |
| macro score | 방향과 확신을 섞어버려 반증 가능성이 낮다. |

### 3.1 P0: 첫 화면에 들어갈 방식

| 방식 | 용도 | 왜 필요한가 | 구현 규칙 |
|---|---|---|---|
| Phase strip | KR/US/sector macro state 요약 | 전체 국면을 한 줄로 고정 | 3개 타일, 각 타일은 value/asOf/source 포함 |
| Driver pulse strip | 금리, FX, 유가, CPI, PMI 등 핵심 driver 최신 상태 | macro 움직임을 긴 문장 없이 읽게 함 | 최대 6개, sparkline + delta + frequency |
| Exposure matrix | driver가 revenue/margin/debt/cash/valuation 어디에 닿는지 표시 | 회사 영향 경로를 카드보다 빠르게 비교 | 행=driver, 열=channel, 셀=OBS/PRIOR/TPL/LOCK |
| Evidence gate rail | 데이터 신뢰도와 차단 사유 | "누가 판단하나" 문제를 엔진 출력과 결손으로 바꿈 | macroData/path/comove/company/quant 5개 gate |
| Source stamp | 기준일, 출처, 빈도, coverage | macro 숫자의 시차와 빈 데이터 문제 노출 | 모든 tile/matrix/detail에 sourceRef 유지 |

### 3.2 P1: 다이얼로그 상세 탭에 들어갈 방식

| 방식 | 용도 | 참고 패턴 | 구현 규칙 |
|---|---|---|---|
| Contribution waterfall | driver 변화가 재무 line에 주는 chain 분해 | GDPNow contribution | 매출/마진/차입/밸류 중 한 channel 선택 후 기여 항목 분해 |
| Update path chart | 최근 발표로 snapshot이 어떻게 바뀌었는지 추적 | GDPNow update history | release date별 이전값/현재값/delta 표시 |
| Co-movement scatter | macro driver와 회사/업종 지표의 동행 후보 확인 | 경제 dashboard의 correlation diagnostic | nObs, R2, window, lag 없으면 LOCK |
| Falsifier rail | 해석을 철회할 조건 | nowcast 한계 공시, release calendar | `조건 -> 필요한 데이터 -> 다음 발표일`로 표시 |
| Data packet drawer | 원시값, 단위, 빈도, source, missing reason | DataBank/BIS metadata | 각 chart 하단에서 열리는 source drawer |

### 3.3 P2: 후순위 방식

| 방식 | 쓰는 경우 | 후순위 이유 |
|---|---|---|
| Country/region map | 국가별 macro divergence가 핵심일 때 | 개별 회사 dialog 첫 화면에는 정보 밀도가 낮음 |
| Peer comparator | 같은 업종/국가/수출비중 peer 비교 | peer exposure 데이터가 준비된 뒤 효과가 큼 |
| Scenario fan chart | inflation/rate/FX path 범위 비교 | 모델 분포와 가정 관리가 먼저 필요 |
| Data story canvas | 리서치 리포트용 narrative export | terminal first-use보다 저장/공유 workflow에 가까움 |

---

## 4. Macro Lens 채택 규칙

첫 화면은 아래 순서를 따른다.

1. `Macro Phase Strip`: KR, US, 업종 상태를 3개 타일로 고정한다.
2. `Driver Pulse Strip`: 선택 종목에 닿을 수 있는 상위 driver를 6개 이하로 제한한다.
3. `Exposure Matrix`: 행은 driver, 열은 `매출·마진·차입·현금·밸류`다.
4. `Evidence Gate`: 시계열, 경로, 동행, 회사노출, 민감도 잠금 상태를 노출한다.
5. `Legend`: 색과 약어가 투자 방향이 아니라 증거 상태임을 명시한다.

셀 라벨은 다음만 허용한다.

| 라벨 | 의미 |
|---|---|
| `OBS` | 관측 edge 또는 실제 데이터로 확인 가능한 경로 |
| `PRIOR` | 업종 prior 경로 |
| `TPL` | 템플릿 경로, 회사 증거 필요 |
| `LOCK` | 정량 claim 금지 |
| `·` | 표준 경로 없음 |

---

## 5. 금지 규칙

- 첫 화면에서 긴 thesis 문단을 만들지 않는다.
- `우호`, `부담`, `수혜`, `피해`, `확정`, `판정`을 셀·카드 라벨로 쓰지 않는다.
- 초록색은 투자 긍정이 아니다. `관측 가능/증거 충분`에만 쓴다.
- 빨간색은 투자 부정이 아니다. `차단/stale/사용 금지`에만 쓴다.
- co-movement는 `동행 후보`까지만 표현하고, causal label은 금지한다.
- beta/민감도는 `nObs`, `R²`, `window`, `lag`, `coverage`, `sourceRef`가 없으면 노출하지 않는다.
- gauge, donut, 단일 macro score, 뉴스 카드 wall은 첫 화면에서 쓰지 않는다. 강해 보이지만 원인·경로·결손을 숨긴다.
- 색상은 방향성이 아니라 증거 상태다. 상승/하락 색을 바로 투자 해석으로 연결하지 않는다.

---

## 6. 현재 구현 반영

2026-06-18 현재 `MacroLensDialog.svelte`는 위 규칙 중 첫 화면 핵심을 반영한다.

- 탭 1 이름: `대시보드`
- phase strip: KR/US/업종
- pulse strip: 상위 driver 6개
- exposure matrix: driver × `매출·마진·차입·현금·밸류`
- evidence gate: `MacroLensSnapshot.evidenceGates`가 제공하는 시계열, 경로, 동행, 회사노출, 민감도
- legend: `MED/HIGH`, `LOW`, `BLOCK`, `·` 설명

남은 강화는 UI 입력 전환과 회사 노출 품질 승격이다. `macro.transmission`은 `OBS/PRIOR/TPL` edge와 source/date/value lineage를 내기 시작했다. 다음 단계에서는 UI `MacroLensSnapshot`이 이 산출물을 우선 입력으로 받고, `analysis.macroExposure`가 `nObs/R²/window/lag/coverage/sourceRef`를 제공해야 한다.

---

## 7. 설계 결론

Macro Lens는 "경제를 설명하는 글"이 아니라 **매크로 노출 계기판**이어야 한다. 채택 순서는 다음이다.

1. 첫 화면은 `phase -> pulse -> matrix -> gate`만 둔다.
2. 사용자가 셀을 누르면 `contribution -> co-movement -> falsifier -> source packet`으로 들어간다.
3. 정량 claim은 gate가 열릴 때만 나온다.
4. gate가 닫히면 결론문을 만들지 않고 `왜 잠겼는지`, `어떤 데이터가 필요할지`, `다음 확인일이 언제인지`를 보여준다.
