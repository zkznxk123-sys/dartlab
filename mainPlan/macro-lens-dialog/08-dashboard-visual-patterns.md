# 08. 매크로 대시보드 시각화 조사

상태: 조사 반영 v0.4
범위: 퍼블릭 터미널 `경제지표분석`을 텍스트 리포트가 아니라 매크로 전파 계기판으로 만들기 위한 시각화 방식 조사.

---

## 1. 결론

강한 매크로 화면은 "판정"하지 않는다. 데이터와 모델 조건을 열어 보이고, 사용자가 결론을 내릴 수 있게 한다.

따라서 Macro Lens 첫 화면은 다음 질문에 바로 답해야 한다.

| 질문 | 화면 방식 |
|---|---|
| 지금 무엇이 움직였나 | driver pulse strip, 최신값, 변화율, 기준일 |
| 이 움직임이 어느 경로로 회사에 닿나 | driver x channel exposure matrix |
| 실제 관측인가, 업종 prior인가, 템플릿인가 | OBS/PRIOR/TPL/LOCK evidence label |
| 정량 숫자를 보여줘도 되는가 | nObs/R2/window/lag/sourceRef quality gate |
| 언제 다시 확인해야 하나 | release rail, vintage/update path |
| 무엇이 나오면 해석을 접어야 하나 | falsifier rail |
| 원천을 재현할 수 있나 | source/data packet drawer |

핵심은 `좋다/나쁘다`가 아니라 `열림/잠김/관측/결손`이다. 누가 판정하느냐의 답은 "AI가 판정하지 않는다"다. `macro.transmission`, `analysis.macroExposure`, 공개 데이터의 `asOf/source/frequency/coverage`가 게이트 상태를 만든다. 사용자는 그 게이트를 보고 투자 해석을 한다.

---

## 2. 조사한 실제 패턴

| 레퍼런스 | 확인한 방식 | Macro Lens 적용 |
|---|---|---|
| FRED Dashboard | graph, table, single value, data list, notes, saved map widget을 조합. 관측 범위를 고정하거나 최신값 기준으로 움직일 수 있음. | 큰 문단 대신 driver tile + sparkline + latest stamp. |
| FRED recession shading | NBER 경기 전환점을 그래프 음영으로 표시. 진행 중인 recession은 다르게 표시. | 시계열에는 regime band와 기준 주체를 붙인다. |
| OECD Short-Term Indicators Dashboard | G20/지역 aggregate를 interactive chart/table로 추적. 월 2회 업데이트, codebook에 source/frequency/unit/coverage 제공. | driver마다 source, frequency, coverage를 고정 표시. |
| ECB Data Portal | interactive charts, dashboards, customisation, comparison. regional chart hover 후 국가 상세로 이동. | 비교는 첫 화면이 아니라 drill-down으로 둔다. |
| IMF DataMapper / PortWatch | 국가·지표 visualise/compare/download, 무역 흐름 disruption monitor/simulate. | map은 후순위. 충격 시뮬레이션은 상세 탭에서만 사용. |
| Atlanta Fed GDPNow | running estimate, judgement adjustment 없음, subcomponent contribution과 update date 제공. | 숫자 하나가 아니라 구성요소 변화와 업데이트 경로를 보여준다. |
| Chicago Fed NFCI | 105개 지표를 risk/credit/leverage contribution으로 분해, 주간 업데이트. | 복합 지수는 component contribution 없이 단일 점수로 내지 않는다. |
| NY Fed GSCPI | 공급망 압력을 composite index로 만들고 inflation 설명력은 별도 검증. | pressure index는 방향성 추천이 아니라 상태 변화로만 표시. |
| OFR Vulnerabilities Monitor | 58개 취약성 indicator heatmap. 결론이 아니라 조사 신호라고 명시. | heatmap은 "취약성 탐지"로 쓰고 매수/매도 판정으로 쓰지 않는다. |
| BIS Credit-to-GDP gaps | credit gap dashboard로 국가/글로벌 전개와 data story 제공. 지표를 기계적으로 쓰지 말라고 명시. | macro gate도 기계적 결론이 아니라 조기경보·확인 대상으로 표시. |
| World Bank DataBank | query에서 table/chart/map을 만들고 저장·공유 가능. | 원천 패킷은 chart/table/source metadata를 함께 제공한다. |

