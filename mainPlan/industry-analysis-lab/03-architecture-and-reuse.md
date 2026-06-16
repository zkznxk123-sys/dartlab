# 03. 아키텍처·재사용 — 거처·touchpoint·경계

상태: 비전 PRD v0.2 (2026-06-14, 2차 대대적 조사·적대검증 반영)
목적: "재조사 없이 구현 가능한" 설계. 자산 인벤토리(REUSE/EXTEND/NEW), 거처(engine·public·local), 영향 파일·함수(file:line), 경계, orphan 능력 배선, stale 정리, 엔진 리팩토링 결정(§8).

---

## 1. 데이터 파이프라인 (현재 실측)

```
src/dartlab/industry/build/{stage1_ksic,stage2_product,stage3_docs,stage4_review,
                            financials,edges,hop2,insights,enrichCompany}.py
   → 산출물 JSON: nodes.json · edges.json · hop2.json · (enrichCompany baked)
   → .github/scripts/prebuild/buildIndustryMap.py  (offline only, HF 다운로드)
   → landing static /map/*.json: industries/{id}.json · industryStats.json · movers.json · meta.json
   → landing /industry/[id]/+page.ts (prerender) → +page.svelte (정적 렌더)

런타임 verb (별개 경로):
   dartlab.industry(id, summary/timeline/lifecycle) · Industry().edges() · Company(code).industry()
   → loadNodes()/loadEdges()/buildIndustrySummary()/classifyLifecycle()
   → industryBadge (ai/tools/industryContext.py) → EngineCall/story/workbench
```

