# 03 · 데이터·bake·payload (구현 가능 수준)

> 심판 G5(b/c/d)·G6 해소: payload JSON 완전 예시 · sourceEngine 태깅 메커니즘 · P0 spike 측정→임계 절차 · buildReportView 의사코드.

## 1. 경로 결정 (정공법)

| 후보 | 판정 |
|---|---|
| **(A) CI bake → HF → 클라 정적 투영** | ✅ **채택**. story 가 굽는 payload 1벌을 HF 에 발행, 클라 `loadHfJson` fetch. |
| (B) 클라 TS 재구현 | ❌ story 엔진 중복(DRY 위반), 11.5K LoC 의 100+ calc* 를 TS 복제 불가. |
| (C) localApi(로컬 Python 서버) | ❌ 퍼블릭 정적 클라 불가(localApi 는 로컬 전용). |
| (D) 하이브리드 | ❌ 두 SSOT, 복잡도 폭발. |

## 2. bake 의 offline 분류 (적대 fatal 해소)

story full payload 는 macro 섹션을 포함 → `macroCycleBlock` 이 `analyzeCycle`(외부 API) 호출 위험. **prebuild offline 가드**(`core/offlineGuard.enforceOffline()`)에 걸린다.

정공법(선례 = [`buildMacroJson.py`](../../.github/scripts/sync/buildMacroJson.py) 의 sync/prebuild 분리): bake 의 macro 의존 블록이 **사전 산출된 cached macro JSON**(HF `dashboards/macro.json` 또는 로컬 parquet)을 읽도록 주입 → `analyzeCycle` 외부 호출 차단 → `bakeStoryReports.py` 를 **prebuild(offline)** 에 둘 수 있다. quant 가격이 외부 의존이면 그 부분만 sync 분류. payload 에 `"macroAsOf": "{weekly}"` 명시로 거짓 신선도 방지.

## 3. payload 스키마 — 완전 예시 1벌