참고 링크:

- FRED dashboard: <https://fredhelp.stlouisfed.org/fred/account/dashboard-features/add-widget/>
- FRED recession shading: <https://fredhelp.stlouisfed.org/fred/data/understanding-the-data/recession-bars/>
- OECD Short-Term Indicators Dashboard: <https://www.oecd.org/en/data/dashboards/oecd-short-term-indicators-dashboard.html>
- ECB Data Portal overview: <https://data.ecb.europa.eu/help/data/overview>
- ECB regional chart help: <https://data.ecb.europa.eu/help/selecting-indicators-visualise-dashboard>
- IMF data tools: <https://www.imf.org/en/data>
- Atlanta Fed GDPNow: <https://www.atlantafed.org/research-and-data/data/gdpnow>
- Chicago Fed NFCI: <https://www.chicagofed.org/research/data/nfci/current-data>
- NY Fed GSCPI paper: <https://www.newyorkfed.org/research/staff_reports/sr1017>
- OFR Vulnerabilities Monitor: <https://www.financialresearch.gov/financial-vulnerabilities/>
- BIS Credit-to-GDP gaps: <https://data.bis.org/topics/CREDIT_GAPS/tables-and-dashboards>
- World Bank DataBank: <https://databank.worldbank.org/>

---

## 3. 방식 카탈로그

### 3.1 상태 압축형

| 방식 | 쓰임 | 데이터 계약 | 주의 |
|---|---|---|---|
| KPI tile | 최신값, 기준일, 단위 표시 | `value/unit/asOf/frequency/sourceSeriesId` | 단독 숫자만 두면 해석이 과해진다. |
| Sparkline tile | 최근 방향과 변동성 압축 | `history/window/transform` | 축과 기간이 없으면 장식이다. |
| Pulse strip | 금리, FX, CPI, 유가, PMI 등 핵심 driver 5~7개 정렬 | `driverId/latest/delta/freshness` | 너무 많이 넣으면 다시 지표 목록이 된다. |
| Regime band | recession, tightening, inflation pressure 같은 배경 국면 | `regimeId/start/end/source` | 출처 없는 음영은 금지. |

첫 화면 채택: 필수.

### 3.2 전파 경로형

| 방식 | 쓰임 | 데이터 계약 | 주의 |
|---|---|---|---|
| Exposure matrix | driver가 매출, 마진, 차입, 현금, 밸류 어디에 닿는지 표시 | `driverId/channel/evidenceLabel/sourceRef` | 색은 투자 방향이 아니라 증거 상태다. |
| Channel rail | 선택 driver의 전파 사슬 표시 | `driver -> sector -> financialLine -> valuationLever` | 긴 설명문보다 4~5개 노드로 끝낸다. |
| Sankey/flow | 무역·공급망 충격처럼 실제 흐름 데이터가 있을 때 | `origin/destination/weight/asOf` | 일반 매크로에는 과하다. P2. |
| Network map | 금융기관·국가 간 전염 경로 | `node/edge/exposure/weight` | 데이터 없으면 장식. P2. |

첫 화면 채택: exposure matrix만 필수. channel rail은 셀 클릭 상세.

### 3.3 분해·기여도형

| 방식 | 쓰임 | 데이터 계약 | 주의 |
|---|---|---|---|
| Contribution bar | 복합 지수의 구성요소별 기여 | `component/contribution/sign/updateDate` | 단일 pressure score의 오해를 줄인다. |
| Waterfall | GDPNow처럼 headline 변화 원인 분해 | `prev/current/delta/component` | 모델 산식이 없으면 쓰지 않는다. |
| Bridge chart | macro driver가 재무 line으로 이어지는 중간 계산 | `macroDelta/channelBeta/financialDelta/quality` | beta 품질 gate가 열려야 한다. |

