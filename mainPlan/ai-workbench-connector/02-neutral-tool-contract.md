# 02. 중립 Tool Contract 와 Evidence Pack

상태: 비전 PRD v0.1
범위: 외부 AI 가 호출할 DartLab tool 의 최소 집합, 응답 envelope, evidence schema, 금지 tool.

---

## 1. 결정

tool 은 많으면 안 된다. 외부 AI 에 DartLab 의 내부 API 수십 개를 노출하면 모델이 선택을 헷갈리고, 보안 경계가 흐려진다.

초기 최적 tool set 은 8개다.

```text
resolve_entity
get_company_snapshot
search_filings
get_filing_evidence
get_financial_panel
compare_companies
get_watchlist_delta
create_dartlab_link
```

`get_data_freshness` 는 별도 tool 로 둘 수 있지만, 대부분의 응답 envelope 에 `freshness` 를 포함하면 독립 tool 필요성이 줄어든다. 운영상 필요하면 Phase 1.5 로 추가한다.

---

## 2. Canonical Tool 목록

| Tool | Plane | 인증 | 책임 |
|---|---|---|---|
| `resolve_entity` | Public Evidence | optional | 회사명/코드/별칭을 canonical company 로 해석 |
| `get_company_snapshot` | Public Evidence | optional | 회사 개요, 최신 공시/재무 요약, 사용 가능한 DartLab 링크 |
| `search_filings` | Public Evidence | optional | 회사/키워드/기간 기준 공시 목록 검색 |
| `get_filing_evidence` | Public Evidence | optional | 특정 공시 또는 topic 에 대한 근거 chunk 반환 |
| `get_financial_panel` | Public Evidence | optional | 재무제표/핵심 계정/기간 패널 반환 |
| `compare_companies` | Public Evidence | optional | 동종/사용자 지정 회사 비교 evidence pack |
| `get_watchlist_delta` | User Context | OAuth required | 내 워치리스트의 마지막 기준 이후 공시/재무 변화 |
| `create_dartlab_link` | Link-State | public/private 분기 | viewer/terminal deep link 또는 stateId 생성 |

---

## 3. Tool 상세

### `resolve_entity`

입력:

```ts
{
  query: string
  market?: "KR" | "US"
  limit?: number
}
```

출력:

```ts
{
  data: {
    matches: Array<{
      market: string
      code: string
      name: string
      aliases: string[]
      confidence: "exact" | "alias" | "fuzzy"
    }>
  }
}
```

### `get_company_snapshot`

입력:

```ts
{
  market?: "KR" | "US"
  code: string
  include?: Array<"filings" | "finance" | "links" | "freshness">
}
```

책임:

- 회사 기본 식별자
- 최근 공시 상위 N 개
- 최근 재무 핵심 수치
- viewer/terminal link 후보
- data freshness

### `search_filings`

입력:

```ts
{
  market?: "KR" | "US"
  code?: string
  query?: string
  dateFrom?: string
  dateTo?: string
  limit?: number
}
```

책임:

- 공시 metadata 검색
- receipt 번호, 제목, 날짜, 종류, source link 반환
- 본문 chunk 는 반환하지 않음

### `get_filing_evidence`

입력:

```ts
{
  market?: "KR" | "US"
  code?: string
  rceptNo?: string
  topic?: "business" | "supplyChain" | "risk" | "governance" | "shareholderReturn" | "rnd" | "workforce" | "finance"
  maxChunks?: number
}
```

책임:

- 질문 topic 에 맞는 공시 근거 chunk
- section label, page/paragraph hint, excerpt
- viewer anchor
- external_untrusted 표시

### `get_financial_panel`

입력:

```ts
{
  market?: "KR" | "US"
  code: string
  statement?: "BS" | "IS" | "CIS" | "CF"
  period?: string
  accounts?: string[]
  limit?: number
}
```

책임:

- 재무제표 패널
- 계정 표준명과 원문 계정명
- fiscal period, currency/unit, source filing
- 결손은 0 대체 금지

### `compare_companies`

입력:

```ts
{
  market?: "KR" | "US"
  baseCode: string
  peerCodes?: string[]
  topic?: "profitability" | "growth" | "leverage" | "cashflow" | "valuation" | "disclosure"
  period?: string
}
```

책임:

- 동종 또는 지정 peer 비교
- percentile/ratio 는 source와 계산 방식 명시
- 추천/등급/목표주가 금지

### `get_watchlist_delta`

입력:

```ts
{
  since?: string
  watchlistId?: string
  include?: Array<"filings" | "financeFreshness" | "links">
}
```

권한:

```text
watchlist:read
```

책임:

- 사용자의 watchlist 에 속한 회사만 조회
- 마지막 방문/지정 since 이후 변화
- "완결" 주장 금지
- no-store 기본

### `create_dartlab_link`

입력:

```ts
{
  target: "viewer" | "terminal"
  market?: "KR" | "US"
  code: string
  rceptNo?: string
  section?: string
  tab?: string
  period?: string
  compareCodes?: string[]
  stateVisibility?: "public" | "private"
}
```

책임:

- viewer 또는 terminal deep link 생성
- public state 는 개인 정보 금지
- private state 는 OAuth + ACL

---

## 4. Evidence Pack Envelope

모든 tool response 는 같은 envelope 를 쓴다.

```ts
type DartLabToolResponse<T> = {
  requestId: string
  kind: string
  asOf: string
  locale: "ko-KR" | "en-US"
  data: T
  evidence: EvidenceRef[]
  freshness: Freshness
  links: DartLabLinks
  limitations: string[]
  safety: SafetyFlags
}
```

필드 의미:

| 필드 | 의미 |
|---|---|
| `requestId` | 운영 추적용. 사용자 PII 직접 포함 금지 |
| `kind` | 응답 종류 |
| `asOf` | 응답 기준일 |
| `locale` | 응답 locale |
| `data` | tool 별 structured content |
| `evidence` | claim 의 근거 |
| `freshness` | source 업데이트/조회/캐시 상태 |
| `links` | viewer/terminal/source link |
| `limitations` | 데이터 한계, 투자 조언 아님 |
| `safety` | external untrusted, evidenceOnly 등 |

---

## 5. EvidenceRef

```ts
type EvidenceRef = {
  id: string
  sourceType:
    | "dart_filing"
    | "edgar_filing"
    | "financial_statement"
    | "watchlist_delta"
    | "derived_metric"
    | "dartlab_state"
  title: string
  url?: string
  market?: "KR" | "US"
  companyCode?: string
  companyName?: string
  dartReceiptNo?: string
  accessionNo?: string
  section?: string
  tableRef?: string
  valueRef?: string
  dateRef?: string
  excerpt?: string
  pageHint?: number
  confidence: "direct" | "derived" | "estimated"
  contentTrust: "internal_structured" | "external_untrusted"
}
```

원칙:

- `excerpt` 는 짧게. 원문 전체를 모델에 던지지 않는다.
- 공시 본문은 항상 `external_untrusted`.
- 숫자 claim 은 `valueRef` 또는 `tableRef` 에 닿아야 한다.
- 날짜 claim 은 `dateRef` 또는 `asOf` 에 닿아야 한다.
- derived metric 은 계산식 또는 source fields 를 `data` 안에 명시한다.

---

## 6. Freshness

```ts
type Freshness = {
  source: "HF" | "DART" | "EDGAR" | "DartLabCache" | "UserState"
  sourceUpdatedAt?: string
  fetchedAt: string
  cacheStatus: "hit" | "miss" | "revalidated" | "bypass"
  stale: boolean
  freshnessLabel?: string
}
```

정직 문구:

- "이 fetch 기준"
- "DartLab 공개 데이터 기준"
- "이 기기/계정의 마지막 방문 기준"

금지 문구:

- "모든 공시 확인 완료"
- "신규 없음" 단정
- "실시간"
- "알림 발송됨"

---

## 7. SafetyFlags

```ts
type SafetyFlags = {
  evidenceOnly: true
  notInvestmentAdvice: true
  containsExternalUntrustedContent: boolean
  personalDataIncluded: boolean
  requiresOAuth: boolean
  readOnly: boolean
}
```

초기 connector 는 `readOnly: true` 가 원칙이다. `create_dartlab_link` 의 state 저장만 예외적으로 write 성격을 가질 수 있으나, 그 경우도 거래/추천/메모 작성이 아니다.

---

## 8. 금지 Tool

외부 AI 에 노출 금지:

```text
run_python
run_sql
read_file
write_file
fetch_private_dataset
raw_hf_token_access
admin_query
bulk_export_all_filings
trade_order
recommend_buy_sell
set_target_price
```

DartLab 내부 `runtime.mcp` 나 local workbench 에 범용 도구가 있더라도, public connector 는 별개의 좁은 tool surface 를 가져야 한다.

