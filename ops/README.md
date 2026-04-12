# dartlab 운영문서

프로젝트 전체의 설계 규칙, 엔진별 운영 체계, 품질 관리 절차를 한곳에 모은다.

## 진입점

| 문서 | 레이어 | 엔진 | 한 줄 요약 |
|------|--------|------|----------|
| [company.md](company.md) | L0/L1 | Company facade | sections 사상, 4 namespace, canHandle 라우팅 |
| [data.md](data.md) | L0 | core/dataConfig | HF 데이터셋, 수집 파이프라인, 카테고리 관리 |
| [scan.md](scan.md) | L1.5 | scan/ | 13축 시장 횡단분석 — 전종목 사전 빌드 (parquet) |
| [gather.md](gather.md) | L1 | gather/ | 외부 시장 데이터 (주가/수급/매크로/뉴스) |
| [quant.md](quant.md) | L2 | quant/ | 가격 기반 정량 신호 — c.quant(), dartlab.quant() |
| [search.md](search.md) | L0 | core/search/ | 공시 시맨틱 검색 *(alpha)* |
| [mappers.md](mappers.md) | L0 | core/mappers/ | 매퍼 통합 엔진 — 계정/topic/alias/flow/notes, 학습 메커니즘 |
| [listing.md](listing.md) | facade | listing.py | 목록 조회 단일 진입점 — `dartlab.listing(kind, ...)` |
| [analysis.md](analysis.md) | L2 | analysis/ | 재무 심층분석 + 전망 + 가치평가, 6막 인과 구조 |
| [macro.md](macro.md) | L2 | macro/ | 시장 레벨 매크로 분석 — Company 불필요 |
| [review.md](review.md) | L3 | review/ | 이야기꾼 — L2 엔진 4개 + scan 소비, 보고서 조립 + 4 출력 형식 |
| [credit.md](credit.md) | L2 | credit/ | 독립 신용평가 (dCR 20단계, 7축, 투명 공개) |
| [ai.md](ai.md) | L4 | ai/ | 적극적 분석가, 5 provider (AI + 사람 둘 다 L4 소비자) |
| [guide.md](guide.md) | 교차 | guide/ | 안내 데스크 + 교육 안내자, 4층위 |
| [channel.md](channel.md) | L4 | channel/ | 외부 공유 — Microsoft DevTunnels 자동 셋업, `dartlab channel` |
| [experiments.md](experiments.md) | — | experiments/ | 실험 규칙, 흡수 판단 |
| [edgar.md](edgar.md) | L1 | providers/edgar/ | EDGAR 동기화 규칙, EXEMPT 관리 (데이터/분석 동작은 각 엔진 문서에 통합) |
| [code.md](code.md) | — | 전체 | camelCase, 독스트링 9섹션, 릴리즈, Git |
| [spaces.md](spaces.md) | L4 | server/ + mcp/ | HuggingFace Spaces — 설치 없이 API + MCP 서버, DART 키 프록시, 자동 배포 |
| [vscode.md](vscode.md) | L4 | vscode/ | VSCode 확장 — 프로바이더 연결, stdio 프로토콜, 배포 |
| [ui.md](ui.md) | L4 | ui/ | Svelte SPA — 패리티 규칙 (VSCode 선행) |
| [viz.md](viz.md) | 교차 | viz/ | 차트 + 다이어그램 시각화 엔진 |
| **[api-contract.md](api-contract.md)** | **—** | **전체** | **모든 API 호출 규칙 — 단일 진입점 + 파라미터 계약, 분기 기본 + 연간 파라미터, 파라미터 이름 일관성. 새 함수 추가 전 필독.** |
| **[architecture.md](architecture.md)** | **—** | **전체** | **전체 청사진 — 레이어, 엔진, 규칙, 데이터 출력** |
| **[testing.md](testing.md)** | **—** | **전체** | **테스트 체계 — 마커, 커버리지 90% 목표, CI** |
| **[issues.md](issues.md)** | **—** | **전체** | **이슈 관리 — GitHub Issue + 테스트 + 커밋 연결 체계** |

## 레이어 아키텍처

"엔진 = 도구 (숫자만), review = 이야기꾼, AI/사람 = 소비자" (1.0.0 리팩토링)

```
┌──────────────────────────────────────────────────────────────────────┐
│ L4  소비자          ai/  +  사람 (투자자/분석가)                      │
│                     해석과 판단 (review 보고서를 읽고 판단)            │
├──────────────────────────────────────────────────────────────────────┤
│ L3  이야기꾼        review/                                           │
│                     L2 4엔진 + scan 소비 → 보고서 조립 (6막 서사)     │
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
- **review가 조합한다** — 4개 엔진의 결과를 6막 서사로 조립, narrate 문장 생성

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
