# dartlab 운영문서

프로젝트 전체의 설계 규칙, 엔진별 운영 체계, 품질 관리 절차를 한곳에 모은다.

## 진입점

## 도메인 룰 — 코드 폴더 안 README (2026-04-15 이동, 작업 위치 옆에서 즉시 노출)

| 엔진 | 룰 위치 | 한 줄 요약 |
|---|---|---|
| Company facade | [src/dartlab/README.md](../src/dartlab/README.md) | sections 사상, 4 namespace, canHandle 라우팅 |
| ai/ | [src/dartlab/ai/README.md](../src/dartlab/ai/README.md) | 적극적 분석가, 7+1 원칙, override 매커니즘 |
| analysis/ | [src/dartlab/analysis/README.md](../src/dartlab/analysis/README.md) | 재무 14축 + 전망 + 가치평가, 6막 인과 |
| analysis/credit | [src/dartlab/analysis/CREDIT.md](../src/dartlab/analysis/CREDIT.md) | 독립 신용평가 (dCR 20단계, 7축) |
| quant/ | [src/dartlab/quant/README.md](../src/dartlab/quant/README.md) | 가격 정량 신호 |
| macro/ | [src/dartlab/macro/README.md](../src/dartlab/macro/README.md) | 시장 매크로 — Company 불필요 |
| scan/ | [src/dartlab/scan/README.md](../src/dartlab/scan/README.md) | 13축 시장 횡단 — 사전 빌드 |
| gather/ | [src/dartlab/gather/README.md](../src/dartlab/gather/README.md) | 외부 시장 데이터 (주가/수급/매크로/뉴스) |
| gather/listing | [src/dartlab/gather/LISTING.md](../src/dartlab/gather/LISTING.md) | `dartlab.listing(kind, ...)` 단일 진입점 |
| core/search | [src/dartlab/core/search/README.md](../src/dartlab/core/search/README.md) | 공시 시맨틱 검색 *(alpha)* |
| review/ | [src/dartlab/review/README.md](../src/dartlab/review/README.md) | 이야기꾼 — 보고서 조립 |
| guide/ | [src/dartlab/guide/README.md](../src/dartlab/guide/README.md) | 안내 데스크 |
| providers/edgar | [src/dartlab/providers/edgar/README.md](../src/dartlab/providers/edgar/README.md) | EDGAR 동기화 + EXEMPT |

## ops/ — Cross-cutting 규칙 (한 엔진에 묶을 수 없는 것)

| 문서 | 한 줄 요약 |
|---|---|
| **[api-contract.md](api-contract.md)** | **모든 API 호출 규칙 — 단일 진입점 + 파라미터 계약. 새 함수 추가 전 필독.** |
| **[architecture.md](architecture.md)** | **전체 청사진 — 레이어, 엔진, 규칙** |
| **[testing.md](testing.md)** | **테스트 체계 — 마커, 커버리지 90% 목표, CI** |
| **[code.md](code.md)** | **camelCase, 독스트링 9섹션, 릴리즈, Git** |
| **[issues.md](issues.md)** | **이슈 관리 — GitHub Issue + 테스트 + 커밋 연결** |
| [data.md](data.md) | HF 데이터셋, 수집 파이프라인, 카테고리 |
| [mappers.md](mappers.md) | 매퍼 통합 — 계정/topic/alias/flow/notes |
| [pyodide.md](pyodide.md) | 브라우저/Excel WASM *(alpha)* |
| [industry.md](industry.md) | 산업 매퍼엔진 |
| [channel.md](channel.md) | 외부 공유 (DevTunnels) |
| [spaces.md](spaces.md) | HF Spaces — API + MCP |
| [vscode.md](vscode.md) | VSCode 확장 |
| [ui.md](ui.md) | Svelte SPA |
| [viz.md](viz.md) | 차트 + 다이어그램 |
| [experiments.md](experiments.md) | 실험 규칙, 흡수 판단 |
| [engineAudit.md](engineAudit.md) | 엔진 audit 절차 |
| [selfai.md](selfai.md) | (deprecated 흐름 보존) |

## 레이어 아키텍처

"엔진 = 도구 (숫자만), review = 이야기꾼, AI/사람 = 소비자" (1.0.0 리팩토링)