첫 화면 채택: 요약만. 상세 탭에서 강하게 쓴다.

### 3.4 업데이트·빈티지형

| 방식 | 쓰임 | 데이터 계약 | 주의 |
|---|---|---|---|
| Release rail | 다음 발표일, 마지막 업데이트일, 빈도 | `lastRelease/nextRelease/frequency/source` | stale 데이터를 바로 드러낸다. |
| Vintage path | 발표가 누적되며 판단이 어떻게 바뀌었는지 | `vintageDate/value/modelVersion` | public 산출물이 없으면 보류. |
| Revision marker | 지표 수정/확정치 반영 | `initial/revised/revisionDate` | macro 해석 실패 원인 추적에 필요. |

첫 화면 채택: release rail은 필수. vintage path는 P1.

### 3.5 품질·반증형

| 방식 | 쓰임 | 데이터 계약 | 주의 |
|---|---|---|---|
| Evidence gate rail | 데이터, 경로, 동행, 회사노출, 정량 gate 표시 | `gateId/status/blockReason/sourceRef` | "판정"이 아니라 잠금 사유다. |
| Co-movement scatter | driver와 회사/업종 지표의 동행 후보 | `nObs/rSquared/lag/window` | causality 라벨 금지. |
| Falsifier rail | 해석을 버릴 조건 | `condition/requiredData/nextCheckDate` | 이게 없으면 그냥 서사다. |
| Model card drawer | 모델 한계, 표본, 결손, 버전 | `method/modelVersion/sample/limit` | 숫자가 강해 보일수록 더 필요하다. |

첫 화면 채택: evidence gate + falsifier 필수. scatter는 상세.

### 3.6 비교·분포형

| 방식 | 쓰임 | 데이터 계약 | 주의 |
|---|---|---|---|
| Country comparator | 같은 지표의 국가/지역 차이 | `country/value/rank/asOf` | 종목 다이얼로그 첫 화면에는 느리다. |
| Peer comparator | 같은 업종 내 exposure 차이 | `peerCode/driver/channel/quality` | 회사별 exposure 품질이 있어야 한다. |
| Fan chart / probability band | forecast uncertainty | `pointEstimate/band/modelBasis/calibration` | 모델 분포 계약 없으면 금지. |
| Scenario table | 금리/환율/유가 path별 민감도 | `scenario/inputAssumption/outputDelta/quality` | 목표가 시뮬레이터로 오해되지 않게 한다. |

첫 화면 채택: 없음. P1~P2.

### 3.7 원천 패킷형

| 방식 | 쓰임 | 데이터 계약 | 주의 |
|---|---|---|---|
| Source drawer | 값의 출처, 단위, 빈도, 기준일 | `sourceName/sourceSeriesId/unit/frequency/asOf` | 모든 숫자에 붙인다. |
| Data table | chart 뒤의 원시 관측치 확인 | `date/value/vintage/source` | 다운로드보다 화면 내 검증이 먼저다. |
| Download/export | 분석 재현 | `artifactPath/schemaVersion` | public artifact만 노출. |

첫 화면 채택: drawer로 필수.

---

## 4. Macro Lens 화면 구조

첫 화면은 아래 순서로 고정한다.

```text
Header
  종목명 / sector / macro asOf / data freshness

Row 1: Macro Phase Strip
  KR / US / Sector 상태 3개

Row 2: Driver Pulse Strip
  USDKRW / BASE_RATE / CPI / EXPORT / OIL / PMI 등 최대 6개

Main: Exposure Matrix
  rows = drivers
  columns = revenue / margin / debt / cash / valuation
  cells = OBS / PRIOR / TPL / LOCK / -

Bottom: Evidence Gate + Release Rail
  macro data / path / co-move / company exposure / quant gate
  last release / next release / stale reason

Drawer: Source Packet
  sourceSeriesId / unit / frequency / latest observation / method / missing reason
```

