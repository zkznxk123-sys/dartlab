# 02. Runtime, AI, Services

상태: v2 확정 기준 문서 (개정 이력은 07 원장)  
범위: runtime contract, public/local adapter, AI provider 직접 연결, Ask 엔진, 챗모드, 터미널모드, 서비스 registry

---

## 1. Runtime 원칙

1. Surface는 데이터를 직접 가져오지 않는다.
2. Surface는 runtime에 데이터를 요청한다.
3. Runtime은 public/local/test adapter를 통해 실제 데이터를 가져온다.
4. Surface는 route, server, static host, local API, provider, workspace 권한을 직접 알지 않는다.
5. public/local 차이는 adapter polymorphism으로만 해결한다 — surface 안의 `runtime.env.kind` 분기 코드를 금지한다(§10과 동일 강도).

Surface 내부 금지:

```ts
fetch('/api/company/005930/meta');
fetch('https://huggingface.co/...');
import { base } from '$app/paths';
window.localStorage.getItem('lastCompany');
window.location.href = '/viewer/company/005930';
```

Surface 내부 허용:

```ts
const runtime = useDartLabRuntime();
const company = await runtime.company.getCompany(code);
const url = runtime.viewer.urlForCompany(code);
await runtime.navigation.toViewer(code);
await runtime.storage.set('lastCompany', company);
await runtime.services.executeCommand({ commandId: 'filing.openRegularList', context });
```

---

## 2. Runtime 최상위 계약

```ts
export interface DartLabRuntime {
  env: RuntimeEnvironment;
  company: CompanyPort;
  price: PricePort;
  filing: FilingPort;
  finance: FinancePort;
  viewer: ViewerPort;
  scan: ScanPort;
  map: MapPort;
  search: SearchPort;
  ai: AiPort;
  services: ServicesPort;
  navigation: NavigationPort;
  storage: StoragePort;
  telemetry: TelemetryPort;
  featureFlags: FeatureFlagPort;
}

export type RuntimeKind = 'public' | 'local' | 'test';

export interface RuntimeEnvironment {
  kind: RuntimeKind;
  basePath: string;
  locale: 'ko' | 'en';
  marketDefault: 'KR' | 'US';
  buildVersion: string;
  readonly: boolean;
}
```

---

## 3. Data Port 계약

### 3.1 CompanyPort

```ts
export interface CompanyPort {
  search(query: string, limit?: number): Promise<CompanySearchHit[]>;
  getCompany(code: string): Promise<CompanyProfile>;
  getCompanyUniverse(): Promise<CompanyUniverse>;
  getRecentCompanies(): Promise<RecentCompany[]>;
  putRecentCompany(company: RecentCompany): Promise<void>;
}
```

### 3.2 PricePort

```ts
export interface PricePort {
  getInitialCandles(input: PriceInitialRequest): Promise<CompanyPriceSeries | null>;
  getOlderCandles(input: PriceOlderRequest): Promise<Candle[]>;
  getRecentMarketCandles(input: RecentMarketRequest): Promise<Map<string, Candle[]>>;
  getPriceEvents(input: PriceEventsRequest): Promise<PriceEventsPayload>;
}
```

### 3.3 FilingPort

```ts
export interface FilingPort {
  getRegularFilings(code: string, limit?: number): Promise<RegularFiling[]>;
  getNonRegularFilings(code: string, limit?: number): Promise<NonRegularFiling[]>;
  getPanelToc(code: string): Promise<PanelToc>;
  getPanelGrid(input: PanelGridRequest): Promise<PanelGrid>;
  getPanelInit(code: string): Promise<PanelInit>;
  getReportFacts(code: string): Promise<ReportFact[]>;
  getDisclosureChanges(code: string, limit?: number): Promise<DisclosureChange[]>;
}
```

### 3.4 ViewerPort