**핵심 관찰**: 퍼블릭 화면은 런타임 verb가 아니라 prebuild static JSON을 소비한다. `insights.py`/`hop2.py` *함수*는 `enrichCompany` 빌드에만 들어가고 verb·화면 어디서도 query-time 호출이 없다(orphan은 함수·화면·DataFrame 한정 — 산업 분석 *능력* 자체는 recipe 층이 이미 런타임 제공, [§5.1](#51-이미-live한-recipe-층--orphan-범위-정정)).

---

## 2. 자산 인벤토리 판정

### REUSE (그대로 씀)
| 자산 | 위치 | 용도 |
|---|---|---|
| `buildIndustrySummary` | [financials.py:219](../../src/dartlab/industry/build/financials.py#L219) | Phase A profit-pool 데이터 소스 (stage 매출·영업이익·기업수) |
| `industries/{id}.json` (stages[].nodes[].revenue/opMargin) | landing static `/map/` | Phase A 브라우저 격자 (신규 fetch 0) |
| `industryStats.json` (p10~p90 분포) | landing static `/map/` | Phase C 분포 밴드 |
| `computeHop2` · `calcSupplyInsights` | [hop2.py:32](../../src/dartlab/industry/build/hop2.py#L32) · [insights.py:201](../../src/dartlab/industry/build/insights.py#L201) | Phase B hop2/다양성 (현재 orphan → 배선) |
| `calcTopNRatio` | [insights.py:136](../../src/dartlab/industry/build/insights.py#L136) | Phase B CR_N evidence (라벨 뗀 raw만) |
| `FreshnessBadge` · `rt.company.relations` · RightStack 패턴 · `PriceChart` 스택 | ui/packages/surfaces | 로컬 재사용 |
| `compare()` | [providers/dart/panel/compare.py](../../src/dartlab/providers/dart/panel/compare.py) | Phase C funnel 대상 (재구현 금지) |

### EXTEND (확장 — 새 파일·verb 금지)
| 자산 | 변경 | Phase |
|---|---|---|
| `buildIndustrySummary` | 출력에 `영업이익률(%)`(revenue-weighted 파생) + `coverageRatio` 2컬럼 | A |
| `/industry/[id]/+page.svelte` | stage 섹션에 2D(매출규모×영업이익률) 격자 렌더 (브라우저 롤업) | A |
| `Industry.edges()` DataFrame | [__init__.py:359-371](../../src/dartlab/industry/__init__.py#L359) select에 `의존도(%)`(ratio)·`거래액`(amount) 2컬럼 + `hop`/`insights` 인자. 디스크 필드 `type` 주의 | B |
| `/industry/[id]/+page.svelte` 공급망 섹션 | ratio %·confidence/source 칩 (이미 amount top20 有) | B |
| `engine.ts industryPercentile` | [engine.ts:492](../../ui/packages/surfaces/src/terminal/lib/engine.ts#L492)(★PRD 동결 후 cross-universe-percentile 리팩토링으로 301-312→492 이동 + `buildFundMetrics` 공유 산식 신설 → 분포 정의 industryStats 통일은 post-06-15 잔존 분기 재실측 선결). inert `marketShare`(`점유율`) 선제 제거는 engine.ts 아닌 [CenterStack.svelte:194/198](../../ui/packages/surfaces/src/terminal/panels/CenterStack.svelte#L194)·[ScreenerModal.svelte:42](../../ui/packages/surfaces/src/terminal/panels/ScreenerModal.svelte#L42)(producer 없어 `null→'—'`) | C |
| `/industry/[id]/+page.svelte` | industryStats 분포 밴드 위 회사 마커 + compare funnel 링크 | C |
| 로컬 CenterStack / RightStack | profit-pool 버블 · hop walk · 회사→산업 점프 | A/B |

### NEW (최소 — 정당성 입증된 것만)
- **없음(파일 단위).** 모든 Phase가 기존 함수·화면·JSON의 EXTEND로 떨어진다. Python 의존 신규 계산이 생기면(예: 적응형 lifecycle 임계) `tests/_attempts/industryAnalysisLab/` 졸업 게이트 후 build 내부에만.

---

## 3. 거처 분담 (engine / public / local)

- **엔진(`src/dartlab/industry/`)**: `buildIndustrySummary` 파생 컬럼(A) · `Industry.edges()` 컬럼·인자(B) · hop2/insights 런타임 배선(B). AI·EngineCall이 "이 산업 이익은 어느 단계가 버나" / "이 거래선 의존도"를 질의로 답하게.
- **퍼블릭(landing, adapter-static·서버0·SEO)**: 결정론적·정적·인용가능 산출물의 거처. profit-pool 스냅샷·분포 밴드·edges evidence는 브라우저에서 기존 JSON으로 떨어진다. SEO 가치(검색·AI 인용되는 "이익은 어느 단계" 한 줄).
- **로컬(터미널, 인터랙티브)**: 탐색·드릴다운의 거처. profit-pool 인터랙티브 버블·hop walk·회사↔산업 점프.

---

## 4. 경계 (불가침 — 위반 = 덕지덕지/회귀)

- **L2 단방향**: industry는 다른 L2(analysis/credit/macro/quant) 직접 import 금지. 조합은 L3 story. driver 연계(수요/공급)는 story 또는 scenario-simulator 소유.
- **compare() = peer N사 비교 SSOT.** industry는 "분포 위 1점 읽기"로 funnel만, N사 비교 재구현 금지.
- **scan = 횡단 스크리닝 SSOT.** 전종목 필터/랭킹 재구현 금지.
- **/map = 산업맵 전체뷰 SSOT.** IndustryAtlas·Treemap 재구현 금지.
- **story(L3) = 조합·내러티브.** chainPositionBlock/sectorMetricsBlock/sectorOutlookBlock가 이미 calcChainPosition·calcSectorMetrics·calcSectorCycle 조합 — industry는 데이터만, 조합은 story.
- **백분위 SSOT(Phase C 선결)**: industry = KSIC섹터 분포(읽기), compare + financial-statement-lab = 큐레이션 peer 정밀. 이 경계를 본 PRD에서 박는다.
- **scenario-simulator 경계**: 인과·미래예측·driver DAG는 simulate 소유. industry는 static 다양성/hop/lifecycle 라벨만.
- **profit-pool 영업이익률 dual-source SSOT**: 엔진 `buildIndustrySummary`는 `opIncome.sum()/revenue.sum()`([financials.py:307-308](../../src/dartlab/industry/build/financials.py#L307), panel 소스)로, 브라우저 격자는 `industries/{id}.json`의 per-node `revenue×opMargin/100` Σ/Σ 롤업(prebuild JSON, opMargin 82.4% 커버리지)으로 계산 — 두 경로의 소스·커버리지가 달라 같은 stage 마진이 화면별로 갈릴 수 있다. ★**엔진 파생컬럼=캐논, 브라우저=표시만**으로 고정. coverageRatio 분모(전체노드 vs finance-join노드)도 경로별 명시 고정 + 불일치 회귀테스트 동행.

---

## 5. 묻어둔 능력 배선 (orphan → runtime)

`calcHHI`/`calcTopNRatio`/`calcSupplyInsights`/`computeHop2`는 현재 `enrichCompany`(빌드)·테스트만 호출. 배선 원칙:
- **별 verb 금지** — `Industry().edges(hop=2, insights=True)` 인자 확장으로만.
- **HHI는 DOJ 라벨 없이 CR4/top1 비중 evidence로만**(04 킬리스트). `calcHHI` 자체는 호출하되 `riskLabel`(독점/경쟁 라벨)은 surface 금지.
- count 기반만 honest(amount 가중은 4.1% 커버리지라 비활성).
- **Leontief 명명 금지**: `computeHop2`는 nodes/edges count 인접리스트 2-hop BFS다. "Leontief 승수"·"IO 분석 경량판"으로 *명명*하지 않는다 — 진짜 후방/전방연쇄(Rasmussen/Hirschman)는 산업연관표(한국은행) 기술계수 행렬 필요(부재). hop2 count ≠ IO linkage. SPLC 단어 금지와 동일 사유(강한 학술 권위 라벨일수록 확신오정렬 큼).

### 5.1 ★이미 live한 recipe 층 — orphan 범위 정정

industry 분석 *능력*은 통째 orphan이 아니다. [recipes/industry/](../../src/dartlab/skills/specs/recipes/industry/)에 8개 curated·validated(2026-05-27) recipe가 RunPython/EngineCall로 런타임 실행되는 *조합 분석*으로 존재한다 — `industryStagePhase`(peer ROIC-WACC spread+CAGR phase)·`marginCompressionScan`(peer GP/OM/NM 3축 z-score)·`peerCapexWave`(capex/매출 wave lead-lag)·`rdIntensityTrend`(R&D/매출 추세+peer rank)·`supplyChainConcentration`(top5 고객/거래처 HHI)·`sectorMomentumLeadership`·`sectorFlowConcentration`·`peerPriceConvergence`.

따라서 본 PRD의 **"만들어 묻어둔 엔진" 프레임은 *화면·DataFrame 노출*에 한정**한다. 진짜 orphan은 (a) `build/insights.py`의 `calcHHI`/`calcTopNRatio`/`calcIndustryConcentration`/`computeHop2`/`calcSupplyInsights` *함수가 Industry verb DataFrame·화면으로 안 나오는 것* + (b) `/industry/[id]` static JSON이 profit-pool 격자·분포 밴드를 안 그리는 것 + (c) `Industry.edges()` amount/ratio 컬럼 누락 + (d) engine.ts marketShare inert dead 일 뿐, 산업 분석 capability *전체*가 아니다. **recipe 층과 기능 중복 신설 금지** — profit-pool 격자는 화면이지 새 recipe가 아니고, `supplyChainConcentration` recipe가 이미 HHI 교섭력을 RunPython으로 답한다. 신규 능력 착수 전 recipes.industry 중복 여부 확인 의무.

---

## 6. stale 정리 (선결 위생 commit)

별도 "정리: industry stale 청소" commit으로 분리:
1. **유령 *verb/모듈* 제거 (★recipe는 보존)**: [industry/README.md](../../src/dartlab/industry/README.md)가 광고하는 Python verb `dartlab.industry.sectorMomentumLeadership(...)` 및 모듈 파일 `sectorMomentum.py`·`peerMatrix.py`·`map.py`·`concentration.py`는 실재 0(Glob 확인) → 삭제·재작성. **단 `recipes.industry.sectorMomentumLeadership.md`·`supplyChainConcentration.md`는 curated 라이브 recipe로 실재 → 삭제 금지.** stale은 "verb/모듈 광고"지 "recipe"가 아니다. scan/README·skills `*.json` 카탈로그 전파 점검(검색 cascade 주의 — `generateSkills` 동기화).
2. **edges.json 재빌드**: 목적은 *커버리지 증가 아님* — `source` 라벨(코드 panel_text/panel_table vs 디스크 docs/docs_table)·docstring(precise 642 vs 실측 132) 정합. ★642 vs 132 격차 원인(파서 변경 vs 데이터 손실)을 재빌드 *전* 1회 진단이 선결. 빈곤(amount 0.7%·customer 7·ratio 19)은 원천 한계라 재빌드 후에도 안 늘 수 있음 → 1급시민 유지. Phase B 선결.
3. **README ↔ 코드 정합**: calcs/ 실제 3파일(companyCalcs·lifecycle·peers) + build/ 13파일 + 공개표면(Industry().__call__/edges/map/build/addOverride)으로 재작성. + `enrichCompany.py` docstring Example(L238-240)의 `buildCompanyEgograph` import 거짓 정정(def 없음 → ImportError), `__init__` docstring `data/industry/` → `src/dartlab/industry/` 통일·`deltas.json`/`hop2.json`은 prebuild 산출이라 `build()` 산출물 목록서 제거.

---

## 7. 덕지덕지 함정 (적대렌즈 박제)

- profit-pool을 **새 패널**로 만들면 "셀 1줄 변환을 부풀린 것"으로 kill(migration이 이 이유로 kill됨). → 기존 stage 섹션 축 확장으로만.
- 백분위를 **새 엔진/패널**로 만들면 compare 중복으로 kill. → 표시층 통일 + inert dead 정리로만.
- HHI를 **DOJ 라벨**로 surface하면 규제기관 척도 사칭. → 라벨 뗀 CR4 evidence + "상장사 매출 기준" 캡션.
- 공급망을 **"SPLC식"·"Leontief 승수"**로 포장하면 빈곤(0.7%) 대비 확신오정렬. → 빈곤 화면 1급시민, 학술 권위 라벨 금지.

---

## 8. 엔진 리팩토링 결정 — **design-only**

"사업분석을 위한 클린코드·폴더구조·리팩토링"의 결론: **새 서브폴더·새 엔진 신설 금지.** Phase A 선결 위생(now-safe, 문서/docstring만) + Phase B 동행 배선 + 3중복 수렴 defer로 분배. profit-pool 파생은 `buildIndustrySummary` select 확장으로 정확히 떨어진다(폴더 변경 0).

**[지금 — Phase A 선결 위생, now-safe, docstring/문서만]**
1. `industry/README.md` 전면 재작성(§6.1 — 유령 verb/모듈 삭제, recipe 보존).
2. `enrichCompany.py` docstring Example(L238-240) `buildCompanyEgograph` import 거짓 정정(전 src/dartlab def 0 → 4섹션 hook은 통과하나 Example 실행 시 ImportError).
3. `__init__` addOverride/build/edges docstring `data/industry/` → `src/dartlab/industry/` 통일, `deltas.json`·`hop2.json`은 prebuild 산출이라 `build()` 산출물 목록서 제거.
4. `calcs/__init__.py`·`build/__init__.py` 둘 다 docstring-only(`__all__` SSOT 없음, 실측) → 재배치/신규 시 `__all__` 채움 동반 명문화.

**[Phase B 동행 — 정공법 배선]**
5. edges.json 재빌드(§6.2 — 라벨 정합, 642 vs 132 진단 선결).
6. `build/insights.py`의 순수계산(`calcHHI`·`calcTopNRatio`·`calcSupplyInsights`·`calcIndustryConcentration`)을 **`calcs/concentration.py`로 승격**(런타임·prebuild 양쪽 import) → 집중도·교섭력·다양성이 calcs/ 단일 런타임 거처에 모이고 `Industry.edges(insights=True)`가 build deep-import 대신 calcs 호출로 정공법화. `riskLabel`은 surface 금지(캡슐화 유지). `peers.py` `_findIndustryFor`의 방어적 lazy try/except import도 이때 정리. ★단 `supplyChainConcentration` recipe와 기능 중복 신설 아님 — calcs=함수 거처, recipe=조합 분석으로 역할 분리.

**[설계만 — design-only]**
7. orphan 함수 런타임 노출은 새 verb·패널 금지, `Industry.edges(hop=2, insights=True)` 인자 확장으로만(§5 일치). `computeHop2`는 전종목 인접리스트 빌드 비용이라 런타임 호출 시 캐시/precompute 경계 설계 필요.

**[연기 — defer, 별도 트랙·골든]**
8. `financials._extractYearly`·`enrichCompany._getFinancials5y`·`delta`의 CFS우선-OFS폴백 추출 *3중복*을 scan.io SSOT로 수렴 — `_REVENUE_SANITY_LIMIT` 단위가드 유실·전종목 매출집계 회귀 큼. Phase A 영업이익률 파생은 `buildIndustrySummary`가 이미 `opIncome.sum()`을 하므로 파생만 추가하면 되어 지금 수렴 불필요.

**폴더구조 결론**: (a) Phase A 파생=financials.py select 확장. (b) 집중도 함수 거처=calcs/concentration.py(insights.py 승격이지 새 능력 아님). (c) Capital Cycle·DOL·Damodaran 자본효율 등 신규 다년 집계/회귀는 single-year snapshot 엔진의 신규 계산이라 `tests/_attempts/industryAnalysisLab/` 졸업 후 build/calcs(직행 금지). (d) Damodaran 자본효율은 `synth/damodaranL15.py`(L1.5)에 이미 거처 — industry 신설 금지.
