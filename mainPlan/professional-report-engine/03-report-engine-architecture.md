# 03 · 리포트 엔진 아키텍처 — story 갈아엎기 + 계약 SSOT + 랜딩 conform

> 출처: 시니어 아키텍트 설계. 코드 직독(file:line) 기반. 00-PRD(thesis 아크·18 블록)·01-감사(폐기 목록·4대 결함)·02a~d(능력 격상)를 *구현 가능한 완전 설계*로 박는다. 재조사 없이 이 문서만으로 구현한다.

---

## 0. 결론 — CRUX 해소: SSOT 는 *문법 계약*이지 구현이 아니다

거시 시뮬 선례(`mainPlan/macro-simulation-engine`)가 동형 문제를 이미 풀었다:

- 계약 패키지(`ui/packages/contracts/src/macro.ts:201` `MacroSimFile`)가 **출력 *형태* 만** SSOT 로 보유한다.
- Python(`src/dartlab/macro/simulate/`)과 브라우저 TS(`ui/packages/surfaces/src/terminal/lib/macroSimCompute.ts`)는 **각자 독립으로 같은 형태를 emit** 한다 — 베이크·publish 0, 런타임 직독.
- 해석 상수(z값·Minnesota δ·시나리오 프리셋)는 **공유 파일 없이 양쪽에 인라인 중복** + mirror-comment(`fan.py:18` "Python _Z 와 동일 상수" ↔ `macroSimCompute.ts:32` 동) + **희소 골든 수치 테스트**(`macroSimCompute.test.ts`, ~30 셀·1e-5)로 drift 핀.

→ 리포트 엔진의 SSOT 도 **GRAMMAR CONTRACT** (스키마 + 블록 어휘 + 해석 규율 상수)다. Python `story` 와 TS `build.ts` 는 두 개의 conformant builder. "story=SSOT, report 가 동일 소비" 는 **둘 다 같은 `ReportModel` 계약을 emit** 으로 실현 — 정적 사이트가 Python 을 못 돌려도, 베이크 금지여도 성립한다.

핵심 결정 4개:

1. **계약 SSOT 위치** = `ui/packages/contracts/src/report.ts`. 단 이 파일은 *이미* `ReportPort`(parquet 파생 시리즈 포트)를 점유 → **충돌 회피: 새 모델은 `reportModel.ts` 신설** 후 `index.ts` 에서 둘 다 export. (00-PRD §7 의 "report.ts 로 승격" 의도는 "contracts 패키지로 승격"이며, 파일명은 포트 충돌로 `reportModel.ts` 가 정공법.)
2. **랜딩 모델 이주**: `landing/src/lib/report/model.ts:5-106` 의 `ReportModel`/`ReportBlock`/`OverviewModel` 을 contracts 로 끌어올린다 — 랜딩은 re-export 만 남겨 무회귀.
3. **Python emitter 신설**: `src/dartlab/story/report.py::buildReportModel(company, perspective) -> ReportModel(TypedDict)` — `buildStory`(Story dataclass)와 **공존**하되, 신규 계약 출력 경로. 군더더기 삭제는 별도.
4. **drift 핀**: 해석 상수 6개(verdict 임계·window 제외·peer 백분위·valuation 모델선택·thesis 규율·아크 순서)만 양쪽 중복 + 골든 parity 테스트 N=5사. 전수 스냅샷 parity 안 함(over-engineer 금지).

---

## 1. 계약 SSOT — 확장 ReportModel (`ui/packages/contracts/src/reportModel.ts` 신설)

### 1.1 설계 원칙

- **기존 8 블록 불변** (`model.ts:5-18`: heading·text·metrics·table·flags·bars·line·share). 신규 10 블록은 전부 **optional 추가** — 기존 렌더러(`report/+page.svelte` 인라인 switch)가 모르는 블록은 무시(graceful). 회귀 0.
- `EvidenceRef`(`evidence.ts:4`) + `FinCard`(`finance.ts`) 재사용 — 새 근거/카드 타입 신설 금지.
- 모든 신규 verdict 블록은 `noComposite: true` 강제 필드 → 합성 종합점수 영구 차단(01-감사 §5 "독립 verdict" 회귀 금지를 *타입으로* 박음).
- camelCase, `Num = number | null`(빈값 규약: null=미공시/미산출).

### 1.2 블록 어휘 8 → 18 (union 확장)

