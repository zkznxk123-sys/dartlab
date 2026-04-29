# 대시보드 — 회사 종합 스냅샷 (v19 · 정보 깊이 확장)

**주체**: landing 대시보드 (`landing/src/routes/dashboard/[stockCode]/`).
**현재**: v19 · 전 상장사 동시 커버 · 동적 조합 (개별 `{code}.json` 최소화) · 공통 JSON fetch → 클라이언트 조립.
**방향**: v19 섹션별 상세화 · 섹터·산업 크로스 대시보드 · 대시보드 ↔ 블로그 상호 링크.

dartlab 은 scan · macro · credit · analysis · quant · industry · 블로그를 가졌지만 **회사별 한 페이지 스냅샷이 없었다**. 대시보드는 그 빈자리를 채운다. 각 섹션은 **"이렇게 한다"** 명제로 열고, 반복된 실수는 섹션 하단 **"반복 실패"** 에 정리한다.

---

## 1. 설계 원칙 — 전 상장사 동시 커버 · 동적 조합 (v16 확정)

1. **전 상장사 동시 커버** — ecosystem 에 있는 모든 회사는 URL 접근 시 즉시 렌더.
2. **동적 조합** — 개별 `{code}.json` 파일 0 개. 공통 JSON 몇 개만 fetch → 클라이언트에서 회사별 객체 조립.
3. **로컬 빌드 OOM 0** — `Company` 객체 순회 없음. Polars parquet 직접 변환.
4. **신규 상장사 자동 커버** — ecosystem 에 새 노드가 추가되면 빌드 없이 자동 페이지 뜸.

**반복 실패** — v15 까지는 개별 `{code}.json` 을 전 상장사분 프리빌드 → 35 분 빌드 + 9GB OOM. Company 순회 대신 Polars parquet 직접 변환으로 해결.

---

## 2. 5-tier 데이터 구조 (v19)

```
┌────── 클라이언트 (SvelteKit) ──────────────────────────────────┐
│  /dashboard/[stockCode]/+page.svelte                          │
│     ↓ assembleCompany(stockCode, 8 파일)                      │
│  sections/*.svelte 14 drop-in + 4 v19 신규 (data prop 단일)   │
└────────────────────────┬──────────────────────────────────────┘
                         ↓ Promise.all fetch (1회만)
┌───────────────────────────────────────────────────────────────┐
│  Tier 0 — /map/ecosystem.json (4.8MB)                         │
│  Tier 1 — /dashboards/finance.json (3.3MB)   5Y IS/BS/CF      │
│  Tier 2 — /dashboards/valuation.json (CI)   DCF/DDM/RIM       │
│  Tier 3 — /dashboards/meta.json (18KB)      engines + blog    │
│                                                               │
│  v19 신규:                                                    │
│  Tier 4 — /dashboards/quarters.json (2.2MB)  20분기 시계열    │
│  Tier 5 — /dashboards/macro.json (2KB)       경기 국면 + 섹터 │
│  Tier 6 — /dashboards/credit.json (CI)       dCR + 7축        │
│  Tier 7 — /dashboards/peers.json (CI)        업종 백분위      │
└───────────────────────────────────────────────────────────────┘
```

**모든 `.json` 파일은 fallback 가능** — 누락 시 해당 섹션만 숨김 (페이지는 정상).

### 클라이언트 런타임 계산 (`assembleCompany.ts`)

- radar 5 축: grades A-F → 1-5 스케일.
- Altman Z: `finance.bs.totals` 공식 (1.2A + 1.4B + 3.3C + 0.6D + 1.0E).
- Beneish M: 5-var simplified (DSRI · GMI · AQI).
- HHI + Top-N suppliers: `ecosystem.links` 필터.
- Future ensemble: `currP × growth` (업종 · 등급 derive).
- Thesis: grade → strengths·weaknesses 템플릿 매칭.

---

## 3. 섹션 → 데이터 매핑

| 섹션 | 출처 | 파일 |
|---|---|---|
| Hero identity | `node.{label,industryName,stageName,role}` | ecosystem |
| Hero price | `valuation.current` + `ecosystem.revenue` | val + eco |
| Hero radar | 5 grades (profGrade · growthGrade · debtGrade · qualGrade · govGrade) | eco |
| HealthStrip | 5 grades + macro 기본값 | eco |
| PastPerformance | `fin.is.sales/op` + `fin.ratios.roe/debtRatio` | fin |
| FinancialsCard | `fin.is` (5Y IS) · `fin.bs` (5Y BS) · `fin.cf` (최신 CF) | fin |
| ValueCard | `val.methods/blended/mos` + scenarios 합성 | val (없으면 skeleton) |
| FutureCard | 런타임 simple growth (grade 기반) | 계산 |
| HealthCard | Altman Z + Beneish M + flags | 계산 |
| SupplyCard | `ecosystem.links` 필터 + HHI 계산 | 계산 |
| ThesisCTA | grade → template 매칭 + `meta.blog[code]` | meta |
| EnginesCard | `meta.engines` (정적 5 개) | meta |

---

## 4. 빌드 — 로컬은 OOM 없이, CI matrix 로 큰 산출물을 분산한다

### 로컬 빌드 (전부 OK, OOM 없음)