```ts
export interface ViewerPort {
  mode: 'embedded-route' | 'component' | 'external-url';
  urlForCompany(code: string, options?: ViewerOpenOptions): string | null;
  openCompany(code: string, options?: ViewerOpenOptions): Promise<void>;
  openFiling(filing: RegularFiling | NonRegularFiling): Promise<void>;
}
```

### 3.5 FinancePort / ScanPort / MapPort / SearchPort

```ts
export interface FinancePort {
  getFinanceBundle(code: string): Promise<TerminalFinanceBundle>;          // terminal 중앙 재무 요약·시계열
  getStatementTable(input: StatementTableRequest): Promise<StatementTable>; // IS/BS/CF 표 (기간·scope)
  exportCsv(input: FinanceExportRequest): Promise<Blob>;
}

export interface ScanPort {
  listTableSources(): Promise<ScanTableSource[]>; // parquet/duck 테이블 소스 공급 — public=static/HF, local=로컬 캐시/API
  getPresets(): Promise<ScanPreset[]>;
  savePreset(preset: ScanPreset): Promise<void>;
}

export interface MapPort {
  listIndustries(): Promise<IndustrySummary[]>;
  getIndustryMap(id: string): Promise<IndustryMapData>; // public=static map JSON(HF seed), local=로컬 API
}

export interface SearchPort {
  query(input: SearchQuery): Promise<SearchResultPage>;
}
```

FinancePort 메서드 표면은 단계-0 census(`workbench.ts` export + `localAdapter.ts` 25메서드 합집합)로 확정하며, 확정 시 본 문서 개정 entry를 07 원장에 남긴다.

원칙: 쿼리 실행 엔진(duckdb-wasm 등)은 surface 내부 구현 detail이다 — port는 데이터 소스 공급과 저장만 담당한다.

ScanPort 진화 경로(예약): 로컬 1차 경로는 local adapter가 로컬 서버 parquet URL을 소스로 공급한다(엔진=duckdb-wasm 유지, 계약 무변경). 서버측 질의가 필요해지면 `ScanPort.query()` 승격을 예약한다 — 그때 wasm은 public adapter 내부 구현으로 내려가며, 이 역전은 계약 개정 작업 단위로만 한다.

### 3.6 Adapter Response Metadata

데이터 adapter 반환값은 가능한 한 다음 metadata를 포함한다.

```ts
export interface RuntimeDataEnvelope<T> {
  data: T;
  provenance: DataProvenance[];
  asOf: string;
  stale: boolean;
  coverage: DataCoverage;
}
```

원칙:

- stale 데이터를 정상 최신 데이터처럼 표시하지 않는다.
- public static 데이터와 local cache 데이터의 출처를 UI에서 구분 가능하게 한다.
- AI 답변은 원천 데이터가 아니며 evidence와 별도로 표시한다.
- **Port 메서드는 required다.** 어댑터가 지원하지 못하는 기능은 명시적 `unavailable` 상태로 반환한다. optional 메서드(`x?:`) + 조용한 fallback(`localAdapter()?.x() ?? HF로드()`) 구조를 금지한다 — 현행 terminal 코드의 기본 패턴이 바로 이것이며, 로컬 패리티 누락을 컴파일도 테스트도 못 잡게 만든다. conformance test 가 전 포트 메서드의 public/local 구현 존재를 기계 검사한다(05 §2).
- **시장 고유 식별자는 source-namespace + discriminated union으로만** 계약에 들어간다 — `dart:${rceptNo}` / `edgar:${accessionNo}`. KR 전용 필드를 계약 타입에 직박지 않는다(US/EDGAR 확장 대비).

---

## 4. AiPort

로컬 앱은 AI provider를 직접 붙인다.  
단 provider SDK, API key, model 선택, tool execution은 `localAiAdapter`와 Ask 엔진 뒤에 있어야 한다. Surface는 Ask 엔진의 message/event 계약만 사용한다.