```ts
// reportModel.ts — 블록 어휘 SSOT. 기존 8 (model.ts) + 신규 10. 신규는 전부 렌더러 graceful-skip 대상.
import type { Num, EvidenceRef } from './index'; // EvidenceRef 재사용 (evidence.ts)

// ── 기존 8 (model.ts:5-18 에서 이주, 1바이트 동일) ──
export type ReportBlockLegacy =
  | { type: 'heading'; title: string }
  | { type: 'text'; text: string; refs?: EvidenceRef[] }          // refs 추가(optional) — 문장↔근거 결박
  | { type: 'metrics'; metrics: { label: string; value: string }[] }
  | { type: 'table'; label?: string; data: Record<string,string>[]; snapshot?: boolean; unit?: string; refs?: EvidenceRef[] }
  | { type: 'flags'; kind: 'warning'|'opportunity'; flags: string[] }
  | { type: 'bars'; label?: string; rows: { label: string; value: number; display: string; tone?: 'neg' }[] }
  | { type: 'line'; label?: string; series: number[]; xLabels?: [string,string]; markers?: { label: string; v: number }[]; valueFmt?: 'won' }
  | { type: 'share'; label?: string; rows: { year: string; segs: { label: string; pct: number; key: string }[] }[]; legend: { label: string; key: string }[] };

// ── 신규 10 (00-PRD §7) ──
export type ReportBlockPro =
  // [0] thesis — 결론 먼저. 구조화 논증(기계 문장 폐기). 본문 finding 합성, 최상단 1회.
  | { type: 'thesis'; thesis: Thesis }
  // exhibit — 번호·제목·테이크캡션 붙은 인용 표/차트 래퍼(애널 리포트 'Exhibit N'). child=기존 블록.
  | { type: 'exhibit'; n: number; title: string; takeaway: string; source: string; unit?: string; child: ReportBlock; refs?: EvidenceRef[] }
  // callout — 강조 박스(주의/시사점). tone=경고/기회/중립.
  | { type: 'callout'; tone: 'warn'|'opportunity'|'neutral'; title: string; body: string; refs?: EvidenceRef[] }
  // verdict — 독립 판정(축별). ⛔ noComposite:true 필수 — 합성 종합점수 영구 차단.
  | { type: 'verdict'; noComposite: true; rows: VerdictRow[]; caption?: string }
  // scenario — bear/base/bull 3 시나리오(드라이버 3 변동: 성장·마진·WACC). ±10% 장난 아님.
  | { type: 'scenario'; set: ScenarioSet }
  // valuationBridge — 현재가 → 내재가치 워터폴 + reverse-DCF(시장 내재 성장 역산).
  | { type: 'valuationBridge'; view: ValuationView }
  // peerScatter — 동종 2D 산점(예 ROIC×성장). 좌표지 목표가 아님.
  | { type: 'peerScatter'; xLabel: string; yLabel: string; points: PeerPoint[]; subjectCode: string }
  // driverTree — DuPont/ROIC 인과 분해 트리. node=값+기여.
  | { type: 'driverTree'; root: DriverNode }
  // excerpt — 공시 원문 발췌(untrusted 마커 동반). sourceType='external' 시 wrap.
  | { type: 'excerpt'; source: string; rceptNo?: string; text: string; sourceType: 'dart'|'edgar'|'external' }
  // transition — "→ 그래서" 섹션 연결(아크 인과). 다음 섹션 질문을 연다.
  | { type: 'transition'; from: string; to: string; line: string };

export type ReportBlock = ReportBlockLegacy | ReportBlockPro;
```

### 1.3 구조화 객체 — Thesis / VerdictRow / ScenarioSet / ValuationView / Driver

```ts
// ── Thesis (00-PRD §4) — 반증 가능 인과 논증. 형용사 금지, 메커니즘. ──
export interface ThesisPillar {
  claim: string;          // "ROIC 18%로 WACC 6%p 상회 → 자본이 가치 창출" (메커니즘 1문장)
  sectionKey: string;     // 이 기둥을 증명하는 본문 섹션 (결박)
  refs: EvidenceRef[];    // 재무제표 라인·rceptNo
}
export interface Thesis {
  central: string;        // 중심논거 1문장 (검증가능 인과)
  pillars: ThesisPillar[];// 지지기둥 3 — 각 = 본문 섹션 1 + evidenceRef
  bearCase: string;       // 약세론: "이 논지를 깨는 단 하나는 X" (thesis 와 동등 무게)
  triggers: string[];     // 관점전환: "①CCC 2분기 급증 ②ICR 1배 하회 ..."
  call: string | null;    // 콜 (내재가치·등급·상대위치) — 매매지시 아님. 미산출 null.
}

// ── Verdict — 축별 독립 판정. 합성 금지. ──
export interface VerdictRow {
  axis: string;           // '레버리지' '이자감당' ...
  latest: string;         // 최근값 (포맷됨)
  range: string;          // 최근 범위
  threshold: string;      // 기준 (라벨)
  verdict: '양호'|'주의'|'산출 불가'|string; // verdictTone (render.ts:30) 어휘
}

// ── ScenarioSet (00-PRD §5) — 3 드라이버 변동. ──
export interface ScenarioLeg {
  key: 'bear'|'base'|'bull';
  label: string;
  growth: Num;            // 명시구간 성장 가정 (%)
  margin: Num;            // 목표 영업/EBIT 마진 (%)
  wacc: Num;              // 할인율 (%)
  intrinsic: Num;         // 산출 내재가치 (원/주)
  upside: Num;            // 현재가 대비 (%)
}
export interface ScenarioSet {
  current: Num;           // 현재가
  legs: ScenarioLeg[];    // bear/base/bull
  note: string;           // 가정·민감도 노출 (콜 뒤 숨지 않되 가정 명시)
}

// ── ValuationView (00-PRD §5, 02a) — 내재가치 콜 + reverse-DCF. ──
export interface ValuationView {
  model: 'DCF'|'DDM'|'RIM'|'relative'; // 선택된 1차 모델 (§4 모델선택 규율)
  intrinsic: Num;         // 내재가치 (원/주)
  current: Num;           // 현재가
  wacc: Num;              // 회사별 bottom-up WACC (CAPM + dCR 스프레드)
  waccBreakdown: { rf: Num; erp: Num; beta: Num; costDebt: Num; taxRate: Num; weightE: Num }; // 02a
  g: Num;                 // 재투자 묶인 성장 (g = 재투자율 × ROIC)
  reinvestRate: Num; roic: Num; // Damodaran 항등식 노출
  fadeYears: number;      // terminal fade 구간 (ROIC→WACC 수렴)
  bridge: { label: string; value: Num }[]; // 현재가→내재가치 워터폴 단계
  reverseDcf: { impliedGrowth: Num; supportedGrowth: Num; verdict: string } | null; // 시장 내재 성장 역산
}

// ── DriverTree / PeerPoint ──
export interface DriverNode { label: string; value: string; contribution?: Num; children?: DriverNode[] }
export interface PeerPoint { code: string; name: string; x: Num; y: Num }
```

