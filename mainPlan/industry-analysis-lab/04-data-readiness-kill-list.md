# 04. 데이터 준비도 · 킬리스트

상태: 비전 PRD v0.1 (2026-06-14)
목적: 무엇을 *가졌고* 무엇이 *없는지* 정직하게. 데이터 가용성 매트릭스 + EXCLUDED/BLOCKED/CONDITIONAL 킬리스트 + honest-gap 규칙. "데이터 없으면 카드 없음".

---

## 1. 데이터 가용성 매트릭스

| 능력 | 데이터 | 상태 | 근거 |
|---|---|---|---|
| profit-pool 격자 (stage 매출×이익률) | `buildIndustrySummary` 출력 + `industries/{id}.json` stages[].nodes[] | **READY** | revenue 100%·opMargin 82.4%(2561노드). 신규 fetch 0 |
| 공정/밸류체인 위치 | nodes.json (stage·stream·role) | **READY** | 2664노드·34산업·96% 공정매칭 |
| lifecycle phase | `classifyLifecycle` 매출 YoY | **READY(thin)** | 4-phase live, 전산업 공통 임계 |
| 교섭력 ratio | edges.json ratio | **THIN** | ratio 엣지 19개 |
| 공급망 amount | edges.json amount | **POOR** | amount 132/18,418 (0.7%) |
| customer 거래 | edges.json edgeType=customer | **NEAR-EMPTY** | 7건 |
| hop2 전파 | hop2.json / computeHop2 | **READY(count만)** | supplier 3191로 인접리스트 충분, amount 가중은 4.1%만 |
| CR4/top1 비중 | nodes revenue | **CONDITIONAL** | "상장사 매출 기준"만 (시장점유율 raw 부재) |
| 산업 분포 밴드 | industryStats.json p10~p90 | **READY** | 34산업 roe/opMargin/revCagr monotone |
| 시장점유율 (raw) | — | **EXCLUDED** | 어디에도 없음 |
| 애널리스트 컨센서스 | — | **EXCLUDED** | DART/EDGAR/gov 부재 |
| operational KPI (ASM/SSS/subscribers) | — | **EXCLUDED** | panel은 재무계정 격자, 비재무 표준 미보유 |
| TAM/SAM/SOM | — | **EXCLUDED** | 상장사 매출합 = 체계적 과소 |
| 가동률 (capacity utilization %) | DART '생산능력·가동률' 항목 | **BLOCKED** | 미추출 (셀 추출 시 승격) |
| 세그먼트 매출 분해 | panel | **CONDITIONAL** | XBRL 인코딩상 ~2/10만 clean (별도 _attempts) |
| US/EDGAR 산업 | — | **BLOCKED** | taxonomy KSIC 전용, US 17/2664 |

---

## 2. 킬리스트 (만들지 않는다 — 정직 가드)

### EXCLUDED (소스 부재 — 영구)
- **시장점유율 raw**: HHI를 진짜 share로 계산 불가. "상장사 매출=시장규모" 근사만, DOJ 독점/경쟁 라벨 단정 금지(규제기관 척도 사칭 = 확신오정렬).
- **애널리스트 컨센서스·목표주가·실적추정**: 스크래핑 영구 금지(financial-statement-lab와 동일 정책).
- **operational driver KPI 표준격자**(ASM/RPM·SSS·subscribers): 비재무, 산업마다 운영자 큐레이션 필요 = 억지 표준화는 fake precision.
- **정식 TAM/SAM/SOM 삼각**: 상장사 매출합은 비상장+수입+미래수요 누락. summary가 "상장사 산업 매출규모"는 제공하나 TAM이라 부르지 않음.
- **대체재 위협 정량화**: 교차탄력성은 산업 외부 도메인, taxonomy edges는 공급관계만.

### REJECT (데이터는 일부 있으나 정직성 위반)
- **Porter 5힘 종합 스코어카드**: 정성 force(대체재·신규진입)를 가짜 정량 점수로 박는 것 = fake precision. 개별 프록시(거래의존도·자본집약도)는 evidence로 OK, 단일 점수는 금지.
- **HHI DOJ 독점/경쟁 라벨**: `riskLabel` surface 금지. 라벨 뗀 CR4/top1 비중 + "상장사 매출 기준" 강제 캡션만 조건부 잔존(Phase B/C).
- **Morningstar wide/narrow/none moat 라벨**: 본질이 애널리스트 정성판단(5소스·20년전망). ROIC-WACC 스프레드 지속성을 *측정값*으로 보여주는 건 financial-statement-lab(reverseDCF) 영역, 라벨 단정만 kill.
- **진입장벽 단일 점수**: 개별 프록시(자본집약·R&D집약)는 analysis 영역, '진입장벽 점수'는 over-claim.

### BLOCKED (표면 부재 — 재방문 게이트)
- **이익풀 이동 시계열(profit-pool migration)**: 적대검증 kill. `timeline.json`은 `{year:{code:{revenue,opMargin}}}`뿐 stage 필드 없어 nodes.json 2차 join 필수, 2020 코호트 ~1사/산업 노이즈 + stage 1~3사 붕괴로 1사 진입이 결과를 뒤집음 = 확신오정렬. "셀 1줄 추가" 덕지덕지. (정적 profit-pool 스냅샷은 살아있음 — migration만 kill.)
- **가동률·세그먼트·US 산업**: 데이터 추출/파싱 선결.

---

## 3. honest-gap 규칙

1. **opMargin 결손 노드는 격자 제외 + coverageRatio 노출** (0 채움 금지).
2. **ratio 없는 엣지는 굵기 균일** (amount 0을 가는 선으로 거짓 표현 금지).
3. **HHI/CR4는 "상장사 매출 기준, 진짜 시장점유율 아님" 강제 캡션.**
4. **공급망 amount는 "추출 누락분 존재" 캡션 + amount 132/18,418 빈곤을 화면 1급시민으로.**
5. **분포 밴드는 n<10 산업 숨김 + "n=N" 노출, mean±std 금지.**
6. **lifecycle phase는 advisory confidence + 단일 YoY 점추정 한계 명시 + 백테스트 없음**(quant.walkForward가 backtest SSOT).
7. **모든 새 surface → sourceRef/as-of + confidence/source 칩.** provenance 없는 카드 = 회귀.