```
┌──────────────────────────────────────────────────────────────────────┐
│ L4  소비자          ai/  +  사람 (투자자/분석가)                      │
│                     해석과 판단 (review 보고서를 읽고 판단)            │
├──────────────────────────────────────────────────────────────────────┤
│ L3  이야기꾼        review/                                           │
│                     L2 5엔진 + scan 소비 → 보고서 조립 (6막 서사)     │
│                     narrate/builders/catalog/templates/formats       │
├──────────────────────────────────────────────────────────────────────┤
│ L2  분석 엔진       analysis/  quant/  credit/  macro/                │
│                     (4개 동등, 상호 import 금지)                       │
│                     dict/숫자/DataFrame만 반환 — 해석/블록 생성 금지   │
│  ├── analysis/     financial(14축) + forecast + valuation             │
│  ├── quant/        기술적 신호 + 리스크 + 전략 백테스트               │
│  ├── credit/       독립 신용등급 (dCR 20단계, 7축)                    │
│  └── macro/        거시 11축 + scenarios(110) + historicalContext     │
├──────────────────────────────────────────────────────────────────────┤
│ L1.5 데이터 빌더    scan/        전종목 사전 빌드 (parquet)            │
│                     L2가 scan을 읽는 것은 하향 참조로 허용            │
├──────────────────────────────────────────────────────────────────────┤
│ L1  데이터 수집     providers/   DART, EDGAR, EDINET                  │
│                     gather/      주가, 수급, FRED/ECOS 매크로, 뉴스   │
├──────────────────────────────────────────────────────────────────────┤
│ L0  인프라          core/        helpers, finance, docs, memory, ...  │
│                     SSOT 헬퍼: toDictBySnakeId, memoized_calc,        │
│                                parseNumStr, safeDiv, fmtBig, ...     │
└──────────────────────────────────────────────────────────────────────┘
                       교차 관심사: guide/ (모든 레이어 가능)
```

## 엔진 독립 규칙 (import 방향)

- **L0 ← L1 ← L1.5 ← L2 ← L3 ← L4** (하향만 허용)
- **L2 엔진 간 상호 import 금지** (analysis↛quant, macro↛credit 등 — 0건 유지)
- **L2 엔진 → L3 역방향 금지** — 엔진은 dict만, 서사/블록/보고서 생성 금지 (0건 유지)
- **L2 → L1.5(scan) 하향 참조 허용** — scan은 순수 데이터 빌더
- 공유 데이터는 L0/L1에서 가져온다. 공유 헬퍼는 core SSOT (`core/finance/helpers.py` 등)
- **review가 조합한다** — 5개 엔진의 결과를 6막 서사로 조립, narrate 문장 생성

## 엔진 호출 패턴

모든 엔진이 동일 패턴: `엔진("그룹", "축")` 또는 `엔진("축")`.

### analysis — 재무+전망+가치평가
```python
c.analysis("financial", "수익성")          # 그룹 + 하위
c.analysis("financial", "profitability")  # 영문도 동일
c.analysis("valuation")                   # 그룹 가이드
c.analysis("forecast", "revenue")         # 전망
c.analysis()                              # 전체 가이드
```

### scan — 시장 횡단분석
```python
dartlab.scan("financial", "profitability")  # 그룹 + 하위
dartlab.scan("governance")                  # 단일 축
dartlab.scan("screen", "value")             # 스크리닝 프리셋
dartlab.scan("account", "매출액")            # 계정 시계열
```

### 한글/영문 둘 다 가능
```python
c.analysis("financial", "수익성")          # 한글
c.analysis("financial", "profitability")  # 영문
dartlab.scan("financial", "수익성")        # 한글
dartlab.scan("financial", "profitability") # 영문
```

## 공통 규칙

- **코드 스타일**: camelCase (함수/변수), 이동된 snake_case는 하위호환 유지
- **진입점**: 종목코드 하나면 끝. `import dartlab` 하나로 모든 기능 접근
- **README 동기화**: 기능 변경 시 영문+한국어 동시 반영
- **노트북 감사**: 노트북 코드는 실행 확인 후에만 커밋
- **DART/EDGAR 동시**: 모든 개선은 DART/EDGAR 양쪽 반영 (protocol 테스트 강제)
- **import 방향**: L0 ← L1 ← L1.5 ← L2 ← L3 ← L4 (CI 검증)