### 1.4 ReportModel / Section / Overview 확장 (마이그레이션 안전)

```ts
export type ReportSourceEngine = 'analysis'|'credit'|'quant'|'industry'|'macro'|'story'|'valuation'|'forecast'; // +valuation,forecast

export interface ReportSection {
  key: string;
  title: string;          // "{도메인} -- {질문}"
  sourceEngine: ReportSourceEngine;
  blocks: ReportBlock[];
  emph?: boolean;
  arcStep?: number;       // 신규(optional) — 아크 위치 0..10 (PRD §3). 없으면 기존 평면 순서.
}

export interface ReportModel {
  // ── 기존 필드 (model.ts:49-68) 전부 불변 ──
  stockCode: string; corpName: string; asOf: string; dataBasis: string; industry?: string;
  perspectiveKey: string; perspectiveLabel: string; conclusion: string;
  headlineKpis: { label: string; value: string }[];
  narrativeOverview: string;                 // ← thesis 로 graceful 승격(아래)
  keyFindings: { key: string; finding: string; sourceEngine: ReportSourceEngine }[];
  sections: ReportSection[];
  closing: { label: string; engine: ReportSourceEngine; line: string }[];
  provenance: { engines: Record<string,{label:string;sections:number;blocks:number}>; note: string };
  assumptionsNote: string;
  qualityLabel: 'verified'|'conditional';
  focusQuestions: string[];
  pending?: boolean;
  // ── 신규 (전부 optional — 구 렌더러 무회귀) ──
  thesis?: Thesis;        // narrativeOverview(string) 의 구조화 후계. 둘 다 채우면 thesis 우선.
  schemaVersion?: number; // 1=레거시, 2=pro 아크. 부재=1.
}

// OverviewModel — thesis(string) → 구조화 Thesis graceful 승격
export interface OverviewModel {
  corpName: string; stockCode: string; asOf: string; dataBasis: string; industry?: string;
  thesis: string;         // 기존 string 유지(구 렌더러) — 항상 채움(폴백)
  thesisStruct?: Thesis;  // 신규 구조화 (pro 렌더러가 우선 소비)
  takes: { key: string; label: string; line: string; engine: ReportSourceEngine }[];
}

export interface ReportSkipped { skipped: true; stockCode: string; reason: string }
export type ReportResult = ReportModel | ReportSkipped;
export function isSkipped(r: ReportResult): r is ReportSkipped { return (r as ReportSkipped).skipped === true; }
```

### 1.5 마이그레이션 규약 — 무회귀 보장

| 변경 | 기존 소비자 영향 | 안전장치 |
|---|---|---|
| `model.ts` → `reportModel.ts` 이주 | `import './model'` 다수 | `model.ts` 를 `export * from '@dartlab/ui-contracts'` re-export shim 으로 축소(한 줄). 모든 import 경로 무변경 |
| 신규 10 블록 | `+page.svelte` switch | 모르는 `type` = `default: null` (기존 동작). 신규 블록 렌더는 *추가* case 만 |
| `narrativeOverview` → `thesis` | 텍스트 한 문단 렌더 | `thesis` 부재 시 `narrativeOverview` 렌더(폴백). Python/TS 둘 다 당분간 *양쪽 채움* |
| `arcStep`/`schemaVersion` optional | 정렬 로직 | 부재 시 기존 평면 순서(회귀 0) |
| `ReportSourceEngine` +2 | `render.ts:10` engineLabel | engineLabel 에 `valuation`/`forecast` 2줄 추가 |

**핵심**: contracts 변경은 전부 *additive*. 기존 랜딩 렌더러는 한 줄(engineLabel 2개)만 건드리고 나머지는 무변경으로 통과.

---

## 2. Python story 갈아엎기

### 2.1 폐기 목록 (file:line — 검증가 실측 교정 반영)

