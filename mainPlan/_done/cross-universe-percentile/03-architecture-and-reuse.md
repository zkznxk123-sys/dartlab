# 03 — 아키텍처 · 영향 · 재사용 · 롤백

> plan-deep 자기충족: 이 문서만 보고 재조사 없이 구현 가능하도록 영향 파일/함수/테스트/롤백을 구체화.

## 영향 파일

| 파일 | 변경 | 비고 |
|---|---|---|
| `terminal/lib/engine.ts` | `industryPercentile(code)` → `percentileIn(code, universe)` 일반화 + export | 기존 호출부 동작 불변(아래) |
| `terminal/lib/types.ts` | `Universe` 타입 + `CrossUniversePercentile` 타입 추가 | `PercentileMetric` 재사용 |
| `terminal/panels/PercentileCrossDialog.svelte` | **신규** 다이얼로그 컴포넌트 | 셸·DistCurve·띠 마크업 재사용 |
| `terminal/panels/RightStack.svelte` | 업종내 백분위 Panel 에 `{#snippet right()}` 버튼 + `$state` open + `{#if}` 다이얼로그 | CenterStack 패턴 미러 |

## 영향 함수

### `percentileIn(code, universe)` — engine.ts 일반화
현 [engine.ts:303-336](../../ui/packages/surfaces/src/terminal/lib/engine.ts) 의 `peers` 선택 한 줄만 분기:
```ts
type Universe = 'industry' | 'market' | 'all';   // 'index' = Phase 3(BLOCKED)
function percentileIn(code: string, universe: Universe): Company['percentile'] {
  const node = ecoByCode[code];
  if (!node) return null;
  const allNodes = raw.eco?.nodes ?? [];
  const peers =
    universe === 'industry' ? industryNodes(node.industry)        // 현행(engine.ts:144)
    : universe === 'market' ? allNodes.filter(n => n.market === node.market)
    : allNodes;                                                   // 'all'
  // ↓ 이하 col/pctRank/metrics 구성은 현행과 100% 동일.
  // band: industry = raw.industryStats(기존). market/all = 같은 peers 배열에서 라이브 5분위
  //   (quantile(col(f), [.10,.25,.50,.75,.90])) → 전 유니버스 DistCurve 곡선. prebuild 0.
  ...
}
// 라이브 5분위 헬퍼(신규, ~8줄) — 정렬된 값 배열에서 p10~p90 선형보간.
function quantileBand(vals: number[]): PercentileMetric['band'] { /* sort + index */ }
// 기존 호출부(engine.ts:600) 동작 불변:
co.percentile = percentileIn(code, 'industry');
```
- `pctRank`(engine.ts:88) · `col` · lowerBetter 분기 전부 그대로. **로직 복제 0.**
- `bandOf` 는 `raw.industryStats[node.industry]` 를 보므로 market/all 에선 자연히 null → 그대로 표시(00).
- 라벨: industry=`node.industryName`, market=`node.market`, all=`'전체상장사'`. 표본수 `n=peers.length`.

### `PercentileCrossDialog.svelte` — 신규
- props: `{ co, lang, onClose }` (GradeExplainDialog 와 동일 시그니처).
- 셸: 전역 `.scrimWrap`/`.scrModal`/`.scrHead`/`.scrClose` + Escape 핸들러([GradeExplainDialog.svelte:46-68](../../ui/packages/surfaces/src/terminal/panels/GradeExplainDialog.svelte) 미러).
- 본문: `['industry','market','all']` 각각 `percentileIn(co.code, u)` 호출 → 지표를 행으로, 유니버스를 열로. 띠 = RightStack `.pctTrack/.pctFill/.pctMark`(:241) 재사용. 행 클릭 → `DistCurve`(band 있는 유니버스).
- 정성: `gradeScore`(engine.ts:104)로 서열, 칩+비중.
- 가격 격리: 밸류에이션은 하단 별 소격자(02 KILL #2).

### RightStack 배선 — CenterStack:342,353 미러
```svelte
let crossOpen = $state(false);
// 업종내 백분위 Panel:
{#snippet right()}<button class="finFullBtn" onclick={() => (crossOpen = true)}>{lang==='en'?'detail':'상세 보기'}</button>{/snippet}
...
{#if crossOpen}<PercentileCrossDialog {co} {lang} onClose={() => (crossOpen = false)} />{/if}
```

## 테스트

- **단위(engine)**: `percentileIn` 3유니버스 — (a) 결과 `metrics.length` > 0 (b) `p ∈ [0,100]` (c) `universe='market'` 모집단이 `market` 일치만 (d) `'all'` = 전 노드 (e) market/all `band` 라이브 산출: p10≤median≤p90 단조 + 모집단 5분위와 일치 (f) `quantileBand` 단위 테스트(정렬·선형보간) (g) 회귀: `percentileIn(code,'industry')` === 기존 `industryPercentile` 출력(업종내 백분위 섹션 미회귀).
- **svelte-check** 0 error + **build** 통과.
- **★UI 눈검수**: Playwright 정량(버튼·다이얼로그·띠·드릴다운·닫기·콘솔 0) + **푸시 전 스크린샷 전수 눈검수**(정량 PASS 가 디자인 디테일 못 봄, feedback_ui_rules). 자동 push 금지.

## 롤백
순수 *추가* 변경(신규 함수·컴포넌트·버튼). `industryPercentile` 동작은 `percentileIn('industry')` 로 보존되므로, 다이얼로그 제거 = ① RightStack snippet/`$state`/`{#if}` 3곳 ② 컴포넌트 파일 ③ (선택) 함수명 원복 — 으로 무손상 복원. 기존 업종내 백분위 패널은 영향 0.

## 공유 SSOT 계약
`percentileIn` 은 scan-grade-explainer 와 **같은 pctRank/EcoNode** 를 쓰는 단일 진입. scan-grade 다이얼로그가 백분위를 쓸 때도 이 함수(`'industry'`)를 경유 → 두 다이얼로그가 산식을 복제하지 않는다. 새 백분위 *엔진/prebuild 파이프라인* 신설은 02 KILL #6.
