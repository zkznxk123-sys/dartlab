# 03. 아키텍처·재사용 — 거처·touchpoint·경계

상태: 비전 PRD v0.1 (2026-06-14)
목적: "재조사 없이 구현 가능한" 설계. 자산 인벤토리(REUSE/EXTEND/NEW), 거처(engine·public·local), 영향 파일·함수(file:line), 경계, orphan 능력 배선, stale 정리.

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

**핵심 관찰**: 퍼블릭 화면은 런타임 verb가 아니라 prebuild static JSON을 소비한다. 묻어둔 능력(insights/hop2)은 `enrichCompany` 빌드에만 들어가고 verb·화면 어디서도 query-time 호출이 없다.

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
| `Industry.edges()` DataFrame | [__init__.py:359-371](../../src/dartlab/industry/__init__.py#L359) select에 `의존도(%)`·`거래액` 2컬럼 + `hop`/`insights` 인자 | B |
| `/industry/[id]/+page.svelte` 공급망 섹션 | ratio %·confidence/source 칩 (이미 amount top20 有) | B |
| `engine.ts industryPercentile` | [engine.ts:301-312](../../ui/packages/surfaces/src/terminal/lib/engine.ts#L301) line 311 `점유율` 제거 + 분포 정의 industryStats 통일 | C |
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

---

## 5. 묻어둔 능력 배선 (orphan → runtime)

`calcHHI`/`calcTopNRatio`/`calcSupplyInsights`/`computeHop2`는 현재 `enrichCompany`(빌드)·테스트만 호출. 배선 원칙:
- **별 verb 금지** — `Industry().edges(hop=2, insights=True)` 인자 확장으로만.
- **HHI는 DOJ 라벨 없이 CR4/top1 비중 evidence로만**(04 킬리스트). `calcHHI` 자체는 호출하되 `riskLabel`(독점/경쟁 라벨)은 surface 금지.
- count 기반만 honest(amount 가중은 4.1% 커버리지라 비활성).

---

## 6. stale 정리 (선결 위생 commit)

별도 "정리: industry stale 청소" commit으로 분리:
1. **유령 API 제거**: `sectorMomentumLeadership`·`concentration.py`·`peerMatrix.py`·`map.py` 광고를 [industry/README.md](../../src/dartlab/industry/README.md)에서 삭제·재작성. scan/README·skills `*.json` 카탈로그 잔존 정리(검색 cascade 주의 — `generateSkills` 동기화).
2. **edges.json 재빌드**: docstring(precise 642)·source 라벨을 실제와 정합. Phase B 선결.
3. **README ↔ 코드 정합**: calcs/ 실제 3파일(companyCalcs·lifecycle·peers) + Industry().__call__/edges/map/addOverride로 재작성.

---

## 7. 덕지덕지 함정 (적대렌즈 박제)

- profit-pool을 **새 패널**로 만들면 "셀 1줄 변환을 부풀린 것"으로 kill(migration이 이 이유로 kill됨). → 기존 stage 섹션 축 확장으로만.
- 백분위를 **새 엔진/패널**로 만들면 compare 중복으로 kill. → 표시층 통일 + 정직 버그 정리로만.
- HHI를 **DOJ 라벨**로 surface하면 규제기관 척도 사칭. → 라벨 뗀 CR4 evidence + "상장사 매출 기준" 캡션.
- 공급망을 **"SPLC식"**으로 포장하면 빈곤(0.7%) 대비 확신오정렬. → 빈곤 화면 1급시민.