> ⚠ 01-감사 §2 의 "reportTypes/templates 삭제" 는 **부정확**했다. 실측: 둘 다 `buildStory` 의 live 의존(`registry.py:15` import, `:1550/:1571/:1610/:1630` 호출). **삭제 아님 — 단순화·아크수렴**. 진짜 dead 만 삭제한다.

**확정 DELETE (외부 importer 0, 실측):**

| 파일/심볼 | file:line | LOC | 증거 |
|---|---|---|---|
| `publisher.py` 전체 | `story/publisher.py:1-327` | 327 | 외부 importer 0. blog 는 `<CompanyFinancials>` SSOT 이주(`0f6a6f2f7`). docstring 자체가 dead bridge 명시 |
| `sections/__init__.py` (빈 디렉터리) | `story/sections/__init__.py:1` | 1 | docstring 1줄, 서브모듈 0, importer 0 |
| `story/macro/` 서브트리 전체 | `story/macro/{__init__,report,builders,narrative,catalog,charts}.py` | 1823 | `macroReport` importer 0 (자기 모듈+`testCoverage.json` baseline 만). 거시 섹션은 신규 아크가 macro 엔진 직접 호출 |
| `templates.py` PERSPECTIVE_* 블록 | `story/templates.py:412-543` | ~130 | self-labeled "deprecated 2026-Q3 제거", importer 0 |
| `templates.py` LIFECYCLE_PHASES | `story/templates.py:738-781` | ~44 | importer 0 |

**DELETE — story-report 엔진 기준 cruft (각 1 외부 소비자 → 절단/이주):**

| 파일/심볼 | file:line | LOC | 처리 |
|---|---|---|---|
| `sixAct.py` (`SixActScore`/`sixActScore`/`_macroScore` 스텁) | `story/sixAct.py:1-268` | 268 | landing `_scripts/buildCompanyCharts.py:122` hero 레이더만 소비. 레이더 차트 폐기(00-PRD §7 합성점수 차단과 정합) → 삭제. `__init__.py:58,487-488` re-export 제거 |
| `dashboard.py` (`DASHBOARD_QUESTIONS`) | `story/dashboard.py:1-121` | 121 | offline prebuild `buildStoryManifest.py:14,142` 만 소비. 해당 매니페스트 데이터를 prebuild 스크립트 로컬 상수로 이주 후 삭제 |

**삭제 합계 ≈ 2,834 LOC** (01-감사의 "~1,250" 은 보수 추정 — macro 서브트리 1,823 이 더 큼).

**KEEP-and-simplify (buildStory live 의존, 아크로 수렴):**
- `registry.py:1450 buildBlocks` / `:1520 buildStory` — 엔진 본체. 신규 emitter 가 *재사용*(블록 빌더 호출), 갈아엎지 않음.
- `reportTypes.py`(334)·`templates.py`(잔여 ~617)·`catalog.py`(459)·`narrative.py`(919)·`narrate.py`(1299)·`builders/`(6399)·`validators/validators.py`(363) — 전부 유지. builders 가 곧 능력(02 격상 대상).
- `storyTree.py`·`narrativeDiff.py` — `Company.storyTree()`/`narrativeDiff()` 별도 public verb. 리포트 무관, 유지.

### 2.2 신규 모듈 구조 — emitter 신설 (130-파일 정리)

```
src/dartlab/story/
├── report.py            ★신규 — 계약 emitter. buildReportModel(company, perspective) -> ReportModel(dict)
├── arc.py               ★신규 — 아크 순서(11단계)·transition 합성·섹션→arcStep 매핑. PRD §3 SSOT
├── thesis.py            ★신규 — buildThesis(findings, sections) -> Thesis. 정규식 합성 폐기, 구조화 논증
├── constants.py         ★신규 — 해석 상수 SSOT (verdict 임계·window 제외·peer 컷·valuation 모델선택). §4 drift 핀 대상
├── registry.py          유지 — buildBlocks/buildStory (레거시 Story dataclass 경로 + emitter 가 블록 재사용)
├── catalog.py templates.py reportTypes.py  유지(단순화) — 섹션 SSOT
├── builders/            유지 — 도메인 블록 빌더(능력). report.py 가 호출
├── narrative.py narrate.py validators/  유지
├── __init__.py          수정 — sixAct re-export 제거, buildReportModel export 추가
├── storyTree.py narrativeDiff.py  유지(별도 verb)
└── (삭제) publisher.py sixAct.py dashboard.py sections/ macro/
```

### 2.3 emitter 시그니처 + 동작 (self-calc 0·L3 placement·import 방향)

