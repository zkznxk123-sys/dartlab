# 대시보드 — 회사 종합 스냅샷 (v19 · 정보 깊이 확장)

**주체**: landing 대시보드 (`landing/src/routes/dashboard/[stockCode]/`).
**현재**: v19 · 2,664 사 동시 커버 · 동적 조합 (개별 {code}.json 최소화) · 공통 JSON fetch → 클라이언트 조립.
**방향**: v19 섹션 별 상세화 · 섹터/산업 크로스 대시보드 · 대시보드↔블로그 상호 링크.

## 존재 이유

dartlab 은 scan 13축 · macro 11축 · credit 20등급 · analysis 140+ calc · quant 43모듈 · industry 18,418 edges · 블로그 65편을 가졌지만, **회사별 한 페이지 스냅샷이 없었다**. 대시보드는 그 빈자리를 채운다.

## v16 설계 원칙

1. **전 2,664사 동시 커버** — ecosystem 에 있는 모든 회사는 URL 접근 시 즉시 렌더
2. **동적 조합** — 개별 `{code}.json` 파일 0개. 공통 JSON 몇 개만 fetch → 클라이언트에서 회사별 객체 조립
3. **로컬 빌드 OOM 0** — `Company` 객체 순회 금지. Polars parquet 직접 변환
4. **신규 상장사 자동 커버** — ecosystem 에 새 노드가 추가되면 빌드 없이 자동 페이지 뜸

## 5-tier 데이터 구조 (v19)

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

**모든 .json 파일은 fallback 가능** — 누락 시 해당 섹션만 숨김 (페이지는 정상).

Tier 4 — 클라이언트 런타임 계산 (assembleCompany.ts):
  · radar 5축: grades A-F → 1-5 스케일
  · Altman Z: finance.bs.totals 공식 (1.2A + 1.4B + 3.3C + 0.6D + 1.0E)
  · Beneish M: 5-var simplified (DSRI/GMI/AQI)
  · HHI + Top-N suppliers: ecosystem.links 필터
  · Future ensemble: currP × growth (업종·등급 derive)
  · Thesis: grade → strengths/weaknesses 템플릿 매칭
```

## 섹션 → 데이터 매핑

| 섹션 | 출처 | 파일 |
|------|------|------|
| Hero identity | node.{label,industryName,stageName,role} | ecosystem |
| Hero price | valuation.current + ecosystem.revenue | val + eco |
| Hero radar | 5 grades (profGrade/growthGrade/debtGrade/qualGrade/govGrade) | eco |
| HealthStrip | 5 grades + macro 기본값 | eco |
| PastPerformance | fin.is.sales/op + fin.ratios.roe/debtRatio | fin |
| FinancialsCard | fin.is (5Y IS), fin.bs (5Y BS), fin.cf (최신 CF) | fin |
| ValueCard | val.methods/blended/mos + scenarios 합성 | val (없으면 skeleton) |
| FutureCard | 런타임 simple growth (grade 기반) | 계산 |
| HealthCard | Altman Z + Beneish M (fin 공식) + flags | 계산 |
| SupplyCard | ecosystem.links 필터 + HHI 계산 | 계산 |
| ThesisCTA | grade → template 매칭 + meta.blog[code] | meta |
| EnginesCard | meta.engines (정적 5개) | meta |

## 빌드 명령

**로컬 빌드 (전부 OK, OOM 없음)**:
```bash
uv run python -X utf8 scripts/build/buildFinanceJson.py     # 3.3MB · 77초
uv run python -X utf8 scripts/build/buildMetaJson.py        # 18KB · 1초
uv run python -X utf8 scripts/build/buildQuartersJson.py    # 2.2MB · 35초 (v19)
uv run python -X utf8 scripts/build/buildMacroJson.py       # 2KB · 6초 (v19)
```

**CI 전용 (Company 객체 순회 → matrix chunk 분할)**:
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

## 드롭인 컴포넌트 수정 정책

`sections/*.svelte` 14개는 Claude Design drop-in.
- **건드리지 않는다** — 구조/로직/스타일 계약.
- **예외**: Svelte 5 컴파일 에러 (`{@const a, b}` 등) 또는 `// @ts-nocheck` 도입.
- **재디자인 필요 시**: Claude Design 에 재요청. 계약 (`data` prop 단일) 유지.
- **데이터 shape 이 안 맞으면**: 컴포넌트 건드리지 말고 `assembleCompany.ts` 수정.

## 차별점 (vs Simply Wall St)

1. **무료 · 오픈소스** — 상단 strip: `FREE · OPEN SOURCE · DART 2,664사`
2. **산업지도 연계** — `/map?focus={stockCode}` 양방향
3. **Buy Me A Coffee** — 후원 유도 (`brand.coffee`)
4. **DART 공시 특화** — 한국 전자공시 기반, 매일 CI 자동 업데이트

## v15 → v16 마이그레이션 요약

| 항목 | v15 | v16 |
|------|-----|-----|
| 개별 JSON | 2,664개 (35분 빌드, OOM) | 0개 |
| 빌더 | `buildDashboards.py` (Company 순회) | `buildFinanceJson.py` (Polars) + `buildValuationJson.py` (CI matrix) |
| 로컬 빌드 시간 | 35분+ (불가) | 77초 + 1초 |
| 로컬 메모리 | 9GB OOM | <2GB 안전 |
| 커버리지 | 2,664사 이론적, 실제 15사 | 2,664사 실제 작동 |
| 새 회사 대응 | 재빌드 필요 | ecosystem 갱신만으로 자동 |

## 확장 로드맵

- **최신 주가** — 일별 KRX 프리빌드 (`dashboards/price.json`), 매일 18:00 KST CI
- **Peer 비교** — 같은 industry 레이더 overlay (ecosystem 필터만)
- **Supply 1홉 interactive SVG** — 현재 top 5 표. force layout subgraph 확장
- **HF CDN fetch 옵션** — finance/valuation 용량 커지면 HF 로 이관

## 참고

- `scripts/build/buildFinanceJson.py` — Tier 1 빌더
- `scripts/build/buildMetaJson.py` — Tier 3 빌더
- `scripts/build/buildValuationJson.py` + `mergeValuation.py` — Tier 2 (CI)
- `landing/src/routes/dashboard/[stockCode]/assembleCompany.ts` — 런타임 조립
- `landing/src/routes/dashboard/[stockCode]/+page.svelte` — 13 섹션 조합
- `landing/src/routes/dashboard/[stockCode]/sections/*.svelte` — 14 drop-in
- `.github/workflows/mapBuild.yml` — CI matrix 빌드