이 구조의 목적은 텍스트를 줄이는 것이 아니라 읽는 순서를 고정하는 것이다. 첫 화면에 결론문을 크게 두지 않는다. 결론문이 필요하면 matrix와 gate 아래에서 2줄 이하로만 둔다.

---

## 5. 상태 라벨

셀과 gate 라벨은 아래만 허용한다.

| 라벨 | 의미 | 누가 만든 상태인가 |
|---|---|---|
| OBS | 관측값 또는 공개 edge로 확인됨 | `macro.transmission` source lineage |
| PRIOR | 업종 prior 경로만 있음 | sector/industry prior registry |
| TPL | 템플릿 경로, 회사 증거 없음 | macroLens fallback view-model |
| LOCK | 정량/강한 해석 금지 | quality gate |
| STALE | 기준일 초과 | source freshness check |
| MISSING | 원천 또는 series 미배선 | data contract |
| - | 표준 경로 없음 | driver registry |

사용하지 않을 말:

- 판정
- 수혜 확정
- 피해 확정
- 매수/매도
- 좋음/나쁨
- 위기 임박

화면은 "판정"을 내리지 않는다. 화면은 `왜 열렸고 왜 잠겼는지`를 보여준다.

---

## 6. 가장 강한 조합

Macro Lens에 바로 쓸 강한 조합은 다섯 개다.

| 조합 | 구성 | 효과 |
|---|---|---|
| Driver Pulse + Source Stamp | latest, delta, sparkline, asOf, source | 지금 움직임을 짧게 확인한다. |
| Exposure Matrix + Evidence Label | driver x channel, OBS/PRIOR/TPL/LOCK | 회사 영향 경로를 한 번에 본다. |
| Contribution Drilldown | component bar, waterfall, update marker | 숫자가 왜 바뀌었는지 본다. |
| Quality Gate + Model Card | nObs, R2, lag, window, coverage, blockedReason | 정량 claim 가능 여부를 기계적으로 잠근다. |
| Falsifier + Release Rail | 반증 조건, 필요 데이터, 다음 발표일 | 다음에 무엇을 보면 되는지 남긴다. |

이 다섯 개가 없으면 화면은 예쁜 매크로 뉴스판이 된다. 이 다섯 개가 있으면 분석 도구가 된다.

---

## 7. 금지할 시각화

| 금지 | 이유 |
|---|---|
| Gauge | 기준과 원천을 숨기고 점수처럼 보인다. |
| Donut | 매크로 전파 경로를 설명하지 못한다. |
| 단일 macro score | 방향, 확신, 품질을 섞는다. |
| 뉴스 카드 wall | source lineage와 반증 조건이 없다. |
| 첫 화면 지도 | 종목 영향 경로보다 국가 비교를 먼저 보게 만든다. |
| 출처 없는 heatmap | 색이 결론처럼 읽힌다. |
| 모델 분포 없는 fan chart | 정밀한 예측처럼 오해된다. |

---

## 8. 구현 우선순위

### P0

- Driver Pulse Strip
- Exposure Matrix
- Evidence Gate Rail
- Source Stamp
- Release Rail
- Falsifier Rail

### P1

- Contribution Waterfall
- Update/Vintage Path
- Co-movement Scatter
- Model Card Drawer
- Peer/sector comparator

### P2

- Country map
- Sankey/flow
- Fan chart
- Scenario table
- Data story export

---

## 9. 제품 결론

`경제지표분석`은 "경제지표를 보여주는 화면"이 아니라 "매크로가 이 종목의 어느 재무 채널에 닿을 수 있는지 검증하는 화면"이어야 한다.

따라서 첫 화면의 정답은 긴 텍스트가 아니다.

```text
무엇이 움직였나
어느 채널에 닿나
증거가 관측인가 prior인가
정량 숫자는 열렸나 잠겼나
무엇을 보면 해석을 바꿀까
원천은 어디인가
```

이 여섯 줄에 답하지 못하는 시각화는 제거한다.