```python
# src/dartlab/story/report.py
from __future__ import annotations
from typing import Any, Literal, TypedDict
# L2 분석엔진은 company 메서드/lazy import 로만 — story 는 L3 조합기, 직접 숫자 계산 0.

PerspectiveKey = Literal[
    "thesis", "business", "earnings", "cashConversion", "capitalAllocation",
    "creditRisk", "competitive", "valuation", "forward", "risk", "full",
]

class ReportModelDict(TypedDict, total=False):  # contracts ReportModel 1:1 (camelCase 키)
    stockCode: str; corpName: str; asOf: str; dataBasis: str; industry: str
    perspectiveKey: str; perspectiveLabel: str; conclusion: str
    headlineKpis: list[dict]; narrativeOverview: str; keyFindings: list[dict]
    sections: list[dict]; closing: list[dict]; provenance: dict
    assumptionsNote: str; qualityLabel: str; focusQuestions: list[str]
    thesis: dict; schemaVersion: int

def buildReportModel(
    company: Any,
    perspective: PerspectiveKey = "full",
    *,
    basePeriod: str | None = None,
) -> ReportModelDict:
    """계약 ReportModel emitter (contracts/reportModel.ts conform).

    동작: company(L2 sub-engine 결과)에서 블록을 buildBlocks/builders 로 조립 →
    arc.assemble 로 11단계 아크 정렬·transition 합성 → thesis.buildThesis 로 구조화
    논거 → ReportModelDict(camelCase) 반환. self-calc 0 — 모든 숫자는 analysis/credit/
    quant/industry/macro/valuation/forecast/segment/moat 가 계산, story 는 *엮기*만.

    Sig: buildReportModel(company, perspective='full', *, basePeriod=None) -> dict
    Returns: ReportModel conform dict (schemaVersion=2). skip 은 {'skipped':True,...}.
    Example: dartlab.Company('005930').report('valuation')  → 밸류에이션 아크
    Raises: never (데이터 부족 = skipped dict, 억지 채움 0).
    """
    ...
```

- **self-calc 0 유지**: 02 격상 능력(valuation/forecast/segment/moat)은 L2 엔진(`analysis/valuation`, `analysis/forecast`, `revenue.segment`, 신규 `analysis/moat`)에 산다. report.py 는 결과를 블록으로 포장만.
- **L3 placement 유지**: import 방향 L2→L3, story 가 L2 를 lazy import(현 `dart/company.py:2946` 패턴 그대로). emitter 가 ai/agent.py 에 들어가지 않음(§5 가드).
- **공개 verb 배선**: `Company.report(perspective='full')` 신설(`dart/company.py`·`edgar/company.py`), `buildReportModel` lazy 호출. 기존 `Company.story()`(Story dataclass·CLI 용)는 *공존*.

### 2.4 02 능력 격상 배선점 (이 아키텍처가 소비)

| 아크 단계 | 블록 | 호출 능력(L2) | 02 문서 |
|---|---|---|---|
| [2] 수익체력 | driverTree(ROIC×WACC) | `analysis.valuation` ROIC·WACC | 02a |
| [5] 재무·신용 | verdict + valuationBridge(스프레드) | `credit.engine.evaluateCompany` dCR 20등급 | 02·E |
| [6] 경쟁위치 | peerScatter + verdict(moat) | 신규 `analysis.moat`(ROIC 지속·마진안정 시계열) | 02d |
| [7] 밸류에이션 | valuationBridge + scenario | `analysis.valuation` (회사별 WACC·재투자묶인 g·fade·reverse-DCF) | 02a |
| [8] 포워드뷰 | line + callout | `analysis.forecast`(백테스트된 driver) + macro | 02b |
| [1] 사업구조 | table + driverTree | `revenue.segment`(axisPath + 마진도출) | 02c |

---

## 3. 랜딩 TS conformance

### 3.1 무엇이 공유 / 무엇이 TS-side

| 계층 | 위치 | 공유 여부 |
|---|---|---|
| **계약**(ReportModel·18블록·구조화객체) | `contracts/reportModel.ts` | **공유 SSOT** — Python·TS 둘 다 conform |
| **해석 상수**(verdict 임계·window·peer컷·모델선택) | `contracts/reportConstants.ts` + Python `story/constants.py` | **중복**(macro 선례) + parity 테스트 핀 |
| **라이브 빌더**(분기윈도·peer백분위·thesis합성) | `landing/src/lib/report/{build,window,peer,series,market}.ts` | TS-side (브라우저 런타임) |
| **렌더링**(geo·tone·spark·splitTitle) | `landing/src/lib/report/render.ts` + `+page.svelte` | TS-side (Svelte 비의존 순수) |
| **데이터 fetch** | `dataCore.requestParquetRows` / `rt.finance.bundle` / `rt.report.*` | TS-side 단일 SSOT (불변) |

### 3.2 build.ts 리팩터 — 동일 ReportModel emit (live·브라우저·베이크 0)

현 `build.ts:1333 buildReport` 는 이미 `ReportModel` 을 반환한다(`model.ts:49`). 리팩터 = **그 모델을 확장 계약으로 승격**:

1. **import 교체**: `import type { ReportModel, ReportBlock, ... } from './model'` → `from '@dartlab/ui-contracts'`. `model.ts` 는 re-export shim 으로 축소(§1.5).
2. **5관점 → 11 아크 매핑**: `perspectives.ts:11` 5관점은 유지하되 각 빌더 섹션에 `arcStep` 부여. 신규 아크 단계(business[1]·valuation[7]·forward[8]·risk[9])는 02 능력 배선 후 점진 추가 — *현재 빌더 회귀 0*, 새 섹션만 append.
3. **thesis 구조화**: `buildOverview`(`build.ts:1484`)의 정규식 합성(`:1504-1519`)을 **`buildThesisStruct(built)` 로 교체** — `OverviewModel.thesisStruct: Thesis` 채움. 기존 `thesis: string` 은 폴백으로 계속 채움(무회귀).
4. **신규 블록 emit**: valuation 격상 시 `buildMarket`(`build.ts:889`)에 `valuationBridge`·`scenario` 블록 추가. peer 는 `buildEarningsPower`(`:254`)에 `peerScatter` 추가. 전부 기존 블록과 *병존*.
5. **데이터 fetch 불변**: `rt.finance.bundle(code)`(`:1341`) + `loadJson`(`:1342`) + `rt.report.*`(`:1384-1418`) 단일 진입점 유지. 신규 능력(valuation/credit)도 같은 포트 경유 — 직접 URL·자체 캐시 금지(CLAUDE.md UI 배선 규칙).

**브라우저가 못 하는 것**: dCR 20등급·DCF·forecast 의 무거운 계산. → 랜딩은 두 길 중 하나:
- (a) `rt` pyodide 런타임이 `dartlab.Company(code).report()` 직접 실행(거시 시뮬 `MacroSimRunner` 선례, `macro.ts:230`) → 무거운 능력만 pyodide, 가벼운 건 TS.
- (b) TS 가 *경량 근사*(현 healthTable 처럼) emit + "정밀판은 터미널/Python" 정직 표기.

→ **결정: 밸류에이션·신용 정밀 블록은 (a) pyodide runner** (계약 동형 `ReportModel`), 나머지는 (b) TS 라이브. 둘 다 같은 `ReportModel` 슬롯을 채운다 — 소비자(렌더러)는 출처 무관.

---

## 4. drift 관리 — 해석 상수 핀 (over-engineer 금지)

### 4.1 drift-prone 상수 6개 (양쪽 중복 + parity 핀)

거시 선례대로 **공유 파일 없이 양쪽 인라인 중복 + mirror-comment + 희소 골든 테스트**. 핀 대상은 *값이 갈리면 결론이 바뀌는* 소수만:

| # | 상수 | Python | TS | drift 위험 |
|---|---|---|---|---|
| 1 | verdict 임계(부채비율 200·유동 100·ICR 1·FCF 0) | `story/constants.py` `VERDICT_THRESHOLDS` | `contracts/reportConstants.ts` `VERDICT_THRESHOLDS` | 양호/주의 판정 뒤집힘 (현 `build.ts:620-623`) |
| 2 | window 제외 규율(후행 2분기·buf=min(25,max(8,3·MAD))·rev×1.4) | `constants.py` `WINDOW_GUARD` | 현 `window.ts:26-43` → 상수 추출 | 오염분기 포함/제외 갈림 |
| 3 | peer 백분위 컷(tail≤6/≥94·n<3 게이트·self-exclusion) | `constants.py` `PEER_CUTS` | 현 `peer.ts:42,98` → 상수 추출 | "상위 X%" 라벨 갈림 |
| 4 | valuation 모델선택(적자=RIM·금융=DDM·else DCF) | `analysis/valuation/` (이미 Python) | pyodide 경유(§3 (a)) → TS 미중복 | 모델 갈리면 내재가치 갈림 |
| 5 | thesis 규율(지지기둥 3·메커니즘 강제·bearCase 동등무게) | `story/thesis.py` | `landing/.../build.ts buildThesisStruct` | 구조 갈리면 논증 형태 갈림 |
| 6 | 아크 순서(11단계 PRD §3) | `story/arc.py` `ARC_ORDER` | `contracts/reportConstants.ts` `ARC_ORDER` | 섹션 순서=논증 → 갈리면 인과 깨짐 |

**#4 는 pyodide 단일 실행이라 중복 0**(macro regimePath 가 TS 미구현으로 parity 면제한 것과 동형). #1·#6 은 contracts 에 상수로 둬 TS 가 import, Python 이 `constants.py` 에 mirror — **#1/#6 만 contracts export 상수**(순수 데이터), #2/#3/#5 는 알고리즘이라 양쪽 인라인.

### 4.2 골든 parity 테스트 (N=5사·희소 셀·macro 선례)

```
tests/story/test_report_parity.py    ★신규
- 고정 5사: 005930(삼성전자·제조)·035420(NAVER·플랫폼)·105560(KB금융·금융=DDM)·
  068270(셀트리온·바이오 적자년 포함)·000270(기아·자본집약). 업종·모델 다양성 커버.
- 비교: 전수 스냅샷 아님. 셀 ~20개 — verdict 판정 5축·peer 라벨 3개·아크 순서 11·
  thesis 기둥 수 3·valuation 모델선택 1 (= 결론 바뀌는 지점만).
- 골든: Python buildReportModel 출력에서 추출(체크인 JSON fixture).
- TS 측 미러: macroSimCompute.test.ts 처럼 TS build 결과의 같은 셀을 하드코딩 골든과 비교.
- 허용: 판정·라벨·순서는 정확 일치(==). 내재가치 같은 부동소수는 #4(pyodide 단일)라 parity 면제.
```