```bash
uv run python -X utf8 scripts/build/buildFinanceJson.py     # 3.3MB · 77초
uv run python -X utf8 scripts/build/buildMetaJson.py        # 18KB · 1초
uv run python -X utf8 scripts/build/buildQuartersJson.py    # 2.2MB · 35초 (v19)
uv run python -X utf8 scripts/build/buildMacroJson.py       # 2KB · 6초 (v19)
```

### CI 전용 (Company 객체 순회 → matrix chunk 분할)

```bash
# 로컬 스팟 테스트
uv run python -X utf8 scripts/build/buildValuationJson.py --codes 005930
uv run python -X utf8 scripts/build/buildCreditJson.py --codes 005930
uv run python -X utf8 scripts/build/buildPeersJson.py --codes 005930

# CI matrix [1,2,3,4] 자동
uv run python -X utf8 scripts/build/buildValuationJson.py --chunk N/4
uv run python -X utf8 scripts/build/buildCreditJson.py    --chunk N/4
uv run python -X utf8 scripts/build/buildPeersJson.py     --chunk N/4

# merger
uv run python -X utf8 scripts/build/mergeChunks.py {valuation|credit|peers}
```

---

## 5. 드롭인 컴포넌트 — `sections/*.svelte` 14 개는 손대지 않는다

`sections/*.svelte` 14 개는 design drop-in.

- **건드리지 않는다** — 구조·로직·스타일 계약.
- **예외** — Svelte 5 컴파일 에러 (`{@const a, b}` 등) 또는 `// @ts-nocheck` 도입.
- **재디자인 필요 시** — 같은 drop-in 계약으로 다시 생성. 계약 (`data` prop 단일) 유지.
- **데이터 shape 이 안 맞으면** — 컴포넌트 건드리지 말고 `assembleCompany.ts` 수정.

**반복 실패** — 섹션 컴포넌트를 직접 고쳐서 계약 깨짐 → 다음 재디자인 시 merge 충돌. shape 불일치는 항상 `assembleCompany.ts` 에서 조립 단계에 맞춘다.

---

## 6. 차별점 (vs Simply Wall St)

1. **무료 · 오픈소스** — 상단 strip: `FREE · OPEN SOURCE · DART 전 상장사`.
2. **산업지도 연계** — `/map?focus={stockCode}` 양방향.
3. **Buy Me A Coffee** — 후원 유도 (`brand.coffee`).
4. **DART 공시 특화** — 한국 전자공시 기반, 매일 CI 자동 업데이트.

---

## 7. v15 → v16 마이그레이션 요약

| 항목 | v15 | v16 |
|---|---|---|
| 개별 JSON | 전 상장사분 (35 분 빌드, OOM) | 0 개 |
| 빌더 | `buildDashboards.py` (Company 순회) | `buildFinanceJson.py` (Polars) + `buildValuationJson.py` (CI matrix) |
| 로컬 빌드 시간 | 35 분+ (불가) | 77 초 + 1 초 |
| 로컬 메모리 | 9GB OOM | <2GB 안전 |
| 커버리지 | 이론적 전 상장사, 실제 소수 | 전 상장사 실제 작동 |
| 새 회사 대응 | 재빌드 필요 | ecosystem 갱신만으로 자동 |

---

## 8. 확장 로드맵

- **최신 주가** — 일별 KRX 프리빌드 (`dashboards/price.json`), 매일 18:00 KST CI.
- **Peer 비교** — 같은 industry 레이더 overlay (ecosystem 필터만).
- **Supply 1 홉 interactive SVG** — 현재 top 5 표 → force layout subgraph 확장.
- **HF CDN fetch 옵션** — finance · valuation 용량 커지면 HF 로 이관.

---

## 참고

- `scripts/build/buildFinanceJson.py` — Tier 1 빌더.
- `scripts/build/buildMetaJson.py` — Tier 3 빌더.
- `scripts/build/buildValuationJson.py` + `mergeValuation.py` — Tier 2 (CI).
- `landing/src/routes/dashboard/[stockCode]/assembleCompany.ts` — 런타임 조립.
- `landing/src/routes/dashboard/[stockCode]/+page.svelte` — 13 섹션 조합.
- `landing/src/routes/dashboard/[stockCode]/sections/*.svelte` — 14 drop-in.
- `.github/workflows/mapBuild.yml` — CI matrix 빌드.

---

## 요약 — 명제 7 줄

1. 대시보드는 회사별 한 페이지 스냅샷 — scan·macro·credit·analysis·quant·industry·블로그의 빈자리를 채운다.
2. 설계 4 원칙 — 전 상장사 동시 커버 · 동적 조합 · OOM 없음 · 신규 상장사 자동.
3. 5-tier + v19 신규 4 tier = 총 8 파일을 `Promise.all` fetch 후 `assembleCompany.ts` 에서 조립.
4. 섹션 12 종 (Hero · HealthStrip · PastPerformance · Financials · Value · Future · Health · Supply · Thesis · Engines · …) 은 파일·데이터 매핑이 고정.
5. 빌드는 로컬 (Finance · Meta · Quarters · Macro) + CI matrix (Valuation · Credit · Peers) 분산.
6. `sections/*.svelte` 14 drop-in 은 `data` prop 단일 계약 — 건드리지 않고 `assembleCompany.ts` 로 shape 맞춘다.
7. v16 이후 빌드 시간 35 분 → 77 초 · 메모리 9GB → 2GB · 커버리지 이론 → 실제 전 상장사.