```ts
export interface AiPort {
  capabilities(): Promise<AiCapabilities>;
  ask(input: AiAskInput): Promise<AiAskResult>;
  streamAsk(input: AiAskInput): AsyncIterable<AiStreamEvent>;
  runTool(input: AiToolRunInput): Promise<AiToolRunResult>;
  explainEvidence(input: EvidenceExplainInput): Promise<EvidenceExplainResult>;
  listModes(): Promise<AiMode[]>;
  setMode(mode: AiModeId): Promise<void>;
  getMode(): Promise<AiModeId>;
}

export type AiTier = 'advanced' | 'onDevice' | 'deterministic' | 'none';
// none = test fake 초기화 전 전용 — public은 항상 deterministic 이상, local 무provider도 deterministic으로 동작한다.

export interface AiCapabilities {
  tier: AiTier;                  // advanced=로컬 엔진, onDevice=WebGPU, deterministic=결정론 Q&A
  streaming: boolean;
  toolCalling: boolean;
  localWorkspace: boolean;
  deterministicAnswers: boolean; // 결정론 Q&A — public에서도 항상 true
  providerLabel?: string;
  modelLabel?: string;
  upgradeHint?: string;          // advanced 미만 tier에서 로컬 업그레이드 안내 문구
}

export type AiModeId = 'chat' | 'terminal';

export interface AiMode {
  id: AiModeId;
  label: string;
  description: string;
  available: boolean;
}
```

Public adapter:

- `tier: 'deterministic'` 기본 — 결정론 Q&A(Tier0)는 항상 동작한다.
- WebGPU 가용 기기(`webgpuUsable` 실측 게이트 — requestAdapter 검사, 작동 어댑터 없는 기기의 헛다운로드 차단)에서는 `tier: 'onDevice'`로 승급 — 온디바이스 추론(@mlc-ai/web-llm), 서버 0, secret 0.
- **이미 출시된 공개 AskDrawer(Tier0 + WebGPU)의 회귀를 금지한다.**
- server-side agent gateway 없음, local-only tool call 없음.
- `upgradeHint`로 로컬 고급 엔진의 존재를 알린다 — 숨기지 않는다.

Local adapter:

- `/api/agent/*` 또는 현재 agent gateway 사용
- provider settings와 연동
- provider SDK/API key는 local server 또는 local adapter boundary 안에만 둔다.
- Ask 엔진을 통해 chat mode와 terminal mode를 모두 실행한다.
- workspace context 첨부 가능
- viewer selection, terminal state, chart cursor, filing evidence를 context로 전달한다.
- terminal mode에서는 `runtime.services`의 도구와 데이터 포트를 tool registry로 노출한다.

---

## 5. Ask 엔진

Ask 엔진은 로컬 AI 상호작용의 관문이다.

책임:

1. chat mode와 terminal mode의 공통 message state 관리
2. provider 선택과 model 선택 위임
3. stream event normalize
4. tool call request/response normalize
5. evidence reference 연결
6. provider error, rate limit, timeout 표시 규칙
7. local workspace permission 확인
8. terminal service command 실행 요청
9. AG-UI allowlist 소유 — 렌더 허용 이벤트 목록은 단계-1b에서 현행 `ui/web` agent gateway 이벤트 스키마 census로 확정해 `contracts/ai.ts`에 박는다(07 원장 entry 동반). 목록 밖 이벤트는 렌더하지 않고 드롭한다.

금지:

- surface별로 별도 AI 구현을 만든다.
- provider별 parser를 TerminalSurface나 ViewerSurface 안에 둔다.
- raw tool args/result를 일반 답변 UI에 섞는다.
- evidence 없는 AI 답변을 원천 데이터처럼 표시한다.

---

## 6. Chat Mode와 Terminal Mode

### 6.1 Chat Mode

목적:

- 일반 질의
- 회사 검색
- 문맥 요약
- 작업 지시
- terminal mode 진입 준비

특성:

- 기본 route는 `chat/+page.svelte`
- terminal이 필요하면 같은 Ask thread와 context를 유지한 채 terminal mode로 전환한다.
- 회사 context가 없으면 search service를 먼저 실행한다.

### 6.2 Terminal Mode

목적:

- 현재 회사, 차트, 공시, 재무, viewer selection, service command를 한 화면에서 실행한다.
- 로컬 서비스 대부분을 붙이는 운영 화면이다.

연결 서비스:

- company/search
- price/market
- filing cache
- viewer
- finance table/export
- screener/scan
- workspace recent/pin/history
- evidence/source/provenance
- cache refresh/index status
- AI tools
- local file/export helper

규칙:

- TerminalSurface는 서비스 구현을 import하지 않는다.
- `ServicesPort`의 descriptor와 command만 렌더한다.
- command 실행 결과는 status, toast, panel update, Ask event 중 하나로 normalize한다.
- public에서는 local-only command를 `localOnly` descriptor + `upgradeHint`로 표시한다. 완전 숨김은 시스템 명령만 허용한다(03 §1-7).

---

## 7. ServicesPort

```ts
export interface ServicesPort {
  listServices(context: ServiceContext): Promise<ServiceDescriptor[]>;
  listCommands(context: ServiceContext): Promise<ServiceCommand[]>;
  executeCommand(input: ServiceCommandInput): Promise<ServiceCommandResult>;
  subscribeStatus?(cb: (status: ServiceStatusEvent) => void): () => void;
}

export interface ServiceDescriptor {
  id: string;
  label: string;
  group: 'market' | 'filing' | 'finance' | 'viewer' | 'ai' | 'workspace' | 'export' | 'system';
  availability: 'available' | 'localOnly' | 'disabled' | 'loading' | 'error';
  reason?: string;
  upgradeHint?: string; // localOnly 일 때 "로컬에서 사용 가능" 안내 — command palette 가 렌더
}

export interface ServiceCommand {
  id: string;
  serviceId: string;
  label: string;
  icon?: string;
  shortcut?: string;
  mode: 'chat' | 'terminal' | 'both';
  requires?: ServiceRequirement[];
}
```

Local registry:

- local company/search API
- price/market API
- filing cache and viewer
- finance table/export
- screener/scan
- workspace recent/pin/history
- Ask engine tools
- cache refresh/index status
- local file/export helpers

Public registry:

- public search
- static/HF market data
- static disclosure metadata
- public viewer link
- deterministic/onDevice tier AI descriptor (`upgradeHint` 포함 — disabled 아님, §4)
- public-safe export only + localOnly descriptor (실행 불가·upgradeHint 표시)

금지:

- TerminalSurface 내부에서 service별 API endpoint 분기
- provider SDK 또는 API key를 descriptor에 노출
- public registry에서 local-only command를 **실행 가능하게** 노출 (단, `localOnly` descriptor 로 존재는 보여준다 — funnel)
- 승격 가능(또는 로컬 전용 상위) 기능의 완전 숨김 — 완전 숨김은 cache refresh 같은 시스템 명령에만 허용
- service 실패를 정상 데이터처럼 렌더

---

## 8. NavigationPort와 StoragePort

```ts
export interface NavigationPort {
  toTerminal(code: string): Promise<void>;
  toViewer(code: string, options?: ViewerOpenOptions): Promise<void>;
  toCompany(code: string): Promise<void>;
  toAsk(initialContext?: AskContext): Promise<void>;
  href(route: DartLabRoute): string;
}

export interface StoragePort {
  get<T>(key: RuntimeStorageKey): Promise<T | null>;
  set<T>(key: RuntimeStorageKey, value: T): Promise<void>;
  remove(key: RuntimeStorageKey): Promise<void>;
  subscribe?<T>(key: RuntimeStorageKey, cb: (value: T | null) => void): () => void;
}
```

Storage key 규칙 — surface 네임스페이스 키 기본:

```ts
export type RuntimeStorageKey = `${DartLabSurfaceId}.${string}` | GlobalStorageKey;
export type GlobalStorageKey = 'lastCompany' | 'recentCompanies' | 'locale';
// 예: 'terminal.chartState', 'terminal.backtestConfig', 'viewer.layout', 'ask.draft'
```

surface 내부 기능 추가가 contracts 개정을 강제하지 않도록 네임스페이스 템플릿 키를 기본으로 한다. 닫힌 union은 전역 키만.

```ts
export interface TelemetryPort {
  event(name: string, props?: Record<string, string | number>): void; // public=무PII 집계만, local=옵트인 로컬 로그
}

export interface FeatureFlagPort {
  isEnabled(flag: DartLabFeatureFlag): boolean;
}
```

---

## 9. Adapter 책임

### 9.1 Public Adapter

책임:

- GitHub Pages base path 처리
- static JSON/parquet/HF dataset 접근 — hyparquet, hfProxy worker, static JSON 은 어댑터 내부 구현 detail 이며 surface 는 모른다
- 공개 viewer route href 생성
- 서버측 쓰기 없음 — storage 쓰기는 브라우저(localStorage 등) 한정
- public-safe telemetry (무PII 집계만)
- AI tier 'deterministic' 기본 + WebGPU 가용 시 'onDevice' 승급 (§4)
- public-safe service registry 제공 (localOnly descriptor 포함)

금지:

- localhost API 호출
- API key 요구
- workspace file access
- local database assumption
- provider 설정 UI 노출

### 9.2 Local Adapter

책임:

- `/api/company/:code/meta`
- `/api/company/:code/panel/init`
- `/api/company/:code/panel/grid`
- `/api/dartlab/price-events`
- `/api/status`
- `/api/agent/*`
- provider settings
- AI provider 직접 연결
- Ask engine chat/terminal mode 실행
- service registry와 tool registry 제공
- workspace state
- local file/cache status
- terminal mode에서 로컬 service command 노출

금지:

- HF/static fallback을 UI surface에 노출
- provider SDK를 surface로 전달
- AI key 또는 raw provider config를 client visible state로 노출

### 9.3 Test Adapter

책임:

- visual regression fixture
- unit/integration test
- 네트워크 없이 surface 렌더 검증
- public/local fixture conformance

---

## 10. 기능 승격 경로 (local → public)

기능은 로컬에서 먼저 개발한다. 공개 승격은 게이트를 통과한 것만 한다.

절차:

1. 트리거 — 로컬 기능이 1회 릴리스 동안 안정된 뒤 운영자가 발의한다. AI 세션은 체크리스트를 채워 제안만 한다.
2. 판정자 — 운영자 단독.
3. 기록 — 판정 결과를 07 원장에 `승격(기능명)` entry로 남긴다.

승격 체크리스트:

1. 공개 데이터 가용성 — static/HF만으로 해당 기능의 데이터가 충족되는가.
2. AI tier 매핑 — deterministic으로 동작 / onDevice로 동작 / 승격 불가(advanced 전용) 중 어디인가.
3. 열화 UX 문구 — 공개판에서 무엇이 빠지고, `upgradeHint`는 뭐라고 쓰는가.
4. 성능·번들 예산 — Pages 번들 무게와 콜드 fetch 시간이 예산 안인가.
5. SEO/llms.txt 영향 — 공개 route·메타데이터 변경이 있는가.
6. 무중단 smoke — landing build + 기존 공개 route 검증 통과.

원칙:

- surface는 capability 검사로 렌더한다 — public/local 분기 코드를 만들지 않는다.
- 승격 가능(또는 로컬 전용 상위) 기능은 public에서 숨기지 않는다. tier 표시 + `upgradeHint` + 설치 CTA로 보여준다.
- 승격은 어댑터에 capability 구현을 추가하는 일이지, surface를 고치는 일이 아니어야 한다. surface 수정이 필요하면 설계 위반 신호다.