- **CI 배선**: `tests/run.py` story 게이트에 추가(strict). macro `macroSimCompute.test.ts` 가 ci-fast 에 있는 것과 동형.
- **안 하는 것**: 전체 ReportModel 스냅샷 parity(섹션 문장 전수) — 텍스트는 자연어라 brittle, 결론 불변 셀만 핀. 거시 선례 §4 "대표 희소 셀" 규율.

---

## 5. 가드레일 — no-graph-regression + emitter 위치

### 5.1 emitter 는 ai/agent.py 가 아니다

- `buildReportModel` 은 `src/dartlab/story/report.py` (L3) — **ai/ 밖**. `Company.report()` 가 lazy 호출. AI 엔진 본체(`ai/agent.py` chat-native + 자율 tool calling)는 무변경.
- 신규 클래스 명명 금지: `*Loop`/`*Graph`/`*Kernel` 안 씀(`checkAgentBoundary.py:157`). emitter 는 함수(`buildReportModel`)·dataclass 아닌 TypedDict.
- 5패스 노드 이름(`BriefNode`·`runWorkPass` 등 `checkAgentBoundary.py:82-95`) 식별자 안 씀.

### 5.2 companyStory MCP 부활 차단

- 실측 확인: `companyStory` 는 `mcp/protocol.py:44,215` 의 *제거 문서/에러메시지* 에만 존재. 핸들러 0(0.10 BREAKING). **신규 emitter 를 MCP 도구로 노출 금지** — 데이터 작업대는 `EngineCall`/`RunPython`/`ask` 가 정본. `Company.report()` 는 RunPython 안에서 호출되는 라이브러리 API 일 뿐.
- **가드 명시**: `tests/audit/checkAgentBoundary.py` (이미 `tests/run.py` strict 배선). 추가 가드 불필요 — emitter 가 ai/ 밖이고 *Loop 클래스 아니라 기존 구조 검사로 충분. report.py 가 ai/agent.py 흐름에 노드를 끼우면 `_check_five_pass_node_identifiers` 가 검출.
- **회귀 시나리오 차단**: "리포트를 5패스 verify-강제 파이프라인으로" 같은 시도 = `no-graph-regression` skill + `feedback_no_graph_regression.md`. emitter 는 *단일 함수 호출*, 다단 강제 그래프 아님.

---

## 6. 소비자 마이그레이션 (최소 파손)

| 소비자 | 현 결합 | 마이그레이션 | 파손도 |
|---|---|---|---|
| **CLI `dartlab story`** | `cli/commands/story.py:36` `buildStory` + `:45` `renderStory` | 무변경(레거시 Story dataclass 경로 유지). 신규 `dartlab report <code> [perspective]` 서브커맨드 추가 → `buildReportModel` + 신규 rich 렌더. **둘 공존** | 0 (추가만) |
| **테스트 ~277개** (`tests/story/` 8파일) | 대부분 CORE(블록·catalog·builders) | builders/catalog 유지라 **대부분 무변경**. `test_r31.py:34`(reportTypes·3함수)만 단순화 동반. sixAct 테스트 0(폐기 무파손). 신규 `test_report_parity.py` 추가 | 낮음 (~3 함수 수정) |
| **AI `storyTemplate.py`** | `ai/tools/storyTemplate.py:43-63` 섹션키 *문자열 리터럴* (engine import 0) | 섹션키 어휘 안정 유지 시 무변경. 아크 도입으로 키 추가 시 리터럴 리스트에 *추가*만(rename 안 함) | 0~낮음 |
| **providers** `Company.story()`/`storyTree()` | `dart/company.py:2946`·`edgar/company.py:1872` lazy `buildStory` | 무변경. 신규 `Company.report()` 메서드 *추가*(같은 lazy 패턴) | 0 (추가만) |
| **viz adapter** | `viz/display/adapters.py:881` `narrative.buildActTransitions` | narrative 유지라 무변경 | 0 |
| **MCP** | companyStory 이미 제거 | 확인만(§5.2). 신규 도구 노출 금지 | 0 |
| **landing `_scripts/buildCompanyCharts.py`** | `:122` `sixActScore` import | sixAct 폐기 → hero 레이더 제거 또는 스크립트에서 import 절단 | 낮음(1 import) |
| **prebuild `buildStoryManifest.py`** | `:14` dashboard·`:15` reportTypes | dashboard 데이터를 스크립트 로컬 상수로 이주. reportTypes 는 유지라 무변경 | 낮음 |

---

## 7. 파일 수준 영향 맵

### 7.1 신규 (CREATE)