현 `renderJson` 출력 = `stockCode/corpName/sections`(+summaryCard/circulationSummary), [`formats.py:493-507`](../../src/dartlab/story/formats.py#L493). 아래는 **신규 `bakeStoryReport(company) -> dict` 직렬화기**(renderJson 의 ~70% 확장)가 내는 형태. renderJson 을 호출하지 않고 **BlockMap(blockKey→[Block]) + catalog 을 walk** 해 blockKey·sourceEngine·act 를 stamp 한다(§4·§5).

```jsonc
{
  "schemaVersion": 1,
  "engine": "dartlab.story",            // 주체중립 (모델명·1인칭 금지)
  "engineVersion": "0.10.x",
  "bakedAt": "2026-06-19",              // 날짜 박힘 (참조HTML DNA)
  "stockCode": "005930",
  "corpName": "삼성전자",
  "basePeriod": "2026Q1",               // 최신 확정 분기
  "macroAsOf": "2026-W24",              // macro/업종 컨텍스트 신선도 (거짓신선도 방지)
  "template": "사이클",                  // STORY_TEMPLATES 자동감지 (보조)
  "grade": "A",                         // scorecard 5영역 (helper _extractCreditGrade 재사용)
  "sector": "반도체",                    // helper _extractSector 재사용

  "summaryCard": {                      // 경영요약 한 줄 (참조HTML '종합 의견')
    "conclusion": "...",                // ★C-2 변환 통과 후 (04 §conclusion) — 판정어휘 raw 금지
    "strengths": ["..."],
    "warnings": ["..."],
    "grades": {"수익성": "...", "안정성": "..."}  // 영역별 라벨 (종합점수 아님)
  },

  "evidenceFrame": {                    // killer2 — sixActScore(company).asDict() 직렬화
    "axes": {                           // ★score 키는 직렬화하되 화면 비노출 (내부 게이트용, F4)
      "macro":     {"coverage": "missing", "evidenceIds": []},
      "sector":    {"coverage": "ready",   "evidenceIds": ["industry:position", "industry:profitPool"]},
      "firm":      {"coverage": "ready",   "evidenceIds": ["analysis:insights:grades"]},
      "financial": {"coverage": "ready",   "evidenceIds": ["analysis:scorecard", "credit:distress"]},
      "value":     {"coverage": "ready",   "evidenceIds": ["quant:valuation"]},
      "risk":      {"coverage": "ready",   "evidenceIds": ["credit:distress", "analysis:flags"]}
    },
    "_internalScore": {"macro": null, "sector": 78, "firm": 84, "financial": 88, "value": 62, "risk": 71}
    // _internalScore = honest-skip reject-gate 신호 전용. 클라 렌더 금지 (NEVER-CLAIM 레이더).
  },

  "storyValidation": {                  // registry ~960 calc 직접 호출 조립 (F2 패턴)
    "precedents": [...],                // Damodaran Possible Test
    "plausibilityBand": {"revenue2027e": {"point": ..., "lo": ..., "hi": ..., "method": "..."}},
    "valuationSins": [...]
  },

  "sections": [
    {
      "key": "수익구조",
      "partId": "1",                    // 실제 catalog 값 (SectionMeta("수익구조","1",...))
      "act": 1,                         // ★F1: catalog SectionMeta.act 정수 (manifest 이미 bake)
      "actHeader": "제1막: 이 회사는 뭘 하는가",   // ACT_HEADERS["1"] (manifest 와 단일화)
      "representativeRceptNo": "20260514000123",  // 간판5: 섹션→공시뷰어 딥링크 (panel 보유)
      "title": "수익 구조 — 이 회사는 무엇으로 돈을 버는가",
      "summary": "...",                 // detail=False 폴백용
      "blocks": [
        {
          "blockKey": "segmentComposition",      // ★F/G6: BlockMap 키 (renderJson 엔 없음)
          "sourceEngine": "panel",               // ★G6: catalog BlockMeta.sourceEngine 정적
          "emphasized": false,                   // blocks.py 필드 (renderJson 미출력 → 추가)
          "type": "table",
          "label": "부문별 매출 구성",
          "data": [ {"부문": "DS", "매출": ..., "영업이익": ...}, ... ]
        },
        {
          "blockKey": "marginTrend",
          "sourceEngine": "analysis",
          "emphasized": true,
          "type": "metrics",
          "metrics": [ {"label": "영업이익률", "value": "13.0%"}, ... ]
        },
        {
          "blockKey": "revenueFlags",
          "sourceEngine": "analysis",
          "type": "flags",
          "kind": "warning",
          "flags": ["..."]
        }
      ],
      "threads": [                       // detectThreads (renderJson 이미 직렬화)
        {"threadId": "...", "title": "...", "story": "...", "severity": "warn",
         "involvedSections": ["수익구조","수익성"], "evidence": ["..."]}
      ]
    }
    // ... 27 섹션 (nonEmpty 만)
  ],

  "meta": {
    "nonEmptySectionCount": 21,
    "refCount": 34,                      // evidenceIds + sourceEngine 도달 블록 수
    "actsCovered": ["1","2","3","4","5","6"],
    "publishablePerspectives": ["executive","credit","valuation","growth","dashboard","crisis"],
    // ★P0 spike 가 실측한, emphasize 블록이 nonEmpty 를 낸 관점 집합 (박지 않음)
    "qualityLabel": "verified"           // verified | conditional (정직라벨, 점수 아님)
  }
}
```

**payload 크기.** spike 실측 → 상한(예: 200KB) 초과 시 ChartBlock spec 을 별 sidecar 로 분리 결정. `circulationSummary`(주식 유통)도 직렬화.

## 4. ★sourceEngine 태깅 메커니즘 (G6 해소)

문제: `blocks.py` 6 dataclass 에 `sourceEngine` 필드 0, registry 가 calc 결과를 블록에 넣을 뿐 출처 태그를 운반 안 함. 100+ 호출부(`_safeCall` 래퍼, [`registry.py:57`](../../src/dartlab/story/registry.py#L57))에 engine 인자를 꿰는 것은 침습적.

**정공법 — 정적 catalog 필드 + bake walk:**

1. `catalog.py` `BlockMeta` 에 **정적 `sourceEngine: str` 필드 1개 추가**(key/label/section/description 옆). 블록키당 사람 큐레이션 1줄 — docstring 규칙처럼(자동 sweep 금지, [[feedback_no_docstring_auto_sweep]] 정합). 값 = `panel | analysis | credit | quant | industry | macro`. 멀티소스 블록은 **계산 주도 엔진**(primary). 100+ 항목이나 **단일 파일·사람 큐레이션**.
2. bake 직렬화기는 `renderJson(story)`(blockKey 손실)을 호출하지 않고 **`buildBlocks` 의 BlockMap(blockKey→[Block]) + catalog(keysForSection, getBlockMeta)** 을 walk. 각 blockKey 그룹에 `sourceEngine = getBlockMeta(blockKey).sourceEngine` stamp. blockKey 가 직렬화 시점에 살아 있으므로 100% 결정론.

> ★정직 계상(H3): **섹션→blockKey 골격 + act 는 manifest 에 이미 baked**([`buildStoryManifest.py:102-104`](../../.github/scripts/prebuild/buildStoryManifest.py#L102), per-section `keys`/`act`/`partId`, manifest.json 25 섹션). 따라서 catalog 골격 자체는 신규가 아니다. bake 의 신규 작업 = **회사별로 *실제 present(nonEmpty) 블록* + 그 블록의 sourceEngine·emphasized·데이터**를 emit 하는 per-company 직렬화. act 도 catalog `SectionMeta.act` 그대로(파생 불필요, F1 재정정).

**정직 한계 명시.** `sourceEngine` = "어느 dartlab 엔진이 계산했는가"이지 "어느 DART 공시 줄"이 아니다. 후자(rcept_no 풀 회로)는 신규 후속 트랙(P4+). 이 구분을 EvidenceStrip 툴팁·푸터에 명시해 과대주장 차단.

## 5. bake 조립 절차 (publisher 재사용 거짓 철회)

`publisher.publishReportFromCompany` 는 **재사용 불가**(blog markdown/파일시스템/registry 강결합, [`publisher.py:44,50`](../../src/dartlab/story/publisher.py#L44)). 재사용은 helper `_extractSector`/`_extractCreditGrade` **2개만**.

신규 `bakeStoryReport(company) -> dict`:
1. `story = buildStory(company, type='full', detail=True)` — 전 섹션.
2. BlockMap+catalog walk → sections[].blocks[] 에 blockKey·sourceEngine·act(partId 파생)·emphasized stamp.
3. `sixActScore(company).asDict()` 직접 호출(F2). ★asDict 는 `score:{axis:value}` 0~100 을 포함([`sixAct.py:55`](../../src/dartlab/story/sixAct.py#L55)) → bake 가 **`score` 를 `_internalScore`(숨김 키)로 분리**하고 `evidenceFrame.axes` 엔 `coverage`+`evidenceIds` 만 넣는다(NEVER-CLAIM 레이더 비노출, F4·H5). 클라/인쇄 렌더는 `_internalScore` 미참조.
4. `calcValuationSins(company)` · `calcPlausibilityBand(company)` 직접 호출(registry ~960 패턴) → storyValidation.
5. meta 집계(nonEmptySectionCount·refCount·actsCovered·publishablePerspectives·qualityLabel).
6. `_reportQualifies(payload)` → 통과 시 HF push, 미달 시 `_skipped.json` 누적.

## 6. P0 spike — 측정→임계 절차 (G5(b) 해소)

`tests/_attempts/storyReportBake/` 에서 **30~50사**(대형·중형·소형·적자·턴어라운드 층화 표본) bake 실행. 측정 항목·임계 변환 공식:

| 측정 | 산출식 | → 임계 변환 |
|---|---|---|
| `nonEmptySectionCount` 분포 | 회사별 nonEmpty 섹션 수 | **N = 분포 25 분위수 floor**(하위 25% 도 핵심 섹션은 가짐을 보장하는 컷) |
| 핵심막 블록 수 | 수익구조·수익성·현금흐름·안정성·가치평가 중 블록 보유 막 수 | **M = 3**(5막 중 과반, 분포로 검증) |
| evidenceFrame 채움 | `coverage='ready'` 축 수 | **K = 분포 중앙값 −1**(과반 회사 통과·빈약 회사 컷) |
| 관점별 nonEmpty emphasize 충족률 | 관점 p 의 emphasize 블록 중 nonEmpty 비율 | 충족률 ≥ 0.5 관점만 `publishablePerspectives` 등록 |
| breakevenEstimate/operatingLeverage coverage | 실데이터 산출 회사 비율(구현은 확인됨: [`builders.py:1784,1805`](../../src/dartlab/story/builders.py#L1784)·registry 586/596/604) | 손익분기/안전마진(참조HTML DNA 핵심)이 몇 % 회사에서 뜨는지 — 낮으면 honest-skip 라벨로 정직 표시 |
| payload 크기 | JSON byte | 상한 결정(>200KB 시 ChartBlock sidecar 분리) |
| macro offline 경로 | cached JSON 주입 시 enforceOffline 통과 여부 | bake 의 prebuild 분류 확정 |
| **섹션→대표 rcept_no coverage**(간판5) | 핵심 5막에 대표 rcept_no 매핑되는 회사 비율(panel 보유 rcept 로) | 딥링크 닻 도달율 — 낮은 막은 honest-skip 라벨, 매핑식 확정 |

산출 후 `_reportQualifies` 의 N/M/K 을 **코드 상수 + 주석에 분포 근거** 박제. "권장값" 추측 금지.

## 7. buildReportView — 클라 정적 투영 의사코드 (G5(d) 해소)

```ts
// companyReport.ts — 재fetch 0, payload 1벌 위 결정론 투영
function buildReportView(payload: ReportPayload, reportType: string, manifest: Manifest): ReportView {
  const rt = manifest.reportTypes[reportType];           // sectionOrder/emphasize/focusQuestions (baked)
  const order = rt.sectionOrder;                         // 예: ["종합평가","수익구조",...]
  const emphasizeKeys = new Set(rt.emphasize);

  // 1) 관점 sectionOrder 로 섹션 필터+정렬 (payload 에 없는 섹션은 skip)
  const present = new Map(payload.sections.map(s => [s.key, s]));
  const sections = order
    .map(k => present.get(k))
    .filter(Boolean)
    .map(s => ({
      ...s,
      // 2) emphasize ∩ blockKey → ★ 강조
      blocks: s.blocks.map(b => ({ ...b, starred: emphasizeKeys.has(b.blockKey) })),
    }));

  // 3) focusQuestions 상단 칩 (참조HTML '한 줄 요약' DNA)
  const focusQuestions = rt.focusQuestions ?? [];

  // 4) 발행가능 여부 — publishablePerspectives 미포함 관점은 dim + 정직라벨
  const publishable = payload.meta.publishablePerspectives.includes(reportType);

  return { reportType, label: rt.label, focusQuestions, sections,
           summaryCard: payload.summaryCard, evidenceFrame: payload.evidenceFrame,
           meta: payload.meta, publishable };
}
// thesis 관점 제외: hypothesis 입력 필요 → 정적 투영 불가, ask 워크벤치 전용.
```

## 8. bake CI (P1)

- 신규 `storyReportBake.yml` — [`valuationSnapshot.yml`](../../.github/workflows) 동형 격리 워크플로(실패 시 이전 HF 본 유지, dataPrebuild 무영향).
- `on`: `workflow_run`[Data Prebuild 완료] + 주간 cron + `workflow_dispatch`. `concurrency`: hf-dart-push, `cancel-in-progress: false`.
- 증분: `listRemoteFiles(panel/finance)` size ledger 대조 → 변경 종목만. 신선도 트리거 확장: "panel rcept 변화 OR 하위엔진 baked JSON(macro/industry/credit/quant) 갱신".
- 유니버스 Tier SLA: featured+워치 = nightly, 전체 상장사 = weekly. 회사당 ~70초 × 동시성 N → 소요 시간 표(spike 실측 후 확정).
- OOM 가드: `POLARS_MAX_THREADS=2`, `MALLOC_ARENA_MAX=2`, 순차 gc.
- 클라: `dataConfig` DATA_RELEASES `storyReport` 1줄 + `loadStoryReport` 로더. `checkUiDataWiring` 에 storyReport 가 `loadHfJson` 단일 진입 경유 확인(가드).
