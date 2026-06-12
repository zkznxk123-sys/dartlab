# 02. Runtime, AI, Services

상태: v1 확정 기준 문서  
범위: runtime contract, public/local adapter, AI provider 직접 연결, Ask 엔진, 챗모드, 터미널모드, 서비스 registry

---

## 1. Runtime 원칙

1. Surface는 데이터를 직접 가져오지 않는다.
2. Surface는 runtime에 데이터를 요청한다.
3. Runtime은 public/local/test adapter를 통해 실제 데이터를 가져온다.
4. Surface는 route, server, static host, local API, provider, workspace 권한을 직접 알지 않는다.
5. public/local 차이는 `runtime.env.kind` 분기보다 adapter polymorphism으로 해결한다.

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

### 3.5 Adapter Response Metadata

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

export interface AiCapabilities {
  enabled: boolean;
  streaming: boolean;
  toolCalling: boolean;
  localWorkspace: boolean;
  providerLabel?: string;
  modelLabel?: string;
  disabledReason?: string;
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

- `enabled: false` 또는 제한된 explain/demo만 허용
- secret 없음
- server-side agent gateway 없음
- local-only tool call 없음

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
- public에서는 local-only command를 숨기거나 disabled 상태로 표시한다.

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
  availability: 'available' | 'disabled' | 'loading' | 'error';
  reason?: string;
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
- disabled AI descriptor
- public-safe export only

금지:

- TerminalSurface 내부에서 service별 API endpoint 분기
- provider SDK 또는 API key를 descriptor에 노출
- public registry에 local-only command 노출
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

Storage key 예:

```ts
export type RuntimeStorageKey =
  | 'lastCompany'
  | 'recentCompanies'
  | 'terminalChartState'
  | 'terminalLanguage'
  | 'viewerLayout'
  | 'askDraft';
```

---

## 9. Adapter 책임

### 9.1 Public Adapter

책임:

- GitHub Pages base path 처리
- static JSON/parquet/HF dataset 접근
- 공개 viewer route href 생성
- read-only storage
- public-safe telemetry
- AI disabled 또는 demo-only
- public-safe service registry 제공

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