```
ui/packages/contracts/src/reportModel.ts        — ReportModel·18블록·Thesis/Verdict/Scenario/ValuationView/Driver
ui/packages/contracts/src/reportConstants.ts    — VERDICT_THRESHOLDS·ARC_ORDER (#1,#6 공유 상수)
src/dartlab/story/report.py                      — buildReportModel emitter
src/dartlab/story/arc.py                          — ARC_ORDER·assemble·transition 합성
src/dartlab/story/thesis.py                       — buildThesis (구조화 논증)
src/dartlab/story/constants.py                    — VERDICT_THRESHOLDS·WINDOW_GUARD·PEER_CUTS (Python mirror)
src/dartlab/analysis/moat/__init__.py             — 정량 moat (ROIC 지속·마진안정, 02d)
tests/story/test_report_parity.py                 — N=5 골든 parity (§4.2)
landing/src/lib/report/thesisStruct.ts            — buildThesisStruct (정규식 합성 후계)
```

### 7.2 수정 (EDIT)

```
ui/packages/contracts/src/index.ts               — export './reportModel' './reportConstants'
landing/src/lib/report/model.ts                  — re-export shim 축소(@dartlab/ui-contracts)
landing/src/lib/report/build.ts                  — import 교체·arcStep 부여·신규블록 emit·thesisStruct 배선
landing/src/lib/report/build.ts:1504-1519        — 정규식 thesis → buildThesisStruct 호출
landing/src/lib/report/window.ts:26-43           — WINDOW_GUARD 상수 추출
landing/src/lib/report/peer.ts:42,98             — PEER_CUTS 상수 추출
landing/src/lib/report/render.ts:10              — engineLabel +valuation +forecast
landing/src/routes/.../report/+page.svelte       — 신규 10블록 switch case 추가(graceful)
src/dartlab/story/__init__.py:58,487-488         — sixAct re-export 제거, buildReportModel export
src/dartlab/story/registry.py                     — buildBlocks 를 emitter 재사용 가능하게(소폭)
src/dartlab/story/templates.py:412-543,738-781   — PERSPECTIVE_*·LIFECYCLE_PHASES 삭제
src/dartlab/providers/dart/company.py            — Company.report() 메서드 추가
src/dartlab/providers/edgar/company.py           — Company.report() 메서드 추가
src/dartlab/cli/commands/story.py                — report 서브커맨드 추가
src/dartlab/analysis/valuation/dcf.py:429,455-465,194-197 — 4대 결함 수정(02a)
.github/scripts/prebuild/buildStoryManifest.py   — dashboard 데이터 로컬 이주
landing/_scripts/buildCompanyCharts.py:122       — sixAct import 절단
tests/story/test_r31.py:34                        — reportTypes 단순화 동반
tests/run.py                                      — test_report_parity 게이트 배선
```

### 7.3 삭제 (DELETE)

```
src/dartlab/story/publisher.py                    — 327 LOC, importer 0
src/dartlab/story/sixAct.py                        — 268 LOC, landing 레이더만(폐기)
src/dartlab/story/dashboard.py                     — 121 LOC, prebuild 만(이주)
src/dartlab/story/sections/__init__.py             — 1 LOC, 빈 디렉터리
src/dartlab/story/macro/                            — 1823 LOC, macroReport importer 0
```

### 7.4 의존·순서 (구현 순서)

```
1. contracts: reportModel.ts + reportConstants.ts + index.ts          (계약 SSOT 먼저)
2. landing model.ts shim + build.ts import 교체 + +page.svelte case   (무회귀 통과 확인)
3. Python: constants.py + arc.py + thesis.py + report.py + Company.report()  (emitter)
4. 삭제: publisher/sixAct/dashboard/sections/macro + 소비자 절단        (cruft 제거)
5. 02 능력 격상 배선(valuation/credit/forecast/segment/moat) → 신규 블록 채움
6. test_report_parity.py + tests/run.py 게이트                          (drift 핀)
7. CLI report 서브커맨드 + storyTemplate 키 정합 확인                    (소비자)
```

**롤백**: 계약은 additive 라 1~2 단계는 독립 롤백 가능(shim 되돌리면 끝). 4 단계(삭제) 전 5 단계(능력) 가 신규 블록을 채우는지 확인 후 진행 — 삭제와 신설을 분리 커밋해 회귀 격리.

---

## 8. 수용 게이트 (이 아키텍처가 충족하는 PRD §8)

1. **Thesis-first** = `thesis` 블록 arcStep 0, `buildThesis` 구조화(정규식 폐기). ✅
2. **evidenceRef 결박** = 모든 신규 블록 `refs?: EvidenceRef[]`, ThesisPillar.refs 필수. ✅
3. **약세론 정량 동등** = `Thesis.bearCase` 필수 + `ScenarioSet` bear leg. ✅
4. **콜을 낸다** = `ValuationView.intrinsic` + `Thesis.call` (가정·민감도는 waccBreakdown·scenario.note 노출). ✅
5. **포워드 정량** = forecast 백테스트 능력(02b) → line+callout, 막연 성장 금지. ✅
6. **세그먼트 모델 산출** = `revenue.segment` axisPath + 마진도출(02c) → driverTree. ✅
7. **인과 연쇄** = `transition` 블록 + `arcStep` 11단계 순서. ✅
8. **미검증 확신 금지** = parity 테스트 + 02 능력 백테스트 게이트 후 탑재. ✅
9. **합성점수 영구차단** = `verdict.noComposite: true` 타입 강제. ✅
```
